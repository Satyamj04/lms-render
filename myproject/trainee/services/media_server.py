"""
Simple media serving endpoint for local media files
Fetches videos, PDFs, and PPTs from the local folder
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
import os
import mimetypes
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Local media folder path
MEDIA_FOLDER = r'C:\Users\mukesh.pawar\OneDrive - Ampcus Tech Pvt Ltd\Desktop\media'

def get_file_type(filename):
    """Determine file type from extension"""
    ext = os.path.splitext(filename)[1].lower()
    
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv']
    pdf_extensions = ['.pdf']
    ppt_extensions = ['.ppt', '.pptx']
    
    if ext in video_extensions:
        return 'video'
    elif ext in pdf_extensions:
        return 'pdf'
    elif ext in ppt_extensions:
        return 'ppt'
    else:
        return 'document'

@api_view(['GET'])
@permission_classes([AllowAny])
def get_all_media_files(request):
    """
    GET /api/trainee/media/files/
    Get all media files from the local folder
    """
    try:
        if not os.path.exists(MEDIA_FOLDER):
            return Response({
                'success': False,
                'error': f'Media folder not found: {MEDIA_FOLDER}',
                'files': []
            }, status=status.HTTP_404_NOT_FOUND)
        
        media_files = []
        
        # List all files in media folder
        for filename in os.listdir(MEDIA_FOLDER):
            filepath = os.path.join(MEDIA_FOLDER, filename)
            
            # Skip directories
            if not os.path.isfile(filepath):
                continue
            
            # Skip system files
            if filename.startswith('.') or filename.startswith('~'):
                continue
            
            # Get file info
            file_type = get_file_type(filename)
            file_size = os.path.getsize(filepath)
            file_modified = datetime.fromtimestamp(os.path.getmtime(filepath))
            
            media_files.append({
                'id': filename,
                'name': filename,
                'title': os.path.splitext(filename)[0],
                'type': file_type,
                'file_type': file_type,
                'content_type': file_type,
                'size_bytes': file_size,
                'size_mb': round(file_size / (1024*1024), 2),
                'url': f'/media/{filename}',
                'modified': file_modified.isoformat(),
                'extension': os.path.splitext(filename)[1].lower()
            })
        
        # Sort by type and name
        media_files.sort(key=lambda x: (x['type'], x['name']))
        
        # Group by type
        videos = [f for f in media_files if f['type'] == 'video']
        pdfs = [f for f in media_files if f['type'] == 'pdf']
        ppts = [f for f in media_files if f['type'] == 'ppt']
        
        return Response({
            'success': True,
            'total': len(media_files),
            'videos': videos,
            'video_count': len(videos),
            'pdfs': pdfs,
            'pdf_count': len(pdfs),
            'ppts': ppts,
            'ppt_count': len(ppts),
            'all_files': media_files
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.exception(f"Error fetching media files: {str(e)}")
        return Response({
            'success': False,
            'error': str(e),
            'files': []
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_media_by_type(request, file_type):
    """
    GET /api/trainee/media/{type}/
    Get media files of specific type (video, pdf, ppt)
    """
    try:
        if not os.path.exists(MEDIA_FOLDER):
            return Response({
                'success': False,
                'error': 'Media folder not found',
                'files': []
            }, status=status.HTTP_404_NOT_FOUND)
        
        media_files = []
        
        # List files of specified type
        for filename in os.listdir(MEDIA_FOLDER):
            filepath = os.path.join(MEDIA_FOLDER, filename)
            
            if not os.path.isfile(filepath):
                continue
            
            if filename.startswith('.') or filename.startswith('~'):
                continue
            
            if get_file_type(filename) == file_type:
                file_size = os.path.getsize(filepath)
                file_modified = datetime.fromtimestamp(os.path.getmtime(filepath))
                
                media_files.append({
                    'id': filename,
                    'name': filename,
                    'title': os.path.splitext(filename)[0],
                    'type': file_type,
                    'size_bytes': file_size,
                    'size_mb': round(file_size / (1024*1024), 2),
                    'url': f'/media/{filename}',
                    'modified': file_modified.isoformat(),
                })
        
        media_files.sort(key=lambda x: x['name'])
        
        return Response({
            'success': True,
            'type': file_type,
            'total': len(media_files),
            'files': media_files
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.exception(f"Error fetching {file_type} files: {str(e)}")
        return Response({
            'success': False,
            'error': str(e),
            'files': []
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
