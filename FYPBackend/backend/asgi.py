import os
import django
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()  # <-- Initialize Django first!

# Now it's safe to import anything that uses models
from .middleware import JWTAuthMiddleware
import myapp.routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": JWTAuthMiddleware(
        URLRouter(
            myapp.routing.websocket_urlpatterns
        )
    ),
})
