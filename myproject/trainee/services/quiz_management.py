"""
Trainer Quiz Management API
Allows trainers to add quizzes at any position in module content
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Q
from trainee.models import (
    User, Module, Course, ModuleQuiz, ModuleQuizQuestion
)
from admin.models import CourseAssignment
from trainee.serializers.module_content import ModuleQuizSerializer


@api_view(['POST'])
@permission_classes([AllowAny])
def create_quiz_in_module(request, module_id):
    """
    POST /trainer/module/{id}/quiz/create
    Create a new quiz in a module at a specific position
    Request body:
    {
        "title": "Quiz Title",
        "description": "Quiz description",
        "sequence_order": 1,  # Position in module (0 = before everything)
        "time_limit_minutes": 30,
        "passing_score": 70,
        "max_attempts": 3,
        "points_possible": 100,
        "is_mandatory": true
    }
    """
    try:
        user = User.objects.get(email=request.user.email)
        
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
                    'message': 'Quiz created successfully at position ' + str(data.get('sequence_order', 0)),
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
def update_quiz_position(request, quiz_id):
    """
    PUT /trainer/quiz/{id}/position
    Update quiz position in module
    Request body:
    {
        "sequence_order": 2  # New position
    }
    """
    try:
        user = User.objects.get(email=request.user.email)
        quiz = get_object_or_404(ModuleQuiz, quiz_id=quiz_id)
        
        # Verify trainer owns this course
        if quiz.module.course.created_by != user:
            return Response(
                {'error': 'You do not have permission to edit this quiz'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        new_sequence = request.data.get('sequence_order')
        if new_sequence is not None:
            quiz.sequence_order = new_sequence
            quiz.save()
            
            return Response(
                {
                    'success': True,
                    'message': f'Quiz moved to position {new_sequence}',
                    'quiz': ModuleQuizSerializer(quiz).data
                },
                status=status.HTTP_200_OK
            )
        
        return Response(
            {'error': 'sequence_order is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_module_content_positions(request, module_id):
    """
    GET /trainer/module/{id}/content-positions
    Get all content items in module with their positions
    Helps trainer see where they can insert quizzes
    """
    try:
        user = User.objects.get(email=request.user.email)
        module = get_object_or_404(Module, module_id=module_id)
        
        # Verify trainer owns this course
        if module.course.created_by != user:
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        from trainee.serializers.module_content import (
            ModuleQuizListSerializer, LearningResourceListSerializer
        )
        
        # Get all content
        quizzes = ModuleQuiz.objects.filter(module=module).order_by('sequence_order')
        resources = module.resources.all().order_by('sequence_order')
        
        # Combine and sort
        content_items = []
        for quiz in quizzes:
            serializer = ModuleQuizListSerializer(quiz)
            item = serializer.data
            item['content_type'] = 'quiz'
            item['type'] = 'quiz'
            content_items.append(item)
        
        for resource in resources:
            serializer = LearningResourceListSerializer(resource)
            item = serializer.data
            item['content_type'] = 'resource'
            item['type'] = 'resource'
            content_items.append(item)
        
        content_items.sort(key=lambda x: x['sequence_order'])
        
        return Response({
            'module_id': str(module.module_id),
            'module_title': module.title,
            'content': content_items,
            'message': 'You can create a quiz at any position. Use sequence_order to position it.',
            'available_positions': list(range(-1, len(content_items) + 2)),
            'position_help': {
                '-1': 'Before everything (very start)',
                '0': 'At the beginning',
                '1': 'After first item',
                '2': 'After second item',
                'etc': 'Any number to position quiz'
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
