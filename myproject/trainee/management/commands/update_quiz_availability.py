"""
Django management command to update quiz availability in all modules.
This script:
1. Sets max_attempts to 5 for all existing quizzes
2. Updates has_quizzes flag for all modules
3. Ensures all modules properly reference their quizzes
"""
from django.core.management.base import BaseCommand
from django.db.models import Count
from trainee.models import Module, ModuleQuiz, Test


class Command(BaseCommand):
    help = 'Update quiz availability and max_attempts for all modules and quizzes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making any database changes',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('Starting Quiz Availability Update'))
        self.stdout.write(self.style.SUCCESS('=' * 80))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be saved'))
        
        # Task 1: Update max_attempts to 5 for all ModuleQuiz
        self.stdout.write('\n' + self.style.SUCCESS('TASK 1: Updating ModuleQuiz max_attempts to 5'))
        module_quizzes = ModuleQuiz.objects.filter(max_attempts__lt=5)
        quiz_update_count = module_quizzes.count()
        
        if quiz_update_count > 0:
            self.stdout.write(f'  Found {quiz_update_count} ModuleQuizzes with max_attempts < 5')
            
            if not dry_run:
                module_quizzes.update(max_attempts=5)
                self.stdout.write(self.style.SUCCESS(f'  ✓ Updated {quiz_update_count} ModuleQuizzes'))
            else:
                self.stdout.write(f'  [DRY RUN] Would update {quiz_update_count} ModuleQuizzes')
        else:
            self.stdout.write(self.style.WARNING('  No ModuleQuizzes found with max_attempts < 5'))
        
        # Task 2: Update max_attempts to 5 for all Test (old model)
        self.stdout.write('\n' + self.style.SUCCESS('TASK 2: Updating Test max_attempts to 5'))
        tests = Test.objects.filter(max_attempts__lt=5)
        test_update_count = tests.count()
        
        if test_update_count > 0:
            self.stdout.write(f'  Found {test_update_count} Tests with max_attempts < 5')
            
            if not dry_run:
                tests.update(max_attempts=5)
                self.stdout.write(self.style.SUCCESS(f'  ✓ Updated {test_update_count} Tests'))
            else:
                self.stdout.write(f'  [DRY RUN] Would update {test_update_count} Tests')
        else:
            self.stdout.write(self.style.WARNING('  No Tests found with max_attempts < 5'))
        
        # Task 3: Update has_quizzes flag for all modules
        self.stdout.write('\n' + self.style.SUCCESS('TASK 3: Updating Module has_quizzes flag'))
        all_modules = Module.objects.all()
        modules_with_quizzes = 0
        modules_updated = 0
        
        self.stdout.write(f'  Processing {all_modules.count()} modules...')
        
        for module in all_modules:
            # Check if module has any quizzes or tests
            quiz_count = module.quizzes.count()
            test_count = module.tests.count()
            has_content = quiz_count > 0 or test_count > 0
            
            if has_content:
                modules_with_quizzes += 1
                
                # Update if flag is not correct
                if not module.has_quizzes:
                    if not dry_run:
                        module.has_quizzes = True
                        module.save(update_fields=['has_quizzes'])
                        modules_updated += 1
                    else:
                        modules_updated += 1
        
        self.stdout.write(f'  Found {modules_with_quizzes} modules with quizzes/tests')
        
        if modules_updated > 0:
            if not dry_run:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Updated {modules_updated} modules'))
            else:
                self.stdout.write(f'  [DRY RUN] Would update {modules_updated} modules')
        else:
            self.stdout.write(self.style.WARNING('  All modules already have correct has_quizzes flag'))
        
        # Task 4: Summary statistics
        self.stdout.write('\n' + self.style.SUCCESS('TASK 4: Summary Statistics'))
        
        total_modules = Module.objects.count()
        modules_with_quizzes_count = Module.objects.filter(has_quizzes=True).count()
        total_module_quizzes = ModuleQuiz.objects.count()
        total_tests = Test.objects.count()
        
        self.stdout.write(f'  Total Modules: {total_modules}')
        self.stdout.write(f'  Modules with Quizzes: {modules_with_quizzes_count}')
        self.stdout.write(f'  Total ModuleQuizzes: {total_module_quizzes}')
        self.stdout.write(f'  Total Tests: {total_tests}')
        
        # Show modules without quizzes
        modules_without_quizzes = Module.objects.filter(has_quizzes=False)
        if modules_without_quizzes.exists():
            self.stdout.write(self.style.WARNING(f'\n  ⚠ {modules_without_quizzes.count()} modules without quizzes:'))
            for module in modules_without_quizzes[:10]:  # Show first 10
                self.stdout.write(f'    - {module.course.title} > {module.title}')
            
            if modules_without_quizzes.count() > 10:
                self.stdout.write(f'    ... and {modules_without_quizzes.count() - 10} more')
        
        # Show quiz details by course
        self.stdout.write(self.style.SUCCESS('\n  Quiz Distribution by Course:'))
        from trainee.models import Course
        courses = Course.objects.annotate(
            quiz_count=Count('modules__quizzes', distinct=True),
            test_count=Count('modules__tests', distinct=True),
            module_count=Count('modules', distinct=True)
        ).filter(module_count__gt=0)
        
        for course in courses[:20]:  # Show first 20 courses
            quiz_count = course.modules.aggregate(quiz_count=Count('quizzes'))['quiz_count'] or 0
            test_count = course.modules.aggregate(test_count=Count('tests'))['test_count'] or 0
            self.stdout.write(f'    {course.title}: {quiz_count} quizzes, {test_count} tests')
        
        self.stdout.write('\n' + self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('Quiz Availability Update Complete!'))
        self.stdout.write(self.style.SUCCESS('=' * 80))
