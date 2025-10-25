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

**Currently**: Phase 3 - Display Service (starting next)
**See**: Commit b3647ee for Phase 2 implementation details

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

- [Phase 1 Code Review](PHASE_1_REVIEW.md) - ⭐ Comprehensive code review and Phase 2 recommendations
- [Project Plan](distributed-wiki-project-plan.md) - Complete project specification with developer handoff
- [Implementation Plan](IMPLEMENTATION_PLAN.md) - Detailed step-by-step implementation roadmap (Phase 1 complete)
- [Development Guidelines](Claude.md) - Commenting and commit guidelines with AIDEV-NOTE index

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

# Create a superuser (optional, for admin access)
python manage.py createsuperuser

# Start development server
python manage.py runserver
```

The Git Service API will be available at `http://localhost:8000/api/git/`

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

**Current Progress**: ✅ Phase 2 Complete - Editor Service with SimpleMDE, image upload, and session management

**Code Quality**: ✅ Phase 1 & 2 complete - Excellent architecture, ready for Phase 3 (Display Service)

*Last Updated: October 25, 2025 (Phase 2 Complete)*
