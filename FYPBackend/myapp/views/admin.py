from rest_framework import viewsets, filters, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from django.db.models import Sum
from ..models import (
    CustomUser, Property, SellerProfile, Payment, RentalAgreement, UserStatus
)
from ..serializers import (
    UserSerializer, PropertyDetailSerializer, PropertyListSerializer,
    SellerProfileSerializer, PaymentSerializer, RentalAgreementSerializer
)
from ..permissions import IsAdmin

class AdminPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

# Step 1: Admin Dashboard Stats
class AdminDashboardStatsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        total_users = CustomUser.objects.count()
        total_properties = Property.objects.count()
        
        # Pending verifications
        # Sellers who have uploaded docs but are not verified yet
        pending_sellers = SellerProfile.objects.filter(is_verified_seller=False).exclude(docs=None).count()
        # Properties that are not verified
        pending_properties = Property.objects.filter(is_verified=False).count()
        
        return Response({
            "total_users": total_users,
            "total_properties": total_properties,
            "pending_verifications": {
                "sellers": pending_sellers,
                "properties": pending_properties,
                "total": pending_sellers + pending_properties
            }
        })

# Step 2: User Management
class AdminUserViewSet(viewsets.ModelViewSet):
    """
    Admin view to manage users.
    Supports search by username/email and filtering by role/status.
    """
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]
    pagination_class = AdminPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['username', 'email', 'full_name']

    def get_queryset(self):
        queryset = CustomUser.objects.all().order_by('-id')
        
        # Filter by role (buyer/seller)
        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)
        
        # Filter by status (active/suspended)
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
            
        return queryset

    @action(detail=True, methods=['post'])
    def suspend(self, request, pk=None):
        user = self.get_object()
        user.status = UserStatus.SUSPENDED
        user.is_active = False
        user.save()
        return Response({'message': f'User {user.username} suspended.'})

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        user = self.get_object()
        user.status = UserStatus.ACTIVE
        user.is_active = True
        user.save()
        return Response({'message': f'User {user.username} activated.'})

# Step 3 & 4: Property Management & Listing Verification
class AdminPropertyViewSet(viewsets.ModelViewSet):
    """
    Admin view to manage properties.
    Includes stats, filtering, suspension, and verification logic.
    """
    permission_classes = [IsAdmin]
    pagination_class = AdminPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['title', 'location', 'user__username']

    def get_serializer_class(self):
        if self.action == 'list':
            return PropertyListSerializer
        return PropertyDetailSerializer

    def get_queryset(self):
        queryset = Property.objects.all().order_by('-created_at')
        
        # Filter by status (active/suspended/sold/rented etc)
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
            
        # Filter for verification requests (Step 4 Listing Verification)
        # Usage: /api/admin/properties/?verification_pending=true
        verification_pending = self.request.query_params.get('verification_pending')
        if verification_pending == 'true':
            queryset = queryset.filter(is_verified=False)
            
        return queryset

    @action(detail=False, methods=['get'])
    def stats(self, request):
        total = Property.objects.count()
        active = Property.objects.filter(status='active').count()
        suspended = Property.objects.filter(status='inactive').count() # Assuming inactive = suspended
        sold = Property.objects.filter(status='sold').count()
        rented = Property.objects.filter(status='reserved').count()
        
        return Response({
            "total": total,
            "active": active,
            "suspended": suspended,
            "sold": sold,
            "rented": rented
        })

    # Step 4: Listing Verification Actions
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        prop = self.get_object()
        prop.is_verified = True
        prop.status = 'active'
        prop.save()
        return Response({'message': 'Property verified and activated.'})

    @action(detail=True, methods=['post'])
    def reject_verification(self, request, pk=None):
        prop = self.get_object()
        prop.is_verified = False
        prop.status = 'reject'
        prop.save()
        return Response({'message': 'Property verification rejected.'})

    # Step 3: Suspend/Activate Actions
    @action(detail=True, methods=['post'])
    def suspend(self, request, pk=None):
        prop = self.get_object()
        prop.status = 'inactive'
        prop.save()
        return Response({'message': 'Property suspended.'})

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        prop = self.get_object()
        prop.status = 'active'
        prop.save()
        return Response({'message': 'Property activated.'})

# Step 4: User (Seller) Verification
class AdminSellerVerificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Viewset specifically for Seller Verification requests.
    Lists sellers who have uploaded documents.
    """
    serializer_class = SellerProfileSerializer
    permission_classes = [IsAdmin]
    pagination_class = AdminPagination

    def get_queryset(self):
        # Return sellers who have docs but are not verified (or all with docs)
        return SellerProfile.objects.exclude(docs=None).order_by('-created_at')

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        profile = self.get_object()
        profile.is_verified_seller = True
        profile.save()
        return Response({'message': 'Seller verified successfully.'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        profile = self.get_object()
        profile.is_verified_seller = False
        profile.save()
        return Response({'message': 'Seller verification rejected.'})

# Step 5: Financials
class AdminFinanceViewSet(viewsets.ViewSet):
    permission_classes = [IsAdmin]

    def list(self, request):
        return self.stats(request)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        sales_count = Payment.objects.filter(payment_type='sale', status='succeeded').count()
        active_rentings = RentalAgreement.objects.filter(status='active').count()
        
        revenue_sales = Payment.objects.filter(
            payment_type='sale', status='succeeded'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        revenue_rent = Payment.objects.filter(
            payment_type__in=['rent', 'security_deposit'], 
            status='succeeded'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        return Response({
            "sales_count": sales_count,
            "active_rentings": active_rentings,
            "revenue_sales": revenue_sales,
            "revenue_rent": revenue_rent
        })

    @action(detail=False, methods=['get'])
    def sales(self, request):
        """
        List sold properties (Payments of type 'sale').
        Supports date range filtering.
        """
        queryset = Payment.objects.filter(payment_type='sale', status='succeeded').order_by('-timestamp')
        
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(timestamp__range=[start_date, end_date])
            
        paginator = AdminPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = PaymentSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @action(detail=False, methods=['get'])
    def rentals(self, request):
        """
        List rented properties (Rental Agreements).
        Supports date range filtering.
        """
        queryset = RentalAgreement.objects.all().order_by('-created_at')
        
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(created_at__range=[start_date, end_date])

        paginator = AdminPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = RentalAgreementSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
