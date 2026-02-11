"""
LMS Models based on postgres_table.sql schema.
Uses UUIDs as primary keys for better distribution and security.

Note: User, Team, and TeamMember models are imported from admin.models to avoid duplication.
"""

import uuid
from django.db import models
from admin.models import User, Team, TeamMember, UserProfile


# ==============================
# MODULE 2: COURSES & MODULES
# ==============================

class Course(models.Model):
    """Courses in the LMS"""
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
    
    course_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True, null=True)
    about = models.TextField(blank=True, null=True)
    outcomes = models.TextField(blank=True, null=True)
    course_type = models.CharField(max_length=30, choices=COURSE_TYPE_CHOICES, default='self_paced')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_mandatory = models.BooleanField(default=False)
    estimated_duration_hours = models.IntegerField(blank=True, null=True)
    passing_criteria = models.IntegerField(default=70)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, db_column='created_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'courses'
        managed = False
        indexes = [
            models.Index(fields=['created_by']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return self.title


class CoursePrerequisite(models.Model):
    """Prerequisites for courses"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='prerequisites', db_column='course_id')
    prerequisite_course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='is_prerequisite_for', db_column='prerequisite_course_id')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'course_prerequisites'
        unique_together = ('course', 'prerequisite_course')

    def __str__(self):
        return f"{self.prerequisite_course} -> {self.course}"


class Module(models.Model):
    """Modules within courses"""
    MODULE_TYPE_CHOICES = [
        ('video', 'Video'),
        ('pdf', 'PDF'),
        ('ppt', 'PowerPoint'),
        ('document', 'Document'),
        ('quiz', 'Quiz'),
        ('mixed', 'Mixed'),
        ('text', 'Text'),
        ('audio', 'Audio'),
        ('presentation', 'Presentation'),
        ('page', 'Page'),
        ('assignment', 'Assignment'),
        ('survey', 'Survey'),
    ]
    
    module_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules', db_column='course_id')
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True, null=True)
    module_type = models.CharField(max_length=30, choices=MODULE_TYPE_CHOICES, blank=True, null=True)
    sequence_order = models.IntegerField()
    is_mandatory = models.BooleanField(default=True)
    estimated_duration_minutes = models.IntegerField(blank=True, null=True)
    video_count = models.IntegerField(default=0)
    has_quizzes = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'modules'
        managed = False
        unique_together = ('course', 'sequence_order')
        indexes = [
            models.Index(fields=['course']),
            models.Index(fields=['course', 'sequence_order']),
        ]

    def __str__(self):
        return f"{self.course} - {self.title}"


class LearningResource(models.Model):
    """Learning resources (PDFs, PPTs, DOCX, Videos, etc.) within modules"""
    RESOURCE_TYPE_CHOICES = [
        ('pdf', 'PDF'),
        ('ppt', 'PowerPoint'),
        ('docx', 'Word Document'),
        ('xlsx', 'Excel'),
        ('image', 'Image'),
        ('video', 'Video'),
        ('link', 'Link'),
        ('document', 'Document'),
        ('other', 'Other'),
    ]
    
    resource_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='resources', db_column='module_id')
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True, null=True)
    resource_type = models.CharField(max_length=30, choices=RESOURCE_TYPE_CHOICES)
    file_url = models.TextField()
    file_size_bytes = models.IntegerField(blank=True, null=True)
    sequence_order = models.IntegerField()
    is_mandatory = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, db_column='created_by_id')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'learning_resources'
        ordering = ['sequence_order']
        unique_together = ('module', 'sequence_order')
        indexes = [
            models.Index(fields=['module']),
            models.Index(fields=['resource_type']),
        ]

    def __str__(self):
        return f"{self.module} - {self.title}"


class ModuleSequencing(models.Model):
    """Module sequencing and drip-feed rules"""
    DRIP_FEED_CHOICES = [
        ('none', 'None'),
        ('time_based', 'Time Based'),
        ('completion_based', 'Completion Based'),
    ]
    
    sequence_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, db_column='course_id')
    module = models.ForeignKey(Module, on_delete=models.CASCADE, db_column='module_id')
    preceding_module = models.ForeignKey(Module, on_delete=models.CASCADE, null=True, blank=True, related_name='following_modules', db_column='preceding_module_id')
    drip_feed_rule = models.CharField(max_length=30, choices=DRIP_FEED_CHOICES, default='none')
    drip_feed_delay_days = models.IntegerField(default=0)
    prerequisite_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'module_sequencing'
        unique_together = ('course', 'module')

    def __str__(self):
        return f"{self.course} - {self.module}"


class ModuleCompletion(models.Model):
    """User completion of modules"""
    completion_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='completions', db_column='module_id')
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id')
    completion_percentage = models.IntegerField(default=0)
    is_completed = models.BooleanField(default=False)
    time_spent_minutes = models.IntegerField(default=0)
    completed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'module_completions'
        unique_together = ('module', 'user')
        indexes = [
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"{self.user} - {self.module}"


class Note(models.Model):
    """Notes on modules by users"""
    note_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notes', db_column='user_id')
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='notes', db_column='module_id')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notes'

    def __str__(self):
        return f"{self.user} - {self.module}"


# =========================
# MODULE 3: ASSIGNMENTS & TESTS
# =========================

class Assignment(models.Model):
    """Assignments in courses/modules"""
    ASSIGNMENT_TYPE_CHOICES = [
        ('task', 'Task'),
        ('role_play', 'Role Play'),
        ('written', 'Written'),
        ('project', 'Project'),
        ('other', 'Other'),
    ]
    
    assignment_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True, related_name='course_assignments_items', db_column='course_id')
    module = models.ForeignKey(Module, on_delete=models.CASCADE, null=True, blank=True, related_name='assignments', db_column='module_id')
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True, null=True)
    assignment_type = models.CharField(max_length=30, choices=ASSIGNMENT_TYPE_CHOICES, blank=True, null=True)
    due_date = models.DateTimeField(blank=True, null=True)
    max_attempts = models.IntegerField(default=5)
    points_possible = models.IntegerField(default=100)
    is_mandatory = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, db_column='created_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'assignments'
        indexes = [
            models.Index(fields=['course']),
        ]

    def __str__(self):
        return self.title


class AssignmentTargeting(models.Model):
    """Targeting for assignments to users or teams"""
    assignment_target_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='targeting', db_column='assignment_id')
    assigned_to_user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, db_column='assigned_to_user_id')
    assigned_to_team = models.ForeignKey(Team, on_delete=models.CASCADE, null=True, blank=True, db_column='assigned_to_team_id')
    assigned_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='assigned_assignments', db_column='assigned_by')
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'assignment_targeting'

    def __str__(self):
        target = self.assigned_to_user or self.assigned_to_team
        return f"{self.assignment} -> {target}"


class AssignmentSubmission(models.Model):
    """Submissions for assignments"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('graded', 'Graded'),
        ('returned', 'Returned'),
    ]
    
    submission_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions', db_column='assignment_id')
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id')
    attempt_number = models.IntegerField(default=1)
    submission_text = models.TextField(blank=True, null=True)
    submission_files = models.JSONField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='submitted')
    score = models.IntegerField(blank=True, null=True)
    points_earned = models.IntegerField(default=0)
    feedback = models.TextField(blank=True, null=True)
    graded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='graded_submissions')
    graded_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'assignment_submissions'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['assignment']),
        ]

    def __str__(self):
        return f"{self.user} - {self.assignment}"


