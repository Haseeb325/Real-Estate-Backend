from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from .models import (
    CustomUser, UserStatus, BuyerProfile, SellerProfile, Property,
    Features, House, Apartment, PlotsAndLand, Commercial, ChatSession,
    ChatMessage, SellerAvailability, Appointment, Payment, Receipt,
    RentalAgreement, MonthlyRentPayment, PropertyImage, SellerDocs
)

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('id', 'email', 'username', 'full_name', 'role', 'status', 'is_active', 'is_staff', 'is_superuser')
    list_filter = ('role', 'status', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('id', 'email', 'username', 'full_name')
    ordering = ('email',)
    readonly_fields = ('id', 'last_login')
    actions = ['suspend_users', 'activate_users']
    
    fieldsets = (
        (None, {'fields': ('id', 'email', 'password')}),
        ('Personal info', {'fields': ('username', 'full_name', 'role')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Status', {'fields': ('status', 'is_email_verified')}),
        ('Important dates', {'fields': ('last_login',)}),
    )
    
    # Add this to allow creating users in Admin
    add_fieldsets = (
        (None, {'classes': ('wide',),
                'fields': ('email', 'username', 'full_name', 'password', 'confirm_password')}),
    )


    def suspend_users(self, request, queryset):
        # Never suspend superusers
        not_super = queryset.exclude(is_superuser=True)
        updated = not_super.update(status=UserStatus.SUSPENDED, is_active=False)
        self.message_user(request, f"{updated} user(s) suspended.", level=messages.SUCCESS)
    suspend_users.short_description = "Suspend selected users"

    def activate_users(self, request, queryset):
        updated = queryset.update(status=UserStatus.ACTIVE, is_active=True)
        self.message_user(request, f"{updated} user(s) activated.", level=messages.SUCCESS)
    activate_users.short_description = "Activate selected users"

@admin.register(BuyerProfile)
class BuyerProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'phone', 'city', 'state', 'country', 'created_at')
    readonly_fields = ('id', 'created_at', 'updated_at')
    search_fields = ('id', 'user__username', 'user__email', 'phone', 'city', 'state', 'country')
    list_filter = ('city', 'state', 'country', 'created_at')
    ordering = ('-created_at',)

@admin.register(SellerDocs)
class SellerDocsAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'created_at')
    readonly_fields = ('id', 'created_at', 'updated_at')
    search_fields = ('id', 'user__username',)
    ordering = ('-created_at',)

@admin.register(SellerProfile)
class SellerProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'company_name', 'phone', 'is_verified_seller', 'city', 'state')
    readonly_fields = ('id', 'created_at', 'updated_at')
    search_fields = ('id', 'user__username', 'user__email', 'company_name', 'city', 'state')
    list_filter = ('is_verified_seller', 'city', 'state', 'country')
    ordering = ('-created_at',)

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'user', 'property_type', 'status', 'is_available', 'is_verified', 'created_at')
    readonly_fields = ('id', 'created_at', 'updated_at')
    list_filter = ('property_type', 'status', 'is_available', 'is_verified', 'sale_type', 'created_at')
    search_fields = ('id', 'title', 'user__username', 'location')
    ordering = ('-created_at',)

@admin.register(PropertyImage)
class PropertyImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'property', 'image')
    readonly_fields = ('id',)
    search_fields = ('id', 'property__title',)
    autocomplete_fields = ['property']


@admin.register(Features)
class FeaturesAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    readonly_fields = ('id',)
    search_fields = ('id', 'name',)
    ordering = ('name',)

@admin.register(House)
class HouseAdmin(admin.ModelAdmin):
    list_display = ('id', 'property', 'bedrooms', 'bathrooms', 'builtup_area', 'parking', 'sub_type')
    readonly_fields = ('id', 'created_at', 'updated_at')
    search_fields = ('id', 'property__title',)
    list_filter = ('bedrooms', 'bathrooms', 'parking', 'sub_type', 'floors')
    autocomplete_fields = ['property']

