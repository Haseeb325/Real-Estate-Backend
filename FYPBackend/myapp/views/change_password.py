from ..serializers import ChangePasswordSerializer
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
import logging

logger = logging.getLogger(__name__)

class ChangePasswordView(viewsets.ViewSet):
    """
    ViewSet for changing password.
    """
    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request):
        try:
            serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(
                {"message": "Password changed successfully."},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Password change failed for user {request.user.id}: {str(e)}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )