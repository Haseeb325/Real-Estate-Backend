from ..serializers import ChangePasswordSerializer
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from ..utils.api_response import success_response, error_response
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
            return success_response(message="Password changed successfully.", data={}, status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Password change failed for user {request.user.id}: {str(e)}")
            return error_response(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)
