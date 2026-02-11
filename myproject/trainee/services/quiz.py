"""
Quiz Endpoints - Uses Quiz/Question/QuizAttempt/TestResponse tables
Handles quiz attempts, submissions, and scoring for Quiz instances
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
import json
import logging

from trainee.models import (
    Quiz, Question, QuizAttempt, TestResponse, Enrollment, Module
)
from admin.models import UserProfile

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
def start_quiz_attempt(request, quiz_id):
    """
    POST /trainee/quiz/{quiz_id}/start
    Start a new quiz attempt using Quiz/Question tables
    Returns: attempt_id and quiz details with questions from 'questions' table
    """
    try:
        logger.info(f"[START_QUIZ] Starting quiz attempt for quiz_id: {quiz_id}")

        # Get user from session (use same pattern as other endpoints)
        from trainee.services.api_views import get_session_user
        user = get_session_user(request)
        if not user:
            logger.error(f"[START_QUIZ] User not found. request.user: {request.user}")
            return Response({'error': 'User not found in database'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get quiz from 'quizzes' table
        try:
            quiz = Quiz.objects.get(id=quiz_id)
            logger.info(f"[START_QUIZ] Found quiz: {quiz.id}")
        except Quiz.DoesNotExist:
            logger.error(f"[START_QUIZ] Quiz not found: {quiz_id}")
            return Response(
                {'error': f'Quiz not found: {quiz_id}'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get module and course
        module = quiz.unit
        course = module.course
        
        # Simplified access check - allow all users for now
        # In production, implement proper team-based access control
        logger.info(f"[START_QUIZ] User {user.email} attempting quiz for course {course.title}")
        
        # Check max attempts - CRITICAL: Filter by both quiz AND user
        attempt_count = QuizAttempt.objects.filter(
            quiz=quiz,
            user=user
        ).count()
        
        logger.info(f"[START_QUIZ] Quiz attempts: {attempt_count}/{quiz.attempts_allowed}")
        
        if attempt_count >= quiz.attempts_allowed:
            logger.error(f"[START_QUIZ] Max attempts reached")
            return Response(
                {'error': f'Maximum attempts ({quiz.attempts_allowed}) reached'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create attempt from 'quiz_attempts' table
        attempt = QuizAttempt.objects.create(
            quiz=quiz,
            user=user
        )
        
        # Get questions from 'questions' table
        questions = Question.objects.filter(quiz=quiz).order_by('order')
        questions_data = []
        for q in questions:
            questions_data.append({
                'question_id': str(q.id),
                'text': q.text,
                'type': q.type,
                'options': q.options if isinstance(q.options, list) else (json.loads(q.options) if q.options else None),
                'points': q.points,
                'order': q.order
            })
        
        logger.info(f"[START_QUIZ] Created attempt: {attempt.id} with {len(questions_data)} questions")
        
        return Response({
            'attempt_id': str(attempt.id),
            'quiz_id': str(quiz.id),
            'quiz_title': str(module.title),
            'module_id': str(module.module_id),
            'module_title': module.title,
            'time_limit_minutes': quiz.time_limit,
            'passing_score': quiz.passing_score,
            'total_questions': len(questions_data),
            'questions': questions_data,
            'attempt_number': attempt_count + 1,
            'max_attempts': quiz.attempts_allowed,
            'randomize_questions': quiz.randomize_questions,
            'show_correct_answers': quiz.show_answers
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"[START_QUIZ] Error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return Response(
            {'error': str(e), 'type': type(e).__name__},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def check_quiz_status(request, quiz_id):
    """
    GET /trainee/quiz/{quiz_id}/status
    Check if quiz attempts are exhausted for the CURRENT AUTHENTICATED user
    """
    try:
        logger.info(f"[CHECK_QUIZ_STATUS] Checking quiz status for quiz_id: {quiz_id}")
        
        # Get user from session (use same pattern as other endpoints)
        from trainee.services.api_views import get_session_user
        user = get_session_user(request)
        if not user:
            logger.error(f"[CHECK_QUIZ_STATUS] Could not find User in database. request.user: {request.user}")
            return Response({'error': 'User not found in database'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get quiz
        try:
            quiz = Quiz.objects.get(id=quiz_id)
        except Quiz.DoesNotExist:
            logger.error(f"[CHECK_QUIZ_STATUS] Quiz not found: {quiz_id}")
            return Response({'error': 'Quiz not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get module and course
        module = quiz.unit
        course = module.course
        
        # Simplified access check - allow all users for now
        logger.info(f"[CHECK_QUIZ_STATUS] User {user.email} checking status for course {course.title}")
        
        # Check attempts - CRITICAL: Filter by both quiz AND user
        attempt_count = QuizAttempt.objects.filter(
            quiz=quiz,
            user=user
        ).count()
        
        attempts_exhausted = attempt_count >= quiz.attempts_allowed
        
        logger.info(f"[CHECK_QUIZ_STATUS] User {user.email}: Quiz attempts: {attempt_count}/{quiz.attempts_allowed}, Exhausted: {attempts_exhausted}")
        
        return Response({
            'quiz_id': str(quiz.id),
            'user_email': user.email,
            'attempts_exhausted': attempts_exhausted,
            'current_attempts': attempt_count,
            'max_attempts': quiz.attempts_allowed,
            'attempts_remaining': max(0, quiz.attempts_allowed - attempt_count)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"[CHECK_QUIZ_STATUS] Error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def submit_quiz_attempt(request, attempt_id):
    """
    POST /trainee/quiz/attempt/{attempt_id}/submit
    Submit answers for a quiz attempt - Stores in 'test_responses' table
    Body: {
        "answers": {
            "question_id": {"answer": "selected_answer_text", "confidence": 0-100}
        }
    }
    """
    try:
        logger.info(f"[SUBMIT_QUIZ] Received submission for attempt_id: {attempt_id}")
        logger.info(f"[SUBMIT_QUIZ] Request data: {request.data}")
        
        # Get user from session (use same pattern as other endpoints)
        from trainee.services.api_views import get_session_user
        user = get_session_user(request)
        if not user:
            logger.error(f"[SUBMIT_QUIZ] User not found. request.user: {request.user}")
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get attempt from 'quiz_attempts' table
        try:
            attempt = QuizAttempt.objects.get(id=attempt_id)
            logger.info(f"[SUBMIT_QUIZ] Found attempt: {attempt.id}")
        except QuizAttempt.DoesNotExist:
            logger.error(f"[SUBMIT_QUIZ] Attempt not found: {attempt_id}")
            return Response(
                {'error': f'Quiz attempt not found: {attempt_id}'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verify user owns this attempt
        if attempt.user.id != user.id:
            logger.error(f"[SUBMIT_QUIZ] Access denied. Attempt user: {attempt.user.id}, Current user: {user.id}")
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get answers from request
        answers = request.data.get('answers', {})
        logger.info(f"[SUBMIT_QUIZ] Processing {len(answers)} answers")
        
        quiz = attempt.quiz
        correct_count = 0
        total_points_earned = 0
        total_points_possible = 0
        detailed_answers = []
        
        for question_id, answer_data in answers.items():
            try:
                # Fetch question from 'questions' table
                question = Question.objects.get(id=question_id)
                logger.info(f"[SUBMIT_QUIZ] Processing question: {question_id}")
                
                # Handle both simple string answers and object answers with confidence
                if isinstance(answer_data, dict):
                    user_answer = answer_data.get('answer')
                    confidence_score = answer_data.get('confidence', 0)
                else:
                    user_answer = answer_data
                    confidence_score = 0
                
                # Compare answer - handle correct_answer as index or text
                correct_answer = question.correct_answer
                options = question.options if isinstance(question.options, list) else []
                
                logger.info(f"[SUBMIT_QUIZ] Original - User: {repr(user_answer)}, Correct: {repr(correct_answer)}, Options: {options}")
                
                # If correct_answer is an integer, it's an index - convert to actual option text
                if isinstance(correct_answer, int) and options:
                    if 0 <= correct_answer < len(options):
                        correct_answer_text = options[correct_answer]
                        logger.info(f"[SUBMIT_QUIZ] Converted index {correct_answer} to text: '{correct_answer_text}'")
                        correct_answer = correct_answer_text
                
                # If correct_answer is a list, take the first element
                elif isinstance(correct_answer, list):
                    correct_answer = correct_answer[0] if correct_answer else None
                    logger.info(f"[SUBMIT_QUIZ] Extracted from list: {repr(correct_answer)}")
                
                # If correct_answer is a string, handle JSON parsing
                elif isinstance(correct_answer, str):
                    try:
                        # Try to parse as JSON first
                        parsed = json.loads(correct_answer)
                        if isinstance(parsed, int) and options:
                            # Parsed to an index
                            if 0 <= parsed < len(options):
                                correct_answer = options[parsed]
                                logger.info(f"[SUBMIT_QUIZ] Parsed JSON index {parsed} to text: '{correct_answer}'")
                        else:
                            correct_answer = parsed
                            logger.info(f"[SUBMIT_QUIZ] Parsed JSON correct_answer: {repr(parsed)}")
                    except (json.JSONDecodeError, TypeError):
                        # If it's not JSON, use the string as-is
                        correct_answer = correct_answer.strip()
                        logger.info(f"[SUBMIT_QUIZ] Not JSON, using as string: {repr(correct_answer)}")
                
                # Normalize both answers for comparison
                correct_str = str(correct_answer).strip() if correct_answer is not None else ""
                user_str = str(user_answer).strip() if user_answer is not None else ""
                
                logger.info(f"[SUBMIT_QUIZ] Final comparison - User: '{user_str}', Correct: '{correct_str}'")
                
                # Perform comparison (case-insensitive for better matching)
                is_correct = (user_str.lower() == correct_str.lower())
                logger.info(f"[SUBMIT_QUIZ] Result: {is_correct}")
                
                if is_correct:
                    correct_count += 1
                    points_earned = question.points
                else:
                    points_earned = 0
                
                total_points_earned += points_earned
                total_points_possible += question.points

                # Save response to 'test_responses' table using raw SQL
                # Note: Database has FK constraints expecting test_attempts/tests/test_questions
                # but we're inserting quiz data. We'll insert the data anyway and let it fail gracefully if needed.
                try:
                    from django.db import connection
                    import uuid
                    
                    response_id = uuid.uuid4()
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            INSERT INTO test_responses 
                            (response_id, attempt_id, test_id, question_id, user_id, 
                             answer_text, is_correct, score, confidence_score, confidence_scale,
                             answered_at, created_at, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, [
                            response_id,
                            attempt.id,
                            quiz.id,
                            question.id,
                            user.id,
                            str(user_answer),
                            is_correct,
                            points_earned,
                            confidence_score,
                            '0_to_100',
                            timezone.now(),
                            timezone.now(),
                            timezone.now()
                        ])
                    logger.info(f"[SUBMIT_QUIZ] Saved response {response_id} with confidence: {confidence_score}")
                except Exception as save_error:
                    # Log the error but continue - responses won't be saved to test_responses table
                    # due to FK constraints, but quiz attempt score will still be saved
                    logger.warning(f"[SUBMIT_QUIZ] Could not save to test_responses table (FK constraint): {str(save_error)}")
                    # Don't raise - continue processing
                
                detailed_answers.append({
                    'question_id': str(question_id),
                    'question_text': question.text,
                    'user_answer': user_answer,
                    'correct_answer': correct_answer,
                    'is_correct': is_correct,
                    'points_earned': points_earned,
                    'points_possible': question.points,
                    'confidence_score': confidence_score
                })
                
            except Question.DoesNotExist:
                logger.warning(f"[SUBMIT_QUIZ] Question not found: {question_id}")
                continue
            except Exception as e:
                logger.error(f"[SUBMIT_QUIZ] Error processing answer: {str(e)}")
                continue
        
        # Calculate final score based on points earned
        score = (total_points_earned / total_points_possible * 100) if total_points_possible > 0 else 0
        score = round(score, 2)
        passed = score >= quiz.passing_score
        
        # Update attempt in 'quiz_attempts' table with only available fields
        attempt.score = score
        attempt.passed = passed
        attempt.completed_at = timezone.now()
        attempt.answers = answers  # Store the raw answers JSON
        attempt.save()
        
        logger.info(f"[SUBMIT_QUIZ] Attempt saved. Score: {score}, Passed: {passed}")
        
        # Check if user can retry - recalculate attempt count
        current_attempt_count = QuizAttempt.objects.filter(
            quiz=quiz,
            user=user
        ).count()
        attempts_remaining = max(0, quiz.attempts_allowed - current_attempt_count)
        can_retry = not passed and attempts_remaining > 0
        
        return Response({
            'attempt_id': str(attempt.id),
            'quiz_id': str(quiz.id),
            'status': 'completed',
            'score': score,
            'passed': passed,
            'passing_score': quiz.passing_score,
            'correct_answers': correct_count,
            'total_questions_answered': len(answers),
            'points_earned': total_points_earned,
            'points_possible': total_points_possible,
            'answers': detailed_answers,
            'submitted_at': timezone.now().isoformat(),
            'attempt_number': current_attempt_count,
            'max_attempts': quiz.attempts_allowed,
            'attempts_remaining': attempts_remaining,
            'can_retry': can_retry
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"[SUBMIT_QUIZ] Error: {str(e)}", exc_info=True)
        return Response(
            {'error': str(e), 'type': type(e).__name__},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_module_quizzes(request, module_id):
    """
    GET /trainee/module/{module_id}/quizzes/
    Fetch all quizzes for a module from the 'quizzes' table
    """
    try:
        logger.info(f"[GET_QUIZZES] Fetching quizzes for module_id: {module_id}")
        
        # Get module
        try:
            module = Module.objects.get(module_id=module_id)
            logger.info(f"[GET_QUIZZES] Found module: {module.title}")
        except Module.DoesNotExist:
            logger.error(f"[GET_QUIZZES] Module not found: {module_id}")
            return Response(
                {'error': 'Module not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Fetch quizzes for this module from 'quizzes' table
        quizzes = Quiz.objects.filter(
            unit=module
        ).order_by('order').values(
            'id',
            'title',
            'unit__title',
            'is_mandatory',
            'passing_score',
            'attempts_allowed',
            'time_limit',
            'order'
        )
        
        quizzes_list = list(quizzes)
        logger.info(f"[GET_QUIZZES] Found {len(quizzes_list)} quizzes")
        
        return Response({
            'success': True,
            'module_id': str(module_id),
            'module_title': module.title,
            'quizzes': quizzes_list,
            'count': len(quizzes_list),
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"[GET_QUIZZES] Error: {str(e)}", exc_info=True)
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_quiz_attempt_result(request, attempt_id):
    """
    GET /trainee/quiz/attempt/{attempt_id}/result/
    Retrieve the result of a completed quiz attempt from 'quiz_attempts' and 'test_responses' tables
    """
    try:
        logger.info(f"[GET_RESULT] Fetching result for attempt_id: {attempt_id}")

        # Get the attempt from 'quiz_attempts' table
        try:
            attempt = QuizAttempt.objects.get(id=attempt_id)
            logger.info(f"[GET_RESULT] Found attempt: {attempt.id}")
        except QuizAttempt.DoesNotExist:
            logger.error(f"[GET_RESULT] Attempt not found: {attempt_id}")
            return Response({'error': 'Quiz attempt not found'}, status=status.HTTP_404_NOT_FOUND)

        # Get user from session and verify ownership
        from trainee.services.api_views import get_session_user
        user = get_session_user(request)
        if not user:
            logger.error(f"[GET_RESULT] User not found. request.user: {request.user}")
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        if attempt.user.id != user.id:
            logger.error(f"[GET_RESULT] Access denied for user {user.id} on attempt {attempt_id}")
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
        
        # Fetch all responses from 'test_responses' table for this attempt using attempt_id
        # Join with questions table to get question details
        from django.db.models import F
        responses = TestResponse.objects.filter(
            attempt_id=attempt.id
        ).annotate(
            question_text=F('question_id')  # We'll need to fetch question details separately
        ).values(
            'question_id',
            'answer_text',
            'is_correct',
            'score',
            'confidence_score'
        )
        
        responses_list = list(responses)
        
        # Enrich with question details
        question_ids = [r['question_id'] for r in responses_list]
        questions = {str(q.id): q for q in Question.objects.filter(id__in=question_ids)}
        
        for response in responses_list:
            qid = str(response['question_id'])
            if qid in questions:
                q = questions[qid]
                response['question_text'] = q.text
                response['correct_answer'] = q.correct_answer
            response['question_id'] = qid  # Convert UUID to string
        
        logger.info(f"[GET_RESULT] Found {len(responses_list)} responses")
        
        # Calculate total questions and correct answers from responses
        correct_answers = sum(1 for r in responses_list if r.get('is_correct', False))
        
        return Response({
            'success': True,
            'attempt_id': str(attempt.id),
            'quiz_id': str(attempt.quiz.id),
            'quiz_title': str(attempt.quiz.unit.title),
            'score': attempt.score,
            'passed': attempt.passed,
            'passing_score': attempt.quiz.passing_score,
            'correct_answers': correct_answers,
            'total_questions': len(responses_list),
            'completed_at': attempt.completed_at.isoformat() if attempt.completed_at else None,
            'max_attempts': attempt.quiz.attempts_allowed,
            'responses': responses_list,
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"[GET_RESULT] Error: {str(e)}", exc_info=True)
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
