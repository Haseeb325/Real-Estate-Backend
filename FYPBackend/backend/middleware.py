from asgiref.sync import sync_to_async
from urllib.parse import parse_qs
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from django.contrib.auth.models import AnonymousUser

class JWTAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        jwt_auth = JWTAuthentication()
        scope["user"] = AnonymousUser()

        # Check query string
        query_string = parse_qs(scope.get("query_string", b"").decode())
        token = query_string.get("token", [None])[0]

        if token:
            try:
                validated_token = jwt_auth.get_validated_token(token)
                # Use sync_to_async here for ORM
                user = await sync_to_async(jwt_auth.get_user)(validated_token)
                scope["user"] = user
            except InvalidToken:
                pass

        return await self.app(scope, receive, send)
