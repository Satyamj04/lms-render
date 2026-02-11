"""
Module Progress, Quiz Results, and Leaderboard Models
"""
from django.db import models
import uuid


class ModuleProgress(models.Model):
    """Track individual module completion per user"""
    progress_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField()
    module_id = models.UUIDField()
    course_id = models.UUIDField()
    
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    
    time_spent_minutes = models.IntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_locked = models.BooleanField(default=True)
    completion_percentage = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'module_progress'
        managed = False
        unique_together = ('user_id', 'module_id')
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['module_id']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Module Progress: User {self.user_id} - Module {self.module_id}"


class QuizResult(models.Model):
    """Store quiz attempt results with detailed metrics"""
    result_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt_id = models.UUIDField(unique=True)
    user_id = models.UUIDField()
    quiz_id = models.UUIDField()
    module_id = models.UUIDField()
    course_id = models.UUIDField()
    
    total_questions = models.IntegerField(default=0)
    correct_answers = models.IntegerField(default=0)
    incorrect_answers = models.IntegerField(default=0)
    score_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    points_earned = models.IntegerField(default=0)
    max_points = models.IntegerField(default=0)
    time_taken_seconds = models.IntegerField(default=0)
    passed = models.BooleanField(default=False)
    attempt_number = models.IntegerField(default=1)
    
    submitted_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'quiz_results'
        managed = False
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['quiz_id']),
            models.Index(fields=['attempt_id']),
        ]
    
    def __str__(self):
        return f"Quiz Result: User {self.user_id} - Quiz {self.quiz_id} ({self.score_percentage}%)"


class UserLeaderboard(models.Model):
    """Individual user leaderboard with weighted scoring"""
    leaderboard_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField()
    course_id = models.UUIDField(null=True, blank=True)
    
    total_points = models.IntegerField(default=0)
    modules_completed = models.IntegerField(default=0)
    time_spent_minutes = models.IntegerField(default=0)
    correct_answers = models.IntegerField(default=0)
    total_answers = models.IntegerField(default=0)
    weighted_score = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    rank = models.IntegerField(null=True, blank=True)
    
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'user_leaderboard'
        managed = False
        unique_together = ('user_id', 'course_id')
        indexes = [
            models.Index(fields=['course_id']),
            models.Index(fields=['rank']),
            models.Index(fields=['-weighted_score']),
        ]
        ordering = ['rank', '-weighted_score']
    
    def __str__(self):
        return f"Leaderboard: User {self.user_id} - Rank {self.rank}"


class TeamLeaderboard(models.Model):
    """Team leaderboard based on average completion"""
    team_leaderboard_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team_id = models.UUIDField()
    course_id = models.UUIDField(null=True, blank=True)
    
    total_members = models.IntegerField(default=0)
    average_completion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    total_points = models.IntegerField(default=0)
    weighted_score = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    rank = models.IntegerField(null=True, blank=True)
    
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'team_leaderboard'
        managed = False
        unique_together = ('team_id', 'course_id')
        indexes = [
            models.Index(fields=['course_id']),
            models.Index(fields=['rank']),
            models.Index(fields=['-weighted_score']),
        ]
        ordering = ['rank', '-weighted_score']
    
    def __str__(self):
        return f"Team Leaderboard: Team {self.team_id} - Rank {self.rank}"
