"""
Quiz Results Service
Handles quiz attempt validation and result storage
"""
from django.db import connection
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class QuizResultsService:
    """Service for processing and storing quiz results"""
    
    @staticmethod
    def process_quiz_attempt(attempt_id, user_id, quiz_id, module_id, course_id, 
                            time_taken_seconds=0):
        """
        Process a quiz attempt by reading from test_responses table, calculate score, and store results
        
        Args:
            attempt_id: UUID of the attempt (from quiz_attempts or test_attempts)
            user_id: UUID of the user
            quiz_id: UUID of the quiz
            module_id: UUID of the module
            course_id: UUID of the course
            time_taken_seconds: Time taken to complete quiz
            
        Returns:
            Dict with score, passed status, and detailed results
        """
        try:
            with connection.cursor() as cursor:
                # Get user's responses from test_responses table
                cursor.execute("""
                    SELECT tr.question_id, tr.selected_answer, tq.correct_answer, tq.points
                    FROM test_responses tr
                    JOIN test_questions tq ON tr.question_id = tq.question_id
                    WHERE tr.attempt_id = %s;
                """, [str(attempt_id)])
                
                responses = cursor.fetchall()
                
                if not responses:
                    logger.warning(f"No responses found for attempt {attempt_id}")
                    return None
                
                # Calculate results from existing responses
                total_questions = len(responses)
                correct_answers = 0
                incorrect_answers = 0
                max_points = 0
                points_earned = 0
                
                for question_id, user_answer, correct_answer, question_points in responses:
                    max_points += question_points or 0
                    
                    user_ans = (user_answer or '').strip().lower()
                    correct_ans = (correct_answer or '').strip().lower()
                    
                    if user_ans == correct_ans:
                        correct_answers += 1
                        points_earned += question_points or 0
                    else:
                        incorrect_answers += 1
                
                # Calculate percentage
                score_percentage = (correct_answers / total_questions * 100) if total_questions > 0 else 0
                
                # Get passing threshold from tests table (where quizzes are stored)
                cursor.execute("""
                    SELECT passing_marks FROM tests WHERE test_id = %s;
                """, [str(quiz_id)])
                
                passing_threshold = cursor.fetchone()
                passing_score = passing_threshold[0] if passing_threshold else 70.0
                
                passed = score_percentage >= passing_score
                
                # Get attempt number for this user/quiz
                cursor.execute("""
                    SELECT COUNT(*) FROM quiz_results 
                    WHERE user_id = %s AND quiz_id = %s;
                """, [str(user_id), str(quiz_id)])
                
                attempt_number = cursor.fetchone()[0] + 1
                
                # Insert quiz result
                cursor.execute("""
                    INSERT INTO quiz_results 
                    (result_id, attempt_id, user_id, quiz_id, module_id, course_id,
                     total_questions, correct_answers, incorrect_answers, score_percentage,
                     points_earned, max_points, time_taken_seconds, passed, attempt_number,
                     submitted_at, created_at)
                    VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    ON CONFLICT (attempt_id) 
                    DO UPDATE SET
                        total_questions = EXCLUDED.total_questions,
                        correct_answers = EXCLUDED.correct_answers,
                        incorrect_answers = EXCLUDED.incorrect_answers,
                        score_percentage = EXCLUDED.score_percentage,
                        points_earned = EXCLUDED.points_earned,
                        max_points = EXCLUDED.max_points,
                        time_taken_seconds = EXCLUDED.time_taken_seconds,
                        passed = EXCLUDED.passed,
                        submitted_at = NOW();
                """, [
                    str(attempt_id), str(user_id), str(quiz_id), str(module_id), str(course_id),
                    total_questions, correct_answers, incorrect_answers, score_percentage,
                    points_earned, max_points, time_taken_seconds, passed, attempt_number
                ])
                
                # Update user_progress table with quiz results
                if passed:
                    cursor.execute("""
                        UPDATE user_progress
                        SET tests_passed = tests_passed + 1,
                            tests_attempted = tests_attempted + 1,
                            total_points_earned = total_points_earned + %s,
                            last_activity = NOW(),
                            updated_at = NOW()
                        WHERE user_id = %s AND course_id = %s;
                    """, [points_earned, str(user_id), str(course_id)])
                else:
                    cursor.execute("""
                        UPDATE user_progress
                        SET tests_attempted = tests_attempted + 1,
                            last_activity = NOW(),
                            updated_at = NOW()
                        WHERE user_id = %s AND course_id = %s;
                    """, [str(user_id), str(course_id)])
                
                logger.info(f"Processed quiz attempt {attempt_id}: {score_percentage}% ({correct_answers}/{total_questions})")
                
                return {
                    'attempt_id': str(attempt_id),
                    'total_questions': total_questions,
                    'correct_answers': correct_answers,
                    'incorrect_answers': incorrect_answers,
                    'score_percentage': float(score_percentage),
                    'points_earned': points_earned,
                    'max_points': max_points,
                    'passed': passed,
                    'attempt_number': attempt_number,
                    'time_taken_seconds': time_taken_seconds
                }
                
        except Exception as e:
            logger.error(f"Error processing quiz attempt: {str(e)}")
            raise
    
    @staticmethod
    def get_quiz_results(user_id, quiz_id=None, course_id=None):
        """
        Get quiz results for a user
        Can filter by specific quiz or course
        """
        try:
            with connection.cursor() as cursor:
                where_clauses = ["user_id = %s"]
                params = [str(user_id)]
                
                if quiz_id:
                    where_clauses.append("quiz_id = %s")
                    params.append(str(quiz_id))
                
                if course_id:
                    where_clauses.append("course_id = %s")
                    params.append(str(course_id))
                
                where_sql = " AND ".join(where_clauses)
                
                cursor.execute(f"""
                    SELECT 
                        result_id, attempt_id, quiz_id, module_id, course_id,
                        total_questions, correct_answers, incorrect_answers, 
                        score_percentage, points_earned, max_points, 
                        time_taken_seconds, passed, attempt_number, submitted_at
                    FROM quiz_results
                    WHERE {where_sql}
                    ORDER BY submitted_at DESC;
                """, params)
                
                columns = ['result_id', 'attempt_id', 'quiz_id', 'module_id', 'course_id',
                          'total_questions', 'correct_answers', 'incorrect_answers',
                          'score_percentage', 'points_earned', 'max_points',
                          'time_taken_seconds', 'passed', 'attempt_number', 'submitted_at']
                
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]
                return results
                
        except Exception as e:
            logger.error(f"Error getting quiz results: {str(e)}")
            raise
    
    @staticmethod
    def get_best_attempt(user_id, quiz_id):
        """Get the best scoring attempt for a user on a specific quiz"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        result_id, attempt_id, score_percentage, points_earned, 
                        passed, attempt_number, submitted_at
                    FROM quiz_results
                    WHERE user_id = %s AND quiz_id = %s
                    ORDER BY score_percentage DESC, submitted_at DESC
                    LIMIT 1;
                """, [str(user_id), str(quiz_id)])
                
                result = cursor.fetchone()
                
                if result:
                    columns = ['result_id', 'attempt_id', 'score_percentage', 
                              'points_earned', 'passed', 'attempt_number', 'submitted_at']
                    return dict(zip(columns, result))
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting best attempt: {str(e)}")
            raise
    
    @staticmethod
    def get_quiz_statistics(quiz_id):
        """Get aggregate statistics for a quiz across all attempts"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        COUNT(DISTINCT user_id) as total_attempts,
                        AVG(score_percentage) as average_score,
                        MAX(score_percentage) as highest_score,
                        MIN(score_percentage) as lowest_score,
                        SUM(CASE WHEN passed THEN 1 ELSE 0 END) as total_passed,
                        AVG(time_taken_seconds) as average_time
                    FROM quiz_results
                    WHERE quiz_id = %s;
                """, [str(quiz_id)])
                
                result = cursor.fetchone()
                
                if result:
                    return {
                        'total_attempts': result[0] or 0,
                        'average_score': float(result[1]) if result[1] else 0.0,
                        'highest_score': float(result[2]) if result[2] else 0.0,
                        'lowest_score': float(result[3]) if result[3] else 0.0,
                        'total_passed': result[4] or 0,
                        'average_time': float(result[5]) if result[5] else 0.0
                    }
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting quiz statistics: {str(e)}")
            raise
    
    @staticmethod
    def validate_quiz_answers_server_side(quiz_id, attempt_id):
        """
        Server-side validation of quiz answers from test_responses table
        Returns detailed feedback per question
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        tr.question_id, 
                        tq.question_text, 
                        tr.selected_answer,
                        tq.correct_answer, 
                        tq.points
                    FROM test_responses tr
                    JOIN test_questions tq ON tr.question_id = tq.question_id
                    WHERE tr.attempt_id = %s;
                """, [str(attempt_id)])
                
                responses = cursor.fetchall()
                validation_results = []
                
                for question_id, question_text, user_answer, correct_answer, points in responses:
                    is_correct = (user_answer or '').strip().lower() == (correct_answer or '').strip().lower()
                    
                    validation_results.append({
                        'question_id': str(question_id),
                        'question_text': question_text,
                        'user_answer': user_answer,
                        'is_correct': is_correct,
                        'points_awarded': points if is_correct else 0,
                        'correct_answer': correct_answer if not is_correct else None  # Only show if wrong
                    })
                
                return validation_results
                
        except Exception as e:
            logger.error(f"Error validating quiz answers: {str(e)}")
            raise
