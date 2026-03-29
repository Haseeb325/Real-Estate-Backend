from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.http import Http404
from ..models import BuyerProfile
from ..serializers import BuyerProfileSerializer
from ..utils.api_response import success_response, error_response
from ..utils.mixins import StandardAPIViewMixin


class BuyerProfileDetailView(StandardAPIViewMixin, generics.RetrieveUpdateAPIView):
    """
    get:
    Retrieve the profile of the currently authenticated buyer.

    update:
    Update or create the profile of the currently authenticated buyer (upsert).
    """
    serializer_class = BuyerProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        try:
            return BuyerProfile.objects.get(user=self.request.user)
        except BuyerProfile.DoesNotExist:
            raise Http404

    def update(self, request, *args, **kwargs):
        # This checks if the request is a PATCH (partial=True) or PUT (partial=False).
        partial = kwargs.get('partial', False)
        try:
            # If profile exists, update it
            
            instance = self.get_object() # This will raise Http404 if not found
            # update path
            # if get_object() succeeds , profile exists, so we update it
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            try:

             self.perform_update(serializer)
             return success_response(serializer.data, message='Profile updated successfully.', status_code=status.HTTP_200_OK)
            except Exception as e:
                print(f"Error during update: {e}")
                return error_response(message='failed to upload', status_code=status.HTTP_400_BAD_REQUEST)
        except Http404:
            # If profile does not exist, create it
            # if get_object() fails , no profile exists, so we create a new one
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            # manually associate the new profile with the current user before saving
            try:
             serializer.save(user=request.user)
             return success_response(serializer.data, status_code=status.HTTP_201_CREATED, message='Profile created successfully.')
            except Exception as e:
                print(f"Error during creation: {e}")
                return error_response(message=str(serializer.errors), data=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)
            