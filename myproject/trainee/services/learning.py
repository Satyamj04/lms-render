"""
Learning Interface Endpoints
Handles modules, notes, and interactive content
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from trainee.models import (
    User, Module, ModuleCompletion, Note, 
    TestQuestion, Course, Test,
    Quiz, LearningResource
)
from admin.models import CourseAssignment
from django.db.models import Q


@api_view(['GET'])
@permission_classes([AllowAny])
def get_course_modules(request, course_id):
    """
    GET /trainee/course/{id}/modules
    Get list of modules for a course with video count and quiz info
    """
    try:
        # Get Mukesh Pawar user from database or fallback
        try:
            user = User.objects.get(email='mukesh.pawar@example.com', first_name='Mukesh', last_name='Pawar')
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if user has access to this course
        course = get_object_or_404(Course, course_id=course_id)
        assignment = CourseAssignment.objects.filter(
            Q(assigned_to_user=user) | Q(assigned_to_team__members__user=user),
            course=course
        ).first()
        
        if not assignment:
            return Response(
                {'error': 'You do not have access to this course'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        modules = Module.objects.filter(course=course).order_by('sequence_order')
        
        modules_data = []
        for module in modules:
            # Get completion status for this user
            completion = ModuleCompletion.objects.filter(
                module=module, user=user
            ).first()
            
            # Count videos and quizzes from model attributes
            video_count = module.video_count  # From model
            has_quizzes = module.has_quizzes  # From model
            
            modules_data.append({
                'module_id': str(module.module_id),
                'title': module.title,
                'description': module.description,
                'sequence_order': module.sequence_order,
                'is_mandatory': module.is_mandatory,
                'video_count': video_count,
                'has_quizzes': has_quizzes,
                'completion_percentage': completion.completion_percentage if completion else 0,
                'is_completed': completion.is_completed if completion else False,
            })
        
        return Response({
            'course_id': str(course_id),
            'course_title': course.title,
            'modules': modules_data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_module_content(request, module_id):
    """
    GET /trainee/module/{id}
    Get module content (videos, PDFs, PPTs, links, quizzes, etc.)
    """
    try:
        # Get authenticated user
        if not request.user or not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            user = User.objects.get(email=request.user.email)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found in system'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        module = get_object_or_404(Module, module_id=module_id)
        
        # Check access through course
        course = module.course
        assignment = CourseAssignment.objects.filter(
            Q(assigned_to_user=user) | Q(assigned_to_team__members__user=user),
            course=course
        ).first()
        
        if not assignment:
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get module completion info
        completion = ModuleCompletion.objects.filter(
            module=module, user=user
        ).first()
        
        # Count mixed content items
        quiz_count = ModuleQuiz.objects.filter(module=module).count()
        resource_count = LearningResource.objects.filter(module=module).count()
        
        return Response({
            'module_id': str(module.module_id),
            'title': module.title,
            'description': module.description,
            'module_type': module.module_type,
            'video_count': module.video_count,
            'quiz_count': quiz_count,
            'resource_count': resource_count,
            'has_quizzes': module.has_quizzes or quiz_count > 0,
            'has_mixed_content': quiz_count > 0 or resource_count > 0,
            'estimated_duration_minutes': module.estimated_duration_minutes,
            'completion_percentage': completion.completion_percentage if completion else 0,
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.exception(f"Error fetching module content: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def mark_module_complete(request, module_id):
    """
    POST /trainee/module/{id}/complete
    Mark module as completed
    """
    try:
        # Get Mukesh Pawar user from database or fallback
        try:
            user = User.objects.get(email='mukesh.pawar@example.com', first_name='Mukesh', last_name='Pawar')
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        module = get_object_or_404(Module, module_id=module_id)
        
        completion, created = ModuleCompletion.objects.update_or_create(
            module=module,
            user=user,
            defaults={
                'is_completed': True,
                'completion_percentage': 100
            }
        )
        
        return Response({
            'message': 'Module marked as completed',
            'completion_percentage': 100,
            'is_completed': True
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def track_learning_time(request, module_id):
    """
    GET /trainee/module/{id}/time
    Get user's time spent on module
    """
    try:
        # Get Mukesh Pawar user from database or fallback
        try:
            user = User.objects.get(email='mukesh.pawar@example.com', first_name='Mukesh', last_name='Pawar')
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        module = get_object_or_404(Module, module_id=module_id)
        
        completion = ModuleCompletion.objects.filter(
            module=module, user=user
        ).first()
        
        return Response({
            'module_id': str(module_id),
            'time_spent_minutes': completion.time_spent_minutes if completion else 0,
            'estimated_duration_minutes': module.estimated_duration_minutes,
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_module_questions(request, module_id):
    """
    GET /trainee/module/{id}/questions
    Get in-content questions for progression control
    """
    try:
        # Get Mukesh Pawar user from database or fallback
        try:
            user = User.objects.get(email='mukesh.pawar@example.com', first_name='Mukesh', last_name='Pawar')
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        module = get_object_or_404(Module, module_id=module_id)
        
        # Get tests in this module
        tests = Test.objects.filter(module=module)
        
        questions_data = []
        for test in tests:
            test_questions = TestQuestion.objects.filter(
                test=test
            ).values('question_id', 'question_text', 'question_type', 'options', 'points')
            questions_data.extend(list(test_questions))
        
        return Response({
            'module_id': str(module_id),
            'questions': questions_data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def answer_module_question(request, module_id):
    """
    POST /trainee/module/{id}/questions/answer
    Submit answer to unlock next content
    """
    try:
        # Get Mukesh Pawar user from database or fallback
        try:
            user = User.objects.get(email='mukesh.pawar@example.com', first_name='Mukesh', last_name='Pawar')
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        question_id = request.data.get('question_id')
        answer = request.data.get('answer')
        
        # Verify answer
        question = get_object_or_404(TestQuestion, question_id=question_id)
        is_correct = str(answer).lower() == str(question.correct_answer).lower()
        
        return Response({
            'message': 'Answer submitted',
            'is_correct': is_correct,
            'can_proceed': is_correct
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_module_notes(request, module_id):
    """
    GET /trainee/module/{id}/notes
    Get all notes created by user for this module
    """
    try:
        # Get Mukesh Pawar user from database or fallback
        try:
            user = User.objects.get(email='mukesh.pawar@example.com', first_name='Mukesh', last_name='Pawar')
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        module = get_object_or_404(Module, module_id=module_id)
        
        notes = Note.objects.filter(
            module=module, user=user
        ).values('note_id', 'content', 'created_at', 'updated_at')
        
        return Response({
            'module_id': str(module_id),
            'notes': list(notes)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def create_module_note(request, module_id):
    """
    POST /trainee/module/{id}/notes
    Create a new note for module
    """
    try:
        # Get Mukesh Pawar user from database or fallback
        try:
            user = User.objects.get(email='mukesh.pawar@example.com', first_name='Mukesh', last_name='Pawar')
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        module = get_object_or_404(Module, module_id=module_id)
        content = request.data.get('content')
        
        if not content:
            return Response(
                {'error': 'Content is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        note = Note.objects.create(
            user=user,
            module=module,
            content=content
        )
        
        return Response({
            'message': 'Note created',
            'note_id': str(note.note_id),
            'created_at': note.created_at
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['PUT'])
@permission_classes([AllowAny])
def update_module_note(request, module_id, note_id):
    """
    PUT /trainee/module/{id}/notes/{note_id}
    Update a note
    """
    try:
        # Get Mukesh Pawar user from database or fallback
        try:
            user = User.objects.get(email='mukesh.pawar@example.com', first_name='Mukesh', last_name='Pawar')
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        note = get_object_or_404(Note, note_id=note_id, user=user)
        
        content = request.data.get('content')
        if not content:
            return Response(
                {'error': 'Content is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        note.content = content
        note.save()
        
        return Response({
            'message': 'Note updated',
            'note_id': str(note.note_id),
            'updated_at': note.updated_at
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['DELETE'])
@permission_classes([AllowAny])
def delete_module_note(request, module_id, note_id):
    """
    DELETE /trainee/module/{id}/notes/{note_id}
    Delete a note
    """
    try:
        # Get Mukesh Pawar user from database or fallback
        try:
            user = User.objects.get(email='mukesh.pawar@example.com', first_name='Mukesh', last_name='Pawar')
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        note = get_object_or_404(Note, note_id=note_id, user=user)
        
        note.delete()
        
        return Response({
            'message': 'Note deleted'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['PATCH', 'DELETE'])
@permission_classes([AllowAny])
def note_by_id(request, note_id):
    """
    PATCH /trainee/note/{id}  -> Update note content
    DELETE /trainee/note/{id} -> Delete note
    Wrapper to support documented simple note endpoints.
    """
    try:
        # Get Mukesh Pawar user from database or fallback
        try:
            user = User.objects.get(email='mukesh.pawar@example.com', first_name='Mukesh', last_name='Pawar')
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        note = get_object_or_404(Note, note_id=note_id, user=user)

        if request.method == 'PATCH':
            content = request.data.get('content')
            if not content:
                return Response({'error': 'Content is required'}, status=status.HTTP_400_BAD_REQUEST)
            note.content = content
            note.save()
            return Response({
                'message': 'Note updated',
                'note_id': str(note.note_id),
                'updated_at': note.updated_at
            }, status=status.HTTP_200_OK)

        # DELETE
        note.delete()
        return Response({'message': 'Note deleted'}, status=status.HTTP_200_OK)

    except Note.DoesNotExist:
        return Response({'error': 'Note not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