class TestBank(models.Model):
    """Test bank for storing questions"""
    test_bank_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=100, blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, db_column='created_by_id')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'test_bank'

    def __str__(self):
        return self.name


class Test(models.Model):
    """Tests/Quizzes in the system"""
    TEST_TYPE_CHOICES = [
        ('quiz', 'Quiz'),
        ('test', 'Test'),
        ('exam', 'Exam'),
        ('assessment', 'Assessment'),
    ]
    
    test_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True, related_name='tests', db_column='course_id')
    module = models.ForeignKey(Module, on_delete=models.CASCADE, null=True, blank=True, related_name='tests', db_column='module_id')
    test_bank = models.ForeignKey(TestBank, on_delete=models.SET_NULL, null=True, blank=True, db_column='test_bank_id')
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True, null=True)
    test_type = models.CharField(max_length=30, choices=TEST_TYPE_CHOICES, blank=True, null=True)
    time_limit_minutes = models.IntegerField(blank=True, null=True)
    passing_score = models.IntegerField(default=70)
    max_attempts = models.IntegerField(default=5)
    randomize_questions = models.BooleanField(default=False)
    show_correct_answers = models.BooleanField(default=False)
    points_possible = models.IntegerField(default=100)
    is_mandatory = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, db_column='created_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tests'
        managed = False
        indexes = [
            models.Index(fields=['course']),
        ]

    def __str__(self):
        return self.title


class TestQuestion(models.Model):
    """Questions in tests"""
    QUESTION_TYPE_CHOICES = [
        ('mcq', 'Multiple Choice'),
        ('true_false', 'True/False'),
        ('short_answer', 'Short Answer'),
        ('essay', 'Essay'),
        ('fill_blank', 'Fill in the Blank'),
    ]
    
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]
    
    question_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    test = models.ForeignKey(Test, on_delete=models.CASCADE, null=True, blank=True, related_name='questions', db_column='test_id')
    test_bank = models.ForeignKey(TestBank, on_delete=models.CASCADE, null=True, blank=True, db_column='test_bank_id')
    question_text = models.TextField()
    question_type = models.CharField(max_length=30, choices=QUESTION_TYPE_CHOICES)
    options = models.JSONField(blank=True, null=True)
    correct_answer = models.TextField(blank=True, null=True)
    points = models.IntegerField(default=1)
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, blank=True, null=True)
    explanation = models.TextField(blank=True, null=True)
    sequence_order = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'test_questions'
        managed = False

    def __str__(self):
        return self.question_text[:100]


