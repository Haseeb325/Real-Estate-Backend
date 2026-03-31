import random
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from ..serializers import UserRegisterationStep1Serializer
from ..models import *
from ..utils.api_response import success_response, error_response
import uuid
from django.core.cache import cache
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from ..tasks import send_otp_email, send_reset_password_email, send_welcome_email


class UserRegisterationStep1View(APIView):
    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        email = request.data.get('email')

        # Check existing users in DB
        if CustomUser.objects.filter(username=username).exists():
            return error_response(message="Username already exists.", status_code=status.HTTP_400_BAD_REQUEST)
        if CustomUser.objects.filter(email=email).exists():
            return error_response(message="Email already exists.", status_code=status.HTTP_400_BAD_REQUEST)

        serializer = UserRegisterationStep1Serializer(data=request.data)
        if serializer.is_valid():
            # Check if user already started registration (reuse token)
            existing_tokens = [
                key for key in cache.keys("registration:*")
                if cache.get(key)["data"]["email"] == email
            ]
            if existing_tokens:
                token = existing_tokens[0].split(":")[-1]
                print(">>> Reusing existing token:", token)
            else:
                token = str(uuid.uuid4())
                # Store registration data permanently
                cache.set(
                    f"registration:{token}",
                    {"data": serializer.validated_data},
                    timeout=None
                )
                print(">>> Writing new registration to Redis:", token)

            # Always generate new OTP (even for reused token)
            otp = str(random.randint(100000, 999999))
            cache.set(f"registration_otp:{token}", {"otp": otp, "attempt": 0}, timeout=60)
            print(f"--- REGISTRATION OTP for {serializer.validated_data['email']}: {otp} ---")
            send_otp_email.delay(serializer.validated_data["email"], otp)


         
            return success_response(
                data={"token": token, "otp": otp},
                message="A verification OTP has been sent to your email.",
                status_code=status.HTTP_200_OK,
            )

        return error_response(message="Validation error", data=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)


class VerifyOTPView(APIView):
    """
    Verify OTP for registration.
    Expects:
        - token: string (from Step 1 response)
        - otp: string (6-digit)
    """
    def post(self, request, *args, **kwargs):
        token = request.headers.get("token")
        otp = request.data.get("otp")

        if not token or not otp:
            return error_response(message="Token and OTP are required", status_code=status.HTTP_400_BAD_REQUEST)

        otp_data = cache.get(f"registration_otp:{token}")
        if not otp_data:
            return error_response(message="OTP expired or invalid", status_code=status.HTTP_400_BAD_REQUEST)

        if otp_data["otp"] == otp:
            # OTP verified successfully, you can delete OTP to prevent reuse
            cache.delete(f"registration_otp:{token}")
            return success_response(message="OTP Verified", data={}, status_code=status.HTTP_200_OK)

        # OTP verification failed
        return error_response(message="Invalid OTP", status_code=status.HTTP_400_BAD_REQUEST)
    


class ResendOTPView(APIView):
    """
    Resend OTP for registration.
    Expects:
        - token: string (from Step 1 response)
    """
    def get(self, request, *args, **kwargs):
        token = request.headers.get("token")

        if not token:
            return error_response(message="Token is required", status_code=status.HTTP_400_BAD_REQUEST)

        registration = cache.get(f"registration:{token}")
        if not registration:
            return error_response(message="Invalid token", status_code=status.HTTP_400_BAD_REQUEST)

        # Generate a new OTP
        new_otp = str(random.randint(100000, 999999))
        cache.set(f"registration_otp:{token}", {"otp": new_otp, "attempt": 0}, timeout=60)
        print(registration)

        print(f"--- RESEND OTP for {registration['data']['email']}: {new_otp} ---")
        send_otp_email.delay(registration["data"]["email"], new_otp)

        return success_response(data={"otp": new_otp}, message="A verification OTP has been sent to your email.", status_code=status.HTTP_200_OK)
    


class UserRegistrationStep2View(APIView):
    """
    Step 2: Set Password
    Expects:
      - Headers: X-Registration-Token
      - Body: password, confirm_password
    """
    def post(self, request, *args, **kwargs):
        password = request.data.get("password")
        confirm_password = request.data.get("confirm_password")
        token = request.headers.get("token")

        if not token:
            return error_response(message="Token is required", status_code=status.HTTP_400_BAD_REQUEST)

        if not password or not confirm_password:
            return error_response(message="Password and confirm password are required", status_code=status.HTTP_400_BAD_REQUEST)

        if password != confirm_password:
            return error_response(message="Passwords do not match", status_code=status.HTTP_400_BAD_REQUEST)

        registration = cache.get(f"registration:{token}")
        if not registration:
            return error_response(message="Invalid token", status_code=status.HTTP_400_BAD_REQUEST)

        # Update password in registration data (hash later during final user creation)
        registration["data"]["password"] = password

        # Save back to Redis so Step 3 can access it
        cache.set(f"registration:{token}", registration, timeout=None)
        print(registration)
        print(token)
        print(registration["data"]["password"])

        return success_response(data={"token": token}, message="Password set successfully.", status_code=status.HTTP_200_OK)





