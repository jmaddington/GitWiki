"""
Comprehensive tests for Display Service.

AIDEV-NOTE: display-tests; Tests for wiki rendering, search, caching, and navigation
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.cache import cache
from django.conf import settings
from pathlib import Path
import shutil
import tempfile
import json

from git_service.git_operations import GitRepository


class DisplayViewsTest(TestCase):
    """Tests for display service views."""

    def setUp(self):
        """Set up test environment with temporary repository."""
        self.client = Client()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')

        # Create temporary directories
        self.temp_repo_dir = Path(tempfile.mkdtemp())
        self.temp_static_dir = Path(tempfile.mkdtemp())

        # Override settings
        self.old_repo_path = settings.WIKI_REPO_PATH
        self.old_static_path = settings.WIKI_STATIC_PATH
        settings.WIKI_REPO_PATH = self.temp_repo_dir
        settings.WIKI_STATIC_PATH = self.temp_static_dir

        # Initialize repository and create test content
        self.repo = GitRepository(repo_path=self.temp_repo_dir)

        # Create test pages
        self._create_test_page('README.md', '# Home Page\nWelcome to the wiki!')
        self._create_test_page('docs/getting-started.md', '# Getting Started\nThis is a guide.')
        self._create_test_page('docs/advanced.md', '# Advanced Topics\nAdvanced content here.')

        # Generate static files
        self.repo.write_branch_to_disk('main')

        # Clear cache before each test
        cache.clear()

    def tearDown(self):
        """Clean up temporary directories and restore settings."""
        if self.temp_repo_dir.exists():
            shutil.rmtree(self.temp_repo_dir)
        if self.temp_static_dir.exists():
            shutil.rmtree(self.temp_static_dir)

        settings.WIKI_REPO_PATH = self.old_repo_path
        settings.WIKI_STATIC_PATH = self.old_static_path

        cache.clear()

    def _create_test_page(self, file_path, content):
        """Helper to create a test page in the repository."""
        self.repo.commit_changes(
            branch_name='main',
            file_path=file_path,
            content=content,
            commit_message=f'Add {file_path}',
            user_info={'name': 'Test User', 'email': 'test@example.com'},
            user=self.user
        )

    def test_wiki_home_renders(self):
        """Test that wiki home page renders successfully."""
        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Home Page')
        self.assertContains(response, 'Welcome to the wiki')

    def test_wiki_page_renders(self):
        """Test that individual wiki pages render."""
        response = self.client.get('/wiki/docs/getting-started')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Getting Started')

    def test_wiki_page_not_found(self):
        """Test 404 for non-existent pages."""
        response = self.client.get('/wiki/nonexistent')

        self.assertEqual(response.status_code, 404)

    def test_directory_listing(self):
        """Test directory listing shows files and subdirectories."""
        response = self.client.get('/wiki/docs/')

        self.assertEqual(response.status_code, 200)
        # Should show files in docs directory
        self.assertContains(response, 'Getting Started')
        self.assertContains(response, 'Advanced Topics')

    def test_breadcrumbs_generation(self):
        """Test breadcrumb navigation generation."""
        response = self.client.get('/wiki/docs/getting-started')

        self.assertEqual(response.status_code, 200)
        # Should have breadcrumbs
        self.assertContains(response, 'Home')
        self.assertContains(response, 'Docs')

    def test_metadata_caching(self):
        """Test that metadata is properly cached."""
        from display.views import _load_metadata

        # First call - cache miss
        metadata1 = _load_metadata('README.md', 'main')

        # Check cache hit
        cache_key = 'metadata:main:README.md'
        cached = cache.get(cache_key)
        self.assertIsNotNone(cached)

        # Second call - should be cached
        metadata2 = _load_metadata('README.md', 'main')

        # Should return same data
        if metadata1 and metadata2:
            self.assertEqual(metadata1.get('file_path'), metadata2.get('file_path'))

    def test_directory_listing_caching(self):
        """Test that directory listings are cached."""
        from display.views import _list_directory

        # First call - cache miss
        items1 = _list_directory('', 'main')

        # Check cache
        cache_key = 'directory:main:root'
        cached = cache.get(cache_key)
        self.assertIsNotNone(cached)

        # Second call - should be cached
        items2 = _list_directory('', 'main')

        # Should return same data
        self.assertEqual(len(items1), len(items2))

    def test_search_no_query(self):
        """Test search with empty query returns empty results."""
        response = self.client.get('/wiki/search/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Search')

    def test_search_with_results(self):
        """Test search returns matching pages."""
        response = self.client.get('/wiki/search/', {'q': 'Getting Started'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Getting Started')

    def test_search_no_results(self):
        """Test search with no matches."""
        response = self.client.get('/wiki/search/', {'q': 'nonexistent-content-xyz'})

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Getting Started')

    def test_search_caching(self):
        """Test that search results are cached."""
        # First search
        response1 = self.client.get('/wiki/search/', {'q': 'guide'})
        self.assertEqual(response1.status_code, 200)

        # Check cache
        cache_key = 'search:main:guide'
        cached = cache.get(cache_key)
        self.assertIsNotNone(cached)

        # Second search - should hit cache
        response2 = self.client.get('/wiki/search/', {'q': 'guide'})
        self.assertEqual(response2.status_code, 200)

    def test_page_history(self):
        """Test page history view."""
        response = self.client.get('/wiki/history/README.md')

        self.assertEqual(response.status_code, 200)
        # Should show commit history

    def test_branch_switching(self):
        """Test viewing pages from different branches."""
        # Create a draft branch
        branch_result = self.repo.create_draft_branch(user_id=1, user=self.user)
        branch_name = branch_result['branch_name']

        # Add content to draft
        self.repo.commit_changes(
            branch_name=branch_name,
            file_path='draft.md',
            content='# Draft Page\nDraft content',
            commit_message='Add draft',
            user_info={'name': 'Test', 'email': 'test@example.com'},
            user=self.user
        )

        # Generate static files for draft
        self.repo.write_branch_to_disk(branch_name, self.user)

        # View draft branch page
        response = self.client.get(f'/wiki/draft?branch={branch_name}')

        self.assertEqual(response.status_code, 200)

    def test_cache_invalidation_on_update(self):
        """Test that cache is invalidated when content is updated."""
        from config.cache_utils import invalidate_file_cache

        # Cache metadata
        from display.views import _load_metadata
        _load_metadata('README.md', 'main')

        # Verify cached
        cache_key = 'metadata:main:README.md'
        self.assertIsNotNone(cache.get(cache_key))

        # Invalidate
        invalidate_file_cache('main', 'README.md')

        # Cache should be cleared
        self.assertIsNone(cache.get(cache_key))

    def test_search_pagination(self):
        """Test search results pagination."""
        # Create many test pages
        for i in range(25):
            self._create_test_page(f'page{i}.md', f'# Page {i}\nContent with keyword')

        # Regenerate static files
        self.repo.write_branch_to_disk('main')

        # Search should return paginated results
        response = self.client.get('/wiki/search/', {'q': 'keyword'})

        self.assertEqual(response.status_code, 200)
        # Default pagination is 20 per page

    def test_markdown_rendering_with_code(self):
        """Test that markdown with code blocks renders correctly."""
        self._create_test_page('code.md', '# Code Example\n```python\nprint("hello")\n```')
        self.repo.write_branch_to_disk('main')

        response = self.client.get('/wiki/code')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Code Example')

    def test_markdown_rendering_with_tables(self):
        """Test that markdown tables render correctly."""
        table_content = '''# Table Example
| Column 1 | Column 2 |
|----------|----------|
| Data 1   | Data 2   |
'''
        self._create_test_page('table.md', table_content)
        self.repo.write_branch_to_disk('main')

        response = self.client.get('/wiki/table')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Table Example')

    def test_directory_listing_with_images(self):
        """Test that directory listing includes image files."""
        # Create an images directory with test images
        images_dir = self.temp_static_dir / 'main' / 'images'
        images_dir.mkdir(parents=True, exist_ok=True)

        # Create test image files
        test_image_1 = images_dir / 'test1.png'
        test_image_2 = images_dir / 'test2.jpg'
        test_image_1.write_bytes(b'fake png data')
        test_image_2.write_bytes(b'fake jpg data')

        # Clear cache to ensure fresh listing
        cache.clear()

        # Get directory listing
        from display.views import _list_directory
        items = _list_directory('images', 'main')

        # Should include both image files
        image_names = [item['name'] for item in items if item['type'] in ['viewable_image']]
        self.assertIn('test1.png', image_names)
        self.assertIn('test2.jpg', image_names)

        # Files should have size information
        for item in items:
            if item['type'] == 'viewable_image':
                self.assertIn('size', item)
                self.assertIn('icon', item)
                self.assertEqual(item['icon'], 'image')

    def test_file_type_classification(self):
        """Test file type classification function."""
        from display.views import _classify_file_type

        # Test images
        self.assertEqual(
            _classify_file_type(Path('test.png')),
            {'category': 'viewable_image', 'icon': 'image'}
        )
        self.assertEqual(
            _classify_file_type(Path('test.jpg')),
            {'category': 'viewable_image', 'icon': 'image'}
        )

        # Test videos
        self.assertEqual(
            _classify_file_type(Path('test.mp4')),
            {'category': 'viewable_video', 'icon': 'film'}
        )

        # Test documents
        self.assertEqual(
            _classify_file_type(Path('test.pdf')),
            {'category': 'document', 'icon': 'file'}
        )

        # Test code files
        self.assertEqual(
            _classify_file_type(Path('test.py')),
            {'category': 'code', 'icon': 'code'}
        )

        # Test archives
        self.assertEqual(
            _classify_file_type(Path('test.zip')),
            {'category': 'archive', 'icon': 'archive'}
        )

        # Test unknown
        self.assertEqual(
            _classify_file_type(Path('test.unknown')),
            {'category': 'other', 'icon': 'file'}
        )

    def test_serve_image_file(self):
        """Test serving an image file."""
        # Create test image
        images_dir = self.temp_static_dir / 'main' / 'images'
        images_dir.mkdir(parents=True, exist_ok=True)

        test_image = images_dir / 'test.png'
        test_image.write_bytes(b'PNG fake data')

        # Request the image
        response = self.client.get('/wiki/file/images/test.png')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')
        self.assertIn('inline', response['Content-Disposition'])

    def test_serve_file_with_download(self):
        """Test serving a file with download flag."""
        # Create test document
        docs_dir = self.temp_static_dir / 'main' / 'documents'
        docs_dir.mkdir(parents=True, exist_ok=True)

        test_doc = docs_dir / 'test.pdf'
        test_doc.write_bytes(b'PDF fake data')

        # Request the file with download flag
        response = self.client.get('/wiki/file/documents/test.pdf?download=1')

        self.assertEqual(response.status_code, 200)
        self.assertIn('attachment', response['Content-Disposition'])

    def test_serve_file_not_found(self):
        """Test 404 for non-existent files."""
        response = self.client.get('/wiki/file/nonexistent/file.png')

        self.assertEqual(response.status_code, 404)

    def test_serve_file_directory_traversal_protection(self):
        """Test that directory traversal is prevented."""
        response = self.client.get('/wiki/file/../../../etc/passwd')

        self.assertEqual(response.status_code, 404)

    def test_serve_file_hidden_file_protection(self):
        """Test that hidden files cannot be served."""
        # Create hidden file
        static_main = self.temp_static_dir / 'main'
        static_main.mkdir(parents=True, exist_ok=True)

        hidden_file = static_main / '.hidden'
        hidden_file.write_text('secret data')

        response = self.client.get('/wiki/file/.hidden')

        self.assertEqual(response.status_code, 404)

    def test_directory_view_shows_image_files(self):
        """Test that directory view page shows image files."""
        # Create images directory with files
        images_dir = self.temp_static_dir / 'main' / 'images'
        images_dir.mkdir(parents=True, exist_ok=True)

        test_image = images_dir / 'screenshot.png'
        test_image.write_bytes(b'PNG data')

        # Clear cache
        cache.clear()

        # View directory
        response = self.client.get('/wiki/images/')

        self.assertEqual(response.status_code, 200)
        # Should show the image file
        self.assertContains(response, 'screenshot.png')
        # Should not show "This directory is empty"
        self.assertNotContains(response, 'This directory is empty')

    def test_file_size_formatting(self):
        """Test file size formatting function."""
        from display.views import _format_file_size

        self.assertEqual(_format_file_size(0), '0.0 B')
        self.assertEqual(_format_file_size(500), '500.0 B')
        self.assertEqual(_format_file_size(1024), '1.0 KB')
        self.assertEqual(_format_file_size(1024 * 1024), '1.0 MB')
        self.assertEqual(_format_file_size(1024 * 1024 * 1024), '1.0 GB')
        self.assertEqual(_format_file_size(1536), '1.5 KB')  # 1.5 KB


class CacheUtilsTest(TestCase):
    """Tests for cache utility functions."""

    def setUp(self):
        """Clear cache before each test."""
        cache.clear()

    def tearDown(self):
        """Clear cache after each test."""
        cache.clear()

    def test_invalidate_branch_cache(self):
        """Test branch cache invalidation."""
        from config.cache_utils import invalidate_branch_cache

        # Set various cache entries for a branch
        cache.set('metadata:main:test.md', {'title': 'Test'}, 3600)
        cache.set('metadata:main:other.md', {'title': 'Other'}, 3600)
        cache.set('directory:main:root', ['file1', 'file2'], 600)
        cache.set('directory:main:subdir', ['file3'], 600)
        cache.set('search:main:test', [{'title': 'Result'}], 300)
        cache.set('search:main:other', [{'title': 'Result2'}], 300)

        # Also set cache for a different branch (should not be affected)
        cache.set('metadata:draft-1:test.md', {'title': 'Draft'}, 3600)

        # Invalidate main branch
        invalidate_branch_cache('main')

        # All main branch caches should be cleared
        self.assertIsNone(cache.get('metadata:main:test.md'))
        self.assertIsNone(cache.get('metadata:main:other.md'))
        self.assertIsNone(cache.get('directory:main:root'))
        self.assertIsNone(cache.get('directory:main:subdir'))
        self.assertIsNone(cache.get('search:main:test'))
        self.assertIsNone(cache.get('search:main:other'))

        # Other branch should still have cache
        self.assertIsNotNone(cache.get('metadata:draft-1:test.md'))

    def test_invalidate_file_cache(self):
        """Test file cache invalidation."""
        from config.cache_utils import invalidate_file_cache

        # Set some cache entries
        cache.set('metadata:main:test.md', {'test': 'data'}, 3600)
        cache.set('directory:main:root', ['item1'], 600)

        # Invalidate
        invalidate_file_cache('main', 'test.md')

        # Metadata should be cleared
        self.assertIsNone(cache.get('metadata:main:test.md'))

    def test_invalidate_search_cache(self):
        """Test search cache invalidation."""
        from config.cache_utils import invalidate_search_cache

        # Set search cache for multiple branches and queries
        cache.set('search:main:query1', ['result1'], 300)
        cache.set('search:main:query2', ['result2'], 300)
        cache.set('search:draft-1:query3', ['result3'], 300)

        # Invalidate main branch search cache
        invalidate_search_cache('main')

        # Main branch search caches should be cleared
        self.assertIsNone(cache.get('search:main:query1'))
        self.assertIsNone(cache.get('search:main:query2'))

        # Other branch should still have cache
        self.assertIsNotNone(cache.get('search:draft-1:query3'))

        # Test clearing all search caches
        cache.set('search:main:query4', ['result4'], 300)
        cache.set('search:draft-1:query5', ['result5'], 300)

        invalidate_search_cache()  # No branch specified = clear all

        self.assertIsNone(cache.get('search:main:query4'))
        self.assertIsNone(cache.get('search:draft-1:query3'))  # From earlier
        self.assertIsNone(cache.get('search:draft-1:query5'))

    def test_clear_all_caches(self):
        """Test clearing all caches."""
        from config.cache_utils import clear_all_caches

        # Set multiple cache entries
        cache.set('key1', 'value1', 3600)
        cache.set('key2', 'value2', 3600)

        # Clear all
        result = clear_all_caches()

        self.assertTrue(result['success'])
        self.assertIsNone(cache.get('key1'))
        self.assertIsNone(cache.get('key2'))

    def test_get_cache_stats(self):
        """Test getting cache statistics."""
        from config.cache_utils import get_cache_stats

        stats = get_cache_stats()

        self.assertIsNotNone(stats)
        self.assertIn('supported', stats)


class MarkdownRenderingTest(TestCase):
    """Tests for markdown-to-HTML conversion with caching."""

    def setUp(self):
        """Set up test repository."""
        self.temp_repo_dir = Path(tempfile.mkdtemp())
        self.old_repo_path = settings.WIKI_REPO_PATH
        settings.WIKI_REPO_PATH = self.temp_repo_dir

        self.repo = GitRepository(repo_path=self.temp_repo_dir)
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')

        cache.clear()

    def tearDown(self):
        """Clean up."""
        if self.temp_repo_dir.exists():
            shutil.rmtree(self.temp_repo_dir)

        settings.WIKI_REPO_PATH = self.old_repo_path
        cache.clear()

    def test_markdown_to_html_basic(self):
        """Test basic markdown conversion."""
        content = '# Heading\nParagraph text'

        html, toc = self.repo._markdown_to_html(content)

        self.assertIn('<h1', html)
        self.assertIn('Heading', html)
        self.assertIn('Paragraph text', html)

    def test_markdown_to_html_caching(self):
        """Test that markdown rendering is cached."""
        content = '# Test Heading\nTest content'

        # First call - cache miss
        html1, toc1 = self.repo._markdown_to_html(content)

        # Second call - should hit cache
        html2, toc2 = self.repo._markdown_to_html(content)

        # Should return same result
        self.assertEqual(html1, html2)
        self.assertEqual(toc1, toc2)

    def test_markdown_to_html_with_code_blocks(self):
        """Test markdown with code blocks."""
        content = '''# Code Example
```python
def hello():
    print("world")
```
'''

        html, toc = self.repo._markdown_to_html(content)

        self.assertIn('Code Example', html)
        # Should have code highlighting

    def test_markdown_to_html_with_tables(self):
        """Test markdown with tables."""
        content = '''# Table
| A | B |
|---|---|
| 1 | 2 |
'''

        html, toc = self.repo._markdown_to_html(content)

        self.assertIn('<table', html)

    def test_markdown_to_html_with_toc(self):
        """Test markdown generates table of contents."""
        content = '''# Heading 1
## Heading 2
### Heading 3
'''

        html, toc = self.repo._markdown_to_html(content)

        # TOC should be generated
        self.assertIsInstance(toc, str)

    def test_markdown_different_content_different_cache(self):
        """Test that different content has different cache entries."""
        content1 = '# Heading 1'
        content2 = '# Heading 2'

        html1, _ = self.repo._markdown_to_html(content1)
        html2, _ = self.repo._markdown_to_html(content2)

        self.assertNotEqual(html1, html2)
        self.assertIn('Heading 1', html1)
        self.assertIn('Heading 2', html2)
