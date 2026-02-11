"""
Trainee Courses API - Returns enrolled courses for the current trainee
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from admin.models import UserProfile
from django.db import connection


@api_view(['POST'])
@permission_classes([AllowAny])
def get_trainee_courses(request):
    """
    Get enrolled courses for a trainee
    Request body: {"user_id": "uuid"}
    Returns list of courses assigned to this trainee
    """
    user_id = request.data.get('user_id')
    email = request.data.get('email')
    
    if not user_id and not email:
        return Response(
            {'success': False, 'error': 'user_id or email is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Get user by ID or email
        if user_id:
            user = UserProfile.objects.get(id=user_id)
        else:
            user = UserProfile.objects.get(email__iexact=email)
    except UserProfile.DoesNotExist:
        return Response(
            {'success': False, 'courses': [], 'stats': {
                'total_courses': 0,
                'active_courses': 0,
                'completed_courses': 0
            }},
            status=status.HTTP_200_OK
        )
    
    # Query the database to get enrolled courses
    try:
        with connection.cursor() as cursor:
            # Get courses assigned to this user from enrollments table
            cursor.execute("""
                SELECT 
                    c.course_id,
                    c.title,
                    c.description,
                    c.estimated_duration_hours,
                    c.status,
                    COUNT(m.module_id) as total_modules
                FROM courses c
                LEFT JOIN modules m ON c.course_id = m.course_id
                WHERE c.course_id IN (
                    SELECT course_id FROM enrollments 
                    WHERE user_id = %s AND status = 'assigned'
                )
                GROUP BY c.course_id, c.title, c.description, c.estimated_duration_hours, c.status
                ORDER BY c.created_at DESC
            """, [str(user.id)])
            
            columns = [col[0] for col in cursor.description]
            courses = []
            for row in cursor.fetchall():
                course_dict = dict(zip(columns, row))
                courses.append({
                    'course_id': str(course_dict['course_id']),
                    'id': str(course_dict['course_id']),
                    'title': course_dict['title'],
                    'description': course_dict['description'] or '',
                    'status': 'active',
                    'completion_percentage': 0,
                    'total_modules': course_dict['total_modules'] or 0,
                    'duration': f"{course_dict['estimated_duration_hours']} hours" if course_dict['estimated_duration_hours'] else "Unknown",
                })
        
        # Calculate stats
        total = len(courses)
        
        return Response({
            'success': True,
            'courses': courses,
            'stats': {
                'total_courses': total,
                'active_courses': total,
                'completed_courses': 0,
                'not_started_courses': 0
            },
            'rank': {
                'rank': 1,
                'points': 0,
                'total_active_hours': 0
            },
            'leaderboard': [],
            'badges': []
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        print(f"Error fetching courses: {str(e)}")
        return Response(
            {'success': False, 'error': str(e), 'courses': [], 'stats': {
                'total_courses': 0,
                'active_courses': 0,
                'completed_courses': 0
            }},
            status=status.HTTP_200_OK
        )

@api_view(['GET'])
@permission_classes([AllowAny])
def get_course_detail(request, course_id):
    """
    Get course detail with modules
    Returns course info + list of modules
    """
    try:
        with connection.cursor() as cursor:
            # Get course details
            cursor.execute("""
                SELECT 
                    course_id,
                    title,
                    description,
                    estimated_duration_hours,
                    status,
                    created_at
                FROM courses
                WHERE course_id = %s
            """, [course_id])
            
            course_row = cursor.fetchone()
            if not course_row:
                return Response(
                    {'success': False, 'error': 'Course not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            course_columns = [col[0] for col in cursor.description]
            course_data = dict(zip(course_columns, course_row))
            
            # Get modules for this course
            cursor.execute("""
                SELECT 
                    module_id,
                    title,
                    description,
                    module_type,
                    sequence_order,
                    estimated_duration_minutes,
                    is_mandatory
                FROM modules
                WHERE course_id = %s
                ORDER BY sequence_order ASC
            """, [course_id])
            
            modules_rows = cursor.fetchall()
            modules = []
            if modules_rows:
                modules_columns = [col[0] for col in cursor.description]
                for row in modules_rows:
                    module_dict = dict(zip(modules_columns, row))
                    modules.append({
                        'id': str(module_dict['module_id']),
                        'title': module_dict['title'],
                        'description': module_dict['description'],
                        'type': module_dict['module_type'],
                        'position': module_dict['sequence_order'],
                        'duration': module_dict['estimated_duration_minutes'],
                        'mandatory': module_dict['is_mandatory'],
                    })
        
        return Response({
            'success': True,
            'course': {
                'id': str(course_data['course_id']),
                'course_id': str(course_data['course_id']),
                'title': course_data['title'],
                'description': course_data['description'],
                'status': course_data['status'],
                'modules': modules,
                'module_count': len(modules),
            }
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        print(f"Error fetching course details: {str(e)}")
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )