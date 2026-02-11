from django.db import models
from django.contrib.auth.models import User
import uuid

# Team model for grouping users
class Team(models.Model):
	team_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='team_id')
	name = models.CharField(max_length=255, unique=True, db_column='team_name')
	description = models.TextField(blank=True, db_column='description')
	status = models.CharField(max_length=20, default='active', db_column='status')
	created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
	updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')

	class Meta:
		db_table = 'teams'
		managed = True

	def __str__(self):
		return self.name


# User Profile model - maps to PostgreSQL users table
class UserProfile(models.Model):
	ROLE_CHOICES = [
		('admin', 'Admin'),
		('manager', 'Manager'),
		('trainer', 'Trainer'),
		('trainee', 'Trainee'),
	]

	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='user_id')
	first_name = models.CharField(max_length=100, db_column='first_name')
	last_name = models.CharField(max_length=100, db_column='last_name')
	email = models.EmailField(unique=True, db_column='email')
	password_hash = models.CharField(max_length=255, db_column='password_hash')
	role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='trainee', db_column='primary_role')
	status = models.CharField(max_length=20, default='active', db_column='status')
	profile_image_url = models.TextField(blank=True, null=True, db_column='profile_image_url')
	last_login = models.DateTimeField(blank=True, null=True, db_column='last_login')
	created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
	updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')
	teams = models.ManyToManyField(Team, blank=True, related_name='members', through='TeamMember')

	class Meta:
		db_table = 'users'
		managed = True
	
	def __str__(self):
		return f"{self.first_name} {self.last_name}"


class TeamMember(models.Model):
	"""Explicit through table for Team members relationship"""
	user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, db_column='user_id', primary_key=True)
	team = models.ForeignKey(Team, on_delete=models.CASCADE, db_column='team_id')
	is_primary_team = models.BooleanField(default=True, db_column='is_primary_team')
	assigned_at = models.DateTimeField(auto_now_add=True, db_column='assigned_at')
	assigned_by = models.CharField(max_length=255, blank=True, null=True, db_column='assigned_by')

	class Meta:
		db_table = 'team_members'
		managed = True
		unique_together = ('team', 'user')
	
	def __str__(self):
		return f"{self.user.email} in {self.team.name}"


class CourseAssignment(models.Model):
	assignment_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='assignment_id')
	"""Local mapping of external course id to a Team for assignment management."""
	course_id = models.CharField(max_length=255, db_column='course_id', help_text='External LMS course id')
	team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='course_assignments', db_column='assigned_to_team_id')
	assigned_at = models.DateTimeField(auto_now_add=True, db_column='assigned_at')

	class Meta:
		db_table = 'course_assignments'
		managed = True
		unique_together = ('course_id', 'team')

	def __str__(self):
		return f"Course {self.course_id} -> Team {self.team.name}"
