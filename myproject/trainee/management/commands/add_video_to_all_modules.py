"""
Management command to add video units to ALL modules in all courses
"""
from django.core.management.base import BaseCommand
from trainee.models import Course, Module, VideoUnit
import uuid


class Command(BaseCommand):
    help = 'Add video units to all modules in all courses'

    def handle(self, *args, **options):
        courses = Course.objects.filter(status='published').all()
        
        video_config = {
            'Python Programming Fundamentals': [
                {'title': 'Introduction to Python', 'duration': 1200, 'url': 'https://example.com/videos/python-intro.mp4'},
                {'title': 'Variables and Data Types', 'duration': 1500, 'url': 'https://example.com/videos/python-vars.mp4'},
                {'title': 'Control Flow', 'duration': 1800, 'url': 'https://example.com/videos/python-control.mp4'},
                {'title': 'Functions and Modules', 'duration': 2000, 'url': 'https://example.com/videos/python-functions.mp4'},
                {'title': 'Object-Oriented Programming', 'duration': 2200, 'url': 'https://example.com/videos/python-oop.mp4'},
                {'title': 'Assessment Quiz', 'duration': 600, 'url': 'https://example.com/videos/python-summary.mp4'},
            ],
            'Web Development with Django': [
                {'title': 'Django Overview', 'duration': 1200, 'url': 'https://example.com/videos/django-intro.mp4'},
                {'title': 'Building Apps', 'duration': 1600, 'url': 'https://example.com/videos/django-app.mp4'},
                {'title': 'Models & ORM', 'duration': 2000, 'url': 'https://example.com/videos/django-models.mp4'},
                {'title': 'Views & URLs', 'duration': 1800, 'url': 'https://example.com/videos/django-views.mp4'},
                {'title': 'Templates & Static Files', 'duration': 1900, 'url': 'https://example.com/videos/django-templates.mp4'},
            ],
            'Database Design & SQL': [
                {'title': 'Database Fundamentals', 'duration': 1400, 'url': 'https://example.com/videos/db-intro.mp4'},
                {'title': 'SELECT Queries', 'duration': 1300, 'url': 'https://example.com/videos/sql-select.mp4'},
                {'title': 'Database Design', 'duration': 1700, 'url': 'https://example.com/videos/db-design.mp4'},
                {'title': 'Indexing & Optimization', 'duration': 1600, 'url': 'https://example.com/videos/db-index.mp4'},
                {'title': 'Advanced SQL', 'duration': 2000, 'url': 'https://example.com/videos/sql-advanced.mp4'},
            ],
        }
        
        total_added = 0
        total_skipped = 0
        
        for course in courses:
            course_title = course.title
            self.stdout.write(f"\n📚 Processing Course: {course_title}")
            
            if course_title not in video_config:
                self.stdout.write(f"  ⚠️  No video config for this course, skipping...")
                continue
            
            modules = course.modules.all().order_by('sequence_order')
            videos_config = video_config[course_title]
            
            for idx, module in enumerate(modules):
                # Get or create video config for this module
                if idx < len(videos_config):
                    video_info = videos_config[idx]
                else:
                    # Use default if not enough configs
                    video_info = {
                        'title': f'{course_title} - Video {idx + 1}',
                        'duration': 1200,
                        'url': f'https://example.com/videos/{course_title.lower().replace(" ", "-")}-module-{idx + 1}.mp4'
                    }
                
                # Check if video unit already exists
                try:
                    video = VideoUnit.objects.get(unit=module)
                    self.stdout.write(f"  ✓ Module {module.sequence_order}: Already has video unit")
                    total_skipped += 1
                except VideoUnit.DoesNotExist:
                    # Create new video unit
                    try:
                        video = VideoUnit.objects.create(
                            id=uuid.uuid4(),
                            unit=module,
                            video_url=video_info['url'],
                            duration=video_info['duration'],
                            completion_type='full',
                            required_watch_percentage=100,
                            allow_rewind=True,
                            allow_skip=False,
                        )
                        self.stdout.write(
                            f"  ✓ Module {module.sequence_order}: Created video unit"
                            f"\n    - Title: {video_info['title']}"
                            f"\n    - Duration: {video_info['duration']}s"
                            f"\n    - URL: {video_info['url']}"
                        )
                        total_added += 1
                    except Exception as e:
                        self.stdout.write(
                            f"  ✗ Module {module.sequence_order}: Error creating video - {str(e)}"
                        )
        
        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Complete!\n"
            f"   - Added: {total_added} video units\n"
            f"   - Already existed: {total_skipped} video units"
        ))
