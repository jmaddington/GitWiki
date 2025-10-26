# GitWiki Developer Guide

Complete guide for developers working on GitWiki including architecture, APIs, development setup, and contributing guidelines.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Code Style and Standards](#code-style-and-standards)
- [Contributing](#contributing)
- [Release Process](#release-process)

---

## Architecture Overview

### System Architecture

GitWiki is built on Django and uses Git as the backend storage system. The architecture follows a clear separation of concerns:

```
┌─────────────────────────────────────────────┐
│          Web Browser (User)                 │
└─────────────┬───────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│      Nginx/Apache (Web Server)              │
└─────────────┬───────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│        Django Application                    │
│  ┌──────────────────────────────────────┐  │
│  │  Display Service (Read-only views)   │  │
│  ├──────────────────────────────────────┤  │
│  │  Editor Service (Edit operations)    │  │
│  ├──────────────────────────────────────┤  │
│  │  Git Service (Core git operations)   │  │
│  └──────────────────────────────────────┘  │
└─────────────┬───────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│          Git Repository                      │
│     (wiki_repo/ - versioned content)        │
└─────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│       Static Files Directory                 │
│   (wiki_static/ - rendered HTML/metadata)   │
└─────────────────────────────────────────────┘
```

### Three-Service Architecture

GitWiki is organized into three Django apps with clear responsibilities:

#### 1. Git Service (`git_service/`)

**Responsibility:** Core Git operations

**Key Components:**
- `git_operations.py`: GitRepository class with all Git operations
- `models.py`: Configuration and GitOperation (audit log)
- `api.py`: REST API for Git operations
- `tasks.py`: Celery tasks for background operations

**Operations:**
- Branch creation (`create_draft_branch`)
- Committing changes (`commit_changes`)
- Merging branches (`publish_draft`)
- Conflict detection (`get_conflicts`)
- Static file generation (`write_branch_to_disk`)
- GitHub sync (`pull_from_github`, `push_to_github`)

#### 2. Editor Service (`editor/`)

**Responsibility:** User editing workflow

**Key Components:**
- `models.py`: EditSession (tracks active edits)
- `api.py`: REST API for editor operations
- `views.py`: UI views for editor interface
- `serializers.py`: Request/response validation

**Features:**
- Edit session management
- Auto-save functionality
- Conflict resolution UI
- Image upload handling
- Markdown validation

#### 3. Display Service (`display/`)

**Responsibility:** Read-only wiki viewing

**Key Components:**
- `views.py`: Page rendering, search, history
- `urls.py`: URL routing
- `templates/`: Page display templates

**Features:**
- Wiki page rendering
- Search functionality
- Directory browsing
- Page history
- Breadcrumb navigation
- Custom error pages

### Data Flow

**Reading a Page:**
```
User Request → Display View → Static HTML File → Rendered Page
```

**Editing a Page:**
```
User Edit Request → Editor API → Git Service → Create Draft Branch
User Saves → Editor API → Git Service → Commit to Branch
User Publishes → Editor API → Git Service → Merge to Main
Main Updated → Static Generation → New HTML Files
```

**Conflict Resolution:**
```
Publish Fails → Conflict Detected → Three-Way Diff Generated
User Resolves → Resolution Committed → Merge Retried
```

### Technology Stack

**Core Technologies:**
- **Python 3.9+**: Application language
- **Django 4.2**: Web framework
- **GitPython**: Git operations
- **PostgreSQL**: Production database (SQLite for development)
- **Redis**: Caching and task queue
- **Celery**: Background task processing

**Frontend:**
- **Bootstrap 5**: UI framework
- **SimpleMDE**: Markdown editor
- **Monaco Editor**: Conflict resolution diff view
- **Vanilla JavaScript**: Minimal JS, no heavy frameworks

**Development Tools:**
- **Black**: Code formatting
- **Flake8**: Linting
- **Pytest**: Testing framework
- **Coverage**: Test coverage measurement

---

## Development Setup

### Prerequisites

- Python 3.9 or higher
- Git 2.30 or higher
- PostgreSQL 14+ (optional for development)
- Redis 7+ (optional for development)
- Node.js 16+ (optional for frontend work)

### Quick Start

```bash
# Clone repository
git clone https://github.com/your-org/gitwiki.git
cd gitwiki

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env for development
nano .env
# Set: DEBUG=True
# Leave DATABASE_URL unset (will use SQLite)

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Install Git hooks
./scripts/install-hooks.sh

# Run development server
python manage.py runserver
```

Visit http://localhost:8000

### IDE Setup

**VS Code:**

Create `.vscode/settings.json`:
```json
{
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "python.formatting.blackArgs": ["--line-length=120"],
    "editor.formatOnSave": true,
    "editor.rulers": [120],
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true
    }
}
```

**PyCharm:**

1. Open project in PyCharm
2. Configure Python interpreter: Settings → Project → Python Interpreter
3. Select virtual environment (`venv/`)
4. Enable Django support: Settings → Languages & Frameworks → Django
5. Set Django project root and settings file

### Running Tests

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test git_service
python manage.py test editor
python manage.py test display

# Run with coverage
coverage run manage.py test
coverage report
coverage html  # Generate HTML report in htmlcov/

# Run specific test class
python manage.py test git_service.tests.GitRepositoryTest

# Run specific test method
python manage.py test git_service.tests.GitRepositoryTest.test_create_draft_branch
```

### Running Celery (for background tasks)

```bash
# Terminal 1: Redis
redis-server

# Terminal 2: Celery worker
celery -A config worker --loglevel=info

# Terminal 3: Celery beat (scheduled tasks)
celery -A config beat --loglevel=info

# Terminal 4: Django dev server
python manage.py runserver
```

---

## Project Structure

```
gitwiki/
├── config/                 # Django project settings
│   ├── settings.py        # Base settings
│   ├── settings_production.py  # Production settings
│   ├── urls.py           # URL configuration
│   ├── api_utils.py      # API error handling utilities
│   └── cache_utils.py    # Cache invalidation utilities
│
├── git_service/           # Git operations app
│   ├── models.py         # Configuration, GitOperation
│   ├── git_operations.py # GitRepository class
│   ├── api.py           # REST API views
│   ├── tasks.py         # Celery tasks
│   ├── utils.py         # SSH testing, URL validation
│   └── tests.py         # Comprehensive tests
│
├── editor/                # Editor app
│   ├── models.py         # EditSession
│   ├── api.py           # REST API for editing
│   ├── views.py         # UI views
│   ├── serializers.py   # DRF serializers
│   └── tests.py         # Comprehensive tests
│
├── display/               # Display app
│   ├── views.py          # Page rendering, search
│   ├── urls.py           # URL patterns
│   └── tests.py          # Comprehensive tests
│
├── templates/             # Django templates
│   ├── base.html         # Base template
│   ├── display/          # Display templates
│   ├── editor/           # Editor templates
│   └── errors/           # Error page templates
│
├── static/                # Static assets
│   ├── css/              # Stylesheets
│   ├── js/               # JavaScript
│   └── images/           # Static images
│
├── docs/                  # Documentation
│   ├── user/             # User guides
│   ├── admin/            # Admin guides
│   └── developer/        # Developer guides
│
├── scripts/               # Utility scripts
│   └── install-hooks.sh  # Git hooks installer
│
├── .githooks/            # Git hooks
│   └── pre-commit       # Pre-commit validation
│
├── .env.example          # Environment template
├── requirements.txt      # Python dependencies
├── manage.py            # Django management
├── Claude.md            # AI-assisted development guide
├── README.md            # Project overview
└── IMPLEMENTATION_PLAN.md  # Implementation phases
```

### Key Files and Their Purposes

**Configuration:**
- `config/settings.py`: Core Django settings
- `config/settings_production.py`: Production-specific settings
- `.env.example`: Environment variable template

**Git Operations:**
- `git_service/git_operations.py`: All Git logic (1,758 lines)
- `git_service/models.py`: Configuration storage and operation audit log

**Editor Workflow:**
- `editor/models.py`: EditSession tracking
- `editor/api.py`: Complete editing API (750 lines)

**Display:**
- `display/views.py`: Page rendering with caching (494 lines)

**Testing:**
- `git_service/tests.py`: Git operations tests (546 lines)
- `editor/tests.py`: Editor tests (576 lines)
- `display/tests.py`: Display tests (442 lines)

---

## API Reference

### Git Service API

Base URL: `/api/git/`

#### Create Branch

**Endpoint:** `POST /api/git/create-branch/`

**Request:**
```json
{
    "user_id": 1
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "branch_name": "draft-1-a1b2c3d4"
    },
    "message": "Draft branch 'draft-1-a1b2c3d4' created successfully"
}
```

#### Commit Changes

**Endpoint:** `POST /api/git/commit/`

**Request:**
```json
{
    "branch_name": "draft-1-a1b2c3d4",
    "file_path": "docs/getting-started.md",
    "content": "# Getting Started\nContent here...",
    "commit_message": "Update getting started guide",
    "user_info": {
        "name": "John Doe",
        "email": "john@example.com"
    }
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "commit_hash": "abc123def456"
    },
    "message": "Changes committed successfully"
}
```

#### Publish Draft

**Endpoint:** `POST /api/git/publish/`

**Request:**
```json
{
    "branch_name": "draft-1-a1b2c3d4"
}
```

**Response (Success):**
```json
{
    "success": true,
    "data": {
        "merged": true,
        "pushed": false,
        "commit_hash": "def789ghi012"
    },
    "message": "Draft published successfully"
}
```

**Response (Conflict):**
```json
{
    "success": false,
    "data": {
        "merged": false,
        "conflicts": [
            {
                "file_path": "docs/getting-started.md",
                "conflict_type": "content"
            }
        ]
    },
    "message": "Merge conflicts detected"
}
```

### Editor Service API

Base URL: `/api/editor/`

#### Start Edit Session

**Endpoint:** `POST /api/editor/start/`

**Request:**
```json
{
    "user_id": 1,
    "file_path": "docs/api.md"
}
```

**Response (New Session):**
```json
{
    "success": true,
    "data": {
        "session_id": 42,
        "branch_name": "draft-1-a1b2c3d4",
        "file_path": "docs/api.md",
        "content": "# Existing content...",
        "resumed": false
    },
    "message": "Started new edit session for 'docs/api.md'"
}
```

#### Save Draft

**Endpoint:** `POST /api/editor/save-draft/`

**Request:**
```json
{
    "session_id": 42,
    "content": "# Updated content\nNew text..."
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "session_id": 42,
        "last_saved": "2025-10-26T10:30:00Z"
    },
    "message": "Draft saved successfully"
}
```

#### Commit Draft

**Endpoint:** `POST /api/editor/commit/`

**Request:**
```json
{
    "session_id": 42,
    "content": "# Final content\nReady to publish...",
    "commit_message": "Update API documentation",
    "user_info": {
        "name": "Jane Doe",
        "email": "jane@example.com"
    }
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "commit_hash": "xyz789abc123",
        "session_id": 42
    },
    "message": "Changes committed to draft branch"
}
```

#### Publish Edit

**Endpoint:** `POST /api/editor/publish/`

**Request:**
```json
{
    "session_id": 42
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "merged": true,
        "commit_hash": "final123hash",
        "session_closed": true
    },
    "message": "Edit published successfully"
}
```

### Error Response Format

All API endpoints use standardized error responses:

```json
{
    "success": false,
    "error": {
        "message": "User-friendly error message",
        "code": "GREPABLE-CODE01",
        "details": {
            "technical_info": "Detailed error for debugging"
        }
    }
}
```

**Common Error Codes:**
- `422`: Validation error
- `404`: Resource not found
- `409`: Conflict detected
- `500`: Internal server error

---

## Testing

### Test Structure

Tests are organized by Django app:

**git_service/tests.py:**
- Configuration model tests
- GitOperation model tests
- GitRepository tests
- GitHub integration tests
- SSH utility tests

**editor/tests.py:**
- EditSession model tests
- Editor API tests
- Editor view tests
- Image upload tests
- Permission tests

**display/tests.py:**
- Display view tests
- Cache utility tests
- Markdown rendering tests

### Writing Tests

**Test Template:**

```python
from django.test import TestCase
from pathlib import Path
import tempfile
import shutil

