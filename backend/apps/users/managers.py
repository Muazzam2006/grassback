import re

from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _normalize_phone(self, phone):
        phone = re.sub(r"[^\d+]", "", str(phone).strip())
        if phone.startswith("00"):
            phone = "+" + phone[2:]
        if not phone.startswith("+"):
            phone = "+" + phone
        return phone

    def _validate_phone(self, phone):
        if not phone:
            raise ValueError("Phone number is required")
        normalized = self._normalize_phone(phone)
        if not re.fullmatch(r"\+\d{10,15}", normalized):
            raise ValueError("Phone must be in valid international format")
        return normalized

    def rebuild(self):
        """Compatibility bridge for django-mptt rebuild API."""
        return self.model._tree_manager.rebuild()

    def _create_user_record(self, phone, password=None, **extra_fields):
        normalized_phone = self._validate_phone(phone)

        if not extra_fields.get("first_name"):
            raise ValueError("First name is required")
        if not extra_fields.get("last_name"):
            raise ValueError("Last name is required")

        user = self.model(phone=normalized_phone, **extra_fields)

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    def create_user(self, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff"):
            raise ValueError("Regular user cannot have is_staff=True")
        if extra_fields.get("is_superuser"):
            raise ValueError("Regular user cannot have is_superuser=True")

        return self._create_user_record(phone, password, **extra_fields)

    def create_superuser(self, phone, password=None, **extra_fields):
        if not password:
            raise ValueError("Superuser must have a password")

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")

        return self._create_user_record(phone, password, **extra_fields)
