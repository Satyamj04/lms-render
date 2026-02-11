"""
Media Content Service - Handles fetching and managing media content from MongoDB
Links module_content_items with media_files collections
Fetches content properly according to module and course structure
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from trainee.models import Course, Module, User
from admin.models import CourseAssignment
from trainee.mongo_collection import get_mongodb_connection
from django.db.models import Q
from django.shortcuts import get_object_or_404
import logging

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_course_content_by_type(request, course_id):
    """
    GET /api/trainee/course/{course_id}/content-by-type/
    
    Fetch all content for a course organized by type:
    - Videos
    - PDFs
    - Presentations
    - Documents
    
    Fetches from MongoDB module_content_items and links with media_files
    """
    try:
        course = Course.objects.get(course_id=course_id)
        
        # Get all modules in course
        modules = course.modules.all()
        module_ids = [str(m.module_id) for m in modules]
        
        if not module_ids:
            return Response({
                'success': True,
                'course_id': str(course_id),
                'course_title': course.title,
                'content_by_type': {
                    'videos': [],
                    'pdfs': [],
                    'presentations': [],
                    'documents': []
                },
                'totals': {
                    'videos': 0,
                    'pdfs': 0,
                    'presentations': 0,
                    'documents': 0,
                    'total': 0
                }
            }, status=status.HTTP_200_OK)
        
        # Fetch from MongoDB
        try:
            db = get_mongodb_connection()
            module_content_collection = db['module_content_items']
            
            # Fetch all content for these modules
            all_content = list(module_content_collection.find({
                'module_id': {'$in': module_ids}
            }, {
                '_id': 0,
                'module_id': 1,
                'title': 1,
                'description': 1,
                'content_type': 1,
                'file_reference': 1,
                'file_size_bytes': 1,
                'duration_seconds': 1,
                'thumbnail_url': 1,
                'sequence_order': 1,
                'metadata': 1,
            }))
            
            # Organize content by type
            videos = [c for c in all_content if c.get('content_type') == 'video']
            pdfs = [c for c in all_content if c.get('content_type') == 'pdf']
            presentations = [c for c in all_content if c.get('content_type') == 'ppt']
            documents = [c for c in all_content if c.get('content_type') == 'document']
            
            return Response({
                'success': True,
                'course_id': str(course_id),
                'course_title': course.title,
                'content_by_type': {
                    'videos': sorted(videos, key=lambda x: x.get('sequence_order', 0)),
                    'pdfs': sorted(pdfs, key=lambda x: x.get('sequence_order', 0)),
                    'presentations': sorted(presentations, key=lambda x: x.get('sequence_order', 0)),
                    'documents': sorted(documents, key=lambda x: x.get('sequence_order', 0))
                },
                'totals': {
                    'videos': len(videos),
                    'pdfs': len(pdfs),
                    'presentations': len(presentations),
                    'documents': len(documents),
                    'total': len(all_content)
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.exception(f"MongoDB error: {str(e)}")
            return Response({
                'success': False,
                'error': f'Failed to fetch content from MongoDB: {str(e)}',
                'course_id': str(course_id)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Course.DoesNotExist:
        return Response(
            {'success': False, 'error': 'Course not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.exception(f"Error in get_course_content_by_type: {str(e)}")
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_module_content_detailed(request, module_id):
    """
    GET /api/trainee/module/{module_id}/content-detailed/
    
    Fetch detailed content for a module with media file metadata
    Combines module_content_items with media_files information
    """
    try:
        module = Module.objects.get(module_id=module_id)
        
        try:
            db = get_mongodb_connection()
            module_content_collection = db['module_content_items']
            media_files_collection = db['media_files']
            
            # Fetch all content for this module
            module_content = list(module_content_collection.find({
                'module_id': str(module_id)
            }, {
                '_id': 0,
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
            
            # Fetch media files for reference
            media_files = list(media_files_collection.find({}, {
                '_id': 0,
                'title': 1,
                'file_type': 1,
                'file_path': 1,
                'file_size_bytes': 1,
                'duration_seconds': 1,
                'encoding_status': 1,
                'thumbnail_path': 1,
            }))
            
            # Enhance module content with media file info if available
            enhanced_content = []
            for item in module_content:
                file_ref = item.get('file_reference', '')
                
                # Try to find matching media file
                matching_media = None
                for media in media_files:
                    if (media.get('file_path', '') == file_ref or 
                        media.get('title', '') == item.get('title', '')):
                        matching_media = media
                        break
                
                # Create enhanced item
                enhanced_item = {
                    **item,
                    'media_info': matching_media if matching_media else {
                        'encoding_status': 'unknown',
                        'available': False
                    }
                }
                enhanced_content.append(enhanced_item)
            
            return Response({
                'success': True,
                'module_id': str(module_id),
                'module_title': module.title,
                'content': enhanced_content,
                'media_files_available': len(media_files),
                'total_content_items': len(enhanced_content),
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.exception(f"MongoDB error: {str(e)}")
            return Response({
                'success': False,
                'error': f'MongoDB error: {str(e)}',
                'module_id': str(module_id)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Module.DoesNotExist:
        return Response(
            {'success': False, 'error': 'Module not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_user_course_content(request, course_id):
    """
    GET /api/trainee/course/{course_id}/user-content/
    
    Fetch all content for a course that user has access to
    Verifies course assignment before returning content
    """
    try:
        course = Course.objects.get(course_id=course_id)
        
        # Get user from request
        user = None
        if request.user and request.user.is_authenticated:
            try:
                user = User.objects.get(email=request.user.email)
            except User.DoesNotExist:
                pass
        
        # Check access if user is authenticated
        if user:
            assignment = CourseAssignment.objects.filter(
                Q(assigned_to_user=user) | Q(assigned_to_team__members__user=user),
                course=course
            ).first()
            
            if not assignment:
                return Response(
                    {'success': False, 'error': 'Access denied to this course'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Get all modules in course
        modules = course.modules.all()
        module_ids = [str(m.module_id) for m in modules]
        
        if not module_ids:
            return Response({
                'success': True,
                'course_id': str(course_id),
                'course_title': course.title,
                'modules': []
            }, status=status.HTTP_200_OK)
        
        # Fetch from MongoDB
        try:
            db = get_mongodb_connection()
            module_content_collection = db['module_content_items']
            media_files_collection = db['media_files']
            
            # Fetch content for all modules
            modules_content = []
            
            for module in modules:
                module_id_str = str(module.module_id)
                
                # Get content for this module
                content = list(module_content_collection.find({
                    'module_id': module_id_str
                }, {
                    '_id': 0,
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
                
                # Get media files
                media_files = list(media_files_collection.find({}, {
                    '_id': 0,
                    'title': 1,
                    'file_type': 1,
                    'file_path': 1,
                    'file_size_bytes': 1,
                    'duration_seconds': 1,
                    'encoding_status': 1,
                }))
                
                modules_content.append({
                    'module_id': module_id_str,
                    'module_title': module.title,
                    'module_description': module.description,
                    'content_items': content,
                    'media_files': media_files,
                    'total_items': len(content),
                    'sequence_order': module.sequence_order,
                })
            
            return Response({
                'success': True,
                'course_id': str(course_id),
                'course_title': course.title,
                'modules': sorted(modules_content, key=lambda x: x.get('sequence_order', 0)),
                'total_modules': len(modules_content),
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.exception(f"MongoDB error: {str(e)}")
            return Response({
                'success': False,
                'error': f'Failed to fetch content: {str(e)}',
                'course_id': str(course_id)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Course.DoesNotExist:
        return Response(
            {'success': False, 'error': 'Course not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.exception(f"Error in get_user_course_content: {str(e)}")
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_media_files_summary(request):
    """
    GET /api/trainee/media-files-summary/
    
    Get summary of all media files in MongoDB
    Useful for admin dashboard and monitoring
    """
    try:
        db = get_mongodb_connection()
        media_files_collection = db['media_files']
        
        # Get all media files
        media_files = list(media_files_collection.find({}, {
            '_id': 0,
            'title': 1,
            'file_type': 1,
            'file_size_bytes': 1,
            'duration_seconds': 1,
            'encoding_status': 1,
            'created_at': 1,
        }))
        
        # Calculate statistics
        stats = {
            'total_files': len(media_files),
            'by_type': {},
            'by_encoding_status': {},
            'total_size_mb': 0,
            'total_duration_minutes': 0,
        }
        
        for media in media_files:
            file_type = media.get('file_type', 'unknown')
            status_val = media.get('encoding_status', 'unknown')
            size_bytes = media.get('file_size_bytes', 0)
            duration_seconds = media.get('duration_seconds', 0)
            
            # Count by type
            if file_type not in stats['by_type']:
                stats['by_type'][file_type] = 0
            stats['by_type'][file_type] += 1
            
            # Count by status
            if status_val not in stats['by_encoding_status']:
                stats['by_encoding_status'][status_val] = 0
            stats['by_encoding_status'][status_val] += 1
            
            # Sum sizes and durations
            stats['total_size_mb'] += size_bytes / (1024 * 1024) if size_bytes else 0
            stats['total_duration_minutes'] += duration_seconds / 60 if duration_seconds else 0
        
        stats['total_size_mb'] = round(stats['total_size_mb'], 2)
        stats['total_duration_minutes'] = round(stats['total_duration_minutes'], 2)
        
        return Response({
            'success': True,
            'stats': stats,
            'media_files': media_files,
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.exception(f"Error fetching media summary: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
