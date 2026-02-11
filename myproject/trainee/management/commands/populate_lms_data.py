"""
Django management command to populate sample LMS data for testing
Creates users, courses, modules, enrollments, and links media files
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
import uuid

from trainee.models import (
    User, Role, UserRole, Team, TeamMember, Course, Module, ModuleQuiz, 
    ModuleQuizQuestion, Assignment, Enrollment, UnitProgress, Badge, 
    BadgeAssignment, Leaderboard, Notification, UserProgress, VideoUnit,
    AudioUnit, PresentationUnit, TextUnit, ScormPackage, MediaMetadata, Quiz,
    Question, QuizAttempt, Assessment, AssignmentSubmission, TestBank, Test,
    TestQuestion, TestAttempt
)
from trainee.utils.media_handler import MediaHandler


class Command(BaseCommand):
    help = 'Populate LMS database with sample data for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--media',
            action='store_true',
            help='Scan and link media files from C:\\LMS_uploads'
        )
        parser.add_argument(
            '--minimal',
            action='store_true',
            help='Create minimal sample data'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('[LMS] Starting LMS data population...'))
        
        try:
            # Create roles
            self.stdout.write('[STEP] Creating roles...')
            self.create_roles()
            
            # Create users
            self.stdout.write('[STEP] Creating users...')
            admin_user, trainer_user, trainee_users = self.create_users()
            
            # Create teams
            self.stdout.write('[STEP] Creating teams...')
            teams = self.create_teams(trainer_user, trainee_users)
            
            # Create courses
            self.stdout.write('[STEP] Creating courses...')
            courses = self.create_courses(trainer_user)
            
            # Create modules
            self.stdout.write('[STEP] Creating modules...')
            modules_by_course = self.create_modules(courses, trainer_user)
            
            # Create enrollments
            self.stdout.write('[STEP] Creating enrollments...')
            self.create_enrollments(courses, trainee_users, trainer_user)
            
            # Create quizzes and assignments
            self.stdout.write('[STEP] Creating assessments...')
            self.create_assessments(courses, modules_by_course, trainer_user)
            
            # Link media files if requested
            if options.get('media'):
                self.stdout.write('[STEP] Linking media files...')
                self.link_media_files(modules_by_course, trainer_user)
            
            self.stdout.write(self.style.SUCCESS(
                '[SUCCESS] Data population completed successfully!'
            ))
            
            # Print summary
            self.print_summary()
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[ERROR] Error: {str(e)}'))
            raise

    def create_roles(self):
        """Create system roles"""
        role_names = ['admin', 'trainer', 'manager', 'trainee']
        for role_name in role_names:
            Role.objects.get_or_create(
                role_name=role_name,
                defaults={'description': f'{role_name.title()} Role'}
            )

    def create_users(self):
        """Create sample users"""
        # Admin user
        admin_user, created = User.objects.get_or_create(
            email='admin@lms.com',
            defaults={
                'first_name': 'Admin',
                'last_name': 'User',
                'password_hash': 'hashed_password_123',
                'primary_role': 'admin',
                'status': 'active'
            }
        )

        # Trainer user
        trainer_user, created = User.objects.get_or_create(
            email='trainer@lms.com',
            defaults={
                'first_name': 'John',
                'last_name': 'Trainer',
                'password_hash': 'hashed_password_456',
                'primary_role': 'trainer',
                'status': 'active'
            }
        )

        # Create 5 trainee users
        trainee_users = []
        for i in range(1, 6):
            trainee, created = User.objects.get_or_create(
                email=f'trainee{i}@lms.com',
                defaults={
                    'first_name': f'Trainee',
                    'last_name': f'User{i}',
                    'password_hash': f'hashed_password_{i}00',
                    'primary_role': 'trainee',
                    'status': 'active'
                }
            )
            trainee_users.append(trainee)

        self.stdout.write(f'  Created {len(trainee_users) + 2} users')
        return admin_user, trainer_user, trainee_users

    def create_teams(self, trainer_user, trainee_users):
        """Create sample teams"""
        teams = []
        team_names = ['Team Alpha', 'Team Beta', 'Team Gamma']
        
        for team_name in team_names:
            team, created = Team.objects.get_or_create(
                team_name=team_name,
                defaults={
                    'description': f'{team_name} - Sample team',
                    'status': 'active',
                    'manager': trainer_user,
                    'created_by': trainer_user
                }
            )
            
            # Add members to team
            for trainee in trainee_users[:len(trainee_users)//len(team_names) + 1]:
                TeamMember.objects.get_or_create(
                    team=team,
                    user=trainee,
                    defaults={
                        'is_primary_team': True,
                        'assigned_by': trainer_user
                    }
                )
            
            teams.append(team)
        
        self.stdout.write(f'  Created {len(teams)} teams')
        return teams

    def create_courses(self, trainer_user):
        """Create sample courses"""
        courses = []
        course_data = [
            {
                'title': 'Python Programming Fundamentals',
                'description': 'Learn Python basics including variables, loops, and functions',
                'course_type': 'self_paced',
                'status': 'published'
            },
            {
                'title': 'Web Development with Django',
                'description': 'Master Django framework for web development',
                'course_type': 'instructor_led',
                'status': 'published'
            },
            {
                'title': 'Database Design & SQL',
                'description': 'Learn database concepts and SQL queries',
                'course_type': 'blended',
                'status': 'published'
            }
        ]
        
        for data in course_data:
            course, created = Course.objects.get_or_create(
                title=data['title'],
                defaults={
                    'description': data['description'],
                    'about': f'About {data["title"]}',
                    'outcomes': 'Learn and master the subject',
                    'course_type': data['course_type'],
                    'status': data['status'],
                    'is_mandatory': True,
                    'estimated_duration_hours': 40,
                    'passing_criteria': 70,
                    'created_by': trainer_user
                }
            )
            courses.append(course)
        
        self.stdout.write(f'  Created {len(courses)} courses')
        return courses

    def create_modules(self, courses, trainer_user):
        """Create sample modules for courses"""
        modules_by_course = {}
        # Only use types that exist in database constraint: video, pdf, ppt, document, quiz, mixed, text, audio, presentation, page, assignment, survey
        module_types = ['video', 'text', 'audio', 'presentation', 'quiz']
        
        for course in courses:
            modules = []
            module_count = 5  # 5 modules per course
            
            for i in range(1, module_count + 1):
                module, created = Module.objects.get_or_create(
                    course=course,
                    sequence_order=i,
                    defaults={
                        'title': f'{course.title} - Module {i}',
                        'description': f'Module {i} content for {course.title}',
                        'module_type': module_types[i % len(module_types)],
                        'is_mandatory': True,
                        'estimated_duration_minutes': 45,
                        'video_count': i % 3,
                        'has_quizzes': i % 2 == 0
                    }
                )
                modules.append(module)
            
            modules_by_course[course.title] = modules
        
        self.stdout.write(f'  Created modules for {len(courses)} courses')
        return modules_by_course

    def create_enrollments(self, courses, trainee_users, trainer_user):
        """Create course enrollments"""
        total_enrollments = 0
        
        for course in courses:
            for trainee in trainee_users:
                enrollment, created = Enrollment.objects.get_or_create(
                    course=course,
                    user=trainee,
                    defaults={
                        'status': 'in_progress',
                        'progress_percentage': 0,
                        'assigned_by': trainer_user,
                        'started_at': timezone.now()
                    }
                )
                
                # Create user progress
                UserProgress.objects.get_or_create(
                    user=trainee,
                    course=course,
                    defaults={
                        'status': 'in_progress',
                        'completion_percentage': 0,
                        'total_points_earned': 0,
                        'started_at': timezone.now()
                    }
                )
                
                if created:
                    total_enrollments += 1
        
        self.stdout.write(f'  Created {total_enrollments} enrollments')

    def create_assessments(self, courses, modules_by_course, trainer_user):
        """Create quizzes, tests, and assignments"""
        
        for course in courses:
            modules = modules_by_course.get(course.title, [])
            
            for i, module in enumerate(modules):
                # Create quiz if applicable
                if module.has_quizzes:
                    quiz, created = Quiz.objects.get_or_create(
                        unit=module,
                        defaults={
                            'time_limit': 30,
                            'passing_score': 70,
                            'attempts_allowed': 3,
                            'show_answers': True,
                            'randomize_questions': False,
                            'mandatory_completion': True
                        }
                    )
                    
                    # Create 3 questions per quiz
                    for q in range(1, 4):
                        Question.objects.get_or_create(
                            quiz=quiz,
                            order=q,
                            defaults={
                                'type': 'mcq',
                                'text': f'Question {q}: What is the correct answer?',
                                'options': ['Option A', 'Option B', 'Option C', 'Option D'],
                                'correct_answer': 'Option A',
                                'points': 1
                            }
                        )
                
                # Create assignment
                if i % 2 == 0:  # Every other module
                    Assignment.objects.get_or_create(
                        module=module,
                        defaults={
                            'title': f'Assignment for {module.title}',
                            'description': 'Complete this assignment to demonstrate your understanding',
                            'assignment_type': 'task',
                            'due_date': timezone.now() + timedelta(days=7),
                            'max_attempts': 3,
                            'points_possible': 100,
                            'is_mandatory': True,
                            'created_by': trainer_user
                        }
                    )
        
        self.stdout.write('  Created quizzes and assignments')

    def link_media_files(self, modules_by_course, trainer_user):
        """Link media files from C:\LMS_uploads to modules"""
        media_handler = MediaHandler()
        media_stats = media_handler.get_media_stats()
        
        self.stdout.write(f'  [Media files found]')
        for file_type, stats in media_stats.items():
            if file_type != 'total' and stats.get('count', 0) > 0:
                self.stdout.write(f'    - {file_type}: {stats["count"]} files ({stats["total_size_mb"]} MB)')
        
        # Map media files to modules
        media_files = media_handler.scan_media_directory()
        module_list = [m for modules in modules_by_course.values() for m in modules]
        
        file_index = 0
        for file_type, files in media_files.items():
            for file_info in files:
                if file_index < len(module_list):
                    module = module_list[file_index]
                    try:
                        media_handler.link_media_to_module(file_info, module, trainer_user)
                        file_index += 1
                    except Exception as e:
                        self.stdout.write(f'  [WARNING] Could not link {file_info["name"]}: {str(e)}')

    def print_summary(self):
        """Print summary of created data"""
        self.stdout.write(self.style.SUCCESS('\n[DATA SUMMARY]'))
        self.stdout.write(f'  Users: {User.objects.count()}')
        self.stdout.write(f'  Courses: {Course.objects.count()}')
        self.stdout.write(f'  Modules: {Module.objects.count()}')
        self.stdout.write(f'  Enrollments: {Enrollment.objects.count()}')
        self.stdout.write(f'  Quizzes: {Quiz.objects.count()}')
        self.stdout.write(f'  Assignments: {Assignment.objects.count()}')
        self.stdout.write(f'  Media Files: {MediaMetadata.objects.count()}')
        self.stdout.write('\n[READY TO TEST]')
