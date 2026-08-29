from rest_framework import serializers

from .models import Branch, Company
from users.models import User


class CompanySerializer(serializers.ModelSerializer):

    branch_count = serializers.SerializerMethodField()

    class Meta:
        model = Company

        fields = [
            "id",
            "name",
            "code",
            "address",
            "phone",
            "email",
            "is_active",
            "branch_count",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "branch_count",
            "created_at",
            "updated_at",
        ]

    def get_branch_count(self, obj):
        return obj.branches.count()


class BranchSerializer(serializers.ModelSerializer):

    user_count = serializers.SerializerMethodField()

    users = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=User.objects.all(),
        required=False,
    )

    class Meta:
        model = Branch

        fields = [
            "id",
            "company",
            "name",
            "code",
            "address",
            "phone",
            "email",
            "users",
            "user_count",
            "is_active",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "user_count",
            "created_at",
            "updated_at",
        ]

    def get_user_count(self, obj):
        return obj.users.count()