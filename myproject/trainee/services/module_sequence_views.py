"""
Module Sequence API Views
Endpoints for module access control and progress tracking
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from ..services.module_sequence_service import ModuleSequenceService
import logging

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
def check_module_access(request, module_id):
    """
    GET /api/trainee/module/<module_id>/access/
    
    Check if user can access a specific module
    """
    try:
        user_id = request.GET.get('user_id')
        
        if not user_id:
            return Response({
                'success': False,
                'error': 'user_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        can_access, is_locked, reason = ModuleSequenceService.check_module_access(
            user_id=user_id,
            module_id=module_id
        )
        
        return Response({
            'success': True,
            'can_access': can_access,
            'is_locked': is_locked,
            'reason': reason
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error checking module access: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def initialize_course_modules(request, course_id):
    """
    POST /api/trainee/course/<course_id>/modules/initialize/
    
    Initialize module progress for a user in a course
    Body: { user_id: UUID }
    """
    try:
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response({
                'success': False,
                'error': 'user_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        success = ModuleSequenceService.initialize_module_progress(
            user_id=user_id,
            course_id=course_id
        )
        
        if success:
            return Response({
                'success': True,
                'message': 'Module progress initialized successfully'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'error': 'Failed to initialize module progress'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    except Exception as e:
        logger.error(f"Error initializing modules: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_module_progress_list(request, course_id):
    """
    GET /api/trainee/course/<course_id>/modules/progress/
    
    Get all module progress for a user in a course
    Query params: user_id
    """
    try:
        user_id = request.GET.get('user_id')
        
        if not user_id:
            return Response({
                'success': False,
                'error': 'user_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        modules = ModuleSequenceService.get_module_progress_list(
            user_id=user_id,
            course_id=course_id
        )
        
        return Response({
            'success': True,
            'modules': modules,
            'total_modules': len(modules)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting module progress: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def update_module_progress(request, module_id):
    """
    POST /api/trainee/module/<module_id>/progress/update/
    
    Update progress for a specific module
    Body: {
        user_id: UUID,
        completion_percentage: int (0-100),
        time_spent_minutes: int (optional, incremental)
    }
    """
    try:
        user_id = request.data.get('user_id')
        completion_percentage = request.data.get('completion_percentage', 0)
        time_spent_minutes = request.data.get('time_spent_minutes', 0)
        
        if not user_id:
            return Response({
                'success': False,
                'error': 'user_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        success = ModuleSequenceService.update_module_progress(
            user_id=user_id,
            module_id=module_id,
            completion_percentage=completion_percentage,
            time_spent_minutes=time_spent_minutes
        )
        
        if success:
            return Response({
                'success': True,
                'message': 'Module progress updated successfully',
                'completion_percentage': completion_percentage
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'error': 'Failed to update module progress'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    except Exception as e:
        logger.error(f"Error updating module progress: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def mark_module_completed(request, module_id):
    """
    POST /api/trainee/module/<module_id>/complete/
    
    Mark a module as completed and unlock next module
    Body: {
        user_id: UUID,
        time_spent_minutes: int (optional)
    }
    """
    try:
        user_id = request.data.get('user_id')
        time_spent_minutes = request.data.get('time_spent_minutes', 0)
        
        if not user_id:
            return Response({
                'success': False,
                'error': 'user_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        success = ModuleSequenceService.mark_module_completed(
            user_id=user_id,
            module_id=module_id,
            time_spent_minutes=time_spent_minutes
        )
        
        if success:
            return Response({
                'success': True,
                'message': 'Module completed and next module unlocked'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'error': 'Failed to mark module as completed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    except Exception as e:
        logger.error(f"Error marking module completed: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