class TestAttempt(models.Model):
    """Test attempts by users"""
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('abandoned', 'Abandoned'),
        ('timed_out', 'Timed Out'),
    ]
    
    attempt_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='attempts', db_column='test_id')
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id')
    attempt_number = models.IntegerField()
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(blank=True, null=True)
    time_spent_minutes = models.IntegerField(blank=True, null=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='in_progress')
    score = models.IntegerField(blank=True, null=True)
    points_earned = models.IntegerField(default=0)
    passed = models.BooleanField(blank=True, null=True)
    graded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='graded_test_attempts', db_column='graded_by')
    graded_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'test_attempts'
        managed = False
        unique_together = ('test', 'user', 'attempt_number')
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['test']),
        ]

    def __str__(self):
        return f"{self.user} - {self.test}"


class TestAnswer(models.Model):
    """Answers given during test attempts"""
    answer_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt = models.ForeignKey(TestAttempt, on_delete=models.CASCADE, related_name='answers', db_column='attempt_id')
    question = models.ForeignKey(TestQuestion, on_delete=models.CASCADE, db_column='question_id')
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id', blank=True, null=True)
    answer_text = models.TextField(blank=True, null=True)
    selected_options = models.JSONField(blank=True, null=True)
    is_correct = models.BooleanField(blank=True, null=True)
    points_earned = models.IntegerField(default=0)
    confidence_score = models.IntegerField(blank=True, null=True, help_text="Candidate's confidence level (0-100)")
    feedback = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'test_answers'
        managed = False
        unique_together = ('attempt', 'question')
        indexes = [
            models.Index(fields=['attempt']),
            models.Index(fields=['user', 'question']),
            models.Index(fields=['user']),
            models.Index(fields=['question']),
        ]

    def __str__(self):
        return f"{self.attempt} - Q{self.question}"


# =========================
# MODULE 4: PROGRESS & GAMIFICATION
# =========================

class UserProgress(models.Model):
    """User's progress in courses"""
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]
    
    progress_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='course_progress')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='user_progress')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    completion_percentage = models.IntegerField(default=0)
    total_points_earned = models.IntegerField(default=0)
    average_score = models.IntegerField(default=0)
    time_spent_minutes = models.IntegerField(default=0)
    modules_completed = models.IntegerField(default=0)
    total_modules = models.IntegerField(default=0)
    tests_passed = models.IntegerField(default=0)
    tests_attempted = models.IntegerField(default=0)
    assignments_submitted = models.IntegerField(default=0)
    assignments_graded = models.IntegerField(default=0)
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    last_activity = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_progress'
        unique_together = ('user', 'course')
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['course']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.user} - {self.course} ({self.status})"


class BadgeRule(models.Model):
    """Rules for earning badges"""
    RULE_TYPE_CHOICES = [
        ('points_threshold', 'Points Threshold'),
        ('completion', 'Completion'),
        ('score', 'Score'),
        ('streak', 'Streak'),
        ('deadline', 'Deadline'),
        ('custom', 'Custom'),
    ]
    
    rule_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rule_name = models.CharField(max_length=255)
    rule_type = models.CharField(max_length=50, choices=RULE_TYPE_CHOICES)
    description = models.TextField(blank=True, null=True)
    criteria = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'badge_rules'

    def __str__(self):
        return self.rule_name


class Badge(models.Model):
    """Badges that can be earned"""
    BADGE_TYPE_CHOICES = [
        ('gold', 'Gold'),
        ('silver', 'Silver'),
        ('bronze', 'Bronze'),
        ('positive', 'Positive'),
        ('negative', 'Negative'),
        ('custom', 'Custom'),
    ]
    
    
    VISIBILITY_CHOICES = [
        ('public', 'Public'),
        ('private', 'Private'),
    ]
    
    badge_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    badge_name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    badge_type = models.CharField(max_length=30, choices=BADGE_TYPE_CHOICES, blank=True, null=True)
    badge_icon_url = models.TextField(blank=True, null=True)
    rule = models.ForeignKey(BadgeRule, on_delete=models.SET_NULL, null=True, blank=True, db_column='rule_id')
    points_threshold = models.IntegerField(default=0)
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='public')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'badges'

    def __str__(self):
        return self.badge_name