class MyFeatureTest(TestCase):
    """Tests for my feature."""

    def setUp(self):
        """Set up test environment."""
        # Create temp directory
        self.temp_dir = Path(tempfile.mkdtemp())
        # Create test data
        self.test_user = User.objects.create_user('testuser')

    def tearDown(self):
        """Clean up test environment."""
        # Remove temp directory
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_feature_works(self):
        """Test that feature works correctly."""
        # Arrange
        input_data = {...}

        # Act
        result = my_function(input_data)

        # Assert
        self.assertEqual(result, expected_output)
```

**Best Practices:**
- Use descriptive test names: `test_create_branch_with_valid_user_id`
- Test happy path and error cases
- Use temporary directories for file operations
- Clean up resources in `tearDown()`
- Test API responses, not just functions
- Mock external dependencies (GitHub, etc.)

### Coverage Goals

Target coverage: **80%+** overall

Current coverage (Phase 7):
- Git service: ~90% (very comprehensive)
- Editor service: ~85% (comprehensive API tests)
- Display service: ~80% (view and cache tests)

**Checking Coverage:**
```bash
coverage run manage.py test
coverage report
coverage html  # View in browser: htmlcov/index.html
```

---

## Code Style and Standards

### Python Code Style

Follow PEP 8 with these modifications:
- Line length: 120 characters (not 79)
- Use double quotes for strings
- Use f-strings for formatting

**Format Code:**
```bash
# Format all Python files
black --line-length=120 .

