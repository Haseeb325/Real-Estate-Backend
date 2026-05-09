from requests import Response
from rest_framework import serializers
from .models import *
import cloudinary.exceptions
import json


class UserRegisterationStep1Serializer(serializers.ModelSerializer):
    """
    Serializer for the first step of registration.
    Validates email, username, and full_name, checking for uniqueness.
    """
    class Meta:
        model = CustomUser
        fields = ('email', 'username', 'full_name')
        extra_kwargs = {
            'email': {'required': True},
            'username': {'required': True},
            'full_name': {'required': True},
        }

# User and Profile Serializers

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for the CustomUser model.
    Used to display user details within other serializers.
    """
    class Meta:
        model = CustomUser
        fields = ('id', 'email', 'username', 'full_name', 'role', 'is_email_verified', 'status', 'is_active')

class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for password change endpoint.
    """
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)
    confirm_new_password = serializers.CharField(required=True, write_only=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Your old password was entered incorrectly. Please enter it again.")
        return value

    def validate(self, data):
        if data['new_password'] != data['confirm_new_password']:
            raise serializers.ValidationError({"new_password": "The two password fields didn't match."})
        # You could add more password strength validation here if desired
        return data

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user

# ...existing code...

class SellerDocsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SellerDocs
        fields = ['id', 'CNIC_Front', 'CNIC_Back','PAN_Card']  # Exclude 'user'
        
        
    # def create(self, validated_data):
    #     # Get user from request context
    #     user = self.context['request'].user
    #     return SellerDocs.objects.create(user=user, **validated_data)
class BuyerProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for the BuyerProfile model. The user field is read-only
    as it should not be changed once the profile is created.
    """
    user = UserSerializer(read_only=True)

    class Meta:
        model = BuyerProfile
        fields = '__all__'


class SellerProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for the SellerProfile model.
    Includes a nested serializer for seller documents.
    Fields like user, verification status, and stripe ID are read-only.
    """
    user = UserSerializer(read_only=True)
    docs = SellerDocsSerializer(read_only=True) # Nested serializer for retrieving docs

    class Meta:
        model = SellerProfile
        fields = '__all__'
        read_only_fields = ['docs', 'verification_status', 'is_verified_seller']


class PropertyImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyImage
        fields = ('id', 'image')


class FeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Features
        fields = ('id', 'name')


class HouseSerializer(serializers.ModelSerializer):
    features = FeatureSerializer(many=True, read_only=True)

    class Meta:
        model = House
        exclude = ('property',)


class ApartmentSerializer(serializers.ModelSerializer):
    features = FeatureSerializer(many=True, read_only=True)

    class Meta:
        model = Apartment
        exclude = ('property',)


class PlotsAndLandSerializer(serializers.ModelSerializer):
    features = FeatureSerializer(many=True, read_only=True)

    class Meta:
        model = PlotsAndLand
        exclude = ('property',)


class CommercialSerializer(serializers.ModelSerializer):
    features = FeatureSerializer(many=True, read_only=True)

    class Meta:
        model = Commercial
        exclude = ('property',)


class PropertyListSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = Property
        fields = ('id', 'title', 'property_type', 'sale_type', 'sale_price', 'rent_price', 'location', 'location_text', 'hero_image', 'user', 'status', 'is_verified')


class PropertyDetailSerializer(serializers.ModelSerializer):
    images = PropertyImageSerializer(many=True, read_only=True)
    user = UserSerializer(read_only=True)
    house = HouseSerializer(read_only=True)
    # Note: The model's related_name for the apartment OneToOneField is 'apartments'.
    # Using 'source' to correctly map it.
    apartment = ApartmentSerializer(read_only=True, source='apartments')
    plots_and_land = PlotsAndLandSerializer(read_only=True)
    commercial = CommercialSerializer(read_only=True)

    class Meta:
        model = Property
        fields = '__all__'


# --- Create/Update Serializers ---

# Custom field to handle feature serialization for both input and output
class FeatureListField(serializers.ListField):
    def to_internal_value(self, data):
        # Handle comma-separated string from form-data or single-item lists
        if isinstance(data, str):
            return [item.strip() for item in data.split(',') if item.strip()]
        if isinstance(data, list) and len(data) == 1 and isinstance(data[0], str) and ',' in data[0]:
            return [item.strip() for item in data[0].split(',') if item.strip()]
        return super().to_internal_value(data)

    def to_representation(self, data):
        # On output (to_representation), data is a ManyRelatedManager.
        # We need to query it to get the actual Feature objects.
        return [feature.name for feature in data.all()]


class HouseCreateUpdateSerializer(serializers.ModelSerializer):
    features = FeatureListField(child=serializers.CharField(max_length=100), required=False, allow_empty=True)

    class Meta:
        model = House
        exclude = ('property', 'id')

class ApartmentCreateUpdateSerializer(serializers.ModelSerializer):
    features = FeatureListField(child=serializers.CharField(max_length=100), required=False, allow_empty=True)

    class Meta:
        model = Apartment
        exclude = ('property', 'id')

class PlotsAndLandCreateUpdateSerializer(serializers.ModelSerializer):
    features = FeatureListField(child=serializers.CharField(max_length=100), required=False, allow_empty=True)

    class Meta:
        model = PlotsAndLand
        exclude = ('property', 'id')

class CommercialCreateUpdateSerializer(serializers.ModelSerializer):
    features = FeatureListField(child=serializers.CharField(max_length=100), required=False, allow_empty=True)

    class Meta:
        model = Commercial
        exclude = ('property', 'id')



class PropertyCreateUpdateSerializer(serializers.ModelSerializer):
    house = HouseCreateUpdateSerializer(required=False, allow_null=True)
    apartment = ApartmentCreateUpdateSerializer(required=False, allow_null=True)
    plots_and_land = PlotsAndLandCreateUpdateSerializer(required=False, allow_null=True)
    commercial = CommercialCreateUpdateSerializer(required=False, allow_null=True)
    # This field will accept a list of uploaded image files.
    images = serializers.ListField(
        child=serializers.ImageField(), required=False, write_only=True
    )
    
    class Meta:
        model = Property
        fields = (
            'id', 'property_type', 'title', 'location', 'location_text', 'is_available', 'status',
            'sale_type', 'sale_price', 'rent_price', 'security_deposit', 'hero_image',
            'house', 'apartment', 'plots_and_land', 'commercial',
            'images'  # Add images field here
        )
        read_only_fields = ('id',)

    def to_internal_value(self, data):
        # Use a plain dictionary to avoid QueryDict's list-wrapping behavior.
        # QueryDict (from form-data) wraps every value in a list, which breaks 
        # nested serializers when we try to group flat keys into a dictionary.
        if hasattr(data, 'dict'):
            processed_data = data.dict()
            # Explicitly restore the list for 'images' since it's a valid list of files
            if 'images' in data:
                processed_data['images'] = data.getlist('images')
        else:
            processed_data = dict(data)

        # Handle nested objects sent as flat keys (e.g. apartment[bedrooms] or apartment.bedrooms)
        # This is essential for MultiPartParser (image uploads) which doesn't support nested JSON.
        nested_fields = ['house', 'apartment', 'plots_and_land', 'commercial']
        
        for field in nested_fields:
            # Case 1: Field is sent as a JSON string (e.g. apartment: '{"bedrooms": 3}')
            if field in processed_data and isinstance(processed_data[field], str):
                try:
                    processed_data[field] = json.loads(processed_data[field])
                except (ValueError, TypeError):
                    pass

            # Case 2: Field is sent as flat keys (e.g. apartment[bedrooms]: 3)
            if not isinstance(processed_data.get(field), dict):
                nested_dict = {}
                keys_to_remove = []
                for key in list(processed_data.keys()):
                    for prefix in [f"{field}.", f"{field}["]:
                        if key.startswith(prefix):
                            inner_key = key[len(prefix):].rstrip(']')
                            
                            # If the user sent features as multiple fields, get the list from original data
                            if inner_key == 'features' and hasattr(data, 'getlist'):
                                val = data.getlist(key)
                            else:
                                val = processed_data[key]

                            nested_dict[inner_key] = val
                            keys_to_remove.append(key)
                
                if nested_dict:
                    processed_data[field] = nested_dict
                    for key in keys_to_remove:
                        processed_data.pop(key, None)

        return super().to_internal_value(processed_data)

    def validate(self, data):
        # Determine the property type (from input or existing instance)
        property_type = data.get('property_type')
        if not property_type and self.instance:
            property_type = self.instance.property_type

        # Map property types to their respective fields and serializers
        type_map = {
            'house': ('house', HouseCreateUpdateSerializer),
            'apartment': ('apartment', ApartmentCreateUpdateSerializer),
            'plots_and_land': ('plots_and_land', PlotsAndLandCreateUpdateSerializer),
            'commercial': ('commercial', CommercialCreateUpdateSerializer)
        }

        # ONLY enforce detailed validation for missing blocks during creation (POST)
        if not self.instance and property_type in type_map:
            field_name, serializer_class = type_map[property_type]
            
            if not data.get(field_name):
                # Trigger validation on an empty dict to get detailed "field is required" errors
                sub_serializer = serializer_class(data={}, context=self.context)
                sub_serializer.is_valid()
                raise serializers.ValidationError({
                    field_name: sub_serializer.errors
                })

        return data

    def _handle_features(self, sub_property, feature_names):
        """Helper function to get or create feature objects and set them."""
        if feature_names:
            feature_objects = []
            for name in feature_names:
                feature, _ = Features.objects.get_or_create(name=name.strip())
                feature_objects.append(feature)
            sub_property.features.set(feature_objects)
        else: # If an empty list is passed, clear existing features
            sub_property.features.clear()


    def create(self, validated_data):
        house_data = validated_data.pop('house', None)
        apartment_data = validated_data.pop('apartment', None)
        plots_and_land_data = validated_data.pop('plots_and_land', None)
        commercial_data = validated_data.pop('commercial', None)
        # Pop the image list from the validated data
        image_data = validated_data.pop('images', [])

        # Set the user from the request context
        validated_data['user'] = self.context['request'].user
        
        property_instance = Property.objects.create(**validated_data)

        # After creating the property, create the associated PropertyImage objects
        try:
            for image_file in image_data:
                PropertyImage.objects.create(property=property_instance, image=image_file)
        except Exception as e:
            # If an upload fails, delete the property that was just created to be safe
            property_instance.delete()
            # Check if it's a known cloudinary error and raise a user-friendly validation error
            if isinstance(e, cloudinary.exceptions.Error):
                raise serializers.ValidationError({
                    "images": "Image upload failed: Could not connect to the image storage service. Please try again."
                })
            # Re-raise any other unexpected errors
            raise e

        property_type = property_instance.property_type

        if property_type == 'house' and house_data:
            feature_names = house_data.pop('features', [])
            house = House.objects.create(property=property_instance, **house_data)
            self._handle_features(house, feature_names)
        elif property_type == 'apartment' and apartment_data:
            feature_names = apartment_data.pop('features', [])
            apartment = Apartment.objects.create(property=property_instance, **apartment_data)
            self._handle_features(apartment, feature_names)
        elif property_type == 'plots_and_land' and plots_and_land_data:
            feature_names = plots_and_land_data.pop('features', [])
            plot = PlotsAndLand.objects.create(property=property_instance, **plots_and_land_data)
            self._handle_features(plot, feature_names)
        elif property_type == 'commercial' and commercial_data:
            feature_names = commercial_data.pop('features', [])
            commercial = Commercial.objects.create(property=property_instance, **commercial_data)
            self._handle_features(commercial, feature_names)

        return property_instance
    
    def update(self, instance, validated_data):
        house_data = validated_data.pop('house', None)
        apartment_data = validated_data.pop('apartment', None)
        plots_and_land_data = validated_data.pop('plots_and_land', None)
        commercial_data = validated_data.pop('commercial', None)
        image_data = validated_data.pop('images', None)

        # Handle image updates
        if image_data is not None:
            # Clear existing images before adding new ones
            instance.images.all().delete()
            try:
                for image_file in image_data:
                    PropertyImage.objects.create(property=instance, image=image_file)
            except cloudinary.exceptions.Error as e:
                raise serializers.ValidationError({
                    "images": f"Image upload failed. Please try again. Error: {str(e)}"
                })

        instance = super().update(instance, validated_data)

        property_type = instance.property_type
        
        # This update logic assumes the property_type does not change.
        
        if property_type == 'house' and house_data:
            if hasattr(instance, 'house'):
                feature_names = house_data.pop('features', None)
                for key, value in house_data.items():
                    setattr(instance.house, key, value)
                instance.house.save()
                if feature_names is not None:
                    self._handle_features(instance.house, feature_names)

        elif property_type == 'apartment' and apartment_data:
            if hasattr(instance, 'apartments'):
                feature_names = apartment_data.pop('features', None)
                for key, value in apartment_data.items():
                    setattr(instance.apartments, key, value)
                instance.apartments.save()
                if feature_names is not None:
                    self._handle_features(instance.apartments, feature_names)

        elif property_type == 'plots_and_land' and plots_and_land_data:
            if hasattr(instance, 'plots_and_land'):
                feature_names = plots_and_land_data.pop('features', None)
                for key, value in plots_and_land_data.items():
                    setattr(instance.plots_and_land, key, value)
                instance.plots_and_land.save()
                if feature_names is not None:
                    self._handle_features(instance.plots_and_land, feature_names)

        elif property_type == 'commercial' and commercial_data:
            if hasattr(instance, 'commercial'):
                feature_names = commercial_data.pop('features', None)
                for key, value in commercial_data.items():
                    setattr(instance.commercial, key, value)
                instance.commercial.save()
                if feature_names is not None:
                    self._handle_features(instance.commercial, feature_names)

        return instance


# --- Chat Serializers ---

class ChatMessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.ReadOnlyField(source='sender.username')

    class Meta:
        model = ChatMessage
        fields = ['id', 'sender_username', 'content', 'timestamp']


class ChatSessionSerializer(serializers.ModelSerializer):
    buyer = serializers.ReadOnlyField(source='buyer.username')
    seller = serializers.ReadOnlyField(source='property.user.username')
    property_title = serializers.ReadOnlyField(source='property.title')

    class Meta:
        model = ChatSession
        fields = [
            'id', 
            'property', 
            'property_title', 
            'buyer', 
            'seller', 
            'created_at', 
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'property_title', 'buyer', 'seller']


# --- Appointment Serializers ---

class SellerAvailabilitySerializer(serializers.ModelSerializer):
    """
    Serializer for the SellerAvailability model.
    Handles validation to ensure end_time is after start_time.
    """
    seller = serializers.ReadOnlyField(source='seller.username')
    days_of_week = serializers.ListField(
        child=serializers.IntegerField(min_value=0, max_value=6),
        required=True,
        write_only=True,
        help_text="List of days (0=Monday, 6=Sunday)."
    )

    class Meta:
        model = SellerAvailability
        fields = ['id', 'seller', 'property', 'days_of_week', 'start_time', 'end_time']
        read_only_fields = ['id', 'seller']

    def validate(self, data):
        """
        Check that the start_time is before the end_time.
        """
        start = data.get('start_time')
        end = data.get('end_time')
        days = data.get('days_of_week')
        property_obj = data.get('property')
        
        day_mapping = {
            0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday",
            4: "Friday", 5: "Saturday", 6: "Sunday"
        }

        # Handle partial updates where one field might be missing
        if self.instance:
            start = start or self.instance.start_time
            end = end or self.instance.end_time
            days = days if days is not None else self.instance.days_of_week
            property_obj = property_obj or self.instance.property

        if start and end and start >= end:
            raise serializers.ValidationError({"time_error": "End time must be after start time."})
        
        # Check for overlaps with existing availability
        user = self.context['request'].user
        
        # Query existing availabilities for this property
        queryset = SellerAvailability.objects.filter(seller=user, property=property_obj)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        for availability in queryset:
            # Check time overlap
            if start < availability.end_time and end > availability.start_time:
                # Check day overlap
                existing_days = set(availability.days_of_week)
                
                # Normalize current request days to strings for comparison
                new_days_strings = set()
                if days:
                    for d in days:
                        if isinstance(d, int):
                            new_days_strings.add(day_mapping[d])
                        else:
                            new_days_strings.add(d)

                if existing_days.intersection(new_days_strings):
                    overlapping = sorted(list(existing_days.intersection(new_days_strings)))
                    raise serializers.ValidationError(f"Availability overlaps on {', '.join(overlapping)} with existing slot {availability.start_time}-{availability.end_time}.")
        
        # Convert integers to strings for storage
        if 'days_of_week' in data:
            data['days_of_week'] = [day_mapping[d] for d in data['days_of_week']]
            
        return data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['days_of_week'] = instance.days_of_week
        return data


class AppointmentSerializer(serializers.ModelSerializer):
    property_details = PropertyListSerializer(source='property', read_only=True)
    buyer_details = UserSerializer(source='buyer', read_only=True)
    seller_details = UserSerializer(source='seller', read_only=True)

    buyer_name = serializers.ReadOnlyField(source='buyer.username')
    seller_name = serializers.ReadOnlyField(source='seller.username')
    property_title = serializers.ReadOnlyField(source='property.title')

    # Add this to help frontend show/hide buttons easily
    available_actions = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            'id', 
            'property', 'property_details', 'property_title',
            'buyer', 'buyer_details', 'buyer_name',
            'seller', 'seller_details', 'seller_name',
            'start_time', 'end_time', 'status', 'notes',
            'available_actions'
        ]
        read_only_fields = [
            'id', 'status', 'buyer', 'seller', 'property_title',
            'property_details', 'buyer_details', 'seller_details'
        ]

    def get_available_actions(self, obj):
        """
        Returns which actions the CURRENT user can perform on this appointment.
        """
        user = self.context['request'].user
        actions = []
        
        # Cancellation logic (Both can cancel unless completed/already cancelled)
        if obj.status not in ['completed', 'cancelled']:
            if user == obj.buyer or user == obj.seller:
                actions.append('cancel')

        # Confirmation logic (Only seller can confirm pending)
        if obj.status == 'pending' and user == obj.seller:
            actions.append('confirm')

        # Completion logic (Both can complete confirmed)
        if obj.status == 'confirmed':
            if user == obj.buyer or user == obj.seller:
                actions.append('complete')
                
        return actions


