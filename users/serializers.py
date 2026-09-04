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