import json
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

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message.content,
                'sender_username': sender.username,
                'timestamp': str(message.timestamp.isoformat())
            }
        )

    # Receive message from room group
    # This method is triggered by group_send for every connected user in the group
    async def chat_message(self, event):
        message = event['message']
        sender_username = event['sender_username']
        timestamp = event['timestamp']

        # Send message to WebSocket
        # Step 3: Server sends data back -> Client receives it
        await self.send(text_data=json.dumps({
            'message': message,
            'sender_username': sender_username,
            'timestamp': timestamp
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
    Frontend should connect to this when the user logs in.
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

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def send_notification(self, event):
        # Send notification data to the WebSocket
        await self.send(text_data=json.dumps(event))
