"""
Trainer app models - Complete integration from standalone trainer backend
Includes comprehensive course management, units, enrollments, quizzes, assignments, and more
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


class Profile(models.Model):
    """User profile - Maps to PostgreSQL users table per finalized schema"""
    ROLE_CHOICES = [('admin','admin'), ('trainer','trainer'), ('manager','manager'), ('trainee','trainee')]
    STATUS_CHOICES = [('active','active'), ('inactive','inactive'), ('archived','archived')]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='user_id')
    first_name = models.CharField(max_length=100, db_column='first_name')
    last_name = models.CharField(max_length=100, db_column='last_name')
    email = models.EmailField(unique=True, db_column='email')
    password = models.CharField(max_length=255, db_column='password_hash')
    
    primary_role = models.CharField(
        max_length=50,
        db_column='primary_role',
        choices=ROLE_CHOICES,
        default='trainee'
    )
    status = models.CharField(
        max_length=20,
        db_column='status',
        choices=STATUS_CHOICES,
        default='active'
    )
    profile_image_url = models.TextField(blank=True, null=True, db_column='profile_image_url')
    last_login = models.DateTimeField(blank=True, null=True, db_column='last_login')
    created_at = models.DateTimeField(default=timezone.now, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'users'
        managed = False  # Managed by admin.UserProfile
        managed = False  # Managed by admin.UserProfile

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def username(self):
        """Computed property for backward compatibility"""
        return f"{self.first_name.lower()}.{self.last_name.lower()}"
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}" or self.email

    # Note: managed = False because this table is managed by admin.UserProfile


class Course(models.Model):
    """Maps to PostgreSQL courses table - Per finalized schema"""
    
    COURSE_TYPE_CHOICES = [
        ('self_paced', 'Self Paced'),
        ('instructor_led', 'Instructor Led'),
        ('blended', 'Blended'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='course_id')
    title = models.CharField(max_length=500, db_column='title')
    description = models.TextField(blank=True, null=True, db_column='description')
    about = models.TextField(blank=True, null=True, db_column='about')
    outcomes = models.TextField(blank=True, null=True, db_column='outcomes')
    course_type = models.CharField(
        max_length=30, 
        default='self_paced', 
        choices=COURSE_TYPE_CHOICES,
        db_column='course_type'
    )
    status = models.CharField(
        max_length=20, 
        default='draft', 
        choices=STATUS_CHOICES,
        db_column='status'
    )
    is_mandatory = models.BooleanField(default=False, db_column='is_mandatory')
    estimated_duration_hours = models.IntegerField(blank=True, null=True, db_column='estimated_duration_hours')
    passing_criteria = models.IntegerField(default=70, db_column='passing_criteria')
    
    created_by = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='created_courses', db_column='created_by')
    created_at = models.DateTimeField(default=timezone.now, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'courses'
        managed = True
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title


class Unit(models.Model):
    """Mapped to DDL `modules` table - Module/Unit level metadata"""
    MODULE_TYPES = [
        ('text', 'Text'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('presentation', 'Presentation'),
        ('scorm', 'SCORM'),
        ('xapi', 'xAPI'),
        ('quiz', 'Quiz'),
        ('test', 'Test'),
        ('assignment', 'Assignment'),
        ('survey', 'Survey'),
        ('page', 'Page'),
        ('mixed', 'Mixed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='module_id')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='units', db_column='course_id')
    module_type = models.CharField(max_length=30, choices=MODULE_TYPES, db_column='module_type')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    sequence_order = models.IntegerField(default=0, db_column='sequence_order')
    is_mandatory = models.BooleanField(default=True, db_column='is_mandatory')
    estimated_duration_minutes = models.IntegerField(blank=True, null=True, db_column='estimated_duration_minutes')
    video_count = models.IntegerField(default=0, db_column='video_count')
    has_quizzes = models.BooleanField(default=False, db_column='has_quizzes')
    created_at = models.DateTimeField(default=timezone.now, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'modules'
        managed = True
        ordering = ['course', 'sequence_order']

    @property
    def order(self):
        """Backward-compatible alias for `sequence_order`"""
        return self.sequence_order

    @order.setter
    def order(self, value):
        self.sequence_order = value


class VideoUnit(models.Model):
    """Video-specific unit content"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    unit = models.OneToOneField(Unit, on_delete=models.CASCADE, related_name='video_details', db_column='unit_id')
    video_url = models.CharField(max_length=500, blank=True, null=True, db_column='video_url')
    video_storage_path = models.CharField(max_length=500, blank=True, null=True, db_column='video_storage_path')
    duration = models.IntegerField(default=0, db_column='duration')
    completion_type = models.CharField(
        max_length=20,
        choices=[('full', 'Full'), ('percentage', 'Percentage')],
        default='full',
        db_column='completion_type'
    )
    required_watch_percentage = models.IntegerField(default=100, db_column='required_watch_percentage')
    allow_skip = models.BooleanField(default=False, db_column='allow_skip')
    allow_rewind = models.BooleanField(default=True, db_column='allow_rewind')

    class Meta:
        db_table = 'video_units'
        managed = True


