"""
Management command to migrate quiz data from ModuleQuiz* tables to Quiz/Question and QuizAttempt/TestAnswer tables.
This script should be run after all models are updated but before dropping old tables.

Usage: python manage.py migrate_quiz_to_test_tables
"""
import uuid
from django.core.management.base import BaseCommand
from django.db import transaction
from trainee.models import (
    Quiz, Question, QuizAttempt, TestAnswer, TestAttempt, TestQuestion,
    ModuleQuizQuestion, ModuleQuizAttempt, ModuleQuizAnswer, ModuleQuiz
)


class Command(BaseCommand):
    help = 'Migrate quiz data from ModuleQuiz* tables to Quiz/Question and QuizAttempt/TestAnswer tables'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run migration in dry-run mode without saving changes',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        
        self.stdout.write(self.style.WARNING(f'Starting quiz data migration (dry_run={dry_run})...'))
        
        try:
            # Step 1: Migrate ModuleQuiz -> Quiz
            self.stdout.write(self.style.SUCCESS('\n--- Step 1: Migrating ModuleQuiz to Quiz ---'))
            self._migrate_module_quizzes(dry_run)
            
            # Step 2: Migrate ModuleQuizQuestion -> Question
            self.stdout.write(self.style.SUCCESS('\n--- Step 2: Migrating ModuleQuizQuestion to Question ---'))
            self._migrate_module_quiz_questions(dry_run)
            
            # Step 3: Migrate ModuleQuizAttempt -> QuizAttempt
            self.stdout.write(self.style.SUCCESS('\n--- Step 3: Migrating ModuleQuizAttempt to QuizAttempt ---'))
            self._migrate_module_quiz_attempts(dry_run)
            
            # Step 4: Migrate ModuleQuizAnswer -> TestAnswer
            self.stdout.write(self.style.SUCCESS('\n--- Step 4: Migrating ModuleQuizAnswer to TestAnswer ---'))
            self._migrate_module_quiz_answers(dry_run)
            
            if dry_run:
                self.stdout.write(self.style.WARNING('\nDRY RUN - No changes were saved to the database.'))
            else:
                self.stdout.write(self.style.SUCCESS('\nMigration completed successfully!'))
                self.stdout.write(self.style.WARNING('\nNOTE: Old tables (module_quizzes, module_quiz_questions, module_quiz_attempts, module_quiz_answers) can now be safely dropped after verifying data.'))
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\nMigration failed with error: {str(e)}'))
            raise

    def _migrate_module_quizzes(self, dry_run):
        """Migrate ModuleQuiz to Quiz"""
        try:
            module_quizzes = ModuleQuiz.objects.all()
            count = 0
            
            for mq in module_quizzes:
                # Check if Quiz already exists for this module
                quiz, created = Quiz.objects.get_or_create(
                    unit_id=mq.module_id,
                    defaults={
                        'time_limit': mq.time_limit_minutes,
                        'passing_score': mq.passing_score,
                        'attempts_allowed': mq.max_attempts,
                        'show_answers': mq.show_correct_answers,
                        'randomize_questions': mq.randomize_questions,
                        'mandatory_completion': mq.is_mandatory,
                    }
                )
                if created:
                    count += 1
            
            if dry_run:
                self.stdout.write(f'[DRY RUN] Would migrate {count} ModuleQuiz records to Quiz')
            else:
                self.stdout.write(self.style.SUCCESS(f'✓ Migrated {count} ModuleQuiz records to Quiz'))
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error migrating ModuleQuiz: {str(e)}'))
            raise

    def _migrate_module_quiz_questions(self, dry_run):
        """Migrate ModuleQuizQuestion to Question"""
        try:
            module_questions = ModuleQuizQuestion.objects.all()
            count = 0
            
            for mq in module_questions:
                # Find corresponding Quiz
                quiz = Quiz.objects.filter(unit_id=mq.quiz.module_id).first()
                
                if quiz:
                    question, created = Question.objects.get_or_create(
                        quiz_id=quiz.id,
                        order=mq.sequence_order,
                        defaults={
                            'type': mq.question_type,
                            'text': mq.question_text,
                            'options': mq.options,
                            'correct_answer': mq.correct_answer,
                            'points': mq.points,
                        }
                    )
                    if created:
                        count += 1
            
            if dry_run:
                self.stdout.write(f'[DRY RUN] Would migrate {count} ModuleQuizQuestion records to Question')
            else:
                self.stdout.write(self.style.SUCCESS(f'✓ Migrated {count} ModuleQuizQuestion records to Question'))
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error migrating ModuleQuizQuestion: {str(e)}'))
            raise

    def _migrate_module_quiz_attempts(self, dry_run):
        """Migrate ModuleQuizAttempt to QuizAttempt"""
        try:
            module_attempts = ModuleQuizAttempt.objects.all()
            count = 0
            
            for ma in module_attempts:
                # Find corresponding Quiz
                quiz = Quiz.objects.filter(unit_id=ma.quiz.module_id).first()
                
                if quiz:
                    attempt, created = QuizAttempt.objects.get_or_create(
                        id=ma.attempt_id,
                        defaults={
                            'quiz_id': quiz.id,
                            'user_id': ma.user_id,
                            'score': int(ma.score) if ma.score else 0,
                            'passed': ma.passed or False,
                            'answers': ma.answers,
                            'started_at': ma.started_at,
                            'completed_at': ma.completed_at,
                            'created_at': ma.created_at,
                            'updated_at': ma.updated_at,
                        }
                    )
                    if created:
                        count += 1
            
            if dry_run:
                self.stdout.write(f'[DRY RUN] Would migrate {count} ModuleQuizAttempt records to QuizAttempt')
            else:
                self.stdout.write(self.style.SUCCESS(f'✓ Migrated {count} ModuleQuizAttempt records to QuizAttempt'))
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error migrating ModuleQuizAttempt: {str(e)}'))
            raise

    def _migrate_module_quiz_answers(self, dry_run):
        """Migrate ModuleQuizAnswer to TestAnswer"""
        try:
            module_answers = ModuleQuizAnswer.objects.all()
            count = 0
            skipped = 0
            
            for ma in module_answers:
                try:
                    # Find corresponding QuizAttempt (migrated)
                    quiz_attempt = QuizAttempt.objects.filter(id=ma.attempt_id).first()
                    
                    # Find corresponding TestAttempt if it exists, or create one
                    if quiz_attempt:
                        # Find or create TestAttempt for this QuizAttempt
                        test_attempt, _ = TestAttempt.objects.get_or_create(
                            id=ma.attempt_id,  # Reuse same ID for traceability
                            defaults={
                                'test_id': quiz_attempt.quiz_id,
                                'user_id': quiz_attempt.user_id,
                                'attempt_number': 1,
                                'status': 'completed' if quiz_attempt.completed_at else 'in_progress',
                                'score': quiz_attempt.score,
                                'passed': quiz_attempt.passed or False,
                                'started_at': quiz_attempt.started_at,
                                'submitted_at': quiz_attempt.completed_at,
                            }
                        )
                        
                        # Find corresponding TestQuestion
                        test_question = TestQuestion.objects.filter(
                            test_id=test_attempt.test_id,
                            text=ma.question.question_text
                        ).first()
                        
                        if test_question:
                            answer, created = TestAnswer.objects.get_or_create(
                                answer_id=ma.answer_id,
                                defaults={
                                    'attempt_id': test_attempt.id,
                                    'question_id': test_question.id,
                                    'answer_text': ma.answer_text,
                                    'is_correct': ma.is_correct,
                                    'points_earned': ma.points_earned,
                                    'confidence_score': ma.confidence_score,
                                    'created_at': ma.created_at,
                                    'updated_at': ma.updated_at,
                                }
                            )
                            if created:
                                count += 1
                        else:
                            skipped += 1
                    else:
                        skipped += 1
                
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'Skipped answer {ma.answer_id}: {str(e)}'))
                    skipped += 1
            
            if dry_run:
                self.stdout.write(f'[DRY RUN] Would migrate {count} ModuleQuizAnswer records to TestAnswer (skipped: {skipped})')
            else:
                self.stdout.write(self.style.SUCCESS(f'✓ Migrated {count} ModuleQuizAnswer records to TestAnswer (skipped: {skipped})'))
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error migrating ModuleQuizAnswer: {str(e)}'))
            raise
