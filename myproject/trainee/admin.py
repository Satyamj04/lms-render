"""
Django admin configuration for LMS models.
Registers all models for admin interface access.
Note: UserProfile, Team, and TeamMember are registered in admin app.
"""
from django.contrib import admin
from trainee.models import (
    Course, CoursePrerequisite, Module, ModuleSequencing,
    ModuleCompletion, Note,
    Assignment, AssignmentTargeting, AssignmentSubmission,
    TestBank, Test, TestQuestion, TestAttempt, TestAnswer,
    UserProgress, BadgeRule, Badge, BadgeAssignment, Leaderboard,
    Notification, AuditLog, Feedback
)

# Courses & Modules
admin.site.register(Course)
admin.site.register(CoursePrerequisite)
admin.site.register(Module)
admin.site.register(ModuleSequencing)
admin.site.register(ModuleCompletion)
admin.site.register(Note)

# Assignments & Tests
admin.site.register(Assignment)
admin.site.register(AssignmentTargeting)
admin.site.register(AssignmentSubmission)
admin.site.register(TestBank)
admin.site.register(Test)
admin.site.register(TestQuestion)
admin.site.register(TestAttempt)
admin.site.register(TestAnswer)

# Progress & Gamification
admin.site.register(UserProgress)
admin.site.register(BadgeRule)
admin.site.register(Badge)
admin.site.register(BadgeAssignment)
admin.site.register(Leaderboard)

# Notifications & Audit
admin.site.register(Notification)
admin.site.register(AuditLog)
admin.site.register(Feedback)
