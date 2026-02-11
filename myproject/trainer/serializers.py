"""
Trainer app serializers - Complete integration supporting all unit types and advanced features
"""
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from .models import (
    Profile, Course, Unit, VideoUnit, AudioUnit, PresentationUnit,
    TextUnit, PageUnit, Quiz, Question, Assignment, ScormPackage,
    Survey, Enrollment, UnitProgress, AssignmentSubmission,
    QuizAttempt, Leaderboard, MediaMetadata, Team, TeamMember, Notification,
    ModuleSequencing, Note, Role, UserRole
)


class ProfileSerializer(serializers.Serializer):
    """Flexible serializer that handles both Django User and Profile objects"""
    id = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()
    email = serializers.EmailField()
    full_name = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()

    def get_id(self, obj):
        if isinstance(obj, Profile):
            return str(obj.id)
        return str(obj.id) if hasattr(obj, 'id') else None

    def get_username(self, obj):
        if isinstance(obj, Profile):
            return obj.username
        return obj.username

    def get_full_name(self, obj):
        if isinstance(obj, Profile):
            return obj.full_name
        else:
            return f"{obj.first_name} {obj.last_name}".strip() or obj.username

    def get_role(self, obj):
        if isinstance(obj, Profile):
            return obj.primary_role
        # Default role for User objects
        return 'trainer'

    def get_avatar_url(self, obj):
        if isinstance(obj, Profile):
            return obj.profile_image_url
        return None

    def get_created_at(self, obj):
        if isinstance(obj, Profile):
            return obj.created_at
        return obj.date_joined if hasattr(obj, 'date_joined') else None


class VideoUnitSerializer(serializers.ModelSerializer):
    file_path = serializers.CharField(source='video_storage_path', read_only=True)
    video_file = serializers.FileField(write_only=True, required=False)
    
    class Meta:
        model = VideoUnit
        fields = '__all__'
        read_only_fields = ['id']
    
    def create(self, validated_data):
        video_file = validated_data.pop('video_file', None)
        instance = super().create(validated_data)
        if video_file:
            self._save_file(instance, video_file, 'video')
        return instance
    
    def update(self, instance, validated_data):
        video_file = validated_data.pop('video_file', None)
        instance = super().update(instance, validated_data)
        if video_file:
            self._save_file(instance, video_file, 'video')
        return instance
    
    def _save_file(self, instance, file_obj, file_type):
        import os
        from django.conf import settings
        
        media_root = getattr(settings, 'MEDIA_ROOT', r'C:\LMS_uploads')
        os.makedirs(media_root, exist_ok=True)
        
        file_dir = os.path.join(media_root, 'videos')
        os.makedirs(file_dir, exist_ok=True)
        
        filename = f"{instance.id}_{file_obj.name}"
        file_path = os.path.join(file_dir, filename)
        
        with open(file_path, 'wb') as f:
            for chunk in file_obj.chunks():
                f.write(chunk)
        
        instance.video_storage_path = os.path.join('videos', filename)
        instance.save()
        
        try:
            from django.contrib.auth.models import User
            user = User.objects.first()
            profile = Profile.objects.filter(id=user.id).first() if user else Profile.objects.first()
            
            MediaMetadata.objects.filter(storage_path=instance.video_storage_path).delete()
            MediaMetadata.objects.create(
                storage_path=instance.video_storage_path,
                file_name=file_obj.name,
                file_type='video',
                file_size=file_obj.size,
                mime_type=file_obj.content_type,
                unit=instance.unit,
                uploaded_by=profile
            )
        except Exception as e:
            pass


