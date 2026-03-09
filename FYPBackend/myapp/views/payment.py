from rest_framework import viewsets, permissions, status, views
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Q
from ..models import Property, Payment, RentalAgreement, MonthlyRentPayment
from ..serializers import PaymentSerializer, RentalAgreementSerializer
import uuid
import datetime

class MockPaymentView(views.APIView):
    """
    Simulates a payment gateway.
    Accepts payment details, creates a fake transaction, and executes business logic
    (e.g., creating rental agreements, marking rent as paid, or selling a property).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        payment_type = request.data.get('payment_type')
        property_id = request.data.get('property_id')
        
        if not payment_type or not property_id:
            return Response({"error": "payment_type and property_id are required"}, status=status.HTTP_400_BAD_REQUEST)
            
        property_instance = get_object_or_404(Property, id=property_id)
        
        # Check availability only for new transactions (sale or initial rent)
        # Monthly rent is paid on properties that are already 'reserved' (unavailable)
        if payment_type != 'monthly_rent' and not property_instance.is_available:
            return Response({"error": "This property is no longer available."}, status=status.HTTP_400_BAD_REQUEST)

        buyer = request.user
        seller = property_instance.user
        
        # Generate a fake Stripe Charge ID
        mock_charge_id = f"ch_mock_{uuid.uuid4().hex[:16]}"
        
        try:
            with transaction.atomic():
                if payment_type == 'initial_rent':
                    return self._handle_initial_rent(request, property_instance, buyer, seller, mock_charge_id)
                elif payment_type == 'monthly_rent':
                    return self._handle_monthly_rent(request, property_instance, buyer, seller, mock_charge_id)
                elif payment_type == 'sale':
                    return self._handle_sale(request, property_instance, buyer, seller, mock_charge_id)
                else:
                    return Response({"error": "Invalid payment_type"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def _handle_initial_rent(self, request, property_instance, buyer, seller, charge_id):
        """
        Handles the first payment to start a rental.
        Creates RentalAgreement and generates MonthlyRentPayment records.
        """
        if property_instance.sale_type not in ['rent', 'both']:
            raise ValueError("This property is not listed for rent.")

        if not property_instance.rent_price or property_instance.rent_price <= 0:
            raise ValueError("This property cannot be rented as it has no monthly rent price set.")

        months = int(request.data.get('months', 6))
        start_date_str = request.data.get('start_date')
        
        if not start_date_str:
            raise ValueError("start_date is required for renting")
            
        start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = self._add_months(start_date, months)
        
        rent_amount = property_instance.rent_price or 0
        security_deposit = property_instance.security_deposit or 0
        
        # Total paid now: Security Deposit + 1st Month Rent
        total_amount = rent_amount + security_deposit
        
        # 1. Record the Payment
        payment = Payment.objects.create(
            buyer=buyer,
            seller=seller,
            property=property_instance,
            stripe_charge_id=charge_id,
            amount=total_amount,
            payment_type='security_deposit',
            status='succeeded'
        )
        
        # 2. Create the Agreement
        agreement = RentalAgreement.objects.create(
            property=property_instance,
            buyer=buyer,
            start_date=start_date,
            end_date=end_date,
            monthly_rent_amount=rent_amount,
            security_deposit_amount=security_deposit,
            status='active'
        )
        
        # 3. Generate Schedule for all months
        for i in range(months):
            due_date = self._add_months(start_date, i)
            
            rent_payment = MonthlyRentPayment.objects.create(
                rental_agreement=agreement,
                due_date=due_date,
                amount=rent_amount,
                status='pending'
            )
            
            # Mark the 1st month as PAID immediately
            if i == 0:
                rent_payment.status = 'paid'
                rent_payment.date_paid = datetime.date.today()
                rent_payment.payment = payment
                rent_payment.save()
                
        # 4. Update Property Status
        property_instance.status = 'reserved' 
        property_instance.is_available = False
        property_instance.save()

        return Response({
            "message": "Rental agreement created successfully!",
            "agreement_id": agreement.id,
            "amount_paid": total_amount,
            "payment_id": payment.id
        })

    def _handle_monthly_rent(self, request, property_instance, buyer, seller, charge_id):
        monthly_payment_id = request.data.get('monthly_payment_id')
        if not monthly_payment_id:
            raise ValueError("monthly_payment_id is required")
            
        rent_record = get_object_or_404(MonthlyRentPayment, id=monthly_payment_id)
        
        if rent_record.status == 'paid':
             raise ValueError("This month is already paid")

        payment = Payment.objects.create(
            buyer=buyer,
            seller=seller,
            property=property_instance,
            stripe_charge_id=charge_id,
            amount=rent_record.amount,
            payment_type='rent',
            status='succeeded'
        )
        
        rent_record.status = 'paid'
        rent_record.date_paid = datetime.date.today()
        rent_record.payment = payment
        rent_record.save()
        
        return Response({
            "message": "Rent paid successfully",
            "amount_paid": rent_record.amount,
            "payment_id": payment.id
        })

    def _handle_sale(self, request, property_instance, buyer, seller, charge_id):
        if property_instance.sale_type not in ['sale', 'both']:
            raise ValueError("This property is not listed for sale.")

        payment = Payment.objects.create(
            buyer=buyer,
            seller=seller,
            property=property_instance,
            stripe_charge_id=charge_id,
            amount=property_instance.sale_price,
            payment_type='sale',
            status='succeeded'
        )
        
        property_instance.status = 'sold'
        property_instance.is_available = False
        property_instance.save()
        
        return Response({
            "message": "Property purchased successfully",
            "amount_paid": property_instance.sale_price,
            "payment_id": payment.id
        })

    def _add_months(self, source_date, months):
        month = source_date.month - 1 + months
        year = source_date.year + month // 12
        month = month % 12 + 1
        day = min(source_date.day, [31,
            29 if year % 4 == 0 and not year % 100 == 0 or year % 400 == 0 else 28,
            31, 30, 31, 30, 31, 31, 30, 31, 30, 31, 30, 31][month-1])
        return datetime.date(year, month, day)

class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet to retrieve payment history (Sales, Rent, Security Deposits).
    Allows users to view payments they have made (as buyer) or received (as seller).
    """
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Payment.objects.filter(Q(buyer=user) | Q(seller=user)).order_by('-timestamp')

class RentalAgreementViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RentalAgreementSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'buyer':
            return RentalAgreement.objects.filter(buyer=user)
        elif user.role == 'seller':
            return RentalAgreement.objects.filter(property__user=user)
        return RentalAgreement.objects.none()


















# Body:
# json
#  Show full code block 
# {
#     "payment_type": "initial_rent",
#     "property_id": "PROPERTY_UUID",
#     "start_date": "2024-02-01",
#     "months": 12
# }
# Result:
# Creates a RentalAgreement.
# Marks the property as reserved.
# Generates 12 MonthlyRentPayment records.
# Marks Month 1 as paid.
# Step 3: Get Rental Agreement Details (Buyer)
# Now the buyer needs to see their payment schedule to pay for the 2nd Month.

# Endpoint: GET /api/rental-agreements/

# Auth: Buyer Token

# Response Analysis: Look for the monthly_payments array inside the response.

# Find the entry where status is "pending" (usually the second item in the list).
# Copy its id (e.g., MONTHLY_PAYMENT_UUID).
# json
#  Show full code block 
# {
#     "id": "...",
#     "property_title": "Luxury Apartment for Rent",
#     "monthly_payments": [
#         {
#             "id": "...",
#             "due_date": "2024-02-01",
#             "status": "paid"  <-- 1st month is already paid
#         },
#         {
#             "id": "MONTHLY_PAYMENT_UUID", <-- COPY THIS ID
#             "due_date": "2024-03-01",
#             "status": "pending"
#         }
#     ]
# }
# Step 4: Pay Monthly Rent (Buyer)
# The buyer pays for the specific pending month.

# Endpoint: POST /api/payments/process/
# Auth: Buyer Token
# Body:
# json
# {
#     "payment_type": "monthly_rent",
#     "property_id": "PROPERTY_UUID",
#     "monthly_payment_id": "MONTHLY_PAYMENT_UUID"
# }
# Result: The status of that specific month changes to paid.
# Step 5: Verify Payment History (Buyer or Seller)
# Check the financial transaction records.

# Endpoint: GET /api/payments/
# Auth: Buyer Token (or Seller Token)
# Result: You should see two transactions:
# Type: security_deposit (Amount = Deposit + 1st Month)
# Type: rent (Amount = 1 Month Rent)
# Generated by Gemini 3 Pro Preview
# Prompts to try



