"""
URL Configuration for Trainee API
Handles all trainee-facing endpoints for the LMS
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.response import Response
from rest_framework import status
from trainee.services.auth import login, logout
from trainee.services.dashboard import DashboardView
from trainee.services.profile import ProfileView
from trainee.services.courses import (
    get_my_courses,
    get_course_detail,
    start_course
)
from trainee.services.api_views import (
    get_courses,
    get_course_detail as api_get_course_detail,
    start_course as api_start_course,
    get_module_detail,
    get_module_mixed_content as api_get_module_mixed_content,
    get_video,
    mark_module_complete,
    get_dashboard,
    convert_ppt_to_pdf
)
from trainee.services.learning import (
    get_course_modules,
    get_module_content,
    track_learning_time,
    get_module_questions,
    answer_module_question,
    get_module_notes,
    create_module_note,
    update_module_note,
    delete_module_note
    , note_by_id
)
from trainee.services.history import (
    get_consolidated_history,
    get_test_results,
    get_assignment_results,
    get_trainer_feedback,
    get_earned_badges,
    get_points_breakdown,
    get_user_leaderboard,
    get_appraisal_summary,
    get_user_progress_stats
)
from trainee.services.assessments import (
    get_notifications,
    mark_notification_read,
    mark_all_notifications_read,
    submit_feedback
)
from trainee.services.videos import (
    get_lesson_videos,
    get_course_videos,
    record_video_view,
    get_video_detail,
    get_video_from_mongodb,
    stream_video,
    get_video_player_data
)
from trainee.services.media import (
    get_resource_file,
    get_media_files_list
)
from trainee.services.media_server import (
    get_all_media_files,
    get_media_by_type
)
from trainee.services.module_content import (
    get_module_mixed_content,
    create_module_quiz,
    update_module_quiz,
    delete_module_quiz,
    add_quiz_question,
    create_learning_resource,
    update_learning_resource,
    delete_learning_resource,
    get_quiz_detail
)
from trainee.services.content_fetcher import (
    get_course_content_counts,
    get_module_videos_from_mongodb,
    get_module_pdfs_from_mongodb,
    get_module_quizzes_postgresql,
    get_module_all_content
)
from trainee.services.media_content import (
    get_course_content_by_type,
    get_module_content_detailed,
    get_user_course_content,
    get_media_files_summary
)
from trainee.services.api import (
    TestViewSet,
    TestAttemptViewSet,
    AssignmentViewSet,
    AssignmentSubmissionViewSet,
    UserProgressViewSet
)
from trainee.services.api import (
    submit_assignment_by_id,
    submit_quiz_attempt_by_attempt
)
from trainee.services.api import get_test_attempt_result
from trainee.services.screentime_api import (
    start_module_session,
    record_screentime,
    get_module_screentime,
    get_course_screentime,
    get_total_screentime,
    get_screentime_analytics
)
from trainee.services.quiz import (
    get_module_quizzes,
    start_quiz_attempt,
    check_quiz_status,
    submit_quiz_attempt,
    get_quiz_attempt_result
)
from trainee.services.quiz_management import (
    create_quiz_in_module,
    update_quiz_position,
    get_module_content_positions
)
from trainee.services.progress_views import (
    update_progress,
    get_progress,
    get_completed_content
)
from trainee.services.leaderboard_views import (
    get_individual_leaderboard,
    get_team_leaderboard,
    calculate_leaderboards,
    get_user_rank
)
from trainee.services.module_sequence_views import (
    check_module_access,
    initialize_course_modules,
    get_module_progress_list,
    update_module_progress,
    mark_module_completed
)
from trainee.services.quiz_results_views import (
    process_quiz_attempt,
    get_quiz_results,
    get_best_attempt,
    get_quiz_statistics,
    validate_quiz_attempt
)

# Register viewsets for tests and assignments so routes like
# /trainee/tests/, /trainee/test-attempts/, /trainee/assignments/, and
# /trainee/assignment-submissions/ are exposed to the frontend.
router = DefaultRouter()
router.register(r'tests', TestViewSet, basename='test')
router.register(r'test-attempts', TestAttemptViewSet, basename='test-attempt')
router.register(r'assignments', AssignmentViewSet, basename='assignment')
router.register(r'assignment-submissions', AssignmentSubmissionViewSet, basename='assignment-submission')
router.register(r'progress', UserProgressViewSet, basename='progress')

urlpatterns = [
    # ========== Authentication ==========
    path('auth/login/', login, name='login'),
    path('auth/logout/', logout, name='logout'),
    
    # ========== Dashboard & Profile ==========
    # path('dashboard/', DashboardView.as_view(), name='dashboard'),  # OLD - Commented out, using get_dashboard instead
    path('profile/', ProfileView.as_view(), name='profile'),
    
    # ========== NEW REST API ENDPOINTS (WORKING) ==========
    # Note: These are prefixed with 'api/trainee/' in lms_backend/urls.py via include()
    path('courses/', get_courses, name='api-courses'),
    path('course/<str:course_id>/', api_get_course_detail, name='api-course-detail'),
    path('course/<str:course_id>/start/', api_start_course, name='api-start-course'),
    path('course/<str:course_id>/modules/', get_course_modules, name='api-course-modules'),
    path('module/<str:module_id>/', get_module_content, name='api-module-detail'),
    path('module/<str:module_id>/content/', api_get_module_mixed_content, name='module-mixed-content'),
    path('module/<str:module_id>/complete/', mark_module_complete, name='api-module-complete'),
    path('videos/<str:video_id>/', get_video, name='api-video-detail'),
    path('dashboard/', get_dashboard, name='api-dashboard'),  # NEW - Function-based view with correct user_id handling
    path('convert-ppt/<str:resource_id>/', convert_ppt_to_pdf, name='convert-ppt-to-pdf'),
    path('module/<str:module_id>/time/', track_learning_time, name='learning-time'),
    path('module/<str:module_id>/videos-mongodb/', get_module_videos_from_mongodb, name='module-videos-mongodb'),
    path('module/<str:module_id>/pdfs-mongodb/', get_module_pdfs_from_mongodb, name='module-pdfs-mongodb'),
    path('module/<str:module_id>/quizzes-postgresql/', get_module_quizzes_postgresql, name='module-quizzes-postgresql'),
    path('module/<str:module_id>/all-content/', get_module_all_content, name='module-all-content'),
    path('module/<str:module_id>/content-detailed/', get_module_content_detailed, name='module-content-detailed'),
    
    # Module Quizzes (Trainer: CRUD, Trainee: View)
    path('module/<str:module_id>/quiz/', create_module_quiz, name='create-quiz'),
    path('module/<str:module_id>/quizzes/', get_module_quizzes, name='module-quizzes'),
    path('quiz/<str:quiz_id>/', get_quiz_detail, name='quiz-detail'),
    path('quiz/<str:quiz_id>/update/', update_module_quiz, name='update-quiz'),
    path('quiz/<str:quiz_id>/delete/', delete_module_quiz, name='delete-quiz'),
    path('quiz/<str:quiz_id>/question/', add_quiz_question, name='add-quiz-question'),
    
    # Trainer Quiz Management (positioning quizzes anywhere in module)
    path('trainer/module/<str:module_id>/quiz/create/', create_quiz_in_module, name='trainer-create-quiz'),
    path('trainer/quiz/<str:quiz_id>/position/', update_quiz_position, name='trainer-update-quiz-position'),
    path('trainer/module/<str:module_id>/content-positions/', get_module_content_positions, name='trainer-module-content-positions'),
    
    # Quiz Attempt Routes
    path('quiz/<str:quiz_id>/start/', start_quiz_attempt, name='start-quiz-attempt'),
    path('quiz/<str:quiz_id>/status/', check_quiz_status, name='check-quiz-status'),
    path('quiz/attempt/<str:attempt_id>/submit/', submit_quiz_attempt, name='submit-quiz-attempt'),
    path('quiz/attempt/<str:attempt_id>/result/', get_quiz_attempt_result, name='quiz-attempt-result'),
    
    # Progress Tracking
    path('course/<str:course_id>/progress/', get_progress, name='get-progress'),
    path('course/<str:course_id>/progress/update/', update_progress, name='update-progress'),
    path('course/<str:course_id>/completed/', get_completed_content, name='get-completed-content'),
    
    # ========== NEW: MODULE SEQUENCE MANAGEMENT ==========
    path('module/<str:module_id>/access/', check_module_access, name='check-module-access'),
    path('course/<str:course_id>/modules/initialize/', initialize_course_modules, name='initialize-modules'),
    path('course/<str:course_id>/modules/progress/', get_module_progress_list, name='module-progress-list'),
    path('module/<str:module_id>/progress/update/', update_module_progress, name='update-module-progress'),
    path('module/<str:module_id>/complete/', mark_module_completed, name='mark-module-completed'),
    
    # ========== NEW: QUIZ RESULTS & SCORING ==========
    path('quiz/process-attempt/', process_quiz_attempt, name='process-quiz-attempt'),
    path('quiz/results/', get_quiz_results, name='get-quiz-results'),
    path('quiz/<str:quiz_id>/best-attempt/', get_best_attempt, name='get-best-attempt'),
    path('quiz/<str:quiz_id>/statistics/', get_quiz_statistics, name='get-quiz-statistics'),
    path('quiz/validate/<str:attempt_id>/', validate_quiz_attempt, name='validate-quiz-attempt'),
    
    # ========== NEW: LEADERBOARDS ==========
    path('leaderboard/individual/', get_individual_leaderboard, name='individual-leaderboard'),
    path('leaderboard/individual/<str:course_id>/', get_individual_leaderboard, name='individual-leaderboard-course'),
    path('leaderboard/team/', get_team_leaderboard, name='team-leaderboard'),
    path('leaderboard/team/<str:course_id>/', get_team_leaderboard, name='team-leaderboard-course'),
    path('leaderboard/calculate/', calculate_leaderboards, name='calculate-leaderboards'),
    path('leaderboard/user/<str:user_id>/rank/', get_user_rank, name='user-rank'),
    path('leaderboard/user/<str:user_id>/rank/<str:course_id>/', get_user_rank, name='user-rank-course'),
    
    # Module Learning Resources (Trainer: CRUD, Trainee: View in mixed content)
    path('module/<str:module_id>/resource/', create_learning_resource, name='create-resource'),
    path('resource/<str:resource_id>/update/', update_learning_resource, name='update-resource'),
    path('resource/<str:resource_id>/delete/', delete_learning_resource, name='delete-resource'),
    
    # In-Content Questions
    path('module/<str:module_id>/questions/', get_module_questions, name='module-questions'),
    path('module/<str:module_id>/questions/answer/', answer_module_question, name='answer-question'),
    
    # Notes
    path('module/<str:module_id>/notes/', get_module_notes, name='module-notes'),
    path('module/<str:module_id>/notes/create/', create_module_note, name='create-note'),
    path('module/<str:module_id>/notes/<str:note_id>/update/', update_module_note, name='update-note'),
    path('module/<str:module_id>/notes/<str:note_id>/delete/', delete_module_note, name='delete-note'),
    
    # ========== SECTION 6.3: Performance & History ==========
    path('history/', get_consolidated_history, name='consolidated-history'),
    path('progress/stats/', get_user_progress_stats, name='progress-stats'),
    path('test-results/', get_test_results, name='test-results'),
    path('assignment-results/', get_assignment_results, name='assignment-results'),
    path('feedback/received/', get_trainer_feedback, name='trainer-feedback'),
    path('badges/', get_earned_badges, name='earned-badges'),
    path('points/', get_points_breakdown, name='points-breakdown'),
    path('leaderboard/', get_user_leaderboard, name='user-leaderboard'),
    path('appraisal-summary/', get_appraisal_summary, name='appraisal-summary'),
    
    # ========== SECTION 7.1: Notifications ==========
    path('notifications/', get_notifications, name='notifications'),
    path('notification/<str:notification_id>/read/', mark_notification_read, name='mark-notification-read'),
    path('notifications/mark-all-read/', mark_all_notifications_read, name='mark-all-read'),
    
    # ========== SECTION 7.2: Feedback Submission ==========
    path('feedback/', submit_feedback, name='submit-feedback'),
    
    # ========== SECTION 7.3: Screentime Tracking ==========
    path('screentime/module/<str:module_id>/start/', start_module_session, name='start-module-session'),
    path('screentime/module/<str:module_id>/track/', record_screentime, name='record-screentime'),
    path('screentime/module/<str:module_id>/', get_module_screentime, name='module-screentime'),
    path('screentime/course/<str:course_id>/', get_course_screentime, name='course-screentime'),
    path('screentime/total/', get_total_screentime, name='total-screentime'),
    path('screentime/analytics/', get_screentime_analytics, name='screentime-analytics'),
    
    # ========== SECTION 8: Videos ==========
    path('videos/lesson/<str:lesson_id>/', get_lesson_videos, name='lesson-videos'),
    path('videos/course/<str:course_id>/', get_course_videos, name='course-videos'),
    path('videos/<str:video_id>/record_view/', record_video_view, name='record-video-view'),
    # Direct video streaming
    path('video/stream/<str:resource_id>/', stream_video, name='stream-video'),
    path('video/player/<str:resource_id>/', get_video_player_data, name='video-player'),
    # Alias endpoints matching documented URIs
    path('video/<str:video_id>/', get_video_detail, name='video-detail'),
    path('video/<str:resource_id>/', get_video_from_mongodb, name='video-mongodb'),
    path('video/<str:video_id>/progress/', record_video_view, name='video-progress'),
    
    # ========== SECTION 8.1: Media Files (PDF, PPT, Videos) ==========
    path('resource/<str:resource_id>/file/', get_resource_file, name='get-resource-file'),
    path('media/<str:folder_type>/list/', get_media_files_list, name='media-files-list'),
    path('media-files/summary/', get_media_files_summary, name='media-files-summary'),
    
    # Simple note endpoints matching documented URIs
    path('note/<str:note_id>/', note_by_id, name='note-by-id'),
    # Aliases for slash-style documented endpoints
    path('test/results/', get_test_results, name='test-results-slash'),
    path('assignment/results/', get_assignment_results, name='assignment-results-slash'),
    path('test/<str:pk>/', TestViewSet.as_view({'get': 'retrieve'}), name='test-detail-slash'),
    path('tests/', TestViewSet.as_view({'get': 'list'}), name='tests-list-slash'),
    path('quiz/<str:pk>/', TestViewSet.as_view({'get': 'retrieve'}), name='quiz-detail-slash'),
    path('quiz/<str:pk>/attempt/', TestViewSet.as_view({'post': 'start_attempt'}), name='quiz-start-slash'),
    path('quiz/attempt/<str:attempt_id>/submit/', submit_quiz_attempt_by_attempt, name='quiz-attempt-submit-slash'),
    # Alias mappings for 'test' style documented endpoints
    path('test/<str:pk>/attempt/', TestViewSet.as_view({'post': 'start_attempt'}), name='test-start-slash'),
    path('test/attempt/<str:attempt_id>/submit/', submit_quiz_attempt_by_attempt, name='test-attempt-submit-slash'),
    path('test/attempt/<str:attempt_id>/result/', get_test_attempt_result, name='test-attempt-result-slash'),
    path('assignments/', AssignmentViewSet.as_view({'get': 'list'}), name='assignments-list-slash'),
    path('assignment/<str:pk>/', AssignmentViewSet.as_view({'get': 'retrieve'}), name='assignment-detail-slash'),
    path('assignment/<str:assignment_id>/submit/', submit_assignment_by_id, name='assignment-submit-slash'),
    path('assignment/submission/<str:pk>/', AssignmentSubmissionViewSet.as_view({'get': 'retrieve'}), name='assignment-submission-detail-slash'),
    path('media/files/', get_all_media_files, name='all-media-files'),
    path('media/<str:file_type>/', get_media_by_type, name='media-by-type'),
    
    # Include router URLs (tests, attempts, assignments)
    path('', include(router.urls)),
]
