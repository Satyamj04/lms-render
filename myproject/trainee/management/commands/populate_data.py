"""
Management command to populate sample data for testing and development.
Creates sample courses, modules, tests, badges, and other learning content.

NOTE: Users must be created through Django admin panel using:
  python main.py createsuperuser
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
import uuid
from trainee.models import (
    User, Role,
    Course, Module, 
    Test, TestQuestion,
    UserProgress, Badge, BadgeAssignment, Leaderboard,
    Assignment
)
from admin.models import CourseAssignment


class Command(BaseCommand):
    help = 'Populate sample data for the LMS (courses, badges, etc.)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting data population...'))
        self.stdout.write(self.style.WARNING('NOTE: Users must be created through Django admin using: python main.py createsuperuser'))
        
        # Create roles (required for the system)
        admin_role, _ = Role.objects.get_or_create(
            role_name='admin',
            defaults={'description': 'Administrator role'}
        )
        trainer_role, _ = Role.objects.get_or_create(
            role_name='trainer',
            defaults={'description': 'Trainer role'}
        )
        trainee_role, _ = Role.objects.get_or_create(
            role_name='trainee',
            defaults={'description': 'Trainee role'}
        )
        manager_role, _ = Role.objects.get_or_create(
            role_name='manager',
            defaults={'description': 'Manager role'}
        )
        
        self.stdout.write(self.style.SUCCESS('✓ Roles configured'))
        
        # Get existing users from database (created via Django admin)
        admin_users = User.objects.filter(primary_role='admin')
        if not admin_users.exists():
            self.stdout.write(self.style.ERROR(
                '⚠ No admin user found! Create one with: python main.py createsuperuser'
            ))
            return
        
        admin_user = admin_users.first()
        self.stdout.write(self.style.SUCCESS(f'✓ Using admin user: {admin_user.email}'))
        
        # Get all trainees (users created via Django admin)
        trainees = User.objects.filter(primary_role='trainee')
        if not trainees.exists():
            self.stdout.write(self.style.WARNING(
                '⚠ No trainee users found. Create trainee users via Django admin at: http://localhost:8000/admin/'
            ))
        
        # Create sample courses
        courses_data = [
            {
                'title': 'Python Fundamentals',
                'description': 'Learn Python basics and programming concepts with hands-on projects',
                'course_type': 'self_paced',
                'estimated_duration_hours': 40,
                'instructor': 'Rajesh Kumar'
            },
            {
                'title': 'Web Development with Django',
                'description': 'Build robust web applications using Django framework and best practices',
                'course_type': 'instructor_led',
                'estimated_duration_hours': 60,
                'instructor': 'Priya Sharma'
            },
            {
                'title': 'Database Design & SQL',
                'description': 'Design and optimize relational databases with SQL and NoSQL',
                'course_type': 'blended',
                'estimated_duration_hours': 50,
                'instructor': 'Amit Patel'
            },
            {
                'title': 'React Frontend Development',
                'description': 'Build modern interactive user interfaces with React',
                'course_type': 'self_paced',
                'estimated_duration_hours': 45,
                'instructor': 'Sneha Verma'
            }
        ]
        
        courses = []
        for course_data in courses_data:
            course, created = Course.objects.get_or_create(
                title=course_data['title'],
                defaults={
                    'course_id': uuid.uuid4(),
                    'description': course_data['description'],
                    'course_type': course_data['course_type'],
                    'estimated_duration_hours': course_data['estimated_duration_hours'],
                    'status': 'published',
                    'passing_criteria': 70,
                    'created_by': admin_user
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created course: {course.title}'))
            courses.append(course)
            
            # Create modules for each course
            modules_data = [
                {'title': 'Getting Started', 'sequence_order': 1, 'duration': 5},
                {'title': 'Core Concepts', 'sequence_order': 2, 'duration': 8},
                {'title': 'Advanced Topics', 'sequence_order': 3, 'duration': 10},
                {'title': 'Project Work', 'sequence_order': 4, 'duration': 12},
            ]
            
            for mod_data in modules_data:
                module, mod_created = Module.objects.get_or_create(
                    course=course,
                    sequence_order=mod_data['sequence_order'],
                    defaults={
                        'title': mod_data['title'],
                        'description': f"{course.title} - {mod_data['title']} module",
                        'module_type': 'mixed',
                        'is_mandatory': True,
                        'estimated_duration_minutes': mod_data['duration'] * 60,
                        'video_count': 3,
                        'has_quizzes': True
                    }
                )
                if mod_created:
                    self.stdout.write(f'  Created module: {module.title}')
                    
                    # Create tests for each module
                    test, test_created = Test.objects.get_or_create(
                        module=module,
                        title=f"{module.title} Quiz",
                        defaults={
                            'description': f"Assessment for {module.title}",
                            'test_type': 'quiz',
                            'passing_score': 70,
                            'max_attempts': 3,
                            'time_limit_minutes': 15,
                            'points_possible': 100,
                            'is_mandatory': True,
                            'created_by': admin_user
                        }
                    )
                    if test_created:
                        self.stdout.write(f'    Created test: {test.title}')
                        
                        # Create test questions
                        for q_num in range(1, 6):
                            TestQuestion.objects.get_or_create(
                                test=test,
                                sequence_order=q_num,
                                defaults={
                                    'question_text': f"Sample question {q_num}: What is the correct answer?",
                                    'question_type': 'mcq',
                                    'points': 20,
                                    'difficulty': 'medium',
                                    'correct_answer': 'A',
                                    'options': {'A': 'Option A', 'B': 'Option B', 'C': 'Option C', 'D': 'Option D'}
                                }
                            )
        
        # Assign courses to trainees
        for trainee in trainees:
            for course in courses:
                assignment, created = CourseAssignment.objects.get_or_create(
                    course=course,
                    assigned_to_user=trainee,
                    defaults={
                        'assigned_by': admin_user,
                        'due_date': timezone.now() + timezone.timedelta(days=30)
                    }
                )
                if created:
                    self.stdout.write(f'Assigned {course.title} to {trainee.email}')
        
        # Create badges
        badges_data = [
            {'badge_name': 'Quick Learner', 'badge_type': 'gold', 'points_threshold': 100},
            {'badge_name': 'Completion Master', 'badge_type': 'silver', 'points_threshold': 50},
            {'badge_name': 'Good Start', 'badge_type': 'bronze', 'points_threshold': 10}
        ]
        
        badge_objs = []
        for badge_data in badges_data:
            badge, created = Badge.objects.get_or_create(
                badge_name=badge_data['badge_name'],
                defaults={
                    'description': f"{badge_data['badge_name']} achievement",
                    'badge_type': badge_data['badge_type'],
                    'points_threshold': badge_data['points_threshold'],
                    'visibility': 'public',
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created badge: {badge.badge_name}'))
            badge_objs.append(badge)
        
        # Assign some badges to trainees
        for trainee in trainees[:1]:  # Assign to first trainee for demo
            for badge in badge_objs:
                BadgeAssignment.objects.get_or_create(
                    user=trainee,
                    badge=badge,
                    defaults={
                        'assigned_by': admin_user,
                        'reason': 'Sample achievement'
                    }
                )
        
        # Create user progress records with varied data
        progress_data = [
            {'completion': 65, 'points': 650, 'score': 75},
            {'completion': 40, 'points': 400, 'score': 65},
            {'completion': 85, 'points': 850, 'score': 88},
            {'completion': 20, 'points': 200, 'score': 45},
        ]
        
        for idx, trainee in enumerate(trainees):
            progress_idx = idx % len(progress_data)
            data = progress_data[progress_idx]
            
            for course_idx, course in enumerate(courses):
                UserProgress.objects.get_or_create(
                    user=trainee,
                    course=course,
                    defaults={
                        'completion_percentage': max(0, data['completion'] - (course_idx * 5)),
                        'total_points_earned': max(0, data['points'] - (course_idx * 50)),
                        'average_score': max(0, data['score'] - (course_idx * 3)),
                        'started_at': timezone.now() - timezone.timedelta(days=30)
                    }
                )
        
        # Create leaderboard entries with varied scores
        leaderboard_points = [1000, 950, 880, 750, 600, 500, 450, 350, 250, 150]
        for idx, trainee in enumerate(trainees):
            points = leaderboard_points[idx % len(leaderboard_points)]
            Leaderboard.objects.get_or_create(
                scope='global',
                user=trainee,
                defaults={
                    'points': points,
                    'rank': idx + 1
                }
            )
        
        self.stdout.write(self.style.SUCCESS('Data population completed successfully!'))
