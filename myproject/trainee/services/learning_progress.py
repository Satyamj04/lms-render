"""
Learning Progress Service - Handles all calculations for dashboard and learning data
Aggregates user progress, calculates points, hours, and course statistics
"""
from django.db.models import Count, Q, Sum, F, Case, When, IntegerField
from trainee.models import User, Course, UserProgress, Leaderboard, BadgeAssignment, TestAttempt, QuizAttempt
from admin.models import CourseAssignment


class LearningProgressService:
    """Service for calculating learning progress and statistics"""
    
    @staticmethod
    def get_user(email=None, user_id=None):
        """Get user by email or id, with fallback to Mukesh Pawar"""
        if user_id:
            try:
                return User.objects.get(user_id=user_id)
            except User.DoesNotExist:
                pass
        
        if email:
            try:
                return User.objects.get(email=email)
            except User.DoesNotExist:
                pass
        
        # Fallback to Mukesh Pawar
        try:
            return User.objects.get(
                email='mukesh.pawar@example.com',
                first_name='Mukesh',
                last_name='Pawar'
            )
        except User.DoesNotExist:
            return None
    
    @staticmethod
    def calculate_total_active_hours(user):
        """Calculate total active hours from UserProgress time_spent_minutes"""
        if not user:
            return 0
        
        total_minutes = UserProgress.objects.filter(user=user).aggregate(
            total=Sum('time_spent_minutes')
        )['total'] or 0
        
        return round(total_minutes / 60, 1)
    
    @staticmethod
    def calculate_total_points(user):
        """Calculate total points earned across all courses"""
        if not user:
            return 0
        
        total_points = UserProgress.objects.filter(user=user).aggregate(
            total=Sum('total_points_earned')
        )['total'] or 0
        
        return total_points
    
    @staticmethod
    def get_leaderboard_rank(user):
        """Get user's rank from leaderboard"""
        if not user:
            return 1
        
        try:
            leaderboard = Leaderboard.objects.get(scope='global', user=user)
            return leaderboard.rank or 1
        except Leaderboard.DoesNotExist:
            return 1
    
    @staticmethod
    def get_user_courses(user):
        """Get all courses assigned to user with progress info"""
        if not user:
            courses = Course.objects.filter(status='published')
        else:
            # Get courses assigned to user or user's teams
            assignments = CourseAssignment.objects.filter(
                Q(assigned_to_user=user) |
                Q(assigned_to_team__members__user=user)
            ).distinct()
            courses = Course.objects.filter(
                Q(assignments__in=assignments) |
                Q(status='published')
            ).distinct()
        
        courses_data = []
        for course in courses:
            if user:
                progress = UserProgress.objects.filter(user=user, course=course).first()
                if progress:
                    completion_rate = progress.completion_percentage or 0
                    modules_completed = progress.modules_completed or 0
                    total_modules = progress.total_modules or 0
                    
                    # Derive status from completion_percentage and completed_at
                    if completion_rate == 100 and progress.completed_at:
                        status_text = 'completed'
                    elif completion_rate > 0 and completion_rate < 100:
                        status_text = 'in_progress'
                    else:
                        status_text = 'not_started'
                else:
                    status_text = 'not_started'
                    completion_rate = 0
                    modules_completed = 0
                    total_modules = course.modules.count()
            else:
                status_text = 'not_started'
                completion_rate = 0
                modules_completed = 0
                total_modules = course.modules.count()
            
            courses_data.append({
                'course_id': str(course.course_id),
                'id': str(course.course_id),
                'title': course.title,
                'description': course.description,
                'status': status_text,
                'completion_percentage': completion_rate,
                'completionRate': completion_rate,
                'progress_percentage': completion_rate,
                'modules_completed': modules_completed,
                'total_modules': total_modules,
                'is_mandatory': course.is_mandatory,
                'estimated_duration_hours': course.estimated_duration_hours,
                'duration': f"{course.estimated_duration_hours} hours" if course.estimated_duration_hours else "Unknown",
                'passing_criteria': course.passing_criteria,
                'course_type': course.course_type,
            })
        
        return courses_data
    
    @staticmethod
    def get_course_stats(user):
        """
        Get statistics about courses
        - total_courses: All assigned + published courses
        - active_courses: Courses with status='in_progress'
        - not_started_courses: Courses with status='not_started'
        - completed_courses: Courses with status='completed'
        """
        if not user:
            courses = Course.objects.filter(status='published')
            return {
                'total_courses': courses.count(),
                'active_courses': 0,
                'not_started_courses': courses.count(),
                'completed_courses': 0,
            }
        
        # Get all courses available to user (assigned or published)
        assigned_courses = CourseAssignment.objects.filter(
            Q(assigned_to_user=user) |
            Q(assigned_to_team__members__user=user)
        ).values_list('course_id', flat=True).distinct()
        
        published_courses = Course.objects.filter(status='published').values_list('course_id', flat=True)
        all_available_ids = set(assigned_courses) | set(published_courses)
        
        # Get progress records for all available courses
        all_progress = UserProgress.objects.filter(
            user=user,
            course_id__in=all_available_ids
        )
        
        # Calculate stats based on completion_percentage and completed_at
        active_courses = 0
        completed_courses = 0
        not_started_courses = 0
        
        progress_course_ids = set()
        
        for progress in all_progress:
            progress_course_ids.add(progress.course_id)
            completion_rate = progress.completion_percentage or 0
            
            # Derive status from completion_percentage and completed_at
            if completion_rate == 100 and progress.completed_at:
                completed_courses += 1
            elif completion_rate > 0 and completion_rate < 100:
                active_courses += 1
            else:  # Not started or 0% completion
                not_started_courses += 1
        
        # Count courses with no progress record yet (truly not started)
        not_started_no_progress = len(all_available_ids - progress_course_ids)
        not_started_courses += not_started_no_progress
        
        total_courses = len(all_available_ids)
        
        return {
            'total_courses': total_courses,
            'active_courses': active_courses,
            'not_started_courses': not_started_courses,
            'completed_courses': completed_courses,
        }
    
    @staticmethod
    def get_dashboard_data(user):
        """Get complete dashboard data for user"""
        if not user:
            # Return default data
            return {
                'total_active_hours': 0,
                'total_points': 0,
                'rank': 1,
                'courses': [],
                'course_stats': {
                    'total_courses': 0,
                    'active_courses': 0,
                    'not_started_courses': 0,
                    'completed_courses': 0,
                },
                'badges_count': 0,
            }
        
        # Calculate all metrics
        total_active_hours = LearningProgressService.calculate_total_active_hours(user)
        total_points = LearningProgressService.calculate_total_points(user)
        rank = LearningProgressService.get_leaderboard_rank(user)
        courses = LearningProgressService.get_user_courses(user)
        course_stats = LearningProgressService.get_course_stats(user)
        
        # Get badges count
        badges_count = BadgeAssignment.objects.filter(user=user).count()
        
        return {
            'total_active_hours': total_active_hours,
            'total_points': total_points,
            'rank': rank,
            'courses': courses,
            'course_stats': course_stats,
            'badges_count': badges_count,
        }
    
    @staticmethod
    def start_course(user, course):
        """
        Start a course - create or update UserProgress record
        Transitions course from 'not_started' to 'in_progress'
        Sets completion_percentage to 1 to mark it as started
        """
        from django.utils import timezone
        
        if not user or not course:
            return None
        
        progress, created = UserProgress.objects.get_or_create(
            user=user,
            course=course,
            defaults={
                'status': 'in_progress',
                'started_at': timezone.now(),
                'total_modules': course.modules.count(),
                'completion_percentage': 1,  # Set to 1 to indicate course has been started
            }
        )
        
        # If already exists but not started yet, update to mark as in_progress
        if not created and progress.completion_percentage == 0:
            progress.status = 'in_progress'
            progress.started_at = timezone.now()
            progress.completion_percentage = 1  # Mark as started
            progress.save()
        
        return progress
    
    @staticmethod
    def update_course_progress(user, course, completion_percentage):
        """
        Update course progress percentage and status
        Automatically transitions to 'completed' when completion reaches 100%
        """
        if not user or not course:
            return None
        
        try:
            progress = UserProgress.objects.get(user=user, course=course)
            progress.completion_percentage = min(completion_percentage, 100)
            
            # Update status based on completion
            if completion_percentage >= 100:
                progress.status = 'completed'
                if not progress.completed_at:
                    from django.utils import timezone
                    progress.completed_at = timezone.now()
            elif progress.status == 'not_started' and completion_percentage > 0:
                # Auto-transition to in_progress if any progress made
                progress.status = 'in_progress'
                if not progress.started_at:
                    from django.utils import timezone
                    progress.started_at = timezone.now()
            
            progress.save()
            return progress
        except UserProgress.DoesNotExist:
            return None
