from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.http import Http404
from ..models import BuyerProfile
from ..serializers import BuyerProfileSerializer


class BuyerProfileDetailView(generics.RetrieveUpdateAPIView):
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
             return Response(serializer.data)
            except Exception as e:
                print(f"Error during update: {e}")
                return Response({"message":"failed to upload"}, status=status.HTTP_400_BAD_REQUEST)
        except Http404:
            # If profile does not exist, create it
            # if get_object() fails , no profile exists, so we create a new one
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            # manually associate the new profile with the current user before saving
            try:
             serializer.save(user=request.user)
             return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                print(f"Error during creation: {e}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            