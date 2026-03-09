from django.db import models
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser , PermissionsMixin
from django.core.exceptions import ValidationError
import uuid
from cloudinary.models import CloudinaryField


class CustomUserManager(BaseUserManager):

    def create_user(self, email, username, full_name, role, password=None, status=None, is_email_verified=False, **extra_fields):
        if not email:
            raise ValueError("Email must be set")
        if not username:
            raise ValueError("Username must be set")

        email = self.normalize_email(email)

        # Default to ACTIVE if no status provided; validate if provided
        if status is None:
            status = UserStatus.ACTIVE
        else:
            valid_values = [choice[0] for choice in UserStatus.choices]
            if status not in valid_values:
                raise ValueError(f"Invalid status: {status}")

        user = self.model(
            email=email,
            username=username,
            full_name=full_name,
            role=role,
            status=status,
            is_email_verified=is_email_verified,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, full_name, password=None, **extra_fields):
        """
        Used ONLY for Django admin.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")

        return self.create_user(
            email=email,
            username=username,
            full_name=full_name,
            password=password,
            role="admin",
            status=UserStatus.ACTIVE,
            is_email_verified=True,
            **extra_fields
        )

    # def suspend_users(self, queryset):
    #     """Suspend users in the provided queryset (never suspend superusers)."""
    #     not_super = queryset.exclude(is_superuser=True)
    #     return not_super.update(status=UserStatus.SUSPENDED, is_active=False)

    # def activate_users(self, queryset):
    #     """Activate users in the provided queryset."""
    #     return queryset.update(status=UserStatus.ACTIVE, is_active=True)


    

class UserRole(models.TextChoices):
    ADMIN = "admin", "Admin"
    BUYER = "buyer", "Buyer"
    SELLER = "seller", "Seller"    

class UserStatus(models.TextChoices):
    ACTIVE = "active","Active"
    SUSPENDED = "suspended","Suspended"

class CustomUser(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True)
    full_name = models.CharField(max_length=150)
    role = models.CharField(max_length=50, choices=UserRole.choices,)
    is_email_verified = models.BooleanField(default=False)
    # Status allows admins to suspend/reactivate users without deleting them
    status = models.CharField(max_length=20, choices=UserStatus.choices, default=UserStatus.ACTIVE)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "full_name"]

    def __str__(self):
        return f"{self.username} ({self.role} - {self.status})"
           



# Buyer Profile Model
class BuyerProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="buyer_profile")
    phone=models.CharField(max_length=15 , blank=True , null=True)
    profile_image = CloudinaryField('image', blank=True, null=True)
    address =models.TextField(blank=True , null=True)
    city = models.CharField(max_length=100 , blank=True , null=True)
    state = models.CharField(max_length=100 , blank=True , null=True)
    
    country = models.CharField(max_length=100 , blank=True , null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return f"Buyer Profile for {self.user.username}"
    


# Seller Profile Model

class SellerDocs(models.Model):
      id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
      user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="seller_docs")
      CNIC_Front = CloudinaryField('image', blank=True, null=True)
      CNIC_Back = CloudinaryField('image', blank=True, null=True)
      PAN_Card = CloudinaryField('image', blank=True, null=True)

      created_at = models.DateTimeField(auto_now_add=True)
      updated_at = models.DateTimeField(auto_now=True)

class SellerProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="seller_profile")
    stripe_account_id = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=20)
    profile_image = CloudinaryField('image', blank=True, null=True)
    docs = models.OneToOneField(SellerDocs, on_delete=models.CASCADE, blank=True, null=True)
    company_name = models.CharField(max_length=150, blank=True)
    city = models.CharField(max_length=100, blank=True)
    address =models.TextField(blank=True , null=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    license_number = models.CharField(max_length=100, blank=True)
    is_verified_seller = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"SellerProfile - {self.user.username}"



# Property Seller Models

class PropertyType(models.TextChoices):
      HOUSE = "house","House"
      APARTMENT = "apartment","Apartment"
      PLOTS_AND_LAND = "plots_and_land","Plots & Land"
      COMMERCIAL = "commercial","Commercial"


class Property(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="properties")
    property_type = models.CharField(max_length=20, choices=PropertyType.choices, default=PropertyType.HOUSE)
    title = models.CharField(max_length=200)
    location = models.URLField()
    is_available = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    
    STATUSES = (
        ("pending", "Pending"),
        ("active", "Active"),
        ("pause", "Pause"),
        ("reject", "Reject"),
        ("inactive", "Inactive"),
        ("sold", "Sold"),
        ("reserved", "Reserved")
    )  
    status = models.CharField(max_length=20, choices=STATUSES, default="pending")
    
    SALE_TYPE = (
        ("sale","Sale"),
        ("rent","Rent"),
        ("both","Both")
    )
    sale_type = models.CharField(max_length=20, choices=SALE_TYPE, default="sale")
    sale_price = models.DecimalField(max_digits=20, decimal_places=4)
    rent_price = models.DecimalField(max_digits=20, decimal_places=4, blank=True, null=True)
    security_deposit = models.DecimalField(max_digits=20, decimal_places=4, blank=True, null=True)
    hero_image = CloudinaryField('image')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class PropertyImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='images')
    image = CloudinaryField('image', blank=True, null=True)

    def __str__(self):
        return f"Image for {self.property.title}"


class Features(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class House(models.Model):
      id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
      property = models.OneToOneField(Property, on_delete=models.CASCADE,related_name="house")
      bedrooms = models.IntegerField()
      bathrooms = models.IntegerField()
      builtup_area = models.IntegerField()
      year_built= models.IntegerField()
      PARKING= (
          ("2carriage","2 Carriage"),
          ("3carriage","3 Carriage"),
          ("4carriage","4 Carriage"),
          ("5carriage","5 Carriage"),
      )
      parking= models.CharField(max_length=20, choices=PARKING, default="2carriage")
      plot_size = models.IntegerField()
      floors = models.IntegerField()
      features = models.ManyToManyField(Features, blank=True)
      description = models.TextField()
      PROPERTY_SUBTYPE = (
          ("detached","Detached"),
          ("semi-detached","Semi-detached"),
          ("terraced","Terraced"),
      )
      sub_type=models.CharField(max_length=20, choices=PROPERTY_SUBTYPE, default="detached")
      created_at = models.DateTimeField(auto_now_add=True)
      updated_at = models.DateTimeField(auto_now=True)


class Apartment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.OneToOneField(Property, on_delete=models.CASCADE, related_name="apartments")
    bedrooms = models.IntegerField()
    bathrooms = models.IntegerField()
    builtup_area = models.IntegerField()
    FURNISHING = (
        ("furnished", "Furnished"),
        ("unfurnished", "Unfurnished"),
        ("semi-furnished", "Semi-furnished")
    )
    furnishing = models.CharField(max_length=20, choices=FURNISHING, default="furnished")
    OCCUPANT_PREFERENCE = (
        ("WorkingProfessionals", "Working Professionals"),
        ("Students", "Students"),
        ("Family", "Family"),
        ("Others", "Others")
    )
    parking = models.IntegerField()
    has_balcony = models.BooleanField(default=False)
    occupant_preference = models.CharField(max_length=20, choices=OCCUPANT_PREFERENCE, default="WorkingProfessionals")
    features = models.ManyToManyField(Features, blank=True)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class PlotsAndLand(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.OneToOneField(Property, on_delete=models.CASCADE, related_name="plots_and_land")
    PLOT_TYPE = (
        ("residential", "Residential"),
        ("commercial", "Commercial"),
        ("agricultural", "Agricultural"),
        ("industrial", "Industrial"),
        ("other", "Other")
    )
    
    plot_type = models.CharField(max_length=20, choices=PLOT_TYPE, default="residential")

    PERMITTED_USE =(
        ("zoning", "Zoning"),
        ("agricultural", "Agricultural"),
        ("R1", "R1"),
        ("R2", "R2"),
        ("mixed use", "Mixed Use"),
        ("other", "Other")
    )
    permitted_use = models.CharField(max_length=20, choices=PERMITTED_USE, default="zoning")
    ownership= models.CharField(max_length=20)
    area = models.IntegerField()
    frontage = models.CharField(max_length=20)
    depth = models.CharField(max_length=20)
    facing = models.CharField(max_length=20)
    has_corner_plot = models.BooleanField(default=False)
    road_width = models.CharField(max_length=20)
    approval_by = models.CharField(max_length=20)
    POSESSION_STATUS = (
        ("immediate", "Immediate"),
        ("conditional", "Conditional"),
        ("under development", "Under Development")
    )
    possession_status = models.CharField(max_length=20, choices=POSESSION_STATUS, default="immediate")
    features = models.ManyToManyField(Features, blank=True)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    

class Commercial(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.OneToOneField(Property, on_delete=models.CASCADE, related_name="commercial")

    COMMERCIAL_TYPE = (
        ("commercial", "Commercial"),
        ("office", "Office"),
        ("retail", "Retail"),
        ("industrial", "Industrial"),
        ("other", "Other")
    )
    # Mapping of commercial type to allowed subtypes (used for validation & UI)
    COMMERCIAL_SUBTYPE_MAP = {
        "commercial": ["Mixed Use", "Business Center", "Others"],
        "office": ["Corporate Office", "Software Office", "Accounts Office", "Co-working"],
        "retail": ["Shop", "Mall Kiosk", "Showroom"],
        "industrial": ["Factory", "Warehouse", "Manufacturing Unit"],
        "other": ["Other"]
    }

    commercial_type = models.CharField(max_length=20, choices=COMMERCIAL_TYPE, default="commercial")
    # Store subtype as free text but validate it belongs to the selected commercial_type
    commercial_subtype = models.CharField(max_length=100, blank=True, null=True)
    ownership = models.CharField(max_length=20)
    builtup_area = models.IntegerField()
    useable_area = models.CharField(max_length=20)
    floor_number = models.CharField(max_length=20)
    frontage = models.CharField(max_length=20)
    washrooms = models.IntegerField()
    has_kitchen = models.BooleanField(default=False)
    FURNISHING = (
        ("furnished", "Furnished"),
        ("unfurnished", "Unfurnished"),
        ("semi-furnished", "Semi-furnished")
    )
    furnishing = models.CharField(max_length=20, choices=FURNISHING, default="furnished")
    parking_details = models.CharField(max_length=20)
    BUILDING_GRADE = (
        ("A", "A"),
        ("B", "B"),
        ("C", "C"),
        ("D", "D"),)
    building_grade = models.CharField(max_length=20, choices=BUILDING_GRADE, default="A")
    features = models.ManyToManyField(Features, blank=True)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        """Ensure the chosen subtype (if any) is valid for the selected commercial_type."""
        subtype = self.commercial_subtype
        ctype = self.commercial_type
        if subtype:
            valid = self.COMMERCIAL_SUBTYPE_MAP.get(ctype, [])
            if subtype not in valid:
                raise ValidationError({"commercial_subtype": "Invalid subtype for selected commercial type."})

    def save(self, *args, **kwargs):
        # Run validation before saving; caller can skip by using force_insert/force_update directly
        self.full_clean()
        return super().save(*args, **kwargs)




# Chat Models

class ChatSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    """
    Represents a chat conversation between a buyer and a seller about a specific property.
    """
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="chat_sessions")
    buyer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="chat_sessions_as_buyer")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('property', 'buyer')
        ordering = ['-updated_at']

    def __str__(self):
        return f"Chat for '{self.property.title}' between {self.buyer.username} and {self.property.user.username}"


class ChatMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    """
    Represents a single message within a ChatSession.
    """
    chat_session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="sent_messages")
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"Message from {self.sender.username} at {self.timestamp}"




# Appointment Models

class SellerAvailability(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    """
    Stores a seller's recurring weekly availability for specific property.
    """
    seller = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="availabilities")
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="availabilities")
    
    # Stores list of integers representing days (0=Monday, 6=Sunday)
    days_of_week = models.JSONField(default=list)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ['seller', 'start_time']

    def __str__(self):
       return f"Availability for {self.property.title} on days {self.days_of_week} from {self.start_time} to {self.end_time}"
 

class Appointment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    """
    Represents an appointment scheduled by a buyer with a seller for a specific property.
    """
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("cancelled", "Cancelled"),
        ("completed", "Completed"),
    ]

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="appointments")
    buyer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="appointments_as_buyer")
    # The seller is implicitly available via the property's user (property.user)
    # but adding a direct foreign key can make queries easier.
    seller = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="appointments_as_seller")

    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['start_time']

    def __str__(self):
        return f"Appointment for {self.property.title} with {self.buyer.username} at {self.start_time}"

    def clean(self):
        # Ensure end_time is after start_time
        if self.start_time >= self.end_time:
            raise ValidationError("End time must be after start time.")
        
        # Add more complex validation here if needed, for example, checking for overlapping appointments for the same seller.
        # This is often better handled in the View/Serializer level during creation to provide immediate feedback to the user.

# Payment & Transaction Models

class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    buyer = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name="payments_made")
    seller = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name="payments_received")
    property = models.ForeignKey(Property, on_delete=models.SET_NULL, null=True, related_name="payments")
    
    stripe_charge_id = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=20, decimal_places=4)

    PAYMENT_TYPE_CHOICES = [
        ('sale', 'Property Sale'),
        ('rent', 'Monthly Rent'),
        ('security_deposit', 'Security Deposit'),
    ]
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES)

    STATUS_CHOICES = [
        ('succeeded', 'Succeeded'),
        ('pending', 'Pending'),
        ('failed', 'Failed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.id} for {self.property.title} by {self.buyer.username}"

class Receipt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name="receipt")
    # Using a URLField assuming receipts are stored in a cloud storage and accessed via URL.
    receipt_url = models.URLField(max_length=500)
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Receipt for Payment {self.payment.id}"

class RentalAgreement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.OneToOneField(Property, on_delete=models.CASCADE, related_name="rental_agreement")
    buyer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="rental_agreements")
    
    start_date = models.DateField()
    end_date = models.DateField()
    monthly_rent_amount = models.DecimalField(max_digits=20, decimal_places=4)
    security_deposit_amount = models.DecimalField(max_digits=20, decimal_places=4)
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('ended', 'Ended'),
        ('defaulted', 'Defaulted'), # If buyer misses payments
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Rental Agreement for {self.property.title}"

    def clean(self):
        if self.end_date <= self.start_date:
            raise ValidationError("End date must be after start date.")

class MonthlyRentPayment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rental_agreement = models.ForeignKey(RentalAgreement, on_delete=models.CASCADE, related_name="monthly_payments")
    payment = models.OneToOneField(Payment, on_delete=models.SET_NULL, null=True, blank=True, related_name="rent_payment_record")
    
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=20, decimal_places=4)
    
    STATUS_CHOICES = [
        ('pending', 'Pending'), # As requested by user
        ('paid', 'Paid'),
        ('late', 'Late'),
        ('waived', 'Waived'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    date_paid = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Rent for {self.rental_agreement.property.title} due on {self.due_date}"
    
    

    #     PROCESS OF RENTING 
# means when buyer selects the renting then first it will decide how long will stay minimum i will say 6 months atleast then pay then automatically set due date of all months and show to buyer means it can see selected months due date of all and status of fee of that month fee pending or done and on by cicking user can pay rent on by clicking and in advance also and we will change status is this approach correct ? if yes then set the models of renting like this