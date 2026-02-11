"""
Unified Authentication Service
Validates credentials for all user roles
- Admin: Hardcoded credentials
- Trainer, Manager, Trainee: PostgreSQL users table
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.hashers import check_password
from django.utils import timezone
from .models import UserProfile

# Hardcoded admin credentials
ADMIN_EMAIL = 'chris.w@company.com'
ADMIN_PASSWORD = 'demo'


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    Unified login endpoint for all roles
    - Admin: Uses hardcoded credentials
    - Other roles: Validates against the users table
    
    Request body:
    {
        "email": "user@example.com",
        "password": "password123"
    }
    
    Response:
    {
        "success": true,
        "user": {
            "id": "uuid",
            "email": "user@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "name": "John Doe",
            "role": "admin|trainer|manager|trainee",
            "status": "active",
            "createdAt": "2024-01-01",
            "lastLogin": "2024-12-22"
        }
    }
    """
    email = request.data.get('email')
    password = request.data.get('password')
    
    if not email or not password:
        return Response(
            {'success': False, 'error': 'Email and password are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    email = email.strip().lower()
    
    # Check hardcoded admin credentials first
    if email == ADMIN_EMAIL.lower() and password == ADMIN_PASSWORD:
        # Return hardcoded admin user
        return Response({
            'success': True,
            'user': {
                'id': 'u007',
                'email': ADMIN_EMAIL,
                'first_name': 'Chris',
                'last_name': 'Wilson',
                'name': 'Chris Wilson',
                'role': 'admin',
                'status': 'active',
                'createdAt': '2023-12-01',
                'lastLogin': timezone.now().strftime('%Y-%m-%d'),
            }
        }, status=status.HTTP_200_OK)
    
    # For non-admin users, validate against database (case-insensitive email lookup)
    try:
        user = UserProfile.objects.get(email__iexact=email)
    except UserProfile.DoesNotExist:
        return Response(
            {'success': False, 'error': 'Invalid email or password'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Check if account is active
    if user.status != 'active':
        return Response(
            {'success': False, 'error': 'Your account is inactive. Please contact an administrator.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Verify password (handles PBKDF2 hashes)
    if not check_password(password, user.password_hash):
        return Response(
            {'success': False, 'error': 'Invalid email or password'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Update last login timestamp
    user.last_login = timezone.now()
    user.save(update_fields=['last_login'])
    
    # Generate or get authentication token for API access
    from django.contrib.auth.models import User as DjangoUser
    from rest_framework.authtoken.models import Token
    
    try:
        # Get or create Django User for token authentication
        django_user, created = DjangoUser.objects.get_or_create(
            username=f"user_{user.id}",
            defaults={
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
            }
        )
        
        # Get or create authentication token
        token, _ = Token.objects.get_or_create(user=django_user)
        token_key = token.key
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception('Failed to generate token: %s', e)
        token_key = None
    
    # Format response matching frontend User type
    response_data = {
        'success': True,
        'user': {
            'id': str(user.id),
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'name': f"{user.first_name} {user.last_name}",
            'role': user.role,
            'status': user.status,
            'createdAt': user.created_at.strftime('%Y-%m-%d') if user.created_at else None,
            'lastLogin': user.last_login.strftime('%Y-%m-%d') if user.last_login else None,
        }
    }
    
    # Include token if generated successfully
    if token_key:
        response_data['token'] = token_key
    
    return Response(response_data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def logout(request):
    """
    Logout endpoint - currently just returns success
    Frontend handles token cleanup
    """
    return Response(
        {'success': True, 'message': 'Logged out successfully'},
        status=status.HTTP_200_OK
    )
