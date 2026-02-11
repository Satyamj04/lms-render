"""
Screentime Tracking Service
Handles calculation and tracking of user learning time across modules and courses
"""

from django.utils import timezone
from trainee.models import User, UserProgress, ModuleCompletion, Course, Module
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class ScreentimeService:
    """Service for tracking and calculating screentime metrics"""
    
    @staticmethod
    def start_module_session(user, module):
        """
        Start a learning session for a module
        Records the timestamp when user begins learning
        
        Returns:
            dict: session info with session_start_time
        """
        if not user or not module:
            return None
        
        try:
            completion, created = ModuleCompletion.objects.get_or_create(
                module=module,
                user=user,
                defaults={
                    'time_spent_minutes': 0,
                }
            )
            
            # Store session start in a way that can be tracked
            # We'll use the updated_at timestamp as last activity marker
            completion.save()
            
            return {
                'session_started': True,
                'session_start_time': timezone.now().isoformat(),
                'module_id': str(module.module_id),
            }
        except Exception as e:
            logger.error(f"Error starting module session: {str(e)}")
            return None
    
    @staticmethod
    def record_screentime(user, module, time_spent_seconds):
        """
        Record time spent on a module
        
        Args:
            user: User instance
            module: Module instance  
            time_spent_seconds: int - seconds spent on this module
        
        Returns:
            dict: Updated module completion with new time
        """
        if not user or not module or time_spent_seconds < 0:
            return None
        
        try:
            completion, created = ModuleCompletion.objects.get_or_create(
                module=module,
                user=user,
            )
            
            # Convert seconds to minutes and accumulate
            additional_minutes = time_spent_seconds // 60
            completion.time_spent_minutes += additional_minutes
            
            # Update last activity
            completion.updated_at = timezone.now()
            completion.save()
            
            # Update course progress time_spent_minutes
            course = module.course
            progress, _ = UserProgress.objects.get_or_create(user=user, course=course)
            progress.time_spent_minutes += additional_minutes
            progress.last_activity = timezone.now()
            progress.save()
            
            return {
                'success': True,
                'module_id': str(module.module_id),
                'time_added_minutes': additional_minutes,
                'total_time_minutes': completion.time_spent_minutes,
                'course_total_time_minutes': progress.time_spent_minutes,
            }
        except Exception as e:
            logger.error(f"Error recording screentime: {str(e)}")
            return None
    
    @staticmethod
    def get_module_screentime(user, module):
        """
        Get total time spent on a module
        
        Args:
            user: User instance
            module: Module instance
        
        Returns:
            dict: Screentime data
        """
        try:
            completion = ModuleCompletion.objects.filter(
                user=user,
                module=module
            ).first()
            
            time_minutes = completion.time_spent_minutes if completion else 0
            
            # Calculate hours and remaining minutes
            hours = time_minutes // 60
            minutes = time_minutes % 60
            
            # Get module estimated duration for comparison
            est_duration_minutes = module.estimated_duration_minutes or 0
            est_hours = est_duration_minutes // 60
            est_mins = est_duration_minutes % 60
            
            # Calculate efficiency: actual vs estimated
            efficiency_percentage = 0
            if est_duration_minutes > 0:
                efficiency_percentage = min(100, int((time_minutes / est_duration_minutes) * 100))
            
            return {
                'module_id': str(module.module_id),
                'module_title': module.title,
                'time_spent_minutes': time_minutes,
                'time_spent_formatted': f"{hours}h {minutes}m",
                'time_spent_hours': round(time_minutes / 60, 2),
                'estimated_duration_minutes': est_duration_minutes,
                'estimated_duration_formatted': f"{est_hours}h {est_mins}m",
                'efficiency_percentage': efficiency_percentage,
            }
        except Exception as e:
            logger.error(f"Error getting module screentime: {str(e)}")
            return None
    
    @staticmethod
    def get_course_screentime(user, course):
        """
        Get total screentime for a course (sum of all modules)
        
        Args:
            user: User instance
            course: Course instance
        
        Returns:
            dict: Course screentime data with module breakdown
        """
        try:
            progress = UserProgress.objects.filter(user=user, course=course).first()
            
            total_time_minutes = progress.time_spent_minutes if progress else 0
            
            # Get all modules in course with their screentime
            modules = Module.objects.filter(course=course).order_by('sequence_order')
            
            module_times = []
            for module in modules:
                completion = ModuleCompletion.objects.filter(
                    user=user,
                    module=module
                ).first()
                
                time_mins = completion.time_spent_minutes if completion else 0
                module_times.append({
                    'module_id': str(module.module_id),
                    'module_title': module.title,
                    'time_spent_minutes': time_mins,
                    'time_spent_hours': round(time_mins / 60, 2),
                    'estimated_duration_minutes': module.estimated_duration_minutes or 0,
                })
            
            # Calculate course statistics
            hours = total_time_minutes // 60
            minutes = total_time_minutes % 60
            
            # Get course estimated total duration
            course_est_total = sum(m.get('estimated_duration_minutes', 0) for m in module_times)
            course_est_hours = course_est_total // 60
            course_est_mins = course_est_total % 60
            
            # Calculate efficiency
            efficiency = 0
            if course_est_total > 0:
                efficiency = min(100, int((total_time_minutes / course_est_total) * 100))
            
            return {
                'course_id': str(course.course_id),
                'course_title': course.title,
                'total_time_spent_minutes': total_time_minutes,
                'total_time_spent_formatted': f"{hours}h {minutes}m",
                'total_time_spent_hours': round(total_time_minutes / 60, 2),
                'estimated_course_duration_minutes': course_est_total,
                'estimated_course_duration_formatted': f"{course_est_hours}h {course_est_mins}m",
                'efficiency_percentage': efficiency,
                'module_breakdown': module_times,
                'modules_with_activity': len([m for m in module_times if m['time_spent_minutes'] > 0]),
                'total_modules': len(module_times),
            }
        except Exception as e:
            logger.error(f"Error getting course screentime: {str(e)}")
            return None
    
    @staticmethod
    def get_total_screentime(user):
        """
        Get user's total screentime across all courses
        
        Args:
            user: User instance
        
        Returns:
            dict: Total screentime and breakdown by course
        """
        try:
            # Get all progress records for user
            all_progress = UserProgress.objects.filter(user=user)
            
            total_minutes = sum(p.time_spent_minutes for p in all_progress)
            
            # Get breakdown by course
            courses_breakdown = []
            for progress in all_progress:
                course_data = ScreentimeService.get_course_screentime(user, progress.course)
                if course_data:
                    courses_breakdown.append({
                        'course_id': course_data['course_id'],
                        'course_title': course_data['course_title'],
                        'time_spent_minutes': course_data['total_time_spent_minutes'],
                        'time_spent_hours': course_data['total_time_spent_hours'],
                        'efficiency_percentage': course_data['efficiency_percentage'],
                    })
            
            # Sort by time spent (descending)
            courses_breakdown.sort(key=lambda x: x['time_spent_minutes'], reverse=True)
            
            # Calculate total hours and remaining minutes
            hours = total_minutes // 60
            minutes = total_minutes % 60
            
            # Calculate average time per course
            avg_time_per_course = round(total_minutes / len(all_progress), 2) if all_progress.count() > 0 else 0
            
            return {
                'total_screentime_minutes': total_minutes,
                'total_screentime_formatted': f"{hours}h {minutes}m",
                'total_screentime_hours': round(total_minutes / 60, 2),
                'average_time_per_course_hours': round(avg_time_per_course / 60, 2),
                'courses_count': all_progress.count(),
                'courses_breakdown': courses_breakdown,
            }
        except Exception as e:
            logger.error(f"Error getting total screentime: {str(e)}")
            return None
    
    @staticmethod
    def get_screentime_analytics(user, days=30):
        """
        Get screentime analytics for a period
        
        Args:
            user: User instance
            days: int - number of days to analyze
        
        Returns:
            dict: Analytics including daily breakdown
        """
        try:
            cutoff_date = timezone.now() - timedelta(days=days)
            
            # Get modules with activity in the period
            completions = ModuleCompletion.objects.filter(
                user=user,
                updated_at__gte=cutoff_date
            ).select_related('module__course')
            
            total_minutes = 0
            daily_breakdown = {}
            
            for completion in completions:
                total_minutes += completion.time_spent_minutes
                
                # Group by date
                date_str = completion.updated_at.date().isoformat()
                if date_str not in daily_breakdown:
                    daily_breakdown[date_str] = 0
                daily_breakdown[date_str] += completion.time_spent_minutes
            
            # Calculate statistics
            days_active = len(daily_breakdown)
            avg_per_day = round(total_minutes / days_active, 2) if days_active > 0 else 0
            
            hours = total_minutes // 60
            minutes = total_minutes % 60
            
            return {
                'period_days': days,
                'total_time_minutes': total_minutes,
                'total_time_formatted': f"{hours}h {minutes}m",
                'total_time_hours': round(total_minutes / 60, 2),
                'days_active': days_active,
                'average_time_per_active_day_minutes': avg_per_day,
                'average_time_per_active_day_formatted': f"{int(avg_per_day // 60)}h {int(avg_per_day % 60)}m",
                'daily_breakdown': daily_breakdown,
            }
        except Exception as e:
            logger.error(f"Error calculating screentime analytics: {str(e)}")
            return None
