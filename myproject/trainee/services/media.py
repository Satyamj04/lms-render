"""
Media File Serving View
Handles serving of PDF, PPT, and other resources from the media folder
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.http import FileResponse
from django.conf import settings
from trainee.models import LearningResource, Module, Course, User
from admin.models import CourseAssignment
from django.db.models import Q
import os
import mimetypes


@api_view(['GET'])
@permission_classes([AllowAny])
def get_resource_file(request, resource_id):
    """
    GET /api/trainee/resource/{resource_id}/file/
    Serve PDF, PPT, and other resource files from the media folder
    """
    try:
        user = User.objects.get(email=request.user.email)
        resource = get_object_or_404(LearningResource, resource_id=resource_id)
        
        # Verify user has access through the module's course
        module = resource.module
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
        
        # Check if file exists
        if not os.path.exists(file_path):
            return Response(
                {'error': 'File not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get file size and mime type
        file_size = os.path.getsize(file_path)
        mime_type, _ = mimetypes.guess_type(file_path)
        
        if not mime_type:
            # Default mime types for common file extensions
            ext = os.path.splitext(file_path)[1].lower()
            mime_types = {
                '.pdf': 'application/pdf',
                '.ppt': 'application/vnd.ms-powerpoint',
                '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                '.doc': 'application/msword',
                '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                '.xls': 'application/vnd.ms-excel',
                '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                '.txt': 'text/plain',
                '.zip': 'application/zip',
            }
            mime_type = mime_types.get(ext, 'application/octet-stream')
        
        # Serve the file
        response = FileResponse(
            open(file_path, 'rb'),
            content_type=mime_type,
            as_attachment=False
        )
        response['Content-Length'] = file_size
        response['Content-Disposition'] = f'inline; filename="{os.path.basename(file_path)}"'
        
        return response
        
    except LearningResource.DoesNotExist:
        return Response(
            {'error': 'Resource not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_media_files_list(request, folder_type):
    """
    GET /api/trainee/media/{folder_type}/list/
    List all files in a media folder (videos, pdfs, ppts)
    folder_type: 'videos', 'pdf', 'ppt'
    """
    try:
        if folder_type not in ['videos', 'pdf', 'ppt']:
            return Response(
                {'error': 'Invalid folder type'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        folder_path = os.path.join(settings.MEDIA_ROOT, folder_type)
        
        if not os.path.exists(folder_path):
            return Response({
                'folder': folder_type,
                'files': []
            })
        
        files = []
        try:
            for filename in os.listdir(folder_path):
                file_path = os.path.join(folder_path, filename)
                if os.path.isfile(file_path):
                    file_size = os.path.getsize(file_path)
                    files.append({
                        'name': filename,
                        'size': file_size,
                        'path': f'/media/{folder_type}/{filename}'
                    })
        except PermissionError:
            pass
        
        return Response({
            'folder': folder_type,
            'files': files
        })
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
