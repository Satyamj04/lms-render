"""
Trainer module permissions - Role-based access control for trainer operations
"""
from rest_framework import permissions
from .models import Profile, Course, Enrollment


class IsTrainer(permissions.BasePermission):
    """Only trainers can access"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and hasattr(request.user, 'primary_role') and request.user.primary_role == 'trainer'


class IsTrainerUser(permissions.BasePermission):
    """Permission check using Profile model"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        try:
            profile = Profile.objects.get(id=request.user.id)
            return profile.primary_role == 'trainer'
        except Profile.DoesNotExist:
            return False


class IsTrainerOrReadOnly(permissions.BasePermission):
    """Trainers can edit, others can only read"""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated and hasattr(request.user, 'primary_role') and request.user.primary_role == 'trainer'


class IsTrainerOrAdmin(permissions.BasePermission):
    """Only trainers and admins"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        try:
            profile = Profile.objects.get(id=request.user.id)
            return profile.primary_role in ['trainer', 'admin']
        except Profile.DoesNotExist:
            return False


class CanManageCourse(permissions.BasePermission):
    """
    Trainer can only manage courses they created.
    Admin can manage any course.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        try:
            profile = Profile.objects.get(id=request.user.id)
            return profile.primary_role in ['trainer', 'admin']
        except Profile.DoesNotExist:
            return False

    def has_object_permission(self, request, view, obj):
        try:
            profile = Profile.objects.get(id=request.user.id)
            # Admin can do anything
            if profile.primary_role == 'admin':
                return True
            # Trainer can only edit their own courses
            if profile.primary_role == 'trainer':
                return obj.created_by_id == profile.id
            return False
        except Profile.DoesNotExist:
            return False


class CanManageEnrollment(permissions.BasePermission):
    """
    Trainer can manage enrollments for their courses.
    Admin can manage any enrollment.
    Trainees can view their own enrollments.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return True

    def has_object_permission(self, request, view, obj):
        try:
            profile = Profile.objects.get(id=request.user.id)
            # Admin can do anything
            if profile.primary_role == 'admin':
                return True
            # Trainer can only manage enrollments for their courses
            if profile.primary_role == 'trainer':
                return obj.course.created_by_id == profile.id
            # Trainees can view their own enrollments
            if profile.primary_role == 'trainee':
                return request.method in permissions.SAFE_METHODS and obj.user_id == profile.id
            return False
        except Profile.DoesNotExist:
            return False


class CanViewProgress(permissions.BasePermission):
    """
    Trainer can view progress for their courses.
    Admin can view any progress.
    Trainees can view their own progress.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return True

    def has_object_permission(self, request, view, obj):
        try:
            profile = Profile.objects.get(id=request.user.id)
            # Admin can view anything
            if profile.primary_role == 'admin':
                return True
            # Trainer can view progress for their courses
            if profile.primary_role == 'trainer':
                if hasattr(obj, 'enrollment') and obj.enrollment:
                    return obj.enrollment.course.created_by_id == profile.id
                if hasattr(obj, 'course') and obj.course:
                    return obj.course.created_by_id == profile.id
                return False
            # Trainees can view their own progress
            if profile.primary_role == 'trainee':
                if hasattr(obj, 'user'):
                    return obj.user_id == profile.id
                if hasattr(obj, 'enrollment') and obj.enrollment:
                    return obj.enrollment.user_id == profile.id
                return False
            return False
        except Profile.DoesNotExist:
            return False


class IsTraineeOrTrainerOrAdmin(permissions.BasePermission):
    """Allow trainees (viewing own), trainers, and admins"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return True

    def has_object_permission(self, request, view, obj):
        try:
            profile = Profile.objects.get(id=request.user.id)
            # Admin and trainer can do anything
            if profile.primary_role in ['admin', 'trainer']:
                return True
            # Trainee can only read
            if profile.primary_role == 'trainee':
                return request.method in permissions.SAFE_METHODS
            return False
        except Profile.DoesNotExist:
            return False
