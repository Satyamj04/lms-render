"""
Module Sequence Management Service
Handles module locking/unlocking based on sequential completion
"""
from django.db import connection
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ModuleSequenceService:
    """Service for managing module access based on sequence"""
    
    @staticmethod
    def initialize_module_progress(user_id, course_id):
        """
        Initialize module progress for a user enrolled in a course
        First module is unlocked, rest are locked
        """
        try:
            with connection.cursor() as cursor:
                # Get all modules for the course ordered by sequence
                cursor.execute("""
                    SELECT module_id, sequence_order, is_mandatory
                    FROM modules
                    WHERE course_id = %s
                    ORDER BY sequence_order ASC;
                """, [str(course_id)])
                
                modules = cursor.fetchall()
                
                if not modules:
                    logger.warning(f"No modules found for course {course_id}")
                    return False
                
                # Create module_progress entries for each module
                for idx, (module_id, sequence_order, is_mandatory) in enumerate(modules):
                    # First module is unlocked, rest are locked
                    is_locked = idx != 0
                    
                    cursor.execute("""
                        INSERT INTO module_progress 
                        (progress_id, user_id, module_id, course_id, status, 
                         is_locked, time_spent_minutes, completion_percentage, created_at, updated_at)
                        VALUES (gen_random_uuid(), %s, %s, %s, 'not_started', %s, 0, 0, NOW(), NOW())
                        ON CONFLICT (user_id, module_id) DO NOTHING;
                    """, [str(user_id), str(module_id), str(course_id), is_locked])
                
                logger.info(f"Initialized {len(modules)} modules for user {user_id} in course {course_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error initializing module progress: {str(e)}")
            raise
    
    @staticmethod
    def check_module_access(user_id, module_id):
        """
        Check if a user can access a specific module
        Returns: (can_access: bool, is_locked: bool, reason: str)
        """
        try:
            with connection.cursor() as cursor:
                # Get module progress
                cursor.execute("""
                    SELECT is_locked, status
                    FROM module_progress
                    WHERE user_id = %s AND module_id = %s;
                """, [str(user_id), str(module_id)])
                
                result = cursor.fetchone()
                
                if not result:
                    # No progress entry - initialize it
                    cursor.execute("""
                        SELECT course_id FROM modules WHERE module_id = %s;
                    """, [str(module_id)])
                    
                    course_result = cursor.fetchone()
                    if course_result:
                        course_id = course_result[0]
                        ModuleSequenceService.initialize_module_progress(user_id, course_id)
                        
                        # Re-fetch after initialization
                        cursor.execute("""
                            SELECT is_locked, status
                            FROM module_progress
                            WHERE user_id = %s AND module_id = %s;
                        """, [str(user_id), str(module_id)])
                        result = cursor.fetchone()
                
                if not result:
                    return False, True, "Module not found"
                
                is_locked, status = result
                
                if is_locked:
                    return False, True, "Previous modules must be completed first"
                
                return True, False, "Access granted"
                
        except Exception as e:
            logger.error(f"Error checking module access: {str(e)}")
            return False, True, "Error checking access"
    
    @staticmethod
    def unlock_next_module(user_id, current_module_id):
        """
        Unlock the next module in sequence after completing current module
        """
        try:
            with connection.cursor() as cursor:
                # Get course_id and sequence_order of current module
                cursor.execute("""
                    SELECT m.course_id, m.sequence_order
                    FROM modules m
                    WHERE m.module_id = %s;
                """, [str(current_module_id)])
                
                result = cursor.fetchone()
                if not result:
                    logger.warning(f"Current module {current_module_id} not found")
                    return False
                
                course_id, current_sequence = result
                
                # Find next module in sequence
                cursor.execute("""
                    SELECT module_id
                    FROM modules
                    WHERE course_id = %s AND sequence_order > %s
                    ORDER BY sequence_order ASC
                    LIMIT 1;
                """, [str(course_id), current_sequence])
                
                next_module = cursor.fetchone()
                
                if not next_module:
                    logger.info(f"No next module found - {current_module_id} is the last module")
                    return True  # Not an error - just the last module
                
                next_module_id = next_module[0]
                
                # Unlock the next module
                cursor.execute("""
                    UPDATE module_progress
                    SET is_locked = FALSE, updated_at = NOW()
                    WHERE user_id = %s AND module_id = %s;
                """, [str(user_id), str(next_module_id)])
                
                logger.info(f"Unlocked module {next_module_id} for user {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error unlocking next module: {str(e)}")
            raise
    
    @staticmethod
    def mark_module_completed(user_id, module_id, time_spent_minutes=0):
        """
        Mark a module as completed and unlock the next module
        Also updates the existing user_progress table
        """
        try:
            with connection.cursor() as cursor:
                # Update module progress to completed
                cursor.execute("""
                    UPDATE module_progress
                    SET status = 'completed',
                        completion_percentage = 100,
                        completed_at = NOW(),
                        time_spent_minutes = time_spent_minutes + %s,
                        updated_at = NOW()
                    WHERE user_id = %s AND module_id = %s
                    RETURNING course_id;
                """, [time_spent_minutes, str(user_id), str(module_id)])
                
                result = cursor.fetchone()
                if not result:
                    logger.warning(f"Module progress not found for user {user_id}, module {module_id}")
                    return False
                
                course_id = result[0]
                
                # Update user_progress table (existing table)
                ModuleSequenceService._update_user_progress(user_id, course_id, time_spent_minutes)
                
                # Unlock next module
                ModuleSequenceService.unlock_next_module(user_id, module_id)
                
                logger.info(f"Marked module {module_id} as completed for user {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error marking module completed: {str(e)}")
            raise
    
    @staticmethod
    def update_module_progress(user_id, module_id, completion_percentage, time_spent_minutes=0):
        """
        Update module progress without completing it
        Also syncs with user_progress table
        """
        try:
            with connection.cursor() as cursor:
                # Get course_id first
                cursor.execute("""
                    SELECT course_id FROM module_progress
                    WHERE user_id = %s AND module_id = %s;
                """, [str(user_id), str(module_id)])
                
                course_result = cursor.fetchone()
                if not course_result:
                    logger.warning(f"Module progress not found for user {user_id}, module {module_id}")
                    return False
                
                course_id = course_result[0]
                
                # Update status based on completion
                if completion_percentage == 0:
                    status = 'not_started'
                elif completion_percentage == 100:
                    status = 'completed'
                    # If completed, also unlock next module
                    ModuleSequenceService.unlock_next_module(user_id, module_id)
                else:
                    status = 'in_progress'
                
                # Start tracking time when first accessed
                cursor.execute("""
                    UPDATE module_progress
                    SET status = %s,
                        completion_percentage = %s,
                        time_spent_minutes = time_spent_minutes + %s,
                        started_at = COALESCE(started_at, NOW()),
                        completed_at = CASE WHEN %s = 100 THEN NOW() ELSE completed_at END,
                        updated_at = NOW()
                    WHERE user_id = %s AND module_id = %s;
                """, [status, completion_percentage, time_spent_minutes, 
                      completion_percentage, str(user_id), str(module_id)])
                
                # Update user_progress table
                ModuleSequenceService._update_user_progress(user_id, course_id, time_spent_minutes)
                
                logger.info(f"Updated module progress: user {user_id}, module {module_id}, {completion_percentage}%")
                return True
                
        except Exception as e:
            logger.error(f"Error updating module progress: {str(e)}")
            raise
    
    @staticmethod
    def get_module_progress_list(user_id, course_id):
        """
        Get all module progress for a user in a course
        Returns list with lock status, completion, etc.
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        mp.module_id,
                        mp.status,
                        mp.is_locked,
                        mp.completion_percentage,
                        mp.time_spent_minutes,
                        mp.started_at,
                        mp.completed_at,
                        m.title,
                        m.sequence_order,
                        m.is_mandatory
                    FROM module_progress mp
                    JOIN modules m ON mp.module_id = m.module_id
                    WHERE mp.user_id = %s AND mp.course_id = %s
                    ORDER BY m.sequence_order ASC;
                """, [str(user_id), str(course_id)])
                
                columns = ['module_id', 'status', 'is_locked', 'completion_percentage', 
                          'time_spent_minutes', 'started_at', 'completed_at', 'title', 
                          'sequence_order', 'is_mandatory']
                
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]
                return results
                
        except Exception as e:
            logger.error(f"Error getting module progress list: {str(e)}")
            raise
    
    @staticmethod
    def _update_user_progress(user_id, course_id, time_spent_minutes):
        """
        Update the existing user_progress table with aggregated data from module_progress
        """
        try:
            with connection.cursor() as cursor:
                # Count completed modules
                cursor.execute("""
                    SELECT COUNT(*) FROM module_progress
                    WHERE user_id = %s AND course_id = %s AND status = 'completed';
                """, [str(user_id), str(course_id)])
                
                modules_completed = cursor.fetchone()[0] or 0
                
                # Get total modules
                cursor.execute("""
                    SELECT COUNT(*) FROM modules WHERE course_id = %s;
                """, [str(course_id)])
                
                total_modules = cursor.fetchone()[0] or 0
                
                # Calculate overall completion percentage
                completion_percentage = int((modules_completed / total_modules) * 100) if total_modules > 0 else 0
                
                # Check if user_progress record exists
                cursor.execute("""
                    SELECT progress_id FROM user_progress
                    WHERE user_id = %s AND course_id = %s;
                """, [str(user_id), str(course_id)])
                
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing record
                    cursor.execute("""
                        UPDATE user_progress
                        SET modules_completed = %s,
                            total_modules = %s,
                            completion_percentage = %s,
                            time_spent_minutes = time_spent_minutes + %s,
                            last_activity = NOW(),
                            updated_at = NOW(),
                            status = CASE 
                                WHEN %s = 100 THEN 'completed'
                                WHEN %s > 0 THEN 'in_progress'
                                ELSE 'not_started'
                            END
                        WHERE user_id = %s AND course_id = %s;
                    """, [modules_completed, total_modules, completion_percentage, 
                          time_spent_minutes, completion_percentage, completion_percentage,
                          str(user_id), str(course_id)])
                else:
                    # Create new record
                    cursor.execute("""
                        INSERT INTO user_progress (
                            progress_id, user_id, course_id, completion_percentage,
                            modules_completed, total_modules, time_spent_minutes,
                            total_points_earned, average_score, tests_passed, tests_attempted,
                            assignments_submitted, assignments_graded, 
                            started_at, last_activity, created_at, updated_at, status
                        ) VALUES (
                            gen_random_uuid(), %s, %s, %s, %s, %s, %s, 
                            0, 0, 0, 0, 0, 0, 
                            NOW(), NOW(), NOW(), NOW(), 'in_progress'
                        );
                    """, [str(user_id), str(course_id), completion_percentage, 
                          modules_completed, total_modules, time_spent_minutes])
                
                logger.info(f"Updated user_progress for user {user_id}, course {course_id}: {completion_percentage}%")
                return True
                
        except Exception as e:
            logger.error(f"Error updating user_progress: {str(e)}")
            raise
