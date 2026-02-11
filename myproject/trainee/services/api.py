"""
API views for courses, tests, and assignments.
Based on the new LMS schema models.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils import timezone
from django.db.models import Q
import json
from trainee.models import (
    User, Course, Module, Test, TestAttempt, TestAnswer, TestQuestion,
    Assignment, AssignmentSubmission,
    ModuleCompletion, UserProgress, Note, Notification
)
from admin.models import CourseAssignment
from trainee.serializers.course import (
    CourseSerializer, CourseDetailSerializer, CourseAssignmentSerializer,
    TestSerializer, TestDetailSerializer, TestAttemptSerializer,
    AssignmentSerializer, AssignmentSubmissionSerializer, UserProgressSerializer
)


class CourseViewSet(viewsets.ModelViewSet):
    """ViewSet for courses"""
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CourseDetailSerializer
        return CourseSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    @action(detail=False, methods=['get'])
    def my_courses(self, request):
        """Get user's assigned courses"""
        assignments = CourseAssignment.objects.filter(
            Q(assigned_to_user=request.user) | 
            Q(assigned_to_team__members__user=request.user)
        ).distinct()
        courses = Course.objects.filter(
            assignments__in=assignments
        ).distinct()
        serializer = self.get_serializer(courses, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def modules(self, request, pk=None):
        """Get modules in a course"""
        course = self.get_object()
        modules = course.modules.all().order_by('sequence_order')
        from trainee.serializers.course import ModuleSerializer
        serializer = ModuleSerializer(modules, many=True, context={'request': request})
        return Response(serializer.data)


class ModuleViewSet(viewsets.ModelViewSet):
    """ViewSet for modules"""
    queryset = Module.objects.all()
    from trainee.serializers.course import ModuleSerializer
    serializer_class = ModuleSerializer
    permission_classes = [AllowAny]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    @action(detail=True, methods=['post'])
    def mark_complete(self, request, pk=None):
        """Mark module as complete"""
        module = self.get_object()
        completion, created = ModuleCompletion.objects.get_or_create(
            module=module,
            user=request.user
        )
        completion.is_completed = True
        completion.completion_percentage = 100
        completion.completed_at = timezone.now()
        completion.save()

        return Response({
            'status': 'completed',
            'completion_id': completion.completion_id
        })

    @action(detail=True, methods=['post'])
    def add_note(self, request, pk=None):
        """Add a note to a module"""
        module = self.get_object()
        content = request.data.get('content', '')
        if not content:
            return Response(
                {'error': 'Content is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        note = Note.objects.create(
            user=request.user,
            module=module,
            content=content
        )
        from trainee.serializers.course import NoteSerializer
        serializer = NoteSerializer(note)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CourseAssignmentViewSet(viewsets.ModelViewSet):
    """ViewSet for course assignments"""
    queryset = CourseAssignment.objects.all()
    serializer_class = CourseAssignmentSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        """Filter assignments for current user"""
        return CourseAssignment.objects.filter(
            Q(assigned_to_user=self.request.user) |
            Q(assigned_to_team__members__user=self.request.user)
        ).distinct()

    @action(detail=False, methods=['post'])
    def assign_course(self, request):
        """Assign a course to a user (admin/manager only)"""
        course_id = request.data.get('course_id')
        user_id = request.data.get('user_id')
        due_date = request.data.get('due_date')

        if not course_id or not user_id:
            return Response(
                {'error': 'course_id and user_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            course = Course.objects.get(course_id=course_id)
            user = User.objects.get(id=user_id)
        except (Course.DoesNotExist, User.DoesNotExist):
            return Response(
                {'error': 'Course or user not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if already assigned
        existing = CourseAssignment.objects.filter(
            course=course,
            assigned_to_user=user
        ).first()

        if existing:
            return Response(
                {'error': 'Course already assigned to this user'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create assignment
        assignment = CourseAssignment.objects.create(
            course=course,
            assigned_to_user=user,
            assigned_by=request.user,
            due_date=due_date
        )

        serializer = self.get_serializer(assignment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def all_courses(self, request):
        """Get all available courses for assignment"""
        courses = Course.objects.all()
        from trainee.serializers.course import CourseSerializer
        serializer = CourseSerializer(courses, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def all_users(self, request):
        """Get all users for assignment"""
        users = User.objects.filter(is_active=True)
        data = [
            {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'username': user.username,
            }
            for user in users
        ]
        return Response(data)


class TestViewSet(viewsets.ModelViewSet):
    """ViewSet for tests/quizzes"""
    queryset = Test.objects.all()
    serializer_class = TestSerializer
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return TestDetailSerializer
        return TestSerializer

    @action(detail=True, methods=['post'])
    def start_attempt(self, request, pk=None):
        """Start a test attempt"""
        test = self.get_object()

        # Check if user has exceeded max attempts
        attempts = TestAttempt.objects.filter(
            test=test,
            user=request.user
        ).exclude(status='abandoned')
        
        if attempts.count() >= test.max_attempts:
            return Response(
                {'error': f'Maximum attempts ({test.max_attempts}) reached'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create new attempt
        attempt_number = attempts.count() + 1
        attempt = TestAttempt.objects.create(
            test=test,
            user=request.user,
            attempt_number=attempt_number,
            status='in_progress'
        )

        serializer = TestAttemptSerializer(attempt)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def submit_attempt(self, request, pk=None):
        """Submit a test attempt"""
        test = self.get_object()
        attempt_id = request.data.get('attempt_id')
        answers = request.data.get('answers', {})  # {question_id: answer}

        try:
            attempt = TestAttempt.objects.get(
                test_id=pk,
                attempt_id=attempt_id,
                user=request.user
            )
        except TestAttempt.DoesNotExist:
            return Response(
                {'error': 'Attempt not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        correct_count = 0
        total_points = 0

        for question_id, answer in answers.items():
            try:
                question = TestQuestion.objects.get(question_id=question_id)
                is_correct = False
                points_earned = 0

                # Check answer based on question type
                if question.question_type == 'true_false':
                    is_correct = (str(answer).lower() == str(question.correct_answer).lower())
                elif question.question_type == 'mcq':
                    is_correct = (answer == question.correct_answer)

                if is_correct:
                    correct_count += 1
                    points_earned = question.points

                total_points += question.points

                # Record the answer
                TestAnswer.objects.create(
                    attempt=attempt,
                    question=question,
                    answer_text=str(answer),
                    is_correct=is_correct,
                    points_earned=points_earned
                )

            except TestQuestion.DoesNotExist:
                continue

        # Calculate score
        score = (correct_count / len(answers) * 100) if answers else 0
        score = round(score)

        # Update attempt
        attempt.status = 'completed'
        attempt.submitted_at = timezone.now()
        attempt.score = score
        attempt.points_earned = sum(
            a.points_earned for a in attempt.answers.all()
        )
        attempt.passed = score >= test.passing_score
        attempt.save()

        return Response({
            'attempt_id': attempt.attempt_id,
            'score': attempt.score,
            'points_earned': attempt.points_earned,
            'passed': attempt.passed,
            'status': attempt.status
        })


class TestAttemptViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for test attempts"""
    queryset = TestAttempt.objects.all()
    serializer_class = TestAttemptSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        """Filter attempts for current user"""
        return TestAttempt.objects.filter(user=self.request.user)


class AssignmentViewSet(viewsets.ModelViewSet):
    """ViewSet for assignments"""
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer
    permission_classes = [AllowAny]


class AssignmentSubmissionViewSet(viewsets.ModelViewSet):
    """ViewSet for assignment submissions"""
    queryset = AssignmentSubmission.objects.all()
    serializer_class = AssignmentSubmissionSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        """Filter submissions for current user"""
        return AssignmentSubmission.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'])
    def submit(self, request):
        """Submit an assignment"""
        assignment_id = request.data.get('assignment_id')
        submission_text = request.data.get('submission_text', '')
        submission_files = request.data.get('submission_files')

        try:
            assignment = Assignment.objects.get(assignment_id=assignment_id)
        except Assignment.DoesNotExist:
            return Response(
                {'error': 'Assignment not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check max attempts
        submissions = AssignmentSubmission.objects.filter(
            assignment=assignment,
            user=request.user
        )
        if submissions.count() >= assignment.max_attempts:
            return Response(
                {'error': f'Maximum attempts ({assignment.max_attempts}) reached'},
                status=status.HTTP_400_BAD_REQUEST
            )

        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            user=request.user,
            attempt_number=submissions.count() + 1,
            submission_text=submission_text,
            submission_files=submission_files,
            status='submitted'
        )

        serializer = self.get_serializer(submission)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class UserProgressViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for user progress"""
    queryset = UserProgress.objects.all()
    serializer_class = UserProgressSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        """Filter progress for current user"""
        return UserProgress.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def my_progress(self, request):
        """Get user's progress across all courses"""
        progress = UserProgress.objects.filter(user=request.user)
        serializer = self.get_serializer(progress, many=True)
        return Response(serializer.data)


@api_view(['POST'])
@permission_classes([AllowAny])
def submit_assignment_by_id(request, assignment_id):
    """Wrapper: POST /trainee/assignment/{id}/submit - Submit an assignment by assignment_id"""
    try:
        user = request.user
        try:
            assignment = Assignment.objects.get(assignment_id=assignment_id)
        except Assignment.DoesNotExist:
            return Response({'error': 'Assignment not found'}, status=status.HTTP_404_NOT_FOUND)

        submission_text = request.data.get('submission_text', '')
        submission_files = request.data.get('submission_files')

        submissions = AssignmentSubmission.objects.filter(assignment=assignment, user=user)
        if submissions.count() >= assignment.max_attempts:
            return Response({'error': f'Maximum attempts ({assignment.max_attempts}) reached'}, status=status.HTTP_400_BAD_REQUEST)

        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            user=user,
            attempt_number=submissions.count() + 1,
            submission_text=submission_text,
            submission_files=submission_files,
            status='submitted'
        )

        serializer = AssignmentSubmissionSerializer(submission)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def submit_quiz_attempt_by_attempt(request, attempt_id):
    """Wrapper: POST /trainee/quiz/attempt/{attempt_id}/submit - submit answers by attempt id"""
    try:
        user = request.user
        try:
            attempt = TestAttempt.objects.get(attempt_id=attempt_id, user=user)
        except TestAttempt.DoesNotExist:
            return Response({'error': 'Attempt not found'}, status=status.HTTP_404_NOT_FOUND)

        answers = request.data.get('answers', {})

        correct_count = 0
        total_points = 0

        for question_id, answer in answers.items():
            try:
                question = TestQuestion.objects.get(question_id=question_id)
                is_correct = False
                points_earned = 0

                # Handle both simple string answers and object answers with confidence
                if isinstance(answer, dict):
                    user_answer = answer.get('answer')
                    confidence_score = answer.get('confidence', 0)
                else:
                    user_answer = answer
                    confidence_score = 0

                # Normalize answers for comparison
                correct_answer = question.correct_answer
                
                # Extract correct answer from list if it's stored as list
                if isinstance(correct_answer, list):
                    correct_answer = correct_answer[0] if correct_answer else None
                
                # Normalize the correct answer - handle stored values
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
                
                if question.question_type == 'true_false':
                    # For boolean questions, do case-insensitive comparison
                    is_correct = (user_str.lower() == correct_str.lower())
                elif question.question_type == 'mcq':
                    # For MCQ, do exact comparison
                    is_correct = (user_str == correct_str)
                else:
                    # For other types, do case-insensitive comparison
                    is_correct = (user_str.lower() == correct_str.lower())

                if is_correct:
                    correct_count += 1
                    points_earned = question.points

                total_points += question.points

                TestAnswer.objects.create(
                    attempt=attempt,
                    question=question,
                    user=user,
                    answer_text=str(user_answer),
                    is_correct=is_correct,
                    points_earned=points_earned,
                    confidence_score=confidence_score
                )
            except TestQuestion.DoesNotExist:
                continue

        # Calculate score based on points earned out of total possible points
        score = (correct_count / len(answers) * 100) if answers else 0
        score = round(score)

        attempt.status = 'completed'
        attempt.submitted_at = timezone.now()
        attempt.score = score
        attempt.points_earned = total_points if total_points > 0 else 0
        attempt.passed = score >= attempt.test.passing_score
        attempt.save()

        return Response({
            'attempt_id': attempt.attempt_id,
            'score': attempt.score,
            'points_earned': attempt.points_earned,
            'passed': attempt.passed,
            'status': attempt.status
        })

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_test_attempt_result(request, attempt_id):
    """GET /trainee/test/attempt/{attempt_id}/result - return attempt details/result"""
    try:
        user = request.user
        try:
            attempt = TestAttempt.objects.get(attempt_id=attempt_id, user=user)
        except TestAttempt.DoesNotExist:
            return Response({'error': 'Attempt not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = TestAttemptSerializer(attempt)
        return Response({'attempt': serializer.data}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
