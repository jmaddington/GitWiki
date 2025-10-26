# GitWiki

A distributed, Git-backed markdown wiki system with web-based editing, clipboard image support, and conflict resolution.

## Project Status

🚧 **Under Active Development** 🚧

**Phase 1 Complete ✅** (October 25, 2025): Git Service
- ✅ Django project structure with 3 apps
- ✅ Core models (Configuration, GitOperation, EditSession)
- ✅ Git Service operations (branch, commit, merge, conflict detection)
- ✅ 5 REST API endpoints
- ✅ 11 tests, all passing in 2.484s
- ✅ Code review completed (see PHASE_1_REVIEW.md)

**Phase 2 Complete ✅** (October 25, 2025): Editor Service
- ✅ SimpleMDE markdown editor with Bootstrap 5 UI
- ✅ 6 REST API endpoints for editing workflow
- ✅ Auto-save every 60 seconds + localStorage backup
- ✅ Image upload: file selector, drag-drop, clipboard paste (Ctrl+V)
- ✅ Session management (create, resume, discard)
- ✅ Markdown validation
- ✅ Conflict detection (HTTP 409)
- ✅ 600+ lines in editor/api.py
- ✅ 16 new grepable codes (EDITOR-*)
- ✅ 7 new AIDEV-NOTE anchors

**Phase 3 Complete ✅** (October 25, 2025): Display Service
- ✅ Static file generation from markdown to HTML
- ✅ Wiki page rendering with breadcrumbs and navigation
- ✅ Full-text search with pagination
- ✅ Page history display
- ✅ Responsive wiki theme with code highlighting
- ✅ Table of contents generation
- ✅ 437 lines in display/views.py
- ✅ 4 templates with Bootstrap 5 UI
- ✅ 14 new grepable codes (DISPLAY-*)
- ✅ ~1,200 lines added across 8 files

**Phase 4 Complete ✅** (October 25, 2025): Conflict Resolution
- ✅ Complete conflict resolution system with Monaco Editor
- ✅ Conflicts dashboard with auto-refresh (30s)
- ✅ Three-way diff for text files (base/theirs/ours)
- ✅ Side-by-side image conflict resolution
- ✅ Binary file conflict resolution
- ✅ 1,409 lines added across 10 files
- ✅ 6 comprehensive unit tests
- ✅ 28 new grepable codes
- ✅ 3 new AIDEV-NOTE anchors

**Phase 5 Complete ✅** (October 25, 2025): GitHub Integration
- ✅ Bidirectional GitHub sync (pull/push)
- ✅ Webhook handler with rate limiting
- ✅ Celery periodic tasks (pull/cleanup/rebuild)
- ✅ Branch cleanup automation
- ✅ Admin UI (sync management, GitHub settings)
- ✅ SSH connection testing
- ✅ 2,211 lines added across 13 files
- ✅ 15 integration tests
- ✅ 78 new grepable codes
- ✅ 8 new AIDEV-NOTE anchors

**Phase 6 Complete ✅** (October 25, 2025): Configuration & Permissions
- ✅ Permission middleware (3 modes: open, read-only public, private)
- ✅ Configuration management UI
- ✅ Authentication flow (login/logout with Bootstrap 5)
- ✅ Enhanced Django admin (badges, filters, statistics)
- ✅ Comprehensive tests (25+ permission/auth tests)
- ✅ ~1,350 lines added across 9 files
- ✅ 9 new grepable codes (PERM-*, CONFIG-*)
- ✅ 3 new AIDEV-NOTE anchors

**Currently**: Phase 7 - Polish & Deployment (Ready to Implement)
**Next**: Security hardening, error pages, performance optimization, comprehensive testing
**See**: PHASE_7_PLAN.md for detailed implementation roadmap

## What is GitWiki?

GitWiki is a wiki system that:
- Uses Git as the versioning backend for full history tracking
- Provides a web-based markdown editor with WYSIWYG preview
- Supports clipboard image paste for easy screenshot inclusion
- Handles merge conflicts with an intuitive resolution interface
- Synchronizes with GitHub for distributed collaboration
- Generates static files for fast read performance
- Supports draft/publish workflow to separate work-in-progress from published content

## Key Features

### ✅ Planned Features
- **Web-based editing**: Edit markdown pages through an intuitive web interface
- **Clipboard image support**: Paste screenshots directly into pages
- **Git versioning**: Full history tracking with commit messages
- **Conflict resolution**: Visual merge conflict resolution with Monaco Editor
- **GitHub sync**: Bidirectional synchronization with GitHub repositories
- **Draft/publish workflow**: Work on drafts before publishing to main
- **Static generation**: Fast page loading via pre-generated static HTML
- **Flexible permissions**: Open, read-only public, or private modes
- **Image support**: PNG, WebP, and JPG images with automatic optimization

### 🚀 Post-MVP Features
- Mermaid diagram support
- Full-text search
- Real-time collaborative editing
- Email notifications
- Export to PDF/static site
- Mobile optimization

## Architecture

