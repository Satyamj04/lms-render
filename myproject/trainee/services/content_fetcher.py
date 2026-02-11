"""
Course Content Fetcher - Fetch actual content from MongoDB and PostgreSQL
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from trainee.models import Course, Module, Quiz
from trainee.mongo_collection import get_mongodb_connection
import logging

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_course_content_counts(request, course_id):
    """
    GET /api/trainee/course/{course_id}/content-counts/
    
    Fetch actual content counts from:
    - PostgreSQL: Quiz counts (ModuleQuiz model)
    - MongoDB: Video and PDF metadata counts (content_metadata collection)
    """
    try:
        course = Course.objects.get(course_id=course_id)
        
        # Get all modules in course
        modules = course.modules.all()
        module_ids = list(modules.values_list('id', flat=True))
        
        if not module_ids:
            return Response({
                'success': True,
                'course_id': str(course_id),
                'videos': 0,
                'pdfs': 0,
                'quizzes': 0,
                'total_items': 0,
            }, status=status.HTTP_200_OK)
        
        # COUNT FROM POSTGRESQL: Quizzes
        quiz_count = Quiz.objects.filter(
            unit__in=modules
        ).count()
        
        # COUNT FROM MONGODB: Videos and PDFs from module_content_items
        try:
            db = get_mongodb_connection()
            
            # Count module_content_items by type
            module_content_collection = db['module_content_items']
            
            # Query for videos in module_content_items
            video_count = module_content_collection.count_documents({
                'module_id': {'$in': [str(m_id) for m_id in module_ids]},
                'content_type': 'video'
            })
            
            # Query for PDFs/Presentations in module_content_items
            pdf_count = module_content_collection.count_documents({
                'module_id': {'$in': [str(m_id) for m_id in module_ids]},
                'content_type': {'$in': ['pdf', 'ppt', 'document']}
            })
            
        except Exception as e:
            logger.warning(f"MongoDB connection error: {str(e)}")
            video_count = 0
            pdf_count = 0
        
        total_items = video_count + pdf_count + quiz_count
        
        return Response({
            'success': True,
            'course_id': str(course_id),
            'videos': video_count,
            'pdfs': pdf_count,
            'quizzes': quiz_count,
            'total_items': total_items,
        }, status=status.HTTP_200_OK)
        
    except Course.DoesNotExist:
        return Response(
            {'success': False, 'error': 'Course not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.exception(f"Error fetching content counts: {str(e)}")
        return Response(
            {'success': False, 'error': f'Failed to fetch content counts: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_module_videos_from_mongodb(request, module_id):
    """
    GET /api/trainee/module/{module_id}/videos-mongodb/
    
    Fetch actual videos for a module from MongoDB module_content_items collection
    """
    try:
        module = Module.objects.get(module_id=module_id)
        
        try:
            db = get_mongodb_connection()
            module_content_collection = db['module_content_items']
            
            # Fetch videos for this module from module_content_items
            videos = list(module_content_collection.find({
                'module_id': str(module_id),
                'content_type': 'video'
            }, {
                '_id': 0,
                'title': 1,
                'description': 1,
                'file_reference': 1,
                'file_size_bytes': 1,
                'duration_seconds': 1,
                'thumbnail_url': 1,
                'sequence_order': 1,
                'metadata': 1,
            }).sort('sequence_order', 1))
            
            return Response({
                'success': True,
                'module_id': str(module_id),
                'videos': videos,
                'count': len(videos),
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.exception(f"MongoDB error: {str(e)}")
            return Response({
                'success': True,
                'module_id': str(module_id),
                'videos': [],
                'count': 0,
                'note': 'MongoDB not available'
            }, status=status.HTTP_200_OK)
            
    except Module.DoesNotExist:
        return Response(
            {'success': False, 'error': 'Module not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_module_quizzes_postgresql(request, module_id):
    """
    GET /api/trainee/module/{module_id}/quizzes-postgresql/
    
    Fetch actual quizzes for a module from PostgreSQL Quiz model
    """
    try:
        module = Module.objects.get(module_id=module_id)
        
        # Fetch quizzes for this module
        quizzes = Quiz.objects.filter(
            unit=module
        ).order_by('order').values(
            'id',
            'unit__title',
            'is_mandatory'
        )
        
        quizzes_list = list(quizzes)
        
        return Response({
            'success': True,
            'module_id': str(module_id),
            'quizzes': quizzes_list,
            'count': len(quizzes_list),
        }, status=status.HTTP_200_OK)
        
    except Module.DoesNotExist:
        return Response(
            {'success': False, 'error': 'Module not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.exception(f"Error fetching quizzes: {str(e)}")
        return Response(
            {'success': False, 'error': f'Failed to fetch quizzes: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_module_all_content(request, module_id):
    """
    GET /api/trainee/module/{module_id}/all-content/
    
    Fetch ALL content for a module:
    - Quizzes from PostgreSQL
    - Videos, PDFs, PPTs from MongoDB module_content_items collection
    """
    try:
        module = Module.objects.get(module_id=module_id)
        
        content_data = {
            'success': True,
            'module_id': str(module_id),
            'module_title': module.title,
        }
        
        # FETCH QUIZZES FROM POSTGRESQL
        try:
            quizzes = list(Quiz.objects.filter(
                unit=module
            ).order_by('order').values(
                'id',
                'unit__title',
                'passing_score',
                'order'
            ))
            content_data['quizzes'] = quizzes
            content_data['quiz_count'] = len(quizzes)
        except Exception as e:
            logger.warning(f"PostgreSQL quiz fetch error: {str(e)}")
            content_data['quizzes'] = []
            content_data['quiz_count'] = 0
        
        # FETCH ALL CONTENT FROM MONGODB module_content_items
        try:
            db = get_mongodb_connection()
            
            # Fetch from module_content_items collection
            module_content_collection = db['module_content_items']
            media_files_collection = db['media_files']
            
            # Fetch all content items for this module from module_content_items
            all_items = list(module_content_collection.find({
                'module_id': str(module_id)
            }, {
                '_id': 0,
                'title': 1,
                'description': 1,
                'file_reference': 1,
                'file_size_bytes': 1,
                'duration_seconds': 1,
                'content_type': 1,
                'sequence_order': 1,
                'thumbnail_url': 1,
                'metadata': 1,
            }).sort('sequence_order', 1))
            
            # Normalize file references in all items
            for item in all_items:
                file_ref = item.get('file_reference', '')
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
                    
                    item['file_reference'] = file_ref
            
            # Fetch related media files metadata
            try:
                media_files = list(media_files_collection.find({}, {
                    '_id': 0,
                    'title': 1,
                    'file_type': 1,
                    'file_path': 1,
                    'file_size_bytes': 1,
                    'duration_seconds': 1,
                    'encoding_status': 1,
                }))
            except Exception as e:
                logger.warning(f"Media files fetch warning: {str(e)}")
                media_files = []
            
            # Separate content by type
            videos = [item for item in all_items if item.get('content_type') == 'video']
            pdfs = [item for item in all_items if item.get('content_type') == 'pdf']
            ppts = [item for item in all_items if item.get('content_type') == 'ppt']
            
            # Add to response
            content_data['videos'] = videos
            content_data['video_count'] = len(videos)
            
            content_data['pdfs'] = pdfs
            content_data['pdf_count'] = len(pdfs)
            
            content_data['ppts'] = ppts
            content_data['ppt_count'] = len(ppts)
            
            # Add media files info to response
            content_data['media_files'] = media_files
            content_data['media_files_count'] = len(media_files)
            
            # Combined count for all media (videos + pdfs + ppts + documents)
            content_data['media_count'] = len(videos) + len(pdfs) + len(ppts)
            
        except Exception as e:
            logger.warning(f"MongoDB content fetch error: {str(e)}")
            content_data['videos'] = []
            content_data['video_count'] = 0
            content_data['pdfs'] = []
            content_data['pdf_count'] = 0
            content_data['ppts'] = []
            content_data['ppt_count'] = 0
            content_data['media_count'] = 0
        
        # CALCULATE TOTALS
        total_items = content_data.get('quiz_count', 0) + \
                     content_data.get('media_count', 0)
        
        content_data['total_items'] = total_items
        
        return Response(content_data, status=status.HTTP_200_OK)
        
    except Module.DoesNotExist:
        return Response(
            {'success': False, 'error': 'Module not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.exception(f"Error fetching all content: {str(e)}")
        return Response(
            {'success': False, 'error': f'Failed to fetch content: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_module_pdfs_from_mongodb(request, module_id):
    """
    GET /api/trainee/module/{module_id}/pdfs-mongodb/
    
    Fetch actual PDFs/Presentations for a module from MongoDB module_content_items
    """
    try:
        module = Module.objects.get(module_id=module_id)
        
        try:
            db = get_mongodb_connection()
            module_content_collection = db['module_content_items']
            
            # Fetch PDFs and presentations for this module from module_content_items
            pdfs = list(module_content_collection.find({
                'module_id': str(module_id),
                'content_type': {'$in': ['pdf', 'ppt', 'document']}
            }, {
                '_id': 0,
                'title': 1,
                'description': 1,
                'file_reference': 1,
                'file_size_bytes': 1,
                'content_type': 1,
                'thumbnail_url': 1,
                'sequence_order': 1,
                'metadata': 1,
            }).sort('sequence_order', 1))
            
            return Response({
                'success': True,
                'module_id': str(module_id),
                'pdfs': pdfs,
                'count': len(pdfs),
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.exception(f"MongoDB error: {str(e)}")
            return Response({
                'success': True,
                'module_id': str(module_id),
                'pdfs': [],
                'count': 0,
                'note': 'MongoDB not available'
            }, status=status.HTTP_200_OK)
            
    except Module.DoesNotExist:
        return Response(
            {'success': False, 'error': 'Module not found'},
            status=status.HTTP_404_NOT_FOUND
        )
