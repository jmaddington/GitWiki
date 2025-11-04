"""
Rate limiting utilities for API endpoints.

AIDEV-NOTE: rate-limiting; Protect against abuse and spam
"""

from functools import wraps
from datetime import datetime, timedelta
from django.core.cache import cache
from django.http import JsonResponse
import logging

logger = logging.getLogger(__name__)


def rate_limit(max_requests=10, window_seconds=60, key_func=None):
    """
    Decorator to rate limit API endpoints using Django cache.

    Args:
        max_requests: Maximum number of requests allowed in the window
        window_seconds: Time window in seconds
        key_func: Optional function to generate cache key from request
                 Default: uses user ID if authenticated, else IP address

    Returns:
        Decorated function that enforces rate limiting

    Example:
        @rate_limit(max_requests=5, window_seconds=60)
        def my_view(request):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(request)
            else:
                # Default: use user ID if authenticated, else IP
                if request.user.is_authenticated:
                    identifier = f'user:{request.user.id}'
                else:
                    # Get IP address
                    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                    if x_forwarded_for:
                        ip = x_forwarded_for.split(',')[0]
                    else:
                        ip = request.META.get('REMOTE_ADDR')
                    identifier = f'ip:{ip}'

                cache_key = f'ratelimit:{func.__name__}:{identifier}'

            # Get current request count
            request_data = cache.get(cache_key, {'count': 0, 'reset_time': None})

            # Check if window has expired
            now = datetime.now()
            if request_data['reset_time']:
                reset_time = datetime.fromisoformat(request_data['reset_time'])
                if now >= reset_time:
                    # Window expired, reset count
                    request_data = {'count': 0, 'reset_time': None}

            # Set reset time if this is first request in window
            if request_data['reset_time'] is None:
                request_data['reset_time'] = (now + timedelta(seconds=window_seconds)).isoformat()

            # Check if rate limit exceeded
            if request_data['count'] >= max_requests:
                reset_time = datetime.fromisoformat(request_data['reset_time'])
                retry_after = int((reset_time - now).total_seconds())

                logger.warning(
                    f'Rate limit exceeded for {func.__name__} by {identifier} '
                    f'[RATELIMIT-{func.__name__.upper()}]'
                )

                return JsonResponse({
                    'success': False,
                    'error': {
                        'message': f'Rate limit exceeded. Maximum {max_requests} requests per {window_seconds} seconds.',
                        'code': 'RATE_LIMIT_EXCEEDED',
                        'retry_after': retry_after
                    }
                }, status=429)

            # Increment count
            request_data['count'] += 1

            # Save to cache with TTL
            cache.set(cache_key, request_data, timeout=window_seconds + 10)

            # Add rate limit headers to response
            response = func(self, request, *args, **kwargs)

            if hasattr(response, '__setitem__'):
                response['X-RateLimit-Limit'] = str(max_requests)
                response['X-RateLimit-Remaining'] = str(max_requests - request_data['count'])
                reset_time = datetime.fromisoformat(request_data['reset_time'])
                response['X-RateLimit-Reset'] = str(int(reset_time.timestamp()))

            return response

        return wrapper
    return decorator
