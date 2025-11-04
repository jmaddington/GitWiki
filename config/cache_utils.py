"""
Cache utility functions for invalidating caches after content updates.

AIDEV-NOTE: cache-invalidation; Clear caches after git operations to ensure fresh data
"""

from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


def _supports_pattern_deletion():
    """
    Check if the cache backend supports pattern-based deletion.

    Returns:
        bool: True if cache.delete_pattern() is available (e.g., Redis backend)
    """
    return hasattr(cache, 'delete_pattern') and callable(getattr(cache, 'delete_pattern'))


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
        if _supports_pattern_deletion():
            # Redis backend supports pattern deletion
            patterns = [
                f'metadata:{branch_name}:*',
                f'directory:{branch_name}:*',
                f'search:{branch_name}:*'
            ]

            deleted_count = 0
            for pattern in patterns:
                deleted = cache.delete_pattern(pattern)
                deleted_count += deleted if isinstance(deleted, int) else 0

            logger.info(f'Pattern deletion supported, cleared {deleted_count} keys for branch: {branch_name} [CACHE-PATTERN01]')
        else:
            # Fallback: rely on TTL expiration
            logger.info(f'Pattern deletion not supported, relying on TTL for branch: {branch_name} [CACHE-PATTERN02]')

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
        if _supports_pattern_deletion():
            # Redis backend supports pattern deletion
            if branch_name:
                pattern = f'search:{branch_name}:*'
            else:
                pattern = 'search:*'

            deleted = cache.delete_pattern(pattern)
            deleted_count = deleted if isinstance(deleted, int) else 0

            logger.info(f'Pattern deletion supported, cleared {deleted_count} search cache keys for branch: {branch_name or "all"} [CACHE-PATTERN03]')
        else:
            # Fallback: rely on TTL expiration (5 minutes)
            logger.info(f'Pattern deletion not supported, relying on TTL for search cache: {branch_name or "all"} [CACHE-PATTERN04]')

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
