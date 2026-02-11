"""
Serializers for module quizzes and learning resources.
Handles mixed content (videos, quizzes, PDFs, PPTs, etc.) within modules.
"""
from rest_framework import serializers
from trainee.models import ModuleQuiz, ModuleQuizQuestion, LearningResource


class ModuleQuizQuestionSerializer(serializers.ModelSerializer):
    """Serializer for module quiz questions"""
    class Meta:
        model = ModuleQuizQuestion
        fields = [
            'question_id', 'question_text', 'question_type', 'options',
            'correct_answer', 'points', 'difficulty', 'explanation', 'sequence_order'
        ]
        read_only_fields = ['question_id', 'created_at', 'updated_at']


class ModuleQuizSerializer(serializers.ModelSerializer):
    """Serializer for module quizzes with questions"""
    questions = ModuleQuizQuestionSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(
        source='created_by.get_full_name',
        read_only=True
    )

    class Meta:
        model = ModuleQuiz
        fields = [
            'quiz_id', 'module', 'title', 'description', 'sequence_order',
            'time_limit_minutes', 'passing_score', 'max_attempts',
            'randomize_questions', 'show_correct_answers', 'points_possible',
            'is_mandatory', 'created_by', 'created_by_name', 'questions',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['quiz_id', 'created_at', 'updated_at']


class ModuleQuizListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for quizzes in module content list"""
    id = serializers.CharField(source='quiz_id', read_only=True)
    content_type = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(
        source='created_by.get_full_name',
        read_only=True
    )
    questions_count = serializers.SerializerMethodField()
    questions = ModuleQuizQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = ModuleQuiz
        fields = [
            'id', 'quiz_id', 'title', 'description', 'sequence_order', 'time_limit_minutes',
            'passing_score', 'points_possible', 'is_mandatory', 'created_by_name',
            'content_type', 'questions_count', 'questions', 'max_attempts', 'randomize_questions',
            'show_correct_answers'
        ]

    def get_content_type(self, obj):
        return 'quiz'

    def get_questions_count(self, obj):
        """Get the count of questions for this quiz"""
        return obj.questions.count()


class LearningResourceSerializer(serializers.ModelSerializer):
    """Serializer for learning resources"""
    created_by_name = serializers.CharField(
        source='created_by.get_full_name',
        read_only=True
    )

    class Meta:
        model = LearningResource
        fields = [
            'resource_id', 'module', 'title', 'description', 'resource_type',
            'file_url', 'file_size_bytes', 'sequence_order', 'is_mandatory',
            'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['resource_id', 'created_at', 'updated_at']


class LearningResourceListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for resources in module content list"""
    id = serializers.CharField(source='resource_id', read_only=True)
    content_type = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(
        source='created_by.get_full_name',
        read_only=True
    )
    file_size_mb = serializers.SerializerMethodField()

    class Meta:
        model = LearningResource
        fields = [
            'id', 'resource_id', 'title', 'description', 'resource_type', 'file_url',
            'file_size_bytes', 'file_size_mb', 'sequence_order', 'is_mandatory',
            'created_by_name', 'content_type'
        ]

    def get_content_type(self, obj):
        return 'resource'

    def get_file_size_mb(self, obj):
        """Convert file size to MB if available"""
        if obj.file_size_bytes:
            return round(obj.file_size_bytes / (1024 * 1024), 2)
        return None
