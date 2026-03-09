from ..serializers import UserSerializer
from rest_framework import generics, permissions
from ..models import CustomUser

class UserDetailView(generics.RetrieveAPIView):
    """
    get:
    Retrive the details of the currently authenticated user.
"""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_object(self):
        return CustomUser.objects.get(id = self.request.user.id)
