"""
Trainer app views - Complete integration with all ViewSets for trainer module management
"""
from rest_framework import viewsets, status, permissions, serializers
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from django.contrib.auth import authenticate
from django.views.decorators.csrf import csrf_exempt
from django.db import IntegrityError, transaction
from django.db.models import Max, Q

from .models import (
    Profile, Course, Unit, VideoUnit, AudioUnit, PresentationUnit,
    TextUnit, PageUnit, Quiz, Question, Assignment, ScormPackage,
    Survey, Enrollment, UnitProgress, AssignmentSubmission,
    QuizAttempt, Leaderboard, MediaMetadata, Team, TeamMember, Notification,
    ModuleSequencing, Note, Role, UserRole
)
from .serializers import (
    ProfileSerializer, CourseSerializer, CourseDetailSerializer, CourseNestedCreateSerializer,
    UnitSerializer, VideoUnitSerializer, AudioUnitSerializer,
    PresentationUnitSerializer, TextUnitSerializer, PageUnitSerializer,
    QuizSerializer, QuestionSerializer, AssignmentSerializer,
    ScormPackageSerializer, SurveySerializer, EnrollmentSerializer,
    UnitProgressSerializer, AssignmentSubmissionSerializer,
    QuizAttemptSerializer, LeaderboardSerializer,
    MediaMetadataSerializer, TeamSerializer, TeamMemberSerializer, NotificationSerializer,
    ModuleSequencingSerializer, NoteSerializer, RoleSerializer, UserRoleSerializer
)


# ============ Authentication Endpoints ============

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """Login with username/email and password - returns token and user profile"""
    from admin.models import UserProfile
    from django.contrib.auth.hashers import check_password
    from django.contrib.auth.models import User as DjangoUser
    
    username_or_email = request.data.get('username') or request.data.get('email')
    password = request.data.get('password')
    
    if not username_or_email or not password:
        return Response({'error': 'username/email and password are required'}, status=400)
    
    try:
        # Find user profile by email
        profile = UserProfile.objects.get(email=username_or_email)
        
        # Check password
        if not check_password(password, profile.password_hash):
            return Response({'error': 'Invalid email or password'}, status=400)
        
        # Get or create Django User for token auth
        django_user, created = DjangoUser.objects.get_or_create(
            username=f"user_{profile.id}",
            defaults={
                'email': profile.email,
                'first_name': profile.first_name,
                'last_name': profile.last_name,
            }
        )
        
        # Generate or get token
        token, _ = Token.objects.get_or_create(user=django_user)
        
        # Return profile data (not Django user data)
        profile_data = {
            'id': str(profile.id),
            'email': profile.email,
            'first_name': profile.first_name,
            'last_name': profile.last_name,
            'full_name': f"{profile.first_name} {profile.last_name}".strip(),
            'primary_role': profile.role,
            'status': profile.status,
            'profile_image_url': profile.profile_image_url,
        }
        
        return Response({'token': token.key, 'user': profile_data})
        
    except UserProfile.DoesNotExist:
        return Response({'error': 'Invalid email or password'}, status=400)
    except Exception as e:
        return Response({'error': f'Login error: {str(e)}'}, status=500)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """Register new user"""
    from admin.models import UserProfile
    from django.contrib.auth.hashers import make_password
    from django.contrib.auth.models import User as DjangoUser
    
    email = request.data.get('email')
    password = request.data.get('password')
    full_name = request.data.get('full_name', '')
    role = request.data.get('primary_role', 'trainee')
    
    if not email or not password:
        return Response({'error': 'email and password are required'}, status=400)
    
    if len(password) < 6:
        return Response({'error': 'Password must be at least 6 characters long'}, status=400)
    
    first_name = ''
    last_name = ''
    if full_name:
        parts = full_name.split(' ', 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ''
    
    try:
        # Create UserProfile
        profile = UserProfile.objects.create(
            email=email,
            password_hash=make_password(password),
            first_name=first_name,
            last_name=last_name,
            role=role,
            status='active'
        )
        
        # Create corresponding Django User for token auth
        django_user = DjangoUser.objects.create(
            username=f"user_{profile.id}",
            email=profile.email,
            first_name=profile.first_name,
            last_name=profile.last_name,
        )
        
        # Generate token
        token, _ = Token.objects.get_or_create(user=django_user)
        
        # Return profile data
        profile_data = {
            'id': str(profile.id),
            'email': profile.email,
            'first_name': profile.first_name,
            'last_name': profile.last_name,
            'full_name': f"{profile.first_name} {profile.last_name}".strip(),
            'primary_role': profile.role,
            'status': profile.status,
        }
        
        return Response({'token': token.key, 'user': profile_data}, status=201)
        
    except IntegrityError:
        return Response({'error': 'A user with this email already exists'}, status=400)
    except Exception as e:
        return Response({'error': f'Registration error: {str(e)}'}, status=500)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def token_by_email(request):
    """Get token by email - for development/testing"""
    email = request.data.get('email')
    if not email:
        return Response({'error': 'email is required'}, status=400)
    
    try:
        user = Profile.objects.get(email=email)
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key})
    except Profile.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)


@api_view(['GET'])
@permission_classes([AllowAny])
def test_auth(request):
    """Test authentication endpoint"""
    from admin.models import UserProfile
    
    data = {
        'user': str(request.user),
        'is_authenticated': request.user.is_authenticated,
        'username': request.user.username if request.user.is_authenticated else None,
    }
    
    if request.user.is_authenticated:
        try:
            user_id = request.user.username.replace('user_', '')
            data['extracted_id'] = user_id
            profile = UserProfile.objects.get(id=user_id)
            data['profile_found'] = True
            data['profile_email'] = profile.email
            data['profile_role'] = profile.role
        except Exception as e:
            data['profile_found'] = False
            data['error'] = str(e)
    
    return Response(data)


