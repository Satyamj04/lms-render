"""
Custom authentication backend for optional JWT tokens
Supports both authenticated and non-authenticated access for testing/development
"""
import jwt
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from admin.models import UserProfile as User
import os


class OptionalJWTAuthentication(BaseAuthentication):
    """
    Optional JWT authentication that works with our custom User model.
    If NO_AUTH environment variable is set to True, uses default credentials.
    Otherwise, requires valid JWT token for authentication.
    """
    
    def authenticate(self, request):
        # Check if authentication is disabled
        if os.getenv('NO_AUTH', 'False') == 'True':
            # Use default user from environment
            default_email = os.getenv('DEFAULT_USER_EMAIL', 'trainee@example.com')
            try:
                user = User.objects.get(email=default_email)
                class AuthenticatedUser:
                    def __init__(self, user):
                        self.user_id = user.user_id
                        self.email = user.email
                        self.is_authenticated = True
                
                auth_user = AuthenticatedUser(user)
                return (auth_user, None)
            except User.DoesNotExist:
                # Create default user if it doesn't exist
                default_password = os.getenv('DEFAULT_USER_PASSWORD', 'password123')
                default_first_name = os.getenv('DEFAULT_USER_FIRST_NAME', 'Default')
                default_last_name = os.getenv('DEFAULT_USER_LAST_NAME', 'User')
                
                from django.contrib.auth.hashers import make_password
                user = User.objects.create(
                    email=default_email,
                    password_hash=make_password(default_password),
                    first_name=default_first_name,
                    last_name=default_last_name,
                    primary_role='trainee',
                    status='active'
                )
                
                class AuthenticatedUser:
                    def __init__(self, user):
                        self.user_id = user.user_id
                        self.email = user.email
                        self.is_authenticated = True
                
                auth_user = AuthenticatedUser(user)
                return (auth_user, None)
        
        # Standard JWT authentication
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header.startswith('Bearer '):
            return None
        
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        
        try:
            # Decode JWT token
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            
            # Get user from database using email from payload
            email = payload.get('email')
            user_id = payload.get('user_id')
            
            if not email and not user_id:
                raise AuthenticationFailed('Invalid token: missing email or user_id')
            
            # Try to get user by email first, then by user_id
            try:
                if email:
                    user = User.objects.get(email=email)
                else:
                    user = User.objects.get(user_id=user_id)
            except User.DoesNotExist:
                raise AuthenticationFailed('User not found')
            
            # Create a simple object to hold user info
            class AuthenticatedUser:
                def __init__(self, user):
                    self.user_id = user.user_id
                    self.email = user.email
                    self.is_authenticated = True
            
            auth_user = AuthenticatedUser(user)
            
            return (auth_user, token)
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token has expired')
        except jwt.InvalidTokenError:
            raise AuthenticationFailed('Invalid token')
        except Exception as e:
            raise AuthenticationFailed(f'Authentication failed: {str(e)}')