@admin.register(Apartment)
class ApartmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'property', 'bedrooms', 'bathrooms', 'furnishing', 'has_balcony')
    readonly_fields = ('id', 'created_at', 'updated_at')
    search_fields = ('id', 'property__title',)
    list_filter = ('bedrooms', 'bathrooms', 'furnishing', 'has_balcony', 'occupant_preference')
    autocomplete_fields = ['property']

@admin.register(PlotsAndLand)
class PlotsAndLandAdmin(admin.ModelAdmin):
    list_display = ('id', 'property', 'plot_type', 'area', 'ownership')
    readonly_fields = ('id', 'created_at', 'updated_at')
    search_fields = ('id', 'property__title',)
    list_filter = ('plot_type', 'ownership', 'has_corner_plot', 'possession_status')
    autocomplete_fields = ['property']

@admin.register(Commercial)
class CommercialAdmin(admin.ModelAdmin):
    list_display = ('id', 'property', 'commercial_type', 'builtup_area', 'ownership', 'furnishing')
    readonly_fields = ('id', 'created_at', 'updated_at')
    search_fields = ('id', 'property__title',)
    list_filter = ('commercial_type', 'ownership', 'furnishing', 'building_grade', 'has_kitchen')
    autocomplete_fields = ['property']

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'property', 'buyer', 'created_at', 'updated_at')
    readonly_fields = ('id', 'created_at', 'updated_at')
    search_fields = ('id', 'property__title', 'buyer__username')
    list_filter = ('created_at',)
    ordering = ('-created_at',)
    autocomplete_fields = ['property', 'buyer']

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'chat_session', 'sender', 'timestamp', 'is_read')
    readonly_fields = ('id', 'timestamp')
    search_fields = ('id', 'chat_session__id', 'sender__username', 'content')
    list_filter = ('is_read', 'timestamp')
    ordering = ('-timestamp',)
    autocomplete_fields = ['chat_session', 'sender']

@admin.register(SellerAvailability)
class SellerAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('id', 'seller', 'property', 'days_of_week', 'start_time', 'end_time')
    readonly_fields = ('id',)
    search_fields = ('id', 'seller__username', 'property__title')
    autocomplete_fields = ['seller', 'property']

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'property', 'buyer', 'seller', 'start_time', 'end_time', 'status')
    readonly_fields = ('id', 'created_at', 'updated_at')
    list_filter = ('status', 'start_time')
    search_fields = ('id', 'property__title', 'buyer__username', 'seller__username')
    ordering = ('-start_time',)
    autocomplete_fields = ['property', 'buyer', 'seller']

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'stripe_charge_id', 'property', 'buyer', 'seller', 'amount', 'payment_type', 'status')
    readonly_fields = ('id', 'timestamp')
    list_filter = ('payment_type', 'status', 'timestamp')
    search_fields = ('id', 'stripe_charge_id', 'property__title', 'buyer__username', 'seller__username')
    ordering = ('-timestamp',)
    autocomplete_fields = ['property', 'buyer', 'seller']

@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ('id', 'payment', 'generated_at')
    readonly_fields = ('id', 'generated_at')
    search_fields = ('id', 'payment__id', 'payment__stripe_charge_id')
    list_filter = ('generated_at',)
    ordering = ('-generated_at',)
    autocomplete_fields = ['payment']

@admin.register(RentalAgreement)
class RentalAgreementAdmin(admin.ModelAdmin):
    list_display = ('id', 'property', 'buyer', 'start_date', 'end_date', 'status')
    readonly_fields = ('id', 'created_at')
    list_filter = ('status', 'start_date', 'end_date')
    search_fields = ('id', 'property__title', 'buyer__username')
    ordering = ('-start_date',)
    autocomplete_fields = ['property', 'buyer']

@admin.register(MonthlyRentPayment)
class MonthlyRentPaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'rental_agreement', 'due_date', 'amount', 'status', 'date_paid')
    readonly_fields = ('id',)
    list_filter = ('status', 'due_date', 'date_paid')
    search_fields = ('id', 'rental_agreement__id', 'rental_agreement__property__title')
    ordering = ('-due_date',)
    autocomplete_fields = ['rental_agreement']