class UserRegistrationStep3View(APIView):
    def post(self, request, *args, **kwargs):
        token = request.headers.get("token")
        role = request.data.get("role")

        if not token:
            return error_response(message="Token is required", status_code=status.HTTP_400_BAD_REQUEST)

        registration = cache.get(f"registration:{token}")
        if not registration:
            return error_response(message="Invalid token", status_code=status.HTTP_400_BAD_REQUEST)

        if not role:
            return error_response(message="Role is required", status_code=status.HTTP_400_BAD_REQUEST)

        if role not in [UserRole.BUYER, UserRole.SELLER]:
            return error_response(message="Invalid role", status_code=status.HTTP_400_BAD_REQUEST)

        full_name = registration["data"]["full_name"]
        username = registration["data"]["username"]
        email = registration["data"]["email"]
        password = registration["data"]["password"]

        already_exists = CustomUser.objects.filter(email=email).exists() or CustomUser.objects.filter(username=username).exists()
        if already_exists:
            return error_response(message="User already exists", status_code=status.HTTP_400_BAD_REQUEST)

        user = CustomUser.objects.create_user(email=email,
                                              username=username,
                                              full_name=full_name,
                                              password=password,
                                              role=role)
        user.save()

        send_welcome_email.delay(user.email, user.full_name)

        return success_response(data={"user_id": user.id}, message="User created successfully.", status_code=status.HTTP_200_OK)
    



# def send_forgot_password_email(email, link):
#     # Simulate email sending process
#     try:
#         # Code to send the email goes here
#         print("Sending email...")
#         print(link)
#         return True
#     except Exception as e:
#         print(f"Failed to send email: {e}")
#         return False

class ForgotPassword(APIView):
    def post(self, request, *args, **kwargs):
        email = request.data.get("email")
        if not email:
            return error_response(message="Email is required", status_code=status.HTTP_400_BAD_REQUEST)

        already_user = CustomUser.objects.filter(email=email).first()
        if not already_user:
            return error_response(message="Account not found", status_code=status.HTTP_401_UNAUTHORIZED)
        
        # Check if token already exists for this email
        existing_tokens = [
            key for key in cache.keys("forgot_password:*")
            if cache.get(key) is not None and cache.get(key).get("email") == email
        ]
        
        if existing_tokens:
            # Reuse existing token
            token = existing_tokens[0].split(":")[-1]
            print(">>> Reusing existing token:", token)
        else:
            # Create new token
            token = str(uuid.uuid4())
            cache.set(f"forgot_password:{token}", {"email": email, "attempt": 0}, timeout=3600)
            print(">>> Created new token:", token)
        
        base_url = "http://127.0.0.1"
        link = f"{base_url}/{email}/{token}"

        send_reset_password_email.delay(email, link)
        return success_response(message="Link has been sent. Click to reset password", data={"token": token}, status_code=status.HTTP_200_OK)


class ResetPassword(APIView):
    def post(self, request):
        new_password = request.data.get("new_password")
        confirm_password = request.data.get("confirm_password")
        token = request.headers.get("token")
        email = request.headers.get("email")

        if not new_password or not confirm_password:
            return error_response(message="All fields are required", status_code=status.HTTP_400_BAD_REQUEST)
        if new_password != confirm_password:
            return error_response(message="Password must be same", status_code=status.HTTP_400_BAD_REQUEST)

        already_token = cache.get(f"forgot_password:{token}")
        if not already_token:
            return error_response(message="Token Expired or invalid", status_code=status.HTTP_400_BAD_REQUEST)

        if already_token.get("email") != email:
            return error_response(message="Invalid token", status_code=status.HTTP_400_BAD_REQUEST)

        user = CustomUser.objects.filter(email=email).first()
        if user:
            user.set_password(new_password)
            user.save()
            return success_response(message="Password updated successfully", data={}, status_code=status.HTTP_200_OK)

        return error_response(message="User not found", status_code=status.HTTP_400_BAD_REQUEST)
        
            

#   Sign in process

class SignInView(APIView):
      def post(self, request, *args, **kwargs):
        email = request.data.get("email")
        password = request.data.get("password")
        if not email or not password:
            return error_response(message="Email and password are required", status_code=status.HTTP_400_BAD_REQUEST)

        #   Authenticate the user
        user = CustomUser.objects.filter(email=email).first()
        if not user:
            return error_response(message="Invalid credentials", status_code=status.HTTP_401_UNAUTHORIZED)

        # Check password in two ways
        if not (user.check_password(password) or user.password == password):
            return error_response(message="Invalid credentials", status_code=status.HTTP_401_UNAUTHORIZED)

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        refresh_token = str(refresh)
        access_token = str(refresh.access_token)

        # create response
        response = success_response(
            data={
                "access": access_token,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                    "role": user.role,
                },
            },
            message="Login Successfully",
            status_code=status.HTTP_200_OK,
        )
        response.set_cookie(
            'access_token',
            access_token,
            max_age=5*60,
            httponly=True,
            secure=settings.DEBUG is False,
            samesite='Lax'
        )
        response.set_cookie(
            'refresh_token',
            refresh_token,
            max_age=7*24*60*60,
            httponly=True,
            secure=settings.DEBUG is False,
            samesite='Lax'
        )
        print(refresh_token)
        print(access_token)
        return response
              



class RefreshAccessTokenView(APIView):
    """
    Refresh expired access token using refresh token from cookie
    """
    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get('refresh_token')

        if not refresh_token:
            return error_response(message="Refresh token missing", status_code=status.HTTP_401_UNAUTHORIZED)

        try:
            refresh = RefreshToken(refresh_token)
            new_access_token = str(refresh.access_token)

            response = success_response(message="Token refreshed successfully", data={"access": new_access_token}, status_code=status.HTTP_200_OK)

            response.set_cookie(
                'access_token',
                new_access_token,
                max_age=5*60,
                httponly=True,
                secure=settings.DEBUG is False,
                samesite='Lax'
            )
            return response
        except TokenError:
            return error_response(message="Invalid refresh token", status_code=status.HTTP_401_UNAUTHORIZED)



class LogoutView(APIView):
    """
    Logout by clearing cookies
    """
    def post(self, request, *args, **kwargs):
        response = success_response(message="Logout successful", data={}, status_code=status.HTTP_200_OK)

        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')

        return response