class BadgeAssignment(models.Model):
    """Badges assigned to users"""
    badge_assignment_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE, related_name='assignments', db_column='badge_id')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='badges', db_column='user_id')
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True, db_column='course_id')
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_badges', db_column='assigned_by')
    reason = models.TextField(blank=True, null=True)
    earned_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'badge_assignments'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['badge']),
        ]

    def __str__(self):
        return f"{self.user} - {self.badge}"


class Leaderboard(models.Model):
    """Leaderboard entries"""
    SCOPE_CHOICES = [
        ('global', 'Global'),
        ('team', 'Team'),
        ('course', 'Course'),
        ('batch', 'Batch'),
        ('module', 'Module'),
    ]
    
    leaderboard_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scope = models.CharField(max_length=30, choices=SCOPE_CHOICES)
    scope_id = models.UUIDField(blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id')
    points = models.IntegerField(default=0)
    rank = models.IntegerField(blank=True, null=True)
    calculated_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'leaderboard'
        indexes = [
            models.Index(fields=['scope', 'scope_id']),
            models.Index(fields=['user']),
            models.Index(fields=['scope', 'rank']),
        ]

    def __str__(self):
        return f"{self.scope} - {self.user}"


# =========================
# MODULE 5: NOTIFICATIONS & AUDIT
# =========================

class Notification(models.Model):
    """Notifications for users"""
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
    
    notification_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', db_column='user_id')
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPE_CHOICES, blank=True, null=True)
    title = models.CharField(max_length=500, blank=True, null=True)
    message = models.TextField()
    link_url = models.TextField(blank=True, null=True)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unread')
    sent_via = models.CharField(max_length=30, choices=SENT_VIA_CHOICES, default='in_app')
    read_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['status']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.user} - {self.notification_type}"


class AuditLog(models.Model):
    """Audit logs for tracking actions"""
    log_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, db_column='user_id')
    action_type = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=100, blank=True, null=True)
    entity_id = models.UUIDField(blank=True, null=True)
    details = models.JSONField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit_logs'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['-timestamp']),
            models.Index(fields=['entity_type', 'entity_id']),
        ]

    def __str__(self):
        return f"{self.action_type} - {self.entity_type}"


# =========================
# MODULE 6: FEEDBACK & COMMUNICATION
# =========================

class Feedback(models.Model):
    """Feedback from users"""
    FEEDBACK_TYPE_CHOICES = [
        ('course', 'Course'),
        ('module', 'Module'),
        ('trainer', 'Trainer'),
        ('system', 'System'),
        ('general', 'General'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('reviewed', 'Reviewed'),
        ('resolved', 'Resolved'),
    ]
    
    feedback_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True, db_column='course_id')
    module = models.ForeignKey(Module, on_delete=models.CASCADE, null=True, blank=True, db_column='module_id')
    feedback_type = models.CharField(max_length=30, choices=FEEDBACK_TYPE_CHOICES, blank=True, null=True)
    rating = models.IntegerField(blank=True, null=True)
    content = models.TextField()
    is_anonymous = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_feedback', db_column='reviewed_by')
    reviewed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'feedback'

    def __str__(self):
        return f"{self.user} - {self.feedback_type}"


# =========================
# MODULE 7: CONTENT UNITS (Video, Audio, Text, etc.)
# =========================

