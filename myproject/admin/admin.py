from django.contrib import admin
from .models import Team, UserProfile


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
	list_display = ('team_id', 'name', 'created_at')
	search_fields = ('name',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
	list_display = ('id', 'email', 'first_name', 'last_name', 'role', 'status')
	list_filter = ('role', 'status')
	search_fields = ('email', 'first_name', 'last_name')
