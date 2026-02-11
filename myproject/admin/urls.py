from django.urls import path, include
from rest_framework import routers
from .views import AdminUserViewSet, TeamViewSet, metrics, CourseViewSet, AuditViewSet, progress, lms_teams, notifications
from .auth import login, logout
from .trainee_api import get_trainee_courses, get_course_detail

router = routers.DefaultRouter()
router.register(r'users', AdminUserViewSet, basename='admin-users')
router.register(r'teams', TeamViewSet, basename='admin-teams')
router.register(r'courses', CourseViewSet, basename='admin-courses')
router.register(r'audit-logs', AuditViewSet, basename='admin-audit-logs')

urlpatterns = [
    path('', include(router.urls)),
    path('metrics/', metrics, name='admin-metrics'),
    path('progress/', progress, name='admin-progress'),
    path('lms-teams/', lms_teams, name='admin-lms-teams'),
    path('notifications/', notifications, name='admin-notifications'),
    path('auth/login/', login, name='admin-login'),
    path('auth/logout/', logout, name='admin-logout'),
    path('trainee/courses/', get_trainee_courses, name='trainee-courses'),
    path('course/<str:course_id>/', get_course_detail, name='course-detail'),
]
