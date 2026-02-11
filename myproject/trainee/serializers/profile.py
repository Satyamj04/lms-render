"""
Serializers for user profiles.
"""
from rest_framework import serializers
from admin.models import UserProfile as User, Team, TeamMember


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user profiles"""
    class Meta:
        model = User
        fields = [
            'user_id', 'first_name', 'last_name', 'email', 'primary_role',
            'status', 'profile_image_url', 'last_login', 'created_at'
        ]
        read_only_fields = ['user_id', 'created_at']


class UserDetailSerializer(serializers.ModelSerializer):
    """Detailed user serializer with roles"""
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'user_id', 'first_name', 'last_name', 'email', 'primary_role',
            'status', 'profile_image_url', 'last_login', 'created_at',
            'updated_at', 'roles'
        ]
        read_only_fields = ['user_id', 'created_at', 'updated_at']

    def get_roles(self, obj):
        """Get all roles assigned to the user"""
        roles = obj.user_roles.all()
        return [{'role_id': r.role.role_id, 'role_name': r.role.role_name} for r in roles]


class TeamSerializer(serializers.ModelSerializer):
    """Serializer for teams"""
    class Meta:
        model = Team
        fields = [
            'team_id', 'team_name', 'description', 'status',
            'manager', 'created_by', 'created_at'
        ]


class TeamMemberSerializer(serializers.ModelSerializer):
    """Serializer for team members"""
    user_details = UserSerializer(source='user', read_only=True)

    class Meta:
        model = TeamMember
        fields = [
            'team', 'user', 'user_details', 'is_primary_team',
            'assigned_at', 'assigned_by'
        ]


class UserRoleSerializer(serializers.ModelSerializer):
    """Serializer for user roles assignment"""
    role_name = serializers.CharField(source='role.role_name', read_only=True)

    class Meta:
        model = UserRole
        fields = [
            'user', 'role', 'role_name', 'assigned_at', 'assigned_by'
        ]