class AudioUnitSerializer(serializers.ModelSerializer):
    file_path = serializers.CharField(source='audio_storage_path', read_only=True)
    audio_file = serializers.FileField(write_only=True, required=False)
    
    class Meta:
        model = AudioUnit
        fields = '__all__'
        read_only_fields = ['id']
    
    def create(self, validated_data):
        audio_file = validated_data.pop('audio_file', None)
        instance = super().create(validated_data)
        if audio_file:
            self._save_file(instance, audio_file, 'audio')
        return instance
    
    def update(self, instance, validated_data):
        audio_file = validated_data.pop('audio_file', None)
        instance = super().update(instance, validated_data)
        if audio_file:
            self._save_file(instance, audio_file, 'audio')
        return instance
    
    def _save_file(self, instance, file_obj, file_type):
        import os
        from django.conf import settings
        
        media_root = getattr(settings, 'MEDIA_ROOT', r'C:\LMS_uploads')
        os.makedirs(media_root, exist_ok=True)
        
        file_dir = os.path.join(media_root, 'audio')
        os.makedirs(file_dir, exist_ok=True)
        
        filename = f"{instance.id}_{file_obj.name}"
        file_path = os.path.join(file_dir, filename)
        
        with open(file_path, 'wb') as f:
            for chunk in file_obj.chunks():
                f.write(chunk)
        
        instance.audio_storage_path = os.path.join('audio', filename)
        instance.save()
        
        try:
            from django.contrib.auth.models import User
            user = User.objects.first()
            profile = Profile.objects.filter(id=user.id).first() if user else Profile.objects.first()
            
            MediaMetadata.objects.filter(storage_path=instance.audio_storage_path).delete()
            MediaMetadata.objects.create(
                storage_path=instance.audio_storage_path,
                file_name=file_obj.name,
                file_type='audio',
                file_size=file_obj.size,
                mime_type=file_obj.content_type,
                unit=instance.unit,
                uploaded_by=profile
            )
        except Exception as e:
            pass


class PresentationUnitSerializer(serializers.ModelSerializer):
    file_path = serializers.CharField(source='file_storage_path', read_only=True)
    presentation_file = serializers.FileField(write_only=True, required=False)
    
    class Meta:
        model = PresentationUnit
        fields = '__all__'
        read_only_fields = ['id']
    
    def create(self, validated_data):
        presentation_file = validated_data.pop('presentation_file', None)
        instance = super().create(validated_data)
        if presentation_file:
            self._save_file(instance, presentation_file, 'presentation')
        return instance
    
    def update(self, instance, validated_data):
        presentation_file = validated_data.pop('presentation_file', None)
        instance = super().update(instance, validated_data)
        if presentation_file:
            self._save_file(instance, presentation_file, 'presentation')
        return instance
    
    def _save_file(self, instance, file_obj, file_type):
        import os
        from django.conf import settings
        
        media_root = getattr(settings, 'MEDIA_ROOT', r'C:\LMS_uploads')
        os.makedirs(media_root, exist_ok=True)
        
        file_dir = os.path.join(media_root, 'presentations')
        os.makedirs(file_dir, exist_ok=True)
        
        filename = f"{instance.id}_{file_obj.name}"
        file_path = os.path.join(file_dir, filename)
        
        with open(file_path, 'wb') as f:
            for chunk in file_obj.chunks():
                f.write(chunk)
        
        instance.file_storage_path = os.path.join('presentations', filename)
        instance.save()
        
        try:
            from django.contrib.auth.models import User
            user = User.objects.first()
            profile = Profile.objects.filter(id=user.id).first() if user else Profile.objects.first()
            
            MediaMetadata.objects.filter(storage_path=instance.file_storage_path).delete()
            MediaMetadata.objects.create(
                storage_path=instance.file_storage_path,
                file_name=file_obj.name,
                file_type='presentation',
                file_size=file_obj.size,
                mime_type=file_obj.content_type,
                unit=instance.unit,
                uploaded_by=profile
            )
        except Exception as e:
            pass


class TextUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = TextUnit
        fields = '__all__'
        read_only_fields = ['id']


class PageUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = PageUnit
        fields = '__all__'
        read_only_fields = ['id']


class QuestionSerializer(serializers.ModelSerializer):
    quiz = serializers.PrimaryKeyRelatedField(
        queryset=Quiz.objects.all(),
        many=False,
        required=True,
        help_text='UUID of the quiz'
    )
    
    class Meta:
        model = Question
        fields = '__all__'
        read_only_fields = ['id']


class QuizSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    unit = serializers.PrimaryKeyRelatedField(queryset=Unit.objects.all(), many=False, required=False)

    class Meta:
        model = Quiz
        fields = ['id', 'unit', 'time_limit', 'passing_score', 'attempts_allowed', 
                  'show_answers', 'randomize_questions', 'mandatory_completion', 'questions']
        read_only_fields = ['id', 'questions']


