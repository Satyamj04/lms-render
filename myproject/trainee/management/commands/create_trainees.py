"""
Management command to create sample trainee users with Indian names.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
import uuid
from trainee.models import User, Role, UserRole


class Command(BaseCommand):
    help = 'Create sample trainee users with Indian names'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creating sample trainee users with Indian names...'))
        
        # Get or create trainee role
        trainee_role, _ = Role.objects.get_or_create(
            role_name='trainee',
            defaults={'description': 'Trainee role'}
        )
        
        # Get or create an admin user for assignment
        admin_user, _ = User.objects.get_or_create(
            email='admin@lms.local',
            defaults={
                'first_name': 'System',
                'last_name': 'Admin',
                'password_hash': make_password('Admin@123'),
                'primary_role': 'admin',
                'status': 'active'
            }
        )
        
        # Sample trainee data with Indian names
        trainees_data = [
            {
                'email': 'mukesh.patel@company.com',
                'first_name': 'Mukesh',
                'last_name': 'Patel',
                'password': 'TraineePass@123'
            },
            {
                'email': 'harsh.sharma@company.com',
                'first_name': 'Harsh',
                'last_name': 'Sharma',
                'password': 'TraineePass@123'
            },
            {
                'email': 'priya.gupta@company.com',
                'first_name': 'Priya',
                'last_name': 'Gupta',
                'password': 'TraineePass@123'
            },
            {
                'email': 'rajesh.kumar@company.com',
                'first_name': 'Rajesh',
                'last_name': 'Kumar',
                'password': 'TraineePass@123'
            },
            {
                'email': 'sneha.verma@company.com',
                'first_name': 'Sneha',
                'last_name': 'Verma',
                'password': 'TraineePass@123'
            },
            {
                'email': 'amit.patel@company.com',
                'first_name': 'Amit',
                'last_name': 'Patel',
                'password': 'TraineePass@123'
            },
            {
                'email': 'neha.singh@company.com',
                'first_name': 'Neha',
                'last_name': 'Singh',
                'password': 'TraineePass@123'
            },
            {
                'email': 'arjun.nair@company.com',
                'first_name': 'Arjun',
                'last_name': 'Nair',
                'password': 'TraineePass@123'
            },
            {
                'email': 'divya.iyer@company.com',
                'first_name': 'Divya',
                'last_name': 'Iyer',
                'password': 'TraineePass@123'
            },
            {
                'email': 'rohan.reddy@company.com',
                'first_name': 'Rohan',
                'last_name': 'Reddy',
                'password': 'TraineePass@123'
            },
        ]
        
        created_users = []
        for trainee_data in trainees_data:
            user, created = User.objects.get_or_create(
                email=trainee_data['email'],
                defaults={
                    'user_id': uuid.uuid4(),
                    'first_name': trainee_data['first_name'],
                    'last_name': trainee_data['last_name'],
                    'password_hash': make_password(trainee_data['password']),
                    'primary_role': 'trainee',
                    'status': 'active'
                }
            )
            
            if created:
                created_users.append(user)
                self.stdout.write(self.style.SUCCESS(
                    f'✓ Created trainee: {trainee_data["first_name"]} {trainee_data["last_name"]} ({trainee_data["email"]})'
                ))
                
                # Assign trainee role
                UserRole.objects.get_or_create(
                    user=user,
                    role=trainee_role,
                    defaults={'assigned_by': admin_user}
                )
            else:
                self.stdout.write(self.style.WARNING(
                    f'⚠ User already exists: {trainee_data["email"]}'
                ))
        
        if created_users:
            self.stdout.write(self.style.SUCCESS(
                f'\n✓ Successfully created {len(created_users)} trainee users!'
            ))
            self.stdout.write(self.style.WARNING('\nNote: Default password is "TraineePass@123" for all trainees.'))
            self.stdout.write(self.style.WARNING('Please change passwords through Django admin after login.'))
        else:
            self.stdout.write(self.style.WARNING('No new users created - all users already exist.'))
