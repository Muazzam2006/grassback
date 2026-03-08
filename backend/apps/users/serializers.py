from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers

User = get_user_model()



class UserSponsorSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ["id", "phone", "first_name", "last_name"]
        read_only_fields = ["id", "phone", "first_name", "last_name"]



class UserCreateSerializer(serializers.ModelSerializer):

    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    sponsor = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True,
        source="parent",           
    )

    class Meta:
        model = User
        fields = ["phone", "first_name", "last_name", "sponsor", "password"]

    def validate_phone(self, value: str) -> str:
        try:
            return User.objects._validate_phone(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def validate_password(self, value: str) -> str:
        validate_password(value)
        return value

    @transaction.atomic
    def create(self, validated_data: dict) -> User:
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)



class UserDetailSerializer(serializers.ModelSerializer):
    
    sponsor = UserSponsorSerializer(read_only=True, source="parent")

    class Meta:
        model = User
        fields = [
            "id",
            "phone",
            "first_name",
            "last_name",
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
        fields = ["first_name", "last_name"]

    def validate(self, attrs: dict) -> dict:
        _financial = {"personal_turnover", "team_turnover", "bonus_balance"}
        for field in _financial:
            if field in self.initial_data:
                raise serializers.ValidationError(
                    {field: "Financial fields cannot be updated through this endpoint."}
                )
        return attrs  

    def update(self, instance: User, validated_data: dict) -> User:
        return super().update(instance, validated_data)



