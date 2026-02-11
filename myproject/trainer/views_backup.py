"""
Trainer app views - Complete integration with all ViewSets for trainer module management
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.views.decorators.csrf import csrf_exempt
from django.db import IntegrityError, transaction
from django.db.models import Max

from .models import (
    Profile, Course, Unit, VideoUnit, AudioUnit, PresentationUnit,
    TextUnit, PageUnit, Quiz, Question, Assignment, ScormPackage,
    Survey, Enrollment, UnitProgress, AssignmentSubmission,
    QuizAttempt, Leaderboard, TeamLeaderboard, MediaMetadata, Team, TeamMember, Notification
)
from .serializers import (
    ProfileSerializer, CourseSerializer, CourseDetailSerializer,
    UnitSerializer, VideoUnitSerializer, AudioUnitSerializer,
    PresentationUnitSerializer, TextUnitSerializer, PageUnitSerializer,
    QuizSerializer, QuestionSerializer, AssignmentSerializer,
    ScormPackageSerializer, SurveySerializer, EnrollmentSerializer,
    UnitProgressSerializer, AssignmentSubmissionSerializer,
    QuizAttemptSerializer, LeaderboardSerializer, TeamLeaderboardSerializer,
    MediaMetadataSerializer, TeamSerializer, TeamMemberSerializer, NotificationSerializer
)


# ============ Authentication Endpoints ============

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """Login with username/email and password - returns token and user profile"""
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response({'error': 'username and password are required'}, status=400)
    
    user = authenticate(username=username, password=password)
    
    if user is None and '@' in username:
        try:
            profile = Profile.objects.get(email=username)
            user = authenticate(username=profile.username, password=password)
        except Profile.DoesNotExist:
            pass
    
    if user is None:
        return Response({'error': 'Invalid credentials'}, status=400)
    
    if not user.is_active:
        return Response({'error': 'Account is disabled'}, status=400)
    
    token, _ = Token.objects.get_or_create(user=user)
    serializer = ProfileSerializer(user, context={'request': request})
    
    return Response({'token': token.key, 'user': serializer.data})


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """Register new user"""
    email = request.data.get('email')
    password = request.data.get('password')
    full_name = request.data.get('full_name', '')
    role = request.data.get('role', 'trainee')
    
    if not email or not password:
        return Response({'error': 'email and password are required'}, status=400)
    
    username = email
    first_name = ''
    last_name = ''
    if full_name:
        parts = full_name.split(' ', 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ''
    
    try:
        if len(password) < 6:
            return Response({'error': 'Password must be at least 6 characters long'}, status=400)
        
        user = Profile.objects.create_user(username=username, email=email, password=password, first_name=first_name, last_name=last_name)
        user.primary_role = role
        user.save()
        token, _ = Token.objects.get_or_create(user=user)
        serializer = ProfileSerializer(user, context={'request': request})
        return Response({'token': token.key, 'user': serializer.data})
    except IntegrityError:
        return Response({'error': 'A user with this email already exists'}, status=400)
    except Exception as e:
        return Response({'error': 'Signup failed'}, status=400)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def token_by_email(request):
    """Get token by email - dev helper"""
    email = request.data.get('email')
    if not email:
        return Response({'error': 'email is required'}, status=400)
    try:
        user = Profile.objects.get(email=email)
    except Profile.DoesNotExist:
        return Response({'error': 'user not found'}, status=404)
    token, created = Token.objects.get_or_create(user=user)
    return Response({'token': token.key})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """Dashboard statistics for logged-in trainer"""
    user = request.user
    
    total_courses = Course.objects.filter(created_by=user).count()
    
    active_learners = Profile.objects.filter(
        enrollments__course__created_by=user,
        primary_role__in=['learner', 'trainee']
    ).distinct().count()
    
    trainer_courses = Course.objects.filter(created_by=user)
    total_enrollments = Enrollment.objects.filter(course__in=trainer_courses).count()
    
    completed_enrollments = Enrollment.objects.filter(
        course__in=trainer_courses,
        progress_percentage__gte=100
    ).count()
    
    completion_rate = 0
    if total_enrollments > 0:
        completion_rate = round((completed_enrollments / total_enrollments) * 100, 1)
    
    return Response({
        'totalCourses': total_courses,
        'activeLearners': active_learners,
        'completionRate': completion_rate,
        'totalEnrollments': total_enrollments
    })


# ============ ViewSets ============

class ProfileViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Profile.objects.all()
        roles_param = self.request.query_params.get('primary_role__in', None)
        if roles_param:
            roles = [role.strip() for role in roles_param.split(',')]
            queryset = queryset.filter(primary_role__in=roles)
        return queryset

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = CourseSerializer

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CourseDetailSerializer
        return CourseSerializer

    def get_queryset(self):
        if self.action == 'assignable_learners':
            return Course.objects.all()
        
        user = self.request.user
        if getattr(user, 'primary_role', '') == 'trainer':
            qs = Course.objects.filter(created_by=user)
        else:
            qs = Course.objects.filter(enrollments__user=user)
        
        if self.action == 'retrieve':
            qs = qs.prefetch_related('units', 'units__quiz_details__questions')
        
        return qs

    def perform_create(self, serializer):
        course = serializer.save(created_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        """Delete course - creator only"""
        course = self.get_object()
        if course.created_by != request.user and not request.user.is_superuser:
            return Response(
                {'detail': 'Only the course creator can delete it.'},
                status=status.HTTP_403_FORBIDDEN
            )
        course.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'])
    def units(self, request, pk=None):
        course = self.get_object()
        units = course.units.all()
        serializer = UnitSerializer(units, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        course = self.get_object()
        course.status = 'published'
        course.save()
        return Response({'status': 'published'})

    @action(detail=True, methods=['get'])
    def assignable_learners(self, request, pk=None):
        """Get learners not yet enrolled"""
        try:
            course = Course.objects.get(pk=pk)
        except Course.DoesNotExist:
            return Response({'detail': 'Course not found'}, status=404)
        
        learners = Profile.objects.filter(primary_role__in=['learner', 'trainee'])
        serializer = ProfileSerializer(learners, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Duplicate course"""
        user = request.user
        if not (user.is_superuser or getattr(user, 'primary_role', '') == 'trainer'):
            return Response({'detail': 'Trainer permission required'}, status=403)

        orig = self.get_object()
        dup = Course.objects.create(
            title=f"{orig.title} (copy)",
            description=orig.description,
            about=orig.about,
            outcomes=orig.outcomes,
            course_type=orig.course_type,
            status='draft',
            is_mandatory=orig.is_mandatory,
            estimated_duration_hours=orig.estimated_duration_hours,
            passing_criteria=orig.passing_criteria,
            created_by=user
        )
        
        for unit in orig.units.all():
            new_unit = Unit.objects.create(
                course=dup,
                module_type=unit.module_type,
                title=unit.title,
                description=unit.description,
                sequence_order=unit.sequence_order,
                is_mandatory=unit.is_mandatory
            )
        
        try:
            serializer = CourseDetailSerializer(dup, context={'request': request})
            return Response(serializer.data)
        except:
            serializer = CourseSerializer(dup, context={'request': request})
            return Response(serializer.data)

    @action(detail=True, methods=['get', 'put'])
    def sequence(self, request, pk=None):
        """Get or update sequencing"""
        user = request.user
        if not (user.is_superuser or getattr(user, 'primary_role', '') == 'trainer'):
            return Response({'detail': 'Trainer permission required'}, status=403)

        course = self.get_object()
        if request.method == 'GET':
            units = course.units.all().order_by('sequence_order')
            return Response(UnitSerializer(units, many=True).data)

        units_data = request.data.get('units', [])
        for idx, unit_id in enumerate(units_data):
            try:
                unit = Unit.objects.get(id=unit_id, course=course)
                unit.sequence_order = idx
                unit.save()
            except Unit.DoesNotExist:
                continue
        
        units = course.units.all().order_by('sequence_order')
        return Response(UnitSerializer(units, many=True).data)

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """Assign course to users/teams"""
        course = self.get_object()
        user_ids = request.data.get('user_ids', []) or []
        team_ids = request.data.get('team_ids', []) or []
        created = 0
        
        for uid in user_ids:
            try:
                u = Profile.objects.get(id=uid)
                if not Enrollment.objects.filter(course=course, user=u).exists():
                    Enrollment.objects.create(course=course, user=u, assigned_by=request.user)
                    created += 1
            except Profile.DoesNotExist:
                continue
        
        for tid in team_ids:
            members = TeamMember.objects.filter(team_id=tid).values_list('user_id', flat=True)
            for uid in members:
                try:
                    u = Profile.objects.get(id=uid)
                    if not Enrollment.objects.filter(course=course, user=u).exists():
                        Enrollment.objects.create(course=course, user=u, assigned_by=request.user)
                        created += 1
                except Profile.DoesNotExist:
                    continue
        
        return Response({'created': created})