class AudioUnit(models.Model):
    """Audio-specific unit content"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    unit = models.OneToOneField(Unit, on_delete=models.CASCADE, related_name='audio_details', db_column='unit_id')
    audio_url = models.CharField(max_length=500, blank=True, null=True, db_column='audio_url')
    audio_storage_path = models.CharField(max_length=500, blank=True, null=True, db_column='audio_storage_path')
    duration = models.IntegerField(default=0, db_column='duration')

    class Meta:
        db_table = 'audio_units'
        managed = True


class PresentationUnit(models.Model):
    """Presentation-specific unit content"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    unit = models.OneToOneField(Unit, on_delete=models.CASCADE, related_name='presentation_details', db_column='unit_id')
    file_url = models.CharField(max_length=500, blank=True, null=True, db_column='file_url')
    file_storage_path = models.CharField(max_length=500, blank=True, null=True, db_column='file_storage_path')
    slide_count = models.IntegerField(default=0, db_column='slide_count')

    class Meta:
        db_table = 'presentation_units'
        managed = True


class TextUnit(models.Model):
    """Text-specific unit content"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    unit = models.OneToOneField(Unit, on_delete=models.CASCADE, related_name='text_details', db_column='unit_id')
    content = models.TextField(blank=True, null=True, db_column='content')

    class Meta:
        db_table = 'text_units'
        managed = True


class PageUnit(models.Model):
    """Page-specific unit content with JSON support"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    unit = models.OneToOneField(Unit, on_delete=models.CASCADE, related_name='page_details', db_column='unit_id')
    content = models.JSONField(default=list, db_column='content')

    class Meta:
        db_table = 'page_units'
        managed = True


class Quiz(models.Model):
    """Quiz unit - Maps to quizzes table"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='quizzes', db_column='unit_id')
    time_limit = models.IntegerField(blank=True, null=True, db_column='time_limit')
    passing_score = models.IntegerField(default=70, db_column='passing_score')
    attempts_allowed = models.IntegerField(default=1, db_column='attempts_allowed')
    show_answers = models.BooleanField(default=False, db_column='show_answers')
    randomize_questions = models.BooleanField(default=False, db_column='randomize_questions')
    mandatory_completion = models.BooleanField(default=False, db_column='mandatory_completion')

    class Meta:
        db_table = 'quizzes'
        managed = True


class Question(models.Model):
    """Quiz questions - Maps to questions table"""
    QUESTION_TYPES = [
        ('multiple_choice', 'Multiple Choice'),
        ('multiple_answer', 'Multiple Answer'),
        ('true_false', 'True/False'),
        ('short_answer', 'Short Answer'),
        ('essay', 'Essay'),
        ('fill_blank', 'Fill in the Blank'),
        ('matching', 'Matching'),
        ('ordering', 'Ordering'),
        ('free_text', 'Free Text'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions', db_column='quiz_id')
    type = models.CharField(max_length=30, choices=QUESTION_TYPES, db_column='type')
    text = models.TextField(db_column='text')
    options = models.JSONField(default=list, db_column='options')
    correct_answer = models.JSONField(blank=True, null=True, db_column='correct_answer')
    points = models.IntegerField(default=1, db_column='points')
    order = models.IntegerField(default=0, db_column='order')

    class Meta:
        db_table = 'questions'
        managed = True
        ordering = ['quiz', 'order']


class Assignment(models.Model):
    """Assignment unit - Maps to assignments table"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='assignment_id')
    unit = models.OneToOneField(Unit, on_delete=models.CASCADE, related_name='assignment_details', db_column='module_id')
    title = models.CharField(max_length=255, db_column='title')
    description = models.TextField(blank=True, null=True, db_column='description')
    assignment_type = models.CharField(max_length=50, blank=True, null=True, db_column='assignment_type')
    evaluation_method = models.CharField(max_length=50, blank=True, null=True, db_column='evaluation_method')
    course_id = models.UUIDField(blank=True, null=True, db_column='course_id')
    due_date = models.DateTimeField(blank=True, null=True, db_column='due_date')
    max_attempts = models.IntegerField(blank=True, null=True, db_column='max_attempts')
    points_possible = models.IntegerField(blank=True, null=True, db_column='points_possible')
    mandatory_completion = models.BooleanField(default=False, db_column='is_mandatory')
    created_by = models.UUIDField(default=uuid.uuid4, db_column='created_by')
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')
    deleted_at = models.DateTimeField(blank=True, null=True, db_column='deleted_at')
    version = models.IntegerField(blank=True, null=True, db_column='version')

    class Meta:
        db_table = 'assignments'
        managed = True


