from rest_framework import generics, permissions
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.pagination import PageNumberPagination
from ..models import Property
from ..serializers import PropertyListSerializer, PropertyDetailSerializer

class PropertyPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = 'page_size'
    max_page_size = 100

class PropertyListAPIView(generics.ListAPIView):
    """
    get:
    Returns a list of all active and verified properties available for sale or rent.
    
    Supports searching by title, location, and property_type.
    Supports ordering by created_at, sale_price, and rent_price.
    
    Example search: /api/properties/browse/?search=house in the city
    Example ordering: /api/properties/browse/?ordering=-created_at
    """
    serializer_class = PropertyListSerializer
    # permission_classes = [permissions.IsAuthenticated]
    pagination_class = PropertyPagination
    filter_backends = [SearchFilter, OrderingFilter]
    
    search_fields = ['title', 'location', 'property_type', 'sale_type']
    ordering_fields = ['created_at', 'updated_at', 'sale_price', 'rent_price']
    
    def get_queryset(self):
        """
        This view should return a list of all active, available, and verified properties.
        """
        return Property.objects.filter(
            status='active', 
            is_available=True, 
            is_verified=True
        ).order_by('-created_at')

class PropertyDetailAPIView(generics.RetrieveAPIView):
    """
    get:
    Retrieve the details of a single active and verified property.
    """
    serializer_class = PropertyDetailSerializer
    # permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'pk'

    def get_queryset(self):
        """
        This view should only return active, available, and verified properties.
        """
        return Property.objects.filter(
            status='active', 
            is_available=True, 
            is_verified=True
        )
