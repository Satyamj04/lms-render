"""
Leaderboard Calculation Service
Implements weighted scoring for individual and team leaderboards
"""
from django.db import connection
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class LeaderboardService:
    """Service for calculating and updating leaderboards"""
    
    # Weighted scoring coefficients
    WEIGHT_MODULES = Decimal('40.0')      # 40% weight on modules completed
    WEIGHT_TIME = Decimal('30.0')         # 30% weight on time efficiency
    WEIGHT_ACCURACY = Decimal('30.0')     # 30% weight on quiz accuracy
    
    @staticmethod
    def calculate_individual_leaderboard(course_id=None):
        """
        Calculate individual leaderboard with weighted scoring
        Formula: weighted_score = (modules_completed * W1) + (1/time_spent * W2) + (correct_answers/total * W3)
        """
        try:
            with connection.cursor() as cursor:
                # Build query with optional course filter
                where_clause = "WHERE up.course_id = %s" if course_id else ""
                params = [str(course_id)] if course_id else []
                
                query = f"""
                WITH user_stats AS (
                    SELECT 
                        up.user_id,
                        up.course_id,
                        COALESCE(up.total_points_earned, 0) as total_points,
                        COALESCE(up.modules_completed, 0) as modules_completed,
                        GREATEST(COALESCE(up.time_spent_minutes, 1), 1) as time_spent_minutes,
                        COALESCE(SUM(qr.correct_answers), 0) as correct_answers,
                        COALESCE(SUM(qr.total_questions), 0) as total_answers
                    FROM user_progress up
                    LEFT JOIN quiz_results qr ON up.user_id = qr.user_id AND up.course_id = qr.course_id
                    {where_clause}
                    GROUP BY up.user_id, up.course_id, up.total_points_earned, up.modules_completed, up.time_spent_minutes
                ),
                scored_users AS (
                    SELECT 
                        user_id,
                        course_id,
                        total_points,
                        modules_completed,
                        time_spent_minutes,
                        correct_answers,
                        total_answers,
                        -- Weighted score calculation
                        (modules_completed * %s) +
                        ((1.0 / time_spent_minutes) * %s * 1000) +  -- Multiply by 1000 to scale time component
                        (CASE WHEN total_answers > 0 
                         THEN (CAST(correct_answers AS DECIMAL) / total_answers) * %s 
                         ELSE 0 END) as weighted_score
                    FROM user_stats
                )
                SELECT 
                    user_id,
                    course_id,
                    total_points,
                    modules_completed,
                    time_spent_minutes,
                    correct_answers,
                    total_answers,
                    weighted_score,
                    ROW_NUMBER() OVER (PARTITION BY course_id ORDER BY weighted_score DESC) as rank
                FROM scored_users
                ORDER BY weighted_score DESC;
                """
                
                cursor.execute(query, params + [
                    LeaderboardService.WEIGHT_MODULES,
                    LeaderboardService.WEIGHT_TIME,
                    LeaderboardService.WEIGHT_ACCURACY
                ])
                
                results = cursor.fetchall()
                
                # Insert or update user_leaderboard table
                for row in results:
                    user_id, course_id, total_points, modules_completed, time_spent, correct, total, score, rank = row
                    
                    LeaderboardService._upsert_user_leaderboard(
                        user_id=user_id,
                        course_id=course_id,
                        total_points=total_points,
                        modules_completed=modules_completed,
                        time_spent_minutes=time_spent,
                        correct_answers=correct,
                        total_answers=total,
                        weighted_score=score,
                        rank=rank
                    )
                
                logger.info(f"Individual leaderboard calculated: {len(results)} entries")
                return results
                
        except Exception as e:
            logger.error(f"Error calculating individual leaderboard: {str(e)}")
            raise
    
    @staticmethod
    def _upsert_user_leaderboard(user_id, course_id, total_points, modules_completed, 
                                  time_spent_minutes, correct_answers, total_answers, 
                                  weighted_score, rank):
        """Insert or update user leaderboard entry"""
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO user_leaderboard 
                (leaderboard_id, user_id, course_id, total_points, modules_completed, 
                 time_spent_minutes, correct_answers, total_answers, weighted_score, rank, 
                 created_at, last_updated)
                VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                ON CONFLICT (user_id, course_id) 
                DO UPDATE SET 
                    total_points = EXCLUDED.total_points,
                    modules_completed = EXCLUDED.modules_completed,
                    time_spent_minutes = EXCLUDED.time_spent_minutes,
                    correct_answers = EXCLUDED.correct_answers,
                    total_answers = EXCLUDED.total_answers,
                    weighted_score = EXCLUDED.weighted_score,
                    rank = EXCLUDED.rank,
                    last_updated = NOW();
            """, [str(user_id), str(course_id), total_points, modules_completed, 
                  time_spent_minutes, correct_answers, total_answers, 
                  float(weighted_score), rank])
    
    @staticmethod
    def calculate_team_leaderboard(course_id=None):
        """
        Calculate team leaderboard based on average completion rate
        """
        try:
            with connection.cursor() as cursor:
                where_clause = "WHERE up.course_id = %s" if course_id else ""
                params = [str(course_id)] if course_id else []
                
                query = f"""
                WITH team_stats AS (
                    SELECT 
                        tm.team_id,
                        up.course_id,
                        COUNT(DISTINCT tm.user_id) as total_members,
                        AVG(up.completion_percentage) as average_completion_rate,
                        SUM(COALESCE(up.total_points_earned, 0)) as total_points,
                        SUM(COALESCE(up.modules_completed, 0)) as total_modules_completed,
                        AVG(COALESCE(up.time_spent_minutes, 0)) as avg_time_spent
                    FROM team_members tm
                    INNER JOIN user_progress up ON tm.user_id = up.user_id
                    {where_clause}
                    GROUP BY tm.team_id, up.course_id
                ),
                scored_teams AS (
                    SELECT 
                        team_id,
                        course_id,
                        total_members,
                        average_completion_rate,
                        total_points,
                        -- Team weighted score: completion rate + normalized points
                        (average_completion_rate * 0.7) + 
                        (CASE WHEN total_members > 0 
                         THEN (CAST(total_points AS DECIMAL) / total_members) * 0.3 
                         ELSE 0 END) as weighted_score
                    FROM team_stats
                )
                SELECT 
                    team_id,
                    course_id,
                    total_members,
                    average_completion_rate,
                    total_points,
                    weighted_score,
                    ROW_NUMBER() OVER (PARTITION BY course_id ORDER BY weighted_score DESC) as rank
                FROM scored_teams
                ORDER BY weighted_score DESC;
                """
                
                cursor.execute(query, params)
                results = cursor.fetchall()
                
                # Insert or update team_leaderboard table
                for row in results:
                    team_id, course_id, total_members, avg_completion, total_points, score, rank = row
                    
                    LeaderboardService._upsert_team_leaderboard(
                        team_id=team_id,
                        course_id=course_id,
                        total_members=total_members,
                        average_completion_rate=avg_completion,
                        total_points=total_points,
                        weighted_score=score,
                        rank=rank
                    )
                
                logger.info(f"Team leaderboard calculated: {len(results)} teams")
                return results
                
        except Exception as e:
            logger.error(f"Error calculating team leaderboard: {str(e)}")
            raise
    
    @staticmethod
    def _upsert_team_leaderboard(team_id, course_id, total_members, average_completion_rate,
                                  total_points, weighted_score, rank):
        """Insert or update team leaderboard entry"""
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO team_leaderboard 
                (team_leaderboard_id, team_id, course_id, total_members, 
                 average_completion_rate, total_points, weighted_score, rank, 
                 created_at, last_updated)
                VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                ON CONFLICT (team_id, course_id) 
                DO UPDATE SET 
                    total_members = EXCLUDED.total_members,
                    average_completion_rate = EXCLUDED.average_completion_rate,
                    total_points = EXCLUDED.total_points,
                    weighted_score = EXCLUDED.weighted_score,
                    rank = EXCLUDED.rank,
                    last_updated = NOW();
            """, [str(team_id), str(course_id), total_members, 
                  float(average_completion_rate), total_points, 
                  float(weighted_score), rank])
    
    @staticmethod
    def get_individual_leaderboard(course_id=None, limit=None):
        """Fetch individual leaderboard from database"""
        with connection.cursor() as cursor:
            where_clause = "WHERE course_id = %s" if course_id else ""
            limit_clause = f"LIMIT {limit}" if limit else ""
            params = [str(course_id)] if course_id else []
            
            query = f"""
                SELECT 
                    leaderboard_id, user_id, course_id, total_points, 
                    modules_completed, time_spent_minutes, correct_answers, 
                    total_answers, weighted_score, rank
                FROM user_leaderboard
                {where_clause}
                ORDER BY rank ASC
                {limit_clause};
            """
            
            cursor.execute(query, params)
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    @staticmethod
    def get_team_leaderboard(course_id=None, limit=None):
        """Fetch team leaderboard from database"""
        with connection.cursor() as cursor:
            where_clause = "WHERE course_id = %s" if course_id else ""
            limit_clause = f"LIMIT {limit}" if limit else ""
            params = [str(course_id)] if course_id else []
            
            query = f"""
                SELECT 
                    team_leaderboard_id, team_id, course_id, total_members, 
                    average_completion_rate, total_points, weighted_score, rank
                FROM team_leaderboard
                {where_clause}
                ORDER BY rank ASC
                {limit_clause};
            """
            
            cursor.execute(query, params)
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
