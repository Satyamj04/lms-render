"""
Quiz Results API Views
Endpoints for processing quiz attempts from test_responses table
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from ..services.quiz_results_service import QuizResultsService
import logging

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
def process_quiz_attempt(request):
    """
    POST /api/trainee/quiz/process-attempt/
    
    Process a quiz attempt from test_responses table and calculate results
    Body: {
        attempt_id: UUID (from test_attempts table),
        user_id: UUID,
        quiz_id: UUID,
        module_id: UUID,
        course_id: UUID,
        time_taken_seconds: int (optional)
    }
    """
    try:
        attempt_id = request.data.get('attempt_id')
        user_id = request.data.get('user_id')
        quiz_id = request.data.get('quiz_id')
        module_id = request.data.get('module_id')
        course_id = request.data.get('course_id')
        time_taken_seconds = request.data.get('time_taken_seconds', 0)
        
        if not all([attempt_id, user_id, quiz_id, module_id, course_id]):
            return Response({
                'success': False,
                'error': 'Missing required fields'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        results = QuizResultsService.process_quiz_attempt(
            attempt_id=attempt_id,
            user_id=user_id,
            quiz_id=quiz_id,
            module_id=module_id,
            course_id=course_id,
            time_taken_seconds=time_taken_seconds
        )
        
        if results:
            return Response({
                'success': True,
                'results': results
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'error': 'No responses found for this attempt'
            }, status=status.HTTP_404_NOT_FOUND)
        
    except Exception as e:
        logger.error(f"Error processing quiz attempt: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_quiz_results(request):
    """
    GET /api/trainee/quiz/results/
    
    Get quiz results for a user
    Query params:
        - user_id: UUID (required)
        - quiz_id: UUID (optional)
        - course_id: UUID (optional)
    """
    try:
        user_id = request.GET.get('user_id')
        quiz_id = request.GET.get('quiz_id', None)
        course_id = request.GET.get('course_id', None)
        
        if not user_id:
            return Response({
                'success': False,
                'error': 'user_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        results = QuizResultsService.get_quiz_results(
            user_id=user_id,
            quiz_id=quiz_id,
            course_id=course_id
        )
        
        return Response({
            'success': True,
            'results': results,
            'total_attempts': len(results)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting quiz results: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_best_attempt(request, quiz_id):
    """
    GET /api/trainee/quiz/<quiz_id>/best-attempt/
    
    Get the best scoring attempt for a user on a specific quiz
    Query params: user_id
    """
    try:
        user_id = request.GET.get('user_id')
        
        if not user_id:
            return Response({
                'success': False,
                'error': 'user_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        best_attempt = QuizResultsService.get_best_attempt(
            user_id=user_id,
            quiz_id=quiz_id
        )
        
        if best_attempt:
            return Response({
                'success': True,
                'best_attempt': best_attempt
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'error': 'No attempts found'
            }, status=status.HTTP_404_NOT_FOUND)
        
    except Exception as e:
        logger.error(f"Error getting best attempt: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_quiz_statistics(request, quiz_id):
    """
    GET /api/trainee/quiz/<quiz_id>/statistics/
    
    Get aggregate statistics for a quiz across all attempts
    """
    try:
        statistics = QuizResultsService.get_quiz_statistics(quiz_id)
        
        if statistics:
            return Response({
                'success': True,
                'statistics': statistics
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'error': 'No statistics available'
            }, status=status.HTTP_404_NOT_FOUND)
        
    except Exception as e:
        logger.error(f"Error getting quiz statistics: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def validate_quiz_attempt(request, attempt_id):
    """
    GET /api/trainee/quiz/validate/<attempt_id>/
    
    Get detailed validation results for a quiz attempt
    """
    try:
        validation_results = QuizResultsService.validate_quiz_answers_server_side(
            quiz_id=None,  # Not needed since we're reading from test_responses
            attempt_id=attempt_id
        )
        
        return Response({
            'success': True,
            'validation_results': validation_results,
            'total_questions': len(validation_results)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error validating quiz attempt: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
