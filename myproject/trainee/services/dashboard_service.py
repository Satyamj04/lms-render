"""
Dashboard service - aggregates user dashboard data from multiple models.
"""
from django.db.models import Sum, Count, Avg, Q
from trainee.models import (
    CourseAssignment, BadgeAssignment, Leaderboard,
    UserProgress, Notification
)

def get_dashboard_data(user):
    """Get aggregated dashboard data for a user"""
    
    # Get pending course assignments
    pending_assignments = CourseAssignment.objects.filter(
        Q(assigned_to_user=user) |
        Q(assigned_to_team__members__user=user),
        due_date__isnull=False
    ).count()

    # Get average progress across courses
    progress = UserProgress.objects.filter(user=user).aggregate(
        avg=Avg('completion_percentage')
    )['avg'] or 0

    # Get total points from leaderboard
    leaderboard_entry = Leaderboard.objects.filter(
        scope='global',
        user=user
    ).first()
    points = leaderboard_entry.points if leaderboard_entry else 0

    # Get total badges
    badges = BadgeAssignment.objects.filter(user=user).count()

    # Get unread notifications
    unread_notifications = Notification.objects.filter(
        user=user,
        status='unread'
    ).count()

    return {
        "pending_tasks": pending_assignments,
        "progress": round(progress, 2),
        "points": points,
        "badges": badges,
        "unread_notifications": unread_notifications,
    }
