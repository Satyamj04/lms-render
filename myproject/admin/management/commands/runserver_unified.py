"""
Unified runserver command for both admin and trainer modules.
Run with: python manage.py runserver_unified [port]
"""
from django.core.management.commands.runserver import Command as RunServerCommand
from django.core.management import call_command


class Command(RunServerCommand):
    help = 'Run server with both admin and trainer modules enabled'

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--with-docs',
            action='store_true',
            dest='with_docs',
            help='Include API documentation'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting unified LMS server...'))
        self.stdout.write(self.style.SUCCESS('✓ Admin module enabled'))
        self.stdout.write(self.style.SUCCESS('✓ Trainer module enabled'))
        self.stdout.write(self.style.WARNING('\nEndpoints:'))
        self.stdout.write('  Admin API: /api/lms-admin/')
        self.stdout.write('  Trainer API: /api/lms-admin/trainer/')
        self.stdout.write(self.style.WARNING('\nFrontend will be served separately\n'))
        
        super().handle(*args, **options)
