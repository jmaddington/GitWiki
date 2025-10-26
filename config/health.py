"""
Health check endpoint for monitoring and load balancer probes.

AIDEV-NOTE: health-check; System health monitoring endpoint for production
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.db import connection
from django.core.cache import cache
import logging
import time

logger = logging.getLogger(__name__)


@never_cache
@require_http_methods(["GET"])
def health_check(request):
    """
    Health check endpoint for monitoring systems and load balancers.

    Returns 200 OK if all systems are healthy, 503 Service Unavailable if any critical system is down.

    Checks:
    - Database connectivity
    - Redis cache connectivity
    - Git repository accessibility

    GET /health/
    """
    start_time = time.time()
    checks = {}
    overall_healthy = True

    # Check database
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks['database'] = {
            'status': 'healthy',
            'message': 'Database connection successful'
        }
        logger.debug('Health check: Database OK [HEALTH-DB01]')
    except Exception as e:
        checks['database'] = {
            'status': 'unhealthy',
            'message': f'Database error: {str(e)}'
        }
        overall_healthy = False
        logger.error(f'Health check: Database failed - {str(e)} [HEALTH-DB02]')

    # Check Redis cache
    try:
        cache_test_key = 'health_check_test'
        cache_test_value = 'ok'
        cache.set(cache_test_key, cache_test_value, 10)
        retrieved_value = cache.get(cache_test_key)

        if retrieved_value == cache_test_value:
            checks['cache'] = {
                'status': 'healthy',
                'message': 'Redis cache operational'
            }
            logger.debug('Health check: Redis OK [HEALTH-CACHE01]')
        else:
            checks['cache'] = {
                'status': 'unhealthy',
                'message': 'Redis cache not returning correct values'
            }
            overall_healthy = False
            logger.error('Health check: Redis cache failed [HEALTH-CACHE02]')
    except Exception as e:
        checks['cache'] = {
            'status': 'unhealthy',
            'message': f'Redis error: {str(e)}'
        }
        overall_healthy = False
        logger.error(f'Health check: Redis failed - {str(e)} [HEALTH-CACHE03]')

    # Check Git repository
    try:
        from git_service.git_operations import get_repository
        repo = get_repository()

        # Check if repository is accessible
        branches = repo.list_branches()
        if 'main' in branches:
            checks['repository'] = {
                'status': 'healthy',
                'message': 'Git repository accessible',
                'branches_count': len(branches)
            }
            logger.debug('Health check: Git repository OK [HEALTH-GIT01]')
        else:
            checks['repository'] = {
                'status': 'degraded',
                'message': 'Git repository accessible but main branch not found',
                'branches_count': len(branches)
            }
            logger.warning('Health check: Main branch not found [HEALTH-GIT02]')
    except Exception as e:
        checks['repository'] = {
            'status': 'unhealthy',
            'message': f'Repository error: {str(e)}'
        }
        overall_healthy = False
        logger.error(f'Health check: Git repository failed - {str(e)} [HEALTH-GIT03]')

    # Calculate response time
    response_time_ms = int((time.time() - start_time) * 1000)

    # Build response
    response_data = {
        'status': 'healthy' if overall_healthy else 'unhealthy',
        'timestamp': time.time(),
        'checks': checks,
        'response_time_ms': response_time_ms
    }

    # Return appropriate status code
    status_code = 200 if overall_healthy else 503

    if not overall_healthy:
        logger.warning(f'Health check failed: {response_data} [HEALTH-FAIL01]')

    return JsonResponse(response_data, status=status_code)


@never_cache
@require_http_methods(["GET"])
def readiness_check(request):
    """
    Readiness probe for Kubernetes and orchestration systems.

    Returns 200 OK if the application is ready to serve traffic.
    This is lighter than health_check and only verifies the app is running.

    GET /ready/
    """
    try:
        # Minimal check - just ensure Django is running
        response_data = {
            'status': 'ready',
            'timestamp': time.time()
        }
        logger.debug('Readiness check: OK [HEALTH-READY01]')
        return JsonResponse(response_data, status=200)
    except Exception as e:
        logger.error(f'Readiness check failed: {str(e)} [HEALTH-READY02]')
        return JsonResponse({
            'status': 'not_ready',
            'message': str(e)
        }, status=503)


@never_cache
@require_http_methods(["GET"])
def liveness_check(request):
    """
    Liveness probe for Kubernetes and orchestration systems.

    Returns 200 OK if the application is alive (not deadlocked/crashed).
    This is the most minimal check possible.

    GET /alive/
    """
    try:
        response_data = {
            'status': 'alive',
            'timestamp': time.time()
        }
        logger.debug('Liveness check: OK [HEALTH-ALIVE01]')
        return JsonResponse(response_data, status=200)
    except Exception as e:
        logger.error(f'Liveness check failed: {str(e)} [HEALTH-ALIVE02]')
        return JsonResponse({
            'status': 'dead',
            'message': str(e)
        }, status=503)