class AssignmentSerializer(serializers.ModelSerializer):
    created_by = serializers.UUIDField(required=False, allow_null=True)
    
    class Meta:
        model = Assignment
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        # Provide a default created_by if not provided
        if 'created_by' not in validated_data or validated_data['created_by'] is None:
            from django.db import connection
            cursor = connection.cursor()
            cursor.execute("SELECT user_id FROM users LIMIT 1")
            row = cursor.fetchone()
            if row:
                import uuid
                validated_data['created_by'] = uuid.UUID(str(row[0]))
        return super().create(validated_data)


class ScormPackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScormPackage
        fields = '__all__'
        read_only_fields = ['id']


class SurveySerializer(serializers.ModelSerializer):
    class Meta:
        model = Survey
        fields = '__all__'
        read_only_fields = ['id']


class UnitListSerializer(serializers.ModelSerializer):
    """Lightweight unit serializer for list views - no nested relations"""
    type = serializers.CharField(source='module_type', required=False)
    order = serializers.IntegerField(source='sequence_order', required=False)
    is_required = serializers.BooleanField(source='is_mandatory', required=False)

    class Meta:
        model = Unit
        fields = [
            'id', 'course', 'module_type', 'type', 'title', 'description', 'sequence_order', 'order',
            'estimated_duration_minutes', 'is_mandatory', 'is_required', 'has_quizzes', 'video_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'module_type': {'required': False},
            'title': {'required': False},
            'description': {'required': False}
        }


class UnitSerializer(serializers.ModelSerializer):
    """Unit/Module serializer with support for all subtypes and backward compatibility"""
    type = serializers.CharField(source='module_type', required=False)
    order = serializers.IntegerField(source='sequence_order', required=False)
    is_required = serializers.BooleanField(source='is_mandatory', required=False)

    video_details = VideoUnitSerializer(read_only=True, required=False)
    audio_details = AudioUnitSerializer(read_only=True, required=False)
    presentation_details = PresentationUnitSerializer(read_only=True, required=False)
    text_details = TextUnitSerializer(read_only=True, required=False)
    page_details = PageUnitSerializer(read_only=True, required=False)
    quiz_details = QuizSerializer(read_only=True, required=False)
    assignment_details = AssignmentSerializer(read_only=True, required=False)
    scorm_details = ScormPackageSerializer(read_only=True, required=False)
    survey_details = SurveySerializer(read_only=True, required=False)
    
    # Frontend compatibility aliases
    video_unit = VideoUnitSerializer(source='video_details', read_only=True, required=False)
    audio_unit = AudioUnitSerializer(source='audio_details', read_only=True, required=False)
    presentation_unit = PresentationUnitSerializer(source='presentation_details', read_only=True, required=False)
    text_content = serializers.CharField(source='text_details.content', read_only=True, allow_null=True, required=False)
    quiz = QuizSerializer(source='quiz_details', read_only=True, required=False)
    assignment_unit = AssignmentSerializer(source='assignment_details', read_only=True, required=False)

    class Meta:
        model = Unit
        fields = [
            'id', 'course', 'module_type', 'type', 'title', 'description', 'sequence_order', 'order',
            'estimated_duration_minutes', 'is_mandatory', 'is_required', 'has_quizzes', 'video_count',
            'created_at', 'updated_at', 'video_details', 'audio_details',
            'presentation_details', 'text_details', 'page_details', 'quiz_details',
            'assignment_details', 'scorm_details', 'survey_details',
            'video_unit', 'audio_unit', 'presentation_unit', 'text_content', 'quiz', 'assignment_unit'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'module_type': {'required': False},
            'title': {'required': False},
            'description': {'required': False}
        }

    def to_representation(self, instance):
        """Ensure type field is always included in response"""
        data = super().to_representation(instance)
        data['type'] = instance.module_type
        data['order'] = instance.sequence_order
        data['is_required'] = instance.is_mandatory
        return data

    def validate(self, attrs):
        """Require module_type for POST requests"""
        if self.context.get('request').method == 'POST':
            if not attrs.get('module_type'):
                raise serializers.ValidationError({'type': 'This field is required.'})
        return attrs


class CourseSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    units_count = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'description', 'about', 'outcomes', 'status', 'course_type',
            'is_mandatory', 'estimated_duration_hours', 'passing_criteria',
            'created_by', 'created_by_name', 'units_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']

    def get_created_by_name(self, obj):
        return obj.created_by.full_name if obj.created_by else 'Unknown'
    
    def get_units_count(self, obj):
        return obj.units.count() if hasattr(obj, 'units') else 0


class CourseDetailSerializer(serializers.ModelSerializer):
    units = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'description', 'about', 'outcomes', 'status', 'course_type',
            'is_mandatory', 'estimated_duration_hours', 'passing_criteria',
            'created_by', 'created_by_name', 'units', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']

    def get_created_by_name(self, obj):
        return obj.created_by.full_name if obj.created_by else 'Unknown'
    
    def get_units(self, obj):
        """Get units with media details for preview"""
        units = obj.units.all()
        data = []
        for unit in units:
            unit_data = {
                'id': str(unit.id),
                'course': str(unit.course.id) if unit.course else None,
                'module_type': unit.module_type,
                'type': unit.module_type,
                'title': unit.title,
                'description': unit.description,
                'sequence_order': unit.sequence_order,
                'order': unit.sequence_order,
                'estimated_duration_minutes': unit.estimated_duration_minutes,
                'is_mandatory': unit.is_mandatory,
                'is_required': unit.is_mandatory,
                'has_quizzes': unit.has_quizzes,
                'video_count': unit.video_count,
                'created_at': unit.created_at,
                'updated_at': unit.updated_at,
            }
            
            # Add media details based on type
            try:
                if unit.module_type == 'video' and hasattr(unit, 'video_details'):
                    if unit.video_details:
                        unit_data['video_unit'] = VideoUnitSerializer(unit.video_details).data
                        unit_data['video_details'] = VideoUnitSerializer(unit.video_details).data
            except:
                pass
            
            try:
                if unit.module_type == 'audio' and hasattr(unit, 'audio_details'):
                    if unit.audio_details:
                        unit_data['audio_unit'] = AudioUnitSerializer(unit.audio_details).data
                        unit_data['audio_details'] = AudioUnitSerializer(unit.audio_details).data
            except:
                pass
            
            try:
                if unit.module_type == 'presentation' and hasattr(unit, 'presentation_details'):
                    if unit.presentation_details:
                        unit_data['presentation_unit'] = PresentationUnitSerializer(unit.presentation_details).data
                        unit_data['presentation_details'] = PresentationUnitSerializer(unit.presentation_details).data
            except:
                pass
            
            try:
                if unit.module_type == 'text' and hasattr(unit, 'text_details'):
                    if unit.text_details:
                        text_serializer = TextUnitSerializer(unit.text_details)
                        unit_data['text_content'] = text_serializer.data.get('content') if text_serializer.data else None
                        unit_data['text_details'] = text_serializer.data
            except:
                pass
            
            try:
                if unit.module_type == 'page' and hasattr(unit, 'page_details'):
                    if unit.page_details:
                        unit_data['page_details'] = PageUnitSerializer(unit.page_details).data
            except:
                pass
            
            try:
                if unit.module_type == 'quiz' and hasattr(unit, 'quiz_details'):
                    if unit.quiz_details:
                        unit_data['quiz'] = QuizSerializer(unit.quiz_details).data
                        unit_data['quiz_details'] = QuizSerializer(unit.quiz_details).data
            except:
                pass
            
            try:
                if unit.module_type == 'assignment' and hasattr(unit, 'assignment_details'):
                    if unit.assignment_details:
                        unit_data['assignment_unit'] = AssignmentSerializer(unit.assignment_details).data
                        unit_data['assignment_details'] = AssignmentSerializer(unit.assignment_details).data
            except:
                pass
            
            data.append(unit_data)
        
        return data


class CourseNestedCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating courses with nested units in a single atomic transaction.
    
    Usage:
    POST /api/trainer/courses/
    {
        "title": "Python Basics",
        "description": "Learn Python fundamentals",
        "course_type": "self_paced",
        "units": [
            {
                "title": "Introduction to Python",
                "module_type": "video",
                "description": "Video introduction",
                "estimated_duration_minutes": 30,
                "is_mandatory": true
            },
            {
                "title": "Python Quiz",
                "module_type": "quiz",
                "description": "Test your knowledge",
                "estimated_duration_minutes": 15,
                "is_mandatory": true
            }
        ]
    }
    """
    
    units = UnitListSerializer(many=True, write_only=True, required=False)
    
    class Meta:
        model = Course
        fields = [
            'id', 'title', 'description', 'about', 'outcomes', 'status', 'course_type',
            'is_mandatory', 'estimated_duration_hours', 'passing_criteria', 'units',
            'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']
        extra_kwargs = {
            'title': {'required': True},
            'description': {'required': False},
            'about': {'required': False},
            'outcomes': {'required': False},
            'status': {'required': False, 'default': 'draft'},
            'course_type': {'required': False, 'default': 'self_paced'},
            'is_mandatory': {'required': False, 'default': False},
            'estimated_duration_hours': {'required': False, 'allow_null': True},
            'passing_criteria': {'required': False, 'default': 70},
        }
    
    def validate_units(self, value):
        """Validate units before creation"""
        if not value:
            return value
        
        for idx, unit_data in enumerate(value):
            if not unit_data.get('title'):
                raise serializers.ValidationError(
                    f"Unit {idx + 1}: 'title' field is required"
                )
            if not unit_data.get('module_type'):
                raise serializers.ValidationError(
                    f"Unit {idx + 1}: 'module_type' field is required"
                )
        
        return value
    
    def create(self, validated_data):
        """
        Create course with nested units using atomic transaction.
        Ensures all-or-nothing insertion.
        """
        from django.db import transaction
        
        units_data = validated_data.pop('units', [])
        
        try:
            with transaction.atomic():
                # Create the course
                course = Course.objects.create(**validated_data)
                
                # Create units in sequence
                for idx, unit_data in enumerate(units_data):
                    # Set sequence_order based on position
                    unit_data['sequence_order'] = idx + 1
                    Unit.objects.create(course=course, **unit_data)
                
                return course
        except Exception as e:
            # Transaction will be automatically rolled back
            raise serializers.ValidationError(
                f"Failed to create course with units: {str(e)}"
            )
    
    def to_representation(self, instance):
        """Return full course data including created units"""
        return CourseDetailSerializer(instance).data


class EnrollmentSerializer(serializers.ModelSerializer):
    # For list/retrieve: show nested profile details
    user_detail = ProfileSerializer(source='user', read_only=True)
    # For create/update: accept user as UUID
    user = serializers.PrimaryKeyRelatedField(
        queryset=Profile.objects.all(),
        write_only=False
    )
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    # Make assigned_by optional and allow null in responses (it's auto-populated by perform_create)
    assigned_by = serializers.PrimaryKeyRelatedField(
        queryset=Profile.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = Enrollment
        fields = '__all__'
        read_only_fields = ['id', 'assigned_at']


class UnitProgressSerializer(serializers.ModelSerializer):
    unit_title = serializers.CharField(source='unit.title', read_only=True)

    class Meta:
        model = UnitProgress
        fields = '__all__'
        read_only_fields = ['id']


class AssignmentSubmissionSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model = AssignmentSubmission
        fields = '__all__'
        read_only_fields = ['id', 'submitted_at', 'graded_at']


class QuizAttemptSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model = QuizAttempt
        fields = '__all__'
        read_only_fields = ['id', 'started_at', 'completed_at']


class LeaderboardSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True, allow_null=True)
    user = serializers.SerializerMethodField()
    team_info = serializers.SerializerMethodField()

    class Meta:
        model = Leaderboard
        fields = '__all__'
        read_only_fields = ['id', 'updated_at']
    
    def get_user(self, obj):
        """Return user details for frontend compatibility"""
        return {
            'id': str(obj.user.id),
            'full_name': obj.user.full_name,
            'email': obj.user.email,
            'avatar_url': None
        }
    
    def get_team_info(self, obj):
        """Return user's primary team information"""
        team_member = TeamMember.objects.filter(
            user=obj.user,
            is_primary_team=True
        ).select_related('team').first()
        
        if team_member and team_member.team:
            return {
                'id': str(team_member.team.team_id),
                'name': team_member.team.team_name,
                'description': team_member.team.description
            }
        return None


# TeamLeaderboardSerializer removed - TeamLeaderboard model used same 'leaderboard' table as Leaderboard
# Use LeaderboardSerializer with team filtering instead


class MediaMetadataSerializer(serializers.ModelSerializer):
    unit_title = serializers.CharField(source='unit.title', read_only=True, required=False)
    course_id = serializers.SerializerMethodField(read_only=True)
    course_title = serializers.SerializerMethodField(read_only=True)
    
    def get_course_id(self, obj):
        return str(obj.unit.course.id) if obj.unit and obj.unit.course else None
    
    def get_course_title(self, obj):
        return obj.unit.course.title if obj.unit and obj.unit.course else None
    
    class Meta:
        model = MediaMetadata
        fields = [
            'id', 'storage_path', 'file_name', 'file_type', 'file_size', 'mime_type',
            'duration', 'width', 'height', 'unit', 'unit_title', 'course_id', 'course_title',
            'uploaded_by', 'uploaded_at'
        ]
        read_only_fields = ['id', 'uploaded_at', 'unit_title', 'course_id', 'course_title']


class TeamMemberSerializer(serializers.ModelSerializer):
    user = ProfileSerializer(read_only=True)
    user_id = serializers.UUIDField(source='user.id', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = TeamMember
        fields = ['user', 'user_id', 'user_name', 'user_email', 'is_primary_team', 'assigned_at']
        read_only_fields = ['assigned_at']


class TeamSerializer(serializers.ModelSerializer):
    members = TeamMemberSerializer(many=True, read_only=True)
    members_count = serializers.SerializerMethodField()
    # manager and created_by columns don't exist in database - removed

    class Meta:
        model = Team
        fields = [
            'team_id', 'team_name', 'description', 'status',
            'members', 'members_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['team_id', 'created_at', 'updated_at']

    def get_members_count(self, obj):
        return obj.members.count()


class NotificationSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    id = serializers.CharField(source='notification_id', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'notification_id', 'user', 'user_name', 'notification_type', 'title', 'message',
            'link_url', 'priority', 'status', 'sent_via', 'read_at', 'created_at'
        ]
        read_only_fields = ['id', 'notification_id', 'user_name', 'created_at']


class ModuleSequencingSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    module_title = serializers.CharField(source='module.title', read_only=True)
    preceding_module_title = serializers.CharField(source='preceding_module.title', read_only=True, allow_null=True)

    class Meta:
        model = ModuleSequencing
        fields = [
            'sequence_id', 'course', 'course_title', 'module', 'module_title',
            'preceding_module', 'preceding_module_title', 'drip_feed_rule',
            'drip_feed_delay_days', 'prerequisite_completed', 'created_at', 'updated_at'
        ]
        read_only_fields = ['sequence_id', 'created_at', 'updated_at']


# ModuleCompletionSerializer removed - ModuleCompletion model used same 'module_completions' table as UnitProgress
# Use UnitProgressSerializer with module filtering instead


class NoteSerializer(serializers.ModelSerializer):
    module_title = serializers.CharField(source='module.title', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model = Note
        fields = [
            'note_id', 'user', 'user_name', 'module', 'module_title',
            'content', 'created_at', 'updated_at'
        ]
        read_only_fields = ['note_id', 'created_at', 'updated_at']


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['role_id', 'role_name', 'description', 'created_at', 'updated_at']
        read_only_fields = ['role_id', 'created_at', 'updated_at']


class UserRoleSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    role_name = serializers.CharField(source='role.role_name', read_only=True)
    assigned_by_name = serializers.CharField(source='assigned_by.full_name', read_only=True, allow_null=True)

    class Meta:
        model = UserRole
        fields = ['user', 'user_name', 'role', 'role_name', 'assigned_at', 'assigned_by', 'assigned_by_name']
        read_only_fields = ['assigned_at']
