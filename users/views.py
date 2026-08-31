from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .permissions import IsAdmin
from .serializers import UserSerializer,UserUpdateSerializer,LoginSerializer,ManagedUserCreateSerializer,ManagedUserSerializer
from rest_framework import status,viewsets
from rest_framework import generics
from .models import User
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema
from .services.user_service import create_managed_user

class LoginView(APIView):

    permission_classes = []
    @extend_schema(
    request=LoginSerializer,
    responses=UserSerializer
    )
    def post(self, request):

        username = request.data.get("username")
        password = request.data.get("password")

        user = authenticate(
            username=username,
            password=password
        )

        if user is None:
            return Response(
                {"message": "Invalid username or password !","error": "Invalid username or password"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        serializer = UserSerializer(user)

        response = Response(
            {
                "message": "Login successful",
                "user": serializer.data
            },
            status=status.HTTP_200_OK
        )

        response.set_cookie(
            key="access_token",
            value=str(access),
            httponly=True,
            secure=True,      # Change to True in production (HTTPS)
            samesite="None",
            max_age=60 * 60
        )

        response.set_cookie(
            key="refresh_token",
            value=str(refresh),
            httponly=True,
            secure=True,
            samesite="None",
            max_age=60 * 60 * 24 * 7
        )

        return response


class ProfileView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        serializer = UserSerializer(request.user)

        return Response(serializer.data)

# create staff 

class StaffCreateView(APIView): 

    permission_classes = [IsAdmin]

    def post(self, request):

        serializer = UserSerializer(data=request.data)

        if serializer.is_valid():

            serializer.save()

            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )    


# all staff 
# 

class StaffListView(generics.ListAPIView):

    serializer_class = UserSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        return User.objects.filter(role="STAFF" )       


# update staff  

class StaffUpdateView(generics.UpdateAPIView):

    queryset = User.objects.filter(role="STAFF")
    serializer_class = UserUpdateSerializer
    permission_classes = [IsAdmin]


# delete staff 

class StaffDeactivateView(generics.UpdateAPIView):

    queryset = User.objects.filter(role="STAFF")
    permission_classes = [IsAdmin]

    def patch(self, request, *args, **kwargs):

        staff = self.get_object()

        staff.is_active = False

        staff.save()

        return Response({
            "message":"Staff account deactivated."
        })



class RefreshView(APIView):

    permission_classes = []

    def post(self, request):

        refresh_token = request.COOKIES.get("refresh_token")

        if not refresh_token:
            return Response(
                {"error": "Refresh token not found"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:

            refresh = RefreshToken(refresh_token)

            access = refresh.access_token

            response = Response(
                {
                    "message": "Token refreshed"
                },
                status=status.HTTP_200_OK
            )

            response.set_cookie(
                key="access_token",
                value=str(access),
                httponly=True,
                secure=True,
                samesite="None",
                max_age=60 * 60
            )

            return response

        except TokenError:

            return Response(
                {"error": "Invalid refresh token"},
                status=status.HTTP_401_UNAUTHORIZED
            )    


class LogoutView(APIView):

    permission_classes = []

    def post(self, request):

        response = Response(
            {
                "message": "Logged out successfully"
            }
        )

        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")

        return response        

    

class UserManagementViewSet(viewsets.ModelViewSet):

    queryset = (
        User.objects
        .filter(
            role__in=[
                User.Roles.MANAGER,
                User.Roles.STAFF,
            ]
        )
        .order_by("username")
    )

    permission_classes = [IsAdmin]

    def get_serializer_class(self):

        if self.action == "create":
            return ManagedUserCreateSerializer

        return ManagedUserSerializer

    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        try:
            user = create_managed_user(
                username=serializer.validated_data["username"],
                password=serializer.validated_data["password"],
                role=serializer.validated_data["role"],
                email=serializer.validated_data.get(
                    "email",
                    ""
                ),
                phone=serializer.validated_data.get(
                    "phone"
                ),
            )

        except ValueError as exc:

            return Response(
                {
                    "detail": str(exc)
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        response_serializer = ManagedUserSerializer(
            user
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )    