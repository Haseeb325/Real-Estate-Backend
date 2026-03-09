from django.db.models import Q
from rest_framework import viewsets, permissions, serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied

from ..models import SellerAvailability, Property, Appointment
from ..serializers import SellerAvailabilitySerializer, AppointmentSerializer
from ..permissions import IsSeller, IsBuyer


class SellerAvailabilityViewSet(viewsets.ModelViewSet):
    """
    ViewSet for sellers to manage their availability for properties.
    - A seller can create, view, update, and delete their availability.
    - They can only manage availability for properties they own.
    """
    serializer_class = SellerAvailabilitySerializer
    permission_classes = [permissions.IsAuthenticated, IsSeller]

    def get_queryset(self):
        """
        This view should only return the availability for the currently authenticated seller.
        """
        return SellerAvailability.objects.filter(seller=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Validate property ownership
        property_instance = serializer.validated_data.get('property')
        if property_instance.user != self.request.user:
            raise PermissionDenied("You do not have permission to set availability for this property.")
        
        # Save and capture the instance(s)
        serializer.save(seller=self.request.user)
        headers = self.get_success_headers(serializer.data)
        return Response({
            'message': 'Availability slot created successfully.',
            'availability': serializer.data
        }, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        response_data = {
            'message': 'Availability slot updated successfully.',
            'availability': serializer.data
        }
        return Response(response_data)

    def perform_update(self, serializer):
        """
        Ensure the seller can only update availability for their own property.
        """
        if 'property' in serializer.validated_data:
            property_instance = serializer.validated_data.get('property')
            if property_instance.user != self.request.user:
                raise PermissionDenied("You do not have permission to change availability to this property.")

        serializer.save()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {'message': 'Availability slot deleted successfully.'},
            status=status.HTTP_200_OK
        )


class AppointmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for handling appointments.
    - Buyers can create (book) appointments.
    - Sellers can confirm/cancel appointments.
    - Users can view their own appointments.
    """
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Users should see appointments where they are either the buyer or the seller.
        """
        user = self.request.user
        if not user.is_authenticated:
            return Appointment.objects.none()
        return Appointment.objects.filter(Q(buyer=user) | Q(seller=user))

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        property_instance = serializer.validated_data.get('property')
        buyer = request.user
        
        # Check if an appointment already exists for this buyer and property
        # We exclude 'completed' appointments to preserve history of past successful visits
        existing_appointment = Appointment.objects.filter(
            buyer=buyer, 
            property=property_instance
        ).exclude(status='completed').order_by('-created_at').first()

        if existing_appointment:
            # Update existing appointment
            serializer = self.get_serializer(existing_appointment, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response({
                'message': 'Appointment request updated successfully. Waiting for seller confirmation.',
                'appointment': serializer.data
            }, status=status.HTTP_200_OK)
        else:
            # Create new appointment
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response({
                'message': 'Appointment request sent successfully. Waiting for seller confirmation.',
                'appointment': serializer.data
            }, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        """
        Allows a BUYER to book an appointment.
        """
        property_instance = serializer.validated_data.get('property')
        start_time = serializer.validated_data.get('start_time')
        end_time = serializer.validated_data.get('end_time')

        # Prevent booking with yourself
        if property_instance.user == self.request.user:
            raise serializers.ValidationError("You cannot book an appointment for your own property.")

        # Check for overlapping appointments for the same property
        queryset = Appointment.objects.filter(
            property=property_instance,
            start_time__lt=end_time,
            end_time__gt=start_time,
            status__in=['pending', 'confirmed']
        )

        # If updating an existing appointment, exclude it from the overlap check
        if serializer.instance:
            queryset = queryset.exclude(pk=serializer.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError("This time slot is no longer available.")

        # TODO: Check if the time slot fits within the seller's defined availability.
        
        seller = property_instance.user
        serializer.save(buyer=self.request.user, seller=seller, status='pending')

    def get_permissions(self):
        """
        - 'create' action requires IsBuyer.
        - Other actions just require authentication.
        """
        if self.action == 'create':
            self.permission_classes = [permissions.IsAuthenticated, IsBuyer]
        return super().get_permissions()

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """
        Allows a SELLER to confirm an appointment.
        """
        appointment = self.get_object()

        # Only the seller can confirm the appointment
        if request.user != appointment.seller:
            raise PermissionDenied("Only the seller can confirm this appointment.")

        if appointment.status != 'pending':
            return Response(
                {'error': f'This appointment cannot be confirmed because its status is "{appointment.status}".'},
                status=status.HTTP_400_BAD_REQUEST
            )

        appointment.status = 'confirmed'
        appointment.save()
        return Response({
            'message': 'Appointment confirmed successfully.',
            'appointment': AppointmentSerializer(appointment).data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Allows a buyer or seller to cancel an appointment.
        """
        appointment = self.get_object()

        # Check if the user is the buyer or the seller for this appointment
        if request.user != appointment.buyer and request.user != appointment.seller:
            raise PermissionDenied("You do not have permission to cancel this appointment.")

        if appointment.status in ['completed', 'cancelled']:
            return Response({'error': 'This appointment cannot be cancelled.'}, status=status.HTTP_400_BAD_REQUEST)

        appointment.status = 'cancelled'
        appointment.save()
        return Response({
            'message': 'Appointment cancelled successfully.',
            'appointment': AppointmentSerializer(appointment).data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """
        Allows a buyer or seller to mark an appointment as completed.
        """
        appointment = self.get_object()

        # Only the buyer or seller can complete the appointment
        if request.user != appointment.buyer and request.user != appointment.seller:
            raise PermissionDenied("You do not have permission to complete this appointment.")

        # An appointment should be 'confirmed' before it can be 'completed'
        if appointment.status != 'confirmed':
            return Response(
                {'error': f'This appointment cannot be completed because its status is "{appointment.status}". It must be confirmed first.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        appointment.status = 'completed'
        appointment.save()
        return Response({
            'message': 'Congratulations on completing the appointment!',
            'appointment': AppointmentSerializer(appointment).data
        }, status=status.HTTP_200_OK)