class ScormPackage(models.Model):
    """SCORM/xAPI package - Maps to scorm_packages table"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='scorm_package_id')
    unit = models.OneToOneField(Unit, on_delete=models.CASCADE, related_name='scorm_details', db_column='module_id')
    package_type = models.CharField(
        max_length=20,
        choices=[('scorm_1_2', 'SCORM 1.2'), ('scorm_2004', 'SCORM 2004'), ('xapi', 'xAPI')],
        blank=True,
        null=True,
        db_column='package_type'
    )
    file_url = models.URLField(blank=True, null=True, db_column='file_url')
    file_storage_path = models.CharField(max_length=500, blank=True, null=True, db_column='file_storage_path')
    version = models.CharField(max_length=50, blank=True, null=True, db_column='version')
    completion_tracking = models.BooleanField(default=True, db_column='completion_tracking')
    score_tracking = models.BooleanField(default=True, db_column='score_tracking')

    class Meta:
        db_table = 'scorm_packages'
        managed = True


class Survey(models.Model):
    """Survey unit - Maps to surveys table"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='survey_id')
    unit = models.OneToOneField(Unit, on_delete=models.CASCADE, related_name='survey_details', db_column='module_id')
    questions = models.JSONField(default=list, db_column='questions')
    allow_anonymous = models.BooleanField(default=False, db_column='allow_anonymous')

    class Meta:
        db_table = 'surveys'
        managed = True


class Enrollment(models.Model):
    """Learner enrollments in courses"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments', db_column='course_id')
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='enrollments', db_column='user_id')
    assigned_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_enrollments', db_column='assigned_by')
    status = models.CharField(
        max_length=20,
        choices=[('assigned', 'Assigned'), ('in_progress', 'In Progress'), ('completed', 'Completed')],
        default='assigned',
        db_column='status'
    )
    progress_percentage = models.IntegerField(default=0, db_column='progress_percentage')
    assigned_at = models.DateTimeField(default=timezone.now, db_column='assigned_at')
    started_at = models.DateTimeField(blank=True, null=True, db_column='started_at')
    completed_at = models.DateTimeField(blank=True, null=True, db_column='completed_at')

    class Meta:
        db_table = 'enrollments'
        managed = True
        unique_together = ['course', 'user']


class UnitProgress(models.Model):
    """Track learner progress per unit/module"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='completion_id')
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='unit_progress_records', db_column='user_id')
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='progress', db_column='module_id')
    completion_percentage = models.IntegerField(default=0, db_column='completion_percentage')
    is_completed = models.BooleanField(default=False, db_column='is_completed')
    time_spent_minutes = models.IntegerField(default=0, db_column='time_spent_minutes')
    completed_at = models.DateTimeField(blank=True, null=True, db_column='completed_at')
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'module_completions'
        managed = True
        unique_together = ['user', 'unit']


class AssignmentSubmission(models.Model):
    """Track assignment submissions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='submission_id')
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions', db_column='assignment_id')
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='assignment_submissions', db_column='user_id')
    submission_text = models.TextField(blank=True, null=True, db_column='submission_text')
    submission_file_url = models.URLField(blank=True, null=True, db_column='submission_files')
    score = models.IntegerField(blank=True, null=True, db_column='score')
    feedback = models.TextField(blank=True, null=True, db_column='feedback')
    status = models.CharField(
        max_length=20,
        choices=[('submitted', 'Submitted'), ('graded', 'Graded')],
        default='submitted',
        db_column='status'
    )
    submitted_at = models.DateTimeField(default=timezone.now, db_column='submitted_at')
    graded_at = models.DateTimeField(blank=True, null=True, db_column='graded_at')
    graded_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name='graded_submissions', db_column='graded_by')

    class Meta:
        db_table = 'assignment_submissions'
        managed = True


class QuizAttempt(models.Model):
    """Track simple quiz attempts - stores completion, score, and answers"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts', db_column='quiz_id')
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='quiz_attempts', db_column='user_id')
    score = models.IntegerField(blank=True, null=True, db_column='score')
    passed = models.BooleanField(blank=True, null=True, db_column='passed')
    answers = models.JSONField(blank=True, null=True, db_column='answers')
    started_at = models.DateTimeField(blank=True, null=True, db_column='started_at')
    completed_at = models.DateTimeField(blank=True, null=True, db_column='completed_at')

    class Meta:
        db_table = 'quiz_attempts'
        managed = True