class VideoUnit(models.Model):
    """Video content for modules"""
    COMPLETION_TYPE_CHOICES = [
        ('full', 'Full'),
        ('percentage', 'Percentage'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit = models.OneToOneField(Module, on_delete=models.CASCADE, related_name='video_unit', db_column='unit_id')
    video_url = models.TextField(blank=True, null=True)
    video_storage_path = models.CharField(max_length=500, blank=True, null=True)
    duration = models.IntegerField(default=0, help_text="Duration in seconds")
    completion_type = models.CharField(max_length=20, choices=COMPLETION_TYPE_CHOICES, default='full', blank=True, null=True)
    required_watch_percentage = models.IntegerField(default=100, blank=True, null=True)
    allow_skip = models.BooleanField(default=False, blank=True, null=True)
    allow_rewind = models.BooleanField(default=True, blank=True, null=True)

    class Meta:
        db_table = 'video_units'
        managed = False
        indexes = [
            models.Index(fields=['unit']),
        ]

    def __str__(self):
        return f"Video: {self.unit.title if self.unit else 'Unknown'}"


class AudioUnit(models.Model):
    """Audio content for modules"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit = models.OneToOneField(Module, on_delete=models.CASCADE, related_name='audio_unit', db_column='unit_id')
    audio_url = models.TextField(blank=True, null=True)
    audio_storage_path = models.CharField(max_length=500, blank=True, null=True)
    duration = models.IntegerField(default=0, help_text="Duration in seconds")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'audio_units'
        indexes = [
            models.Index(fields=['unit']),
        ]

    def __str__(self):
        return f"Audio: {self.unit.title}"


class PresentationUnit(models.Model):
    """Presentation content (PPT, PDF) for modules"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit = models.OneToOneField(Module, on_delete=models.CASCADE, related_name='presentation_unit', db_column='unit_id')
    file_url = models.TextField(blank=True, null=True)
    file_storage_path = models.CharField(max_length=500, blank=True, null=True)
    slide_count = models.IntegerField(default=0)

    class Meta:
        db_table = 'presentation_units'
        managed = False
        indexes = [
            models.Index(fields=['unit']),
        ]

    def __str__(self):
        return f"Presentation: {self.unit.title}"


class TextUnit(models.Model):
    """Text content for modules"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit = models.OneToOneField(Module, on_delete=models.CASCADE, related_name='text_unit', db_column='unit_id')
    content = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'text_units'
        indexes = [
            models.Index(fields=['unit']),
        ]

    def __str__(self):
        return f"Text: {self.unit.title}"


class PageUnit(models.Model):
    """Page content with structured JSON data"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit = models.OneToOneField(Module, on_delete=models.CASCADE, related_name='page_unit', db_column='unit_id')
    content = models.JSONField()
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'page_units'
        indexes = [
            models.Index(fields=['unit']),
        ]

    def __str__(self):
        return f"Page: {self.unit.title}"


class ScormPackage(models.Model):
    """SCORM and xAPI packages for modules"""
    PACKAGE_TYPE_CHOICES = [
        ('scorm_1_2', 'SCORM 1.2'),
        ('scorm_2004', 'SCORM 2004'),
        ('xapi', 'xAPI'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit = models.OneToOneField(Module, on_delete=models.CASCADE, related_name='scorm_package', db_column='unit_id')
    package_type = models.CharField(max_length=20, choices=PACKAGE_TYPE_CHOICES, blank=True, null=True)
    file_url = models.TextField(blank=True, null=True)
    file_storage_path = models.CharField(max_length=500, blank=True, null=True)
    version = models.CharField(max_length=50, blank=True, null=True)
    completion_tracking = models.BooleanField(default=True)
    score_tracking = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'scorm_packages'
        indexes = [
            models.Index(fields=['unit']),
        ]

    def __str__(self):
        return f"SCORM: {self.unit.title}"


class Survey(models.Model):
    """Survey content for modules"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit = models.OneToOneField(Module, on_delete=models.CASCADE, related_name='survey', db_column='unit_id')
    questions = models.JSONField()
    allow_anonymous = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'surveys'
        indexes = [
            models.Index(fields=['unit']),
        ]

    def __str__(self):
        return f"Survey: {self.unit.title}"


# =========================
# MODULE 8: ENROLLMENTS & PROGRESS
# =========================

class Enrollment(models.Model):
    """Course enrollments for users"""
    STATUS_CHOICES = [
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments', db_column='course_id')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments', db_column='user_id')
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_enrollments', db_column='assigned_by')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='assigned')
    progress_percentage = models.IntegerField(default=0)
    assigned_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'enrollments'
        unique_together = ('course', 'user')
        indexes = [
            models.Index(fields=['course']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"{self.user} -> {self.course}"


class UnitProgress(models.Model):
    """User progress within a unit/module"""
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='unit_progress', db_column='enrollment_id')
    unit = models.ForeignKey(Module, on_delete=models.CASCADE, db_column='unit_id')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    watch_percentage = models.IntegerField(default=0)
    score = models.IntegerField(blank=True, null=True)
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'unit_progress'
        unique_together = ('enrollment', 'unit')
        indexes = [
            models.Index(fields=['enrollment']),
            models.Index(fields=['unit']),
        ]

    def __str__(self):
        return f"{self.enrollment} - {self.unit}"


# =========================
# MODULE 9: MODULE QUIZZES (Legacy - for backward compatibility)
# =========================

class ModuleQuiz(models.Model):
    """Quizzes for modules (legacy)"""
    quiz_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='quizzes', db_column='module_id')
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True, null=True)
    sequence_order = models.IntegerField()
    time_limit_minutes = models.IntegerField(blank=True, null=True)
    passing_score = models.IntegerField(default=70)
    max_attempts = models.IntegerField(default=1)
    randomize_questions = models.BooleanField(default=False)
    show_correct_answers = models.BooleanField(default=False)
    points_possible = models.IntegerField(default=100)
    is_mandatory = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, db_column='created_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'module_quizzes'
        ordering = ['sequence_order']
        unique_together = ('module', 'sequence_order')
        indexes = [
            models.Index(fields=['module']),
        ]

    def __str__(self):
        return f"Quiz: {self.module.title}"


class ModuleQuizQuestion(models.Model):
    """Questions for module quizzes (legacy)"""
    QUESTION_TYPE_CHOICES = [
        ('mcq', 'Multiple Choice'),
        ('true_false', 'True/False'),
        ('short_answer', 'Short Answer'),
        ('essay', 'Essay'),
        ('fill_blank', 'Fill in the Blank'),
    ]
    
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]
    
    question_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quiz = models.ForeignKey(ModuleQuiz, on_delete=models.CASCADE, related_name='questions', db_column='quiz_id')
    question_text = models.TextField()
    question_type = models.CharField(max_length=30, choices=QUESTION_TYPE_CHOICES)
    options = models.JSONField(blank=True, null=True)
    correct_answer = models.TextField(blank=True, null=True)
    points = models.IntegerField(default=1)
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, blank=True, null=True)
    explanation = models.TextField(blank=True, null=True)
    sequence_order = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'module_quiz_questions'
        ordering = ['sequence_order']
        indexes = [
            models.Index(fields=['quiz']),
        ]

    def __str__(self):
        return f"{self.quiz} - Q{self.sequence_order}"


class ModuleQuizAttempt(models.Model):
    """Module quiz attempts by users (legacy)"""
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('timed_out', 'Timed Out'),
        ('abandoned', 'Abandoned'),
    ]
    
    attempt_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quiz = models.ForeignKey(ModuleQuiz, on_delete=models.CASCADE, related_name='attempts', db_column='quiz_id')
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id')
    attempt_number = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    score = models.FloatField(blank=True, null=True)
    passed = models.BooleanField(blank=True, null=True)
    points_earned = models.IntegerField(default=0)
    correct_answers = models.IntegerField(default=0)
    total_questions = models.IntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(blank=True, null=True)
    time_spent_seconds = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'module_quiz_attempts'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['quiz']),
            models.Index(fields=['user']),
            models.Index(fields=['quiz', 'user']),
        ]

    def __str__(self):
        return f"{self.user} - {self.quiz}"


class ModuleQuizAnswer(models.Model):
    """Answers given in module quiz attempts (legacy)"""
    answer_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt = models.ForeignKey(ModuleQuizAttempt, on_delete=models.CASCADE, related_name='answers', db_column='attempt_id')
    question = models.ForeignKey(ModuleQuizQuestion, on_delete=models.CASCADE, related_name='attempts', db_column='question_id')
    answer_text = models.TextField()
    is_correct = models.BooleanField(default=False)
    points_earned = models.IntegerField(default=0)
    confidence_score = models.IntegerField(blank=True, null=True, help_text="Candidate's confidence level (0-100)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'module_quiz_answers'
        indexes = [
            models.Index(fields=['attempt']),
            models.Index(fields=['question']),
        ]

    def __str__(self):
        return f"{self.attempt} - Q{self.question}"


# =========================
# MODULE 9A: QUIZZES (Trainer-specific)
# =========================

class Quiz(models.Model):
    """Quizzes for modules (trainer version)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit = models.OneToOneField(Module, on_delete=models.CASCADE, related_name='quiz', db_column='unit_id')
    time_limit = models.IntegerField(blank=True, null=True, help_text="Time limit in minutes")
    passing_score = models.IntegerField(default=70, blank=True, null=True)
    attempts_allowed = models.IntegerField(default=1, blank=True, null=True)
    show_answers = models.BooleanField(default=False, blank=True, null=True)
    randomize_questions = models.BooleanField(default=False, blank=True, null=True)
    mandatory_completion = models.BooleanField(default=False, blank=True, null=True)

    class Meta:
        db_table = 'quizzes'
        managed = False
        indexes = [
            models.Index(fields=['unit']),
        ]

    def __str__(self):
        return f"Quiz: {self.unit.title if self.unit else 'Unknown'}"


class Question(models.Model):
    """Questions for quizzes"""
    QUESTION_TYPE_CHOICES = [
        ('mcq', 'Multiple Choice'),
        ('true_false', 'True/False'),
        ('short_answer', 'Short Answer'),
        ('essay', 'Essay'),
        ('fill_blank', 'Fill in the Blank'),
        ('matching', 'Matching'),
        ('ordering', 'Ordering'),
        ('free_text', 'Free Text'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions', db_column='quiz_id')
    type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES)
    text = models.TextField()
    options = models.JSONField(blank=True, null=True)
    correct_answer = models.JSONField(blank=True, null=True)
    points = models.IntegerField(default=1)
    order = models.IntegerField(default=0)

    class Meta:
        db_table = 'questions'
        managed = False
        ordering = ['order']
        indexes = [
            models.Index(fields=['quiz']),
            models.Index(fields=['quiz', 'order']),
        ]

    def __str__(self):
        return f"{self.quiz} - Q{self.order}"


class QuizAttempt(models.Model):
    """Quiz attempts by users - mapped to existing database table"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts', db_column='quiz_id')
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, db_column='user_id')
    score = models.IntegerField(default=0)
    passed = models.BooleanField(default=False)
    answers = models.JSONField(blank=True, null=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'quiz_attempts'
        managed = False
        indexes = [
            models.Index(fields=['quiz', 'user']),
            models.Index(fields=['user']),
            models.Index(fields=['quiz']),
        ]

    def __str__(self):
        return f"{self.user} - {self.quiz}"




# =========================
# MODULE 10: TEAM LEADERBOARD
# =========================

class TeamLeaderboard(models.Model):
    """Team leaderboard for courses"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, db_column='team_id')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, db_column='course_id')
    total_points = models.IntegerField(default=0)
    average_points = models.FloatField(default=0.0)
    completed_units = models.IntegerField(default=0)
    total_members = models.IntegerField(default=0)
    active_members = models.IntegerField(default=0)
    quiz_score_total = models.IntegerField(default=0)
    rank = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'team_leaderboard'
        unique_together = ('team', 'course')
        indexes = [
            models.Index(fields=['team']),
            models.Index(fields=['course']),
            models.Index(fields=['rank']),
        ]

    def __str__(self):
        return f"{self.team} - {self.course}"


# =========================
# MODULE 11: MEDIA METADATA
# =========================

class MediaMetadata(models.Model):
    """Media file metadata"""
    FILE_TYPE_CHOICES = [
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('image', 'Image'),
        ('document', 'Document'),
        ('presentation', 'Presentation'),
        ('pdf', 'PDF'),
        ('other', 'Other'),
    ]
    
    STORAGE_TYPE_CHOICES = [
        ('local', 'Local'),
        ('s3', 'S3'),
        ('gridfs', 'GridFS'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    storage_path = models.TextField(unique=True)
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50, choices=FILE_TYPE_CHOICES)
    file_size = models.BigIntegerField(blank=True, null=True)
    mime_type = models.CharField(max_length=100, blank=True, null=True)
    duration = models.IntegerField(blank=True, null=True, help_text="Duration in seconds (for video/audio)")
    width = models.IntegerField(blank=True, null=True, help_text="Width in pixels (for images/video)")
    height = models.IntegerField(blank=True, null=True, help_text="Height in pixels (for images/video)")
    unit = models.ForeignKey(Module, on_delete=models.SET_NULL, null=True, blank=True, related_name='media_files', db_column='unit_id')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, db_column='uploaded_by')
    storage_type = models.CharField(max_length=10, choices=STORAGE_TYPE_CHOICES, default='local')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'media_metadata'
        indexes = [
            models.Index(fields=['unit', 'file_type']),
            models.Index(fields=['uploaded_by', '-uploaded_at']),
        ]

    def __str__(self):
        return self.file_name


# =========================
# MODULE 12: ASSESSMENTS (Trainee-specific)
# =========================

class Assessment(models.Model):
    """Assessments for trainee module"""
    ASSESSMENT_TYPE_CHOICES = [
        ('descriptive', 'Descriptive'),
        ('practical', 'Practical'),
        ('oral', 'Oral'),
        ('rubric', 'Rubric'),
        ('peer', 'Peer'),
        ('survey', 'Survey'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]
    
    assessment_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True, db_column='course_id')
    module = models.ForeignKey(Module, on_delete=models.CASCADE, null=True, blank=True, db_column='module_id')
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True, null=True)
    assessment_type = models.CharField(max_length=30, choices=ASSESSMENT_TYPE_CHOICES)
    due_date = models.DateTimeField(blank=True, null=True)
    max_attempts = models.IntegerField(default=1)
    points_possible = models.IntegerField(default=100)
    is_mandatory = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, db_column='created_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.IntegerField(default=1)

    class Meta:
        db_table = 'assessments'
        indexes = [
            models.Index(fields=['course']),
            models.Index(fields=['module']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return self.title


class AssessmentSubmission(models.Model):
    """Assessment submissions by trainees"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('graded', 'Graded'),
        ('returned', 'Returned'),
    ]
    
    submission_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='submissions', db_column='assessment_id')
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id')
    attempt_number = models.IntegerField(default=1)
    response_text = models.TextField(blank=True, null=True)
    response_file_url = models.TextField(blank=True, null=True)
    score = models.IntegerField(blank=True, null=True)
    feedback = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='submitted')
    submitted_at = models.DateTimeField(auto_now_add=True)
    graded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='graded_assessments', db_column='graded_by')
    graded_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'assessment_submissions'
        unique_together = ('assessment', 'user', 'attempt_number')
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['assessment']),
        ]

    def __str__(self):
        return f"{self.user} - {self.assessment}"


class AssessmentItem(models.Model):
    """Assessment rubric items"""
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='items', db_column='assessment_id')
    item_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    criterion = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    max_points = models.IntegerField(default=0)
    weight = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Weight 0-100")
    sequence_order = models.IntegerField()

    class Meta:
        db_table = 'assessment_items'
        indexes = [
            models.Index(fields=['assessment']),
        ]

    def __str__(self):
        return f"{self.assessment} - {self.criterion}"


class AssessmentItemScore(models.Model):
    """Scores for assessment items"""
    item_score_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission = models.ForeignKey(AssessmentSubmission, on_delete=models.CASCADE, related_name='item_scores', db_column='submission_id')
    item = models.ForeignKey(AssessmentItem, on_delete=models.CASCADE, db_column='item_id')
    points_awarded = models.IntegerField(default=0)
    feedback = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'assessment_item_scores'
        unique_together = ('submission', 'item')
        indexes = [
            models.Index(fields=['submission']),
            models.Index(fields=['item']),
        ]

    def __str__(self):
        return f"{self.submission} - {self.item}"


# =========================
# MODULE 13: ASSIGNMENT RUBRICS & REVIEWS
# =========================

class AssignmentRubricItem(models.Model):
    """Assignment rubric items"""
    item_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='rubric_items', db_column='assignment_id')
    criterion = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    max_points = models.IntegerField(default=0)
    weight = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Weight 0-100")
    sequence_order = models.IntegerField()

    class Meta:
        db_table = 'assignment_rubric_items'
        indexes = [
            models.Index(fields=['assignment']),
        ]

    def __str__(self):
        return f"{self.assignment} - {self.criterion}"


class AssignmentRubricItemScore(models.Model):
    """Scores for assignment rubric items"""
    item_score_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission = models.ForeignKey(AssignmentSubmission, on_delete=models.CASCADE, related_name='rubric_item_scores', db_column='submission_id')
    item = models.ForeignKey(AssignmentRubricItem, on_delete=models.CASCADE, db_column='item_id')
    points_awarded = models.IntegerField(default=0)
    feedback = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'assignment_rubric_item_scores'
        unique_together = ('submission', 'item')
        indexes = [
            models.Index(fields=['submission']),
            models.Index(fields=['item']),
        ]

    def __str__(self):
        return f"{self.submission} - {self.item}"


class AssignmentSubmissionReview(models.Model):
    """Reviews for assignment submissions"""
    STATUS_CHOICES = [
        ('reviewed', 'Reviewed'),
        ('pending', 'Pending'),
        ('needs_revision', 'Needs Revision'),
    ]
    
    review_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission = models.ForeignKey(AssignmentSubmission, on_delete=models.CASCADE, related_name='reviews', db_column='submission_id')
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, db_column='reviewer_id')
    review_note = models.TextField(blank=True, null=True)
    score = models.IntegerField(blank=True, null=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='reviewed')
    reviewed_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'assignment_submission_reviews'
        unique_together = ('submission', 'reviewer')
        indexes = [
            models.Index(fields=['submission']),
            models.Index(fields=['reviewer']),
        ]

    def __str__(self):
        return f"Review: {self.submission}"


# =========================
# MODULE 14: TEST QUESTIONS & RESPONSES (Extended)
# =========================

class TestResponse(models.Model):
    """Per-question responses - Unified table for both Test and Quiz systems"""
    CONFIDENCE_SCALE_CHOICES = [
        ('0_to_100', '0-100'),
        ('1_to_5', '1-5'),
        ('1_to_7', '1-7'),
        ('low_med_high', 'Low/Med/High'),
    ]
    
    response_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Polymorphic foreign keys - can reference either Test or Quiz system
    attempt_id = models.UUIDField(blank=True, null=True, db_column='attempt_id')  # Can be TestAttempt or QuizAttempt ID
    test_id = models.UUIDField(blank=True, null=True, db_column='test_id')  # Can be Test or Quiz ID
    question_id = models.UUIDField(blank=True, null=True, db_column='question_id')  # Can be TestQuestion or Question ID
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, db_column='user_id')
    selected_options = models.JSONField(blank=True, null=True)
    answer_text = models.TextField(blank=True, null=True)
    is_correct = models.BooleanField(blank=True, null=True)
    score = models.IntegerField(default=0)
    confidence_score = models.IntegerField(blank=True, null=True, help_text="Confidence level (0-100)")
    confidence_scale = models.CharField(max_length=20, choices=CONFIDENCE_SCALE_CHOICES, default='0_to_100')
    time_spent_seconds = models.IntegerField(blank=True, null=True)
    answered_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'test_responses'
        managed = False

    def __str__(self):
        return f"Response: {self.response_id}"

