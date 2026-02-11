from django.core.management.base import BaseCommand
from trainee.models import Course, Module, VideoUnit, User
import uuid

class Command(BaseCommand):
    help = 'Add video units to all active (published) courses'
    
    def handle(self, *args, **options):
        """Add video units to active courses"""
        
        self.stdout.write(self.style.SUCCESS("\n" + "="*70))
        self.stdout.write(self.style.SUCCESS("📹 ADDING VIDEO UNITS TO ACTIVE COURSES"))
        self.stdout.write(self.style.SUCCESS("="*70 + "\n"))
        
        # Get all published courses
        courses = Course.objects.filter(status='published')
        
        if not courses.exists():
            self.stdout.write(self.style.ERROR("❌ No published courses found!"))
            return
        
        self.stdout.write(self.style.SUCCESS(f"✅ Found {courses.count()} active courses\n"))
        
        # Get a trainer user for creating modules if needed
        trainer = User.objects.filter(primary_role='trainer').first()
        if not trainer:
            trainer = User.objects.filter(primary_role='admin').first()
        
        if not trainer:
            self.stdout.write(self.style.ERROR("❌ No trainer or admin user found!"))
            return
        
        self.stdout.write(f"Using creator: {trainer.first_name} {trainer.last_name}\n")
        
        # Sample video data for each course
        course_videos = {
            'Python Programming Fundamentals': [
                {
                    'title': 'Introduction to Python',
                    'description': 'Learn the basics of Python programming language',
                    'duration': 1200,
                    'video_url': 'https://example.com/videos/python-intro.mp4',
                },
                {
                    'title': 'Python Variables and Data Types',
                    'description': 'Understanding variables, data types, and basic operations',
                    'duration': 1500,
                    'video_url': 'https://example.com/videos/python-variables.mp4',
                },
                {
                    'title': 'Control Flow: If, Else, Loops',
                    'description': 'Conditional statements and loops in Python',
                    'duration': 1800,
                    'video_url': 'https://example.com/videos/python-control-flow.mp4',
                }
            ],
            'Web Development with Django': [
                {
                    'title': 'Django Framework Overview',
                    'description': 'Introduction to Django web framework',
                    'duration': 1200,
                    'video_url': 'https://example.com/videos/django-overview.mp4',
                },
                {
                    'title': 'Building Your First Django App',
                    'description': 'Create and configure your first Django application',
                    'duration': 1600,
                    'video_url': 'https://example.com/videos/django-first-app.mp4',
                },
                {
                    'title': 'Django Models and Databases',
                    'description': 'Working with Django ORM and database models',
                    'duration': 2000,
                    'video_url': 'https://example.com/videos/django-models.mp4',
                }
            ],
            'Database Design & SQL': [
                {
                    'title': 'Database Fundamentals',
                    'description': 'Introduction to relational databases and SQL basics',
                    'duration': 1400,
                    'video_url': 'https://example.com/videos/db-fundamentals.mp4',
                },
                {
                    'title': 'SQL SELECT and WHERE',
                    'description': 'Querying data with SELECT and filtering with WHERE',
                    'duration': 1300,
                    'video_url': 'https://example.com/videos/sql-select.mp4',
                },
                {
                    'title': 'Database Design Best Practices',
                    'description': 'Normalization and database design patterns',
                    'duration': 1700,
                    'video_url': 'https://example.com/videos/db-design.mp4',
                }
            ]
        }
        
        total_videos_added = 0
        
        # Process each course
        for course in courses:
            self.stdout.write(self.style.SUCCESS(f"\n📚 Course: {course.title}"))
            self.stdout.write(f"   Status: {course.status}")
            self.stdout.write(f"   ID: {course.course_id}\n")
            
            # Get videos for this course
            videos_for_course = course_videos.get(course.title, [])
            
            if not videos_for_course:
                self.stdout.write(f"   ⚠️  No video data defined for this course")
                continue
            
            # Get existing modules
            existing_modules = Module.objects.filter(course=course).order_by('sequence_order')
            self.stdout.write(f"   Existing modules: {existing_modules.count()}")
            
            # For each video, either add to existing module or create new one
            for idx, video_data in enumerate(videos_for_course, 1):
                try:
                    # Try to get existing module, or create new one
                    if idx <= existing_modules.count():
                        module = existing_modules[idx - 1]
                        if module.module_type != 'video':
                            module.module_type = 'video'
                            module.save()
                        self.stdout.write(f"   Using existing module: {module.title}")
                    else:
                        # Create new module
                        module = Module.objects.create(
                            module_id=uuid.uuid4(),
                            course=course,
                            title=video_data['title'],
                            description=video_data['description'],
                            module_type='video',
                            sequence_order=idx,
                            is_mandatory=True,
                            estimated_duration_minutes=video_data['duration'] // 60,
                        )
                        self.stdout.write(self.style.SUCCESS(f"   ✨ Created new module: {module.title}"))
                    
                    # Check if VideoUnit already exists for this module
                    if hasattr(module, 'video_unit'):
                        video_unit = module.video_unit
                        video_unit.video_url = video_data['video_url']
                        video_unit.duration = video_data['duration']
                        video_unit.save()
                        self.stdout.write(f"      ✏️  Updated VideoUnit (Duration: {video_unit.duration}s)")
                    else:
                        # Create VideoUnit
                        video_unit = VideoUnit.objects.create(
                            id=uuid.uuid4(),
                            unit=module,
                            video_url=video_data['video_url'],
                            duration=video_data['duration'],
                            completion_type='full',
                            required_watch_percentage=100,
                            allow_skip=False,
                            allow_rewind=True
                        )
                        self.stdout.write(self.style.SUCCESS(f"      ✅ Added VideoUnit"))
                        self.stdout.write(f"         - URL: {video_unit.video_url}")
                        self.stdout.write(f"         - Duration: {video_unit.duration}s ({video_unit.duration//60} mins)")
                        total_videos_added += 1
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"      ❌ Error: {str(e)}"))
                    continue
            
            self.stdout.write(f"   ✓ Course processing complete\n")
        
        self.stdout.write(self.style.SUCCESS("\n" + "="*70))
        self.stdout.write(self.style.SUCCESS(f"✅ COMPLETE! Added/Updated {total_videos_added} video units"))
        self.stdout.write(self.style.SUCCESS("="*70 + "\n"))