class TestAttempt(models.Model):
    """Track full test/quiz attempts with grading workflow"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='attempt_id')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='test_attempts', db_column='test_id')
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='test_attempts', db_column='user_id')
    attempt_number = models.IntegerField(db_column='attempt_number')
    started_at = models.DateTimeField(blank=True, null=True, db_column='started_at')
    submitted_at = models.DateTimeField(blank=True, null=True, db_column='submitted_at')
    time_spent_minutes = models.IntegerField(blank=True, null=True, db_column='time_spent_minutes')
    status = models.CharField(max_length=50, blank=True, null=True, db_column='status')
    score = models.IntegerField(blank=True, null=True, db_column='score')
    points_earned = models.IntegerField(blank=True, null=True, db_column='points_earned')
    passed = models.BooleanField(blank=True, null=True, db_column='passed')
    graded_by = models.UUIDField(blank=True, null=True, db_column='graded_by')
    graded_at = models.DateTimeField(blank=True, null=True, db_column='graded_at')
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'test_attempts'
        managed = True


class Leaderboard(models.Model):
    """Learner leaderboard - individual and course-level"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='leaderboard_id')
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='leaderboard_entries', db_column='user_id')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='leaderboard_entries', blank=True, null=True, db_column='scope_id')
    total_points = models.IntegerField(default=0, db_column='points')
    completed_units = models.IntegerField(default=0, db_column='completed_units')
    quiz_score_total = models.IntegerField(default=0, db_column='quiz_score_total')
    activity_points = models.IntegerField(default=0, db_column='activity_points')
    rank = models.IntegerField(default=0, db_column='rank')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'leaderboard'
        managed = True
        unique_together = ['user', 'course']


class Team(models.Model):
    """Team management"""
    team_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='team_id')
    team_name = models.CharField(max_length=255, unique=True, db_column='team_name')
    description = models.TextField(blank=True, null=True, db_column='description')
    status = models.CharField(max_length=20, default='active', db_column='status')
    # Note: manager_id and created_by columns don't exist in database - removed
    created_at = models.DateTimeField(default=timezone.now, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'teams'
        managed = False  # Managed by admin.Team


class TeamMember(models.Model):
    """Team membership"""
    team = models.ForeignKey(Team, on_delete=models.CASCADE, db_column='team_id', primary_key=True, related_name='members')
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, db_column='user_id')
    is_primary_team = models.BooleanField(default=True, db_column='is_primary_team')
    assigned_at = models.DateTimeField(default=timezone.now, db_column='assigned_at')
    assigned_by = models.CharField(max_length=255, blank=True, null=True, db_column='assigned_by')

    class Meta:
        db_table = 'team_members'
        managed = False  # Managed by admin.TeamMember
        unique_together = ['team', 'user']


# TeamLeaderboard model removed - uses same 'leaderboard' table as Leaderboard model above
# This was causing Django migration conflicts (can't have 2 models per table in same app)
# To query team leaderboard data, use: Leaderboard.objects.filter(team__isnull=False)
# The 'leaderboard' table will still be created by the Leaderboard model


