"""
Screentime API Endpoints
Handles screentime tracking and reporting endpoints
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from trainee.models import User, Module, Course
from trainee.services.screentime import ScreentimeService
from trainee.services.learning_progress import LearningProgressService
import logging

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
def start_module_session(request, module_id):
    """
    POST /api/trainee/screentime/module/{module_id}/start
    Start a learning session for a module
    """
    try:
        module = get_object_or_404(Module, module_id=module_id)
        user = LearningProgressService.get_user()
        
        if not user:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        session_data = ScreentimeService.start_module_session(user, module)
        
        if not session_data:
            return Response(
                {'error': 'Failed to start session'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(session_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.exception(f"Error starting module session: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def record_screentime(request, module_id):
    """
    POST /api/trainee/screentime/module/{module_id}/track
    Record time spent on a module
    
    Request body:
    {
        "time_spent_seconds": 300  # seconds spent
    }
    """
    try:
        module = get_object_or_404(Module, module_id=module_id)
        user = LearningProgressService.get_user()
        
        if not user:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        time_spent_seconds = request.data.get('time_spent_seconds', 0)
        
        if not isinstance(time_spent_seconds, (int, float)) or time_spent_seconds < 0:
            return Response(
                {'error': 'Invalid time_spent_seconds value'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        result = ScreentimeService.record_screentime(user, module, int(time_spent_seconds))
        
        if not result:
            return Response(
                {'error': 'Failed to record screentime'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.exception(f"Error recording screentime: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_module_screentime(request, module_id):
    """
    GET /api/trainee/screentime/module/{module_id}
    Get screentime data for a specific module
    """
    try:
        module = get_object_or_404(Module, module_id=module_id)
        user = LearningProgressService.get_user()
        
        if not user:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        screentime_data = ScreentimeService.get_module_screentime(user, module)
        
        if not screentime_data:
            return Response(
                {'error': 'Failed to retrieve screentime data'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(screentime_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.exception(f"Error retrieving module screentime: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_course_screentime(request, course_id):
    """
    GET /api/trainee/screentime/course/{course_id}
    Get screentime data for a course (sum of all modules)
    """
    try:
        course = get_object_or_404(Course, course_id=course_id)
        user = LearningProgressService.get_user()
        
        if not user:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        screentime_data = ScreentimeService.get_course_screentime(user, course)
        
        if not screentime_data:
            return Response(
                {'error': 'Failed to retrieve screentime data'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(screentime_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.exception(f"Error retrieving course screentime: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_total_screentime(request):
    """
    GET /api/trainee/screentime/total
    Get user's total screentime across all courses
    """
    try:
        user = LearningProgressService.get_user()
        
        if not user:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        screentime_data = ScreentimeService.get_total_screentime(user)
        
        if not screentime_data:
            return Response(
                {'error': 'Failed to retrieve screentime data'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(screentime_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.exception(f"Error retrieving total screentime: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_screentime_analytics(request):
    """
    GET /api/trainee/screentime/analytics
    Get screentime analytics for a period
    
    Query parameters:
    - days: int (default 30) - number of days to analyze
    """
    try:
        user = LearningProgressService.get_user()
        
        if not user:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        days = request.query_params.get('days', 30)
        try:
            days = int(days)
        except (ValueError, TypeError):
            days = 30
        
        analytics_data = ScreentimeService.get_screentime_analytics(user, days=days)
        
        if not analytics_data:
            return Response(
                {'error': 'Failed to retrieve analytics data'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(analytics_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.exception(f"Error retrieving screentime analytics: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
