"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from myapp.views.user import UserDetailView
from myapp.views.auth import *
from myapp.views.buyer import BuyerProfileDetailView
from myapp.views.seller import SellerProfileDetailView, SellerDocsUploadView, PropertyViewSet
from myapp.views.property import PropertyListAPIView, PropertyDetailAPIView
from myapp.views.change_password import ChangePasswordView
from myapp.views.chat import ChatSessionListCreateAPIView, ChatMessageListAPIView
from myapp.views.appointment import SellerAvailabilityViewSet, AppointmentViewSet
from myapp.views.payment import MockPaymentView, RentalAgreementViewSet, PaymentViewSet
from myapp.views.admin import (
    AdminDashboardStatsView,
    AdminUserViewSet,
    AdminPropertyViewSet,
    AdminSellerVerificationViewSet,
    AdminFinanceViewSet
)

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'properties', PropertyViewSet, basename='property')
router.register(r'seller/availabilities', SellerAvailabilityViewSet, basename='seller-availability')
router.register(r'appointments', AppointmentViewSet, basename='appointment')
router.register(r'rental-agreements', RentalAgreementViewSet, basename='rental-agreement')
router.register(r'payments', PaymentViewSet, basename='payment')

router.register(r'admin/users', AdminUserViewSet, basename='admin-users')
router.register(r'admin/properties', AdminPropertyViewSet, basename='admin-properties')
router.register(r'admin/verifications/sellers', AdminSellerVerificationViewSet, basename='admin-verify-sellers')
router.register(r'admin/finance', AdminFinanceViewSet, basename='admin-finance')

urlpatterns = [
    path('admin/', admin.site.urls),

    # Group all API endpoints under '/api/'
    path('api/', include([
        # Authentication
        path("register/step1", UserRegisterationStep1View.as_view(), name="register-step1"),
        path("verify-otp", VerifyOTPView.as_view(), name="verify-otp"),
        path("resend-otp", ResendOTPView.as_view(), name="resend-otp"),
        path("register/step2", UserRegistrationStep2View.as_view(), name="register-step2"),
        path("register/step3", UserRegistrationStep3View.as_view(), name="register-step3"),
        path("forgot-password", ForgotPassword.as_view(), name="forgot-password"),
        path("reset-password", ResetPassword.as_view(), name="reset-password"),
        path("sign-in", SignInView.as_view(), name="sign-in"),
        path("refresh-access-token", RefreshAccessTokenView.as_view(), name="refresh-access-token"),
        path("logout", LogoutView.as_view(), name="logout"),
        
        # User, Profiles, and Password
        path("get-current-user", UserDetailView.as_view(), name="get-current-user"),
        path("profile/buyer", BuyerProfileDetailView.as_view(), name="profile-buyer"),
        path("profile/seller", SellerProfileDetailView.as_view(), name="profile-seller"),
        path("profile/seller/docs", SellerDocsUploadView.as_view(), name="profile-seller-docs"),
        path("change-password", ChangePasswordView.as_view({'post': 'create'}), name="change-password"),
        
        # Property Browsing
        path('properties/browse/', PropertyListAPIView.as_view(), name='property-browse'),
        path('properties/browse/<uuid:pk>/', PropertyDetailAPIView.as_view(), name='property-detail-browse'),
        
        # Chat
        path('chat/sessions/', ChatSessionListCreateAPIView.as_view(), name='chat-session-list-create'),
        path('chat/sessions/<uuid:session_id>/messages/', ChatMessageListAPIView.as_view(), name='chat-message-list'),

        # Payment
        path('payments/process/', MockPaymentView.as_view(), name='payment-process'),

        # Admin Dashboard Stats
        path('admin/stats/', AdminDashboardStatsView.as_view(), name='admin-stats'),

        # Include the router-generated URLs for seller-specific property management
        path('', include(router.urls)),
    ]))
]
