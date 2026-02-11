"""
Leaderboard API Views
Endpoints for individual and team leaderboards
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from ..services.leaderboard_service import LeaderboardService
import logging

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_individual_leaderboard(request, course_id=None):
    """
    GET /api/trainee/leaderboard/individual/
    GET /api/trainee/leaderboard/individual/<course_id>/
    
    Query params:
        - limit: Number of top results to return (optional)
        - refresh: If true, recalculate before returning (optional)
    """
    try:
        limit = request.GET.get('limit', None)
        refresh = request.GET.get('refresh', 'false').lower() == 'true'
        
        # Recalculate if requested
        if refresh:
            LeaderboardService.calculate_individual_leaderboard(course_id)
        
        # Fetch leaderboard
        leaderboard = LeaderboardService.get_individual_leaderboard(
            course_id=course_id, 
            limit=int(limit) if limit else None
        )
        
        return Response({
            'success': True,
            'leaderboard': leaderboard,
            'total_entries': len(leaderboard)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error fetching individual leaderboard: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_team_leaderboard(request, course_id=None):
    """
    GET /api/trainee/leaderboard/team/
    GET /api/trainee/leaderboard/team/<course_id>/
    
    Query params:
        - limit: Number of top results to return (optional)
        - refresh: If true, recalculate before returning (optional)
    """
    try:
        limit = request.GET.get('limit', None)
        refresh = request.GET.get('refresh', 'false').lower() == 'true'
        
        # Recalculate if requested
        if refresh:
            LeaderboardService.calculate_team_leaderboard(course_id)
        
        # Fetch leaderboard
        leaderboard = LeaderboardService.get_team_leaderboard(
            course_id=course_id,
            limit=int(limit) if limit else None
        )
        
        return Response({
            'success': True,
            'leaderboard': leaderboard,
            'total_teams': len(leaderboard)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error fetching team leaderboard: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def calculate_leaderboards(request):
    """
    POST /api/trainee/leaderboard/calculate/
    
    Body:
        - course_id: UUID (optional) - calculate for specific course
        - type: 'individual' | 'team' | 'both' (default: 'both')
    """
    try:
        course_id = request.data.get('course_id', None)
        leaderboard_type = request.data.get('type', 'both')
        
        results = {}
        
        if leaderboard_type in ['individual', 'both']:
            individual_results = LeaderboardService.calculate_individual_leaderboard(course_id)
            results['individual'] = {
                'calculated': True,
                'entries': len(individual_results)
            }
        
        if leaderboard_type in ['team', 'both']:
            team_results = LeaderboardService.calculate_team_leaderboard(course_id)
            results['team'] = {
                'calculated': True,
                'teams': len(team_results)
            }
        
        return Response({
            'success': True,
            'results': results,
            'message': 'Leaderboards calculated successfully'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error calculating leaderboards: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_user_rank(request, user_id, course_id=None):
    """
    GET /api/trainee/leaderboard/user/<user_id>/rank/
    GET /api/trainee/leaderboard/user/<user_id>/rank/<course_id>/
    
    Get a specific user's rank and stats
    """
    try:
        leaderboard = LeaderboardService.get_individual_leaderboard(course_id)
        
        user_entry = next(
            (entry for entry in leaderboard if str(entry['user_id']) == str(user_id)),
            None
        )
        
        if not user_entry:
            return Response({
                'success': False,
                'error': 'User not found in leaderboard'
            }, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'success': True,
            'user_rank': user_entry,
            'total_participants': len(leaderboard)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error fetching user rank: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
