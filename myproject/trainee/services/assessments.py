"""
Notifications & Feedback Endpoints
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from trainee.models import Notification, Feedback, User
from django.utils import timezone
from django.db.models import Q


@api_view(['GET'])
@permission_classes([AllowAny])
def get_notifications(request):
    """
    GET /trainee/notifications
    Get all notifications (assignment reminders, new content, graded tests)
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
        
        notifications = Notification.objects.filter(
            user=user
        ).order_by('-created_at')
        
        notification_list = []
        for notification in notifications:
            notification_list.append({
                'notification_id': str(notification.notification_id),
                'title': notification.title or notification.notification_type,
                'message': notification.message,
                'notification_type': notification.notification_type,
                'priority': notification.priority,
                'status': notification.status,
                'link_url': notification.link_url,
                'created_at': notification.created_at,
                'read_at': notification.read_at
            })
        
        return Response({
            'notifications': notification_list,
            'unread_count': Notification.objects.filter(user=user, status='unread').count()
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['PATCH'])
@permission_classes([AllowAny])
def mark_notification_read(request, notification_id):
    """
    PATCH /trainee/notification/{id}/read
    Mark notification as read
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
        
        notification = Notification.objects.get(
            notification_id=notification_id,
            user=user
        )
        
        notification.status = 'read'
        notification.read_at = timezone.now()
        notification.save()
        
        return Response({
            'message': 'Notification marked as read',
            'notification_id': str(notification_id)
        }, status=status.HTTP_200_OK)
        
    except Notification.DoesNotExist:
        return Response(
            {'error': 'Notification not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def mark_all_notifications_read(request):
    """
    POST /trainee/notifications/mark-all-read
    Mark all notifications as read
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
        
        count = Notification.objects.filter(
            user=user,
            status='unread'
        ).update(
            status='read',
            read_at=timezone.now()
        )
        
        return Response({
            'message': f'{count} notifications marked as read'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def submit_feedback(request):
    """
    POST /trainee/feedback
    Submit feedback about course/trainer/platform
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
        
        # Get data from request
        feedback_type = request.data.get('feedback_type')  # course, module, trainer, system, general
        rating = request.data.get('rating')
        content = request.data.get('content')
        course_id = request.data.get('course_id')
        module_id = request.data.get('module_id')
        is_anonymous = request.data.get('is_anonymous', False)
        
        if not content:
            return Response(
                {'error': 'Feedback content is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not feedback_type:
            return Response(
                {'error': 'Feedback type is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create feedback
        feedback_data = {
            'user': user,
            'feedback_type': feedback_type,
            'rating': rating,
            'content': content,
            'is_anonymous': is_anonymous,
            'status': 'pending'
        }
        
        # Add optional fields
        if course_id:
            try:
                from trainee.models import Course
                feedback_data['course'] = Course.objects.get(course_id=course_id)
            except:
                pass
        
        if module_id:
            try:
                from trainee.models import Module
                feedback_data['module'] = Module.objects.get(module_id=module_id)
            except:
                pass
        
        feedback = Feedback.objects.create(**feedback_data)
        
        return Response({
            'message': 'Feedback submitted successfully',
            'feedback_id': str(feedback.feedback_id)
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
