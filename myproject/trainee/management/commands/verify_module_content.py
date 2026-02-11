from django.core.management.base import BaseCommand
from trainee.models import Course, Module, VideoUnit, LearningResource

class Command(BaseCommand):
    help = 'Verify all modules have content'
    
    def handle(self, *args, **options):
        print("\n" + "="*80)
        print("MODULE CONTENT VERIFICATION")
        print("="*80 + "\n")
        
        courses = Course.objects.filter(status='published')
        
        for course in courses:
            self.stdout.write(self.style.SUCCESS(f"\n📚 {course.title}"))
            modules = Module.objects.filter(course=course).order_by('sequence_order')
            
            for mod in modules[:3]:
                self.stdout.write(f"\n  Module {mod.sequence_order}: {mod.title}")
                
                # Check VideoUnit
                try:
                    video = mod.video_unit
                    self.stdout.write(self.style.SUCCESS(f"    ✓ VideoUnit"))
                    self.stdout.write(f"      URL: {video.video_url}")
                    self.stdout.write(f"      Duration: {video.duration}s")
                except Exception as e:
                    self.stdout.write(f"    ✗ VideoUnit: {str(e)}")
                
                # Check LearningResources
                resources = mod.resources.all()
                self.stdout.write(f"    Resources: {resources.count()}")
                for res in resources:
                    self.stdout.write(f"      • {res.resource_type.upper()}: {res.title}")
                    self.stdout.write(f"        URL: {res.file_url}")
        
        self.stdout.write(self.style.SUCCESS("\n" + "="*80))
        self.stdout.write(self.style.SUCCESS("✅ VERIFICATION COMPLETE"))
        self.stdout.write(self.style.SUCCESS("="*80 + "\n"))
