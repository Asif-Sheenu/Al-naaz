from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password

from organization.models import Branch

from .models import User


class UserBranchSerializer(serializers.ModelSerializer):

    class Meta:
        model = Branch

        fields = [
            "id",
            "name",
            "code",
        ]


class LoginSerializer(serializers.Serializer):

    username = serializers.CharField()

    password = serializers.CharField(
        write_only=True
    )


class UserSerializer(serializers.ModelSerializer):

    branches = UserBranchSerializer(
    many=True,
    read_only=True,
)

    class Meta:
        model = User

        fields = [
            "id",
            "username",
            "email",
            "phone",
            "role",
            "branches",
            "is_active",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "role",
            "branches",
            "is_active",
            "created_at",
        ]


class UserUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = User

        fields = [
            "username",
            "email",
            "phone",
            "role",
        ]


class ManagedUserCreateSerializer(serializers.Serializer):

    username = serializers.CharField(
        max_length=150
    )

    password = serializers.CharField(
        write_only=True,
        min_length=8
    )

    email = serializers.EmailField(
        required=False,
        allow_blank=True
    )

    phone = serializers.CharField(
        max_length=15,
        required=False,
        allow_blank=True,
        allow_null=True
    )

    role = serializers.ChoiceField(
        choices=[
            (User.Roles.MANAGER, "Manager"),
            (User.Roles.STAFF, "Staff"),
        ]
    )


from rest_framework import serializers

from organization.models import Branch

from .models import User


class UserBranchSerializer(serializers.ModelSerializer):

    class Meta:
        model = Branch

        fields = [
            "id",
            "name",
            "code",
        ]


class LoginSerializer(serializers.Serializer):

    username = serializers.CharField()

    password = serializers.CharField(
        write_only=True
    )


class UserSerializer(serializers.ModelSerializer):

    branches = UserBranchSerializer(
    many=True,
    read_only=True,
)

    class Meta:
        model = User

        fields = [
            "id",
            "username",
            "email",
            "phone",
            "role",
            "branches",
            "is_active",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "role",
            "branches",
            "is_active",
            "created_at",
        ]


class UserUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = User

        fields = [
            "username",
            "email",
            "phone",
            "role",
        ]


class ManagedUserCreateSerializer(serializers.Serializer):

    username = serializers.CharField(
        max_length=150
    )

    password = serializers.CharField(
        write_only=True,
        min_length=8
    )

    email = serializers.EmailField(
        required=False,
        allow_blank=True
    )

    phone = serializers.CharField(
        max_length=15,
        required=False,
        allow_blank=True,
        allow_null=True
    )

    role = serializers.ChoiceField(
        choices=[
            (User.Roles.MANAGER, "Manager"),
            (User.Roles.STAFF, "Staff"),
        ]
    )

class ManagedUserSerializer(serializers.ModelSerializer):

    branches = UserBranchSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = User

        fields = [
            "id",
            "username",
            "email",
            "phone",
            "role",
            "branches",
            "is_active",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "username",
            "role",
            "branches",
            "is_active",
            "created_at",
        ]


class ManagedUserUpdateSerializer(serializers.ModelSerializer):
    branches = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Branch.objects.filter(is_active=True),
        required=False,
    )

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "phone",
            "role",
            "branches",
            "is_active",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "username",
            "role",
            "is_active",
            "created_at",
        ]        


class ProfileSerializer(serializers.ModelSerializer):
    branches = UserBranchSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "phone",
            "role",
            "branches",
            "is_active",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "role",
            "branches",
            "is_active",
            "created_at",
        ]







class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(
        write_only=True,
        required=True,
        trim_whitespace=False,
    )
    new_password = serializers.CharField(
        write_only=True,
        required=True,
        trim_whitespace=False,
    )

    
    def validate(self, attrs):
        user = self.context["request"].user

        if not user.check_password(attrs["current_password"]):
            raise serializers.ValidationError({
                "current_password": "Current password is incorrect."
            })

        if attrs["current_password"] == attrs["new_password"]:
            raise serializers.ValidationError({
                "new_password": "New password must differ from the current password."
            })

        return attrs