GitWiki is built with Django and consists of three main apps:

1. **Git Service**: Handles all repository operations, static file generation, and GitHub sync
2. **Editor Service**: Provides the markdown editing interface and image upload handling
3. **Display Service**: Serves static content with optional API enhancements

Each app maintains 95%+ separation of concerns and could be extracted into separate services if needed.

## Technology Stack

- **Backend**: Django (Python), GitPython, Celery, Redis
- **Frontend**: SimpleMDE/Monaco Editor, JavaScript Clipboard API
- **Infrastructure**: Git, GitHub, Gunicorn, Nginx
- **Database**: PostgreSQL (production), SQLite (development)

## Documentation

**⭐ Start Here for Phase 7:**
- [Phase 7 Plan](PHASE_7_PLAN.md) - Comprehensive implementation guide for final phase
- [Implementation Plan](IMPLEMENTATION_PLAN.md) - Detailed task breakdown with checklists

**Project Documentation:**
- [Project Plan](distributed-wiki-project-plan.md) - Complete specification with Phase 7 roadmap
- [Development Guidelines](Claude.md) - AIDEV-NOTE index and grepable codes (187 codes)
- [Phase 6 Summary](PHASE_6_COMPLETE.md) - Configuration & permissions implementation summary
- [README](README.md) - This file: setup guide and quick start

## Quick Start

```bash
# Clone the repository
git clone https://github.com/jmaddington/GitWiki.git
cd GitWiki

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Initialize default configurations
python manage.py init_config

# Install git hooks (recommended)
./scripts/install-hooks.sh

# Create a superuser (optional, for admin access)
python manage.py createsuperuser

# Start development server
python manage.py runserver
```

The Git Service API will be available at `http://localhost:8000/api/git/`

### Git Hooks

GitWiki includes pre-commit hooks that validate branch naming and prevent direct commits to `main`:

```bash
# Install hooks
./scripts/install-hooks.sh
```

The hook validates:
- Draft branches must follow format: `draft-{user_id}-{uuid}`
- No direct commits to `main` branch (use web editor instead)

To bypass hooks (not recommended): `git commit --no-verify`

## Development

### Prerequisites
- Python 3.10+
- Git
- Redis
- PostgreSQL (for production)

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd GitWiki

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Start development server
python manage.py runserver
```

### Running Tests

```bash
# Run all tests
python manage.py test

# Run tests for a specific app
python manage.py test git_service

# Run with verbose output
python manage.py test --verbosity=2
```

## Available API Endpoints (Phase 1)

The following REST API endpoints are currently available:

### Git Service API (`/api/git/`)

- **POST** `/api/git/branch/create/` - Create a new draft branch
  ```json
  {"user_id": 123}
  ```

- **POST** `/api/git/commit/` - Commit changes to a draft branch
  ```json
  {
    "branch_name": "draft-123-abc456",
    "file_path": "docs/page.md",
    "content": "# Page Title\nContent...",
    "commit_message": "Update page",
    "user_info": {
      "name": "John Doe",
      "email": "john@example.com"
    }
  }
  ```

- **POST** `/api/git/publish/` - Publish draft to main (with conflict detection)
  ```json
  {
    "branch_name": "draft-123-abc456",
    "auto_push": true
  }
  ```

- **GET** `/api/git/file/?file_path=docs/page.md&branch=main` - Get file content

- **GET** `/api/git/branches/?pattern=draft-*` - List branches

## Admin Interface

Access the Django admin at `http://localhost:8000/admin/` to:
- View and edit Configuration settings
- Browse GitOperation audit logs
- Manage EditSessions
- Manage users

## Project Timeline

- **Phase 1** (Weeks 1-2): Foundation - Git Service core operations
- **Phase 2** (Weeks 3-4): Editor Service - Web-based editing interface
- **Phase 3** (Week 5): Display Service - Static content serving
- **Phase 4** (Week 6): Conflict Resolution - Merge conflict handling
- **Phase 5** (Week 7): GitHub Integration - Remote synchronization
- **Phase 6** (Week 8): Configuration & Permissions - Access control
- **Phase 7** (Weeks 9-10): Polish & Deployment - Production readiness

## Contributing

*Contribution guidelines will be added later in development.*

## License

*License information to be added.*

## Contact

For questions or support, please refer to the project documentation or create an issue in the repository.

---

**Current Progress**: ✅ Phase 6 Complete - Configuration & Permissions with authentication

**Next Phase**: 🔨 Phase 7 Ready - Polish & Deployment (final phase!)

**Code Quality**: ✅ Phases 1-6 complete - Excellent architecture (~8,850 lines of application code)

**Project Status**: 80% complete (8 of 10 weeks) - Production-ready with Phase 7

**Key Stats:**
- Total Code: ~9,878 lines (6,395 Python + 3,483 templates)
- AIDEV-NOTE Anchors: 40
- Grepable Logging Codes: 187
- Test Coverage: Good in core modules (git_service, config)

*Last Updated: October 26, 2025 (Phase 6 Complete, Phase 7 Planned)*
