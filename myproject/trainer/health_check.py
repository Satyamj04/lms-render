"""
Health Check Views

Provides comprehensive health check endpoints for monitoring system status:
- Database connectivity
- API responsiveness
- Service dependencies
- System readiness
"""

import logging
from django.http import JsonResponse
from django.db import connection
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


class HealthCheckService:
    """Service for performing health checks on system components."""
    
    @staticmethod
    def check_database():
        """
        Check database connectivity and basic operations.
        
        Returns:
            dict: Health status with details
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return {
                'status': 'healthy',
                'database': 'connected',
                'message': 'Database connection successful'
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                'status': 'unhealthy',
                'database': 'disconnected',
                'error': str(e)
            }
    
    @staticmethod
    def check_tables():
        """
        Verify that all required tables exist.
        
        Returns:
            dict: Table status with count
        """
        try:
            from django.apps import apps
            
            required_tables = []
            for model in apps.get_models():
                required_tables.append(model._meta.db_table)
            
            existing_tables = []
            with connection.cursor() as cursor:
                if 'postgresql' in connection.vendor:
                    cursor.execute("""
                        SELECT table_name FROM information_schema.tables 
                        WHERE table_schema = 'public'
                    """)
                elif 'sqlite' in connection.vendor:
                    cursor.execute("""
                        SELECT name FROM sqlite_master WHERE type='table'
                    """)
                elif 'mysql' in connection.vendor:
                    cursor.execute("SHOW TABLES")
                
                existing_tables = [row[0] for row in cursor.fetchall()]
            
            missing = set(required_tables) - set(existing_tables)
            
            return {
                'status': 'healthy' if not missing else 'degraded',
                'total_required': len(set(required_tables)),
                'total_existing': len(existing_tables),
                'missing': list(missing) if missing else []
            }
        except Exception as e:
            logger.error(f"Table health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    @staticmethod
    def check_api():
        """
        Check API responsiveness.
        
        Returns:
            dict: API status
        """
        try:
            return {
                'status': 'healthy',
                'api': 'responding',
                'message': 'API is ready to handle requests'
            }
        except Exception as e:
            logger.error(f"API health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    @staticmethod
    def get_system_status():
        """
        Get overall system health status.
        
        Returns:
            dict: Complete system status
        """
        database_status = HealthCheckService.check_database()
        table_status = HealthCheckService.check_tables()
        api_status = HealthCheckService.check_api()
        
        # Determine overall status
        statuses = [
            database_status.get('status'),
            table_status.get('status'),
            api_status.get('status')
        ]
        
        # Overall status is worst status among checks
        if 'unhealthy' in statuses:
            overall = 'unhealthy'
        elif 'degraded' in statuses:
            overall = 'degraded'
        else:
            overall = 'healthy'
        
        return {
            'status': overall,
            'timestamp': __import__('datetime').datetime.utcnow().isoformat(),
            'checks': {
                'database': database_status,
                'tables': table_status,
                'api': api_status
            }
        }


# Health Check Endpoints

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Simple health check endpoint.
    
    Returns:
        Response: JSON with health status
    """
    health = HealthCheckService.check_database()
    
    if health['status'] == 'healthy':
        return Response(health, status=status.HTTP_200_OK)
    else:
        return Response(health, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@api_view(['GET'])
@permission_classes([AllowAny])
def system_status(request):
    """
    Comprehensive system status endpoint.
    
    Returns:
        Response: JSON with complete system status
    """
    system_status_data = HealthCheckService.get_system_status()
    
    if system_status_data['status'] == 'healthy':
        return Response(system_status_data, status=status.HTTP_200_OK)
    elif system_status_data['status'] == 'degraded':
        return Response(system_status_data, status=status.HTTP_200_OK)
    else:
        return Response(system_status_data, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@api_view(['GET'])
@permission_classes([AllowAny])
def database_status(request):
    """
    Database status endpoint.
    
    Returns:
        Response: JSON with database and table information
    """
    db_status = HealthCheckService.check_database()
    table_status = HealthCheckService.check_tables()
    
    response_data = {
        'database': db_status,
        'tables': table_status
    }
    
    if db_status['status'] == 'healthy' and table_status['status'] in ['healthy', 'degraded']:
        return Response(response_data, status=status.HTTP_200_OK)
    else:
        return Response(response_data, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@api_view(['GET'])
@permission_classes([AllowAny])
def readiness_check(request):
    """
    Kubernetes-style readiness check.
    
    Returns:
        Response: 200 if system is ready to accept traffic, 503 otherwise
    """
    system_status_data = HealthCheckService.get_system_status()
    
    # System is ready if database is healthy and tables exist
    is_ready = (
        system_status_data['checks']['database']['status'] == 'healthy' and
        system_status_data['checks']['tables'].get('missing', []) == []
    )
    
    if is_ready:
        return Response(
            {'ready': True, 'message': 'System is ready'},
            status=status.HTTP_200_OK
        )
    else:
        return Response(
            {'ready': False, 'message': 'System is not ready', 'status': system_status_data},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def liveness_check(request):
    """
    Kubernetes-style liveness check.
    
    Returns:
        Response: 200 if service is running, 503 otherwise
    """
    try:
        # Simple check that service is running
        return Response(
            {'alive': True, 'message': 'Service is running'},
            status=status.HTTP_200_OK
        )
    except Exception as e:
        logger.error(f"Liveness check failed: {e}")
        return Response(
            {'alive': False, 'error': str(e)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