# --- Payment & Rental Serializers ---

class PaymentSerializer(serializers.ModelSerializer):
    buyer = serializers.ReadOnlyField(source='buyer.username')
    seller = serializers.ReadOnlyField(source='seller.username')
    property_title = serializers.ReadOnlyField(source='property.title')

    class Meta:
        model = Payment
        fields = ['id', 'stripe_charge_id', 'amount', 'payment_type', 'status', 'timestamp', 'buyer', 'seller', 'property', 'property_title']
        read_only_fields = ['id', 'stripe_charge_id', 'status', 'timestamp', 'buyer', 'seller', 'property_title']

class MonthlyRentPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonthlyRentPayment
        fields = ['id', 'due_date', 'amount', 'status', 'date_paid']

class RentalAgreementSerializer(serializers.ModelSerializer):
    buyer = serializers.ReadOnlyField(source='buyer.username')
    property_title = serializers.ReadOnlyField(source='property.title')
    monthly_payments = MonthlyRentPaymentSerializer(many=True, read_only=True)

    class Meta:
        model = RentalAgreement
        fields = ['id', 'property', 'property_title', 'buyer', 'start_date', 'end_date', 'monthly_rent_amount', 'security_deposit_amount', 'status', 'created_at', 'monthly_payments']
        read_only_fields = ['id', 'buyer', 'status', 'created_at', 'monthly_payments']