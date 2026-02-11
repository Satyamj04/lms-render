from django.core.management.base import BaseCommand
from trainee.models import Course, Module, VideoUnit, PresentationUnit
import uuid

class Command(BaseCommand):
    help = 'Add/fix video units for all course modules'
    
    def handle(self, *args, **options):
        print("\n" + "="*70)
        print("ADDING VIDEO UNITS TO ALL MODULES")
        print("="*70 + "\n")
        
        # Get all published courses
        courses = Course.objects.filter(status='published')
        
        for course in courses:
            self.stdout.write(self.style.SUCCESS(f"\n📚 {course.title}"))
            
            # Get modules
            modules = Module.objects.filter(course=course).order_by('sequence_order')
            self.stdout.write(f"   Modules: {modules.count()}")
            
            # Define video content for each course
            course_videos = {
                'Python Programming Fundamentals': [
                    {'title': 'Introduction to Python', 'duration': 1200, 'url': 'https://example.com/videos/python-intro.mp4'},
                    {'title': 'Variables and Data Types', 'duration': 1500, 'url': 'https://example.com/videos/python-vars.mp4'},
                    {'title': 'Control Flow', 'duration': 1800, 'url': 'https://example.com/videos/python-control.mp4'},
                ],
                'Web Development with Django': [
                    {'title': 'Django Overview', 'duration': 1200, 'url': 'https://example.com/videos/django-intro.mp4'},
                    {'title': 'Building Apps', 'duration': 1600, 'url': 'https://example.com/videos/django-app.mp4'},
                    {'title': 'Models & ORM', 'duration': 2000, 'url': 'https://example.com/videos/django-models.mp4'},
                ],
                'Database Design & SQL': [
                    {'title': 'Database Fundamentals', 'duration': 1400, 'url': 'https://example.com/videos/db-intro.mp4'},
                    {'title': 'SELECT Queries', 'duration': 1300, 'url': 'https://example.com/videos/sql-select.mp4'},
                    {'title': 'Database Design', 'duration': 1700, 'url': 'https://example.com/videos/db-design.mp4'},
                ],
            }
            
            videos = course_videos.get(course.title, [])
            
            if not videos:
                self.stdout.write(f"   ⚠️  No video data for this course")
                continue
            
            # Add video units to first 3 modules
            for idx, mod in enumerate(modules[:3]):
                if idx < len(videos):
                    video_info = videos[idx]
                    
                    try:
                        # Check if video unit already exists
                        vu = mod.video_unit
                        # Update it
                        vu.video_url = video_info['url']
                        vu.duration = video_info['duration']
                        vu.save()
                        self.stdout.write(f"   ✏️  Updated Module {mod.sequence_order}: {mod.title}")
                    except:
                        # Create new video unit
                        vu = VideoUnit.objects.create(
                            id=uuid.uuid4(),
                            unit=mod,
                            video_url=video_info['url'],
                            duration=video_info['duration'],
                            completion_type='full',
                            required_watch_percentage=100,
                            allow_skip=False,
                            allow_rewind=True
                        )
                        self.stdout.write(self.style.SUCCESS(f"   ✅ Created VideoUnit for Module {mod.sequence_order}: {mod.title}"))
                        self.stdout.write(f"      URL: {vu.video_url}")
                        self.stdout.write(f"      Duration: {vu.duration}s\n")
        
        self.stdout.write(self.style.SUCCESS("\n" + "="*70))
        self.stdout.write(self.style.SUCCESS("✅ VIDEO UNITS SETUP COMPLETE!"))
        self.stdout.write(self.style.SUCCESS("="*70 + "\n"))
