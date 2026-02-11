"""
Dashboard API view - returns user dashboard data.
Aggregates courses, tests, badges, and leaderboard info.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.db.models import Count, Q, Avg, Sum
from trainee.models import (
    Course, Test, TestAttempt,
    BadgeAssignment, Leaderboard, UserProgress, Notification, User
)
from trainee.services.learning_progress import LearningProgressService


class DashboardView(APIView):
    """Dashboard API - returns user dashboard data"""
    permission_classes = [AllowAny]

    def get(self, request):
        # Get user from request, or first trainee if not authenticated
        user_obj = None
        if request.user.is_authenticated:
            # Get the full User object from database using user_id or email
            if hasattr(request.user, 'user_id'):
                user_obj = User.objects.filter(user_id=request.user.user_id).first()
            elif hasattr(request.user, 'email'):
                user_obj = User.objects.filter(email=request.user.email).first()
        
        # Fallback to first trainee if not found
        if not user_obj:
            user_obj = User.objects.filter(primary_role='trainee').first()
        
        user_id = str(user_obj.user_id) if user_obj else 'guest'
        user_name = f"{user_obj.first_name} {user_obj.last_name}" if user_obj else 'Guest'
        user_role = user_obj.primary_role if user_obj else 'trainee'
        
        # Get dashboard data using service
        dashboard_data = LearningProgressService.get_dashboard_data(user_obj)
        
        # Get courses for display
        courses = dashboard_data['courses']
        course_stats = dashboard_data['course_stats']
        
        # If no courses from assignment/user, get ALL published courses
        if not courses:
            all_courses = Course.objects.filter(status='published')
            courses_data = []
            total = all_courses.count()
            in_progress = 0
            completed = 0
            not_started = 0
            
            for course in all_courses:
                if user_obj:
                    progress = UserProgress.objects.filter(user=user_obj, course=course).first()
                    if progress:
                        # Use the actual status field from UserProgress, not just completion percentage
                        status_text = progress.status
                        completion_rate = progress.completion_percentage
                    else:
                        status_text = 'not_started'
                        completion_rate = 0
                else:
                    status_text = 'not_started'
                    completion_rate = 0
                
                # Count statuses
                if status_text == 'in_progress':
                    in_progress += 1
                elif status_text == 'completed':
                    completed += 1
                else:
                    not_started += 1
                
                courses_data.append({
                    'course_id': str(course.course_id),
                    'id': str(course.course_id),
                    'title': course.title,
                    'description': course.description or '',
                    'status': status_text,
                    'completion_percentage': completion_rate,
                    'total_modules': course.modules.count(),
                    'duration': f"{course.estimated_duration_hours} hours" if course.estimated_duration_hours else "Unknown",
                })
            
            courses = courses_data
            course_stats = {
                'total_courses': total,
                'active_courses': in_progress,
                'completed_courses': completed,
                'not_started_courses': not_started,
            }
        
        # Get user badges
        if user_obj:
            badges = BadgeAssignment.objects.filter(user=user_obj).select_related('badge')
            badges_data = [
                {
                    'id': str(b.badge_assignment_id),
                    'name': b.badge.badge_name,
                    'description': b.badge.description or '',
                    'earned_date': b.earned_at.isoformat() if b.earned_at else None
                }
                for b in badges[:5]
            ]
        else:
            badges_data = []
        
        # Build leaderboard response
        leaderboard_data = [
            {
                'rank': dashboard_data['rank'],
                'name': user_name,
                'points': dashboard_data['total_points'],
                'badge_count': len(badges_data),
                'total_active_hours': dashboard_data['total_active_hours'],
            }
        ]
        
        # Get recent notifications
        if user_obj:
            notifications = Notification.objects.filter(user=user_obj).order_by('-created_at')[:5]
            notifications_data = [
                {
                    'id': str(n.notification_id),
                    'title': n.title or n.notification_type,
                    'message': n.message,
                    'is_read': n.status == 'read',
                    'created_at': n.created_at.isoformat()
                }
                for n in notifications
            ]
        else:
            notifications_data = []

        return Response({
            'user': {
                'id': user_id,
                'name': user_name,
                'role': user_role,
                'total_points': dashboard_data['total_points'],
                'badges_count': len(badges_data),
            },
            'courses': courses,
            'course_stats': course_stats,
            'badges': badges_data,
            'leaderboard': leaderboard_data,
            'notifications': notifications_data,
            'stats': {
                'total_active_hours': dashboard_data['total_active_hours'],
                'total_courses': course_stats['total_courses'],
                'active_courses': course_stats['active_courses'],
                'completed_courses': course_stats['completed_courses'],
                'not_started_courses': course_stats['not_started_courses'],
            }
        }, status=status.HTTP_200_OK)

