"""
Serializers for dashboard data.
"""
from rest_framework import serializers
from trainee.models import UserProgress, BadgeAssignment, Leaderboard, Notification


class DashboardProgressSerializer(serializers.Serializer):
    """Dashboard progress overview"""
    pending_courses = serializers.IntegerField()
    in_progress_courses = serializers.IntegerField()
    completed_courses = serializers.IntegerField()
    total_points = serializers.IntegerField()
    average_score = serializers.FloatField()


class DashboardBadgeSerializer(serializers.ModelSerializer):
    """Dashboard badge info"""
    badge_name = serializers.CharField(source='badge.badge_name', read_only=True)
    badge_icon = serializers.CharField(source='badge.badge_icon_url', read_only=True)

    class Meta:
        model = BadgeAssignment
        fields = ['badge_assignment_id', 'badge_name', 'badge_icon', 'earned_at']


class DashboardLeaderboardSerializer(serializers.ModelSerializer):
    """Dashboard leaderboard entry"""
    user_name = serializers.CharField(source='user.first_name', read_only=True)

    class Meta:
        model = Leaderboard
        fields = ['user_name', 'points', 'rank']


class DashboardNotificationSerializer(serializers.ModelSerializer):
    """Dashboard notifications"""
    class Meta:
        model = Notification
        fields = [
            'notification_id', 'title', 'message', 'notification_type',
            'priority', 'status', 'created_at'
        ]


class DashboardSerializer(serializers.Serializer):
    """Complete dashboard data"""
    progress = DashboardProgressSerializer()
    recent_badges = DashboardBadgeSerializer(many=True, read_only=True)
    leaderboard_position = DashboardLeaderboardSerializer(read_only=True)
    recent_notifications = DashboardNotificationSerializer(many=True, read_only=True)
