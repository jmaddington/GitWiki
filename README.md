# GitWiki

A distributed, Git-backed markdown wiki system with web-based editing, clipboard image support, and conflict resolution.

## Project Status

🚧 **Under Active Development** 🚧

Currently implementing Phase 1: Foundation

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

*Installation instructions will be added once Phase 1 is complete.*

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
python manage.py test
```

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

**Current Progress**: Phase 1 - Foundation (In Progress)

*Last Updated: October 25, 2025*
