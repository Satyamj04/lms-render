"""
Authentication views for user login and logout.
Uses the reusable MultiModuleAuthService for flexible integration with other modules.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.hashers import check_password
from django.utils import timezone
from trainee.models import User
from trainee.services.multi_module_auth import MultiModuleAuthService, create_multi_module_login_endpoint
import os


# Use the factory function to create the login endpoint for trainee module
login = create_multi_module_login_endpoint('trainee', ['trainee'])


@api_view(['POST'])
@permission_classes([AllowAny])
def logout(request):
    """
    User logout endpoint
    """
    return Response(
        {'success': True, 'message': 'Logged out successfully'},
        status=status.HTTP_200_OK
    )