@api_view(['GET'])
@permission_classes([AllowAny])
def trainee_courses(request):
    """Get courses for a trainee user (enrolled courses)"""
    from admin.models import UserProfile
    import logging
    logger = logging.getLogger(__name__)
    
    # Get user_id from query params or authenticated user
    user_profile = None
    if request.user and request.user.is_authenticated:
        try:
            user_id = request.user.username.replace('user_', '')
            user_profile = UserProfile.objects.get(id=user_id)
        except:
            pass
    
    # Fallback to user_id query parameter
    if not user_profile:
        user_id_param = request.query_params.get('user_id') or request.GET.get('user_id')
        if user_id_param:
            try:
                user_profile = UserProfile.objects.get(id=user_id_param)
            except UserProfile.DoesNotExist:
                return Response({'error': 'User not found'}, status=404)
    
    if not user_profile:
        return Response({'error': 'User ID required'}, status=400)
    
    # Get enrolled courses
    enrollments = Enrollment.objects.filter(user_id=user_profile.id).select_related('course')
    
    courses_data = []
    for enrollment in enrollments:
        course = enrollment.course
        
        # Calculate progress
        total_units = Unit.objects.filter(course=course).count()
        completed_units = UnitProgress.objects.filter(
            user_id=user_profile.id,
            unit__course=course,
            is_completed=True
        ).count()
        
        progress = int((completed_units / total_units * 100)) if total_units > 0 else 0
        
        # Get modules (units) for this course
        modules = Unit.objects.filter(course=course).order_by('sequence_order')
        modules_data = []
        for module in modules:
            modules_data.append({
                'id': str(module.id),
                'title': module.title,
                'description': module.description or '',
                'sequence_order': module.sequence_order,
                'module_type': module.module_type
            })
        
        courses_data.append({
            'id': str(course.id),
            'title': course.title,
            'description': course.description or '',
            'status': enrollment.status,
            'progress': progress,
            'enrolled': True,
            'assigned_at': enrollment.assigned_at.isoformat() if enrollment.assigned_at else None,
            'modules': modules_data,
            'total_modules': len(modules_data)
        })
    
    return Response({
        'courses': courses_data,
        'total': len(courses_data)
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def trainee_course_detail(request, course_id):
    """Get details for a specific course (trainee view)"""
    from admin.models import UserProfile
    import logging
    logger = logging.getLogger(__name__)
    
    # Get user_id from query params or authenticated user
    user_profile = None
    if request.user and request.user.is_authenticated:
        try:
            user_id = request.user.username.replace('user_', '')
            user_profile = UserProfile.objects.get(id=user_id)
        except:
            pass
    
    # Fallback to user_id query parameter
    if not user_profile:
        user_id_param = request.query_params.get('user_id') or request.GET.get('user_id')
        if user_id_param:
            try:
                user_profile = UserProfile.objects.get(id=user_id_param)
            except UserProfile.DoesNotExist:
                return Response({'error': 'User not found'}, status=404)
    
    # Get the course
    try:
        course = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        return Response({'error': 'Course not found'}, status=404)
    
    # Check if user is enrolled (if user_profile provided)
    enrollment = None
    if user_profile:
        try:
            enrollment = Enrollment.objects.get(user_id=user_profile.id, course=course)
        except Enrollment.DoesNotExist:
            pass
    
    # Calculate progress
    total_units = Unit.objects.filter(course=course).count()
    completed_units = 0
    if user_profile:
        completed_units = UnitProgress.objects.filter(
            user_id=user_profile.id,
            unit__course=course,
            is_completed=True
        ).count()
    
    progress = int((completed_units / total_units * 100)) if total_units > 0 else 0
    
    # Get modules (units) for this course
    modules = Unit.objects.filter(course=course).order_by('sequence_order')
    modules_data = []
    total_items = 0
    for module in modules:
        # Count content items in this module
        item_count = 0
        if module.media_files and hasattr(module.media_files, 'all'):
            item_count += module.media_files.count()
        if module.module_type == 'quiz' and hasattr(module, 'quizzes'):
            item_count += module.quizzes.count()
        
        total_items += item_count
        
        modules_data.append({
            'id': str(module.id),
            'title': module.title,
            'description': module.description or '',
            'sequence_order': module.sequence_order,
            'position': module.sequence_order,  # Frontend expects 'position'
            'module_type': module.module_type,
            'item_count': item_count  # Add item count per module
        })
    
    course_data = {
        'id': str(course.id),
        'title': course.title,
        'description': course.description or '',
        'status': enrollment.status if enrollment else 'not_enrolled',
        'progress': progress,
        'enrolled': enrollment is not None,
        'assigned_at': enrollment.assigned_at.isoformat() if enrollment and enrollment.assigned_at else None,
        'modules': modules_data,
        'total_modules': len(modules_data),
        'total_items': total_items  # Add total item count
    }
    
    # Wrap in 'course' key for frontend compatibility
    return Response({'course': course_data})


@api_view(['POST'])
@permission_classes([AllowAny])
def trainee_course_start(request, course_id):
    """Start a course (mark as in_progress)"""
    from admin.models import UserProfile
    import logging
    logger = logging.getLogger(__name__)
    
    # Get user_id from request body or query params
    user_id = request.data.get('user_id') or request.query_params.get('user_id') or request.GET.get('user_id')
    
    if not user_id:
        return Response({'error': 'User ID required'}, status=400)
    
    try:
        user_profile = UserProfile.objects.get(id=user_id)
    except UserProfile.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)
    
    try:
        course = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        return Response({'error': 'Course not found'}, status=404)
    
    # Get or create enrollment
    enrollment, created = Enrollment.objects.get_or_create(
        user_id=user_profile.id,
        course=course,
        defaults={'status': 'in_progress'}
    )
    
    # Update status to in_progress if it was assigned
    if enrollment.status == 'assigned':
        enrollment.status = 'in_progress'
        enrollment.save()
    
    return Response({
        'success': True,
        'status': enrollment.status,
        'message': 'Course started successfully'
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def trainee_course_modules(request, course_id):
    """Get modules for a specific course"""
    try:
        course = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        return Response({'error': 'Course not found'}, status=404)
    
    # Get modules (units) for this course
    modules = Unit.objects.filter(course=course).order_by('sequence_order')
    modules_data = []
    for module in modules:
        modules_data.append({
            'id': str(module.id),
            'title': module.title,
            'description': module.description or '',
            'sequence_order': module.sequence_order,
            'module_type': module.module_type,
            'is_mandatory': module.is_mandatory,
            'estimated_duration_minutes': module.estimated_duration_minutes
        })
    
    return Response(modules_data)


@api_view(['GET'])
@permission_classes([AllowAny])
def trainee_course_completed(request, course_id):
    """Get completed modules for a course"""
    from admin.models import UserProfile
    
    user_id = request.query_params.get('user_id') or request.GET.get('user_id')
    
    if not user_id:
        return Response({'completed_modules': []})
    
    try:
        user_profile = UserProfile.objects.get(id=user_id)
    except UserProfile.DoesNotExist:
        return Response({'completed_modules': []})
    
    try:
        course = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        return Response({'error': 'Course not found'}, status=404)
    
    # Get completed module IDs
    completed_progress = UnitProgress.objects.filter(
        user_id=user_profile.id,
        unit__course=course,
        is_completed=True
    ).values_list('unit_id', flat=True)
    
    completed_module_ids = [str(uid) for uid in completed_progress]
    
    return Response({
        'completed_modules': completed_module_ids,
        'total_completed': len(completed_module_ids)
    })


@api_view(['PATCH'])
@permission_classes([AllowAny])
def trainee_course_update(request, course_id):
    """Update course progress/status"""
    from admin.models import UserProfile
    
    user_id = request.data.get('user_id') or request.query_params.get('user_id')
    
    if not user_id:
        return Response({'error': 'User ID required'}, status=400)
    
    try:
        user_profile = UserProfile.objects.get(id=user_id)
    except UserProfile.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)
    
    try:
        course = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        return Response({'error': 'Course not found'}, status=404)
    
    try:
        enrollment = Enrollment.objects.get(user_id=user_profile.id, course=course)
    except Enrollment.DoesNotExist:
        return Response({'error': 'Enrollment not found'}, status=404)
    
    # Update fields if provided
    if 'status' in request.data:
        enrollment.status = request.data['status']
    
    enrollment.save()
    
    return Response({
        'success': True,
        'status': enrollment.status,
        'message': 'Course updated successfully'
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def trainee_module_content(request, module_id):
    """Get content/media files for a specific module"""
    from admin.models import UserProfile
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        module = Unit.objects.get(id=module_id)
    except Unit.DoesNotExist:
        return Response({'error': 'Module not found'}, status=404)
    
    # Build response based on module type
    response_data = {
        'id': str(module.id),
        'title': module.title,
        'description': module.description or '',
        'module_type': module.module_type,
        'sequence_order': module.sequence_order,
        'estimated_duration_minutes': module.estimated_duration_minutes,
        'is_mandatory': module.is_mandatory,
        'content': []
    }
    
    # Handle type-specific content (video_units, presentation_units, pdf_units, etc.)
    if module.module_type == 'video' and hasattr(module, 'video_details'):
        video = module.video_details
        if video and video.video_url:
            response_data['content'].append({
                'id': str(module.id),
                'content_type': 'video',
                'file_url': video.video_url,
                'file_reference': video.video_url,
                'title': module.title,
                'file_name': f"{module.title}.mp4",
                'duration': video.duration,
                'duration_seconds': video.duration,
                'module_id': str(module.id),
                'module_title': module.title,
                'description': module.description or '',
                'is_unlocked': True
            })
    
    elif module.module_type == 'presentation' and hasattr(module, 'presentation_details'):
        ppt = module.presentation_details
        if ppt and ppt.file_url:
            response_data['content'].append({
                'id': str(module.id),
                'content_type': 'ppt',
                'file_url': ppt.file_url,
                'file_reference': ppt.file_url,
                'title': module.title,
                'file_name': f"{module.title}.pdf",
                'module_id': str(module.id),
                'module_title': module.title,
                'description': module.description or '',
                'is_unlocked': True
            })
    
    # Get media files for this module (from media_metadata table)
    if module.media_files and hasattr(module.media_files, 'all'):
        for media_file in module.media_files.all():
            # Build ABSOLUTE file URL from storage_path
            file_url = None
            if media_file.storage_path:
                from django.conf import settings
                # Build absolute URL so frontend can access media from Django server
                relative_url = f"{settings.MEDIA_URL}{media_file.storage_path}"
                file_url = request.build_absolute_uri(relative_url)
            
            # Convert file size from bytes to MB
            file_size_mb = round(media_file.file_size / (1024 * 1024), 2) if media_file.file_size else 0
            
            # Normalize content types for frontend
            content_type = media_file.file_type
            if content_type == 'pdfs':
                content_type = 'pdf'
            elif content_type == 'presentations':
                content_type = 'ppt'
            elif content_type == 'videos':
                content_type = 'video'
            elif content_type == 'audios':
                content_type = 'audio'
            
            response_data['content'].append({
                'id': str(media_file.id),
                'content_type': content_type,  # Normalized content type
                'file_url': file_url,  # Frontend expects 'file_url', not 'file_path'
                'file_reference': file_url,  # Alternative field name
                'title': media_file.file_name,  # Use file name as title
                'file_name': media_file.file_name,
                'file_size_mb': file_size_mb,  # Frontend expects MB, not bytes
                'mime_type': media_file.mime_type,
                'duration': media_file.duration,
                'duration_seconds': media_file.duration,
                'width': media_file.width,
                'height': media_file.height,
                'module_id': str(module.id),  # Add module reference
                'module_title': module.title,  # Add module title
                'description': '',  # Add empty description if not present
                'is_unlocked': True  # Allow access by default
            })
    
    # For quiz modules, include quiz data in content array
    if module.module_type == 'quiz' and hasattr(module, 'quizzes'):
        quizzes = module.quizzes.all()
        for quiz in quizzes:
            questions_count = quiz.questions.count() if hasattr(quiz, 'questions') else 0
            response_data['content'].append({
                'id': str(quiz.id),
                'quiz_id': str(quiz.id),
                'content_type': 'quiz',
                'title': module.title,  # Use module title for quiz
                'description': module.description or '',
                'time_limit_minutes': quiz.time_limit or 0,
                'passing_score': quiz.passing_score,
                'attempts_allowed': quiz.attempts_allowed,
                'show_answers': quiz.show_answers,
                'randomize_questions': quiz.randomize_questions,
                'mandatory_completion': quiz.mandatory_completion,
                'questions_count': questions_count,
                'points_possible': questions_count * 10,  # Assuming 10 points per question
                'module_id': str(module.id),  # Add module reference
                'module_title': module.title,  # Add module title
                'is_unlocked': True
            })
    
    return Response(response_data)


@api_view(['GET'])
@csrf_exempt
def trainee_convert_ppt(request, module_id):
    """Convert/serve presentation file as PDF"""
    from django.http import FileResponse, HttpResponse, JsonResponse
    from django.conf import settings
    import os
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        module = Unit.objects.get(id=module_id)
    except Unit.DoesNotExist:
        return JsonResponse({'error': 'Module not found'}, status=404)
    
    # Get presentation details
    if module.module_type == 'presentation' and hasattr(module, 'presentation_details'):
        ppt = module.presentation_details
        if ppt and ppt.file_url:
            # Extract file path from URL
            # URL format: http://localhost:8000/media/pdfs/filename.pdf
            file_url = ppt.file_url
            
            # If it's already a PDF, just serve it
            if 'pdfs/' in file_url:
                # Extract the relative path after /media/
                path_parts = file_url.split('/media/', 1)
                if len(path_parts) > 1:
                    relative_path = path_parts[1]
                    full_path = os.path.join(settings.MEDIA_ROOT, relative_path)
                    
                    if os.path.exists(full_path):
                        try:
                            with open(full_path, 'rb') as pdf_file:
                                response = HttpResponse(pdf_file.read(), content_type='application/pdf')
                                response['Content-Disposition'] = f'inline; filename="{os.path.basename(full_path)}"'
                                return response
                        except Exception as e:
                            logger.error(f'Error reading PDF file: {str(e)}')
                            return JsonResponse({'error': f'Error reading file: {str(e)}'}, status=500)
                    else:
                        logger.error(f'File not found: {full_path}')
                        return JsonResponse({'error': 'File not found on server'}, status=404)
    
    return JsonResponse({'error': 'No presentation file found'}, status=404)


@api_view(['GET'])
@permission_classes([AllowAny])
def trainee_quiz_status(request, quiz_id):
    """Check quiz attempt status for trainee"""
    from admin.models import UserProfile
    from django.utils import timezone
    import logging
    logger = logging.getLogger(__name__)
    
    # Get user_id from query params or localStorage
    user_id = request.query_params.get('user_id')
    if not user_id:
        return Response({'error': 'User ID required'}, status=400)
    
    try:
        user = Profile.objects.get(id=user_id)
        quiz = Quiz.objects.get(id=quiz_id)
        
        # Get all attempts for this user and quiz
        attempts = QuizAttempt.objects.filter(
            user=user,
            quiz=quiz
        ).order_by('-started_at')
        
        attempts_count = attempts.count()
        attempts_remaining = max(0, quiz.attempts_allowed - attempts_count)
        
        # Get latest attempt details
        latest_attempt = None
        if attempts.exists():
            latest = attempts.first()
            latest_attempt = {
                'id': str(latest.id),
                'score': latest.score,
                'passed': latest.passed,
                'started_at': latest.started_at.isoformat() if latest.started_at else None,
                'completed_at': latest.completed_at.isoformat() if latest.completed_at else None
            }
        
        return Response({
            'quiz_id': str(quiz.id),
            'attempts_count': attempts_count,
            'attempts_allowed': quiz.attempts_allowed,
            'attempts_remaining': attempts_remaining,
            'can_attempt': attempts_remaining > 0,
            'latest_attempt': latest_attempt,
            'passing_score': quiz.passing_score
        })
        
    except Profile.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)
    except Quiz.DoesNotExist:
        return Response({'error': 'Quiz not found'}, status=404)


@api_view(['POST'])
@permission_classes([AllowAny])
def trainee_quiz_start(request, quiz_id):
    """Start a new quiz attempt"""
    from admin.models import UserProfile
    from django.utils import timezone
    import logging
    logger = logging.getLogger(__name__)
    
    # Get user_id from query params or request body
    user_id = request.query_params.get('user_id') or request.data.get('user_id')
    if not user_id:
        return Response({'error': 'User ID required'}, status=400)
    
    try:
        user = Profile.objects.get(id=user_id)
        quiz = Quiz.objects.get(id=quiz_id)
        
        # Check attempts remaining
        attempts_count = QuizAttempt.objects.filter(user=user, quiz=quiz).count()
        if attempts_count >= quiz.attempts_allowed:
            return Response({
                'error': 'No attempts remaining',
                'attempts_count': attempts_count,
                'attempts_allowed': quiz.attempts_allowed
            }, status=400)
        
        # Create new attempt
        attempt = QuizAttempt.objects.create(
            quiz=quiz,
            user=user,
            started_at=timezone.now()
        )
        
        # Get quiz questions
        questions = quiz.questions.all().order_by('order')
        questions_data = []
        for q in questions:
            questions_data.append({
                'id': str(q.id),
                'question_id': str(q.id),  # Add for frontend compatibility
                'type': q.type,
                'text': q.text,
                'options': q.options,
                'points': q.points,
                'order': q.order
            })
        
        return Response({
            'attempt_id': str(attempt.id),
            'quiz_id': str(quiz.id),
            'started_at': attempt.started_at.isoformat(),
            'time_limit': quiz.time_limit,
            'questions': questions_data,
            'total_questions': len(questions_data)
        })
        
    except Profile.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)
    except Quiz.DoesNotExist:
        return Response({'error': 'Quiz not found'}, status=404)


@api_view(['POST'])
@permission_classes([AllowAny])
def trainee_quiz_submit(request, attempt_id):
    """Submit quiz answers and calculate score"""
    from admin.models import UserProfile
    from django.utils import timezone
    import logging
    logger = logging.getLogger(__name__)
    
    # Get user_id from query params or request body
    user_id = request.query_params.get('user_id') or request.data.get('user_id')
    if not user_id:
        return Response({'error': 'User ID required'}, status=400)
    
    try:
        user = Profile.objects.get(id=user_id)
        attempt = QuizAttempt.objects.get(id=attempt_id, user=user)
        quiz = attempt.quiz
        
        # Get submitted answers
        answers = request.data.get('answers', {})
        confidence_scores = request.data.get('confidence', {})
        
        if not answers:
            return Response({'error': 'No answers provided'}, status=400)
        
        # Calculate score
        questions = quiz.questions.all()
        total_points = 0
        earned_points = 0
        correct_count = 0
        answer_details = []
        
        for question in questions:
            q_id = str(question.id)
            total_points += question.points or 1
            
            # Get user answer - handle both string and object formats
            user_answer_raw = answers.get(q_id, '')
            
            # Frontend may send {answer: "value", confidence: 100} or just "value"
            if isinstance(user_answer_raw, dict):
                user_answer = user_answer_raw.get('answer', '')
                confidence = user_answer_raw.get('confidence', confidence_scores.get(q_id, 0))
            else:
                user_answer = user_answer_raw
                confidence = confidence_scores.get(q_id, 0)
            
            correct_answer = question.correct_answer
            
            # Get the actual correct answer text from options
            # correct_answer is stored as an index (0, 1, 2, etc)
            options = question.options if isinstance(question.options, list) else []
            correct_answer_text = None
            
            if isinstance(correct_answer, int) and 0 <= correct_answer < len(options):
                # correct_answer is an index - get the text from options
                correct_answer_text = str(options[correct_answer])
            else:
                # correct_answer is already text
                correct_answer_text = str(correct_answer)
            
            # Check if answer is correct
            is_correct = False
            user_answer_str = str(user_answer).strip().lower()
            correct_answer_lower = correct_answer_text.strip().lower()
            
            if question.type == 'multiple_choice' or question.type == 'true_false':
                is_correct = user_answer_str == correct_answer_lower
            elif question.type == 'multiple_answer':
                # For multiple answer, compare as lists
                user_ans_set = set(user_answer) if isinstance(user_answer, list) else {user_answer}
                correct_ans_set = set(correct_answer) if isinstance(correct_answer, list) else {correct_answer}
                is_correct = user_ans_set == correct_ans_set
            else:
                # For other types, do string comparison
                is_correct = user_answer_str == correct_answer_lower
            
            if is_correct:
                earned_points += question.points or 1
                correct_count += 1
            
            answer_details.append({
                'question_id': q_id,
                'question_text': question.text,
                'user_answer': user_answer,
                'correct_answer': correct_answer_text,
                'is_correct': is_correct,
                'points': question.points or 1,
                'confidence': confidence
            })
        
        # Calculate percentage score
        score_percentage = int((earned_points / total_points * 100)) if total_points > 0 else 0
        passed = score_percentage >= quiz.passing_score
        
        # Update attempt
        attempt.score = score_percentage
        attempt.passed = passed
        attempt.answers = {
            'submitted_answers': answers,
            'confidence_scores': confidence_scores,
            'answer_details': answer_details
        }
        attempt.completed_at = timezone.now()
        attempt.save()
        
        # Check attempts remaining
        attempts_used = QuizAttempt.objects.filter(user=user, quiz=quiz).count()
        attempts_remaining = quiz.attempts_allowed - attempts_used
        
        return Response({
            'success': True,
            'attempt_id': str(attempt.id),
            'score': score_percentage,
            'passed': passed,
            'correct_count': correct_count,
            'total_questions': questions.count(),
            'passing_score': quiz.passing_score,
            'attempts_remaining': attempts_remaining,
            'attempts_exhausted': attempts_remaining <= 0,
            'max_attempts': quiz.attempts_allowed,
            'show_correct_answers': quiz.show_answers,
            'answers': answer_details if quiz.show_answers else None,
            'completed_at': attempt.completed_at.isoformat()
        })
        
    except Profile.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)
    except QuizAttempt.DoesNotExist:
        return Response({'error': 'Quiz attempt not found'}, status=404)


@api_view(['POST'])
@permission_classes([AllowAny])
def trainee_progress_update(request, course_id):
    """Update course/module progress for trainee"""
    from admin.models import UserProfile
    from django.utils import timezone
    import logging
    logger = logging.getLogger(__name__)
    
    # Get user_id from query params or request body
    user_id = request.query_params.get('user_id') or request.data.get('user_id')
    if not user_id:
        return Response({'error': 'User ID required'}, status=400)
    
    try:
        user = Profile.objects.get(id=user_id)
        
        # Get data from request
        content_id = request.data.get('content_id')
        module_id = request.data.get('module_id')
        progress_percentage = request.data.get('progress', 0)
        completed = request.data.get('completed', False)
        
        if not module_id:
            return Response({'error': 'Module ID required'}, status=400)
        
        # Get or create unit progress
        unit = Unit.objects.get(id=module_id)
        unit_progress, created = UnitProgress.objects.get_or_create(
            user=user,
            unit=unit,
            defaults={
                'completion_percentage': 0,
                'is_completed': False,
                'time_spent_minutes': 0
            }
        )
        
        # Update progress
        if completed:
            unit_progress.is_completed = True
            unit_progress.completion_percentage = 100
            unit_progress.completed_at = timezone.now()
        else:
            unit_progress.completion_percentage = min(100, progress_percentage)
        
        unit_progress.save()
        
        # Update course enrollment progress
        try:
            enrollment = Enrollment.objects.get(user=user, course=unit.course)
            
            # Calculate overall course progress
            total_units = Unit.objects.filter(course=unit.course).count()
            completed_units = UnitProgress.objects.filter(
                user=user,
                unit__course=unit.course,
                is_completed=True
            ).count()
            
            if total_units > 0:
                enrollment.progress = int((completed_units / total_units) * 100)
                
                # Update status
                if enrollment.progress == 100:
                    enrollment.status = 'completed'
                    enrollment.completed_at = timezone.now()
                elif enrollment.progress > 0:
                    enrollment.status = 'in_progress'
                
                enrollment.save()
        except Enrollment.DoesNotExist:
            pass
        
        return Response({
            'success': True,
            'module_id': str(unit.id),
            'module_progress': unit_progress.completion_percentage,
            'module_completed': unit_progress.is_completed,
            'course_progress': enrollment.progress if 'enrollment' in locals() else 0
        })
        
    except Profile.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)
    except Unit.DoesNotExist:
        return Response({'error': 'Module not found'}, status=404)


