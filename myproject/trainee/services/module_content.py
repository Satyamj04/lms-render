"""
Module Content Views - Handling mixed content (videos, quizzes, resources, PDFs from MongoDB)
Trainee: View mixed content in sequence from both PostgreSQL and MongoDB
Trainer: Add/edit/delete quizzes and resources
Fetches content from both PostgreSQL (quizzes) and MongoDB (media files)
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Q
from trainee.models import (
    Module, Course, ModuleQuiz, ModuleQuizQuestion,
    LearningResource, ModuleQuizAttempt, Quiz, PresentationUnit
)
from admin.models import CourseAssignment, UserProfile
from trainee.serializers.module_content import (
    ModuleQuizSerializer, ModuleQuizListSerializer,
    LearningResourceSerializer, LearningResourceListSerializer,
    ModuleQuizQuestionSerializer
)
from trainee.mongo_collection import get_mongodb_connection
import logging

logger = logging.getLogger(__name__)


def is_content_unlocked(user, content_item, content_type, all_content):
    """
    Check if a content item is unlocked for the user.
    Rules:
    - First item is always unlocked
    - If previous item is a quiz, it must be passed to unlock next item
    - If previous item is a resource, it's automatically unlocked
    """
    content_index = all_content.index(content_item)
    
    # First item is always unlocked
    if content_index == 0:
        return True, None
    
    # Check previous item
    previous_item = all_content[content_index - 1]
    previous_type = previous_item.get('content_type')
    
    # If previous is a resource, current is unlocked
    if previous_type == 'resource':
        return True, None
    
    # If previous is a quiz, check if it's passed
    if previous_type == 'quiz':
        quiz_id = previous_item.get('quiz_id')
        attempt = ModuleQuizAttempt.objects.filter(
            user=user,
            quiz_id=quiz_id,
            status='completed',
            passed=True
        ).first()
        
        if attempt:
            return True, None
        else:
            return False, f"Complete the previous quiz to unlock this content"
    
    return True, None


@api_view(['GET'])
@permission_classes([AllowAny])
def get_module_mixed_content(request, module_id):
    """
    GET /trainee/module/{id}/content
    Get all content items in a module (videos, quizzes, resources, PDFs) in sequence order
    Returns mixed content list from both PostgreSQL and MongoDB
    Sequential unlock: Video → Quiz (must pass) → Next Video → etc
    
    Content is fetched from:
    - PostgreSQL: ModuleQuiz, LearningResource
    - MongoDB: module_content_items (videos, PDFs, presentations, documents)
    """
    try:
        # Use get_session_user helper that handles UserProfile correctly
        from trainee.services.api_views import get_session_user
        user = get_session_user(request)
        if not user:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
        module = get_object_or_404(Module, module_id=module_id)
        
        # Check access through course - user must be in a team that has this course assigned
        course = module.course
        user_teams = user.teams.all()
        assignment = CourseAssignment.objects.filter(
            team__in=user_teams,
            course_id=str(course.course_id)
        ).first()
        
        if not assignment:
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Collect all content items with sequence order
        content_items = []
        
        # Get the request's domain and port for building absolute URLs
        # In development: http://localhost:8000
        # In production: https://yourdomain.com
        request_host = request.get_host()  # Gets 'localhost:8000' or 'yourdomain.com'
        request_scheme = request.scheme  # Gets 'http' or 'https'
        base_url = f"{request_scheme}://{request_host}"
        
        # Add video unit from PostgreSQL
        try:
            if hasattr(module, 'video_unit') and module.video_unit:
                video = module.video_unit
                # Build absolute URL for video file
                video_url = video.video_url or f'/media/{video.video_storage_path}'
                # Make absolute if relative
                if video_url.startswith('/'):
                    absolute_video_url = f"{base_url}{video_url}"
                else:
                    absolute_video_url = video_url
                
                video_item = {
                    'id': str(video.id),
                    'video_id': str(video.id),
                    'title': module.title,
                    'description': f'Video lesson for {module.title}',
                    'content_type': 'video',
                    'resource_type': 'video',
                    'file_url': absolute_video_url,  # Use absolute URL
                    'file_reference': absolute_video_url,
                    'duration': video.duration,
                    'duration_seconds': video.duration,
                    'sequence_order': 0,  # Video comes first
                    'is_unlocked': True,
                    'source': 'postgresql',
                }
                content_items.append(video_item)
        except Exception as e:
            logger.error(f"Error adding video unit for module {module_id}: {str(e)}")
        
        # Add presentation unit from PostgreSQL (PPT/PDF files)
        try:
            if hasattr(module, 'presentation_unit') and module.presentation_unit:
                presentation = module.presentation_unit
                # Build absolute URL for presentation file
                ppt_url = presentation.file_url or f'/media/{presentation.file_storage_path}'
                # Make absolute if relative
                if ppt_url.startswith('/'):
                    absolute_ppt_url = f"{base_url}{ppt_url}"
                else:
                    absolute_ppt_url = ppt_url
                
                # Determine if it's PDF or PPT based on file extension
                file_extension = ppt_url.lower().split('.')[-1] if '.' in ppt_url else 'pdf'
                content_type = 'pdf' if file_extension == 'pdf' else 'ppt'
                
                ppt_item = {
                    'id': str(presentation.id),
                    'presentation_id': str(presentation.id),
                    'title': module.title,
                    'description': f'Presentation for {module.title}',
                    'content_type': content_type,
                    'resource_type': content_type,
                    'file_url': absolute_ppt_url,  # Use absolute URL
                    'file_reference': absolute_ppt_url,
                    'slide_count': presentation.slide_count,
                    'sequence_order': module.sequence_order or 0,
                    'is_unlocked': True,
                    'source': 'postgresql',
                }
                content_items.append(ppt_item)
        except Exception as e:
            logger.error(f"Error adding presentation unit for module {module_id}: {str(e)}")
        
        # Add quizzes from PostgreSQL (from new Quiz table)
        quizzes = Quiz.objects.filter(unit=module)
        for quiz in quizzes:
            item = {
                'id': str(quiz.id),
                'quiz_id': str(quiz.id),
                'title': f'Quiz: {module.title}',
                'description': f'Quiz for {module.title}',
                'content_type': 'quiz',
                'time_limit_minutes': quiz.time_limit,
                'passing_score': quiz.passing_score,
                'points_possible': 100,  # Default, actual points are sum of question points
                'attempts_allowed': quiz.attempts_allowed,
                'show_answers': quiz.show_answers,
                'randomize_questions': quiz.randomize_questions,
                'sequence_order': 1,  # Quiz comes after video
                'is_unlocked': True,
                'source': 'postgresql',
            }
            content_items.append(item)
        
        # Add learning resources from PostgreSQL
        resources = LearningResource.objects.filter(module=module).order_by('sequence_order')
        for resource in resources:
            serializer = LearningResourceListSerializer(resource)
            item = serializer.data
            item['content_type'] = 'resource'
            
            # Make resource URLs absolute too
            if 'file_url' in item and item['file_url'] and item['file_url'].startswith('/'):
                item['file_url'] = f"{base_url}{item['file_url']}"
            
            content_items.append(item)
        
        # Add media content from MongoDB module_content_items
        try:
            db = get_mongodb_connection()
            module_content_collection = db['module_content_items']
            
            # Fetch all content items from MongoDB for this module
            mongo_items = list(module_content_collection.find({
                'module_id': str(module_id)
            }, {
                '_id': 1,
                'title': 1,
                'description': 1,
                'content_type': 1,
                'file_reference': 1,
                'file_size_bytes': 1,
                'duration_seconds': 1,
                'thumbnail_url': 1,
                'sequence_order': 1,
                'metadata': 1,
            }).sort('sequence_order', 1))
            
            # Convert MongoDB items to content_items format
            for mongo_item in mongo_items:
                content_type = mongo_item.get('content_type', 'document').lower()
                file_ref = mongo_item.get('file_reference', '')
                
                # Normalize file_reference for frontend consumption
                if file_ref:
                    # Convert Windows backslashes to forward slashes
                    file_ref = file_ref.replace('\\', '/')
                    
                    # Extract filename from full path if it contains 'media'
                    if 'media/' in file_ref.lower():
                        parts = file_ref.lower().split('media/')
                        if len(parts) > 1:
                            file_ref = parts[-1]
                    
                    # Remove leading slashes
                    while file_ref.startswith('/'):
                        file_ref = file_ref[1:]
                    
                    # Add /media/ prefix if not already present
                    if not file_ref.startswith('/media/') and not file_ref.startswith('http'):
                        file_ref = f'/media/{file_ref}'
                
                # Generate unique ID from MongoDB _id
                mongo_id = str(mongo_item.get('_id', mongo_item.get('title', '')))
                
                # Make MongoDB file URLs absolute
                if file_ref.startswith('/'):
                    absolute_file_ref = f"{base_url}{file_ref}"
                else:
                    absolute_file_ref = file_ref
                
                item = {
                    'id': mongo_id,  # Use MongoDB _id as identifier
                    'title': mongo_item.get('title', ''),
                    'description': mongo_item.get('description', ''),
                    'content_type': content_type,
                    'resource_type': content_type,  # Add resource_type for frontend compatibility
                    'file_url': absolute_file_ref,  # Use absolute URL
                    'file_reference': absolute_file_ref,
                    'file_size_bytes': mongo_item.get('file_size_bytes'),
                    'file_size_mb': mongo_item.get('file_size_bytes') / (1024*1024) if mongo_item.get('file_size_bytes') else None,
                    'duration_seconds': mongo_item.get('duration_seconds'),
                    'duration': mongo_item.get('duration_seconds'),  # Add duration for video
                    'thumbnail_url': mongo_item.get('thumbnail_url'),
                    'sequence_order': mongo_item.get('sequence_order', 999),
                    'metadata': mongo_item.get('metadata', {}),
                    'source': 'mongodb',  # Mark as MongoDB content
                    'is_unlocked': True,  # MongoDB content doesn't have unlock rules
                    'resource_id': mongo_id,  # Use mongo_id as resource_id
                }
                content_items.append(item)
                
        except Exception as e:
            logger.warning(f"MongoDB content fetch warning: {str(e)}")
            # Continue without MongoDB content if there's an error
        
        # Sort by sequence_order across all content types
        content_items.sort(key=lambda x: x.get('sequence_order', 999))
        
        # Add unlock status for each item
        final_content = []
        for item in content_items:
            is_unlocked, unlock_reason = is_content_unlocked(user, item, item['content_type'], content_items)
            item['is_unlocked'] = is_unlocked
            item['unlock_reason'] = unlock_reason
            final_content.append(item)
        
        # Count content by type
        video_count = sum(1 for c in final_content if c['content_type'] == 'video')
        pdf_count = sum(1 for c in final_content if c['content_type'] == 'pdf')
        ppt_count = sum(1 for c in final_content if c['content_type'] == 'ppt')
        document_count = sum(1 for c in final_content if c['content_type'] == 'document')
        
        return Response({
            'module_id': str(module.module_id),
            'title': module.title,
            'content': final_content,
            'total_items': len(final_content),
            'has_quizzes': quizzes.exists(),
            'quiz_count': quizzes.count(),
            'resource_count': resources.count(),
            'media_content': {
                'video_count': video_count,
                'pdf_count': pdf_count,
                'ppt_count': ppt_count,
                'document_count': document_count,
                'total_media': video_count + pdf_count + ppt_count + document_count,
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.exception(f"Error in get_module_mixed_content: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def create_module_quiz(request, module_id):
    """
    POST /trainer/module/{id}/quiz
    Create a new quiz in a module
    Trainer only
    """
    try:
        user = UserProfile.objects.get(email=request.user.email)
        
        # Check if user is trainer
        if user.primary_role != 'trainer':
            return Response(
                {'error': 'Only trainers can create quizzes'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        module = get_object_or_404(Module, module_id=module_id)
        
        # Verify trainer owns this course
        if module.course.created_by != user:
            return Response(
                {'error': 'You do not have permission to edit this course'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        data = request.data.copy()
        data['module'] = str(module.module_id)
        data['created_by'] = str(user.user_id)
        
        serializer = ModuleQuizSerializer(data=data)
        if serializer.is_valid():
            quiz = serializer.save()
            return Response(
                {
                    'success': True,
                    'message': 'Quiz created successfully',
                    'quiz': ModuleQuizSerializer(quiz).data
                },
                status=status.HTTP_201_CREATED
            )
        
        return Response(
            {'error': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['PUT'])
@permission_classes([AllowAny])
def update_module_quiz(request, quiz_id):
    """
    PUT /trainer/quiz/{id}
    Update a module quiz
    Trainer only
    """
    try:
        user = UserProfile.objects.get(email=request.user.email)
        quiz = get_object_or_404(ModuleQuiz, quiz_id=quiz_id)
        
        # Verify trainer owns this course
        if quiz.module.course.created_by != user:
            return Response(
                {'error': 'You do not have permission to edit this quiz'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ModuleQuizSerializer(quiz, data=request.data, partial=True)
        if serializer.is_valid():
            quiz = serializer.save()
            return Response(
                {
                    'success': True,
                    'message': 'Quiz updated successfully',
                    'quiz': ModuleQuizSerializer(quiz).data
                },
                status=status.HTTP_200_OK
            )
        
        return Response(
            {'error': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['DELETE'])
@permission_classes([AllowAny])
def delete_module_quiz(request, quiz_id):
    """
    DELETE /trainer/quiz/{id}
    Delete a module quiz
    Trainer only
    """
    try:
        user = UserProfile.objects.get(email=request.user.email)
        quiz = get_object_or_404(ModuleQuiz, quiz_id=quiz_id)
        
        # Verify trainer owns this course
        if quiz.module.course.created_by != user:
            return Response(
                {'error': 'You do not have permission to delete this quiz'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        quiz.delete()
        return Response(
            {'success': True, 'message': 'Quiz deleted successfully'},
            status=status.HTTP_204_NO_CONTENT
        )
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def add_quiz_question(request, quiz_id):
    """
    POST /trainer/quiz/{id}/question
    Add a question to a quiz
    Trainer only
    """
    try:
        user = UserProfile.objects.get(email=request.user.email)
        quiz = get_object_or_404(ModuleQuiz, quiz_id=quiz_id)
        
        # Verify trainer owns this course
        if quiz.module.course.created_by != user:
            return Response(
                {'error': 'You do not have permission to edit this quiz'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        data = request.data.copy()
        data['quiz'] = str(quiz.quiz_id)
        
        serializer = ModuleQuizQuestionSerializer(data=data)
        if serializer.is_valid():
            question = serializer.save()
            return Response(
                {
                    'success': True,
                    'message': 'Question added successfully',
                    'question': ModuleQuizQuestionSerializer(question).data
                },
                status=status.HTTP_201_CREATED
            )
        
        return Response(
            {'error': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def create_learning_resource(request, module_id):
    """
    POST /trainer/module/{id}/resource
    Create a new learning resource in a module
    Trainer only
    """
    try:
        user = UserProfile.objects.get(email=request.user.email)
        
        # Check if user is trainer
        if user.primary_role != 'trainer':
            return Response(
                {'error': 'Only trainers can create resources'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        module = get_object_or_404(Module, module_id=module_id)
        
        # Verify trainer owns this course
        if module.course.created_by != user:
            return Response(
                {'error': 'You do not have permission to edit this course'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        data = request.data.copy()
        data['module'] = str(module.module_id)
        data['created_by'] = str(user.user_id)
        
        serializer = LearningResourceSerializer(data=data)
        if serializer.is_valid():
            resource = serializer.save()
            return Response(
                {
                    'success': True,
                    'message': 'Resource created successfully',
                    'resource': LearningResourceSerializer(resource).data
                },
                status=status.HTTP_201_CREATED
            )
        
        return Response(
            {'error': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['PUT'])
@permission_classes([AllowAny])
def update_learning_resource(request, resource_id):
    """
    PUT /trainer/resource/{id}
    Update a learning resource
    Trainer only
    """
    try:
        user = UserProfile.objects.get(email=request.user.email)
        resource = get_object_or_404(LearningResource, resource_id=resource_id)
        
        # Verify trainer owns this course
        if resource.module.course.created_by != user:
            return Response(
                {'error': 'You do not have permission to edit this resource'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = LearningResourceSerializer(resource, data=request.data, partial=True)
        if serializer.is_valid():
            resource = serializer.save()
            return Response(
                {
                    'success': True,
                    'message': 'Resource updated successfully',
                    'resource': LearningResourceSerializer(resource).data
                },
                status=status.HTTP_200_OK
            )
        
        return Response(
            {'error': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['DELETE'])
@permission_classes([AllowAny])
def delete_learning_resource(request, resource_id):
    """
    DELETE /trainer/resource/{id}
    Delete a learning resource
    Trainer only
    """
    try:
        user = UserProfile.objects.get(email=request.user.email)
        resource = get_object_or_404(LearningResource, resource_id=resource_id)
        
        # Verify trainer owns this course
        if resource.module.course.created_by != user:
            return Response(
                {'error': 'You do not have permission to delete this resource'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        resource.delete()
        return Response(
            {'success': True, 'message': 'Resource deleted successfully'},
            status=status.HTTP_204_NO_CONTENT
        )
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_quiz_detail(request, quiz_id):
    """
    GET /trainer/quiz/{id}
    Get full details of a quiz including questions
    """
    try:
        quiz = get_object_or_404(ModuleQuiz, quiz_id=quiz_id)
        
        # Check access (user must be trainer of the course or trainee with access)
        user = UserProfile.objects.get(email=request.user.email)
        course = quiz.module.course
        
        if user.primary_role == 'trainer':
            # Trainer can view if they own the course
            if course.created_by != user:
                return Response(
                    {'error': 'Access denied'},
                    status=status.HTTP_403_FORBIDDEN
                )
        else:
            # Trainee can view if assigned to the course
            assignment = CourseAssignment.objects.filter(
                Q(assigned_to_user=user) | Q(assigned_to_team__members__user=user),
                course=course
            ).first()
            if not assignment:
                return Response(
                    {'error': 'Access denied'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        serializer = ModuleQuizSerializer(quiz)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
