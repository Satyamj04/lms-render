"""
Profile API view - returns and updates user profile.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.db.models import Sum
from trainee.models import User, BadgeAssignment, Leaderboard


class ProfileView(APIView):
    """Profile API - returns and updates user profile"""
    permission_classes = [AllowAny]

    def get(self, request):
        # Try to get Mukesh Pawar from database
        try:
            user = User.objects.get(email='mukesh.pawar@example.com', first_name='Mukesh', last_name='Pawar')
            
            # Get user points from leaderboard
            try:
                leaderboard = Leaderboard.objects.get(scope='global', user=user)
                points = leaderboard.points
                rank = leaderboard.rank or 0
            except Leaderboard.DoesNotExist:
                points = 0
                rank = 0

            # Get badges count
            badges_count = BadgeAssignment.objects.filter(user=user).count()

            # Determine rank tier based on points
            if points >= 1000:
                rank_tier = 'Gold'
            elif points >= 500:
                rank_tier = 'Silver'
            else:
                rank_tier = 'Bronze'

            data = {
                'user_id': str(user.user_id),
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'primary_role': user.primary_role,
                'profile_image_url': user.profile_image_url,
                'status': user.status,
                'rank_tier': rank_tier,
                'points': points,
                'rank': rank,
                'badges': badges_count,
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'created_at': user.created_at.isoformat()
            }
        except User.DoesNotExist:
            # Fallback to hardcoded data if user doesn't exist
            data = {
                'user_id': 'hardcoded-user-id',
                'first_name': 'Mukesh',
                'last_name': 'Pawar',
                'email': 'mukesh.pawar@example.com',
                'primary_role': 'trainee',
                'profile_image_url': None,
                'status': 'active',
                'rank_tier': 'Bronze',
                'points': 100,
                'rank': 1,
                'badges': 2,
                'last_login': None,
                'created_at': '2024-01-01T00:00:00Z'
            }
        
        return Response(data, status=status.HTTP_200_OK)

    def patch(self, request):
        """Update user profile"""
        try:
            user = User.objects.get(email='mukesh.pawar@example.com', first_name='Mukesh', last_name='Pawar')
            
            # Allow updating specific fields
            if 'first_name' in request.data:
                user.first_name = request.data['first_name']
            if 'last_name' in request.data:
                user.last_name = request.data['last_name']
            if 'profile_image_url' in request.data:
                user.profile_image_url = request.data['profile_image_url']
            
            user.save()
            
            return Response({
                "message": "Profile updated successfully",
                "user_id": str(user.user_id)
            }, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({
                "message": "Profile update not available in demo mode",
                "user_id": "hardcoded-user-id"
            }, status=status.HTTP_200_OK)
