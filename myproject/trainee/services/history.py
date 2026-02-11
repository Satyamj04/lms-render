"""
History & Results Endpoints
Handles performance history, test results, assignment results, etc.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from trainee.models import (
    User, TestAttempt, AssignmentSubmission, BadgeAssignment,
    UserProgress, Leaderboard
)
from django.db.models import Q
from django.utils import timezone
from datetime import datetime
from trainee.services.api_views import get_session_user
import logging

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_consolidated_history(request):
    """
    GET /trainee/history
    Get consolidated history (completed tests, assignments, scores)
    """
    try:
        user = get_session_user(request)
        if not user:
            return Response(
                {'error': 'User not authenticated'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        user_uuid = str(user.id)
        
        # Use raw SQL to avoid model FK issues
        from django.db import connection
        cursor = connection.cursor()
        
        # Get all completed tests
        cursor.execute("""
            SELECT ta.attempt_id, ta.submitted_at, ta.score, ta.points_earned, 
                   ta.status, ta.passed, t.title as test_title
            FROM test_attempts ta
            INNER JOIN tests t ON ta.test_id = t.test_id
            WHERE ta.user_id = %s AND ta.status IN ('completed', 'abandoned')
            ORDER BY ta.submitted_at DESC
            LIMIT 20
        """, [user_uuid])
        
        test_attempts = []
        for row in cursor.fetchall():
            test_attempts.append({
                'attempt_id': str(row[0]),
                'submitted_at': row[1],
                'score': row[2],
                'points_earned': row[3],
                'status': row[4],
                'passed': row[5],
                'title': row[6]
            })
        
        # Get all submitted assignments
        cursor.execute("""
            SELECT asub.submission_id, asub.submitted_at, asub.score, 
                   asub.status, a.title as assignment_title
            FROM assignment_submissions asub
            INNER JOIN assignments a ON asub.assignment_id = a.assignment_id
            WHERE asub.user_id = %s AND asub.status IN ('submitted', 'graded')
            ORDER BY asub.submitted_at DESC
            LIMIT 20
        """, [user_uuid])
        
        assignments = []
        for row in cursor.fetchall():
            assignments.append({
                'submission_id': str(row[0]),
                'submitted_at': row[1],
                'score': row[2],
                'status': row[3],
                'title': row[4]
            })
        
        history_data = []
        
        # Add test attempts
        for attempt in test_attempts:
            history_data.append({
                'type': 'test',
                'title': attempt['title'],
                'score': attempt['score'],
                'points_earned': attempt['points_earned'],
                'status': attempt['status'],
                'completed_at': attempt['submitted_at'],
                'passed': attempt['passed']
            })
        
        # Add assignments
        for submission in assignments:
            history_data.append({
                'type': 'assignment',
                'title': submission['title'],
                'score': submission['score'],
                'points_earned': 0,  # Assignment submissions don't have points_earned
                'status': submission['status'],
                'submitted_at': submission['submitted_at'],
            })
        
        # Sort by date
        history_data.sort(key=lambda x: x.get('completed_at') or x.get('submitted_at'), reverse=True)
        
        return Response({
            'history': history_data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_test_results(request):
    """
    GET /trainee/test/results
    Get all test results log
    """
    try:
        user = get_session_user(request)
        if not user:
            return Response(
                {'error': 'User not authenticated'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        user_uuid = str(user.id)
        test_attempts = TestAttempt.objects.filter(
            user_id=user_uuid
        ).select_related('test').order_by('-submitted_at')
        
        results = []
        for attempt in test_attempts:
            results.append({
                'attempt_id': str(attempt.attempt_id),
                'test_id': str(attempt.test.test_id),
                'test_title': attempt.test.title,
                'attempt_number': attempt.attempt_number,
                'score': attempt.score,
                'points_earned': attempt.points_earned,
                'passing_score': attempt.test.passing_score,
                'passed': attempt.passed,
                'status': attempt.status,
                'started_at': attempt.started_at,
                'submitted_at': attempt.submitted_at,
                'time_spent_minutes': attempt.time_spent_minutes
            })
        
        return Response({
            'test_results': results
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_assignment_results(request):
    """
    GET /trainee/assignment/results
    Get all assignment results log
    """
    try:
        user = get_session_user(request)
        if not user:
            return Response(
                {'error': 'User not authenticated'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        user_uuid = str(user.id)
        submissions = AssignmentSubmission.objects.filter(
            user_id=user_uuid
        ).select_related('assignment').order_by('-submitted_at')
        
        results = []
        for submission in submissions:
            results.append({
                'submission_id': str(submission.submission_id),
                'assignment_id': str(submission.assignment.assignment_id),
                'assignment_title': submission.assignment.title,
                'attempt_number': submission.attempt_number,
                'score': submission.score,
                'points_earned': submission.points_earned,
                'status': submission.status,
                'submitted_at': submission.submitted_at,
                'graded_at': submission.graded_at,
                'feedback': submission.feedback
            })
        
        return Response({
            'assignment_results': results
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_trainer_feedback(request):
    """
    GET /trainee/feedback/received
    Get all private trainer feedback on assignments/tests
    """
    try:
        user = get_session_user(request)
        if not user:
            return Response(
                {'error': 'User not authenticated'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        user_uuid = str(user.id)
        
        # Get feedback from test attempts
        test_feedback = TestAttempt.objects.filter(
            user_id=user_uuid,
            status='graded'
        ).select_related('test', 'graded_by').order_by('-graded_at')
        
        # Get feedback from assignments
        assignment_feedback = AssignmentSubmission.objects.filter(
            user_id=user_uuid,
            status='graded'
        ).select_related('assignment', 'graded_by').order_by('-graded_at')
        
        feedback_list = []
        
        # Add test feedback
        for attempt in test_feedback:
            feedback_list.append({
                'type': 'test',
                'title': attempt.test.title,
                'feedback': f'Score: {attempt.score}/{attempt.test.points_possible}',
                'graded_by': attempt.graded_by.first_name if attempt.graded_by else 'System',
                'graded_at': attempt.graded_at
            })
        
        # Add assignment feedback
        for submission in assignment_feedback:
            feedback_list.append({
                'type': 'assignment',
                'title': submission.assignment.title,
                'feedback': submission.feedback,
                'graded_by': submission.graded_by.first_name if submission.graded_by else 'System',
                'graded_at': submission.graded_at
            })
        
        return Response({
            'feedback': feedback_list
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_earned_badges(request):
    """
    GET /trainee/badges
    List earned badges (positive & negative)
    """
    try:
        user = get_session_user(request)
        if not user:
            return Response(
                {'error': 'User not authenticated'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        user_uuid = str(user.id)
        badges = BadgeAssignment.objects.filter(
            user_id=user_uuid
        ).select_related('badge').order_by('-earned_at')
        
        badge_list = []
        for assignment in badges:
            badge_list.append({
                'badge_id': str(assignment.badge.badge_id),
                'badge_name': assignment.badge.badge_name,
                'badge_type': assignment.badge.badge_type,
                'description': assignment.badge.description,
                'icon_url': assignment.badge.badge_icon_url,
                'reason': assignment.reason,
                'earned_at': assignment.earned_at
            })
        
        return Response({
            'badges': badge_list,
            'total_badges': len(badge_list)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_points_breakdown(request):
    """
    GET /trainee/points
    Get total points breakdown
    """
    try:
        user = User.objects.get(email=request.user.email)
        
        # Get total points from all test attempts
        test_points = TestAttempt.objects.filter(
            user=user,
            passed=True
        ).values_list('points_earned', flat=True)
        test_total = sum(test_points) if test_points else 0
        
        # Get total points from all assignment submissions
        assignment_points = AssignmentSubmission.objects.filter(
            user=user,
            status='graded'
        ).values_list('points_earned', flat=True)
        assignment_total = sum(assignment_points) if assignment_points else 0
        
        total_points = test_total + assignment_total
        
        return Response({
            'total_points': total_points,
            'test_points': test_total,
            'assignment_points': assignment_total,
            'breakdown': {
                'from_tests': test_total,
                'from_assignments': assignment_total
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_user_leaderboard(request):
    """
    GET /trainee/leaderboard
    Get leaderboard standings with all trainees
    Shows all trainees even if they haven't started any course (0 points)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Get current user if authenticated
        current_user = get_session_user(request)
        if current_user:
            logger.info(f"Leaderboard request from user: {current_user.first_name} {current_user.last_name}")
        else:
            logger.info("Leaderboard request from user without valid session - providing public leaderboard")
        
        # Use raw SQL to avoid UUID vs integer type mismatch
        from django.db import connection
        cursor = connection.cursor()
        
        logger.info("Fetching leaderboard entries...")
        cursor.execute("""
            SELECT l.rank, l.points, l.user_id,
                   u.email, u.first_name, u.last_name
            FROM leaderboard l
            INNER JOIN users u ON CAST(l.user_id AS TEXT) = CAST(u.user_id AS TEXT)
            WHERE l.scope = 'global'
            ORDER BY l.points DESC, l.rank ASC
        """)
        
        leaderboard_entries = []
        leaderboard_user_ids = set()
        for row in cursor.fetchall():
            rank, points, user_id, email, first_name, last_name = row
            leaderboard_entries.append({
                'rank': rank,
                'points': points or 0,
                'user_id': str(user_id),
                'email': email,
                'first_name': first_name,
                'last_name': last_name
            })
            leaderboard_user_ids.add(str(user_id))
        
        logger.info(f"Found {len(leaderboard_entries)} leaderboard entries")
        
        # Get all trainee users from database
        logger.info("Fetching all trainees...")
        all_trainees = list(
            User.objects.filter(
                role='trainee'
            ).order_by('-date_joined')
        )
        logger.info(f"Found {len(all_trainees)} total trainees")
        
        leaderboard_data = []
        user_rank = None
        current_rank = 1
        
        # Current user ID for comparison (if authenticated)
        current_user_id = str(current_user.id) if current_user else None
        
        # Add users from leaderboard first (those with points)
        logger.info("Processing leaderboard entries...")
        for entry in leaderboard_entries:
            trainee_name = f"{entry['first_name']} {entry['last_name']}".strip()
            rank_entry = {
                'rank': current_rank,
                'user_id': entry['user_id'],
                'name': trainee_name if trainee_name else entry['email'],
                'points': entry['points'],
                'badges': 0,
                'completion_rate': 0,
                'courses_completed': 0,
                'is_current_user': entry['user_id'] == current_user_id
            }
            leaderboard_data.append(rank_entry)
            logger.info(f"Rank {current_rank}: {trainee_name} - {entry['points']} points")
            
            if current_user_id and entry['user_id'] == current_user_id:
                user_rank = current_rank
            
            current_rank += 1
        
        # Add remaining trainees not in leaderboard (with 0 points)
        logger.info(f"Processing remaining trainees (not in leaderboard)...")
        for trainee in all_trainees:
            if trainee.user_id not in leaderboard_user_ids:
                trainee_name = f"{trainee.first_name} {trainee.last_name}".strip()
                rank_entry = {
                    'rank': current_rank,
                    'user_id': str(trainee.user_id),
                    'name': trainee_name if trainee_name else trainee.email,
                    'points': 0,
                    'badges': 0,
                    'completion_rate': 0,
                    'courses_completed': 0,
                    'is_current_user': trainee.user_id == current_user_id
                }
                leaderboard_data.append(rank_entry)
                logger.info(f"Rank {current_rank}: {trainee_name} - 0 points (new)")
                
                if current_user_id and trainee.user_id == current_user_id:
                    user_rank = current_rank
                
                current_rank += 1
        
        # Get current user's points if available
        user_points = 0
        if current_user:
            try:
                if hasattr(current_user, 'profile_data') and current_user.profile_data:
                    user_points = current_user.profile_data.get('points', 0)
            except:
                pass
        
        logger.info(f"Returning {len(leaderboard_data)} leaderboard entries. User rank: {user_rank}")
        
        return Response({
            'leaderboard': leaderboard_data,
            'user_rank': user_rank,
            'user_points': user_points
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        import traceback
        error_msg = str(e)
        tb = traceback.format_exc()
        logger.error(f"Leaderboard Error: {error_msg}")
        logger.error(f"Traceback: {tb}")
        print(f"ERROR: {error_msg}")
        print(tb)
        
        return Response(
            {'error': f'Failed to load leaderboard: {error_msg}'},
            status=status.HTTP_400_BAD_REQUEST
        )




@api_view(['GET'])
@permission_classes([AllowAny])
def get_appraisal_summary(request):
    """
    GET /trainee/appraisal-summary
    Get summary showing how points/badges affect appraisal
    """
    try:
        user = get_session_user(request)
        if not user:
            return Response(
                {'error': 'User not authenticated'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        user_uuid = str(user.id)
        
        # Get badges count
        badge_count = BadgeAssignment.objects.filter(user_id=user_uuid).count()
        
        # Get total points
        test_points = TestAttempt.objects.filter(
            user_id=user_uuid, passed=True
        ).aggregate(total=Sum('points_earned'))['total'] or 0
        
        assignment_points = AssignmentSubmission.objects.filter(
            user_id=user_uuid, status='graded'
        ).aggregate(total=Sum('points_earned'))['total'] or 0
        
        total_points = test_points + assignment_points
        
        # Get rank
        rank_entry = Leaderboard.objects.filter(
            user_id=user_uuid, scope='global'
        ).first()
        user_rank = rank_entry.rank if rank_entry else 0
        
        # Calculate appraisal impact (this is a simplified example)
        appraisal_score = (total_points / 100) + (badge_count * 5) + (100 - user_rank)
        
        return Response({
            'appraisal_summary': {
                'total_points': total_points,
                'badge_count': badge_count,
                'user_rank': user_rank,
                'appraisal_score': appraisal_score,
                'performance_level': 'High' if appraisal_score > 150 else 'Medium' if appraisal_score > 100 else 'Low'
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_user_progress_stats(request):
    """
    GET /api/trainee/progress/stats
    Get comprehensive user progress statistics and activities
    Returns: total points, modules/courses/badges counts, and activity timeline
    """
    try:
        # Get authenticated user from request
        user_obj = get_session_user(request)
        if not user_obj:
            return Response(
                {'error': 'User not authenticated'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Use raw SQL to avoid model FK issues with UUID
        from django.db import connection
        user_uuid = str(user_obj.id)
        cursor = connection.cursor()
        
        # Get module completions with course info
        cursor.execute("""
            SELECT mc.completion_id, mc.completed_at, m.title as module_title, 
                   m.module_id, c.title as course_title, c.course_id
            FROM module_completions mc
            INNER JOIN modules m ON mc.module_id = m.module_id
            INNER JOIN courses c ON m.course_id = c.course_id
            WHERE mc.user_id = %s AND mc.is_completed = true
            ORDER BY mc.completed_at DESC
        """, [user_uuid])
        
        module_completions = []
        for row in cursor.fetchall():
            module_completions.append({
                'completion_id': str(row[0]),
                'completed_at': row[1],
                'module_title': row[2],
                'module_id': str(row[3]),
                'course_title': row[4],
                'course_id': str(row[5])
            })
        
        # Get badge assignments
        cursor.execute("""
            SELECT ba.badge_assignment_id, ba.earned_at, ba.reason,
                   b.badge_id, b.badge_name, b.badge_type, b.description, b.badge_icon_url
            FROM badge_assignments ba
            INNER JOIN badges b ON ba.badge_id = b.badge_id
            WHERE ba.user_id = %s
            ORDER BY ba.earned_at DESC
        """, [user_uuid])
        
        badge_assignments = []
        for row in cursor.fetchall():
            badge_assignments.append({
                'badge_assignment_id': str(row[0]),
                'earned_at': row[1],
                'reason': row[2],
                'badge_id': str(row[3]),
                'badge_name': row[4],
                'badge_type': row[5],
                'description': row[6],
                'icon_url': row[7]
            })
        
        # Get course progress
        cursor.execute("""
            SELECT up.progress_id, up.completion_percentage, up.total_points_earned,
                   up.started_at, up.completed_at, c.title as course_title, c.course_id
            FROM user_progress up
            INNER JOIN courses c ON up.course_id = c.course_id
            WHERE up.user_id = %s
            ORDER BY up.updated_at DESC
        """, [user_uuid])
        
        course_progress = []
        for row in cursor.fetchall():
            course_progress.append({
                'progress_id': str(row[0]),
                'completion_percentage': row[1] or 0,
                'total_points_earned': row[2] or 0,
                'started_at': row[3],
                'completed_at': row[4],
                'course_title': row[5],
                'course_id': str(row[6])
            })
        
        # Calculate total points from all sources
        # 1. Points from test attempts
        cursor.execute("""
            SELECT SUM(points_earned) FROM test_attempts 
            WHERE user_id = %s AND passed = true
        """, [user_uuid])
        test_points = cursor.fetchone()[0] or 0
        
        # 2. Points from modules (5 points each)
        module_points = len(module_completions) * 5
        
        # 3. Points from badges (10 points each)
        badge_points = len(badge_assignments) * 10
        
        # 4. Points from course progress
        course_points = sum([p['total_points_earned'] for p in course_progress])
        
        total_points = test_points + module_points + badge_points + course_points
        
        # Build activities list combining modules, courses, and badges
        activities = []
        
        # Add module completions as activities
        for completion in module_completions:
            activities.append({
                'id': completion['completion_id'],
                'type': 'module',
                'activity': f"Completed: {completion['module_title']}",
                'course': completion['course_title'],
                'pointsEarned': 5,  # Default points for module
                'date': completion['completed_at'].isoformat() if completion['completed_at'] else None,
            })
        
        # Add badge assignments as activities
        for badge in badge_assignments:
            activities.append({
                'id': badge['badge_assignment_id'],
                'type': 'badge',
                'activity': f"Earned Badge: {badge['badge_name']}",
                'course': None,
                'pointsEarned': 10,  # Default points for badge
                'date': badge['earned_at'].isoformat() if badge['earned_at'] else None,
            })
        
        # Add all courses as activities (both completed and in-progress)
        for progress in course_progress:
            # Determine if course is completed based on completed_at timestamp
            is_completed = progress['completed_at'] is not None
            
            if is_completed:
                activities.append({
                    'id': progress['progress_id'],
                    'type': 'course',
                    'activity': f"Completed Course: {progress['course_title']}",
                    'course': progress['course_title'],
                    'pointsEarned': progress['total_points_earned'],
                    'date': progress['completed_at'].isoformat() if progress['completed_at'] else None,
                    'status': 'completed',
                    'completion': progress['completion_percentage']
                })
            else:
                activities.append({
                    'id': progress['progress_id'],
                    'type': 'course',
                    'activity': f"In Progress: {progress['course_title']}",
                    'course': progress['course_title'],
                    'pointsEarned': 0,
                    'date': progress['started_at'].isoformat() if progress['started_at'] else None,
                    'status': 'in_progress',
                    'completion': progress['completion_percentage']
                })
        
        # Get test/quiz attempts for assessments count
        cursor.execute("""
            SELECT COUNT(*) FROM test_attempts 
            WHERE user_id = %s AND status IN ('completed', 'passed')
        """, [user_uuid])
        assessments_count = cursor.fetchone()[0] or 0
        
        # Sort activities: completed courses first, then by newest date
        def sort_key(activity):
            # Completed courses priority: 0 (highest), then in-progress courses: 1, then others: 2
            if activity['type'] == 'course' and activity.get('status') == 'completed':
                priority = 0
            elif activity['type'] == 'course':
                priority = 1
            else:
                priority = 2
            
            # For secondary sort, use date (newest first)
            try:
                date_obj = datetime.fromisoformat(activity['date'].replace('Z', '+00:00')) if activity['date'] else datetime.min
                date_sort = date_obj.timestamp()
            except:
                date_sort = 0
            
            return (priority, -date_sort)  # Negative date for descending order
        
        activities.sort(key=sort_key)
        
        # Calculate stats
        completed_courses = [p for p in course_progress if p['completed_at'] is not None]
        stats = {
            'totalPoints': total_points,
            'modulesCompleted': len(module_completions),
            'assessmentsCompleted': assessments_count,
            'badgesEarned': len(badge_assignments),
            'coursesCompleted': len(completed_courses),
        }
        
        return Response({
            'stats': stats,
            'activities': activities[:100],  # Return first 100 activities (prioritizing completed courses)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


# Add missing import
from django.db.models import Sum

