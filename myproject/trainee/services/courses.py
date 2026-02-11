"""
Trainee Course Management Views
Handles course access, enrollment, and information
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from trainee.models import User, Course, UserProgress, Enrollment
from admin.models import CourseAssignment
from trainee.services.learning_progress import LearningProgressService
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_my_courses(request):
    """
    GET /trainee/courses
    Get all courses assigned to the user with progress info
    """
    try:
        user = LearningProgressService.get_user()
        courses = LearningProgressService.get_user_courses(user)
        
        return Response({
            'success': True,
            'courses': courses,
            'count': len(courses)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.exception(f"Error fetching courses: {str(e)}")
        return Response(
            {'success': False, 'error': f'Failed to fetch courses: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_course_detail(request, course_id):
    """
    GET /trainee/course/{id}
    Get detailed information about a specific course
    """
    try:
        course = get_object_or_404(Course, course_id=course_id)
        user = LearningProgressService.get_user()
        
        # Get progress if user exists
        if user:
            try:
                progress = UserProgress.objects.get(user=user, course=course)
                completion_percentage = progress.completion_percentage
                modules_completed = progress.modules_completed
                total_modules = progress.total_modules
                started_at = progress.started_at.isoformat() if progress.started_at else None
            except UserProgress.DoesNotExist:
                completion_percentage = 0
                modules_completed = 0
                total_modules = course.modules.count()
                started_at = None
        else:
            completion_percentage = 0
            modules_completed = 0
            total_modules = course.modules.count()
            started_at = None

        # Get course assignment info
        assignment = None
        if user:
            try:
                assignment = CourseAssignment.objects.get(
                    Q(assigned_to_user=user) | Q(assigned_to_team__members__user=user),
                    course=course
                )
            except CourseAssignment.DoesNotExist:
                pass

        return Response({
            'course_id': str(course.course_id),
            'title': course.title,
            'description': course.description,
            'course_type': course.course_type,
            'is_mandatory': course.is_mandatory,
            'estimated_duration_hours': course.estimated_duration_hours,
            'passing_criteria': course.passing_criteria,
            'completion_percentage': completion_percentage,
            'modules_completed': modules_completed,
            'total_modules': total_modules,
            'started_at': started_at,
            'due_date': assignment.due_date.isoformat() if assignment and assignment.due_date else None,
            'assigned_at': assignment.assigned_at.isoformat() if assignment else None,
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def start_course(request, course_id):
    """
    POST /trainee/course/{id}/start
    Start/enroll in a course (initialize progress tracking)
    Updates status to In Progress and sets started_at timestamp
    """
    try:
        course = get_object_or_404(Course, course_id=course_id)
        user = LearningProgressService.get_user()
        
        if not user:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Start course using service
        progress = LearningProgressService.start_course(user, course)
        
        return Response({
            'success': True,
            'message': 'Course started successfully',
            'course_id': str(course_id),
            'status': 'in_progress',
            'started_at': progress.started_at.isoformat() if progress.started_at else None,
            'completion_percentage': progress.completion_percentage,
            'total_modules': progress.total_modules,
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.exception(f"Error starting course: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )

