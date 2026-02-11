"""
Comprehensive Candidate (Trainee) API endpoints for the LMS.
Provides all necessary functionality for candidates to:
- View assigned courses
- Update profile information
- Track progress
- View assessments
- Check leaderboard rankings
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q, F, Count, Avg
from django.db import models
from trainee.models import (
    User, Course, UserProgress,
    Test, TestAttempt, Leaderboard,
    BadgeAssignment, Module, ModuleCompletion
)
from admin.models import CourseAssignment
from trainee.serializers.course import CourseSerializer
from django.utils import timezone


@api_view(['GET'])
@permission_classes([AllowAny])
def get_candidate_courses(request):
    """
    Get all courses assigned to the candidate (trainee)
    
    Returns:
    - List of assigned courses with details
    - Progress information for each course
    """
    try:
        user = User.objects.get(email=request.user.email)
        if user.primary_role != 'trainee':
            return Response(
                {'error': 'This endpoint is for trainees only'},
                status=status.HTTP_403_FORBIDDEN
            )
    except User.DoesNotExist:
        return Response(
            {'error': 'User profile not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Get all course assignments for this user
    assignments = CourseAssignment.objects.filter(
        assigned_to_user=user
    ).select_related('course').order_by('-assigned_at')
    
    courses_list = []
    for assignment in assignments:
        course = assignment.course
        
        # Get progress for this course
        progress = UserProgress.objects.filter(
            user=user,
            course=course
        ).first()
        
        # Get module count
        modules_count = Module.objects.filter(course=course).count()
        modules_completed = ModuleCompletion.objects.filter(
            user=user,
            module__course=course,
            status='completed'
        ).count()
        
        course_data = {
            'course_id': str(course.course_id),
            'title': course.title,
            'description': course.description,
            'status': 'in_progress',
            'completion_status': 'in_progress',
            'progress_percentage': progress.completion_percentage if progress else 0,
            'lessons_completed': modules_completed,
            'total_lessons': modules_count,
            'duration_hours': course.estimated_duration_hours or 0,
            'assignment_date': assignment.assigned_at.isoformat() if assignment.assigned_at else None,
            'due_date': assignment.due_date.isoformat() if assignment.due_date else None,
            'started_at': progress.started_at.isoformat() if progress and progress.started_at else None,
            'completed_at': progress.completed_at.isoformat() if progress and progress.completed_at else None,
        }
        courses_list.append(course_data)
    
    return Response({
        'success': True,
        'count': len(courses_list),
        'courses': courses_list
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_candidate_profile(request):
    """
    Get complete candidate profile information
    """
    try:
        user = User.objects.get(email=request.user.email)
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Get leaderboard info
    leaderboard = Leaderboard.objects.filter(
        scope='global',
        user=user
    ).first()
    
    # Get badges
    badges = BadgeAssignment.objects.filter(user=user).count()
    
    data = {
        'user_id': str(user.user_id),
        'first_name': user.first_name,
        'last_name': user.last_name,
        'full_name': f"{user.first_name} {user.last_name}",
        'email': user.email,
        'role': user.primary_role,
        'status': user.status,
        'profile_image_url': user.profile_image_url,
        'points': leaderboard.points if leaderboard else 0,
        'rank': leaderboard.rank if leaderboard else 0,
        'badges_earned': badges,
        'created_at': user.created_at.isoformat(),
        'last_login': user.last_login.isoformat() if user.last_login else None,
    }
    
    return Response(data, status=status.HTTP_200_OK)


@api_view(['PUT'])
@permission_classes([AllowAny])
def update_candidate_profile(request):
    """
    Update candidate profile information
    
    Allows updating:
    - first_name
    - last_name
    - profile_image_url
    """
    try:
        user = User.objects.get(email=request.user.email)
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Update allowed fields
    if 'first_name' in request.data:
        user.first_name = request.data['first_name'].strip()
    
    if 'last_name' in request.data:
        user.last_name = request.data['last_name'].strip()
    
    if 'profile_image_url' in request.data:
        user.profile_image_url = request.data['profile_image_url'].strip()
    
    # Save to database
    user.save()
    
    return Response({
        'success': True,
        'message': 'Profile updated successfully',
        'user': {
            'user_id': str(user.user_id),
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'profile_image_url': user.profile_image_url,
        }
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_candidate_assessments(request):
    """
    Get all tests/assessments assigned to or available for the candidate
    """
    try:
        user = User.objects.get(email=request.user.email)
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Get courses assigned to user
    assigned_courses = CourseAssignment.objects.filter(
        assigned_to_user=user
    ).values_list('course', flat=True)
    
    # Get tests for those courses
    tests = Test.objects.filter(
        course_id__in=assigned_courses
    ).select_related('course').order_by('-created_at')
    
    assessments_list = []
    for test in tests:
        # Check if user has attempted
        attempt = TestAttempt.objects.filter(
            test=test,
            user=user
        ).first()
        
        assessments_list.append({
            'assessment_id': str(test.test_id),
            'title': test.title,
            'description': test.description,
            'assessment_type': test.test_type or 'quiz',
            'total_points': test.points_possible or 100,
            'passing_score': test.passing_score or 70,
            'course': test.course.title if test.course else None,
            'status': 'submitted' if attempt else 'pending',
            'score': attempt.score if attempt else None,
            'submitted_at': attempt.submission_date.isoformat() if attempt and hasattr(attempt, 'submission_date') else None,
        })
    
    return Response({
        'success': True,
        'count': len(assessments_list),
        'assessments': assessments_list
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_candidate_progress(request):
    """
    Get candidate's learning progress across all courses
    """
    try:
        user = User.objects.get(email=request.user.email)
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Get all progress records
    progress_records = UserProgress.objects.filter(
        user=user
    ).select_related('course').order_by('-updated_at')
    
    progress_list = []
    total_progress = 0
    total_courses = 0
    
    for progress in progress_records:
        total_progress += progress.completion_percentage
        total_courses += 1
        
        progress_list.append({
            'course_id': str(progress.course.course_id),
            'course_name': progress.course.title,
            'progress_percentage': progress.completion_percentage,
            'status': progress.status,
            'lessons_completed': progress.lessons_completed,
            'total_lessons': progress.total_lessons,
            'time_spent_hours': progress.time_spent_hours,
            'started_at': progress.started_at.isoformat() if progress.started_at else None,
            'completed_at': progress.completed_at.isoformat() if progress.completed_at else None,
        })
    
    # Calculate overall progress
    overall_progress = (total_progress / total_courses) if total_courses > 0 else 0
    
    return Response({
        'success': True,
        'overall_progress': round(overall_progress, 2),
        'total_courses': total_courses,
        'progress': progress_list
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
@api_view(['GET'])
@permission_classes([AllowAny])
def get_candidate_leaderboard(request):
    """
    Get candidate's leaderboard ranking with all trainees
    Shows all trainees even if they haven't earned points yet
    """
    try:
        current_user = User.objects.get(email=request.user.email)
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        # Get user's leaderboard entry if exists
        user_leaderboard = Leaderboard.objects.filter(
            scope='global',
            user=current_user
        ).first()
        
        user_rank = user_leaderboard.rank if user_leaderboard else None
        user_points = user_leaderboard.points if user_leaderboard else 0
        
        # Get all leaderboard entries
        leaderboard_entries = list(
            Leaderboard.objects.filter(
                scope='global'
            ).select_related('user').order_by('-points', 'rank')
        )
        
        # Create set of leaderboard user IDs
        leaderboard_user_ids = {entry.user.user_id for entry in leaderboard_entries}
        
        # Get all trainees
        all_trainees = User.objects.filter(
            primary_role='trainee'
        ).order_by('-created_at')
        
        top_list = []
        current_rank = 1
        
        # Add leaderboard entries first
        for leaderboard in leaderboard_entries:
            trainee_name = f"{leaderboard.user.first_name} {leaderboard.user.last_name}".strip()
            top_list.append({
                'rank': current_rank,
                'user_id': str(leaderboard.user.user_id),
                'name': trainee_name if trainee_name else leaderboard.user.email,
                'points': leaderboard.points,
                'email': leaderboard.user.email,
                'is_current_user': leaderboard.user.user_id == current_user.user_id
            })
            current_rank += 1
        
        # Add remaining trainees not in leaderboard
        for trainee in all_trainees:
            if trainee.user_id not in leaderboard_user_ids:
                trainee_name = f"{trainee.first_name} {trainee.last_name}".strip()
                top_list.append({
                    'rank': current_rank,
                    'user_id': str(trainee.user_id),
                    'name': trainee_name if trainee_name else trainee.email,
                    'points': 0,
                    'email': trainee.email,
                    'is_current_user': trainee.user_id == current_user.user_id
                })
                current_rank += 1
        
        return Response({
            'success': True,
            'user_rank': user_rank,
            'user_points': user_points,
            'top_performers': top_list
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        import traceback
        print(f"Candidate Leaderboard Error: {str(e)}")
        print(traceback.format_exc())
        return Response(
            {'error': 'Failed to load leaderboard: ' + str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )



@api_view(['GET'])
@permission_classes([AllowAny])
def get_candidate_dashboard(request):
    """
    Get complete candidate dashboard data
    """
    try:
        user = User.objects.get(email=request.user.email)
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Get courses
    assignments = CourseAssignment.objects.filter(assigned_to_user=user)
    total_courses = assignments.count()
    active_courses = assignments.filter(status='in_progress').count()
    completed_courses = assignments.filter(completion_status='completed').count()
    
    # Get leaderboard
    leaderboard = Leaderboard.objects.filter(
        scope='global',
        user=user
    ).first()
    
    # Get assessments
    assigned_courses = assignments.values_list('course', flat=True)
    pending_assessments = AssessmentSubmission.objects.filter(
        trainee=user,
        status__in=['draft', 'submitted']
    ).count()
    
    # Get badges
    badges = BadgeAssignment.objects.filter(user=user).count()
    
    # Calculate overall progress
    progress_records = UserProgress.objects.filter(user=user)
    overall_progress = 0
    if progress_records.exists():
        overall_progress = progress_records.aggregate(
            avg=models.Avg('completion_percentage')
        )['avg'] or 0
    
    return Response({
        'success': True,
        'user': {
            'name': f"{user.first_name} {user.last_name}",
            'email': user.email,
            'role': user.primary_role,
        },
        'overview': {
            'total_courses': total_courses,
            'active_courses': active_courses,
            'completed_courses': completed_courses,
            'pending_assessments': pending_assessments,
            'overall_progress': round(overall_progress, 2),
        },
        'ranking': {
            'rank': leaderboard.rank if leaderboard else 0,
            'points': leaderboard.points if leaderboard else 0,
            'badges': badges,
        }
    }, status=status.HTTP_200_OK)
