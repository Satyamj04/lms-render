from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Team, UserProfile
from .models import CourseAssignment
from rest_framework import serializers as drf_serializers


class CourseSerializer(drf_serializers.Serializer):
    id = drf_serializers.CharField()
    title = drf_serializers.CharField()
    short_description = drf_serializers.CharField(allow_blank=True)


class CourseDetailSerializer(drf_serializers.Serializer):
    id = drf_serializers.CharField()
    title = drf_serializers.CharField()
    description = drf_serializers.CharField(allow_blank=True)
    modules_count = drf_serializers.IntegerField()
    quizzes_count = drf_serializers.IntegerField()
    metadata = drf_serializers.DictField(child=drf_serializers.CharField(), required=False)


class CourseAssignmentSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = CourseAssignment
        fields = ['assignment_id', 'course_id', 'team', 'assigned_at']


class AuditLogSerializer(drf_serializers.Serializer):
    id = drf_serializers.CharField()
    action = drf_serializers.CharField()
    resource = drf_serializers.CharField(allow_null=True)
    resource_id = drf_serializers.CharField(allow_null=True)
    user_id = drf_serializers.CharField(allow_null=True)
    user_name = drf_serializers.CharField(allow_null=True)
    timestamp = drf_serializers.DateTimeField()
    details = drf_serializers.CharField(allow_blank=True)


class TeamSerializer(serializers.ModelSerializer):
    members_count = serializers.SerializerMethodField(read_only=True)
    manager_id = serializers.SerializerMethodField(read_only=True)
    manager_name = serializers.SerializerMethodField(read_only=True)
    members = serializers.SerializerMethodField(read_only=True)
    trainer_id = serializers.SerializerMethodField(read_only=True)
    trainer_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Team
        fields = ['team_id', 'name', 'description', 'created_at', 'members_count', 'manager_id', 'manager_name', 'trainer_id', 'trainer_name', 'members']

    def get_members_count(self, obj):
        return obj.members.count()

    def get_manager_id(self, obj):
        try:
            manager_profile = obj.members.filter(role='manager').first()
            if manager_profile:
                return str(manager_profile.id)
        except:
            pass
        return None

    def get_manager_name(self, obj):
        try:
            manager_profile = obj.members.filter(role='manager').first()
            if manager_profile:
                first = manager_profile.first_name or ''
                last = manager_profile.last_name or ''
                name = f"{first} {last}".strip()
                return name if name else manager_profile.email
        except:
            pass
        return None

    def get_members(self, obj):
        users = []
        try:
            for profile in obj.members.all():
                users.append({
                    'id': str(profile.id),
                    'first_name': profile.first_name,
                    'last_name': profile.last_name,
                    'email': profile.email
                })
        except:
            pass
        return users

    def get_trainer_id(self, obj):
        try:
            trainer_profile = obj.members.filter(role='trainer').first()
            if trainer_profile:
                return str(trainer_profile.id)
        except:
            pass
        return None

    def get_trainer_name(self, obj):
        try:
            trainer_profile = obj.members.filter(role='trainer').first()
            if trainer_profile:
                first = trainer_profile.first_name or ''
                last = trainer_profile.last_name or ''
                name = f"{first} {last}".strip()
                return name if name else trainer_profile.email
        except:
            pass
        return None


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['id', 'first_name', 'last_name', 'email', 'role', 'status', 'teams']


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['id', 'first_name', 'last_name', 'email', 'role', 'status', 'teams']


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    username = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = UserProfile
        fields = ['first_name', 'last_name', 'email', 'password', 'username', 'role', 'teams']

    def create(self, validated_data):
        from django.contrib.auth.hashers import make_password
        
        # Extract password (required for user creation)
        password = validated_data.pop('password', None)
        if not password:
            raise serializers.ValidationError({'password': 'Password is required'})
        
        # Hash the password using Django's make_password
        hashed_password = make_password(password)
        
        # Extract teams (many-to-many)
        teams = validated_data.pop('teams', [])
        
        # Username is optional - use email if not provided
        username = validated_data.pop('username', None) or validated_data.get('email', '')
        
        # Create the UserProfile instance with hashed password
        user_profile = UserProfile.objects.create(
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            email=validated_data.get('email', ''),
            password_hash=hashed_password,  # Store HASHED password
            role=validated_data.get('role', 'trainee'),
            status='active'
        )
        
        # Add teams if provided
        if teams:
            user_profile.teams.set(teams)
        
        return user_profile
