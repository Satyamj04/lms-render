"""
Serializers for courses, modules, tests, and assessments.
Based on the new LMS schema models.
"""
from rest_framework import serializers
from trainee.models import (
    Course, Module, Test, TestQuestion, TestAttempt, TestAnswer,
    Assignment, AssignmentSubmission,
    ModuleCompletion, UserProgress, Note, ModuleQuiz, ModuleQuizAnswer,
    ModuleQuizAttempt
)
from admin.models import CourseAssignment


class TestQuestionSerializer(serializers.ModelSerializer):
    """Serializer for test questions"""
    class Meta:
        model = TestQuestion
        fields = [
            'question_id', 'question_text', 'question_type', 'options',
            'correct_answer', 'points', 'difficulty', 'explanation', 'sequence_order'
        ]


class TestAttemptAnswerSerializer(serializers.ModelSerializer):
    """Serializer for test answers"""
    class Meta:
        model = TestAnswer
        fields = [
            'answer_id', 'question', 'answer_text', 'selected_options',
            'is_correct', 'points_earned', 'feedback'
        ]


class ModuleQuizAnswerSerializer(serializers.ModelSerializer):
    """Serializer for module quiz answers with confidence scores"""
    class Meta:
        model = ModuleQuizAnswer
        fields = [
            'answer_id', 'question', 'answer_text', 'is_correct',
            'points_earned', 'confidence_score', 'created_at', 'updated_at'
        ]
        read_only_fields = ['answer_id', 'created_at', 'updated_at']


class TestAttemptSerializer(serializers.ModelSerializer):
    """Serializer for test attempts"""
    answers = TestAttemptAnswerSerializer(many=True, read_only=True)

    class Meta:
        model = TestAttempt
        fields = [
            'attempt_id', 'test', 'user', 'attempt_number', 'started_at',
            'submitted_at', 'time_spent_minutes', 'status', 'score',
            'points_earned', 'passed', 'answers'
        ]


class TestSerializer(serializers.ModelSerializer):
    """Serializer for tests"""
    questions = TestQuestionSerializer(many=True, read_only=True)
    attempts = TestAttemptSerializer(many=True, read_only=True)

    class Meta:
        model = Test
        fields = [
            'test_id', 'course', 'module', 'title', 'description', 'test_type',
            'time_limit_minutes', 'passing_score', 'max_attempts',
            'randomize_questions', 'show_correct_answers', 'points_possible',
            'is_mandatory', 'created_by', 'questions', 'attempts'
        ]


class TestDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for tests with all info"""
    questions = TestQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Test
        fields = [
            'test_id', 'course', 'module', 'title', 'description', 'test_type',
            'time_limit_minutes', 'passing_score', 'max_attempts',
            'randomize_questions', 'show_correct_answers', 'points_possible',
            'is_mandatory', 'created_by', 'created_at', 'updated_at', 'questions'
        ]


class ModuleCompletionSerializer(serializers.ModelSerializer):
    """Serializer for module completions"""
    class Meta:
        model = ModuleCompletion
        fields = [
            'completion_id', 'module', 'user', 'completion_percentage',
            'is_completed', 'time_spent_minutes', 'completed_at'
        ]


class NoteSerializer(serializers.ModelSerializer):
    """Serializer for notes on modules"""
    class Meta:
        model = Note
        fields = ['note_id', 'user', 'module', 'content', 'created_at', 'updated_at']


class ModuleQuizBaseSerializer(serializers.ModelSerializer):
    """Base serializer for module quizzes"""
    questions_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ModuleQuiz
        fields = [
            'quiz_id', 'module', 'title', 'description', 'sequence_order',
            'time_limit_minutes', 'passing_score', 'max_attempts',
            'randomize_questions', 'show_correct_answers', 'points_possible',
            'is_mandatory', 'created_by', 'questions_count', 'created_at', 'updated_at'
        ]
    
    def get_questions_count(self, obj):
        return obj.questions.count()


class ModuleSerializer(serializers.ModelSerializer):
    """Serializer for modules with quiz and resource info"""
    tests = TestSerializer(many=True, read_only=True)
    quizzes = ModuleQuizBaseSerializer(many=True, read_only=True)
    notes = NoteSerializer(many=True, read_only=True)
    completion = serializers.SerializerMethodField()
    mongodb_content_count = serializers.SerializerMethodField()

    class Meta:
        model = Module
        fields = [
            'module_id', 'course', 'title', 'description', 'module_type',
            'sequence_order', 'is_mandatory', 'estimated_duration_minutes',
            'video_count', 'has_quizzes', 'tests', 'quizzes', 'notes', 'completion',
            'mongodb_content_count'
        ]

    def get_completion(self, obj):
        """Get completion info for the current user if available"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                completion = ModuleCompletion.objects.get(module=obj, user=request.user)
                return ModuleCompletionSerializer(completion).data
            except ModuleCompletion.DoesNotExist:
                return None
        return None
    
    def get_mongodb_content_count(self, obj):
        """
        Get count of content items from MongoDB for this module
        This includes videos, PDFs, presentations, and documents
        Note: This requires MongoDB to be available
        """
        try:
            from trainee.mongo_collection import get_mongodb_connection
            db = get_mongodb_connection()
            module_content_collection = db['module_content_items']
            
            count = module_content_collection.count_documents({
                'module_id': str(obj.module_id)
            })
            return count
        except Exception:
            # Return 0 if MongoDB is not available
            return 0


