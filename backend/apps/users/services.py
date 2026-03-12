import secrets
import string
import uuid
from datetime import timedelta

import httpx
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from .models import OTPPurpose, OTPToken

User = get_user_model()


class SmsConfigurationError(Exception):
    pass


class SmsDeliveryError(Exception):
    pass


class OTPVerificationError(Exception):
    pass


def _sms_is_configured() -> bool:
    return all(
        [
            getattr(settings, "SMS_LOGIN", ""),
            getattr(settings, "SMS_HASH", ""),
            getattr(settings, "SMS_SENDER", ""),
            getattr(settings, "SMS_SERVER", ""),
        ]
    )


def _normalize_phone(phone: str) -> str:
    return User.objects._validate_phone(phone)


def _phone_for_gateway(phone: str) -> str:
    return phone.lstrip("+")


def _generate_otp_code(length: int = 6) -> str:
    alphabet = string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _otp_ttl_minutes() -> int:
    return int(getattr(settings, "OTP_CODE_TTL_MINUTES", 5))


def _otp_max_attempts() -> int:
    return int(getattr(settings, "OTP_MAX_ATTEMPTS", 5))


def _otp_verified_ttl_minutes() -> int:
    return int(getattr(settings, "OTP_VERIFIED_TTL_MINUTES", 30))


def _otp_verified_cache_key(phone: str) -> str:
    return f"users:registration:otp-verified:{phone}"


def _extract_sms_error_message(response: httpx.Response, payload) -> str:
    if isinstance(payload, dict):
        for key in ("msg", "message", "error", "detail", "description"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        nested_error = payload.get("error")
        if isinstance(nested_error, dict):
            nested_msg = nested_error.get("msg") or nested_error.get("message")
            nested_code = nested_error.get("code")
            if isinstance(nested_msg, str) and nested_msg.strip():
                if nested_code is not None:
                    return f"{nested_msg.strip()} (code={nested_code})"
                return nested_msg.strip()

        status_value = payload.get("status")
        code_value = payload.get("code")
        if status_value is not None or code_value is not None:
            return f"SMS provider rejected request (status={status_value}, code={code_value})."

    raw_text = response.text.strip()
    if raw_text:
        return f"SMS provider returned HTTP {response.status_code}: {raw_text[:400]}"

    return f"SMS provider returned HTTP {response.status_code} without details."


def send_oson_sms(*, phone: str, message: str, txn_id: str | None = None) -> dict:
    if not _sms_is_configured():
        raise SmsConfigurationError("SMS provider settings are not configured.")

    params = {
        "from": settings.SMS_SENDER,
        "phone_number": _phone_for_gateway(phone),
        "msg": message,
        "login": settings.SMS_LOGIN,
        "str_hash": settings.SMS_HASH,
        "txn_id": txn_id or uuid.uuid4().hex[:20],
    }
    headers = {"Authorization": f"Bearer {settings.SMS_HASH}"}

    try:
        with httpx.Client(timeout=float(getattr(settings, "SMS_TIMEOUT_SEC", 10.0))) as client:
            response = client.get(settings.SMS_SERVER, params=params, headers=headers)
    except httpx.HTTPError as exc:
        raise SmsDeliveryError(f"Could not connect to SMS provider: {exc}") from exc

    raw_text = response.text.strip()

    try:
        payload = response.json()
    except ValueError:
        if response.is_success and "status=ok" in raw_text.lower():
            return {"status": "ok", "raw": raw_text}

        if raw_text:
            raise SmsDeliveryError(
                f"SMS provider returned non-JSON response (HTTP {response.status_code}): {raw_text[:400]}"
            )
        raise SmsDeliveryError(
            f"SMS provider returned non-JSON response with HTTP {response.status_code}."
        )

    status_value = ""
    if isinstance(payload, dict):
        status_value = str(payload.get("status", "")).strip().lower()

    if response.is_success and status_value in {"ok", "success"}:
        return payload

    raise SmsDeliveryError(_extract_sms_error_message(response, payload))


@transaction.atomic
def request_registration_otp(phone: str) -> OTPToken:
    normalized_phone = _normalize_phone(phone)

    cache.delete(_otp_verified_cache_key(normalized_phone))

    OTPToken.objects.filter(
        phone=normalized_phone,
        purpose=OTPPurpose.REGISTER,
        is_used=False,
    ).update(is_used=True)

    code = _generate_otp_code()
    token = OTPToken.objects.create(
        phone=normalized_phone,
        code_hash=OTPToken.hash_code(code),
        purpose=OTPPurpose.REGISTER,
        is_used=False,
        attempts=0,
        expires_at=timezone.now() + timedelta(minutes=_otp_ttl_minutes()),
    )

    message = f"Your verification code is: {code}"
    try:
        send_oson_sms(phone=normalized_phone, message=message, txn_id=str(token.pk).replace("-", "")[:20])
    except Exception:
        token.delete()
        raise

    return token


@transaction.atomic
def verify_registration_otp(phone: str, otp_code: str) -> None:
    _verify_registration_otp_impl(phone, otp_code)


def verify_registration_otp_code(phone: str, otp_code: str) -> None:
    _verify_registration_otp_impl(phone, otp_code)


def _verify_registration_otp_impl(phone: str, otp_code: str) -> None:
    normalized_phone = _normalize_phone(phone)

    token = (
        OTPToken.objects.select_for_update()
        .filter(
            phone=normalized_phone,
            purpose=OTPPurpose.REGISTER,
            is_used=False,
        )
        .order_by("-created_at")
        .first()
    )

    if token is None:
        raise OTPVerificationError("OTP code was not requested for this phone number.")

    if token.expires_at <= timezone.now():
        raise OTPVerificationError("OTP code has expired. Please request a new one.")

    if token.attempts >= _otp_max_attempts():
        raise OTPVerificationError("Maximum OTP attempts reached. Please request a new code.")

    token.attempts += 1
    is_valid = token.verify(otp_code)
    if not is_valid:
        token.save(update_fields=["attempts"])
        raise OTPVerificationError("Incorrect OTP code.")

    token.is_used = True
    token.save(update_fields=["attempts", "is_used"])


def mark_phone_verified_for_registration(phone: str) -> None:
    normalized_phone = _normalize_phone(phone)
    cache.set(
        _otp_verified_cache_key(normalized_phone),
        True,
        timeout=_otp_verified_ttl_minutes() * 60,
    )


def is_phone_verified_for_registration(phone: str) -> bool:
    normalized_phone = _normalize_phone(phone)
    return bool(cache.get(_otp_verified_cache_key(normalized_phone), False))


def consume_phone_registration_verification(phone: str) -> None:
    normalized_phone = _normalize_phone(phone)
    cache.delete(_otp_verified_cache_key(normalized_phone))
