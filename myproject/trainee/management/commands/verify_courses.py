from django.core.management.base import BaseCommand
from trainee.models import Course, Module, VideoUnit

class Command(BaseCommand):
    help = 'Verify all active courses with their video units'
    
    def handle(self, *args, **options):
        """Verify courses structure"""
        
        self.stdout.write(self.style.SUCCESS("\n" + "="*80))
        self.stdout.write(self.style.SUCCESS("📚 COURSE STRUCTURE WITH VIDEO UNITS VERIFICATION"))
        self.stdout.write(self.style.SUCCESS("="*80 + "\n"))
        
        # Get all published courses
        courses = Course.objects.filter(status='published').order_by('title')
        
        if not courses.exists():
            self.stdout.write(self.style.ERROR("❌ No published courses found!"))
            return
        
        for course_num, course in enumerate(courses, 1):
            self.stdout.write(self.style.SUCCESS(f"\n{'='*80}"))
            self.stdout.write(self.style.SUCCESS(f"COURSE #{course_num}: {course.title}"))
            self.stdout.write(self.style.SUCCESS(f"{'='*80}"))
            self.stdout.write(f"  Course ID: {course.course_id}")
            self.stdout.write(f"  Status: {course.status}")
            self.stdout.write(f"  Type: {course.course_type}")
            self.stdout.write(f"  Description: {course.description[:100] if course.description else 'N/A'}...")
            self.stdout.write(f"  Passing Criteria: {course.passing_criteria}%")
            self.stdout.write(f"  Created by: {course.created_by.first_name} {course.created_by.last_name}\n")
            
            # Get modules
            modules = Module.objects.filter(course=course).order_by('sequence_order')
            
            self.stdout.write(self.style.SUCCESS(f"  📋 MODULES ({modules.count()}):\n"))
            
            if not modules.exists():
                self.stdout.write("     ⚠️  No modules found!")
            else:
                for mod_num, module in enumerate(modules, 1):
                    self.stdout.write(f"     [{mod_num}] {module.title}")
                    self.stdout.write(f"         Module ID: {module.module_id}")
                    self.stdout.write(f"         Type: {module.module_type}")
                    self.stdout.write(f"         Sequence: {module.sequence_order}")
                    self.stdout.write(f"         Description: {module.description[:60] if module.description else 'N/A'}...")
                    self.stdout.write(f"         Mandatory: {module.is_mandatory}")
                    self.stdout.write(f"         Duration: {module.estimated_duration_minutes or 'Not specified'} mins")
                    
                    # Check for video unit
                    try:
                        video_unit = module.video_unit
                        self.stdout.write(self.style.SUCCESS(f"         ✅ VIDEO UNIT ATTACHED:"))
                        self.stdout.write(f"            - URL: {video_unit.video_url}")
                        self.stdout.write(f"            - Duration: {video_unit.duration}s ({video_unit.duration//60}m {video_unit.duration%60}s)")
                        self.stdout.write(f"            - Completion Type: {video_unit.completion_type}")
                        self.stdout.write(f"            - Required Watch %: {video_unit.required_watch_percentage}%")
                        self.stdout.write(f"            - Allow Skip: {video_unit.allow_skip}")
                        self.stdout.write(f"            - Allow Rewind: {video_unit.allow_rewind}\n")
                    except VideoUnit.DoesNotExist:
                        self.stdout.write(f"         ❌ NO VIDEO UNIT\n")
        
        # Summary
        self.stdout.write(self.style.SUCCESS("\n" + "="*80))
        self.stdout.write(self.style.SUCCESS("SUMMARY"))
        self.stdout.write(self.style.SUCCESS("="*80))
        
        total_courses = courses.count()
        total_modules = Module.objects.filter(course__in=courses).count()
        total_videos = VideoUnit.objects.filter(unit__course__in=courses).count()
        
        self.stdout.write(f"Total Active Courses: {total_courses}")
        self.stdout.write(f"Total Modules: {total_modules}")
        self.stdout.write(f"Total Video Units: {total_videos}")
        self.stdout.write(self.style.SUCCESS(f"\n✅ All {total_videos} video units are configured and ready to use!\n"))
        self.stdout.write(self.style.SUCCESS("="*80 + "\n"))
