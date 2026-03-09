from django.db.models import Q
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from ..models import ChatSession, ChatMessage, Property
from ..serializers import ChatSessionSerializer, ChatMessageSerializer

class ChatSessionListCreateAPIView(generics.ListCreateAPIView):
    """
    get:
    List all chat sessions for the current user (both as buyer and seller).
    
    post:
    Create a new chat session. A buyer can initiate a chat with a seller 
    about a specific property. If a session already exists for the same
    buyer and property, the existing session will be returned.
    """
    serializer_class = ChatSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        This view should return a list of all chat sessions
        for the currently authenticated user, where they are
        either the buyer or the seller of the property involved.
        """
        user = self.request.user
        return ChatSession.objects.filter(
            Q(buyer=user) | Q(property__user=user)
        ).select_related('property__user', 'buyer').order_by('-updated_at')

    def create(self, request, *args, **kwargs):
        """
        Custom create logic to handle idempotent chat session creation by a buyer.
        A buyer cannot start a chat on their own property.
        """
        property_id = request.data.get('property')
        if not property_id:
            return Response({"error": "Property ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            prop = Property.objects.select_related('user').get(id=property_id)
        except Property.DoesNotExist:
            return Response({"error": "Property not found."}, status=status.HTTP_404_NOT_FOUND)

        buyer = request.user # here buyer actually a seller which cant start sesion on own property

        if prop.user == buyer:
            return Response(
                {"error": "You cannot start a chat session for your own property."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # get_or_create is atomic and handles the race condition of creating a session
        session, created = ChatSession.objects.get_or_create(
            property=prop,
            buyer=buyer
        )
        
        serializer = self.get_serializer(session)
        
        # Determine the correct status code
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        
        return Response(serializer.data, status=status_code)


class ChatMessageListAPIView(generics.ListAPIView):
    """
    get:
    Retrieve the message history for a specific chat session.
    """
    serializer_class = ChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """
        This view should return a list of all messages for a given
        chat session, provided the current user is part of that session.
        """
        session_id = self.kwargs.get('session_id')
        user = self.request.user

        try:
            # Ensure the session exists and the user is part of it before proceeding
            session = ChatSession.objects.get(Q(id=session_id) & (Q(buyer=user) | Q(property__user=user)))
            
            # Optimization: Mark messages from the *other* party as read.
            # This prevents a user from marking their own messages as read.
            session.messages.filter(is_read=False).exclude(sender=user).update(is_read=True)

            return session.messages.order_by('timestamp')
            
        except ChatSession.DoesNotExist:
            # If no such session is found for the user, return an empty queryset
            # This is a security measure to prevent leaking information about session existence.
            return ChatMessage.objects.none()

