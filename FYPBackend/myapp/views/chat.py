from django.db.models import Q
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from ..models import ChatSession, ChatMessage, Property
from ..serializers import ChatSessionSerializer, ChatMessageSerializer
from ..utils.api_response import success_response, error_response
from ..utils.mixins import StandardAPIViewMixin

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
            return error_response(message="Property ID is required.", status_code=status.HTTP_400_BAD_REQUEST)

        try:
            prop = Property.objects.select_related('user').get(id=property_id)
        except Property.DoesNotExist:
            return error_response(message="Property not found.", status_code=status.HTTP_404_NOT_FOUND)

        buyer = request.user # here buyer actually a seller which cant start sesion on own property

        if prop.user == buyer:
            return error_response(message="You cannot start a chat session for your own property.", status_code=status.HTTP_400_BAD_REQUEST)

        # get_or_create is atomic and handles the race condition of creating a session
        session, created = ChatSession.objects.get_or_create(
            property=prop,
            buyer=buyer
        )

        serializer = self.get_serializer(session)

        # Determine the correct status code
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK

        return success_response(data=serializer.data, message="Chat session returned.", status_code=status_code)

class ChatMessageListAPIView(StandardAPIViewMixin, generics.ListAPIView):
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
            unread_messages = session.messages.filter(is_read=False).exclude(sender=user)
            unread_ids = list(unread_messages.values_list('id', flat=True))
            
            if unread_ids:
                unread_messages.update(is_read=True)
                # Broadcast WebSocket event so the SENDER sees double blue ticks
                try:
                    from channels.layers import get_channel_layer
                    from asgiref.sync import async_to_sync
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        f'chat_{session_id}',
                        {
                            'type': 'messages_read',
                            'message_ids': [str(uid) for uid in unread_ids]
                        }
                    )
                except Exception:
                    pass  # Don't break message loading if WS broadcast fails

            return session.messages.order_by('timestamp')
            
        except ChatSession.DoesNotExist:
            # If no such session is found for the user, return an empty queryset
            # This is a security measure to prevent leaking information about session existence.
            return ChatMessage.objects.none()


class MarkMessagesReadAPIView(StandardAPIViewMixin, generics.UpdateAPIView):
    """
    patch:
    Mark specific messages as read.
    Expects a JSON payload: {"message_ids": ["uuid-1", "uuid-2"]}
    """
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        session_id = self.kwargs.get('session_id')
        message_ids = request.data.get('message_ids', [])
        
        if not message_ids or not isinstance(message_ids, list):
            return error_response(message="Please provide a list of message_ids.", status_code=status.HTTP_400_BAD_REQUEST)

        user = request.user
        
        try:
            session = ChatSession.objects.get(Q(id=session_id) & (Q(buyer=user) | Q(property__user=user)))
        except ChatSession.DoesNotExist:
            return error_response(message="Chat session not found.", status_code=status.HTTP_404_NOT_FOUND)

        # Mark them as read, ensuring they belong to the session and were sent by the OTHER person
        updated_count = ChatMessage.objects.filter(
            chat_session=session,
            id__in=message_ids,
            is_read=False
        ).exclude(sender=user).update(is_read=True)

        if updated_count > 0:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'chat_{session_id}',
                {
                    'type': 'messages_read',
                    'message_ids': message_ids
                }
            )

        return success_response(data={"updated_count": updated_count}, message="Messages marked as read.", status_code=status.HTTP_200_OK)

