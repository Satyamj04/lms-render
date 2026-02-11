"""
Progress tracking endpoints for trainee
Integrated with module_progress table for sequential access control
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.db import connection, transaction
from admin.models import UserProfile
import uuid
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def get_session_user(request):
    """Get UserProfile from request or return first available user"""
    # Check for user_id in request data or GET params FIRST (from frontend localStorage)
    user_id = request.data.get('user_id') if hasattr(request, 'data') else None
    if not user_id:
        user_id = request.GET.get('user_id')
    if not user_id:
        user_id = request.session.get('user_id')
    
    if user_id:
        try:
            user = UserProfile.objects.get(id=user_id)
            logger.info(f"✅ Found user by ID: {user.email} ({user_id})")
            return user
        except UserProfile.DoesNotExist:
            logger.warning(f"⚠️ User {user_id} not found in database")
    
    # Try Django authenticated user
    if request.user.is_authenticated:
        try:
            if hasattr(request.user, 'email') and request.user.email:
                user = UserProfile.objects.get(email=request.user.email)
                logger.info(f"✅ Found user by auth email: {user.email}")
                return user
        except UserProfile.DoesNotExist:
            pass
    
    # No fallback - user must provide user_id
    logger.warning(f"⚠️ No valid user_id provided and no authenticated user")
    return None


@api_view(['POST'])
@permission_classes([AllowAny])
@transaction.atomic  # Ensure database transaction is committed
def update_progress(request, course_id):
    """
    Update user progress for a course
    Now also updates module_progress table for sequential access control
    Expects: { "module_id": "...", "content_id": "...", "content_type": "video|quiz|pdf|ppt", "completed": true, "time_spent_minutes": 0 }
    """
    try:
        # Get user using helper function
        user = get_session_user(request)
        
        if not user:
            logger.error("No user found - authentication failed")
            return Response(
                {"error": "User not authenticated"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        user_id = str(user.id)  # UserProfile.id maps to user_id column
        logger.info(f"✅ User authenticated: {user.email} (ID: {user_id})")
        
        module_id = request.data.get('module_id')
        content_id = request.data.get('content_id')
        content_type = request.data.get('content_type')
        completed = request.data.get('completed', True)
        time_spent_minutes = request.data.get('time_spent_minutes', 0)
        
        logger.info(f"Update progress called: user={user_id}, course={course_id}, module={module_id}, content={content_id}, type={content_type}, completed={completed}")
        
        if not all([module_id, content_id, content_type]):
            return Response(
                {"error": "Missing required fields"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cursor = connection.cursor()
        
        # First, get the module's course_id to ensure consistency
        cursor.execute("""
            SELECT course_id FROM modules WHERE module_id = %s;
        """, [str(module_id)])
        
        module_course = cursor.fetchone()
        if module_course:
            course_id = str(module_course[0])
        
        # Get or create user_progress record
        cursor.execute("""
            SELECT progress_id, modules_completed, total_modules, completion_percentage
            FROM user_progress
            WHERE user_id = %s AND course_id = %s
        """, [str(user_id), str(course_id)])
        
        progress_row = cursor.fetchone()
        
        # Get total modules count
        cursor.execute("""
            SELECT COUNT(*) FROM modules WHERE course_id = %s
        """, [str(course_id)])
        total_modules = cursor.fetchone()[0]
        
        if not progress_row:
            # Create new progress record
            progress_id = uuid.uuid4()
            cursor.execute("""
                INSERT INTO user_progress (
                    progress_id, user_id, course_id, completion_percentage,
                    total_points_earned, average_score, time_spent_minutes,
                    modules_completed, total_modules, tests_passed, tests_attempted,
                    assignments_submitted, assignments_graded, started_at, last_activity,
                    created_at, updated_at
                ) VALUES (
                    %s, %s, %s, 0, 0, 0, 0, 0, %s, 0, 0, 0, 0, NOW(), NOW(), NOW(), NOW()
                )
            """, [str(progress_id), str(user_id), str(course_id), total_modules])
            modules_completed = 0
            completion_percentage = 0
        else:
            progress_id = progress_row[0]
            modules_completed = progress_row[1] or 0
            completion_percentage = progress_row[3] or 0
        
        # If module is completed, update module_completions table (existing table)
        if completed and module_id:
            logger.info(f"Marking module {module_id} as completed for user {user_id}")
            
            # Check if module_completions entry exists
            cursor.execute("""
                SELECT completion_id, is_completed FROM module_completions
                WHERE user_id = %s AND module_id = %s;
            """, [str(user_id), str(module_id)])
            
            module_comp = cursor.fetchone()
            
            if not module_comp:
                # Create module_completions entry
                logger.info(f"Creating new module_completions entry")
                cursor.execute("""
                    INSERT INTO module_completions (
                        completion_id, user_id, module_id, 
                        completion_percentage, is_completed, time_spent_minutes,
                        completed_at, created_at, updated_at
                    ) VALUES (
                        gen_random_uuid(), %s, %s, 100, TRUE, %s, NOW(), NOW(), NOW()
                    );
                """, [str(user_id), str(module_id), time_spent_minutes])
                logger.info(f"✅ Created module_completions entry")
            elif not module_comp[1]:  # Not yet marked as completed
                # Update existing module_completions
                logger.info(f"Updating existing module_completions entry")
                cursor.execute("""
                    UPDATE module_completions
                    SET completion_percentage = 100,
                        is_completed = TRUE,
                        completed_at = NOW(),
                        time_spent_minutes = time_spent_minutes + %s,
                        updated_at = NOW()
                    WHERE user_id = %s AND module_id = %s;
                """, [time_spent_minutes, str(user_id), str(module_id)])
                logger.info(f"✅ Updated module_completions entry")
            else:
                logger.info(f"Module already marked as completed")
        
        # Count completed modules from module_completions table (existing table)
        cursor.execute("""
            SELECT COUNT(*) FROM module_completions
            WHERE user_id = %s AND module_id IN (
                SELECT module_id FROM modules WHERE course_id = %s
            ) AND is_completed = TRUE;
        """, [str(user_id), str(course_id)])
        
        modules_completed_count = cursor.fetchone()
        if modules_completed_count and modules_completed_count[0] > 0:
            modules_completed = modules_completed_count[0]
        
        # Calculate completion percentage based on total content
        new_completion = int((modules_completed / total_modules) * 100) if total_modules > 0 else 0
        
        logger.info(f"Final progress: {modules_completed}/{total_modules} modules = {new_completion}%")
        
        # Update progress record
        cursor.execute("""
            UPDATE user_progress
            SET completion_percentage = %s,
                modules_completed = %s,
                time_spent_minutes = time_spent_minutes + %s,
                last_activity = NOW(),
                completed_at = CASE 
                    WHEN %s = 100 AND completed_at IS NULL THEN NOW()
                    ELSE completed_at
                END,
                updated_at = NOW()
            WHERE progress_id = %s
        """, [new_completion, modules_completed, time_spent_minutes, 
              new_completion, str(progress_id)])
        
        logger.info(f"✅ Progress updated successfully")
        
        # Transaction will be committed automatically by @transaction.atomic decorator
        cursor.close()
        
        return Response({
            "success": True,
            "progress_id": str(progress_id),
            "completion_percentage": new_completion,
            "modules_completed": modules_completed,
            "total_modules": total_modules
        })
        
    except Exception as e:
        logger.error(f"Error updating progress: {str(e)}")
        # Transaction will be rolled back automatically by @transaction.atomic decorator
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_progress(request, course_id):
    """
    Get user progress for a course
    Includes both overall progress and per-module progress
    """
    try:
        # Get user using helper function
        user = get_session_user(request)
        
        if not user:
            logger.error("No user found - authentication failed")
            return Response(
                {"error": "User not authenticated"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        user_id = str(user.id)  # UserProfile.id maps to user_id column
        logger.info(f"Getting progress for user: {user.email} (ID: {user_id})")
        
        cursor = connection.cursor()
        
        # Get overall progress
        cursor.execute("""
            SELECT progress_id, completion_percentage, modules_completed, 
                   total_modules, total_points_earned, tests_passed, 
                   tests_attempted, last_activity, status, time_spent_minutes
            FROM user_progress
            WHERE user_id = %s AND course_id = %s
        """, [str(user_id), str(course_id)])
        
        progress_row = cursor.fetchone()
        
        if not progress_row:
            cursor.close()
            return Response({
                "completion_percentage": 0,
                "modules_completed": 0,
                "total_modules": 0,
                "status": "not_started",
                "modules": []
            })
        
        # Get per-module progress from module_completions (existing table)
        cursor.execute("""
            SELECT 
                mc.module_id,
                CASE 
                    WHEN mc.is_completed THEN 'completed'
                    WHEN mc.completion_percentage > 0 THEN 'in_progress'
                    ELSE 'not_started'
                END as status,
                FALSE as is_locked,
                mc.completion_percentage,
                mc.time_spent_minutes,
                m.title,
                m.sequence_order
            FROM modules m
            LEFT JOIN module_completions mc ON m.module_id = mc.module_id AND mc.user_id = %s
            WHERE m.course_id = %s
            ORDER BY m.sequence_order ASC;
        """, [str(user_id), str(course_id)])
        
        module_columns = ['module_id', 'status', 'is_locked', 'completion_percentage', 
                         'time_spent_minutes', 'title', 'sequence_order']
        modules = [dict(zip(module_columns, row)) for row in cursor.fetchall()]
        
        cursor.close()
        
        return Response({
            "progress_id": str(progress_row[0]),
            "completion_percentage": progress_row[1] or 0,
            "modules_completed": progress_row[2] or 0,
            "total_modules": progress_row[3] or 0,
            "total_points_earned": progress_row[4] or 0,
            "tests_passed": progress_row[5] or 0,
            "tests_attempted": progress_row[6] or 0,
            "last_activity": progress_row[7],
            "status": progress_row[8] or "in_progress",
            "time_spent_minutes": progress_row[9] or 0,
            "modules": modules
        })
        
    except Exception as e:
        logger.error(f"Error getting progress: {str(e)}")
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_completed_content(request, course_id):
    """
    Get list of completed module IDs for a course
    Returns array of module IDs that have been completed
    Frontend will mark all content in those modules as complete
    """
    try:
        user = get_session_user(request)
        
        if not user:
            return Response(
                {"error": "User not authenticated"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        user_id = str(user.id)
        cursor = connection.cursor()
        
        # Get all completed modules for this course
        cursor.execute("""
            SELECT DISTINCT mc.module_id
            FROM module_completions mc
            INNER JOIN modules m ON mc.module_id = m.module_id
            WHERE mc.user_id = %s 
              AND m.course_id = %s 
              AND mc.is_completed = TRUE
        """, [user_id, str(course_id)])
        
        completed_module_ids = [str(row[0]) for row in cursor.fetchall()]
        cursor.close()
        
        logger.info(f"✅ Found {len(completed_module_ids)} completed modules for user {user.email}: {completed_module_ids}")
        
        return Response({
            "success": True,
            "completed_modules": completed_module_ids
        })
        
    except Exception as e:
        logger.error(f"Error getting completed content: {str(e)}")
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
