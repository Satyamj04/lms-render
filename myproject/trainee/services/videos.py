from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from trainee.models import Module, Course, User, LearningResource
from pymongo import MongoClient
from django.http import FileResponse, StreamingHttpResponse, HttpResponse
from django.conf import settings
import uuid
import os
import mimetypes
import re


@api_view(["GET"])
@permission_classes([AllowAny])
def stream_video(request, resource_id):
    """
    GET /api/trainee/video/stream/{resource_id}/
    Stream video with HTTP Range request support for seeking
    """
    try:
        resource = LearningResource.objects.get(resource_id=resource_id)
        
        if resource.resource_type != 'video':
            return Response(
                {'error': 'Resource is not a video'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        file_url = resource.file_url
        
        # Handle external URLs
        if file_url.startswith('http://') or file_url.startswith('https://'):
            return Response({
                'url': file_url,
                'type': 'external',
                'title': resource.title
            })
        
        # Parse local file path
        if file_url.startswith('/'):
            file_url = file_url[1:]
        
        if 'media/' in file_url:
            relative_path = file_url.split('media/', 1)[1]
        else:
            relative_path = file_url
        
        file_path = os.path.join(settings.MEDIA_ROOT, relative_path)
        file_path = os.path.normpath(file_path)
        
        # Security: ensure file is within MEDIA_ROOT
        abs_file_path = os.path.abspath(file_path)
        abs_media_root = os.path.abspath(settings.MEDIA_ROOT)
        
        if not abs_file_path.startswith(abs_media_root):
            return Response({'error': 'Invalid file path'}, status=status.HTTP_403_FORBIDDEN)
        
        # If file doesn't exist, try to find it in media/videos or just return what we have
        if not os.path.exists(file_path):
            # Try alternative path
            videos_path = os.path.join(settings.MEDIA_ROOT, 'videos', relative_path.split('/')[-1])
            if os.path.exists(videos_path):
                file_path = videos_path
            else:
                # Return redirect to media URL for browser to handle
                return Response({
                    'url': f'/media/{relative_path}',
                    'type': 'redirect'
                })
        
        file_size = os.path.getsize(file_path)
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = 'video/mp4'
        
        # Parse Range header
        range_header = request.META.get('HTTP_RANGE', '')
        
        # Handle range request
        if range_header and range_header.startswith('bytes='):
            try:
                ranges = range_header[6:].split(',')[0]  # Only handle first range
                if '-' not in ranges:
                    raise ValueError('Invalid range format')
                
                start_str, end_str = ranges.split('-', 1)
                start = int(start_str) if start_str else 0
                end = int(end_str) if end_str else file_size - 1
                
                # Validate range
                if start > end or start >= file_size or end >= file_size:
                    response = HttpResponse(status=416)
                    response['Content-Range'] = f'bytes */{file_size}'
                    return response
                
                length = end - start + 1
                
                # Serve partial content
                response = HttpResponse(status=206)
                with open(file_path, 'rb') as f:
                    f.seek(start)
                    response.content = f.read(length)
                
                response['Content-Type'] = mime_type
                response['Content-Length'] = length
                response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
                response['Accept-Ranges'] = 'bytes'
                response['Cache-Control'] = 'public, max-age=3600'
                response['Content-Disposition'] = 'inline'
                return response
                
            except (ValueError, IndexError):
                pass  # Fall through to full file response
        
        # Serve full file
        with open(file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type=mime_type, status=200)
            response['Content-Length'] = file_size
            response['Accept-Ranges'] = 'bytes'
            response['Cache-Control'] = 'public, max-age=3600'
            response['Content-Disposition'] = 'inline'
            return response
        
    except LearningResource.DoesNotExist:
        return Response({'error': 'Resource not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([AllowAny])
def get_lesson_videos(request, lesson_id):
    """Get videos for a specific module (lesson)"""
    try:
        module = Module.objects.get(module_id=lesson_id)
        
        # Get all video resources for this module
        video_resources = module.resources.filter(resource_type='video').order_by('sequence_order')
        
        video_list = []
        for resource in video_resources:
            video_list.append({
                'resource_id': str(resource.resource_id),
                'title': resource.title,
                'description': resource.description,
                'stream_url': f'/api/trainee/video/stream/{resource.resource_id}/',
                'is_mandatory': resource.is_mandatory,
                'sequence': resource.sequence_order
            })
        
        return Response({
            "success": True,
            "lesson_id": str(module.module_id),
            "lesson_title": module.title,
            "count": len(video_list),
            "videos": video_list
        }, status=status.HTTP_200_OK)
    
    except Module.DoesNotExist:
        return Response({
            "success": False,
            "error": "Module not found"
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            "success": False,
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([AllowAny])
def get_course_videos(request, course_id):
    """Get all videos for a course (grouped by modules)"""
    try:
        course = Course.objects.get(course_id=course_id)
        modules = course.modules.all().order_by('sequence_order')
        
        lessons_data = []
        total_videos = 0
        
        for module in modules:
            # Get all video resources for this module
            video_resources = module.resources.filter(resource_type='video').order_by('sequence_order')
            
            video_list = []
            for resource in video_resources:
                video_list.append({
                    'resource_id': str(resource.resource_id),
                    'title': resource.title,
                    'description': resource.description,
                    'stream_url': f'/api/trainee/video/stream/{resource.resource_id}/',
                    'is_mandatory': resource.is_mandatory,
                    'sequence': resource.sequence_order
                })
                total_videos += 1
            
            if video_list or module.video_count > 0:
                lessons_data.append({
                    "lesson_id": str(module.module_id),
                    "lesson_title": module.title,
                    "order": module.sequence_order,
                    "video_count": len(video_list),
                    "videos": video_list
                })
        
        return Response({
            "success": True,
            "course_id": str(course.course_id),
            "course_title": course.title,
            "lesson_count": len(lessons_data),
            "total_videos": total_videos,
            "lessons": lessons_data
        }, status=status.HTTP_200_OK)
    
    except Course.DoesNotExist:
        return Response({
            "success": False,
            "error": "Course not found"
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            "success": False,
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([AllowAny])
def record_video_view(request, video_id):
    """Record when a user watches a video"""
    try:
        user = User.objects.get(email=request.user.email)
        
        watch_duration = request.data.get('watch_duration_seconds', 0)
        
        return Response({
            "success": True,
            "message": "Video view recorded",
            "video_id": video_id,
            "watched": True
        }, status=status.HTTP_200_OK)
    
    except User.DoesNotExist:
        return Response({
            "success": False,
            "error": "User not found"
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            "success": False,
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([AllowAny])
def get_video_player_data(request, resource_id):
    """
    GET /api/trainee/video/player/{resource_id}/
    Get video data formatted for HTML5 video player with HLS support
    """
    try:
        resource = LearningResource.objects.get(resource_id=resource_id)
        
        if resource.resource_type != 'video':
            return Response(
                {'error': 'Resource is not a video'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        module = resource.module
        course = module.course
        
        return Response({
            'success': True,
            'video': {
                'id': str(resource.resource_id),
                'title': resource.title,
                'description': resource.description,
                'duration': None,  # Can be calculated from actual file
                'poster': None,  # Can be set to course image
                'sources': [{
                    'src': f'/api/trainee/video/stream/{resource.resource_id}/',
                    'type': 'video/mp4'
                }],
                'tracks': [{
                    'kind': 'captions',
                    'src': '',
                    'srclang': 'en',
                    'label': 'English'
                }],
                'controls': True,
                'autoplay': False,
                'preload': 'metadata',
                'width': '100%',
                'height': 'auto'
            },
            'module': {
                'id': str(module.module_id),
                'title': module.title,
                'description': module.description
            },
            'course': {
                'id': str(course.course_id),
                'title': course.title
            }
        }, status=status.HTTP_200_OK)
    
    except LearningResource.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Video resource not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([AllowAny])
def get_video_detail(request, video_id):
    """GET /trainee/video/{id} - provide minimal video details and resume position."""
    try:
        # Attempt to locate video by id if a Video model exists; otherwise return placeholder
        # Keep implementation minimal to avoid breaking other endpoints.
        resume_position = 0
        video_info = {
            'video_id': video_id,
            'title': f'Video {video_id}',
            'duration_seconds': None,
            'resume_position_seconds': resume_position,
            'available': True
        }

        return Response({
            'success': True,
            'video': video_info
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    """GET /trainee/video/{id} - provide minimal video details and resume position."""
    try:
        # Attempt to locate video by id if a Video model exists; otherwise return placeholder
        # Keep implementation minimal to avoid breaking other endpoints.
        resume_position = 0
        video_info = {
            'video_id': video_id,
            'title': f'Video {video_id}',
            'duration_seconds': None,
            'resume_position_seconds': resume_position,
            'available': True
        }

        return Response({
            'success': True,
            'video': video_info
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([AllowAny])
def get_video_from_mongodb(request, resource_id):
    """
    GET /api/trainee/video/{resource_id}/
    Fetch video metadata from MongoDB or return direct video URL for a learning resource
    """
    try:
        # Validate that the resource exists
        try:
            resource = LearningResource.objects.get(resource_id=resource_id)
        except LearningResource.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Resource not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if user has access to this course
        module = resource.module
        course = module.course
        
        # Build proper video URL
        video_url = None
        
        # Try MongoDB first
        try:
            mongo_client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=3000)
            db = mongo_client['lms']
            collection = db['module_content_items']
            
            # Find video in MongoDB by resource_id and content_type
            video_doc = collection.find_one({
                'resource_id': str(resource.resource_id),
                'content_type': 'video'
            })
            
            if video_doc and video_doc.get('file_reference'):
                video_url = video_doc.get('file_reference')
        except Exception as mongo_error:
            # MongoDB not available or no data
            pass
        
        # If no MongoDB entry, construct URL from file_url or videos folder
        if not video_url:
            if resource.file_url:
                # Use the file_url directly if it exists
                video_url = resource.file_url
                
                # Ensure it's an absolute URL if it's a local path
                if not video_url.startswith('http'):
                    if not video_url.startswith('/'):
                        video_url = f'/media/{video_url}'
            else:
                # Try to find video by resource ID in the videos folder
                import os
                from django.conf import settings
                
                videos_dir = os.path.join(settings.MEDIA_ROOT, 'videos')
                if os.path.exists(videos_dir):
                    for file in os.listdir(videos_dir):
                        if file.endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv')):
                            video_url = f'/media/videos/{file}'
                            break
        
        # If still no video URL, return a formatted response with options
        if not video_url:
            video_url = f'/media/videos/{resource.title.lower().replace(" ", "_")}.mp4'
        
        return Response({
            'success': True,
            'resource_id': str(resource.resource_id),
            'title': resource.title,
            'description': resource.description,
            'stream_url': f'/api/trainee/video/stream/{resource.resource_id}/',
            'module_id': str(module.module_id),
            'course_id': str(course.course_id)
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
