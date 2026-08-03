from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .permissions import IsAdmin
from .serializers import UserSerializer,UserUpdateSerializer
from rest_framework import status
from rest_framework import generics
from .models import User

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