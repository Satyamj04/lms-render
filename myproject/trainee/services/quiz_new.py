"""
Updated Quiz Service - Uses Quiz/Question and QuizAttempt/TestAnswer tables
Handles quiz attempts, submissions, and scoring with max attempts enforcement
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q
import json

from trainee.models import (
    User, Module, Quiz, Question, Course,
    QuizAttempt, TestAnswer, TestAttempt, TestQuestion, Enrollment
)


@api_view(['POST'])
@permission_classes([AllowAny])
def start_quiz_attempt(request, quiz_id):
    """
    POST /trainee/quiz/{quiz_id}/start/new
    Start a new quiz attempt using Quiz/Question tables
    Returns: attempt_id and quiz details with questions
    """
    try:
        # Get the actual User object from database
        user = None
        
        if hasattr(request.user, 'id') and request.user.id:
            try:
                user = User.objects.get(user_id=request.user.id)
            except User.DoesNotExist:
                pass
        
        if not user and hasattr(request.user, 'email') and request.user.email:
            try:
                user = User.objects.get(email=request.user.email)
            except User.DoesNotExist:
                pass
        
        if not user:
            return Response(
                {'error': 'User not found in database'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get quiz
        try:
            quiz = Quiz.objects.get(id=quiz_id)
        except Quiz.DoesNotExist:
            return Response(
                {'error': f'Quiz not found: {quiz_id}'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        module = quiz.unit
        course = module.course
        
        # Check if user has access to the course via Enrollment
        enrollment = Enrollment.objects.filter(
            user=user,
            course=course
        ).first()
        
        if not enrollment:
            return Response(
                {'error': 'Access denied to this course'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if user has reached max attempts
        attempt_count = QuizAttempt.objects.filter(
            quiz=quiz,
            user=user
        ).exclude(status='abandoned').count()
        
        if attempt_count >= quiz.attempts_allowed:
            return Response(
                {'error': 'Quiz Attempt is Over', 'details': f'Maximum {quiz.attempts_allowed} attempts reached'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Create new QuizAttempt
        attempt = QuizAttempt.objects.create(
            quiz=quiz,
            user=user,
            score=0,
            passed=False,
            started_at=timezone.now()
        )
        
        # Create corresponding TestAttempt (for compatibility with TestAnswer)
        test_attempt = TestAttempt.objects.create(
            test_id=quiz.id,  # Reuse quiz ID as test ID for consistency
            user=user,
            attempt_number=attempt_count + 1,
            status='in_progress'
        )
        
        # Get quiz questions
        questions = Question.objects.filter(quiz=quiz).order_by('order')
        questions_data = []
        
        for q in questions:
            questions_data.append({
                'question_id': str(q.id),
                'text': q.text,
                'type': q.type,
                'options': q.options if isinstance(q.options, list) else (json.loads(q.options) if q.options else []),
                'points': q.points,
                'order': q.order
            })
        
        return Response({
            'attempt_id': str(attempt.id),
            'quiz_id': str(quiz_id),
            'quiz_title': quiz.unit.title,
            'module_id': str(module.module_id),
            'module_title': module.title,
            'time_limit': quiz.time_limit,
            'passing_score': quiz.passing_score,
            'total_questions': len(questions_data),
            'questions': questions_data,
            'attempt_number': attempt_count + 1,
            'max_attempts': quiz.attempts_allowed,
            'randomize_questions': quiz.randomize_questions,
            'show_answers': quiz.show_answers
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        import traceback
        print(f"Error in start_quiz_attempt: {str(e)}\n{traceback.format_exc()}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def submit_quiz_attempt(request, attempt_id):
    """
    POST /trainee/quiz/attempt/{attempt_id}/submit/new
    Submit answers for a quiz attempt using QuizAttempt/TestAnswer
    Body: {
        "answers": {
            "question_id": {"answer": "value", "confidence": 0-100}
        }
    }
    """
    try:
        # Get user
        user = None
        
        if hasattr(request.user, 'id') and request.user.id:
            try:
                user = User.objects.get(user_id=request.user.id)
            except User.DoesNotExist:
                pass
        
        if not user and hasattr(request.user, 'email') and request.user.email:
            try:
                user = User.objects.get(email=request.user.email)
            except User.DoesNotExist:
                pass
        
        if not user:
            return Response(
                {'error': 'User not found in database'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get attempt
        attempt = get_object_or_404(QuizAttempt, id=attempt_id)
        
        # Verify user owns this attempt
        if attempt.user.user_id != user.user_id:
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Verify attempt is in progress
        if attempt.status != 'in_progress':
            return Response(
                {'error': 'Quiz attempt is not in progress'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Process answers
        answers = request.data.get('answers', {})
        quiz = attempt.quiz
        
        correct_count = 0
        total_points = 0
        detailed_answers = []
        
        for question_id, answer_data in answers.items():
            try:
                question = Question.objects.get(id=question_id)
                
                # Extract answer and confidence
                if isinstance(answer_data, dict):
                    user_answer = answer_data.get('answer', '')
                    confidence_score = answer_data.get('confidence', None)
                else:
                    user_answer = str(answer_data)
                    confidence_score = None
                
                # Validate confidence score (0-100)
                if confidence_score is not None:
                    try:
                        confidence_score = int(confidence_score)
                        if confidence_score < 0:
                            confidence_score = 0
                        elif confidence_score > 100:
                            confidence_score = 100
                    except (ValueError, TypeError):
                        confidence_score = 0
                else:
                    confidence_score = 0
                
                # Normalize answers for comparison
                correct_answer = question.correct_answer
                
                # Extract correct answer from list if it's stored as list
                if isinstance(correct_answer, list):
                    correct_answer = correct_answer[0] if correct_answer else None
                
                # Normalize the correct answer - handle JSON stored values
                if isinstance(correct_answer, str):
                    try:
                        parsed = json.loads(correct_answer)
                        correct_answer = parsed
                    except (json.JSONDecodeError, TypeError):
                        correct_answer = correct_answer.strip()
                
                # Normalize the user answer
                if isinstance(user_answer, str):
                    user_answer = user_answer.strip()
                
                # Perform comparison with proper type handling
                correct_str = str(correct_answer).strip() if correct_answer is not None else ""
                user_str = str(user_answer).strip() if user_answer is not None else ""
                
                # For boolean/true-false questions, do case-insensitive comparison
                if correct_str.lower() in ['true', 'false']:
                    is_correct = (user_str.lower() == correct_str.lower())
                else:
                    # For other question types, do exact string comparison
                    is_correct = (user_str == correct_str)
                
                if is_correct:
                    correct_count += 1
                    points_earned = question.points
                else:
                    points_earned = 0
                
                total_points += question.points
                
                # Save answer to TestAnswer
                answer_obj = TestAnswer.objects.create(
                    attempt_id=attempt.id,
                    question=question,
                    user=user,
                    answer_text=user_answer,
                    is_correct=is_correct,
                    points_earned=points_earned,
                    confidence_score=confidence_score
                )
                
                detailed_answers.append({
                    'question_id': str(question_id),
                    'question_text': question.text,
                    'user_answer': user_answer,
                    'correct_answer': question.correct_answer,
                    'is_correct': is_correct,
                    'points_earned': points_earned,
                    'points_possible': question.points,
                    'confidence_score': confidence_score
                })
                
            except Question.DoesNotExist:
                return Response(
                    {'error': f'Question not found: {question_id}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Calculate score
        score = int((correct_count / total_points * 100)) if total_points > 0 else 0
        passed = score >= quiz.passing_score
        
        # Update attempt
        attempt.score = score
        attempt.passed = passed
        attempt.status = 'completed'
        attempt.completed_at = timezone.now()
        attempt.save()
        
        # Update corresponding TestAttempt
        test_attempt = TestAttempt.objects.filter(user=user, test_id=quiz.id).first()
        if test_attempt:
            test_attempt.status = 'completed'
            test_attempt.score = score
            test_attempt.passed = passed
            test_attempt.submitted_at = timezone.now()
            test_attempt.save()
        
        return Response({
            'attempt_id': str(attempt.id),
            'score': score,
            'passed': passed,
            'correct_answers': correct_count,
            'total_questions': len(detailed_answers),
            'passing_score': quiz.passing_score,
            'answers': detailed_answers,
            'message': 'Quiz submitted successfully'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        import traceback
        print(f"Error in submit_quiz_attempt: {str(e)}\n{traceback.format_exc()}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_quiz_attempts(request, quiz_id):
    """
    GET /trainee/quiz/{quiz_id}/attempts/new
    Get all attempts for a quiz by current user
    """
    try:
        user = None
        
        if hasattr(request.user, 'id') and request.user.id:
            try:
                user = User.objects.get(user_id=request.user.id)
            except User.DoesNotExist:
                pass
        
        if not user and hasattr(request.user, 'email') and request.user.email:
            try:
                user = User.objects.get(email=request.user.email)
            except User.DoesNotExist:
                pass
        
        if not user:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        quiz = get_object_or_404(Quiz, id=quiz_id)
        
        attempts = QuizAttempt.objects.filter(
            quiz=quiz,
            user=user
        ).order_by('-started_at')
        
        attempts_data = []
        for attempt in attempts:
            attempts_data.append({
                'attempt_id': str(attempt.id),
                'attempt_number': attempt.id,
                'score': attempt.score,
                'passed': attempt.passed,
                'status': attempt.status,
                'started_at': attempt.started_at.isoformat(),
                'completed_at': attempt.completed_at.isoformat() if attempt.completed_at else None
            })
        
        return Response({
            'quiz_id': str(quiz_id),
            'attempts': attempts_data,
            'total_attempts': len(attempts_data),
            'max_allowed': quiz.attempts_allowed
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
