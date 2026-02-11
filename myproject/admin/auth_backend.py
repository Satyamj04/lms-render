"""
Custom authentication backend for Profile/UserProfile models
"""
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import User as DjangoUser
from admin.models import UserProfile


class ProfileBackend(BaseBackend):
    """
    Authenticate using UserProfile model from admin app
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate user by email/username and password
        """
        email = kwargs.get('email', username)
        
        try:
            # Try to find user by email
            if '@' in str(email):
                profile = UserProfile.objects.get(email=email)
            else:
                # Try as username  pattern (first.last)
                profile = UserProfile.objects.get(email=email)
        except UserProfile.DoesNotExist:
            return None
        
        # Check password
        if check_password(password, profile.password_hash):
            # Get or create corresponding Django user for token auth
            django_user, created = DjangoUser.objects.get_or_create(
                username=f"user_{profile.id}",
                defaults={
                    'email': profile.email,
                    'first_name': profile.first_name,
                    'last_name': profile.last_name,
                }
            )
            
            # Store profile reference
            django_user._profile = profile
            return django_user
        
        return None
    
    def get_user(self, user_id):
        """
        Get user by ID
        """
        try:
            user = DjangoUser.objects.get(pk=user_id)
            # Attach profile if needed
            try:
                profile_id = user.username.replace('user_', '')
                user._profile = UserProfile.objects.get(id=profile_id)
            except:
                pass
            return user
        except DjangoUser.DoesNotExist:
            return None
