"""
Media handling utilities for LMS
Handles linking and managing media files from C:\LMS_uploads
"""

import os
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from django.core.files.storage import default_storage
from trainee.models import MediaMetadata, Module, User, VideoUnit, AudioUnit, PresentationUnit, ScormPackage


class MediaHandler:
    """Handle media file operations and linking"""
    
    MEDIA_ROOT = r"C:\LMS_uploads"
    
    # File type mappings
    VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm', '.3gp'}
    AUDIO_EXTENSIONS = {'.mp3', '.wav', '.aac', '.flac', '.m4a', '.wma', '.ogg'}
    PRESENTATION_EXTENSIONS = {'.ppt', '.pptx', '.pdf', '.odp'}
    SCORM_EXTENSIONS = {'.zip', '.scorm'}
    
    @classmethod
    def get_file_type(cls, file_path: str) -> str:
        """Determine file type from extension"""
        ext = Path(file_path).suffix.lower()
        
        if ext in cls.VIDEO_EXTENSIONS:
            return 'video'
        elif ext in cls.AUDIO_EXTENSIONS:
            return 'audio'
        elif ext in cls.PRESENTATION_EXTENSIONS:
            return 'presentation' if ext in {'.ppt', '.pptx', '.odp'} else 'pdf'
        elif ext in cls.SCORM_EXTENSIONS:
            return 'scorm'
        else:
            return 'document'
    
    @classmethod
    def scan_media_directory(cls) -> Dict[str, List[Dict]]:
        """
        Scan the media directory and organize files by type
        Returns: {file_type: [file_info_dict, ...]}
        """
        media_files = {
            'video': [],
            'audio': [],
            'presentation': [],
            'pdf': [],
            'scorm': [],
            'document': []
        }
        
        if not os.path.exists(cls.MEDIA_ROOT):
            print(f"[WARNING] Media directory not found: {cls.MEDIA_ROOT}")
            return media_files
        
        for root, dirs, files in os.walk(cls.MEDIA_ROOT):
            for file in files:
                file_path = os.path.join(root, file)
                file_size = os.path.getsize(file_path)
                
                file_info = {
                    'name': file,
                    'path': file_path,
                    'relative_path': os.path.relpath(file_path, cls.MEDIA_ROOT),
                    'size': file_size,
                    'mime_type': mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
                }
                
                file_type = cls.get_file_type(file_path)
                media_files[file_type].append(file_info)
        
        return media_files
    
    @classmethod
    def create_media_metadata(cls, file_info: Dict, unit: Optional[Module] = None, 
                            uploaded_by: Optional[User] = None) -> MediaMetadata:
        """Create MediaMetadata record for a file"""
        file_type = cls.get_file_type(file_info['path'])
        
        metadata = MediaMetadata.objects.create(
            storage_path=file_info['relative_path'],
            file_name=file_info['name'],
            file_type=file_type,
            file_size=file_info['size'],
            mime_type=file_info['mime_type'],
            unit=unit,
            uploaded_by=uploaded_by,
            storage_type='local'
        )
        
        return metadata
    
    @classmethod
    def link_media_to_module(cls, file_info: Dict, module: Module, 
                           uploaded_by: Optional[User] = None) -> Optional[object]:
        """
        Link media file to a module and create appropriate content model
        Returns: Created model instance (VideoUnit, AudioUnit, etc.)
        """
        file_type = cls.get_file_type(file_info['path'])
        file_path = file_info['path']
        
        # Create metadata record
        metadata = cls.create_media_metadata(file_info, module, uploaded_by)
        
        # Create type-specific content unit
        content_unit = None
        
        try:
            if file_type == 'video':
                # Get video duration (basic)
                content_unit = VideoUnit.objects.create(
                    unit=module,
                    video_storage_path=file_info['relative_path'],
                    video_url=f"/media/{file_info['relative_path']}",
                    duration=0,  # Would need video processing library for real duration
                    completion_type='full'
                )
                print(f"[OK] Created VideoUnit: {module.title}")
            
            elif file_type == 'audio':
                content_unit = AudioUnit.objects.create(
                    unit=module,
                    audio_storage_path=file_info['relative_path'],
                    audio_url=f"/media/{file_info['relative_path']}",
                    duration=0  # Would need audio processing library
                )
                print(f"[OK] Created AudioUnit: {module.title}")
            
            elif file_type == 'presentation' or file_type == 'pdf':
                content_unit = PresentationUnit.objects.create(
                    unit=module,
                    file_storage_path=file_info['relative_path'],
                    file_url=f"/media/{file_info['relative_path']}",
                    slide_count=0
                )
                print(f"[OK] Created PresentationUnit: {module.title}")
            
            elif file_type == 'scorm':
                content_unit = ScormPackage.objects.create(
                    unit=module,
                    file_storage_path=file_info['relative_path'],
                    file_url=f"/media/{file_info['relative_path']}",
                    package_type='scorm_1_2',
                    completion_tracking=True,
                    score_tracking=True
                )
                print(f"[OK] Created ScormPackage: {module.title}")
            
        except Exception as e:
            print(f"[ERROR] Error creating content unit for {file_info['name']}: {str(e)}")
        
        return content_unit
    
    @classmethod
    def get_media_stats(cls) -> Dict:
        """Get statistics about media directory"""
        media_files = cls.scan_media_directory()
        stats = {}
        total_size = 0
        total_files = 0
        
        for file_type, files in media_files.items():
            if files:
                size = sum(f['size'] for f in files)
                stats[file_type] = {
                    'count': len(files),
                    'total_size': size,
                    'total_size_mb': round(size / (1024*1024), 2)
                }
                total_size += size
                total_files += len(files)
        
        stats['total'] = {
            'count': total_files,
            'total_size': total_size,
            'total_size_mb': round(total_size / (1024*1024), 2)
        }
        
        return stats
