from rest_framework import serializers
from .services.access_service import get_accessible_branches
from .models import Branch, Company,Department
from users.models import User

class AssignUserSerializer(serializers.Serializer):

    user_id = serializers.IntegerField()


class RemoveUserSerializer(serializers.Serializer):

    user_id = serializers.IntegerField()
    
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



class DepartmentSerializer(serializers.ModelSerializer):

    branch_name = serializers.CharField(
        source="branch.name",
        read_only=True,
    )

    class Meta:
        model = Department

        fields = [
            "id",
            "branch",
            "branch_name"
            "name",
            "is_active",
        ]

        read_only_fields = [
            "id",
            "branch_name"
        ]


    def validate_branch(self, branch):

        request = self.context.get("request")

        if not request:
            return branch

        user = request.user

        if user.is_superuser or user.role == "ADMIN":
            return branch

        if not get_accessible_branches(user).filter(
            pk=branch.pk
        ).exists():
            raise serializers.ValidationError(
                "You do not have access to this branch."
            )

        return branch        