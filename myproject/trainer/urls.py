"""
Trainer app URL configuration - Complete routes for all trainer features
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProfileViewSet, CourseViewSet, UnitViewSet, VideoUnitViewSet,
    AudioUnitViewSet, PresentationUnitViewSet, TextUnitViewSet,
    PageUnitViewSet, QuizViewSet, QuestionViewSet, AssignmentViewSet,
    ScormPackageViewSet, SurveyViewSet, EnrollmentViewSet,
    UnitProgressViewSet, AssignmentSubmissionViewSet, QuizAttemptViewSet,
    LeaderboardViewSet, MediaUploadViewSet, MediaUploadView, TeamViewSet, NotificationViewSet,
    ModuleSequencingViewSet, NoteViewSet, RoleViewSet, UserRoleViewSet,
    dashboard_stats, login, register, token_by_email, test_auth
)
from .health_check import (
    health_check, system_status, database_status, readiness_check, liveness_check
)

# DRF router for standard REST endpoints
router = DefaultRouter()
router.register(r'profiles', ProfileViewSet, basename='profile')
router.register(r'courses', CourseViewSet, basename='course')
router.register(r'units', UnitViewSet, basename='unit')
router.register(r'video-units', VideoUnitViewSet, basename='video-unit')
router.register(r'audio-units', AudioUnitViewSet, basename='audio-unit')
router.register(r'presentation-units', PresentationUnitViewSet, basename='presentation-unit')
router.register(r'text-units', TextUnitViewSet, basename='text-unit')
router.register(r'page-units', PageUnitViewSet, basename='page-unit')
router.register(r'quizzes', QuizViewSet, basename='quiz')
router.register(r'questions', QuestionViewSet, basename='question')
router.register(r'assignments', AssignmentViewSet, basename='assignment')
router.register(r'scorm-packages', ScormPackageViewSet, basename='scorm-package')
router.register(r'surveys', SurveyViewSet, basename='survey')
router.register(r'enrollments', EnrollmentViewSet, basename='enrollment')
router.register(r'unit-progress', UnitProgressViewSet, basename='unit-progress')
router.register(r'assignment-submissions', AssignmentSubmissionViewSet, basename='assignment-submission')
router.register(r'quiz-attempts', QuizAttemptViewSet, basename='quiz-attempt')
router.register(r'leaderboard', LeaderboardViewSet, basename='leaderboard')
# router.register(r'team-leaderboard', TeamLeaderboardViewSet, basename='team-leaderboard')  # REMOVED - duplicate table
router.register(r'teams', TeamViewSet, basename='team')
router.register(r'notifications', NotificationViewSet, basename='notifications')
router.register(r'module-sequencing', ModuleSequencingViewSet, basename='module-sequencing')
# router.register(r'module-completions', ModuleCompletionViewSet, basename='module-completion')  # REMOVED - duplicate table
router.register(r'notes', NoteViewSet, basename='note')
router.register(r'roles', RoleViewSet, basename='role')
router.register(r'user-roles', UserRoleViewSet, basename='user-role')

# Trainer-specific routes maintaining frontend compatibility with /trainer/v1/* paths
trainer_urls = [
    path('v1/dashboard/', dashboard_stats, name='trainer-dashboard'),
    path('v1/test-auth/', test_auth, name='test-auth'),
    path('v1/course/', CourseViewSet.as_view({'get': 'list', 'post': 'create'}), name='trainer-course-list'),
    path('v1/course/<uuid:pk>/', CourseViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), name='trainer-course-detail'),
    path('v1/course/<uuid:pk>/publish/', CourseViewSet.as_view({'post': 'publish'}), name='trainer-course-publish'),
    path('v1/course/<uuid:pk>/duplicate/', CourseViewSet.as_view({'post': 'duplicate'}), name='trainer-course-duplicate'),
    path('v1/course/<uuid:pk>/sequence/', CourseViewSet.as_view({'get': 'sequence', 'put': 'sequence'}), name='trainer-course-sequence'),
    path('v1/course/<uuid:pk>/assign/', CourseViewSet.as_view({'post': 'assign'}), name='trainer-course-assign'),
    path('v1/course/<uuid:pk>/modules/', CourseViewSet.as_view({'get': 'units'}), name='trainer-course-modules'),
    path('v1/course/<uuid:pk>/assignable-learners/', CourseViewSet.as_view({'get': 'assignable_learners'}), name='trainer-course-assignable-learners'),
    
    # Standard REST API custom actions (routes that work with /api/trainer/courses/<id>/action/)
    path('courses/<uuid:pk>/duplicate/', CourseViewSet.as_view({'post': 'duplicate'}), name='api-course-duplicate'),
    path('courses/<uuid:pk>/publish/', CourseViewSet.as_view({'post': 'publish'}), name='api-course-publish'),
    path('courses/<uuid:pk>/assignable_learners/', CourseViewSet.as_view({'get': 'assignable_learners'}), name='api-course-assignable-learners'),
    path('courses/<uuid:pk>/bulk_assign/', CourseViewSet.as_view({'post': 'assign'}), name='api-course-bulk-assign'),
    path('courses/<uuid:pk>/reorder_units/', UnitViewSet.as_view({'post': 'reorder'}), name='api-unit-reorder'),
    path('quizzes/<uuid:pk>/bulk_upload_questions/', QuestionViewSet.as_view({'post': 'bulk_create'}), name='api-quiz-bulk-questions'),
    
    # Trainer notifications endpoints
    path('trainer/notifications/', NotificationViewSet.as_view({'get': 'list', 'post': 'create'}), name='trainer-notifications-list'),
    path('trainer/notifications/<uuid:pk>/', NotificationViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), name='trainer-notifications-detail'),
    path('trainer/notifications/unread/', NotificationViewSet.as_view({'get': 'unread'}), name='trainer-notifications-unread'),
    path('trainer/notifications/list_unread/', NotificationViewSet.as_view({'get': 'list_unread'}), name='trainer-notifications-list-unread'),
    path('trainer/notifications/<uuid:pk>/mark_as_read/', NotificationViewSet.as_view({'post': 'mark_as_read'}), name='trainer-notifications-mark-read'),
    path('trainer/notifications/mark_all_as_read/', NotificationViewSet.as_view({'post': 'mark_all_as_read'}), name='trainer-notifications-mark-all-read'),
    path('trainer/notifications/archive_all/', NotificationViewSet.as_view({'post': 'archive_all'}), name='trainer-notifications-archive-all'),
    
    # Media upload and retrieval endpoints
    path('media/upload/', MediaUploadView.as_view(), name='media-upload'),
    path('media/list/', MediaUploadViewSet.as_view({'get': 'list'}), name='media-list'),
    path('media/<uuid:pk>/', MediaUploadViewSet.as_view({'get': 'retrieve'}), name='media-detail'),
    
    # Health check endpoints
    path('health/', health_check, name='health-check'),
    path('health/status/', system_status, name='system-status'),
    path('health/database/', database_status, name='database-status'),
    path('health/ready/', readiness_check, name='readiness-check'),
    path('health/alive/', liveness_check, name='liveness-check'),
]

urlpatterns = [
    # Authentication endpoints
    path('auth/login/', login, name='api_login'),
    path('auth/register/', register, name='api_register'),
    path('auth/token_by_email/', token_by_email, name='token_by_email'),
    
    # Standard REST API endpoints
    path('', include(router.urls)),
    
    # Trainer-specific alias routes
] + trainer_urls

