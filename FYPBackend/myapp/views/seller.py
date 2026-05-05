from django.http import Http404
from django.db.models import Q
from rest_framework import generics, permissions, status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from ..utils.api_response import success_response, error_response
from ..utils.mixins import StandardAPIViewMixin, StandardViewSetMixin
from ..utils.pagination import StandardResultsSetPagination
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

class SellerProfileDetailView(StandardAPIViewMixin, generics.RetrieveUpdateAPIView):
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
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return success_response(serializer.data, message="Profile updated successfully.", status_code=status.HTTP_200_OK)

        except Http404:
            # If profile does not exist, create it
            # if get_object() raises Http404, no profile exists, so we create a new one
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            # manually associate the new profile with the current user before saving
            serializer.save(user=request.user)
            return success_response(serializer.data, message="Profile created successfully.", status_code=status.HTTP_201_CREATED)
        



logger = logging.getLogger(__name__)
class SellerDocsUploadView(StandardAPIViewMixin, generics.RetrieveUpdateAPIView):
    serializer_class = SellerDocsSerializer
    permission_classes = [IsSeller]

    def get_object(self):
        # Always try to get docs directly from the user's relationship first
        try:
            return self.request.user.seller_docs
        except SellerDocs.DoesNotExist:
            return None

    def update(self, request, *args, **kwargs):
        # Determine if this is a partial update (PATCH)
        partial = kwargs.pop('partial', True) 
        instance = self.get_object()

        if instance:
            # --- UPDATE EXISTING DOCS ---
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            if not serializer.is_valid():
                return error_response(
                    message="Invalid seller docs payload", 
                    data=serializer.errors, 
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                self.perform_update(serializer)
                return success_response(
                    serializer.data, 
                    message="Seller docs updated successfully.", 
                    status_code=status.HTTP_200_OK
                )
            except Exception as e:
                logger.error(f"Update failed for user {request.user.id}: {str(e)}")
                return error_response(message="Failed to save document.", status_code=status.HTTP_400_BAD_REQUEST)

        else:
            # --- CREATE NEW DOCS ---
            serializer = self.get_serializer(data=request.data)
            if not serializer.is_valid():
                return error_response(
                    message="Invalid seller docs payload", 
                    data=serializer.errors, 
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                # Create the docs record
                docs = SellerDocs.objects.create(
                    user=request.user,
                    **serializer.validated_data
                )
                
                # Ensure it's linked to the SellerProfile
                seller_profile, created = SellerProfile.objects.get_or_create(user=request.user)
                seller_profile.docs = docs
                seller_profile.save()

                return success_response(
                    SellerDocsSerializer(docs).data, 
                    message="Seller docs created successfully.", 
                    status_code=status.HTTP_201_CREATED
                )
            except Exception as e:
                logger.error(f"Creation failed for user {request.user.id}: {str(e)}")
                return error_response(message="Failed to upload document.", status_code=status.HTTP_400_BAD_REQUEST)



class SellerPropertyPagination(StandardResultsSetPagination):
    page_size = 10
    max_page_size = 50

class PropertyViewSet(StandardViewSetMixin):
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
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    
    search_fields = ['title', 'location_text', 'property_type', 'sale_type']
    ordering_fields = ['created_at', 'updated_at', 'sale_price', 'rent_price']

    def get_queryset(self):
        """
        This view returns a list of properties for the currently authenticated seller.
        Supports filtering by status, property_type, sale_type, and price ranges.
        """
        user = self.request.user
        
        if not (user.is_authenticated and user.role == 'seller'):
            return Property.objects.none()

        queryset = Property.objects.filter(user=user)
        params = self.request.query_params

        # Simple field filters
        for field in ['status', 'property_type', 'sale_type']:
            val = params.get(field)
            if val:
                queryset = queryset.filter(**{field: val})

        # Price range filtering (Sale or Rent)
        q_price = Q()
        min_price = params.get('min_price')
        max_price = params.get('max_price')

        try:
            if min_price:
                val = float(min_price)
                q_price &= (Q(sale_price__gte=val) | Q(rent_price__gte=val))
            if max_price:
                val = float(max_price)
                q_price &= (Q(sale_price__lte=val) | Q(rent_price__lte=val))
        except (ValueError, TypeError):
            pass

        if q_price:
            queryset = queryset.filter(q_price)

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
        return success_response(data=response_serializer.data, message="Property created successfully.", status_code=status.HTTP_201_CREATED)

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
        return success_response(data=response_serializer.data, message="Property updated successfully.", status_code=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='upload-image')
    def upload_image(self, request, pk=None):
        """
        Custom action to upload an image to a specific property.
        """
        property_instance = self.get_object()
        
        # Check if the user owns this property
        if property_instance.user != request.user:
            return error_response(message='You do not have permission to add an image to this property.', status_code=status.HTTP_403_FORBIDDEN)

        # The 'image' field is expected in the request data
        serializer = PropertyImageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(property=property_instance)
            return success_response(data=serializer.data, message="Image uploaded successfully.", status_code=status.HTTP_201_CREATED)
        else:
            return error_response(message="Invalid image payload", data=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """
        Allows a seller to pause their active property listing.
        """
        property_instance = self.get_object()
        if property_instance.status != 'active':
            return error_response(
                message=f"Only active properties can be paused. Current status: {property_instance.status}", 
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        property_instance.status = 'pause'
        property_instance.save()
        return success_response(
            data=PropertyDetailSerializer(property_instance, context={'request': request}).data, 
            message="Property paused successfully."
        )

    @action(detail=True, methods=['post'])
    def reactivate(self, request, pk=None):
        """
        Allows a seller to reactivate a paused property listing.
        """
        property_instance = self.get_object()
        if property_instance.status != 'pause':
            return error_response(
                message="Only paused properties can be reactivated.", 
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        property_instance.status = 'active'
        property_instance.save()
        return success_response(
            data=PropertyDetailSerializer(property_instance, context={'request': request}).data, 
            message="Property reactivated successfully."
        )
