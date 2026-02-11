"""
Management command to create sample quizzes for all courses
Usage: python manage.py create_sample_quizzes
"""
from django.core.management.base import BaseCommand
from trainee.models import Course, Module, ModuleQuiz, ModuleQuizQuestion, User
from django.db.models import Count

QUIZ_DATA = {
    'Python Fundamentals': [
        {
            'title': 'Python Basics Quiz',
            'description': 'Test your understanding of Python fundamentals',
            'time_limit_minutes': 15,
            'passing_score': 70,
            'questions': [
                {
                    'text': 'What is the correct way to define a function in Python?',
                    'type': 'mcq',
                    'options': ['def function_name():', 'function function_name():', 'define function_name():', 'func function_name():'],
                    'correct_answer': 'def function_name():',
                    'points': 5,
                    'explanation': 'In Python, functions are defined using the "def" keyword followed by the function name and parentheses.'
                },
                {
                    'text': 'Which of the following is NOT a valid Python data type?',
                    'type': 'mcq',
                    'options': ['list', 'tuple', 'string', 'array'],
                    'correct_answer': 'array',
                    'points': 5,
                    'explanation': 'Python does not have a built-in "array" data type.'
                },
                {
                    'text': 'What does len() function return?',
                    'type': 'mcq',
                    'options': ['The memory address of an object', 'The length/size of an object', 'The data type of an object', 'The value of an object'],
                    'correct_answer': 'The length/size of an object',
                    'points': 5,
                    'explanation': 'The len() function returns the number of items in an object.'
                }
            ]
        },
        {
            'title': 'Variables and Data Types Quiz',
            'description': 'Test your knowledge of variables and data types',
            'time_limit_minutes': 12,
            'passing_score': 70,
            'questions': [
                {
                    'text': 'How do you assign a value to a variable in Python?',
                    'type': 'mcq',
                    'options': ['variable == value', 'variable = value', 'variable := value', 'var variable value'],
                    'correct_answer': 'variable = value',
                    'points': 5,
                    'explanation': 'The single equals sign (=) is used for assignment.'
                }
            ]
        },
        {
            'title': 'Control Flow Quiz',
            'description': 'Test your understanding of if-else and loops',
            'time_limit_minutes': 15,
            'passing_score': 70,
            'questions': [
                {
                    'text': 'What is the correct syntax for a for loop in Python?',
                    'type': 'mcq',
                    'options': ['for (i = 0; i < 10; i++)', 'for i in range(10):', 'for i = 1 to 10:', 'for i <- 10:'],
                    'correct_answer': 'for i in range(10):',
                    'points': 5,
                    'explanation': 'Python uses "for i in iterable:" syntax.'
                }
            ]
        }
    ],
    'Web Development with Django': [
        {
            'title': 'Django Basics Quiz',
            'description': 'Test your knowledge of Django fundamentals',
            'time_limit_minutes': 15,
            'passing_score': 70,
            'questions': [
                {
                    'text': 'What does Django stand for?',
                    'type': 'mcq',
                    'options': ['Database Ninja Generic', 'A web framework', 'All of the above', 'Data JavaScript Angular'],
                    'correct_answer': 'A web framework',
                    'points': 5,
                    'explanation': 'Django is a high-level Python web framework.'
                },
                {
                    'text': 'Which command creates a new Django project?',
                    'type': 'mcq',
                    'options': ['django new project_name', 'django-admin startproject project_name', 'django create project_name', 'python django.py project_name'],
                    'correct_answer': 'django-admin startproject project_name',
                    'points': 5,
                    'explanation': 'Use django-admin startproject to create new projects.'
                }
            ]
        },
        {
            'title': 'Django Models Quiz',
            'description': 'Test your understanding of Django ORM and models',
            'time_limit_minutes': 15,
            'passing_score': 70,
            'questions': [
                {
                    'text': 'What is a Django Model?',
                    'type': 'mcq',
                    'options': ['A template file', 'A Python class that represents a database table', 'A view function', 'A URL configuration'],
                    'correct_answer': 'A Python class that represents a database table',
                    'points': 5,
                    'explanation': 'Models inherit from django.db.models.Model and represent database tables.'
                }
            ]
        },
        {
            'title': 'Django Views and URLs Quiz',
            'description': 'Test your knowledge of views and routing',
            'time_limit_minutes': 15,
            'passing_score': 70,
            'questions': [
                {
                    'text': 'What does a Django view do?',
                    'type': 'mcq',
                    'options': ['Displays HTML templates', 'Receives a request and returns a response', 'Manages database connections', 'Stores user sessions'],
                    'correct_answer': 'Receives a request and returns a response',
                    'points': 5,
                    'explanation': 'A view receives a web request and returns a web response.'
                }
            ]
        }
    ],
    'JavaScript Essentials': [
        {
            'title': 'JavaScript Basics Quiz',
            'description': 'Test your understanding of JavaScript fundamentals',
            'time_limit_minutes': 15,
            'passing_score': 70,
            'questions': [
                {
                    'text': 'How do you declare a variable in modern JavaScript?',
                    'type': 'mcq',
                    'options': ['var x = 5;', 'let x = 5;', 'const x = 5;', 'All of the above'],
                    'correct_answer': 'All of the above',
                    'points': 5,
                    'explanation': 'All three methods can declare variables.'
                },
                {
                    'text': 'What is the difference between == and ===?',
                    'type': 'mcq',
                    'options': ['They are the same', '== compares values, === compares values and types', '=== compares values, == compares types', 'There is no === operator'],
                    'correct_answer': '== compares values, === compares values and types',
                    'points': 5,
                    'explanation': '=== checks both value and type, while == only checks value.'
                }
            ]
        },
        {
            'title': 'DOM Manipulation Quiz',
            'description': 'Test your knowledge of DOM manipulation',
            'time_limit_minutes': 15,
            'passing_score': 70,
            'questions': [
                {
                    'text': 'How do you select an element by ID in JavaScript?',
                    'type': 'mcq',
                    'options': ['document.getElementById("id")', 'document.querySelect("#id")', 'document.select("#id")', 'getElementById("id")'],
                    'correct_answer': 'document.getElementById("id")',
                    'points': 5,
                    'explanation': 'getElementById() selects an element with a specific ID.'
                }
            ]
        },
        {
            'title': 'Async Programming Quiz',
            'description': 'Test your understanding of promises and async/await',
            'time_limit_minutes': 15,
            'passing_score': 70,
            'questions': [
                {
                    'text': 'What is a Promise in JavaScript?',
                    'type': 'mcq',
                    'options': ['A function that executes immediately', 'An object representing eventual completion of async operation', 'A way to declare variables', 'A loop structure'],
                    'correct_answer': 'An object representing eventual completion of async operation',
                    'points': 5,
                    'explanation': 'A Promise represents eventual completion of async operations.'
                }
            ]
        }
    ],
    'Database Design with PostgreSQL': [
        {
            'title': 'SQL Basics Quiz',
            'description': 'Test your knowledge of SQL fundamentals',
            'time_limit_minutes': 15,
            'passing_score': 70,
            'questions': [
                {
                    'text': 'What does SQL stand for?',
                    'type': 'mcq',
                    'options': ['Structured Query Language', 'Standard Question Language', 'Sequential Query List', 'Secure Query Location'],
                    'correct_answer': 'Structured Query Language',
                    'points': 5,
                    'explanation': 'SQL is Structured Query Language.'
                },
                {
                    'text': 'Which keyword is used to select data from a database?',
                    'type': 'mcq',
                    'options': ['GET', 'FETCH', 'SELECT', 'RETRIEVE'],
                    'correct_answer': 'SELECT',
                    'points': 5,
                    'explanation': 'SELECT is used to select data from a database.'
                }
            ]
        },
        {
            'title': 'PostgreSQL Specific Quiz',
            'description': 'Test your knowledge of PostgreSQL features',
            'time_limit_minutes': 15,
            'passing_score': 70,
            'questions': [
                {
                    'text': 'What is the default port for PostgreSQL?',
                    'type': 'mcq',
                    'options': ['3306', '5432', '1433', '27017'],
                    'correct_answer': '5432',
                    'points': 5,
                    'explanation': 'PostgreSQL uses port 5432 by default.'
                }
            ]
        },
        {
            'title': 'Database Design Quiz',
            'description': 'Test your understanding of database normalization',
            'time_limit_minutes': 15,
            'passing_score': 70,
            'questions': [
                {
                    'text': 'What is database normalization?',
                    'type': 'mcq',
                    'options': ['Process of organizing data to reduce redundancy', 'Backing up the database', 'Compressing database files', 'Encrypting sensitive data'],
                    'correct_answer': 'Process of organizing data to reduce redundancy',
                    'points': 5,
                    'explanation': 'Normalization reduces redundancy and improves data integrity.'
                }
            ]
        }
    ]
}

