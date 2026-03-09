from django.http import Http404
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from ..models import SellerProfile , SellerDocs, Property, PropertyImage
from ..permissions import IsSeller
from ..serializers import (
    SellerProfileSerializer, 
    SellerDocsSerializer, 
    PropertyListSerializer, 
    PropertyDetailSerializer, 
    PropertyCreateUpdateSerializer, 
    PropertyImageSerializer
)
import logging

class SellerProfileDetailView(generics.RetrieveUpdateAPIView):
    """
    get:
    Retrieve the profile of the currently authenticated seller.

    update:
    Update the profile of the currently authenticated seller.
    """
    serializer_class = SellerProfileSerializer
    permission_classes = [IsSeller]

    def get_object(self):
        # Retrieve the profile for the currently authenticated user
        try:
            return SellerProfile.objects.get(user=self.request.user)
        except SellerProfile.DoesNotExist:
            raise Http404
    
    def update(self, request, *args, **kwargs):
        # This checks if the request is a PATCH (partial=True) or PUT (partial=False).
        partial = kwargs.pop('partial', False)
        try:

            instance = self.get_object()
            # if instance is found, update it
            serializer = self.get_serializer(instance, data= request.data, partial= partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data)
        
        except Http404:
            # If profile does not exist, create it
            # if get_object() raises Http404, no profile exists, so we create a new one
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            # manually associate the new profile with the current user before saving
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        



logger = logging.getLogger(__name__)
class SellerDocsUploadView(generics.RetrieveUpdateAPIView):
    serializer_class = SellerDocsSerializer
    permission_classes = [IsSeller]

    def get_object(self):
        try:
            seller_profile = SellerProfile.objects.get(user=self.request.user)
            return seller_profile.docs
        except SellerProfile.DoesNotExist:
            raise Http404
        
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                already_set_user = SellerDocs.objects.get(user=self.request.user)
                if already_set_user:
                    self.perform_update(serializer)
                    return Response(serializer.data, status=status.HTTP_200_OK)
            except Exception as e:
                logger.error(f"Failed to update SellerDocs for user {request.user.id}: {str(e)}")
                return Response(
                    {"error": "Failed to save document. Please try again."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
        except Http404:
            # If docs don't exist, create new ones
            serializer = self.get_serializer(data=request.data)
            
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                docs = SellerDocs.objects.create(
                    user=request.user,
                    **serializer.validated_data
                )
                seller = SellerProfile.objects.get(user=request.user)
                seller.docs = docs
                seller.save()
                return Response(SellerDocsSerializer(docs).data, status=status.HTTP_201_CREATED)
            except SellerProfile.DoesNotExist:
                docs.delete()
                logger.error(f"SellerProfile not found for user {request.user.id}")
                return Response(
                    {"error": "Seller profile not found."},
                    status=status.HTTP_404_NOT_FOUND
                )
            except Exception as e:
                logger.error(f"Failed to create SellerDocs for user {request.user.id}: {str(e)}")
                return Response(
                    {"error": "Failed to upload document. Please try again."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            logger.error(f"Unexpected error in SellerDocsUploadView for user {request.user.id}: {str(e)}")
            return Response(
                {"error": "An unexpected error occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class SellerPropertyPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50

class PropertyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for sellers to manage their properties.
    - list: Returns a list of properties for the authenticated seller.
    - create: Creates a new property.
    - retrieve: Retrieves a specific property by ID.
    - update: Updates a specific property.
    - partial_update: Partially updates a specific property.
    - destroy: Deletes a specific property.
    """
    permission_classes = [IsSeller]
    parser_classes = [MultiPartParser, FormParser]
    pagination_class = SellerPropertyPagination

    def get_queryset(self):
        """
        This view returns a list of properties for the currently authenticated seller.
        The list can be filtered by providing a 'status' query parameter.
        e.g., /api/seller/properties/?status=pending
        """
        user = self.request.user
        
        # This view is protected by IsSeller permission, but a check is good practice.
        if not (user.is_authenticated and user.role == 'seller'):
            return Property.objects.none()

        queryset = Property.objects.filter(user=user)

        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)

        return queryset.order_by('-created_at')

    def get_serializer_class(self):
        """
        Return different serializers for different actions.
        """
        if self.action == 'list':
            return PropertyListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return PropertyCreateUpdateSerializer
        return PropertyDetailSerializer # For 'retrieve'

    def get_serializer_context(self):
        """
        Extra context provided to the serializer.
        """
        return {'request': self.request}

    def create(self, request, *args, **kwargs):
        """
        Custom create method to use a different serializer for the response.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        # Serialize the instance with the detail serializer for the response
        response_serializer = PropertyDetailSerializer(instance, context=self.get_serializer_context())
        headers = self.get_success_headers(response_serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        """
        Custom update method to use a different serializer for the response.
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        updated_instance = serializer.save()

        # Serialize the instance with the detail serializer for the response
        response_serializer = PropertyDetailSerializer(updated_instance, context=self.get_serializer_context())
        return Response(response_serializer.data)

    @action(detail=True, methods=['post'], url_path='upload-image')
    def upload_image(self, request, pk=None):
        """
        Custom action to upload an image to a specific property.
        """
        property_instance = self.get_object()
        
        # Check if the user owns this property
        if property_instance.user != request.user:
            return Response({'error': 'You do not have permission to add an image to this property.'}, status=status.HTTP_403_FORBIDDEN)

        # The 'image' field is expected in the request data
        serializer = PropertyImageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(property=property_instance)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
