"""
Multi-Module Authentication Service
Reusable authentication service for admin, trainer, manager, and trainee modules
"""
import os
from django.contrib.auth.hashers import check_password, make_password
from trainee.models import User
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status


class MultiModuleAuthService:
    """
    Reusable authentication service for multiple modules
    Can be integrated with admin, trainer, manager modules
    """
    
    @staticmethod
    def get_or_create_default_user(role='trainee'):
        """
        Get or create a default user for the specified role
        Useful for development/testing without full auth mechanism
        """
        no_auth = os.getenv('NO_AUTH', 'False') == 'True'
        
        if not no_auth:
            return None
        
        # Build user credentials from environment
        email_key = f'DEFAULT_USER_EMAIL_{role.upper()}'
        password_key = f'DEFAULT_USER_PASSWORD_{role.upper()}'
        first_name_key = f'DEFAULT_USER_FIRST_NAME_{role.upper()}'
        last_name_key = f'DEFAULT_USER_LAST_NAME_{role.upper()}'
        
        # Fallback to generic defaults
        email = os.getenv(email_key, f'{role}@example.com')
        password = os.getenv(password_key, 'password123')
        first_name = os.getenv(first_name_key, role.capitalize())
        last_name = os.getenv(last_name_key, 'User')
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            user = User.objects.create(
                email=email,
                password_hash=make_password(password),
                first_name=first_name,
                last_name=last_name,
                primary_role=role,
                status='active'
            )
        
        return user
    
    @staticmethod
    def verify_user_credentials(email, password):
        """
        Verify user credentials against database
        Returns user object if valid, None otherwise
        """
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return None
        
        # Check if user account is active
        if user.status != 'active':
            return None
        
        # Verify password hash
        if user.password_hash:
            if user.password_hash.startswith('pbkdf2_sha256$'):
                password_valid = check_password(password, user.password_hash)
            else:
                # Fallback: treat as plain text comparison for legacy accounts
                password_valid = (password == user.password_hash)
        else:
            password_valid = False
        
        return user if password_valid else None
    
    @staticmethod
    def get_authenticated_user(request):
        """
        Get authenticated user from request
        Works with both JWT and NO_AUTH modes
        """
        # If NO_AUTH is enabled, return default user
        no_auth = os.getenv('NO_AUTH', 'False') == 'True'
        if no_auth:
            return MultiModuleAuthService.get_or_create_default_user('trainee')
        
        # Otherwise, get from request (set by authentication backend)
        if hasattr(request, 'user') and hasattr(request.user, 'user_id'):
            return User.objects.get(user_id=request.user.user_id)
        
        return None


def create_multi_module_login_endpoint(module_name='trainee', allowed_roles=None):
    """
    Factory function to create a login endpoint for any module
    
    Usage:
        from trainee.services.multi_module_auth import create_multi_module_login_endpoint
        
        # In your urls.py
        login_view = create_multi_module_login_endpoint('admin', ['admin'])
        
        urlpatterns = [
            path('auth/login/', login_view, name='admin-login'),
        ]
    """
    if allowed_roles is None:
        allowed_roles = [module_name]
    
    @api_view(['POST'])
    @permission_classes([AllowAny])
    def login(request):
        """
        Multi-module login endpoint
        Supports any user with valid email and password
        """
        from django.utils import timezone
        
        email = request.data.get('email')
        password = request.data.get('password')
        
        if not email or not password:
            return Response(
                {'error': 'Email and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify credentials
        user = MultiModuleAuthService.verify_user_credentials(email, password)
        
        if not user:
            # Check if NO_AUTH is enabled, return default user
            if os.getenv('NO_AUTH', 'False') == 'True':
                user = MultiModuleAuthService.get_or_create_default_user(module_name)
            
            if not user:
                return Response(
                    {'error': 'Invalid email or password'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        
        # Verify user has allowed role
        if allowed_roles and user.primary_role not in allowed_roles:
            return Response(
                {'error': f'User role must be one of: {", ".join(allowed_roles)}'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Update last login timestamp
        user.last_login = timezone.now()
        user.save()
        
        return Response({
            'success': True,
            'user': {
                'id': str(user.user_id),
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.primary_role,
            },
        }, status=status.HTTP_200_OK)
    
    return login


@api_view(['POST'])
@permission_classes([AllowAny])
def create_multi_module_logout_endpoint():
    """
    Generic logout endpoint for any module
    """
    def logout(request):
        return Response(
            {'success': True, 'message': 'Logged out successfully'},
            status=status.HTTP_200_OK
        )
    return logout
