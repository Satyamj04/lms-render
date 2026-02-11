"""
URL configuration for myproject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from trainer.views import (
    dashboard_stats, 
    trainee_courses, 
    trainee_course_detail, 
    trainee_course_start,
    trainee_course_modules,
    trainee_course_completed,
    trainee_course_update,
    trainee_module_content,
    trainee_convert_ppt,
    trainee_quiz_status,
    trainee_quiz_start,
    trainee_quiz_submit,
    trainee_progress_update,
    trainee_leaderboard,
    trainee_tests,
    trainee_assignments,
    trainee_progress_stats,
    trainee_history
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/admin/', include('admin.urls')),
    path('api/trainer/', include('trainer.urls')),
    # path('api/trainee/', include('trainee.urls')),  # Removed - trainee app not in use
    # Trainee dashboard endpoint (uses same logic as trainer dashboard but routes by role)
    path('api/trainee/dashboard/', dashboard_stats, name='trainee-dashboard'),
    path('api/trainee/courses/', trainee_courses, name='trainee-courses'),
    path('api/trainee/course/<uuid:course_id>/', trainee_course_detail, name='trainee-course-detail'),
    path('api/trainee/course/<uuid:course_id>/start/', trainee_course_start, name='trainee-course-start'),
    path('api/trainee/course/<uuid:course_id>/completed/', trainee_course_completed, name='trainee-course-completed'),
    path('api/trainee/course/<uuid:course_id>/modules/', trainee_course_modules, name='trainee-course-modules'),
    path('api/trainee/modules/<uuid:module_id>/', trainee_module_content, name='trainee-module-content'),
    path('api/trainee/module/<uuid:module_id>/content/', trainee_module_content, name='trainee-module-content-alt'),
    path('api/trainee/convert-ppt/<uuid:module_id>/', trainee_convert_ppt, name='trainee-convert-ppt'),
    # Quiz endpoints
    path('api/trainee/quiz/<uuid:quiz_id>/status/', trainee_quiz_status, name='trainee-quiz-status'),
    path('api/trainee/quiz/<uuid:quiz_id>/start/', trainee_quiz_start, name='trainee-quiz-start'),
    path('api/trainee/quiz/attempt/<uuid:attempt_id>/submit/', trainee_quiz_submit, name='trainee-quiz-submit'),
    # Progress tracking
    path('api/trainee/course/<uuid:course_id>/progress/update/', trainee_progress_update, name='trainee-progress-update'),
    # Leaderboard, tests, assignments, progress stats, history
    path('api/trainee/leaderboard/', trainee_leaderboard, name='trainee-leaderboard'),
    path('api/trainee/trainee/tests/', trainee_tests, name='trainee-tests'),
    path('api/trainee/trainee/assignments/', trainee_assignments, name='trainee-assignments'),
    path('api/trainee/progress/stats/', trainee_progress_stats, name='trainee-progress-stats'),
    path('api/trainee/history/', trainee_history, name='trainee-history'),
    # Also include trainer endpoints directly under /api/ for frontend compatibility
    path('api/', include('trainer.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