# Check style
flake8 --max-line-length=120 .
```

### Django Conventions

**Views:**
- Use function-based views for simple cases
- Use class-based views for complex logic
- Add docstrings to all views

**Models:**
- Add docstrings to models and methods
- Use `help_text` for fields
- Implement `__str__()` method

**URLs:**
- Use descriptive URL names
- Group related URLs with namespaces

### AIDEV-NOTE System

GitWiki uses AIDEV-NOTE comments for AI-assisted development:

```python
# AIDEV-NOTE: feature-name; Brief description (≤ 120 chars)
def important_function():
    """Detailed docstring here."""
    pass
```

**Guidelines:**
- Use for complex, important, or confusing code
- Keep descriptions under 120 characters
- Update when modifying associated code
- Don't remove without human instruction

**Existing AIDEV-NOTEs:** See `Claude.md` for full list (48 anchors)

### Grepable Logging

All log messages must include a unique grepable code:

```python
logger.info(f'Operation completed successfully [FEATURE-SUCCESS01]')
logger.error(f'Operation failed: {error} [FEATURE-ERROR01]')
```

**Code Format:**
- All caps
- Descriptive prefix
- Sequential numbers
- In brackets at end

**Example Codes:**
- `[GITOPS-COMMIT01]` - Git commit operation
- `[EDITOR-START02]` - Editor start session
- `[CACHE-CLEAR01]` - Cache clear operation

---

## Contributing

### Development Workflow

1. **Create Feature Branch:**
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make Changes:**
   - Write code
   - Add tests
   - Update documentation

3. **Run Tests:**
   ```bash
   python manage.py test
   black --check .
   flake8 .
   ```

4. **Commit Changes:**
   ```bash
   git add .
   git commit -m "feat: add my feature

   - Detailed description
   - What changed
   - Why it changed

   Generated with Claude Code"
   ```

5. **Push and Create PR:**
   ```bash
   git push origin feature/my-feature
   # Create pull request on GitHub
   ```

### Commit Message Format

Follow Conventional Commits:

```
type(scope): subject