class MediaMetadata(models.Model):
    """Media file metadata and storage tracking"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='media_id')
    storage_path = models.CharField(max_length=500, unique=True, db_column='storage_path')
    file_name = models.CharField(max_length=255, db_column='file_name')
    file_type = models.CharField(max_length=50, db_column='file_type')
    file_size = models.BigIntegerField(blank=True, null=True, db_column='file_size')
    mime_type = models.CharField(max_length=100, blank=True, null=True, db_column='mime_type')
    duration = models.IntegerField(blank=True, null=True, db_column='duration')
    width = models.IntegerField(blank=True, null=True, db_column='width')
    height = models.IntegerField(blank=True, null=True, db_column='height')
    
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='media_files', blank=True, null=True, db_column='unit_id')
    uploaded_by = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='uploaded_media', db_column='uploaded_by')
    uploaded_at = models.DateTimeField(default=timezone.now, db_column='uploaded_at')

    class Meta:
        db_table = 'media_metadata'
        managed = True


class Notification(models.Model):
    """System notifications for users"""
    NOTIFICATION_TYPE_CHOICES = [
        ('assignment', 'Assignment'),
        ('test', 'Test'),
        ('badge', 'Badge'),
        ('deadline', 'Deadline'),
        ('course', 'Course'),
        ('grade', 'Grade'),
        ('system', 'System'),
        ('reminder', 'Reminder'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    STATUS_CHOICES = [
        ('unread', 'Unread'),
        ('read', 'Read'),
        ('archived', 'Archived'),
    ]
    
    SENT_VIA_CHOICES = [
        ('in_app', 'In App'),
        ('email', 'Email'),
        ('both', 'Both'),
    ]

    notification_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='notification_id')
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='notifications', db_column='user_id')
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPE_CHOICES, db_column='notification_type')
    title = models.CharField(max_length=500, blank=True, null=True, db_column='title')
    message = models.TextField(db_column='message')
    link_url = models.TextField(blank=True, null=True, db_column='link_url')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal', db_column='priority')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unread', db_column='status')
    sent_via = models.CharField(max_length=30, choices=SENT_VIA_CHOICES, default='in_app', db_column='sent_via')
    read_at = models.DateTimeField(blank=True, null=True, db_column='read_at')
    created_at = models.DateTimeField(default=timezone.now, db_column='created_at')

    class Meta:
        db_table = 'notifications'
        managed = True
        ordering = ['-created_at']

    def mark_as_read(self):
        """Mark notification as read"""
        if self.status == 'unread':
            self.status = 'read'
            self.read_at = timezone.now()
            self.save()

class ModuleSequencing(models.Model):
    """Module sequencing and prerequisite rules"""
    sequence_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='sequence_id')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='module_sequencing', db_column='course_id')
    module = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='sequencing', db_column='module_id')
    preceding_module = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='+', blank=True, null=True, db_column='preceding_module_id')
    drip_feed_rule = models.CharField(max_length=30, default='none', db_column='drip_feed_rule')
    drip_feed_delay_days = models.IntegerField(default=0, db_column='drip_feed_delay_days')
    prerequisite_completed = models.BooleanField(default=False, db_column='prerequisite_completed')
    created_at = models.DateTimeField(default=timezone.now, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'module_sequencing'
        managed = True
        constraints = [models.UniqueConstraint(fields=['course', 'module'], name='uq_module_seq')]


# ModuleCompletion model removed - uses same 'module_completions' table as UnitProgress model above
# This was causing Django migration conflicts (can't have 2 models per table in same app)
# To query module completion data, use: UnitProgress.objects.all()
# The 'module_completions' table will still be created by the UnitProgress model


class Note(models.Model):
    """User notes on modules/units"""
    note_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='note_id')
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='notes', db_column='user_id')
    module = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='notes', db_column='module_id')
    content = models.TextField(db_column='content')
    created_at = models.DateTimeField(default=timezone.now, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'notes'
        managed = True


class Role(models.Model):
    """Role definitions"""
    role_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='role_id')
    role_name = models.CharField(max_length=50, unique=True, db_column='role_name')
    description = models.TextField(blank=True, null=True, db_column='description')
    created_at = models.DateTimeField(default=timezone.now, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'roles'
        managed = True


class UserRole(models.Model):
    """User role assignments"""
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, db_column='user_id')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, db_column='role_id')
    assigned_at = models.DateTimeField(default=timezone.now, db_column='assigned_at')
    assigned_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name='+', db_column='assigned_by')

    class Meta:
        db_table = 'user_roles'
        managed = True
        constraints = [models.UniqueConstraint(fields=['user', 'role'], name='user_role_pk')]


# =========================
# ADDITIONAL MODELS FOR COMPLETE SCHEMA
# =========================

class Badge(models.Model):
    """Badge definitions for gamification"""
    badge_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='badge_id')
    badge_name = models.CharField(max_length=255, db_column='badge_name')
    description = models.TextField(blank=True, null=True, db_column='description')
    badge_type = models.CharField(max_length=30, choices=[('gold', 'Gold'), ('silver', 'Silver'), ('bronze', 'Bronze'), ('positive', 'Positive'), ('negative', 'Negative'), ('custom', 'Custom')], db_column='badge_type')
    badge_icon_url = models.URLField(blank=True, null=True, db_column='badge_icon_url')
    points_threshold = models.IntegerField(default=0, db_column='points_threshold')
    visibility = models.CharField(max_length=20, choices=[('public', 'Public'), ('private', 'Private')], default='public', db_column='visibility')
    is_active = models.BooleanField(default=True, db_column='is_active')
    created_at = models.DateTimeField(default=timezone.now, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'badges'
        managed = True


class BadgeAssignment(models.Model):
    """User badge assignments"""
    badge_assignment_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='badge_assignment_id')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE, db_column='badge_id')
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, db_column='user_id')
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True, db_column='course_id')
    assigned_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name='+', db_column='assigned_by')
    reason = models.TextField(blank=True, null=True, db_column='reason')
    earned_at = models.DateTimeField(default=timezone.now, db_column='earned_at')
    created_at = models.DateTimeField(default=timezone.now, db_column='created_at')

    class Meta:
        db_table = 'badge_assignments'
        managed = True


class Certificate(models.Model):
    """Certificates issued to users"""
    certificate_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='certificate_id')
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, db_column='user_id')
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True, db_column='course_id')
    title = models.CharField(max_length=255, db_column='title')
    issued_date = models.DateTimeField(default=timezone.now, db_column='issued_date')
    valid_until = models.DateTimeField(blank=True, null=True, db_column='valid_until')
    issued_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name='+', db_column='issued_by')
    file_url = models.URLField(blank=True, null=True, db_column='file_url')
    status = models.CharField(max_length=20, choices=[('active', 'Active'), ('revoked', 'Revoked'), ('expired', 'Expired')], default='active', db_column='status')
    created_at = models.DateTimeField(default=timezone.now, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'certificates'
        managed = True


class AuditLog(models.Model):
    """Audit logging for system actions"""
    log_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='log_id')
    user = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, db_column='user_id')
    action_type = models.CharField(max_length=100, db_column='action_type')
    entity_type = models.CharField(max_length=50, blank=True, null=True, db_column='entity_type')
    entity_id = models.CharField(max_length=255, blank=True, null=True, db_column='entity_id')
    details = models.JSONField(default=dict, db_column='details')
    ip_address = models.CharField(max_length=45, blank=True, null=True, db_column='ip_address')
    user_agent = models.TextField(blank=True, null=True, db_column='user_agent')
    timestamp = models.DateTimeField(default=timezone.now, db_column='timestamp')

    class Meta:
        db_table = 'audit_logs'
        managed = True
        indexes = [
            models.Index(fields=['user', 'timestamp'], name='idx_audit_user_time'),
            models.Index(fields=['action_type'], name='idx_audit_action'),
            models.Index(fields=['entity_type'], name='idx_audit_entity'),
        ]


class CourseAssignment(models.Model):
    """Course assignments to teams"""
    assignment_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='assignment_id')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, db_column='course_id')
    assigned_to_team = models.ForeignKey(Team, on_delete=models.CASCADE, db_column='assigned_to_team_id')
    assigned_at = models.DateTimeField(default=timezone.now, db_column='assigned_at')

    class Meta:
        db_table = 'course_assignments'
        managed = False  # Managed by admin.CourseAssignment


class TestQuestion(models.Model):
    """Test questions (different from quiz questions)"""
    question_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='question_id')
    test = models.ForeignKey('Test', on_delete=models.CASCADE, related_name='questions', db_column='test_id')
    question_text = models.TextField(db_column='question_text')
    question_type = models.CharField(max_length=30, choices=[('mcq', 'MCQ'), ('true_false', 'True/False'), ('short_answer', 'Short Answer'), ('essay', 'Essay'), ('fill_blank', 'Fill Blank')], db_column='question_type')
    options = models.JSONField(default=dict, db_column='options')
    correct_answer = models.TextField(blank=True, null=True, db_column='correct_answer')
    points = models.IntegerField(default=1, db_column='points')
    difficulty = models.CharField(max_length=20, choices=[('easy', 'Easy'), ('medium', 'Medium'), ('hard', 'Hard')], blank=True, null=True, db_column='difficulty')
    explanation = models.TextField(blank=True, null=True, db_column='explanation')
    sequence_order = models.IntegerField(blank=True, null=True, db_column='sequence_order')
    created_at = models.DateTimeField(default=timezone.now, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'test_questions'
        managed = True


class Test(models.Model):
    """Tests/Exams (comprehensive alternative to quizzes)"""
    test_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='test_id')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, blank=True, null=True, db_column='course_id')
    module = models.ForeignKey(Unit, on_delete=models.CASCADE, blank=True, null=True, db_column='module_id')
    title = models.CharField(max_length=500, db_column='title')
    description = models.TextField(blank=True, null=True, db_column='description')
    test_type = models.CharField(max_length=30, choices=[('quiz', 'Quiz'), ('test', 'Test'), ('exam', 'Exam'), ('assessment', 'Assessment')], db_column='test_type')
    time_limit_minutes = models.IntegerField(blank=True, null=True, db_column='time_limit_minutes')
    passing_score = models.IntegerField(default=70, db_column='passing_score')
    max_attempts = models.IntegerField(default=1, db_column='max_attempts')
    randomize_questions = models.BooleanField(default=False, db_column='randomize_questions')
    show_correct_answers = models.BooleanField(default=False, db_column='show_correct_answers')
    points_possible = models.IntegerField(default=100, db_column='points_possible')
    is_mandatory = models.BooleanField(default=True, db_column='is_mandatory')
    record_confidence = models.BooleanField(default=True, db_column='record_confidence')
    confidence_scale = models.CharField(max_length=20, default='0_to_100', choices=[('0_to_100', '0-100'), ('1_to_5', '1-5'), ('1_to_7', '1-7'), ('low_med_high', 'Low/Med/High')], db_column='confidence_scale')
    created_by = models.ForeignKey(Profile, on_delete=models.CASCADE, db_column='created_by')
    created_at = models.DateTimeField(default=timezone.now, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'tests'
        managed = True


class TestAttempt(models.Model):
    """Test/exam attempts by users"""
    attempt_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='attempt_id')
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='attempts', db_column='test_id')
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, db_column='user_id')
    attempt_number = models.IntegerField(db_column='attempt_number')
    started_at = models.DateTimeField(default=timezone.now, db_column='started_at')
    submitted_at = models.DateTimeField(blank=True, null=True, db_column='submitted_at')
    time_spent_minutes = models.IntegerField(blank=True, null=True, db_column='time_spent_minutes')
    status = models.CharField(max_length=30, choices=[('in_progress', 'In Progress'), ('completed', 'Completed'), ('abandoned', 'Abandoned'), ('timed_out', 'Timed Out')], default='in_progress', db_column='status')
    score = models.IntegerField(blank=True, null=True, db_column='score')
    points_earned = models.IntegerField(default=0, db_column='points_earned')
    passed = models.BooleanField(blank=True, null=True, db_column='passed')
    graded_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name='+', db_column='graded_by')
    graded_at = models.DateTimeField(blank=True, null=True, db_column='graded_at')
    created_at = models.DateTimeField(default=timezone.now, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'test_attempts'
        managed = True
        unique_together = [('test', 'user', 'attempt_number')]


class TestResponse(models.Model):
    """Individual responses to test questions"""
    response_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='response_id')
    attempt = models.ForeignKey(TestAttempt, on_delete=models.CASCADE, related_name='responses', db_column='attempt_id')
    test = models.ForeignKey(Test, on_delete=models.CASCADE, db_column='test_id')
    question = models.ForeignKey(TestQuestion, on_delete=models.CASCADE, db_column='question_id')
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, db_column='user_id')
    selected_options = models.JSONField(default=dict, db_column='selected_options')
    answer_text = models.TextField(blank=True, null=True, db_column='answer_text')
    is_correct = models.BooleanField(blank=True, null=True, db_column='is_correct')
    score = models.IntegerField(default=0, db_column='score')
    confidence_score = models.IntegerField(blank=True, null=True, db_column='confidence_score')
    confidence_scale = models.CharField(max_length=20, default='0_to_100', db_column='confidence_scale')
    time_spent_seconds = models.IntegerField(blank=True, null=True, db_column='time_spent_seconds')
    answered_at = models.DateTimeField(default=timezone.now, db_column='answered_at')
    created_at = models.DateTimeField(default=timezone.now, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'test_responses'
        managed = True
        unique_together = [('attempt', 'question')]


class UserProgress(models.Model):
    """Comprehensive user progress tracking per course"""
    progress_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='progress_id')
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, db_column='user_id')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, db_column='course_id')
    completion_percentage = models.IntegerField(default=0, db_column='completion_percentage')
    total_points_earned = models.IntegerField(default=0, db_column='total_points_earned')
    average_score = models.IntegerField(default=0, db_column='average_score')
    time_spent_minutes = models.IntegerField(default=0, db_column='time_spent_minutes')
    modules_completed = models.IntegerField(default=0, db_column='modules_completed')
    total_modules = models.IntegerField(default=0, db_column='total_modules')
    tests_passed = models.IntegerField(default=0, db_column='tests_passed')
    tests_attempted = models.IntegerField(default=0, db_column='tests_attempted')
    assignments_submitted = models.IntegerField(default=0, db_column='assignments_submitted')
    assignments_graded = models.IntegerField(default=0, db_column='assignments_graded')
    started_at = models.DateTimeField(blank=True, null=True, db_column='started_at')
    completed_at = models.DateTimeField(blank=True, null=True, db_column='completed_at')
    last_activity = models.DateTimeField(blank=True, null=True, db_column='last_activity')
    created_at = models.DateTimeField(default=timezone.now, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'user_progress'
        managed = True
        unique_together = [('user', 'course')]


class Assessment(models.Model):
    """Assessments for trainee module"""
    assessment_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='assessment_id')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, blank=True, null=True, db_column='course_id')
    module = models.ForeignKey(Unit, on_delete=models.CASCADE, blank=True, null=True, db_column='module_id')
    title = models.CharField(max_length=500, db_column='title')
    description = models.TextField(blank=True, null=True, db_column='description')
    assessment_type = models.CharField(max_length=30, choices=[('descriptive', 'Descriptive'), ('practical', 'Practical'), ('oral', 'Oral'), ('rubric', 'Rubric'), ('peer', 'Peer'), ('survey', 'Survey'), ('other', 'Other')], db_column='assessment_type')
    due_date = models.DateTimeField(blank=True, null=True, db_column='due_date')
    max_attempts = models.IntegerField(default=1, db_column='max_attempts')
    points_possible = models.IntegerField(default=100, db_column='points_possible')
    is_mandatory = models.BooleanField(default=True, db_column='is_mandatory')
    status = models.CharField(max_length=20, choices=[('draft', 'Draft'), ('published', 'Published'), ('archived', 'Archived')], default='draft', db_column='status')
    created_by = models.ForeignKey(Profile, on_delete=models.CASCADE, db_column='created_by')
    created_at = models.DateTimeField(default=timezone.now, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'assessments'
        managed = True


class AssessmentSubmission(models.Model):
    """Submissions for assessments"""
    submission_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='submission_id')
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='submissions', db_column='assessment_id')
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, db_column='user_id')
    attempt_number = models.IntegerField(default=1, db_column='attempt_number')
    response_text = models.TextField(blank=True, null=True, db_column='response_text')
    response_file_url = models.URLField(blank=True, null=True, db_column='response_file_url')
    score = models.IntegerField(blank=True, null=True, db_column='score')
    feedback = models.TextField(blank=True, null=True, db_column='feedback')
    status = models.CharField(max_length=30, choices=[('draft', 'Draft'), ('submitted', 'Submitted'), ('graded', 'Graded'), ('returned', 'Returned')], default='submitted', db_column='status')
    submitted_at = models.DateTimeField(default=timezone.now, db_column='submitted_at')
    graded_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name='+', db_column='graded_by')
    graded_at = models.DateTimeField(blank=True, null=True, db_column='graded_at')
    created_at = models.DateTimeField(default=timezone.now, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'assessment_submissions'
        managed = True
        unique_together = [('assessment', 'user', 'attempt_number')]


class AssessmentItem(models.Model):
    """Assessment rubric items"""
    item_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='item_id')
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='items', db_column='assessment_id')
    criterion = models.CharField(max_length=255, db_column='criterion')
    description = models.TextField(blank=True, null=True, db_column='description')
    max_points = models.IntegerField(default=0, db_column='max_points')
    weight = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column='weight')
    sequence_order = models.IntegerField(blank=True, null=True, db_column='sequence_order')

    class Meta:
        db_table = 'assessment_items'
        managed = True


class AssessmentItemScore(models.Model):
    """Scores for individual assessment items"""
    item_score_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='item_score_id')
    submission = models.ForeignKey(AssessmentSubmission, on_delete=models.CASCADE, related_name='item_scores', db_column='submission_id')
    item = models.ForeignKey(AssessmentItem, on_delete=models.CASCADE, db_column='item_id')
    points_awarded = models.IntegerField(default=0, db_column='points_awarded')
    feedback = models.TextField(blank=True, null=True, db_column='feedback')
    created_at = models.DateTimeField(default=timezone.now, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'assessment_item_scores'
        managed = True
        unique_together = [('submission', 'item')]


class AssignmentRubricItem(models.Model):
    """Rubric items for assignments"""
    item_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='item_id')
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='rubric_items', db_column='assignment_id')
    criterion = models.CharField(max_length=255, db_column='criterion')
    description = models.TextField(blank=True, null=True, db_column='description')
    max_points = models.IntegerField(default=0, db_column='max_points')
    weight = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column='weight')
    sequence_order = models.IntegerField(blank=True, null=True, db_column='sequence_order')

    class Meta:
        db_table = 'assignment_rubric_items'
        managed = True


class AssignmentRubricItemScore(models.Model):
    """Scores for individual assignment rubric items"""
    item_score_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='item_score_id')
    submission = models.ForeignKey(AssignmentSubmission, on_delete=models.CASCADE, related_name='rubric_item_scores', db_column='submission_id')
    item = models.ForeignKey(AssignmentRubricItem, on_delete=models.CASCADE, db_column='item_id')
    points_awarded = models.IntegerField(default=0, db_column='points_awarded')
    feedback = models.TextField(blank=True, null=True, db_column='feedback')
    created_at = models.DateTimeField(default=timezone.now, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'assignment_rubric_item_scores'
        managed = True
        unique_together = [('submission', 'item')]


class AssignmentSubmissionReview(models.Model):
    """Reviews for assignment submissions"""
    review_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='review_id')
    submission = models.ForeignKey(AssignmentSubmission, on_delete=models.CASCADE, related_name='reviews', db_column='submission_id')
    reviewer = models.ForeignKey(Profile, on_delete=models.CASCADE, db_column='reviewer_id')
    review_note = models.TextField(blank=True, null=True, db_column='review_note')
    score = models.IntegerField(blank=True, null=True, db_column='score')
    status = models.CharField(max_length=30, choices=[('reviewed', 'Reviewed'), ('pending', 'Pending'), ('needs_revision', 'Needs Revision')], default='reviewed', db_column='status')
    reviewed_at = models.DateTimeField(default=timezone.now, db_column='reviewed_at')
    created_at = models.DateTimeField(default=timezone.now, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'assignment_submission_reviews'
        managed = True
        unique_together = [('submission', 'reviewer')]