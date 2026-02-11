"""
Management command to create test users for the LMS.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from trainee.models import User, Role


class Command(BaseCommand):
    help = 'Create test users for development'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creating test users...'))
        
        # Create roles
        for role_name in ['admin', 'trainer', 'manager', 'trainee']:
            Role.objects.get_or_create(
                role_name=role_name,
                defaults={'description': f'{role_name.capitalize()} role'}
            )
        
        # Create test users
        test_users = [
            {
                'first_name': 'Chris',
                'last_name': 'Williams',
                'email': 'chris.w@company.com',
                'password': 'password123',
                'role': 'admin'
            },
            {
                'first_name': 'John',
                'last_name': 'Doe',
                'email': 'john.doe@company.com',
                'password': 'password123',
                'role': 'trainer'
            },
            {
                'first_name': 'Mike',
                'last_name': 'Johnson',
                'email': 'mike.j@company.com',
                'password': 'password123',
                'role': 'manager'
            },
            {
                'first_name': 'Jane',
                'last_name': 'Smith',
                'email': 'jane.smith@company.com',
                'password': 'password123',
                'role': 'trainee'
            },
        ]
        
        for user_data in test_users:
            email = user_data['email']
            # Skip if user already exists
            if User.objects.filter(email=email).exists():
                self.stdout.write(self.style.WARNING(f'✓ User {email} already exists'))
                continue
            
            user = User.objects.create(
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                email=email,
                password_hash=make_password(user_data['password']),
                primary_role=user_data['role'],
                status='active'
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Created {user_data["role"]} user: {email} (password: {user_data["password"]})'
                )
            )
        
        self.stdout.write(self.style.SUCCESS('\n✓ Test users created successfully!'))
