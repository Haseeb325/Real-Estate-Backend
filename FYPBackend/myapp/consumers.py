import json
from django.utils import timezone
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatMessage, ChatSession, CustomUser

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.room_group_name = f'chat_{self.session_id}'

        user = self.scope["user"]
        print("CONSUMER USER:", user, "Authenticated:", user.is_authenticated)
        print("SESSION ID:", self.session_id)

        # 1️⃣ Check if user is authenticated
        if not user.is_authenticated:
            print("Closing: user not authenticated")
            await self.close()
            return

        # 2️⃣ Check if chat session exists
        self.chat_session = await self.get_chat_session(self.session_id)
        if not self.chat_session:
            print("Closing: chat session not found")
            await self.close()
            return

        print("CHAT SESSION FOUND:", self.chat_session)
        print(
            "BUYER ID:", self.chat_session.buyer_id,
            "PROPERTY OWNER ID:", self.chat_session.property.user_id,
            "USER ID:", user.id
        )

        # 3️⃣ Check if user is part of this chat session (buyer or property owner)
        # Use str() to handle UUID vs string mismatch
        if str(user.id) != str(self.chat_session.buyer_id) and str(user.id) != str(self.chat_session.property.user_id):
            print("Closing: user not part of chat session")
            await self.close()
            return

        # 4️⃣ Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()
        print("WebSocket connection accepted")

    async def disconnect(self, close_code):
        # Leave room group
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    # Receive message from WebSocket
    # Step 1: Client sends data -> Server receives it here
    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message_content = text_data_json.get('message', '').strip() # Suggestion: Strip whitespace
        except (json.JSONDecodeError, AttributeError):
            await self.send(text_data=json.dumps({
                'error': 'Invalid JSON format.'
            }))
            return

        # Suggestion: Validate message content is not empty
        if not message_content:
            return

        sender = self.scope['user']

        # Save message to database
        try:
            message = await self.create_chat_message(message_content, sender)
        except Exception as e:
            # Handle DB errors gracefully
            await self.send(text_data=json.dumps({
                'error': 'Failed to save message.'
            }))
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message_id': str(message.id),
                'sender_id': str(sender.id),
                'message': message.content,
                'sender_username': sender.username,
                'timestamp': str(message.timestamp.isoformat())
            }
        )

        # Also notify the RECIPIENT via their global notification channel
        # so they receive a beep/notification even when the chat screen is not open
        buyer_id = str(self.chat_session.buyer_id)
        seller_id = str(self.chat_session.property.user_id)
        recipient_id = seller_id if str(sender.id) == buyer_id else buyer_id

        await self.channel_layer.group_send(
            f'notifications_{recipient_id}',
            {
                'type': 'send_notification',
                'event_type': 'new_message',
                'session_id': str(self.chat_session.id),
                'sender_username': sender.username,
                'message': message.content,
            }
        )

    # Receive message from room group
    # This method is triggered by group_send for every connected user in the group
    async def chat_message(self, event):
        message_id = event['message_id']
        sender_id = event['sender_id']
        message = event['message']
        sender_username = event['sender_username']
        timestamp = event['timestamp']

        # Send message to WebSocket
        # Step 3: Server sends data back -> Client receives it
        await self.send(text_data=json.dumps({
            'message_id': message_id,
            'sender_id': sender_id,
            'message': message,
            'sender_username': sender_username,
            'timestamp': timestamp
        }))

    async def messages_read(self, event):
        """
        Handler for the 'messages_read' event broadcasted by the REST API.
        """
        await self.send(text_data=json.dumps({
            'type': 'messages_read',
            'message_ids': event['message_ids']
        }))

    @database_sync_to_async
    def get_chat_session(self, session_id):
        try:
            # Suggestion: select_related is good, ensure property is also selected to access property.user
            return ChatSession.objects.select_related('buyer', 'property__user').get(id=session_id)
        except ChatSession.DoesNotExist:
            return None

    
    @database_sync_to_async
    def create_chat_message(self, message_content, sender):
        msg = ChatMessage.objects.create(
            chat_session=self.chat_session,
            sender=sender,
            content=message_content
        )
        # Update the session's updated_at timestamp so it moves to the top of the Inbox
        self.chat_session.save()
        return msg


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    Handles global notifications for a user (e.g., 'You have a new message').
    Also manages online/offline presence and last_seen.
    Frontend connects when the user logs in.
    """
    async def connect(self):
        self.user = self.scope["user"]
        
        if not self.user.is_authenticated:
            await self.close()
            return

        # Create a unique group for this specific user
        self.group_name = f"notifications_{self.user.id}"
        
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Mark user as online
        await self.set_presence(is_online=True)

        # Broadcast presence to all their chat partners
        await self.broadcast_presence(is_online=True)

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

        if hasattr(self, 'user') and self.user.is_authenticated:
            # Mark user as offline and record last_seen
            await self.set_presence(is_online=False, update_last_seen=True)
            # Broadcast presence to all their chat partners
            await self.broadcast_presence(is_online=False)

    async def send_notification(self, event):
        # Send notification data to the WebSocket
        await self.send(text_data=json.dumps(event))

    # ── Presence Helpers ──

    @database_sync_to_async
    def set_presence(self, is_online: bool, update_last_seen: bool = False):
        update_fields = ['is_online']
        self.user.is_online = is_online
        if update_last_seen:
            self.user.last_seen = timezone.now()
            update_fields.append('last_seen')
        CustomUser.objects.filter(pk=self.user.pk).update(
            is_online=self.user.is_online,
            **({'last_seen': self.user.last_seen} if update_last_seen else {})
        )

    @database_sync_to_async
    def get_chat_partner_ids(self):
        """Return IDs of all users who share a chat session with this user."""
        from django.db.models import Q
        sessions = ChatSession.objects.filter(
            Q(buyer=self.user) | Q(property__user=self.user)
        ).select_related('buyer', 'property__user')
        partner_ids = set()
        for session in sessions:
            if str(session.buyer_id) == str(self.user.id):
                partner_ids.add(str(session.property.user_id))
            else:
                partner_ids.add(str(session.buyer_id))
        return partner_ids

    async def broadcast_presence(self, is_online: bool):
        """Broadcast this user's online/offline status to all their chat partners."""
        partner_ids = await self.get_chat_partner_ids()
        last_seen_iso = (
            self.user.last_seen.isoformat() if not is_online and self.user.last_seen else None
        )
        for partner_id in partner_ids:
            await self.channel_layer.group_send(
                f'notifications_{partner_id}',
                {
                    'type': 'send_notification',
                    'event_type': 'presence_update',
                    'user_id': str(self.user.id),
                    'username': self.user.username,
                    'is_online': is_online,
                    'last_seen': last_seen_iso,
                }
            )