class Command(BaseCommand):
    help = 'Create sample quizzes for all courses'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write(self.style.SUCCESS('CREATING SAMPLE QUIZZES FOR COURSES'))
        self.stdout.write(self.style.SUCCESS('='*80))
        
        # Get trainer user
        trainer = User.objects.filter(primary_role='trainer').first()
        if not trainer:
            self.stdout.write(self.style.ERROR('❌ No trainer user found!'))
            return
        
        self.stdout.write(f"\n✓ Using trainer: {trainer.email} (ID: {trainer.user_id})")
        
        quizzes_created = 0
        questions_created = 0
        
        for course_title, quiz_list in QUIZ_DATA.items():
            self.stdout.write(f"\n[Processing Course] {course_title}")
            
            course = Course.objects.filter(title=course_title).first()
            if not course:
                self.stdout.write(f"  ⚠ Course not found: {course_title}")
                continue
            
            modules = course.modules.all().order_by('sequence_order')
            
            if not modules.exists():
                self.stdout.write(f"  ⚠ Creating modules for {course_title}...")
                for i, quiz_data in enumerate(quiz_list, 1):
                    module, created = Module.objects.get_or_create(
                        course=course,
                        sequence_order=i,
                        defaults={
                            'title': f'{course_title} Module {i}',
                            'description': f'Module {i}',
                            'module_type': 'mixed',
                            'is_mandatory': True,
                            'has_quizzes': True
                        }
                    )
                modules = course.modules.all().order_by('sequence_order')
            
            for module, quiz_data in zip(modules, quiz_list):
                quiz, created = ModuleQuiz.objects.get_or_create(
                    module=module,
                    title=quiz_data['title'],
                    defaults={
                        'description': quiz_data['description'],
                        'sequence_order': 1,
                        'time_limit_minutes': quiz_data.get('time_limit_minutes', 15),
                        'passing_score': quiz_data.get('passing_score', 70),
                        'max_attempts': 5,
                        'randomize_questions': False,
                        'show_correct_answers': True,
                        'points_possible': 100,
                        'is_mandatory': True,
                        'created_by_id': str(trainer.user_id)  # Explicitly set the ID
                    }
                )
                
                if created:
                    self.stdout.write(f"  ✓ Quiz created: {quiz.title}")
                    quizzes_created += 1
                    
                    for q_idx, question_data in enumerate(quiz_data['questions'], 1):
                        question, q_created = ModuleQuizQuestion.objects.get_or_create(
                            quiz=quiz,
                            sequence_order=q_idx,
                            defaults={
                                'question_text': question_data['text'],
                                'question_type': question_data['type'],
                                'options': question_data.get('options', []),
                                'correct_answer': question_data['correct_answer'],
                                'points': question_data.get('points', 5),
                                'explanation': question_data.get('explanation', '')
                            }
                        )
                        if q_created:
                            questions_created += 1
                else:
                    self.stdout.write(f"  ⚠ Quiz already exists: {quiz_data['title']}")
                
                if module.quizzes.exists() and not module.has_quizzes:
                    module.has_quizzes = True
                    module.save()
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write(self.style.SUCCESS('SUMMARY'))
        self.stdout.write(self.style.SUCCESS('='*80))
        self.stdout.write(f"\n✓ Quizzes Created: {quizzes_created}")
        self.stdout.write(f"✓ Questions Created: {questions_created}")
        
        courses = Course.objects.annotate(
            quiz_count=Count('modules__quizzes', distinct=True),
            question_count=Count('modules__quizzes__questions', distinct=True)
        )
        
        self.stdout.write(self.style.SUCCESS('\nQuizzes by Course:'))
        for course in courses:
            if course.quiz_count > 0:
                self.stdout.write(f"  {course.title}: {course.quiz_count} quizzes, {course.question_count} questions")
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write(self.style.SUCCESS('✓ QUIZ CREATION COMPLETE!'))
        self.stdout.write(self.style.SUCCESS('='*80 + '\n'))
