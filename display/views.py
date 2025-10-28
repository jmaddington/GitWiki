"""
Display service views for GitWiki.

Handles rendering of wiki pages, search, and navigation.

AIDEV-NOTE: display-views; Wiki page rendering and search functionality
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from django.shortcuts import render, redirect
from django.http import Http404, JsonResponse
from django.conf import settings
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.core.cache import cache

logger = logging.getLogger(__name__)


def _get_static_path(branch: str = 'main') -> Path:
    """
    Get path to static files for a branch.

    Args:
        branch: Branch name

    Returns:
        Path to static directory
    """
    return settings.WIKI_STATIC_PATH / branch


def _load_metadata(file_path: str, branch: str = 'main') -> Optional[Dict]:
    """
    Load metadata for a file with caching.

    AIDEV-NOTE: metadata-cache; Caches metadata for 1 hour to reduce disk I/O

    Args:
        file_path: Relative path to markdown file
        branch: Branch name

    Returns:
        Metadata dict or None
    """
    # Check cache first
    cache_key = f'metadata:{branch}:{file_path}'
    cached_metadata = cache.get(cache_key)

    if cached_metadata is not None:
        logger.debug(f'Metadata cache hit for {file_path} [DISPLAY-CACHE01]')
        return cached_metadata

    try:
        static_path = _get_static_path(branch)
        metadata_file = static_path / f"{file_path}.metadata"

        if metadata_file.exists():
            metadata = json.loads(metadata_file.read_text(encoding='utf-8'))
            # Cache for 1 hour (3600 seconds)
            cache.set(cache_key, metadata, 3600)
            logger.debug(f'Metadata cached for {file_path} [DISPLAY-CACHE02]')
            return metadata

        # Cache None result for 5 minutes to avoid repeated disk checks
        cache.set(cache_key, None, 300)
        return None
    except Exception as e:
        logger.warning(f'Failed to load metadata for {file_path}: {str(e)} [DISPLAY-META01]')
        return None


def _get_breadcrumbs(file_path: str) -> List[Dict[str, str]]:
    """
    Generate breadcrumb navigation from file path.

    Args:
        file_path: Relative path to file

    Returns:
        List of breadcrumb dicts with 'name' and 'url'
    """
    breadcrumbs = [{'name': 'Home', 'url': '/'}]

    if not file_path or file_path == '/':
        return breadcrumbs

    # Remove .md extension if present
    clean_path = file_path.replace('.md', '')

    parts = clean_path.split('/')
    current_path = ''

    for part in parts[:-1]:  # All but last (directories)
        current_path += f'{part}/'
        breadcrumbs.append({
            'name': part.replace('-', ' ').replace('_', ' ').title(),
            'url': f'/wiki/{current_path}'
        })

    # Last part (file name)
    if parts:
        breadcrumbs.append({
            'name': parts[-1].replace('-', ' ').replace('_', ' ').title(),
            'url': f'/wiki/{clean_path}'
        })

    return breadcrumbs


def _list_directory(directory: str, branch: str = 'main') -> List[Dict]:
    """
    List files and subdirectories in a directory with caching.

    AIDEV-NOTE: directory-cache; Caches directory listings for 10 minutes

    Args:
        directory: Directory path relative to static root
        branch: Branch name

    Returns:
        List of file/directory dicts
    """
    # Check cache first
    cache_key = f'directory:{branch}:{directory or "root"}'
    cached_listing = cache.get(cache_key)

    if cached_listing is not None:
        logger.debug(f'Directory cache hit for {directory or "root"} [DISPLAY-CACHE03]')
        return cached_listing

    try:
        static_path = _get_static_path(branch)
        dir_path = static_path / directory if directory else static_path

        if not dir_path.exists() or not dir_path.is_dir():
            # Cache empty result for 5 minutes
            cache.set(cache_key, [], 300)
            return []

        items = []

        for item in sorted(dir_path.iterdir()):
            # Skip hidden files and metadata files
            if item.name.startswith('.') or item.name.endswith('.metadata'):
                continue

            if item.is_dir():
                items.append({
                    'name': item.name,
                    'type': 'directory',
                    'url': f'/wiki/{directory}/{item.name}' if directory else f'/wiki/{item.name}',
                    'path': f'{directory}/{item.name}' if directory else item.name
                })
            elif item.suffix == '.md':
                # Get the corresponding HTML file
                html_file = item.with_suffix('.html')
                if html_file.exists():
                    rel_path = item.relative_to(static_path)
                    clean_path = str(rel_path).replace('.md', '')
                    items.append({
                        'name': item.stem.replace('-', ' ').replace('_', ' ').title(),
                        'type': 'file',
                        'url': f'/wiki/{clean_path}',
                        'path': str(rel_path)
                    })

        # Cache for 10 minutes (600 seconds)
        cache.set(cache_key, items, 600)
        logger.debug(f'Directory cached for {directory or "root"} [DISPLAY-CACHE04]')

        return items

    except Exception as e:
        logger.error(f'Failed to list directory {directory}: {str(e)} [DISPLAY-DIR01]')
        return []


@require_http_methods(["GET"])
def wiki_home(request):
    """
    Render wiki home page.

    Shows README.md or directory listing.
    """
    try:
        branch = request.GET.get('branch', 'main')
        static_path = _get_static_path(branch)

        # Try to load README.html
        readme_html = static_path / 'README.html'
        readme_md = static_path / 'README.md'

        if readme_html.exists():
            content = readme_html.read_text(encoding='utf-8')
            metadata = _load_metadata('README.md', branch)

            context = {
                'content': content,
                'metadata': metadata,
                'breadcrumbs': [{'name': 'Home', 'url': '/'}],
                'file_path': 'README.md',
                'branch': branch,
                'toc': metadata.get('toc', '') if metadata else '',
                'directory_listing': _list_directory('', branch)
            }

            logger.info(f'Rendered wiki home for branch {branch} [DISPLAY-HOME01]')
            return render(request, 'display/page.html', context)

        # No README, show directory listing
        context = {
            'content': '<h1>Wiki Home</h1><p>Welcome to GitWiki!</p>',
            'breadcrumbs': [{'name': 'Home', 'url': '/'}],
            'file_path': '',
            'branch': branch,
            'directory_listing': _list_directory('', branch)
        }

        logger.info(f'Rendered wiki home (directory) for branch {branch} [DISPLAY-HOME02]')
        return render(request, 'display/page.html', context)

    except Exception as e:
        logger.error(f'Error rendering wiki home: {str(e)} [DISPLAY-HOME03]')
        raise Http404("Wiki home not found")


@require_http_methods(["GET"])
def wiki_page(request, file_path):
    """
    Render a wiki page from static HTML.

    Args:
        file_path: Path to markdown file (without .md extension)
    """
    try:
        branch = request.GET.get('branch', 'main')
        static_path = _get_static_path(branch)

        # Clean up path
        clean_path = file_path.strip('/')

        # Check if it's a directory
        dir_path = static_path / clean_path
        if dir_path.exists() and dir_path.is_dir():
            # Show directory listing
            context = {
                'content': f'<h1>{clean_path.split("/")[-1].replace("-", " ").replace("_", " ").title()}</h1>',
                'breadcrumbs': _get_breadcrumbs(clean_path),
                'file_path': clean_path,
                'branch': branch,
                'directory_listing': _list_directory(clean_path, branch),
                'is_directory': True
            }

            logger.info(f'Rendered directory listing: {clean_path} [DISPLAY-PAGE01]')
            return render(request, 'display/page.html', context)

        # Try to load HTML file
        html_file = static_path / f'{clean_path}.html'
        md_file = static_path / f'{clean_path}.md'

        if not html_file.exists():
            # Try with .md extension
            html_file = static_path / clean_path / 'index.html'
            if not html_file.exists():
                logger.warning(f'Page not found: {clean_path} [DISPLAY-PAGE02]')
                raise Http404(f"Page '{clean_path}' not found")

        # Load HTML content
        content = html_file.read_text(encoding='utf-8')

        # Load metadata
        metadata = _load_metadata(f'{clean_path}.md', branch)

        # Get directory listing for parent directory
        parent_dir = '/'.join(clean_path.split('/')[:-1]) if '/' in clean_path else ''
        directory_listing = _list_directory(parent_dir, branch)

        context = {
            'content': content,
            'metadata': metadata,
            'breadcrumbs': _get_breadcrumbs(clean_path),
            'file_path': f'{clean_path}.md',
            'branch': branch,
            'toc': metadata.get('toc', '') if metadata else '',
            'directory_listing': directory_listing,
            'edit_url': f'/editor/edit/{clean_path}.md'
        }

        logger.info(f'Rendered page: {clean_path} [DISPLAY-PAGE03]')
        return render(request, 'display/page.html', context)

    except Http404:
        raise
    except Exception as e:
        logger.error(f'Error rendering page {file_path}: {str(e)} [DISPLAY-PAGE04]')
        raise Http404(f"Error loading page: {str(e)}")


@require_http_methods(["GET"])
def wiki_search(request):
    """
    Search wiki pages with caching.

    AIDEV-NOTE: search-cache; Caches search results for 5 minutes to reduce file I/O

    Query params:
        q: Search query
        branch: Branch to search (default: main)
    """
    try:
        query = request.GET.get('q', '').strip()
        branch = request.GET.get('branch', 'main')

        if not query:
            context = {
                'query': '',
                'results': [],
                'total': 0,
                'branch': branch
            }
            return render(request, 'display/search.html', context)

        # Check cache first
        cache_key = f'search:{branch}:{query.lower()}'
        cached_results = cache.get(cache_key)

        if cached_results is not None:
            logger.info(f'Search cache hit for "{query}" [DISPLAY-CACHE05]')
            results = cached_results
        else:
            # Search in markdown files
            static_path = _get_static_path(branch)
            results = []

            if static_path.exists():
                for md_file in static_path.rglob('*.md'):
                    if md_file.name.endswith('.metadata'):
                        continue

                    try:
                        content = md_file.read_text(encoding='utf-8').lower()
                        query_lower = query.lower()

                        if query_lower in content:
                            # Calculate relevance score
                            title_match = query_lower in md_file.stem.lower()
                            count = content.count(query_lower)

                            # Get snippet
                            snippet = _get_search_snippet(md_file.read_text(encoding='utf-8'), query, max_length=200)

                            rel_path = md_file.relative_to(static_path)
                            clean_path = str(rel_path).replace('.md', '')

                            results.append({
                                'title': md_file.stem.replace('-', ' ').replace('_', ' ').title(),
                                'path': clean_path,
                                'url': f'/wiki/{clean_path}',
                                'snippet': snippet,
                                'matches': count,
                                'score': (count * 10) + (100 if title_match else 0)
                            })

                    except Exception as e:
                        logger.warning(f'Error searching file {md_file}: {str(e)} [DISPLAY-SEARCH01]')

            # Sort by score
            results.sort(key=lambda x: x['score'], reverse=True)

            # Cache search results for 5 minutes (300 seconds)
            cache.set(cache_key, results, 300)
            logger.info(f'Search results cached for "{query}" ({len(results)} results) [DISPLAY-CACHE06]')

        # Paginate
        paginator = Paginator(results, 20)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)

        context = {
            'query': query,
            'results': page_obj,
            'total': len(results),
            'branch': branch,
            'page_obj': page_obj
        }

        logger.info(f'Search for "{query}" returned {len(results)} results [DISPLAY-SEARCH02]')
        return render(request, 'display/search.html', context)

    except Exception as e:
        logger.error(f'Error in search: {str(e)} [DISPLAY-SEARCH03]')
        context = {
            'query': request.GET.get('q', ''),
            'results': [],
            'total': 0,
            'error': str(e),
            'branch': request.GET.get('branch', 'main')
        }
        return render(request, 'display/search.html', context)


def _get_search_snippet(content: str, query: str, max_length: int = 200) -> str:
    """
    Get a snippet of text containing the search query.

    Args:
        content: Full text content
        query: Search query
        max_length: Maximum snippet length

    Returns:
        Text snippet with query highlighted
    """
    try:
        query_lower = query.lower()
        content_lower = content.lower()

        # Find first occurrence
        idx = content_lower.find(query_lower)
        if idx == -1:
            return content[:max_length] + '...'

        # Get surrounding context
        start = max(0, idx - max_length // 2)
        end = min(len(content), idx + max_length // 2)

        snippet = content[start:end]

        # Add ellipsis
        if start > 0:
            snippet = '...' + snippet
        if end < len(content):
            snippet = snippet + '...'

        # Highlight query (simple, case-insensitive)
        import re
        pattern = re.compile(re.escape(query), re.IGNORECASE)
        snippet = pattern.sub(lambda m: f'<mark>{m.group()}</mark>', snippet)

        return snippet

    except Exception:
        return content[:max_length] + '...'


@require_http_methods(["GET"])
def page_history(request, file_path):
    """
    Show page edit history.

    Args:
        file_path: Path to markdown file
    """
    try:
        from git_service.git_operations import get_repository

        branch = request.GET.get('branch', 'main')

        # Get file history
        repo = get_repository()
        history = repo.get_file_history(file_path, branch, limit=50)

        context = {
            'file_path': file_path,
            'branch': branch,
            'commits': history.get('commits', []),
            'total': history.get('total', 0),
            'breadcrumbs': _get_breadcrumbs(file_path),
            'page_url': f'/wiki/{file_path.replace(".md", "")}'
        }

        logger.info(f'Rendered history for {file_path} [DISPLAY-HISTORY01]')
        return render(request, 'display/history.html', context)

    except Exception as e:
        logger.error(f'Error loading history for {file_path}: {str(e)} [DISPLAY-HISTORY02]')
        raise Http404(f"Error loading history: {str(e)}")


@require_http_methods(["GET", "POST"])
def new_page(request):
    """
    Show form for creating a new wiki page.

    GET /wiki/new/?path=<optional-directory>
    POST /wiki/new/ - Validates path and redirects to editor
    """
    try:
        # Get suggested path from query parameter
        suggested_path = request.GET.get('path', '').strip('/')

        if request.method == 'POST':
            # Get the path from form submission
            file_path = request.POST.get('file_path', '').strip()

            # Validate path
            if not file_path:
                context = {
                    'error': 'Please enter a page path',
                    'suggested_path': suggested_path,
                    'breadcrumbs': [{'name': 'Home', 'url': '/'}, {'name': 'New Page', 'url': '/wiki/new/'}]
                }
                logger.warning(f'New page creation failed: empty path [DISPLAY-NEWPAGE01]')
                return render(request, 'display/new_page.html', context)

            # Ensure .md extension
            if not file_path.endswith('.md'):
                file_path += '.md'

            # Validate path doesn't try to escape wiki directory
            if '..' in file_path or file_path.startswith('/'):
                context = {
                    'error': 'Invalid path: cannot use ".." or start with "/"',
                    'file_path': file_path,
                    'suggested_path': suggested_path,
                    'breadcrumbs': [{'name': 'Home', 'url': '/'}, {'name': 'New Page', 'url': '/wiki/new/'}]
                }
                logger.warning(f'New page creation failed: invalid path {file_path} [DISPLAY-NEWPAGE02]')
                return render(request, 'display/new_page.html', context)

            # Redirect to editor
            editor_url = f'/editor/edit/{file_path}'
            logger.info(f'Redirecting to editor for new page: {file_path} [DISPLAY-NEWPAGE03]')
            return redirect(editor_url)

        # GET request - show form
        context = {
            'suggested_path': suggested_path,
            'breadcrumbs': [{'name': 'Home', 'url': '/'}, {'name': 'New Page', 'url': '/wiki/new/'}]
        }

        logger.info(f'Displaying new page form (suggested path: {suggested_path or "none"}) [DISPLAY-NEWPAGE04]')
        return render(request, 'display/new_page.html', context)

    except Exception as e:
        logger.error(f'Error in new page view: {str(e)} [DISPLAY-NEWPAGE05]')
        raise Http404(f"Error creating page: {str(e)}")


# Error Handlers
# AIDEV-NOTE: error-handlers; Custom error pages for better user experience

def custom_404(request, exception=None):
    """
    Custom 404 error handler.

    Shows a user-friendly "Page Not Found" page instead of Django's default.
    """
    logger.warning(f'404 error for path: {request.path} [ERROR-404]')
    return render(request, 'errors/404.html', status=404)


def custom_500(request):
    """
    Custom 500 error handler.

    Shows a user-friendly "Server Error" page instead of Django's default.
    Note: This template must not use any dynamic content that could fail.
    """
    logger.error(f'500 error for path: {request.path} [ERROR-500]')
    return render(request, 'errors/500.html', status=500)


def custom_403(request, exception=None):
    """
    Custom 403 error handler.

    Shows a user-friendly "Permission Denied" page instead of Django's default.
    """
    logger.warning(f'403 error for path: {request.path} - user: {request.user} [ERROR-403]')
    return render(request, 'errors/403.html', status=403)
