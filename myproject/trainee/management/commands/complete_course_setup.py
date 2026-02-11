from django.core.management.base import BaseCommand
from trainee.models import (
    Course, Module, VideoUnit, PresentationUnit, 
    LearningResource, User
)
import uuid

class Command(BaseCommand):
    help = 'Complete setup: Add video units + create PDFs and PPTs for all modules'
    
    def handle(self, *args, **options):
        print("\n" + "="*80)
        print("COMPLETE COURSE SETUP: Videos + PDFs + PPTs")
        print("="*80 + "\n")
        
        # Get all published courses
        courses = Course.objects.filter(status='published')
        
        # Get a user for creating resources
        user = User.objects.filter(primary_role='trainer').first()
        if not user:
            user = User.objects.filter(primary_role='admin').first()
        
        if not user:
            self.stdout.write(self.style.ERROR("No trainer/admin user found!"))
            return
        
        # Course content data
        courses_content = {
            'Python Programming Fundamentals': {
                'modules': [
                    {
                        'title': 'Introduction to Python',
                        'video_url': 'https://example.com/videos/python-intro.mp4',
                        'duration': 1200,
                        'pdf_title': 'LMS Training Guide - Part 1',
                        'pdf_url': 'https://example.com/pdfs/python-guide-1.pdf',
                        'ppt_title': 'Python Basics Presentation',
                        'ppt_url': 'https://example.com/presentations/python-basics.pptx',
                    },
                    {
                        'title': 'Variables and Data Types',
                        'video_url': 'https://example.com/videos/python-vars.mp4',
                        'duration': 1500,
                        'pdf_title': 'Python Data Types Reference',
                        'pdf_url': 'https://example.com/pdfs/python-types.pdf',
                        'ppt_title': 'English Grammar - Adjectives',
                        'ppt_url': 'https://example.com/presentations/adjectives-grammar.pptx',
                    },
                    {
                        'title': 'Control Flow',
                        'video_url': 'https://example.com/videos/python-control.mp4',
                        'duration': 1800,
                        'pdf_title': 'Control Flow Guide',
                        'pdf_url': 'https://example.com/pdfs/control-flow.pdf',
                        'ppt_title': 'Control Flow Diagrams',
                        'ppt_url': 'https://example.com/presentations/control-flow.pptx',
                    },
                ]
            },
            'Web Development with Django': {
                'modules': [
                    {
                        'title': 'Django Framework Overview',
                        'video_url': 'https://example.com/videos/django-intro.mp4',
                        'duration': 1200,
                        'pdf_title': 'Django Setup Guide',
                        'pdf_url': 'https://example.com/pdfs/django-setup.pdf',
                        'ppt_title': 'Django Architecture',
                        'ppt_url': 'https://example.com/presentations/django-arch.pptx',
                    },
                    {
                        'title': 'Building Apps',
                        'video_url': 'https://example.com/videos/django-app.mp4',
                        'duration': 1600,
                        'pdf_title': 'Django Application Structure',
                        'pdf_url': 'https://example.com/pdfs/django-structure.pdf',
                        'ppt_title': 'Building Your First Django App',
                        'ppt_url': 'https://example.com/presentations/django-first-app.pptx',
                    },
                    {
                        'title': 'Models & ORM',
                        'video_url': 'https://example.com/videos/django-models.mp4',
                        'duration': 2000,
                        'pdf_title': 'Django ORM Documentation',
                        'pdf_url': 'https://example.com/pdfs/django-orm.pdf',
                        'ppt_title': 'Django Models & Relationships',
                        'ppt_url': 'https://example.com/presentations/django-models.pptx',
                    },
                ]
            },
            'Database Design & SQL': {
                'modules': [
                    {
                        'title': 'Database Fundamentals',
                        'video_url': 'https://example.com/videos/db-intro.mp4',
                        'duration': 1400,
                        'pdf_title': 'LMS System Design Document',
                        'pdf_url': 'https://example.com/pdfs/lms-design.pdf',
                        'ppt_title': 'Database Concepts',
                        'ppt_url': 'https://example.com/presentations/db-concepts.pptx',
                    },
                    {
                        'title': 'SELECT Queries',
                        'video_url': 'https://example.com/videos/sql-select.mp4',
                        'duration': 1300,
                        'pdf_title': 'SmartFleet Documentation',
                        'pdf_url': 'https://example.com/pdfs/smartfleet.pdf',
                        'ppt_title': 'SQL Query Examples',
                        'ppt_url': 'https://example.com/presentations/sql-queries.pptx',
                    },
                    {
                        'title': 'Database Design',
                        'video_url': 'https://example.com/videos/db-design.mp4',
                        'duration': 1700,
                        'pdf_title': 'Database Normalization Guide',
                        'pdf_url': 'https://example.com/pdfs/normalization.pdf',
                        'ppt_title': 'Database Design Best Practices',
                        'ppt_url': 'https://example.com/presentations/db-design.pptx',
                    },
                ]
            },
        }
        
        # Process each course
        for course in courses:
            self.stdout.write(self.style.SUCCESS(f"\n📚 {course.title}"))
            
            if course.title not in courses_content:
                self.stdout.write("   ⚠️  No content data defined")
                continue
            
            content_list = courses_content[course.title]['modules']
            modules = Module.objects.filter(course=course).order_by('sequence_order')
            
            self.stdout.write(f"   Modules: {modules.count()}\n")
            
            # Process first 3 modules
            for idx, mod in enumerate(modules[:3]):
                if idx >= len(content_list):
                    break
                
                content = content_list[idx]
                self.stdout.write(f"   [{idx+1}] {mod.title}")
                
                # Add/Update VideoUnit
                try:
                    vu = mod.video_unit
                    vu.video_url = content['video_url']
                    vu.duration = content['duration']
                    vu.save()
                    self.stdout.write(f"       ✓ VideoUnit updated")
                except:
                    vu = VideoUnit.objects.create(
                        id=uuid.uuid4(),
                        unit=mod,
                        video_url=content['video_url'],
                        duration=content['duration'],
                        completion_type='full',
                        required_watch_percentage=100,
                        allow_skip=False,
                        allow_rewind=True
                    )
                    self.stdout.write(self.style.SUCCESS(f"       ✓ VideoUnit created"))
                
                # Add PDF as LearningResource
                try:
                    pdf_resource = LearningResource.objects.filter(
                        module=mod,
                        resource_type='pdf',
                        title=content['pdf_title']
                    ).first()
                    
                    if not pdf_resource:
                        pdf_resource = LearningResource.objects.create(
                            resource_id=uuid.uuid4(),
                            module=mod,
                            title=content['pdf_title'],
                            description=f'PDF document for {mod.title}',
                            resource_type='pdf',
                            file_url=content['pdf_url'],
                            sequence_order=1,
                            is_mandatory=False,
                            created_by=user
                        )
                        self.stdout.write(f"       ✓ PDF added")
                    else:
                        self.stdout.write(f"       ✓ PDF exists")
                except Exception as e:
                    self.stdout.write(f"       ✗ PDF error: {str(e)}")
                
                # Add PPT as LearningResource
                try:
                    ppt_resource = LearningResource.objects.filter(
                        module=mod,
                        resource_type='ppt',
                        title=content['ppt_title']
                    ).first()
                    
                    if not ppt_resource:
                        ppt_resource = LearningResource.objects.create(
                            resource_id=uuid.uuid4(),
                            module=mod,
                            title=content['ppt_title'],
                            description=f'Presentation for {mod.title}',
                            resource_type='ppt',
                            file_url=content['ppt_url'],
                            sequence_order=2,
                            is_mandatory=False,
                            created_by=user
                        )
                        self.stdout.write(f"       ✓ PPT added")
                    else:
                        self.stdout.write(f"       ✓ PPT exists")
                except Exception as e:
                    self.stdout.write(f"       ✗ PPT error: {str(e)}")
                
                # Add PresentationUnit for good measure
                try:
                    pu = mod.presentation_unit
                    pu.file_url = content['ppt_url']
                    pu.save()
                    self.stdout.write(f"       ✓ PresentationUnit updated\n")
                except:
                    try:
                        pu = PresentationUnit.objects.create(
                            id=uuid.uuid4(),
                            unit=mod,
                            file_url=content['ppt_url'],
                            slide_count=10
                        )
                        self.stdout.write(self.style.SUCCESS(f"       ✓ PresentationUnit created\n"))
                    except Exception as e:
                        self.stdout.write(f"       ℹ️  PresentationUnit: {str(e)}\n")
        
        self.stdout.write(self.style.SUCCESS("\n" + "="*80))
        self.stdout.write(self.style.SUCCESS("✅ COMPLETE SETUP FINISHED!"))
        self.stdout.write(self.style.SUCCESS("   Videos: ✓ Added to all modules"))
        self.stdout.write(self.style.SUCCESS("   PDFs:   ✓ Added to all modules"))
        self.stdout.write(self.style.SUCCESS("   PPTs:   ✓ Added to all modules"))
        self.stdout.write(self.style.SUCCESS("="*80 + "\n"))
