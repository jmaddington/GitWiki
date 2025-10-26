"""
Cache utility functions for invalidating caches after content updates.

AIDEV-NOTE: cache-invalidation; Clear caches after git operations to ensure fresh data
"""

from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


def invalidate_branch_cache(branch_name: str):
    """
    Invalidate all caches for a specific branch.

    Called after:
    - Branch merge to main
    - Static file regeneration
    - Content updates

    Args:
        branch_name: Name of branch to invalidate cache for
    """
    try:
        # Pattern matching for cache keys
        # Django's default cache doesn't support pattern deletion,
        # so we track what to delete

        # Clear metadata cache for this branch
        # Note: We can't iterate cache keys in Django's default cache backend,
        # so we'll just let items expire naturally or use cache versioning

        logger.info(f'Cache invalidation requested for branch: {branch_name} [CACHE-INVALIDATE01]')

        # For now, we'll rely on TTL expiration
        # In production with Redis, you could use cache.delete_pattern(f'*:{branch_name}:*')

    except Exception as e:
        logger.warning(f'Failed to invalidate cache for {branch_name}: {str(e)} [CACHE-INVALIDATE02]')


def invalidate_file_cache(branch_name: str, file_path: str):
    """
    Invalidate caches for a specific file.

    Called after:
    - File commit
    - File update
    - Conflict resolution

    Args:
        branch_name: Name of branch
        file_path: Path to file that was updated
    """
    try:
        # Clear metadata cache for this specific file
        metadata_key = f'metadata:{branch_name}:{file_path}'
        cache.delete(metadata_key)

        # Clear parent directory cache
        if '/' in file_path:
            parent_dir = '/'.join(file_path.split('/')[:-1])
            dir_key = f'directory:{branch_name}:{parent_dir}'
            cache.delete(dir_key)
        else:
            # Root directory
            dir_key = f'directory:{branch_name}:root'
            cache.delete(dir_key)

        logger.info(f'Cache invalidated for file: {branch_name}:{file_path} [CACHE-INVALIDATE03]')

    except Exception as e:
        logger.warning(f'Failed to invalidate file cache: {str(e)} [CACHE-INVALIDATE04]')


def invalidate_search_cache(branch_name: str = None):
    """
    Invalidate search result caches.

    Called after:
    - Content updates that could affect search results
    - Branch merges

    Args:
        branch_name: Optional branch name (if None, clears all search caches)
    """
    try:
        # Django's default cache doesn't support pattern deletion
        # In production with Redis, you could do:
        # if branch_name:
        #     cache.delete_pattern(f'search:{branch_name}:*')
        # else:
        #     cache.delete_pattern('search:*')

        logger.info(f'Search cache invalidation requested for branch: {branch_name or "all"} [CACHE-INVALIDATE05]')

        # For now, rely on TTL expiration (5 minutes)
        # This is acceptable since search results refresh quickly

    except Exception as e:
        logger.warning(f'Failed to invalidate search cache: {str(e)} [CACHE-INVALIDATE06]')


def clear_all_caches():
    """
    Clear all application caches.

    Use sparingly - only for:
    - Full static rebuild
    - Major configuration changes
    - Admin-triggered cache clear

    Returns:
        Dict with success status
    """
    try:
        cache.clear()
        logger.warning('All caches cleared [CACHE-CLEAR01]')

        return {
            'success': True,
            'message': 'All caches cleared successfully'
        }

    except Exception as e:
        error_msg = f'Failed to clear caches: {str(e)}'
        logger.error(f'{error_msg} [CACHE-CLEAR02]')

        return {
            'success': False,
            'message': error_msg
        }


def get_cache_stats():
    """
    Get cache statistics (if supported by cache backend).

    Returns:
        Dict with cache statistics or None if not supported
    """
    try:
        # Django's default cache backend doesn't provide stats
        # With Redis, you could get detailed stats
        # For now, just return a message

        logger.info('Cache stats requested [CACHE-STATS01]')

        return {
            'supported': False,
            'message': 'Cache statistics require Redis backend',
            'recommendation': 'Install Redis for production caching with statistics'
        }

    except Exception as e:
        logger.error(f'Failed to get cache stats: {str(e)} [CACHE-STATS02]')
        return None
