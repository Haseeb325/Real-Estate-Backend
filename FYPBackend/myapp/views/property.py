from django.db.models import Q
from rest_framework import generics, permissions
from rest_framework.filters import SearchFilter, OrderingFilter
from ..models import Property
from ..serializers import PropertyListSerializer, PropertyDetailSerializer
from ..utils.mixins import StandardAPIViewMixin
from ..utils.pagination import StandardResultsSetPagination


class PropertyPagination(StandardResultsSetPagination):
    page_size = 12

class PropertyListAPIView(StandardAPIViewMixin, generics.ListAPIView):
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

    search_fields = ['title', 'location', 'location_text', 'property_type', 'sale_type']
    ordering_fields = ['created_at', 'updated_at', 'sale_price', 'rent_price']
    
    def get_queryset(self):
        """
        This view should return a list of all active, available, and verified properties.
        Supports filtering by both Property fields and related property-type details.
        """
        queryset = Property.objects.filter(
            status='active', 
            is_available=True, 
            is_verified=True
        ).order_by('-created_at')

        filter_map = {
            'property_type': 'property_type',
            'sale_type': 'sale_type',
            'status': 'status',
            'is_available': 'is_available',
            'is_verified': 'is_verified',
            'location': 'location__icontains',
            'location_text': 'location_text__icontains',
            'title': 'title__icontains',
            'user_id': 'user_id',

            # nested model simple equals
            'bedrooms': ['house__bedrooms', 'apartments__bedrooms'],
            'bathrooms': ['house__bathrooms', 'apartments__bathrooms'],
            'builtup_area': ['house__builtup_area', 'apartments__builtup_area', 'commercial__builtup_area'],
            'year_built': ['house__year_built'],
            'parking': ['house__parking', 'apartments__parking', 'commercial__parking_details'],
            'sub_type': ['house__sub_type'],
            'furnishing': ['apartments__furnishing', 'commercial__furnishing'],
            'occupant_preference': ['apartments__occupant_preference'],
            'plot_type': ['plots_and_land__plot_type'],
            'commercial_type': ['commercial__commercial_type'],
            'commercial_subtype': ['commercial__commercial_subtype'],
        }

        text_contains_map = {'location', 'location_text', 'title'}

        def _parse_bool(value):
            if value is None:
                return None
            value_lower = str(value).strip().lower()
            if value_lower in ['true', '1', 'yes', 'y']:
                return True
            if value_lower in ['false', '0', 'no', 'n']:
                return False
            return None

        def _parse_int(value):
            try:
                return int(value)
            except (ValueError, TypeError):
                return None

        def _parse_float(value):
            try:
                return float(value)
            except (ValueError, TypeError):
                return None

        # apply dynamic filters from query params
        q = Q()
        allowed_keys = set(filter_map.keys()) | {'min_price', 'max_price', 'min_builtup_area', 'max_builtup_area'}
        incoming_keys = [k for k in self.request.query_params.keys() if k not in ['page', 'page_size', 'ordering', 'search']]
        invalid_keys = [k for k in incoming_keys if k not in allowed_keys]
        if invalid_keys:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({
                'filters': f"Invalid filter keys provided: {', '.join(invalid_keys)}. "
                           f"Allowed keys: {', '.join(sorted(allowed_keys))}."
            })

        for key, raw_value in self.request.query_params.items():
            if key in ['page', 'page_size', 'ordering', 'search']:
                continue
            if raw_value is None or raw_value == '':
                continue

            if key in ['min_price', 'max_price', 'min_builtup_area', 'max_builtup_area']:
                if key == 'min_price':
                    parsed = _parse_float(raw_value)
                    if parsed is not None:
                        q &= (Q(sale_price__gte=parsed) | Q(rent_price__gte=parsed))
                if key == 'max_price':
                    parsed = _parse_float(raw_value)
                    if parsed is not None:
                        q &= (Q(sale_price__lte=parsed) | Q(rent_price__lte=parsed))
                if key == 'min_builtup_area':
                    parsed = _parse_int(raw_value)
                    if parsed is not None:
                        q &= (Q(house__builtup_area__gte=parsed) | Q(apartments__builtup_area__gte=parsed) | Q(commercial__builtup_area__gte=parsed))
                if key == 'max_builtup_area':
                    parsed = _parse_int(raw_value)
                    if parsed is not None:
                        q &= (Q(house__builtup_area__lte=parsed) | Q(apartments__builtup_area__lte=parsed) | Q(commercial__builtup_area__lte=parsed))
                continue

            if key in filter_map:
                mapping = filter_map[key]
                bool_val = _parse_bool(raw_value)

                if key in ['is_available', 'is_verified']:
                    if bool_val is None:
                        continue
                    q &= Q(**{mapping: bool_val})
                    continue

                int_val = _parse_int(raw_value)
                if key in ['bedrooms', 'bathrooms', 'year_built', 'building_grade']:
                    if int_val is None:
                        continue
                    raw_value = int_val

                # handle nested lookups for related tables; OR-join across property types
                if isinstance(mapping, list):
                    nested_q = Q()
                    for lookup in mapping:
                        nested_q |= Q(**{lookup: raw_value})
                    q &= nested_q
                else:
                    q &= Q(**{mapping: raw_value})
                continue

            # fallback: try direct property field exact match
            q &= Q(**{f"{key}": raw_value})

        queryset = queryset.filter(q)
        return queryset


class PropertyDetailAPIView(StandardAPIViewMixin, generics.RetrieveAPIView):
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
