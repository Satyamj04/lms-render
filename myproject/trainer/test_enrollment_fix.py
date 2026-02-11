"""
Test script to verify the enrollment creation fix.
Tests that courses can be created and users enrolled without errors.
"""
import uuid
from django.test import TestCase, RequestFactory
from rest_framework.test import APITestCase, force_authenticate
from rest_framework.request import Request
from django.contrib.auth.models import AnonymousUser

from .models import Profile, Course, Enrollment, Team, TeamMember
from .serializers import EnrollmentSerializer
from .views import EnrollmentViewSet, CourseViewSet


class EnrollmentFixTestCase(APITestCase):
    """
    Test suite for the enrollment creation fix.
    Verifies that:
    1. Enrollments can be created via API with or without authenticated user
    2. assigned_by field is properly handled (can be null)
    3. Course assignment to users works end-to-end
    """

    def setUp(self):
        """Set up test data"""
        # Create test users/profiles
        self.trainer = Profile.objects.create(
            id=uuid.uuid4(),
            username='trainer@test.com',
            email='trainer@test.com',
            password='hashed_password',
            primary_role='trainer',
            first_name='Test',
            last_name='Trainer'
        )
        
        self.learner1 = Profile.objects.create(
            id=uuid.uuid4(),
            username='learner1@test.com',
            email='learner1@test.com',
            password='hashed_password',
            primary_role='trainee',
            first_name='Learner',
            last_name='One'
        )
        
        self.learner2 = Profile.objects.create(
            id=uuid.uuid4(),
            username='learner2@test.com',
            email='learner2@test.com',
            password='hashed_password',
            primary_role='trainee',
            first_name='Learner',
            last_name='Two'
        )
        
        # Create test course
        self.course = Course.objects.create(
            id=uuid.uuid4(),
            title='Test Course',
            description='Test course for enrollment',
            status='draft',
            created_by=self.trainer
        )
        
        # Create test team
        self.team = Team.objects.create(
            team_id=uuid.uuid4(),
            team_name='Test Team',
            manager=self.trainer
        )
        
        # Add learners to team
        TeamMember.objects.create(
            id=uuid.uuid4(),
            team=self.team,
            user=self.learner1,
            assigned_by=self.trainer
        )
        TeamMember.objects.create(
            id=uuid.uuid4(),
            team=self.team,
            user=self.learner2,
            assigned_by=self.trainer
        )
        
        self.factory = RequestFactory()

    def test_enrollment_creation_basic(self):
        """Test basic enrollment creation works"""
        enrollment = Enrollment.objects.create(
            id=uuid.uuid4(),
            course=self.course,
            user=self.learner1,
            status='assigned'
            # assigned_by intentionally omitted to test null handling
        )
        
        self.assertIsNotNone(enrollment.id)
        self.assertEqual(enrollment.course, self.course)
        self.assertEqual(enrollment.user, self.learner1)
        self.assertEqual(enrollment.status, 'assigned')
        self.assertIsNone(enrollment.assigned_by)  # Should be null

    def test_enrollment_serializer_with_optional_assigned_by(self):
        """Test that serializer accepts missing assigned_by field"""
        data = {
            'course': self.course.id,
            'user': self.learner1.id,
            'status': 'assigned'
        }
        serializer = EnrollmentSerializer(data=data)
        
        # Serializer should be valid even without assigned_by
        if not serializer.is_valid():
            print(f"Serializer errors: {serializer.errors}")
        self.assertTrue(serializer.is_valid(), f"Serializer errors: {serializer.errors}")

    def test_enrollment_serializer_with_assigned_by(self):
        """Test that serializer accepts assigned_by field"""
        data = {
            'course': self.course.id,
            'user': self.learner1.id,
            'status': 'assigned',
            'assigned_by': self.trainer.id
        }
        serializer = EnrollmentSerializer(data=data)
        
        self.assertTrue(serializer.is_valid(), f"Serializer errors: {serializer.errors}")

    def test_enrollment_viewset_perform_create_with_anon_user(self):
        """Test that perform_create handles AnonymousUser properly"""
        # Create a request with AnonymousUser
        request = self.factory.post('/api/enrollments/')
        request.user = AnonymousUser()
        
        # Create enrollment via viewset
        viewset = EnrollmentViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        
        # Prepare serializer
        data = {
            'course': self.course.id,
            'user': self.learner1.id,
            'status': 'assigned'
        }
        serializer = EnrollmentSerializer(data=data)
        
        self.assertTrue(serializer.is_valid())
        
        # Manually call perform_create (normally done by viewset)
        viewset.perform_create(serializer)
        
        # Verify enrollment was created
        enrollment = Enrollment.objects.get(course=self.course, user=self.learner1)
        self.assertIsNotNone(enrollment)
        self.assertIsNone(enrollment.assigned_by)  # Should be null for AnonymousUser

    def test_enrollment_viewset_perform_create_with_auth_user(self):
        """Test that perform_create auto-sets assigned_by for authenticated user"""
        # Create a request with authenticated user (trainer)
        request = self.factory.post('/api/enrollments/')
        request.user = self.trainer
        
        # Create enrollment via viewset
        viewset = EnrollmentViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        
        # Prepare serializer
        data = {
            'course': self.course.id,
            'user': self.learner2.id,
            'status': 'assigned'
        }
        serializer = EnrollmentSerializer(data=data)
        
        self.assertTrue(serializer.is_valid())
        
        # Manually call perform_create
        viewset.perform_create(serializer)
        
        # Verify enrollment was created with assigned_by set
        enrollment = Enrollment.objects.get(course=self.course, user=self.learner2)
        self.assertIsNotNone(enrollment)
        self.assertEqual(enrollment.assigned_by, self.trainer)

    def test_course_assign_action_single_learner(self):
        """Test course assign action with single learner"""
        request = self.factory.post(f'/api/courses/{self.course.id}/assign/')
        request.user = self.trainer
        request.data = {'learner_ids': [str(self.learner1.id)], 'team_ids': []}
        
        # Test the assign action
        viewset = CourseViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        
        response = viewset.assign(request, pk=self.course.id)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['assigned'], 1)
        
        # Verify enrollment was created
        enrollment = Enrollment.objects.get(course=self.course, user=self.learner1)
        self.assertEqual(enrollment.status, 'assigned')

    def test_course_assign_action_team(self):
        """Test course assign action with entire team"""
        request = self.factory.post(f'/api/courses/{self.course.id}/assign/')
        request.user = self.trainer
        request.data = {'learner_ids': [], 'team_ids': [str(self.team.team_id)]}
        
        viewset = CourseViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        
        response = viewset.assign(request, pk=self.course.id)
        
        self.assertEqual(response.status_code, 200)
        # Should assign to both team members
        self.assertEqual(response.data['assigned'], 2)
        
        # Verify both team members are enrolled
        enrollments = Enrollment.objects.filter(course=self.course)
        self.assertEqual(enrollments.count(), 2)

    def test_unique_enrollment_constraint(self):
        """Test that duplicate enrollments don't create duplicates"""
        # Create first enrollment
        Enrollment.objects.create(
            id=uuid.uuid4(),
            course=self.course,
            user=self.learner1,
            status='assigned'
        )
        
        # Try to create duplicate (should use get_or_create logic in actual code)
        with self.assertRaises(Exception):  # Should raise IntegrityError due to unique constraint
            Enrollment.objects.create(
                id=uuid.uuid4(),
                course=self.course,
                user=self.learner1,
                status='assigned'
            )

    def test_end_to_end_course_creation_and_enrollment(self):
        """
        End-to-end test: Create course → Create enrollment → Verify data
        This tests the complete flow that was failing before the fix.
        """
        # Create a new course
        new_course = Course.objects.create(
            id=uuid.uuid4(),
            title='E2E Test Course',
            description='Full end-to-end test',
            status='draft',
            created_by=self.trainer
        )
        
        # Simulate enrollment via API with AnonymousUser
        request = self.factory.post('/api/enrollments/')
        request.user = AnonymousUser()
        
        viewset = EnrollmentViewSet()
        viewset.request = request
        
        data = {
            'course': new_course.id,
            'user': self.learner1.id,
            'status': 'assigned'
        }
        serializer = EnrollmentSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        viewset.perform_create(serializer)
        
        # Verify enrollment
        enrollment = Enrollment.objects.get(course=new_course, user=self.learner1)
        self.assertIsNotNone(enrollment)
        self.assertEqual(enrollment.status, 'assigned')
        
        # Verify data is retrievable
        retrieved = Enrollment.objects.filter(course=new_course).first()
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.user, self.learner1)
        self.assertEqual(retrieved.course, new_course)


if __name__ == '__main__':
    import django
    from django.conf import settings
    from django.test.utils import get_runner
    
    if not settings.configured:
        import os
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
        django.setup()
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(['trainer.test_enrollment_fix'])