class CourseSerializer(serializers.ModelSerializer):
    """Serializer for courses"""
    modules = ModuleSerializer(many=True, read_only=True)
    total_modules = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'course_id', 'title', 'description', 'about', 'outcomes',
            'course_type', 'status', 'is_mandatory', 'estimated_duration_hours',
            'passing_criteria', 'created_by', 'modules', 'total_modules'
        ]

    def get_total_modules(self, obj):
        return obj.modules.count()


class CourseDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for courses with all info"""
    modules = ModuleSerializer(many=True, read_only=True)
    total_modules = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'course_id', 'title', 'description', 'about', 'outcomes',
            'course_type', 'status', 'is_mandatory', 'estimated_duration_hours',
            'passing_criteria', 'created_by', 'created_at', 'updated_at',
            'modules', 'total_modules', 'progress'
        ]

    def get_total_modules(self, obj):
        return obj.modules.count()

    def get_progress(self, obj):
        """Get progress info for the current user if available"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                progress = UserProgress.objects.get(user=request.user, course=obj)
                return UserProgressSerializer(progress).data
            except UserProgress.DoesNotExist:
                return None
        return None


class CourseAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for course assignments"""
    course_details = CourseSerializer(source='course', read_only=True)

    class Meta:
        model = CourseAssignment
        fields = [
            'assignment_id', 'course', 'course_details', 'assigned_to_user',
            'assigned_to_team', 'assigned_by', 'due_date', 'assigned_at'
        ]


class AssignmentSerializer(serializers.ModelSerializer):
    """Serializer for assignments"""
    class Meta:
        model = Assignment
        fields = [
            'assignment_id', 'course', 'module', 'title', 'description',
            'assignment_type', 'due_date', 'max_attempts', 'points_possible',
            'is_mandatory', 'created_by'
        ]


class AssignmentSubmissionSerializer(serializers.ModelSerializer):
    """Serializer for assignment submissions"""
    class Meta:
        model = AssignmentSubmission
        fields = [
            'submission_id', 'assignment', 'user', 'attempt_number',
            'submission_text', 'submission_files', 'submitted_at', 'status',
            'score', 'points_earned', 'feedback', 'graded_by', 'graded_at'
        ]


class UserProgressSerializer(serializers.ModelSerializer):
    """Serializer for user progress in courses"""
    class Meta:
        model = UserProgress
        fields = [
            'progress_id', 'user', 'course', 'completion_percentage',
            'total_points_earned', 'average_score', 'time_spent_minutes',
            'modules_completed', 'total_modules', 'tests_passed',
            'tests_attempted', 'assignments_submitted', 'assignments_graded',
            'started_at', 'completed_at', 'last_activity'
        ]
