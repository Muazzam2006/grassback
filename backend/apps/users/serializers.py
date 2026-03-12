from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.users import services as user_services

User = get_user_model()



class UserSponsorSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ["id", "phone", "first_name", "last_name"]
        read_only_fields = ["id", "phone", "first_name", "last_name"]



class UserCreateSerializer(serializers.ModelSerializer):

    address = serializers.CharField(required=True, allow_blank=False)
    sponsor = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True,
        source="parent",           
    )

    class Meta:
        model = User
        fields = ["phone", "first_name", "last_name", "address", "sponsor"]

    def validate_phone(self, value: str) -> str:
        try:
            return User.objects._validate_phone(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def validate(self, attrs):
        request = self.context.get("request")
        if request and request.user.is_authenticated and request.user.is_staff:
            return attrs

        phone = attrs.get("phone")
        if not phone:
            return attrs

        if not user_services.is_phone_verified_for_registration(phone):
            raise serializers.ValidationError(
                {"phone": ["Phone number is not verified. Verify OTP code first."]}
            )
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(password=None, **validated_data)
        user_services.consume_phone_registration_verification(validated_data["phone"])
        return user


class RegistrationOTPRequestSerializer(serializers.Serializer):
    phone = serializers.CharField()

    def validate_phone(self, value: str) -> str:
        try:
            normalized_phone = User.objects._validate_phone(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

        if User.objects.filter(phone=normalized_phone).exists():
            raise serializers.ValidationError("A user with this phone already exists.")

        return normalized_phone

    def create(self, validated_data):
        user_services.request_registration_otp(validated_data["phone"])
        return {"detail": "OTP code sent successfully."}


class RegistrationOTPVerifySerializer(serializers.Serializer):
    phone = serializers.CharField()
    otp_code = serializers.CharField()

    def validate_phone(self, value: str) -> str:
        try:
            return User.objects._validate_phone(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def create(self, validated_data):
        try:
            user_services.verify_registration_otp_code(validated_data["phone"], validated_data["otp_code"])
        except user_services.OTPVerificationError as exc:
            raise serializers.ValidationError({"otp_code": str(exc)}) from exc

        user_services.mark_phone_verified_for_registration(validated_data["phone"])
        return {"detail": "OTP code verified successfully."}



class UserDetailSerializer(serializers.ModelSerializer):
    
    sponsor = UserSponsorSerializer(read_only=True, source="parent")

    class Meta:
        model = User
        fields = [
            "id",
            "phone",
            "first_name",
            "last_name",
            "address",
            "is_active",
            "date_joined",
            "referral_code",
            "sponsor",
            "status",
            "personal_turnover",
            "team_turnover",
            "bonus_balance",
        ]
        read_only_fields = fields



class UserUpdateSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = User
        fields = ["first_name", "last_name", "address"]

    def validate(self, attrs):
        _financial = {"personal_turnover", "team_turnover", "bonus_balance"}
        initial_data = self.initial_data if isinstance(self.initial_data, dict) else {}
        for field in _financial:
            if field in initial_data:
                raise serializers.ValidationError(
                    {field: "Financial fields cannot be updated through this endpoint."}
                )
        return attrs  

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)