body

footer
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Formatting, no code change
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(editor): add auto-save functionality

- Save draft every 30 seconds
- Show last saved timestamp
- Handle save errors gracefully

Closes #123
```

### Pull Request Guidelines

**PR Checklist:**
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Code formatted (black)
- [ ] Lint checks pass (flake8)
- [ ] All tests pass
- [ ] AIDEV-NOTEs added for complex code
- [ ] Grepable codes added to logs
- [ ] Claude.md updated if needed

**PR Template:**

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How has this been tested?

## Checklist
- [ ] Tests pass
- [ ] Documentation updated
- [ ] Code formatted
```

### Code Review Process

1. **Self-Review:** Review your own PR first
2. **Automated Checks:** CI must pass
3. **Peer Review:** At least one approval required
4. **Address Feedback:** Make requested changes
5. **Merge:** Squash and merge to main

---

## Release Process

### Versioning

GitWiki uses Semantic Versioning: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes
- **MINOR**: New features (backwards compatible)
- **PATCH**: Bug fixes

### Release Checklist

1. **Update Version:**
   - Update `__version__` in `config/__init__.py`
   - Update `CHANGELOG.md`

2. **Run Full Test Suite:**
   ```bash
   python manage.py test
   coverage run manage.py test
   coverage report  # Should be 80%+
   ```

3. **Update Documentation:**
   - Review all docs for accuracy
   - Update version numbers
   - Update screenshots if needed

4. **Create Release Branch:**
   ```bash
   git checkout -b release/v1.0.0
   ```

5. **Tag Release:**
   ```bash
   git tag -a v1.0.0 -m "Release version 1.0.0"
   git push origin v1.0.0
   ```

6. **Build Package:**
   ```bash
   python setup.py sdist bdist_wheel
   ```

7. **Deploy to PyPI** (if applicable):
   ```bash
   twine upload dist/*
   ```

8. **Update GitHub Release:**
   - Create release on GitHub
   - Add release notes
   - Attach binaries if needed

---

*For administrative tasks, see [Admin Guide](../admin/ADMIN_GUIDE.md). For deployment procedures, see [Deployment Guide](../admin/DEPLOYMENT_GUIDE.md).*