class UnitViewSet(viewsets.ModelViewSet):
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        course_id = self.request.query_params.get('course_id')
        queryset = Unit.objects.select_related(
            'video_details', 'audio_details', 'presentation_details',
            'text_details', 'page_details', 'quiz_details',
            'assignment_details', 'scorm_details', 'survey_details'
        ).prefetch_related('quiz_details__questions')
        
        if course_id:
            return queryset.filter(course_id=course_id).order_by('sequence_order')
        return queryset.all()

    def create(self, request, *args, **kwargs):
        """Create unit with auto-generated sequence"""
        data = request.data.copy()
        course_id = data.get('course') or data.get('course_id')
        
        if data.get('sequence_order') is None and data.get('order') is None:
            if not course_id:
                return Response({'course': 'course is required'}, status=400)
            try:
                result = Unit.objects.filter(course_id=course_id).aggregate(Max('sequence_order'))
                max_seq = result.get('sequence_order__max')
                next_seq = (max_seq if max_seq is not None else -1) + 1
                data['sequence_order'] = next_seq
            except Exception as e:
                return Response({'detail': f'Error: {str(e)}'}, status=400)

        serializer = self.get_serializer(data=data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        
        try:
            unit = serializer.save()
            
            # Auto-create subtype record
            module_type = unit.module_type
            if module_type == 'video' and not hasattr(unit, 'video_details'):
                VideoUnit.objects.create(unit=unit)
            elif module_type == 'audio' and not hasattr(unit, 'audio_details'):
                AudioUnit.objects.create(unit=unit)
            elif module_type == 'presentation' and not hasattr(unit, 'presentation_details'):
                PresentationUnit.objects.create(unit=unit)
            elif module_type == 'text' and not hasattr(unit, 'text_details'):
                TextUnit.objects.create(unit=unit)
            elif module_type == 'page' and not hasattr(unit, 'page_details'):
                PageUnit.objects.create(unit=unit)
            elif module_type == 'quiz' and not hasattr(unit, 'quiz_details'):
                Quiz.objects.create(unit=unit)
            elif module_type == 'assignment' and not hasattr(unit, 'assignment_details'):
                Assignment.objects.create(unit=unit)
            elif module_type == 'scorm' and not hasattr(unit, 'scorm_details'):
                ScormPackage.objects.create(unit=unit)
            elif module_type == 'survey' and not hasattr(unit, 'survey_details'):
                Survey.objects.create(unit=unit)
                
        except Exception as e:
            return Response({'detail': str(e)}, status=500)

        return Response(UnitSerializer(unit).data, status=201)


class VideoUnitViewSet(viewsets.ModelViewSet):
    queryset = VideoUnit.objects.all()
    serializer_class = VideoUnitSerializer
    permission_classes = [IsAuthenticated]

class AudioUnitViewSet(viewsets.ModelViewSet):
    queryset = AudioUnit.objects.all()
    serializer_class = AudioUnitSerializer
    permission_classes = [IsAuthenticated]

class PresentationUnitViewSet(viewsets.ModelViewSet):
    queryset = PresentationUnit.objects.all()
    serializer_class = PresentationUnitSerializer
    permission_classes = [IsAuthenticated]

class TextUnitViewSet(viewsets.ModelViewSet):
    queryset = TextUnit.objects.all()
    serializer_class = TextUnitSerializer
    permission_classes = [IsAuthenticated]

class PageUnitViewSet(viewsets.ModelViewSet):
    queryset = PageUnit.objects.all()
    serializer_class = PageUnitSerializer
    permission_classes = [IsAuthenticated]

class QuizViewSet(viewsets.ModelViewSet):
    queryset = Quiz.objects.all()
    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        unit_id = self.request.query_params.get('unit_id')
        queryset = Quiz.objects.prefetch_related('questions')
        if unit_id:
            return queryset.filter(unit_id=unit_id)
        return queryset

class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    permission_classes = [IsAuthenticated]

class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer
    permission_classes = [IsAuthenticated]

class ScormPackageViewSet(viewsets.ModelViewSet):
    queryset = ScormPackage.objects.all()
    serializer_class = ScormPackageSerializer
    permission_classes = [IsAuthenticated]

class SurveyViewSet(viewsets.ModelViewSet):
    queryset = Survey.objects.all()
    serializer_class = SurveySerializer
    permission_classes = [IsAuthenticated]

class EnrollmentViewSet(viewsets.ModelViewSet):
    queryset = Enrollment.objects.all()
    serializer_class = EnrollmentSerializer
    permission_classes = [IsAuthenticated]

class UnitProgressViewSet(viewsets.ModelViewSet):
    queryset = UnitProgress.objects.all()
    serializer_class = UnitProgressSerializer
    permission_classes = [IsAuthenticated]

class AssignmentSubmissionViewSet(viewsets.ModelViewSet):
    queryset = AssignmentSubmission.objects.all()
    serializer_class = AssignmentSubmissionSerializer
    permission_classes = [IsAuthenticated]

class QuizAttemptViewSet(viewsets.ModelViewSet):
    queryset = QuizAttempt.objects.all()
    serializer_class = QuizAttemptSerializer
    permission_classes = [IsAuthenticated]

class LeaderboardViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Leaderboard.objects.all()
    serializer_class = LeaderboardSerializer
    permission_classes = [IsAuthenticated]

class TeamLeaderboardViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TeamLeaderboard.objects.all()
    serializer_class = TeamLeaderboardSerializer
    permission_classes = [IsAuthenticated]

class MediaUploadViewSet(viewsets.ModelViewSet):
    queryset = MediaMetadata.objects.all()
    serializer_class = MediaMetadataSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.all()
    serializer_class = TeamSerializer
    permission_classes = [IsAuthenticated]

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Notification.objects.filter(user=self.request.user)
        return Notification.objects.none()

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        notification = self.get_object()
        notification.mark_as_read()
        return Response({'status': 'marked as read'})
    queryset = Enrollment.objects.all()
    serializer_class = EnrollmentSerializer
    
    def get_queryset(self):
        # Show enrollments for courses this trainer created
        trainer_id = str(self.request.user.profile.id) if hasattr(self.request.user, 'profile') else None
        course_ids = Course.objects.filter(created_by=trainer_id).values_list('id', flat=True)
        return Enrollment.objects.filter(course_id__in=course_ids)