@api_view(['GET'])
@permission_classes([AllowAny])
def trainee_leaderboard(request):
    """Get leaderboard standings and current user's rank"""
    from django.db.models import Sum, Count, Q, F, Value
    from django.db.models.functions import Coalesce
    from django.utils import timezone
    
    user_id = request.query_params.get('user_id')
    
    try:
        # Get all trainees with their stats
        # Use Coalesce to treat NULL as 0 for proper sorting
        trainees = Profile.objects.filter(primary_role='trainee').annotate(
            total_points=Coalesce(Sum('quiz_attempts__score', filter=Q(quiz_attempts__passed=True)), Value(0)),
            courses_completed=Count('enrollments', filter=Q(enrollments__status='completed')),
            quizzes_passed=Count('quiz_attempts', filter=Q(quiz_attempts__passed=True))
        ).order_by('-total_points', '-courses_completed')
        
        leaderboard = []
        user_rank = None
        user_points = 0
        
        for idx, trainee in enumerate(trainees, start=1):
            points = trainee.total_points or 0
            entry = {
                'rank': idx,
                'user_id': str(trainee.id),
                'name': f"{trainee.first_name} {trainee.last_name}".strip() or trainee.email,
                'email': trainee.email,
                'points': points,
                'courses_completed': trainee.courses_completed or 0,
                'badges': trainee.quizzes_passed or 0,
                'completion_rate': 0,
                'is_current_user': str(trainee.id) == user_id
            }
            
            # Calculate completion rate
            total_enrolled = Enrollment.objects.filter(user=trainee).count()
            if total_enrolled > 0:
                completed_count = Enrollment.objects.filter(user=trainee, status='completed').count()
                entry['completion_rate'] = int((completed_count / total_enrolled) * 100)
            
            leaderboard.append(entry)
            
            if str(trainee.id) == user_id:
                user_rank = idx
                user_points = points
        
        return Response({
            'leaderboard': leaderboard[:50],  # Top 50
            'user_rank': user_rank,
            'user_points': user_points
        })
        
    except Exception as e:
        return Response({
            'error': str(e),
            'leaderboard': [],
            'user_rank': None,
            'user_points': 0
        }, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def trainee_tests(request):
    """Get all tests/quizzes for trainee"""
    from django.utils import timezone
    
    # Get user_id from URL params or from localStorage/session on frontend
    # Frontend should pass user_id in query params
    user_id = request.query_params.get('user_id')
    if not user_id:
        # Try to get from session or lms_user if available
        user_id = request.GET.get('user_id')
    if not user_id:
        return Response({'error': 'User ID required'}, status=400)
    
    try:
        user = Profile.objects.get(id=user_id)
        
        # Get all quizzes from enrolled courses
        enrolled_courses = Enrollment.objects.filter(user=user).values_list('course_id', flat=True)
        quizzes = Quiz.objects.filter(unit__course_id__in=enrolled_courses).select_related('unit', 'unit__course')
        
        tests_list = []
        for quiz in quizzes:
            # Check if user has attempted this quiz
            attempts = QuizAttempt.objects.filter(user=user, quiz=quiz).order_by('-started_at')
            latest_attempt = attempts.first()
            
            status = 'pending'
            score = None
            completed_date = None
            feedback = None
            
            if latest_attempt:
                if latest_attempt.completed_at:
                    status = 'completed'
                    score = latest_attempt.score
                    completed_date = latest_attempt.completed_at.isoformat()
                    if latest_attempt.passed:
                        feedback = 'Great job! You passed the quiz.'
                    else:
                        feedback = 'Keep practicing and try again!'
                else:
                    status = 'in_progress'
            
            # Get course through unit
            course_title = 'Unknown Course'
            try:
                if hasattr(quiz, 'unit') and quiz.unit and hasattr(quiz.unit, 'course') and quiz.unit.course:
                    course_title = quiz.unit.course.title
            except:
                pass
            
            # Quiz name is actually in the unit
            quiz_name = quiz.unit.title if quiz.unit else f"Quiz {quiz.id}"
            
            tests_list.append({
                'id': str(quiz.id),
                'test_id': str(quiz.id),
                'title': quiz_name,
                'name': quiz_name,
                'course_name': course_title,
                'due_date': None,
                'deadline': None,
                'status': status,
                'duration_minutes': quiz.time_limit,
                'duration': quiz.time_limit,
                'total_questions': quiz.questions.count(),
                'question_count': quiz.questions.count(),
                'passing_score': quiz.passing_score,
                'pass_score': quiz.passing_score,
                'score': score,
                'completed_date': completed_date,
                'submission_date': completed_date,
                'feedback': feedback,
                'attempts_used': attempts.count(),
                'attempts_allowed': quiz.attempts_allowed
            })
        
        return Response(tests_list)
        
    except Profile.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def trainee_assignments(request):
    """Get all assignments for trainee"""
    from django.utils import timezone
    
    user_id = request.query_params.get('user_id') or request.GET.get('user_id')
    if not user_id:
        return Response({'error': 'User ID required'}, status=400)
    
    try:
        user = Profile.objects.get(id=user_id)
        
        # For now, return empty list
        # In future, implement actual Assignment model
        assignments_list = []
        
        return Response(assignments_list)
        
    except Profile.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def trainee_progress_stats(request):
    """Get detailed progress statistics for trainee"""
    from django.db.models import Sum, Count, Q
    from django.utils import timezone
    
    user_id = request.query_params.get('user_id')
    if not user_id:
        return Response({'error': 'User ID required'}, status=400)
    
    try:
        user = Profile.objects.get(id=user_id)
        
        # Calculate stats
        total_points = QuizAttempt.objects.filter(
            user=user, 
            passed=True
        ).aggregate(total=Sum('score'))['total'] or 0
        
        modules_completed = UnitProgress.objects.filter(
            user=user,
            is_completed=True
        ).count()
        
        assessments_completed = QuizAttempt.objects.filter(
            user=user,
            completed_at__isnull=False
        ).count()
        
        badges_earned = QuizAttempt.objects.filter(
            user=user,
            passed=True,
            score__gte=90
        ).count()
        
        courses_completed = Enrollment.objects.filter(
            user=user,
            status='completed'
        ).count()
        
        # Get recent activities
        activities = []
        
        # Add quiz attempts as activities
        quiz_attempts = QuizAttempt.objects.filter(
            user=user,
            completed_at__isnull=False
        ).select_related('quiz', 'quiz__unit').order_by('-completed_at')[:20]
        
        for attempt in quiz_attempts:
            # Get quiz name and course through unit
            quiz_name = 'Quiz'
            course_title = 'Unknown'
            try:
                if hasattr(attempt.quiz, 'unit') and attempt.quiz.unit:
                    quiz_name = attempt.quiz.unit.title
                    if hasattr(attempt.quiz.unit, 'course') and attempt.quiz.unit.course:
                        course_title = attempt.quiz.unit.course.title
            except:
                pass
            
            activities.append({
                'id': str(attempt.id),
                'type': 'assessment',
                'activity': quiz_name,
                'course': course_title,
                'pointsEarned': attempt.score if attempt.passed else 0,
                'date': attempt.completed_at.isoformat()
            })
        
        # Add completed modules as activities
        completed_modules = UnitProgress.objects.filter(
            user=user,
            is_completed=True,
            completed_at__isnull=False
        ).select_related('unit').order_by('-completed_at')[:20]
        
        for progress in completed_modules:
            # Get unit first then access course through it
            unit = progress.unit
            course_title = 'Unknown'
            try:
                if hasattr(unit, 'course') and unit.course:
                    course_title = unit.course.title
            except:
                pass
            
            activities.append({
                'id': str(progress.id),
                'type': 'module',
                'activity': f"Completed {unit.title}",
                'course': course_title,
                'pointsEarned': 10,  # Default points for completing a module
                'date': progress.completed_at.isoformat()
            })
        
        # Sort activities by date
        activities.sort(key=lambda x: x['date'], reverse=True)
        
        return Response({
            'stats': {
                'totalPoints': total_points,
                'modulesCompleted': modules_completed,
                'assessmentsCompleted': assessments_completed,
                'badgesEarned': badges_earned,
                'coursesCompleted': courses_completed
            },
            'activities': activities[:20]  # Return top 20 most recent
        })
        
    except Profile.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def trainee_history(request):
    """Get consolidated learning history for trainee"""
    from django.utils import timezone
    
    user_id = request.query_params.get('user_id')
    if not user_id:
        return Response({'error': 'User ID required'}, status=400)
    
    try:
        user = Profile.objects.get(id=user_id)
        
        history = []
        
        # Add quiz attempts to history
        quiz_attempts = QuizAttempt.objects.filter(
            user=user,
            completed_at__isnull=False
        ).select_related('quiz', 'quiz__unit').order_by('-completed_at')
        
        for attempt in quiz_attempts:
            # Get quiz name and course through unit
            quiz_name = 'Quiz'
            course_title = 'Unknown'
            try:
                if hasattr(attempt.quiz, 'unit') and attempt.quiz.unit:
                    quiz_name = attempt.quiz.unit.title
                    if hasattr(attempt.quiz.unit, 'course') and attempt.quiz.unit.course:
                        course_title = attempt.quiz.unit.course.title
            except:
                pass
            
            history.append({
                'type': 'test',
                'title': quiz_name,
                'course': course_title,
                'score': attempt.score,
                'points_earned': attempt.score if attempt.passed else 0,
                'status': 'completed',
                'passed': attempt.passed or False,
                'completed_at': attempt.completed_at.isoformat(),
                'submitted_at': attempt.completed_at.isoformat()
            })
        
        # Add completed modules to history
        completed_modules = UnitProgress.objects.filter(
            user=user,
            is_completed=True,
            completed_at__isnull=False
        ).select_related('unit').order_by('-completed_at')
        
        for progress in completed_modules:
            unit = progress.unit
            course_title = 'Unknown'
            try:
                if hasattr(unit, 'course') and unit.course:
                    course_title = unit.course.title
            except:
                pass
            
            history.append({
                'type': 'module',
                'title': unit.title,
                'course': course_title,
                'score': None,
                'points_earned': 10,
                'status': 'completed',
                'passed': True,
                'completed_at': progress.completed_at.isoformat(),
                'submitted_at': progress.completed_at.isoformat()
            })
        
        # Sort by date
        history.sort(key=lambda x: x['completed_at'], reverse=True)
        
        return Response({'history': history})
        
    except Profile.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def dashboard_stats(request):
    """Dashboard statistics - returns different data based on user role"""
    from admin.models import UserProfile
    from django.db.models import Q, Count, Sum
    import logging
    logger = logging.getLogger(__name__)
    
    # Determine user profile
    user_profile = None
    if request.user and request.user.is_authenticated:
        try:
            # Try to find linked UserProfile
            user_id = request.user.username.replace('user_', '')
            logger.info(f"Trying to find UserProfile with ID: {user_id}")
            user_profile = UserProfile.objects.get(id=user_id)
            logger.info(f"Found UserProfile: {user_profile.email}, role: {user_profile.role}")
        except Exception as e:
            logger.error(f"Error finding UserProfile: {e}")
            pass
    
    # Fallback: Check for user_id query parameter (for frontend compatibility)
    if not user_profile:
        user_id_param = request.query_params.get('user_id') or request.GET.get('user_id')
        if user_id_param:
            try:
                logger.info(f"Looking up user by query param: {user_id_param}")
                user_profile = UserProfile.objects.get(id=user_id_param)
                logger.info(f"Found user by query param: {user_profile.email}, role: {user_profile.role}")
            except UserProfile.DoesNotExist:
                logger.error(f"User with ID {user_id_param} not found")
            except Exception as e:
                logger.error(f"Error finding user by query param: {e}")
    
    if not user_profile:
        logger.info(f"No user profile found - user not authenticated and no valid user_id param")
    
    # If no authenticated user or trainee role, return trainee dashboard data
    if not user_profile or user_profile.role in ['trainee', 'learner']:
        return trainee_dashboard_stats(request, user_profile)
    
    # Otherwise return trainer dashboard
    return trainer_dashboard_stats(request, user_profile)


def trainee_dashboard_stats(request, user_profile):
    """Trainee/Learner dashboard statistics"""
    from admin.models import UserProfile
    
    # If no user profile, return empty data
    if not user_profile:
        return Response({
            'stats': {
                'total_courses': 0,
                'active_courses': 0,
                'completed_courses': 0,
                'not_started_courses': 0
            },
            'courses': [],
            'rank': {
                'rank': 0,
                'points': 0,
                'total_active_hours': 0
            }
        })
    
    # Get user's enrollments
    enrollments = Enrollment.objects.filter(user_id=user_profile.id).select_related('course')

    
    # Get all enrolled courses
    enrolled_courses = Course.objects.filter(
        id__in=enrollments.values_list('course_id', flat=True)
    )
    
    # Calculate stats
    total_courses = enrolled_courses.count()
    
    # If no enrollments, show all published courses as available
    if total_courses == 0:
        available_courses = Course.objects.filter(status='published')
        courses_data = []
        for course in available_courses[:10]:  # Limit to 10
            courses_data.append({
                'id': str(course.id),
                'title': course.title,
                'description': course.description or '',
                'status': 'not_started',
                'progress': 0,
                'enrolled': False
            })
        
        return Response({
            'stats': {
                'total_courses': 0,
                'active_courses': 0,
                'completed_courses': 0,
                'not_started_courses': available_courses.count()
            },
            'courses': courses_data,
            'rank': {
                'rank': 0,
                'points': 0,
                'total_active_hours': 0
            }
        })
    
    # Count courses by status
    completed_count = enrollments.filter(status='completed').count()
    in_progress_count = enrollments.filter(status='in_progress').count()
    not_started_count = enrollments.filter(status='not_started').count()
    
    # Get course details with progress
    courses_data = []
    for enrollment in enrollments:
        course = enrollment.course
        
        # Calculate progress (percentage of completed units)
        total_units = Unit.objects.filter(course=course).count()
        completed_units = UnitProgress.objects.filter(
            user_id=user_profile.id,
            unit__course=course,
            is_completed=True
        ).count()
        
        progress = int((completed_units / total_units * 100)) if total_units > 0 else 0
        
        courses_data.append({
            'id': str(course.id),
            'title': course.title,
            'description': course.description or '',
            'status': enrollment.status,
            'progress': progress,
            'enrolled': True,
            'assigned_at': enrollment.assigned_at.isoformat() if enrollment.assigned_at else None
        })
    
    # Get user rank and points from leaderboard
    try:
        leaderboard_entry = Leaderboard.objects.get(user_id=user_profile.id)
        rank_data = {
            'rank': leaderboard_entry.rank or 0,
            'points': leaderboard_entry.points or 0,
            'total_active_hours': leaderboard_entry.total_active_hours or 0
        }
    except Leaderboard.DoesNotExist:
        rank_data = {
            'rank': 0,
            'points': 0,
            'total_active_hours': 0
        }
    
    return Response({
        'stats': {
            'total_courses': total_courses,
            'active_courses': in_progress_count,
            'completed_courses': completed_count,
            'not_started_courses': not_started_count
        },
        'courses': courses_data,
        'rank': rank_data
    })


def trainer_dashboard_stats(request, trainer_profile):
    """Trainer dashboard statistics - filtered by trainer"""
    # Get or create default trainer
    try:
        trainer = Profile.objects.get(email='trainer_user@example.com')
    except Profile.DoesNotExist:
        from django.contrib.auth.hashers import make_password
        trainer = Profile.objects.create(
            first_name='Trainer',
            last_name='User',
            email='trainer_user@example.com',
            password=make_password('trainer@123'),
            role='trainer'
        )
    
    # Get trainer's courses only
    trainer_courses = Course.objects.filter(created_by=trainer)
    total_courses = trainer_courses.count()
    
    # Count active learners (users with learner/trainee role who have enrollments)
    from django.db.models import Q
    active_learners = Profile.objects.filter(
        Q(primary_role='learner') | Q(primary_role='trainee'),
        enrollments__course__in=trainer_courses
    ).distinct().count()
    
    # Count total enrollments for trainer's courses
    total_enrollments = Enrollment.objects.filter(course__in=trainer_courses).count()
    
    # Calculate completion rate
    completed_enrollments = Enrollment.objects.filter(
        course__in=trainer_courses,
        status='completed'
    ).count()
    completion_rate = int((completed_enrollments / total_enrollments * 100)) if total_enrollments > 0 else 0
    
    # Return stats
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
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = Profile.objects.all()
        roles_param = self.request.query_params.get('role__in', None)
        if roles_param:
            roles = [role.strip() for role in roles_param.split(',')]
            queryset = queryset.filter(role__in=roles)
        return queryset

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    permission_classes = [AllowAny]
    serializer_class = CourseSerializer

    def _get_default_trainer(self):
        """Get or create default trainer profile"""
        try:
            trainer = Profile.objects.get(email='trainer_user@example.com')
        except Exception as e:
            # If Profile table doesn't exist or other error, just return None
            # and handle in get_queryset
            return None
        return trainer

    def get_serializer_class(self):
        """Use different serializer for nested creation vs standard operations"""
        if self.action == 'retrieve':
            return CourseDetailSerializer
        elif self.action == 'create':
            # Use nested serializer that handles units in single request
            return CourseNestedCreateSerializer
        return CourseSerializer

    def get_queryset(self):
        if self.action == 'assignable_learners':
            return Course.objects.all()
        
        # For list/create actions, return trainer's courses if trainer exists
        if self.action in ['list', 'create']:
            trainer = self._get_default_trainer()
            if trainer:
                qs = Course.objects.filter(created_by=trainer)
            else:
                qs = Course.objects.all()
        else:
            qs = Course.objects.all()
        
        if self.action == 'retrieve':
            # Don't use prefetch_related with complex nested relations to avoid errors
            # The serializer will handle fetching relationships
            qs = qs.prefetch_related('units')
        
        return qs

    def perform_create(self, serializer):
        """Create course with authenticated trainer as creator"""
        trainer = None
        
        # Try to get trainer from authenticated user via token
        if self.request.user and self.request.user.is_authenticated:
            try:
                trainer = Profile.objects.get(id=self.request.user.id)
            except:
                pass
        
        # Fall back to default trainer
        if not trainer:
            trainer = self._get_default_trainer()
        
        # Fall back to any available profile
        if not trainer:
            try:
                trainer = Profile.objects.first()
            except:
                pass
        
        # Save with trainer if available, otherwise raise error
        if trainer:
            serializer.save(created_by=trainer)
        else:
            raise serializers.ValidationError(
                "No trainer profile found. Please ensure at least one trainer profile exists in the system."
            )

    def destroy(self, request, *args, **kwargs):
        """Delete course"""
        try:
            from django.db import connection
            
            # Get the course_id from URL kwargs
            course_id = kwargs.get('pk')
            if not course_id:
                return Response({'error': 'Course ID required'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Delete all related data using raw SQL to match actual database schema
            with connection.cursor() as cursor:
                # Check if course exists first
                cursor.execute("SELECT course_id FROM courses WHERE course_id = %s", [course_id])
                if not cursor.fetchone():
                    return Response({'error': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)
                
                # Delete in order of dependencies - be careful to use actual column names
                # First, delete media_metadata that references units in this course
                cursor.execute("""
                    DELETE FROM media_metadata 
                    WHERE unit_id IN (SELECT module_id FROM modules WHERE course_id = %s)
                """, [course_id])
                
                # Module completions and sequencing
                cursor.execute("""
                    DELETE FROM module_completions 
                    WHERE module_id IN (SELECT module_id FROM modules WHERE course_id = %s)
                """, [course_id])
                
                cursor.execute("""
                    DELETE FROM module_sequencing 
                    WHERE module_id IN (SELECT module_id FROM modules WHERE course_id = %s)
                """, [course_id])
                
                # Delete quiz-related data BEFORE deleting modules
                # First delete test_responses (references test_attempts)
                cursor.execute("""
                    DELETE FROM test_responses 
                    WHERE attempt_id IN (
                        SELECT attempt_id FROM test_attempts 
                        WHERE test_id IN (
                            SELECT id FROM quizzes 
                            WHERE unit_id IN (SELECT module_id FROM modules WHERE course_id = %s)
                        )
                    )
                """, [course_id])
                
                # Delete quiz_attempts (references quizzes)
                cursor.execute("""
                    DELETE FROM quiz_attempts 
                    WHERE quiz_id IN (
                        SELECT id FROM quizzes 
                        WHERE unit_id IN (SELECT module_id FROM modules WHERE course_id = %s)
                    )
                """, [course_id])
                
                # Delete test_attempts (references quizzes)
                cursor.execute("""
                    DELETE FROM test_attempts 
                    WHERE test_id IN (
                        SELECT id FROM quizzes 
                        WHERE unit_id IN (SELECT module_id FROM modules WHERE course_id = %s)
                    )
                """, [course_id])
                
                # Delete questions (references quizzes)
                cursor.execute("""
                    DELETE FROM questions 
                    WHERE quiz_id IN (
                        SELECT id FROM quizzes 
                        WHERE unit_id IN (SELECT module_id FROM modules WHERE course_id = %s)
                    )
                """, [course_id])
                
                # Delete quizzes (references modules)
                cursor.execute("""
                    DELETE FROM quizzes 
                    WHERE unit_id IN (SELECT module_id FROM modules WHERE course_id = %s)
                """, [course_id])
                
                # Delete unit-specific records
                cursor.execute("""
                    DELETE FROM video_units 
                    WHERE unit_id IN (SELECT module_id FROM modules WHERE course_id = %s)
                """, [course_id])
                
                cursor.execute("""
                    DELETE FROM audio_units 
                    WHERE unit_id IN (SELECT module_id FROM modules WHERE course_id = %s)
                """, [course_id])
                
                cursor.execute("""
                    DELETE FROM presentation_units 
                    WHERE unit_id IN (SELECT module_id FROM modules WHERE course_id = %s)
                """, [course_id])
                
                cursor.execute("""
                    DELETE FROM text_units 
                    WHERE unit_id IN (SELECT module_id FROM modules WHERE course_id = %s)
                """, [course_id])
                
                cursor.execute("""
                    DELETE FROM page_units 
                    WHERE unit_id IN (SELECT module_id FROM modules WHERE course_id = %s)
                """, [course_id])
                
                # Now safe to delete modules
                cursor.execute("DELETE FROM modules WHERE course_id = %s", [course_id])
                
                # Delete enrollments
                cursor.execute("DELETE FROM enrollments WHERE course_id = %s", [course_id])
                
                # Finally delete the course
                cursor.execute("DELETE FROM courses WHERE course_id = %s", [course_id])
            
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Error deleting course: {str(e)}')
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def units(self, request, pk=None):
        """Get all units for a course"""
        course = self.get_object()
        units = course.units.all()
        serializer = UnitSerializer(units, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Publish a course"""
        course = self.get_object()
        course.status = 'published'
        course.save()
        return Response({'status': 'published'})

    @action(detail=True, methods=['get'])
    def assignable_learners(self, request, pk=None):
        """Get learners that can be assigned to this course"""
        try:
            course = Course.objects.get(pk=pk)
        except Course.DoesNotExist:
            return Response({'detail': 'Course not found'}, status=404)
        
        # Get all learners with trainee or learner primary role
        # Simply return those not already enrolled
        enrolled_ids = Enrollment.objects.filter(course=course).values_list('user_id', flat=True)
        
        learners = Profile.objects.filter(
            primary_role__in=['trainee', 'learner']
        ).exclude(
            id__in=enrolled_ids
        ).order_by('first_name', 'last_name')
        
        serializer = ProfileSerializer(learners, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def enrolled_learners(self, request, pk=None):
        """Get all learners enrolled in this course with enrollment details"""
        try:
            course = Course.objects.get(pk=pk)
        except Course.DoesNotExist:
            return Response({'detail': 'Course not found'}, status=404)
        
        # Get all enrollments with learner data
        enrollments = Enrollment.objects.filter(course=course).select_related('user')
        
        # Build response with enrollment ID and learner details
        result = []
        for enrollment in enrollments:
            learner = enrollment.user
            result.append({
                'id': str(enrollment.id),  # Enrollment ID for deletion
                'user_id': str(learner.id),
                'full_name': learner.full_name,
                'email': learner.email,
                'status': enrollment.status,
                'progress_percentage': enrollment.progress_percentage,
                'assigned_at': enrollment.assigned_at.isoformat() if enrollment.assigned_at else None,
                'started_at': enrollment.started_at.isoformat() if enrollment.started_at else None,
                'completed_at': enrollment.completed_at.isoformat() if enrollment.completed_at else None,
            })
        
        return Response(result)

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Duplicate a course"""
        try:
            user = request.user
            
            # Check if user is superuser
            if user.is_superuser:
                has_permission = True
            # For unauthenticated requests (mock tokens), allow the operation
            elif not user.is_authenticated:
                has_permission = True
            else:
                # Get Profile to check role
                # Django User username format: user_<uuid>
                try:
                    user_id = user.username.replace('user_', '')
                    profile = Profile.objects.get(id=user_id)
                    has_permission = profile.primary_role == 'trainer'
                except (Profile.DoesNotExist, ValueError):
                    has_permission = False
            
            if not has_permission:
                return Response({'detail': 'Trainer permission required'}, status=403)

            orig = self.get_object()
            
            # Use the same default trainer as the list method to ensure consistency
            created_by = self._get_default_trainer()
            
            if not created_by:
                return Response({'detail': 'No valid trainer user found for course creation'}, status=400)
            
            # Only copy fields that actually exist in Course model
            dup = Course.objects.create(
                title=f"{orig.title} (copy)",
                description=orig.description,
                about=orig.about,
                outcomes=getattr(orig, 'outcomes', ''),
                course_type=orig.course_type,
                status='draft',
                is_mandatory=orig.is_mandatory,
                estimated_duration_hours=orig.estimated_duration_hours,
                passing_criteria=orig.passing_criteria,
                created_by=created_by
            )
            
            # Copy units with their content
            for unit in orig.units.all():
                new_unit = Unit.objects.create(
                    course=dup,
                    module_type=unit.module_type,
                    title=unit.title,
                    description=unit.description,
                    sequence_order=unit.sequence_order,
                    is_mandatory=unit.is_mandatory,
                    estimated_duration_minutes=unit.estimated_duration_minutes
                )
                
                # Copy MediaMetadata entries for this unit
                # Since storage_path is unique, we need to handle duplicates carefully
                if hasattr(unit, 'media_files'):
                    for media_file in unit.media_files.all():
                        try:
                            # Try to create new MediaMetadata pointing to same file
                            # This may fail due to unique constraint on storage_path
                            # In that case, the unit-specific content (VideoUnit, PresentationUnit) will be used instead
                            MediaMetadata.objects.create(
                                unit=new_unit,
                                storage_path=media_file.storage_path,
                                file_name=media_file.file_name,
                                file_type=media_file.file_type,
                                file_size=media_file.file_size,
                                mime_type=media_file.mime_type,
                                duration=media_file.duration,
                                width=media_file.width,
                                height=media_file.height,
                                uploaded_by=media_file.uploaded_by
                            )
                        except IntegrityError:
                            # Storage path already exists, skip
                            # The unit-specific content tables will provide the content instead
                            pass
                        except Exception as e:
                            # Log but don't fail the whole duplication
                            print(f"Error copying media metadata: {str(e)}")
                            pass
                
                # Copy unit-specific content based on module type
                if unit.module_type == 'video' and hasattr(unit, 'video_details'):
                    try:
                        orig_video = unit.video_details
                        VideoUnit.objects.create(
                            unit=new_unit,
                            video_url=orig_video.video_url,
                            video_storage_path=orig_video.video_storage_path,
                            duration=orig_video.duration,
                            completion_type=orig_video.completion_type,
                            required_watch_percentage=orig_video.required_watch_percentage,
                            allow_skip=orig_video.allow_skip,
                            allow_rewind=orig_video.allow_rewind
                        )
                    except Exception as e:
                        print(f"Error copying video unit {unit.id}: {str(e)}")
                        pass
                
                elif unit.module_type == 'audio' and hasattr(unit, 'audio_details'):
                    try:
                        orig_audio = unit.audio_details
                        AudioUnit.objects.create(
                            unit=new_unit,
                            audio_url=orig_audio.audio_url,
                            audio_storage_path=orig_audio.audio_storage_path,
                            duration=orig_audio.duration
                        )
                    except Exception as e:
                        print(f"Error copying audio unit {unit.id}: {str(e)}")
                        pass
                
                elif unit.module_type == 'presentation' and hasattr(unit, 'presentation_details'):
                    try:
                        orig_pres = unit.presentation_details
                        PresentationUnit.objects.create(
                            unit=new_unit,
                            file_url=orig_pres.file_url,
                            file_storage_path=orig_pres.file_storage_path,
                            slide_count=orig_pres.slide_count
                        )
                    except Exception as e:
                        print(f"Error copying presentation unit {unit.id}: {str(e)}")
                        pass
                
                elif unit.module_type == 'text' and hasattr(unit, 'text_details'):
                    try:
                        orig_text = unit.text_details
                        TextUnit.objects.create(
                            unit=new_unit,
                            content=orig_text.content
                        )
                    except Exception as e:
                        print(f"Error copying text unit {unit.id}: {str(e)}")
                        pass
                
                elif unit.module_type == 'page' and hasattr(unit, 'page_details'):
                    try:
                        orig_page = unit.page_details
                        PageUnit.objects.create(
                            unit=new_unit,
                            content=orig_page.content
                        )
                    except Exception as e:
                        print(f"Error copying page unit {unit.id}: {str(e)}")
                        pass
                
                elif unit.module_type == 'quiz':
                    # Copy quizzes and their questions
                    for orig_quiz in unit.quizzes.all():
                        new_quiz = Quiz.objects.create(
                            unit=new_unit,
                            time_limit=orig_quiz.time_limit,
                            passing_score=orig_quiz.passing_score,
                            attempts_allowed=orig_quiz.attempts_allowed,
                            show_answers=orig_quiz.show_answers,
                            randomize_questions=orig_quiz.randomize_questions,
                            mandatory_completion=orig_quiz.mandatory_completion
                        )
                        
                        # Copy questions for this quiz
                        for orig_question in orig_quiz.questions.all():
                            Question.objects.create(
                                quiz=new_quiz,
                                type=orig_question.type,
                                text=orig_question.text,
                                options=orig_question.options,
                                correct_answer=orig_question.correct_answer,
                                points=orig_question.points,
                                order=orig_question.order
                            )
                
                elif unit.module_type == 'assignment' and hasattr(unit, 'assignment_details'):
                    try:
                        orig_assignment = unit.assignment_details
                        Assignment.objects.create(
                            unit=new_unit,
                            title=orig_assignment.title,
                            description=orig_assignment.description,
                            assignment_type=orig_assignment.assignment_type,
                            evaluation_method=orig_assignment.evaluation_method,
                            course_id=dup.id,
                            due_date=orig_assignment.due_date,
                            max_attempts=orig_assignment.max_attempts,
                            points_possible=orig_assignment.points_possible,
                            mandatory_completion=orig_assignment.mandatory_completion
                        )
                    except Exception as e:
                        print(f"Error copying assignment unit {unit.id}: {str(e)}")
                        pass
            
            return Response(CourseSerializer(dup).data, status=201)
        except Exception as e:
            import traceback
            error_msg = f"Error duplicating course: {str(e)}"
            print(f"Duplicate course error: {error_msg}")
            print(traceback.format_exc())
            return Response({'detail': error_msg, 'error': str(e)}, status=500)

    @action(detail=True, methods=['get', 'put'])
    def sequence(self, request, pk=None):
        """Get or set module sequence for a course"""
        course = self.get_object()
        
        if request.method == 'GET':
            units = course.units.all().order_by('sequence_order')
            return Response({
                'course_id': str(course.id),
                'modules': [{'id': str(u.id), 'sequence_order': u.sequence_order, 'title': u.title} for u in units]
            })
        
        elif request.method == 'PUT':
            module_ids = request.data.get('module_ids', [])
            for idx, mod_id in enumerate(module_ids):
                try:
                    unit = Unit.objects.get(id=mod_id, course=course)
                    unit.sequence_order = idx
                    unit.save()
                except Unit.DoesNotExist:
                    pass
            
            units = course.units.all().order_by('sequence_order')
            return Response({
                'course_id': str(course.id),
                'modules': [{'id': str(u.id), 'sequence_order': u.sequence_order, 'title': u.title} for u in units]
            })

    @action(detail=False, methods=['post'])
    def reorder_courses(self, request):
        """
        Reorder courses by their created_at or custom order field.
        
        Expected request body:
        {
            "courses": [
                {"id": "course-uuid-1", "order": 0},
                {"id": "course-uuid-2", "order": 1}
            ]
        }
        """
        courses_data = request.data.get('courses', [])
        
        if not courses_data:
            return Response(
                {'status': 'error', 'message': 'No courses provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                # For now, we'll just return success since courses don't have sequence_order
                # but we can add custom ordering logic later if needed
                return Response(
                    {
                        'status': 'success',
                        'count': len(courses_data),
                        'message': f'{len(courses_data)} courses processed'
                    },
                    status=status.HTTP_200_OK
                )
        except Exception as e:
            return Response(
                {'status': 'error', 'message': f'Failed to reorder courses: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """Assign course to learners or teams
        
        Handles assignment of courses to individual learners and/or entire teams.
        The assigned_by field is automatically populated by the get_or_create defaults.
        If the authenticated user is not a Profile instance, assigned_by will remain null,
        which is valid since the field is optional.
        """
        course = self.get_object()
        user_ids = request.data.get('user_ids', [])  # Individual learners
        team_ids = request.data.get('team_ids', [])
        
        print(f"\n=== ASSIGN ENDPOINT DEBUG ===")
        print(f"Course ID: {course.id}")
        print(f"User IDs: {user_ids}")
        print(f"Team IDs: {team_ids}")
        
        enrollments = []
        
        # Determine the assigned_by user - handle both Profile instances and AnonymousUser
        assigned_by = None
        user = request.user
        if user and hasattr(user, 'id') and str(user) != 'AnonymousUser':
            try:
                assigned_by = Profile.objects.get(id=user.id)
            except Profile.DoesNotExist:
                try:
                    assigned_by = Profile.objects.get(username=user.username)
                except (Profile.DoesNotExist, AttributeError):
                    assigned_by = None
        
        # Enroll individual learners
        for user_id in user_ids:
            try:
                learner = Profile.objects.get(id=user_id)
                # Build defaults dict conditionally - only include assigned_by if we have a valid user
                defaults = {'status': 'assigned'}
                if assigned_by:
                    defaults['assigned_by'] = assigned_by
                
                enrollment, created = Enrollment.objects.get_or_create(
                    course=course,
                    user=learner,
                    defaults=defaults
                )
                if created:
                    enrollments.append(enrollment)
                    print(f"Created enrollment for user {user_id}")
            except Profile.DoesNotExist:
                print(f"User {user_id} not found")
                pass
        
        # Enroll team members - use team_id for Team model lookup
        for team_id in team_ids:
            try:
                team = Team.objects.get(team_id=team_id)
                print(f"Found team: {team.team_id} ({team.team_name})")
                
                members = TeamMember.objects.filter(team=team).select_related('user')
                print(f"Team has {members.count()} members")
                
                for member in members:
                    # Build defaults dict conditionally - only include assigned_by if we have a valid user
                    defaults = {'status': 'assigned'}
                    if assigned_by:
                        defaults['assigned_by'] = assigned_by
                    
                    enrollment, created = Enrollment.objects.get_or_create(
                        course=course,
                        user=member.user,
                        defaults=defaults
                    )
                    if created:
                        enrollments.append(enrollment)
                        print(f"Created enrollment for team member {member.user.id} ({member.user.full_name})")
            except Team.DoesNotExist:
                print(f"Team {team_id} not found")
                pass
        
        print(f"Total enrollments created: {len(enrollments)}")
        print(f"=== END ASSIGN DEBUG ===\n")
        
        return Response({
            'assigned': len(enrollments),
            'message': f'Successfully assigned course to {len(enrollments)} learners'
        })


class UnitViewSet(viewsets.ModelViewSet):
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        """Use lightweight serializer for list and create views, full serializer for detail"""
        if self.action in ['list', 'create']:
            from .serializers import UnitListSerializer
            return UnitListSerializer
        return UnitSerializer

    def get_queryset(self):
        queryset = Unit.objects.all()
        course_id = self.request.query_params.get('course_id')
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        return queryset

    def perform_create(self, serializer):
        """Create unit with auto-assigned sequence_order and auto-create subtype record"""
        course_id = serializer.validated_data.get('course').id
        
        # Always calculate and assign next sequence order
        # Get the max sequence order for this course
        existing_units = Unit.objects.filter(course_id=course_id)
        if existing_units.exists():
            max_order = existing_units.aggregate(Max('sequence_order'))['sequence_order__max']
            next_order = (max_order if max_order is not None else -1) + 1
        else:
            next_order = 0
        
        # Override any provided sequence_order with the next auto-assigned value
        serializer.validated_data['sequence_order'] = next_order
        
        unit = serializer.save()
        self._create_subtype(unit)

    def _create_subtype(self, unit):
        """Auto-create subtype record based on module_type"""
        try:
            if unit.module_type == 'video':
                VideoUnit.objects.get_or_create(unit=unit)
            elif unit.module_type == 'audio':
                AudioUnit.objects.get_or_create(unit=unit)
            elif unit.module_type == 'presentation':
                PresentationUnit.objects.get_or_create(unit=unit)
            elif unit.module_type == 'text':
                TextUnit.objects.get_or_create(unit=unit)
            elif unit.module_type == 'page':
                PageUnit.objects.get_or_create(unit=unit)
            elif unit.module_type == 'quiz':
                Quiz.objects.get_or_create(unit=unit)
            elif unit.module_type == 'assignment':
                Assignment.objects.get_or_create(unit=unit)
            elif unit.module_type == 'scorm':
                ScormPackage.objects.get_or_create(unit=unit)
            elif unit.module_type == 'survey':
                Survey.objects.get_or_create(unit=unit)
        except Exception as e:
            print(f"Error creating subtype: {e}")

    def update(self, request, *args, **kwargs):
        """Override update to handle PATCH requests without fetching problematic relationships"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Update fields directly without serializer to avoid relationship queries
        data = request.data
        
        # Update allowed fields directly on the model
        update_fields = ['title', 'description', 'sequence_order', 'order', 'is_mandatory', 'is_required', 'module_type', 'type']
        for field in update_fields:
            if field in data:
                # Handle field name aliases
                if field == 'order':
                    setattr(instance, 'sequence_order', data[field])
                elif field == 'type':
                    setattr(instance, 'module_type', data[field])
                elif field == 'is_required':
                    setattr(instance, 'is_mandatory', data[field])
                else:
                    setattr(instance, field, data[field])
        
        instance.save(update_fields=['title', 'description', 'sequence_order', 'is_mandatory', 'module_type', 'updated_at'])
        
        # Handle content details update (video_url, audio_url, text_content, etc.)
        # This allows frontend to send content fields to update the subtype record
        try:
            if instance.module_type == 'video' and hasattr(instance, 'video_details'):
                video_unit = instance.video_details
                if 'video_url' in data:
                    video_unit.video_url = data['video_url']
                if 'video_storage_path' in data:
                    video_unit.video_storage_path = data['video_storage_path']
                if 'duration' in data:
                    video_unit.duration = data['duration']
                video_unit.save()
            elif instance.module_type == 'audio' and hasattr(instance, 'audio_details'):
                audio_unit = instance.audio_details
                if 'audio_url' in data:
                    audio_unit.audio_url = data['audio_url']
                if 'audio_storage_path' in data:
                    audio_unit.audio_storage_path = data['audio_storage_path']
                if 'duration' in data:
                    audio_unit.duration = data['duration']
                audio_unit.save()
            elif instance.module_type == 'text' and hasattr(instance, 'text_details'):
                text_unit = instance.text_details
                if 'content' in data:
                    text_unit.content = data['content']
                text_unit.save()
            elif instance.module_type == 'presentation' and hasattr(instance, 'presentation_details'):
                pres_unit = instance.presentation_details
                if 'file_url' in data:
                    pres_unit.file_url = data['file_url']
                if 'file_storage_path' in data:
                    pres_unit.file_storage_path = data['file_storage_path']
                if 'slide_count' in data:
                    pres_unit.slide_count = data['slide_count']
                pres_unit.save()
            elif instance.module_type == 'page' and hasattr(instance, 'page_details'):
                page_unit = instance.page_details
                if 'content' in data:
                    page_unit.content = data['content']
                page_unit.save()
        except Exception as e:
            print(f"Error updating content details: {e}")
        
        # Return minimal response to avoid database query issues
        return Response({
            'id': str(instance.id),
            'course': str(instance.course_id),
            'module_type': instance.module_type,
            'type': instance.module_type,
            'title': instance.title,
            'description': instance.description,
            'sequence_order': instance.sequence_order,
            'order': instance.sequence_order,
            'is_mandatory': instance.is_mandatory,
            'is_required': instance.is_mandatory,
            'created_at': instance.created_at.isoformat(),
            'updated_at': instance.updated_at.isoformat()
        })

    def list(self, request, *args, **kwargs):
        """Override list to include content for each unit"""
        queryset = self.filter_queryset(self.get_queryset())
        units = queryset[:100]  # Limit to prevent huge responses
        
        result = []
        for unit in units:
            # Build response for each unit
            data = {
                'id': str(unit.id),
                'course': str(unit.course_id),
                'module_type': unit.module_type,
                'type': unit.module_type,
                'title': unit.title,
                'description': unit.description,
                'sequence_order': unit.sequence_order,
                'order': unit.sequence_order,
                'is_mandatory': unit.is_mandatory,
                'is_required': unit.is_mandatory,
                'created_at': unit.created_at.isoformat(),
                'updated_at': unit.updated_at.isoformat()
            }
            
            # Get media for this unit
            media_files = MediaMetadata.objects.filter(unit=unit)
            media_serializer = MediaMetadataSerializer(media_files, many=True)
            data['media'] = media_serializer.data
            
            # Add content details based on unit type
            try:
                if unit.module_type == 'video' and hasattr(unit, 'video_details'):
                    video_unit = unit.video_details
                    data['video_details'] = VideoUnitSerializer(video_unit).data
            except Exception as e:
                pass
            
            try:
                if unit.module_type == 'audio' and hasattr(unit, 'audio_details'):
                    audio_unit = unit.audio_details
                    data['audio_details'] = AudioUnitSerializer(audio_unit).data
            except Exception as e:
                pass
            
            try:
                if unit.module_type == 'presentation' and hasattr(unit, 'presentation_details'):
                    pres_unit = unit.presentation_details
                    data['presentation_details'] = PresentationUnitSerializer(pres_unit).data
            except Exception as e:
                pass
            
            try:
                if unit.module_type == 'text' and hasattr(unit, 'text_details'):
                    text_unit = unit.text_details
                    data['text_details'] = TextUnitSerializer(text_unit).data
            except Exception as e:
                pass
            
            try:
                if unit.module_type == 'page' and hasattr(unit, 'page_details'):
                    page_unit = unit.page_details
                    data['page_details'] = PageUnitSerializer(page_unit).data
            except Exception as e:
                pass
            
            try:
                if unit.module_type == 'quiz' and hasattr(unit, 'quiz_details'):
                    quiz = unit.quiz_details
                    data['quiz_details'] = QuizSerializer(quiz).data
            except Exception as e:
                pass
            
            try:
                if unit.module_type == 'assignment' and hasattr(unit, 'assignment_details'):
                    assignment = unit.assignment_details
                    data['assignment_details'] = AssignmentSerializer(assignment).data
            except Exception as e:
                pass
            
            result.append(data)
        
        return Response({
            'count': queryset.count(),
            'results': result
        })

    def retrieve(self, request, *args, **kwargs):
        """Override retrieve to return unit data with content details"""
        instance = self.get_object()
        
        # Build manual response with basic fields and content details
        data = {
            'id': str(instance.id),
            'course': str(instance.course_id),
            'module_type': instance.module_type,
            'type': instance.module_type,
            'title': instance.title,
            'description': instance.description,
            'sequence_order': instance.sequence_order,
            'order': instance.sequence_order,
            'is_mandatory': instance.is_mandatory,
            'is_required': instance.is_mandatory,
            'created_at': instance.created_at.isoformat(),
            'updated_at': instance.updated_at.isoformat()
        }
        
        # Get media files for this unit
        media_files = MediaMetadata.objects.filter(unit=instance)
        media_serializer = MediaMetadataSerializer(media_files, many=True)
        data['media'] = media_serializer.data
        
        # Add content details based on unit type
        try:
            if instance.module_type == 'video' and hasattr(instance, 'video_details'):
                video_unit = instance.video_details
                data['video_details'] = VideoUnitSerializer(video_unit).data
        except Exception as e:
            print(f"Error loading video_details: {e}")
        
        try:
            if instance.module_type == 'audio' and hasattr(instance, 'audio_details'):
                audio_unit = instance.audio_details
                data['audio_details'] = AudioUnitSerializer(audio_unit).data
        except Exception as e:
            print(f"Error loading audio_details: {e}")
        
        try:
            if instance.module_type == 'presentation' and hasattr(instance, 'presentation_details'):
                pres_unit = instance.presentation_details
                data['presentation_details'] = PresentationUnitSerializer(pres_unit).data
        except Exception as e:
            print(f"Error loading presentation_details: {e}")
        
        try:
            if instance.module_type == 'text' and hasattr(instance, 'text_details'):
                text_unit = instance.text_details
                data['text_details'] = TextUnitSerializer(text_unit).data
        except Exception as e:
            print(f"Error loading text_details: {e}")
        
        try:
            if instance.module_type == 'page' and hasattr(instance, 'page_details'):
                page_unit = instance.page_details
                data['page_details'] = PageUnitSerializer(page_unit).data
        except Exception as e:
            print(f"Error loading page_details: {e}")
        
        try:
            if instance.module_type == 'quiz' and hasattr(instance, 'quiz_details'):
                quiz = instance.quiz_details
                data['quiz_details'] = QuizSerializer(quiz).data
        except Exception as e:
            print(f"Error loading quiz_details: {e}")
        
        try:
            if instance.module_type == 'assignment' and hasattr(instance, 'assignment_details'):
                assignment = instance.assignment_details
                data['assignment_details'] = AssignmentSerializer(assignment).data
        except Exception as e:
            print(f"Error loading assignment_details: {e}")
        
        return Response(data)

    @action(detail=False, methods=['post'])
    def reorder(self, request):
        """
        Reorder units by their sequence_order.
        
        Expected request body:
        {
            "units": [
                {"id": "unit-uuid-1", "sequence_order": 0},
                {"id": "unit-uuid-2", "sequence_order": 1},
                {"id": "unit-uuid-3", "sequence_order": 2}
            ]
        }
        """
        units_data = request.data.get('units', [])
        
        if not units_data:
            return Response(
                {'status': 'error', 'message': 'No units provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                updated_count = 0
                for item in units_data:
                    unit_id = item.get('id')
                    sequence_order = item.get('sequence_order')
                    
                    if not unit_id or sequence_order is None:
                        continue
                    
                    Unit.objects.filter(id=unit_id).update(sequence_order=sequence_order)
                    updated_count += 1
                
                return Response(
                    {
                        'status': 'success',
                        'count': updated_count,
                        'message': f'{updated_count} units reordered successfully'
                    },
                    status=status.HTTP_200_OK
                )
        except Exception as e:
            return Response(
                {'status': 'error', 'message': f'Failed to reorder units: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

    def destroy(self, request, *args, **kwargs):
        """Override destroy to handle DELETE requests without triggering cascade delete issues"""
        from django.db import connection
        
        instance = self.get_object()
        instance_id = instance.id
        
        # Delete related records in the correct order to avoid foreign key constraint violations
        with connection.cursor() as cursor:
            try:
                # First, delete media_metadata records that reference this unit
                cursor.execute('DELETE FROM media_metadata WHERE unit_id = %s', [instance_id])
                
                # Then delete from all possible subtype tables using id (not unit_id)
                cursor.execute('DELETE FROM video_units WHERE id = %s', [instance_id])
                cursor.execute('DELETE FROM audio_units WHERE id = %s', [instance_id])
                cursor.execute('DELETE FROM presentation_units WHERE id = %s', [instance_id])
                cursor.execute('DELETE FROM text_units WHERE id = %s', [instance_id])
                cursor.execute('DELETE FROM page_units WHERE id = %s', [instance_id])
            except Exception as e:
                # Ignore errors if tables or columns don't exist
                pass
        
        # Delete the unit itself using the correct column name (module_id)
        with connection.cursor() as cursor:
            cursor.execute('DELETE FROM modules WHERE module_id = %s', [instance_id])
        
        # Return 204 No Content
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['get'])
    def media(self, request, pk=None):
        """Get all media files for a unit"""
        unit = self.get_object()
        media_files = MediaMetadata.objects.filter(unit=unit)
        serializer = MediaMetadataSerializer(media_files, many=True)
        return Response(serializer.data)


class VideoUnitViewSet(viewsets.ModelViewSet):
    queryset = VideoUnit.objects.all()
    serializer_class = VideoUnitSerializer
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_queryset(self):
        """Filter by unit_id if provided in query params"""
        queryset = super().get_queryset()
        unit_id = self.request.query_params.get('unit_id')
        if unit_id:
            queryset = queryset.filter(unit=unit_id)
        return queryset
    
    def create(self, request, *args, **kwargs):
        """Handle VideoUnit creation, updating if one already exists"""
        unit_id = request.data.get('unit')
        
        # Check if VideoUnit already exists for this unit
        if unit_id:
            try:
                existing = VideoUnit.objects.get(unit=unit_id)
                # Update existing instead of creating new
                serializer = self.get_serializer(existing, data=request.data, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            except VideoUnit.DoesNotExist:
                pass
        
        # Create new if doesn't exist
        return super().create(request, *args, **kwargs)


class AudioUnitViewSet(viewsets.ModelViewSet):
    queryset = AudioUnit.objects.all()
    serializer_class = AudioUnitSerializer
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_queryset(self):
        """Filter by unit_id if provided in query params"""
        queryset = super().get_queryset()
        unit_id = self.request.query_params.get('unit_id')
        if unit_id:
            queryset = queryset.filter(unit=unit_id)
        return queryset
    
    def create(self, request, *args, **kwargs):
        """Handle AudioUnit creation, updating if one already exists"""
        unit_id = request.data.get('unit')
        
        if unit_id:
            try:
                existing = AudioUnit.objects.get(unit=unit_id)
                serializer = self.get_serializer(existing, data=request.data, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            except AudioUnit.DoesNotExist:
                pass
        
        return super().create(request, *args, **kwargs)


class PresentationUnitViewSet(viewsets.ModelViewSet):
    queryset = PresentationUnit.objects.all()
    serializer_class = PresentationUnitSerializer
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_queryset(self):
        """Filter by unit_id if provided in query params"""
        queryset = super().get_queryset()
        unit_id = self.request.query_params.get('unit_id')
        if unit_id:
            queryset = queryset.filter(unit=unit_id)
        return queryset
    
    def create(self, request, *args, **kwargs):
        """Handle PresentationUnit creation, updating if one already exists"""
        unit_id = request.data.get('unit')
        
        if unit_id:
            try:
                existing = PresentationUnit.objects.get(unit=unit_id)
                serializer = self.get_serializer(existing, data=request.data, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            except PresentationUnit.DoesNotExist:
                pass
        
        return super().create(request, *args, **kwargs)

class TextUnitViewSet(viewsets.ModelViewSet):
    queryset = TextUnit.objects.all()
    serializer_class = TextUnitSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        """Filter by unit_id if provided in query params"""
        queryset = super().get_queryset()
        unit_id = self.request.query_params.get('unit_id')
        if unit_id:
            queryset = queryset.filter(unit=unit_id)
        return queryset
    
    def create(self, request, *args, **kwargs):
        """Handle TextUnit creation, updating if one already exists"""
        unit_id = request.data.get('unit')
        
        if unit_id:
            try:
                existing = TextUnit.objects.get(unit=unit_id)
                serializer = self.get_serializer(existing, data=request.data, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            except TextUnit.DoesNotExist:
                pass
        
        return super().create(request, *args, **kwargs)

class PageUnitViewSet(viewsets.ModelViewSet):
    queryset = PageUnit.objects.all()
    serializer_class = PageUnitSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        """Filter by unit_id if provided in query params"""
        queryset = super().get_queryset()
        unit_id = self.request.query_params.get('unit_id')
        if unit_id:
            queryset = queryset.filter(unit=unit_id)
        return queryset
    
    def create(self, request, *args, **kwargs):
        """Handle PageUnit creation, updating if one already exists"""
        unit_id = request.data.get('unit')
        
        if unit_id:
            try:
                existing = PageUnit.objects.get(unit=unit_id)
                serializer = self.get_serializer(existing, data=request.data, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            except PageUnit.DoesNotExist:
                pass
        
        return super().create(request, *args, **kwargs)

class QuizViewSet(viewsets.ModelViewSet):
    queryset = Quiz.objects.all()
    serializer_class = QuizSerializer
    permission_classes = [AllowAny]
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    
    def get_queryset(self):
        """
        Filter quizzes by unit_id query parameter.
        This ensures GET /api/quizzes/?unit_id=XXX only returns the quiz for that specific unit.
        """
        queryset = super().get_queryset()
        unit_id = self.request.query_params.get('unit_id')
        if unit_id:
            queryset = queryset.filter(unit_id=unit_id)
        return queryset
    
    def create(self, request, *args, **kwargs):
        """Handle Quiz creation, updating if one already exists"""
        import logging
        from django.db import transaction
        logger = logging.getLogger(__name__)
        
        # Validate unit_id is provided
        unit_id = request.data.get('unit')
        logger.info(f'QuizViewSet.create() called with unit_id={unit_id}')
        logger.info(f'Request data: {request.data}')
        
        if not unit_id:
            return Response(
                {'error': 'unit field is required for quiz creation'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if unit exists
        from trainer.models import Unit
        try:
            unit = Unit.objects.get(id=unit_id)
            logger.info(f'Found unit: {unit.id}')
        except Unit.DoesNotExist:
            return Response(
                {'error': f'Unit with ID {unit_id} does not exist'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Use transaction to ensure atomic save
        with transaction.atomic():
            # Check if quiz already exists for this unit
            try:
                existing = Quiz.objects.select_for_update().get(unit_id=unit_id)
                logger.info(f'Found existing quiz for unit: {existing.id}')
                serializer = self.get_serializer(existing, data=request.data, partial=True)
                if not serializer.is_valid():
                    logger.error(f'Serializer validation failed: {serializer.errors}')
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Quiz.DoesNotExist:
                logger.info(f'No existing quiz for unit {unit_id}, creating new one')
                pass
            
            # Create new quiz
            serializer = self.get_serializer(data=request.data)
            logger.info(f'Serializer initial data: {serializer.initial_data}')
            
            if not serializer.is_valid():
                logger.error(f'Serializer validation failed: {serializer.errors}')
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            logger.info('Serializer is valid, saving with unit...')
            # Explicitly set the unit before saving
            quiz_instance = serializer.save(unit=unit)
            logger.info(f'Quiz saved with ID: {quiz_instance.id}')
            
            # Verify it was saved and get it back
            saved_quiz = Quiz.objects.get(id=quiz_instance.id)
            logger.info(f'Verified quiz exists in database: {saved_quiz.id}')
            
            # Re-serialize the saved quiz
            response_serializer = self.get_serializer(saved_quiz)
            logger.info(f'Response serializer data: {response_serializer.data}')
            logger.info(f'Response serializer ID: {response_serializer.data.get("id")}')
            headers = self.get_success_headers(response_serializer.data)
            
            logger.info(f'Returning quiz response: {response_serializer.data}')
            return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    @action(detail=True, methods=['post'], parser_classes=(MultiPartParser, FormParser))
    def bulk_upload_questions(self, request, pk=None):
        """
        Bulk upload questions from CSV or JSON file.
        
        CSV Format:
        question_text,question_type,option_a,option_b,option_c,option_d,correct_answer,points
        "What is Django?","multiple_choice","Framework","Language","Database","IDE","Framework",1
        
        JSON Format:
        [
          {"question_text": "...", "question_type": "...", "options": [...], "correct_answer": "...", "points": 1}
        ]
        """
        import csv
        import json
        
        quiz = self.get_object()
        file = request.FILES.get('file')
        
        if not file:
            return Response(
                {'status': 'error', 'message': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            questions_data = []
            errors = []
            
            # Detect file type and parse
            if file.name.endswith('.csv'):
                # Parse CSV
                csv_file = file.read().decode('utf-8').splitlines()
                reader = csv.DictReader(csv_file)
                
                for row_num, row in enumerate(reader, 1):
                    try:
                        # Handle multiple choice options
                        options = []
                        for key in ['option_a', 'option_b', 'option_c', 'option_d']:
                            if row.get(key):
                                options.append(row.get(key).strip())
                        
                        question_data = {
                            'type': row.get('question_type', 'multiple_choice').strip(),
                            'text': row.get('question_text', '').strip(),
                            'options': options,
                            'correct_answer': row.get('correct_answer', '').strip(),
                            'points': int(row.get('points', 1))
                        }
                        
                        # Validate required fields
                        if not question_data['text']:
                            errors.append(f"Row {row_num}: 'question_text' is required")
                            continue
                        if not question_data['correct_answer']:
                            errors.append(f"Row {row_num}: 'correct_answer' is required")
                            continue
                        
                        questions_data.append(question_data)
                    except Exception as e:
                        errors.append(f"Row {row_num}: {str(e)}")
            
            elif file.name.endswith('.json'):
                # Parse JSON
                json_content = file.read().decode('utf-8')
                json_data = json.loads(json_content)
                
                for idx, item in enumerate(json_data, 1):
                    try:
                        question_data = {
                            'type': item.get('question_type', item.get('type', 'multiple_choice')),
                            'text': item.get('question_text', item.get('text', '')).strip(),
                            'options': item.get('options', []),
                            'correct_answer': item.get('correct_answer', '').strip(),
                            'points': int(item.get('points', 1))
                        }
                        
                        # Validate required fields
                        if not question_data['text']:
                            errors.append(f"Item {idx}: 'question_text' is required")
                            continue
                        if not question_data['correct_answer']:
                            errors.append(f"Item {idx}: 'correct_answer' is required")
                            continue
                        
                        questions_data.append(question_data)
                    except Exception as e:
                        errors.append(f"Item {idx}: {str(e)}")
            else:
                return Response(
                    {'status': 'error', 'message': 'File must be CSV or JSON'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # If there are validation errors, return them without importing
            if errors:
                return Response(
                    {'status': 'error', 'errors': errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create questions atomically
            with transaction.atomic():
                created_count = 0
                for question_data in questions_data:
                    try:
                        Question.objects.create(quiz=quiz, **question_data)
                        created_count += 1
                    except Exception as e:
                        raise Exception(f"Failed to create question: {str(e)}")
            
            return Response(
                {
                    'status': 'success',
                    'count': created_count,
                    'message': f'{created_count} questions imported successfully'
                },
                status=status.HTTP_200_OK
            )
        
        except Exception as e:
            return Response(
                {'status': 'error', 'message': f'Failed to process file: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

class QuestionViewSet(viewsets.ModelViewSet):
    serializer_class = QuestionSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        """Get questions, optionally filtered by quiz"""
        queryset = Question.objects.all()
        quiz_id = self.request.query_params.get('quiz', None)
        if quiz_id:
            queryset = queryset.filter(quiz_id=quiz_id)
        return queryset
    
    def create(self, request, *args, **kwargs):
        """Handle question creation with proper error handling"""
        import logging
        from django.db import transaction
        logger = logging.getLogger(__name__)
        
        try:
            # Validate that quiz exists
            quiz_id = request.data.get('quiz')
            logger.info(f'QuestionViewSet.create() called with quiz_id={quiz_id}')
            logger.info(f'Request data: {request.data}')
            
            if not quiz_id:
                return Response(
                    {'error': 'quiz field is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                from trainer.models import Quiz
                # Use select_for_update to ensure we get the latest data
                quiz = Quiz.objects.select_for_update().get(id=quiz_id)
                logger.info(f'Found quiz: {quiz.id}, unit: {quiz.unit_id}')
            except Quiz.DoesNotExist:
                logger.error(f'Quiz with ID {quiz_id} does not exist')
                return Response(
                    {'error': f'Quiz with ID {quiz_id} does not exist'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except Exception as e:
                logger.error(f'Error validating quiz: {str(e)}')
                return Response(
                    {'error': f'Invalid quiz ID format: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create question with transaction
            with transaction.atomic():
                result = super().create(request, *args, **kwargs)
                logger.info(f'Question created: {result.data}')
                return result
        except Exception as e:
            logger.error(f'Error in QuestionViewSet.create: {str(e)}', exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        """Handle Assignment creation, updating if one already exists"""
        unit_id = request.data.get('unit')
        
        if unit_id:
            try:
                existing = Assignment.objects.get(unit=unit_id)
                serializer = self.get_serializer(existing, data=request.data, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Assignment.DoesNotExist:
                pass
        
        return super().create(request, *args, **kwargs)

class ScormPackageViewSet(viewsets.ModelViewSet):
    queryset = ScormPackage.objects.all()
    serializer_class = ScormPackageSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        """Handle ScormPackage creation, updating if one already exists"""
        unit_id = request.data.get('unit')
        
        if unit_id:
            try:
                existing = ScormPackage.objects.get(unit=unit_id)
                serializer = self.get_serializer(existing, data=request.data, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            except ScormPackage.DoesNotExist:
                pass
        
        return super().create(request, *args, **kwargs)

class SurveyViewSet(viewsets.ModelViewSet):
    queryset = Survey.objects.all()
    serializer_class = SurveySerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        """Handle Survey creation, updating if one already exists"""
        unit_id = request.data.get('unit')
        
        if unit_id:
            try:
                existing = Survey.objects.get(unit=unit_id)
                serializer = self.get_serializer(existing, data=request.data, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Survey.DoesNotExist:
                pass
        
        return super().create(request, *args, **kwargs)

class EnrollmentViewSet(viewsets.ModelViewSet):
    queryset = Enrollment.objects.all()
    serializer_class = EnrollmentSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = Enrollment.objects.all()
        
        # Filter by course if provided in query params
        course_id = self.request.query_params.get('course')
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        
        # Filter by user if provided in query params
        user_id = self.request.query_params.get('user')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        return queryset
    
    def perform_create(self, serializer):
        """
        Auto-populate assigned_by with the authenticated user when creating enrollments.
        This ensures that enrollments are properly attributed to the user who assigned them,
        even when AllowAny permissions are used. The assigned_by field can remain null
        for unauthenticated requests, which is valid since it's an optional field.
        """
        # Extract assigned_by from request or use the authenticated user if available
        assigned_by = None
        user = self.request.user
        
        # Check if user is authenticated and is a Profile instance (not AnonymousUser)
        if user and hasattr(user, 'id') and str(user) != 'AnonymousUser':
            try:
                assigned_by = Profile.objects.get(id=user.id)
            except Profile.DoesNotExist:
                # If user exists in auth but not in Profile, try to find by username
                try:
                    assigned_by = Profile.objects.get(username=user.username)
                except (Profile.DoesNotExist, AttributeError):
                    assigned_by = None
        
        # Save with assigned_by if we found a valid profile, otherwise let it be null
        if assigned_by:
            serializer.save(assigned_by=assigned_by)
        else:
            serializer.save()

class UnitProgressViewSet(viewsets.ModelViewSet):
    queryset = UnitProgress.objects.all()
    serializer_class = UnitProgressSerializer
    permission_classes = [AllowAny]

class AssignmentSubmissionViewSet(viewsets.ModelViewSet):
    queryset = AssignmentSubmission.objects.all()
    serializer_class = AssignmentSubmissionSerializer
    permission_classes = [AllowAny]

class QuizAttemptViewSet(viewsets.ModelViewSet):
    queryset = QuizAttempt.objects.all()
    serializer_class = QuizAttemptSerializer
    permission_classes = [AllowAny]

class LeaderboardViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Leaderboard.objects.all()
    serializer_class = LeaderboardSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = Leaderboard.objects.all().order_by('-total_points', '-rank')
        course_id = self.request.query_params.get('course_id')
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        return queryset

    @action(detail=False, methods=['get'])
    def unread(self, request):
        """Get unread count for notifications"""
        unread_count = Notification.objects.filter(
            user=request.user,
            status='unread'
        ).count()
        return Response({'unread_count': unread_count})

# TeamLeaderboardViewSet removed - TeamLeaderboard model used same 'leaderboard' table as Leaderboard
# Use LeaderboardViewSet with team filtering instead

class MediaUploadView(APIView):
    """Dedicated endpoint for file uploads - avoids viewset routing conflicts"""
    permission_classes = [AllowAny]
    parser_classes = (MultiPartParser, FormParser)
    
    def post(self, request, *args, **kwargs):
        """
        Handle file upload and organize by type
        Files are saved to C:\LMS_uploads\{type}\{unit_id}_{timestamp}_{filename}
        """
        from django.core.files.storage import default_storage
        from django.core.files.base import ContentFile
        import os
        import time
        import uuid as uuid_lib
        
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'error': 'No file provided'}, status=400)
        
        # Determine file type from file extension
        file_ext = os.path.splitext(file_obj.name)[1].lower()
        
        file_type_map = {
            '.mp4': 'videos', '.avi': 'videos', '.mov': 'videos', '.mkv': 'videos', '.webm': 'videos',
            '.pdf': 'pdfs',
            '.ppt': 'ppts', '.pptx': 'ppts',
            '.doc': 'documents', '.docx': 'documents', '.txt': 'documents',
            '.jpg': 'images', '.jpeg': 'images', '.png': 'images', '.gif': 'images',
            '.mp3': 'audio', '.wav': 'audio', '.aac': 'audio',
            '.zip': 'general', '.rar': 'general', '.7z': 'general',
        }
        
        file_category = file_type_map.get(file_ext, 'general')
        
        # Get unit_id and create unique filename
        unit_id = request.data.get('unit_id', str(uuid_lib.uuid4())[:8])
        timestamp = int(time.time())
        base_name = os.path.splitext(file_obj.name)[0]
        
        # Create unique filename: {unit_id}_{timestamp}_{filename}{ext}
        unique_filename = f'{unit_id}_{timestamp}_{base_name}{file_ext}'
        
        # Save file to categorized folder
        file_path = f'{file_category}/{unique_filename}'
        saved_path = default_storage.save(file_path, ContentFile(file_obj.read()))
        
        # Build access URL
        media_url = f'/media/{saved_path}'
        
        # Create MediaMetadata record
        from django.contrib.auth.models import User
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Get profile - try to get from request user first, then default
            profile = None
            if request.user and request.user.is_authenticated:
                try:
                    profile = Profile.objects.get(user=request.user)
                except Profile.DoesNotExist:
                    profile = None
            
            # Fallback to first profile if not authenticated
            if not profile:
                profile = Profile.objects.first()
            
            if not profile:
                logger.error("No profile found to assign as uploaded_by")
                raise Exception("No profile available")
            
            # Find the unit if unit_id was provided
            unit = None
            unit_id_param = request.data.get('unit_id')
            if unit_id_param:
                try:
                    unit = Unit.objects.get(id=unit_id_param)
                except (Unit.DoesNotExist, ValueError) as e:
                    logger.warning(f"Unit not found for unit_id: {unit_id_param}")
            
            # Determine detailed file type
            file_type_detail = file_category
            if file_category == 'videos':
                file_type_detail = 'video'
            elif file_category == 'audio':
                file_type_detail = 'audio'
            elif file_category == 'ppts':
                file_type_detail = 'presentation'
            
            # Create the MediaMetadata record
            media_metadata = MediaMetadata.objects.create(
                storage_path=saved_path,
                file_name=file_obj.name,
                file_type=file_type_detail,
                file_size=file_obj.size,
                mime_type=file_obj.content_type or f'application/{file_ext.lstrip(".")}',
                unit=unit,
                uploaded_by=profile
            )
            logger.info(f"Created MediaMetadata: {media_metadata.id} for {file_obj.name}")
            
        except Exception as e:
            import traceback
            logger.error(f"Error creating MediaMetadata: {str(e)}\n{traceback.format_exc()}")
        
        return Response({
            'filename': file_obj.name,
            'path': saved_path,
            'url': media_url,
            'file_type': file_category,
            'size': file_obj.size
        }, status=201)


class MediaUploadViewSet(viewsets.ModelViewSet):
    queryset = MediaMetadata.objects.all()
    serializer_class = MediaMetadataSerializer
    permission_classes = [AllowAny]

class TeamViewSet(viewsets.ModelViewSet):
    serializer_class = TeamSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Team.objects.prefetch_related('members__user').all()

    @action(detail=False, methods=['get'])
    def available_for_assignment(self, request):
        """Get all teams available for course assignment"""
        # Don't filter by status - return all teams so they can be used for assignment
        teams = Team.objects.prefetch_related('members__user').all().order_by('team_name')
        
        # Debug logging
        import logging
        logger = logging.getLogger(__name__)
        for team in teams:
            logger.warning(f'Team {team.team_name}: members count = {team.members.count()}')
        
        serializer = TeamSerializer(teams, many=True)
        return Response(serializer.data)

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        """Show only current user's notifications"""
        if self.request.user.is_authenticated:
            try:
                # Get Profile from Django User
                profile = Profile.objects.get(id=self.request.user.username.replace('user_', ''))
                return Notification.objects.filter(user=profile).order_by('-created_at')
            except (Profile.DoesNotExist, ValueError):
                return Notification.objects.none()
        return Notification.objects.none()

    @action(detail=False, methods=['get'])
    def unread(self, request):
        """Get unread notifications count"""
        try:
            if not request.user or not request.user.is_authenticated:
                return Response({'unread_count': 0})
            
            # Get Profile from Django User
            try:
                profile = Profile.objects.get(id=request.user.username.replace('user_', ''))
            except (Profile.DoesNotExist, ValueError):
                return Response({'unread_count': 0})
            
            unread_count = Notification.objects.filter(
                user=profile,
                status='unread'
            ).count()
            return Response({'unread_count': unread_count})
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Error in unread notifications: {str(e)}')
            return Response({'unread_count': 0})

    @action(detail=False, methods=['get'])
    def list_unread(self, request):
        """Get list of unread notifications"""
        try:
            if not request.user or not request.user.is_authenticated:
                return Response({'results': []})
            
            limit = request.query_params.get('limit', 20)
            try:
                limit = int(limit)
            except (ValueError, TypeError):
                limit = 20
                
            notifications = Notification.objects.filter(
                user=request.user,
                status='unread'
            ).order_by('-created_at')[:limit]
            
            serializer = self.get_serializer(notifications, many=True)
            return Response({'results': serializer.data})
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Error in list_unread notifications: {str(e)}')
            return Response({'results': []})
        serializer = self.get_serializer(notifications, many=True)
        return Response({'results': serializer.data})

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark single notification as read"""
        notification = self.get_object()
        notification.mark_as_read()
        return Response({'status': 'marked as read'})

    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """Mark all notifications as read"""
        if not request.user or not request.user.is_authenticated:
            return Response({'status': 'authentication required'})
        
        Notification.objects.filter(user=request.user, status='unread').update(status='read')
        return Response({'status': 'all marked as read'})

    @action(detail=False, methods=['post'])
    def archive_all(self, request):
        """Archive all notifications"""
        if not request.user or not request.user.is_authenticated:
            return Response({'status': 'authentication required'})
        
        Notification.objects.filter(user=request.user).update(status='archived')
        return Response({'status': 'all archived'})


class ModuleSequencingViewSet(viewsets.ModelViewSet):
    """Manage module sequencing and prerequisites"""
    queryset = ModuleSequencing.objects.all()
    serializer_class = ModuleSequencingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter by course if provided"""
        queryset = ModuleSequencing.objects.all()
        course_id = self.request.query_params.get('course_id')
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        return queryset


# ModuleCompletionViewSet removed - ModuleCompletion model used same 'module_completions' table as UnitProgress
# Use UnitProgressViewSet with module filtering instead


class NoteViewSet(viewsets.ModelViewSet):
    """Manage user notes on modules"""
    queryset = Note.objects.all()
    serializer_class = NoteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Show only user's notes"""
        return Note.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """Automatically set user to current user"""
        serializer.save(user=self.request.user)


class RoleViewSet(viewsets.ModelViewSet):
    """Manage user roles"""
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAdminUser]


class UserRoleViewSet(viewsets.ModelViewSet):
    """Manage user role assignments"""
    queryset = UserRole.objects.all()
    serializer_class = UserRoleSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        """Filter by user if provided"""
        queryset = UserRole.objects.all()
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        return queryset