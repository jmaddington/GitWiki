# GitWiki

A distributed, Git-backed markdown wiki system with web-based editing, clipboard image support, and conflict resolution.

## Project Status

🚧 **Under Active Development** 🚧

**Phase 1 Complete**: Git Service core operations and API
- ✅ Django project structure with 3 apps
- ✅ Core models (Configuration, GitOperation, EditSession)
- ✅ Git Service operations (branch, commit, merge)
- ✅ REST API endpoints
- ✅ Comprehensive test suite (11 tests passing)

**Phase 2 Complete**: Editor Service with web-based markdown editing
- ✅ SimpleMDE markdown editor integration
- ✅ Editor API endpoints (start, commit, publish, validate, upload, discard)
- ✅ Draft/commit/publish workflow
- ✅ Image upload with clipboard paste support
- ✅ Session management (list, resume, discard)
- ✅ Comprehensive test suite (15 tests passing)
- ✅ Binary file support for images

**Currently**: Phase 3 - Display Service (starting next)

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

- [Project Plan](distributed-wiki-project-plan.md) - Complete project specification
- [Implementation Plan](IMPLEMENTATION_PLAN.md) - Detailed step-by-step implementation roadmap
- [Development Guidelines](Claude.md) - Commenting and commit guidelines

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

## Available API Endpoints (Phases 1 & 2)

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

### Editor Service API (`/api/editor/`)

- **POST** `/api/editor/start/` - Start editing a file
  ```json
  {
    "user_id": 123,
    "file_path": "docs/page.md"
  }
  ```

- **POST** `/api/editor/validate/` - Validate markdown syntax
  ```json
  {
    "content": "# Markdown content..."
  }
  ```

- **POST** `/api/editor/commit/` - Commit draft changes
  ```json
  {
    "session_id": 456,
    "content": "# Updated content",
    "commit_message": "Update page"
  }
  ```

- **POST** `/api/editor/publish/` - Publish draft to main
  ```json
  {
    "session_id": 456,
    "auto_push": true
  }
  ```

- **POST** `/api/editor/upload-image/` - Upload image (multipart/form-data)
  - `session_id`: Session ID
  - `image`: Image file
  - `alt_text`: Alt text for image

- **POST** `/api/editor/discard/` - Discard draft
  ```json
  {
    "session_id": 456
  }
  ```

### Editor Web Views

- **GET** `/editor/{file_path}?user_id={id}` - Edit a markdown file
- **GET** `/editor/sessions/?user_id={id}` - List active edit sessions

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

**Current Progress**:
- ✅ Phase 1 Complete - Git Service implemented with full API and test coverage
- ✅ Phase 2 Complete - Editor Service with SimpleMDE, image upload, and full workflow

**Test Coverage**: 26 tests passing (11 git_service + 15 editor)

*Last Updated: October 25, 2025*
