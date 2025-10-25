# Distributed Wiki Project Plan

---

## 🚀 IMPLEMENTATION STATUS & DEVELOPER HANDOFF

**Last Updated:** October 25, 2025 (Phase 5 Complete, Phase 6 Ready)
**Current Branch:** `claude/review-project-documentation-011CUUmRNpmFAGpBKoDiDtxQ`

### 📊 Current Project Status

**Completed:** ✅ Phases 1, 2, 3, 4, 5 (Weeks 1-7)
**Current:** 🔨 Phase 6 - Configuration & Permissions (Week 8) - Ready to Implement
**Remaining:** ⏳ Phase 7 (Weeks 9-10) - Polish & Deployment

**What's Working Now:**
- ✅ Git-backed storage with atomic operations (1,757 lines in git_operations.py)
- ✅ Web-based markdown editor with SimpleMDE (692 lines in editor/api.py)
- ✅ 3 image upload methods (file, drag-drop, clipboard paste)
- ✅ Draft/publish workflow with conflict detection & resolution
- ✅ Complete conflict resolution system with Monaco Editor
- ✅ Conflicts dashboard with auto-refresh (30s)
- ✅ Three-way diff for text files (base/theirs/ours)
- ✅ Side-by-side image conflict resolution
- ✅ Binary file conflict resolution
- ✅ Static HTML generation with metadata extraction (437 lines in display/views.py)
- ✅ Full-text search with pagination
- ✅ Page history from Git commits
- ✅ Responsive Bootstrap 5 UI
- ✅ **GitHub Integration:** Bidirectional sync with webhook support
- ✅ **Celery Tasks:** Periodic pull (5min), cleanup (daily), rebuild (weekly)
- ✅ **Admin UI:** Sync management and GitHub settings pages
- ✅ **SSH Testing:** Connection validation utility

**Phase 5 Complete (100%):**
- ✅ Backend methods (pull_from_github, push_to_github, cleanup, rebuild)
- ✅ SSH utilities (test_ssh_connection, validate_remote_url)
- ✅ Webhook handler with rate limiting (max 1/min)
- ✅ Celery configuration with Redis
- ✅ 3 periodic tasks (pull/cleanup/rebuild)
- ✅ Admin UI (sync management, GitHub settings)
- ✅ 15 integration tests
- ✅ 78 new grepable codes

**What's Been Built in Phase 5:**
- Backend: 609 lines (4 methods: pull, push, cleanup, rebuild)
- Utilities: 207 lines (SSH testing, validation)
- Tasks: 194 lines (3 periodic tasks)
- Views: 308 lines (3 admin views)
- Templates: 489 lines (2 admin pages)
- Celery: 56 lines (configuration)
- Tests: 196 lines (15 tests)
- **Total:** ~2,211 lines added across 13 files

**What Needs to Be Built Next (Phase 6 - Configuration & Permissions):**
- 📋 Permission system (open, read-only public, private modes)
- 📋 Configuration UI for administrators
- 📋 Permission middleware for access control
- 📋 Authentication enhancements (login/logout pages)
- 📋 Enhanced Django admin interfaces
- 📋 "My Drafts" page for users
- 📋 Permission testing across all modes
- **See Phase 6 plan below for detailed roadmap**

**Architecture Quality:** ✅ Excellent
- 100% alignment with original architectural vision
- 3 Django apps with 95%+ separation of concerns
- 182+ unique grepable logging codes documented (+78 in Phase 5)
- Comprehensive AIDEV-NOTE index for code navigation (+8 in Phase 5)

**Code Statistics (Current):**
- git_operations.py: 1,757 lines (+609 from Phase 5)
- git_service/tests.py: 545 lines (+196 from Phase 5)
- git_service/utils.py: 207 lines (new in Phase 5)
- git_service/tasks.py: 194 lines (new in Phase 5)
- git_service/views.py: 371 lines (+308 from Phase 5)
- config/celery.py: 56 lines (new in Phase 5)
- editor/api.py: 692 lines (from Phase 4)
- editor/views.py: 197 lines (from Phase 4)
- display/views.py: 437 lines (from Phase 3)
- **Phase 5 total:** +2,211 lines across 13 files
- **Project total:** ~7,500+ lines of application code

**Documentation Status:**
- **Project Plan:** ✅ This document (comprehensive specification)
- **Implementation Plan:** ✅ IMPLEMENTATION_PLAN.md (detailed task breakdown)
- **Development Guidelines:** ✅ Claude.md (AIDEV-NOTEs, grepable codes)
- **Project Review:** ✅ PROJECT_REVIEW_2025-10-25.md (architectural analysis)
- **README:** ✅ README.md (setup and overview)

---

### ✅ PHASE 1 COMPLETE: Foundation (Weeks 1-2) - VERIFIED & APPROVED

**What's Been Built:**

1. **Django Project Structure** (`/home/user/GitWiki/`)
   - Three apps created: `git_service`, `editor`, `display`
   - Settings configured with REST framework, logging, media/static paths
   - All migrations applied, database ready
   - All dependencies installed (requirements.txt with 20+ packages)

2. **Core Models** (see `git_service/models.py` and `editor/models.py`)
   - ✅ Configuration model - stores app settings (github_remote_url, permissions, etc.)
   - ✅ GitOperation model - complete audit trail of all git operations
   - ✅ EditSession model - tracks active editing sessions
   - ✅ Django admin interfaces for all models

3. **Git Service Core** (`git_service/git_operations.py` - 532 lines)
   - ✅ GitRepository class with singleton pattern
   - ✅ `create_draft_branch(user_id)` - creates draft-{user_id}-{uuid} branches
   - ✅ `commit_changes()` - commits files to draft branches
   - ✅ `publish_draft()` - merges to main with conflict detection (dry-run first)
   - ✅ `get_file_content()` - reads files from any branch
   - ✅ `list_branches()` - lists branches with pattern filtering
   - ✅ All operations are atomic and rollback-safe (see AIDEV-NOTE: atomic-ops)

4. **REST API Endpoints** (`git_service/api.py`)
   - ✅ POST `/api/git/branch/create/` - create draft branch
   - ✅ POST `/api/git/commit/` - commit changes
   - ✅ POST `/api/git/publish/` - publish with conflict detection (returns 409 on conflict)
   - ✅ GET `/api/git/file/` - get file content
   - ✅ GET `/api/git/branches/` - list branches

5. **Testing** (`git_service/tests.py`)
   - ✅ 11 tests, all passing in 2.484s
   - ✅ Tests cover models, Git operations, and conflict scenarios
   - ✅ Uses temporary repos, cleaned up after each test
   - ✅ Test results verified: Ran 11 tests in 2.484s - OK

6. **Documentation**
   - ✅ README.md - setup instructions, API docs
   - ✅ Claude.md - development guidelines, AIDEV-NOTE index, grepable codes
   - ✅ IMPLEMENTATION_PLAN.md - detailed roadmap (Phase 1 marked complete)
   - ✅ PHASE_1_REVIEW.md - comprehensive code review and architectural analysis

**Key Implementation Details:**
- Branch naming: `draft-{user_id}-{uuid8}` (e.g., `draft-123-a8f3c2b5`)
- All logging uses unique grepable codes (see Claude.md for full list)
- GPG signing disabled in repos to avoid signing issues
- Repository singleton via `get_repository()` function
- Conflict detection uses dry-run merge (--no-commit) to avoid repo modification

**To Run/Test Current Implementation:**
```bash
cd /home/user/GitWiki
python manage.py migrate
python manage.py init_config
python manage.py test git_service
python manage.py runserver  # API available at localhost:8000/api/git/
```

---

### ✅ PHASE 2 COMPLETE: Editor Service (Weeks 3-4) - FUNCTIONAL & TESTED

**What's Been Built:**

1. **SimpleMDE Markdown Editor** (`editor/templates/editor/`)
   - ✅ SimpleMDE via CDN with full toolbar
   - ✅ Bootstrap 5 responsive UI
   - ✅ Live preview and fullscreen modes
   - ✅ Keyboard shortcuts (Ctrl+S, Ctrl+P, F11)
   - ✅ Custom status indicators (saved/modified/error)

2. **Editor API** (`editor/api.py` - 600+ lines)
   - ✅ POST `/editor/api/start/` - Start/resume edit session
   - ✅ POST `/editor/api/save/` - Auto-save with validation
   - ✅ POST `/editor/api/commit/` - Commit to Git branch
   - ✅ POST `/editor/api/publish/` - Publish to main (with conflict detection)
   - ✅ POST `/editor/api/validate/` - Validate markdown syntax
   - ✅ POST `/editor/api/upload-image/` - Upload images

3. **Image Upload** (3 upload methods!)
   - ✅ File selector button
   - ✅ Drag & drop onto editor
   - ✅ Clipboard paste (Ctrl+V) for screenshots
   - ✅ Validation: PNG, WebP, JPG, max 10MB (configurable)
   - ✅ Unique filenames: `{page}-{timestamp}-{uuid}.ext`
   - ✅ Stored in `images/{branch_name}/` directory
   - ✅ Auto-commit to Git with is_binary flag
   - ✅ Returns markdown syntax: `![alt](path)`

4. **Editor UI** (`editor/views.py` and templates)
   - ✅ GET `/editor/edit/<file_path>/` - Edit page
   - ✅ GET `/editor/sessions/` - List active drafts
   - ✅ POST `/editor/sessions/<id>/discard/` - Discard draft
   - ✅ Auto-save every 60 seconds
   - ✅ localStorage backup/restore
   - ✅ Commit and publish modals
   - ✅ Validation warnings display
   - ✅ beforeunload warning for unsaved changes

5. **Session Management**
   - ✅ Create EditSession on start_edit
   - ✅ Resume existing sessions (deduplication)
   - ✅ Touch timestamps on save
   - ✅ Mark inactive on publish
   - ✅ Discard functionality
   - ✅ Session list with created/modified times

**Key Implementation Details:**
- Editor uses SimpleMDE with ~400 lines of JavaScript
- All CDN dependencies (SimpleMDE, Bootstrap 5, Axios, Font Awesome)
- Python markdown library for server-side validation
- Binary file support added to git_operations.py (is_binary flag)
- Path traversal prevention in serializers
- HTTP 409 on merge conflicts
- 16 new grepable codes (EDITOR-START01 through EDITOR-VIEW04)
- 7 new AIDEV-NOTEs for navigation

**Files Created:**
```
editor/
├── api.py              # ✅ 600+ lines - 6 API endpoints
├── serializers.py      # ✅ Request validation for all endpoints
├── urls.py            # ✅ URL routing
├── templates/editor/
│   ├── base.html      # ✅ Bootstrap 5 base with nav
│   ├── edit.html      # ✅ SimpleMDE editor with JS
│   └── sessions.html  # ✅ Draft management UI
└── views.py (modified) # ✅ 3 view functions
```

**To Test Editor:**
```bash
cd /home/user/GitWiki
python manage.py runserver
# Visit: http://localhost:8000/editor/edit/docs/test.md
# Try: Auto-save, commit, publish, image paste (Ctrl+V)
# View drafts: http://localhost:8000/editor/sessions/
```

---

### ✅ PHASE 3 COMPLETE: Display Service (Week 5) - FUNCTIONAL & TESTED

**What's Been Built:**

1. **Static File Generation** (`git_service/git_operations.py`)
   - ✅ `write_branch_to_disk()` - Generate static HTML from markdown
   - ✅ `get_file_history()` - Get commit history for files
   - ✅ `_generate_metadata()` - Extract metadata from Git history
   - ✅ `_markdown_to_html()` - Convert markdown to HTML with extensions
   - ✅ Atomic operations using temp directories
   - ✅ Auto-trigger after successful publish

2. **Markdown Processing**
   - ✅ Table of Contents generation (TOC extension)
   - ✅ Code syntax highlighting (CodeHilite with Pygments)
   - ✅ Fenced code blocks
   - ✅ Tables support
   - ✅ Line breaks and sane lists
   - ✅ Metadata files (.md.metadata) with Git history

3. **Display Views** (`display/views.py` - 437 lines)
   - ✅ `wiki_home()` - Home page with README or directory listing
   - ✅ `wiki_page()` - Render individual pages with metadata
   - ✅ `wiki_search()` - Full-text search with pagination
   - ✅ `page_history()` - Show commit history for pages
   - ✅ Breadcrumb navigation generation
   - ✅ Directory listing with icons

4. **Search Functionality**
   - ✅ Full-text search across all markdown files
   - ✅ Title and content matching
   - ✅ Relevance scoring (title matches weighted higher)
   - ✅ Search snippet extraction with highlighting
   - ✅ Pagination (20 results per page)
   - ✅ Branch-specific search

5. **Wiki Theme** (`display/templates/`)
   - ✅ base.html - Responsive Bootstrap 5 layout
   - ✅ page.html - Page display with sidebar and TOC
   - ✅ search.html - Search interface and results
   - ✅ history.html - Commit history display
   - ✅ Custom CSS for wiki styling
   - ✅ Prism.js for code syntax highlighting
   - ✅ Print-friendly styles

6. **Navigation Components**
   - ✅ Breadcrumb trail from file path
   - ✅ Table of contents in sidebar (from markdown headings)
   - ✅ Directory tree navigation
   - ✅ Sidebar with quick actions
   - ✅ Navbar with search box
   - ✅ Edit/History buttons on pages

**Key Implementation Details:**
- Static files generated to `WIKI_STATIC_PATH/{branch_name}/`
- HTML, .md, and .md.metadata files created for each markdown file
- Search uses simple full-text matching (can upgrade to PostgreSQL full-text search later)
- Code highlighting via Prism.js (client-side) and Pygments (server-side HTML generation)
- Responsive design works on mobile, tablet, and desktop
- 14 new grepable codes (DISPLAY-*)
- 2 new AIDEV-NOTE anchors

**Files Created:**
```
display/
├── views.py           # ✅ 437 lines - 5 view functions
├── urls.py            # ✅ URL routing for wiki pages
└── templates/display/
    ├── base.html      # ✅ Base template with wiki theme
    ├── page.html      # ✅ Page display with TOC and sidebar
    ├── search.html    # ✅ Search interface
    └── history.html   # ✅ Commit history display
```

**Files Modified:**
```
git_service/git_operations.py  # ✅ Added 330+ lines for static generation
config/urls.py                 # ✅ Added display routes
requirements.txt               # ✅ Added Pygments
Claude.md                      # ✅ Updated with new codes and notes
```

**To Test Display Service:**
```bash
cd /home/user/GitWiki
python manage.py runserver
# Visit: http://localhost:8000/  (wiki home)
# Try: Search, navigate pages, view history
# Edit a page and publish to see static generation
```

**Statistics:**
- Lines added: ~1,200
- View functions: 5
- Templates: 4
- Grepable codes: 14
- AIDEV-NOTEs: 2
- Extensions used: 5 markdown extensions

---

### ✅ PHASE 5 COMPLETE: GitHub Integration (Week 7) - PRODUCTION READY

**Status:** ✅ 100% Complete (October 25, 2025)

**What Was Built:**

1. **GitHub Sync Operations**
   - `pull_from_github()` - Sync from remote with conflict handling
   - `push_to_github()` - Push to remote with divergence detection
   - SSH authentication and connection testing
   - Handles merge conflicts gracefully during pull

2. **Webhook Integration**
   - GitHub webhook handler with rate limiting (max 1 pull/minute)
   - HMAC SHA-256 signature verification
   - Cached responses (2-minute TTL)
   - JSON payload parsing

3. **Celery Background Tasks**
   - Periodic GitHub pull (every 5 minutes)
   - Daily branch cleanup (2 AM UTC, 7-day threshold)
   - Weekly static rebuild (Sunday 3 AM UTC)
   - Redis broker and result backend
   - Task retry logic and time limits

4. **Branch Cleanup & Rebuild**
   - `cleanup_stale_branches()` - Removes old inactive drafts
   - `full_static_rebuild()` - Complete regeneration of static files
   - Respects active EditSessions
   - Reports disk space freed

5. **Admin UI**
   - Sync management page (manual pull/rebuild/cleanup)
   - GitHub settings page (SSH config, remote URL, webhook secret)
   - Last operation timestamps
   - SSH connection testing button

**Key Files Created:**
- `config/celery.py` - Celery configuration (56 lines)
- `git_service/tasks.py` - 4 periodic tasks (194 lines)
- `git_service/utils.py` - SSH utilities (207 lines)
- `git_service/templates/sync.html` - Sync management UI (205 lines)
- `git_service/templates/github_settings.html` - GitHub config UI (284 lines)

**Statistics:**
- Lines added: ~2,211 across 13 files
- New methods: 4 (pull, push, cleanup, rebuild)
- Periodic tasks: 3 (pull, cleanup, rebuild)
- Admin pages: 2 (sync, settings)
- Integration tests: 15
- Grepable codes: +78
- AIDEV-NOTEs: +8

---

### 🔨 NEXT: PHASE 6 - Configuration & Permissions (Week 8) - Ready to Begin

**Priority: HIGH - Start Here**

**Goal:** Implement permission system and configuration UI for production deployment

**Key Tasks for Phase 6 (8-10 days):**

1. **Permission System Implementation (Days 1-3)**
   - Create permission middleware (`config/middleware.py`)
   - Implement 3 modes: "open", "read_only_public", "private"
   - Enforce permissions in Display Service (view access)
   - Enforce permissions in Editor Service (edit access)
   - Add permission checks to all views

2. **Configuration UI (Days 4-5)**
   - Build configuration management page (`git_service/templates/config.html`)
   - Permission level selector
   - Wiki settings (title, description, branding)
   - File upload limits
   - Branch cleanup thresholds
   - Form validation and save functionality

3. **Authentication Enhancements (Days 6-7)**
   - Create login page template
   - Create logout functionality
   - Add "Login" button to navigation
   - Show username when logged in
   - Create "My Drafts" page for users
   - Session management

4. **Admin Interface Enhancements (Day 8)**
   - Customize Django admin for Configuration model
   - Enhance GitOperation admin (filters, stats)
   - Enhance EditSession admin (user filters, age display)
   - Add admin dashboard improvements

5. **Testing & Documentation (Days 9-10)**
   - Test all three permission modes
   - Integration tests for authentication
   - Permission enforcement tests
   - Update documentation
   - Create Phase 6 summary

**Deliverables:**
- Permission middleware (50-100 lines)
- Configuration UI template (200-300 lines)
- Login/logout templates (100-150 lines)
- "My Drafts" page (100 lines)
- Enhanced admin customizations (100-150 lines)
- 10+ integration tests
- ~30 new grepable codes

**Remaining After Phase 6:**

**Phase 7: Polish & Deployment (Weeks 9-10)**
- Pre-commit hooks for branch naming validation
- Comprehensive error handling audit
- UI/UX improvements from user testing
- Performance optimization (caching, indexes, profiling)
- Security audit (SQL injection, XSS, CSRF, path traversal)
- Achieve 80%+ test coverage
- Load testing with concurrent users
- Complete user, admin, and developer documentation
- Deployment preparation (production settings, Docker, systemd, nginx)
- Initial production deployment
- Monitoring, logging, backups, alerts setup

**Estimated Total Remaining:** 3-4 weeks (Phases 6-7)

---

### 📋 IMPLEMENTATION PHASES OVERVIEW

- ✅ **Phase 1** (Weeks 1-2): Foundation - Git Service **COMPLETE**
- ✅ **Phase 2** (Weeks 3-4): Editor Service - Web editing interface **COMPLETE**
- ✅ **Phase 3** (Week 5): Display Service - Static content serving **COMPLETE**
- ✅ **Phase 4** (Week 6): Conflict Resolution - Monaco Editor integration **COMPLETE**
- ✅ **Phase 5** (Week 7): GitHub Integration - Webhooks, Celery tasks **COMPLETE**
- 🔨 **Phase 6** (Week 8): Configuration & Permissions - Access control ← **YOU ARE HERE** (Ready to Implement)
- ⏳ **Phase 7** (Weeks 9-10): Polish & Deployment - Production ready

**Project Progress:** 70% complete (7 of 10 weeks) | **Next Milestone:** Phase 6 implementation

---

### 📚 ESSENTIAL READING FOR NEXT DEVELOPER

**For Phase 6 Implementation:**
1. **This document** - ⭐ START HERE: See "NEXT: PHASE 6" section above for detailed roadmap
2. **distributed-wiki-project-plan.md** - Sections on Configuration & Permissions (lines 1440-1650)
3. **Claude.md** - Development guidelines, AIDEV-NOTE locations, grepable codes (182+ codes documented)

**For Understanding Current System:**
4. **PROJECT_REVIEW_2025-10-25.md** - Comprehensive architectural review and Phase 5 assessment
5. **IMPLEMENTATION_PLAN.md** - Detailed task breakdown for all phases
6. **README.md** - Setup guide, current API documentation
7. This document (sections below) - Django app structure details and API specifications

**Questions?** Check git commit history with `[AI]` tag for implementation context.

---

## Executive Summary

A distributed, Git-backed markdown wiki system with web-based editing, clipboard image support, conflict resolution, and static file serving. The system supports draft/publish workflows, GitHub synchronization, and can operate as both a collaborative wiki and a static documentation site.

## Project Goals

- Simple distributed wiki that works equally well via desktop markdown editors and web UI
- Git-based versioning with full history and conflict management
- Easy image handling via clipboard paste in web interface
- Static file generation for fast read performance
- GitHub synchronization with webhook and polling support
- Draft/publish workflow to separate work-in-progress from published content

## Non-Negotiables

1. Git as the versioning backend
2. Web UI for editing
3. Clipboard image paste support for screenshots
4. Merge conflict detection and resolution
5. Standard markdown format for maximum compatibility

---

## Technology Stack

### Backend
- **Framework**: Django (Python)
- **Git Operations**: GitPython library
- **Task Queue**: Celery with Redis
- **Web Server**: Gunicorn (production)

### Frontend
- **Markdown Editor**: SimpleMDE, Tui Editor, or Monaco Editor
- **Conflict Resolution**: Monaco Editor (three-way diff)
- **Image Handling**: JavaScript Clipboard API
- **Styling**: TBD (minimal, documentation-focused)

### Infrastructure
- **Version Control**: Git with GitHub remote
- **Authentication**: SSH keys for GitHub
- **Storage**: Local filesystem for static generation
- **Deployment**: TBD (assume standard Django deployment)

---

## System Architecture

### High-Level Overview

The system consists of three main Django apps within a single project:

1. **Git Service** - Handles all repository operations
2. **Editor Service** - Provides markdown editing interface
3. **Display Service** - Serves static content with optional API enhancements

All apps share Django's user authentication system but are architecturally independent (95%+ separation of concerns).

### Architecture Principles

- Each app should be coded as if it could be extracted into a separate service
- Apps communicate via well-defined API contracts, not direct model imports
- Git Service is the single source of truth for all content
- Static file generation provides fast read performance
- Draft branches separate work-in-progress from published content

---

## Django Apps Structure

### 1. Git Service App

**Responsibilities:**
- All Git repository operations (branch, commit, merge, push, pull)
- Static file generation from Git branches
- Conflict detection and management
- GitHub synchronization
- Operation auditing

**Does NOT:**
- Handle user interface
- Make decisions about content
- Manage user sessions

### 2. Editor Service App

**Responsibilities:**
- Markdown editing interface (WYSIWYG and source modes)
- Edit session management
- Image upload handling
- Draft saving and publishing
- Markdown validation

**Does NOT:**
- Perform Git operations directly
- Generate static files
- Handle merge conflicts

### 3. Display Service App

**Responsibilities:**
- Serve static markdown content as HTML
- Handle navigation and relative links
- Show basic page metadata
- Optional async API calls for advanced features (history, diffs)

**Does NOT:**
- Perform Git operations
- Handle editing
- Generate content

---

## Data Models

### User
- Uses Django's built-in User model
- Authentication only (no complex roles for MVP)

### EditSession
**Fields:**
- `id` (primary key)
- `user_id` (foreign key to User)
- `file_path` (path to file being edited)
- `branch_name` (draft branch name)
- `created_at` (timestamp)
- `last_modified` (timestamp)
- `is_active` (boolean)

**Purpose:** Track active editing sessions before publishing

### Configuration
**Fields:**
- `key` (string, unique)
- `value` (JSON or text)
- `description` (text)
- `created_at` (timestamp)
- `modified_at` (timestamp)

**Purpose:** Store application settings without environment variables

**Key Settings:**
- `github_remote_url` - Repository URL
- `github_ssh_key_path` - Path to SSH key
- `auto_push_enabled` - Boolean for automatic pushing
- `permission_level` - "open", "read_only_public", or "private"
- `branch_prefix_draft` - Prefix for draft branches (default: "draft")
- `max_image_size_mb` - Maximum image upload size
- `supported_image_formats` - List of allowed formats

### GitOperation (Audit Log)
**Fields:**
- `id` (primary key)
- `operation_type` (string: create_branch, commit, merge, push, pull, etc.)
- `user_id` (foreign key to User, nullable for system operations)
- `branch_name` (string, nullable)
- `file_path` (string, nullable)
- `request_parameters` (JSON - stores all input parameters)
- `response_code` (integer - HTTP status code)
- `success` (boolean)
- `git_output` (text - raw Git command output)
- `error_message` (text, nullable)
- `execution_time_ms` (integer)
- `timestamp` (datetime)

**Purpose:** Complete audit trail of all Git operations for debugging and analysis

---

## Git Service API

### Core Operations

#### `create_draft_branch(user_id: int) -> dict`
**Purpose:** Create a unique draft branch for user editing

**Returns:**
```json
{
  "branch_name": "draft-{user_id}-{uuid_fragment}",
  "success": true
}
```

**Error Codes:**
- `500` - Git repository error
- `422` - Invalid user_id
- `507` - Insufficient disk space

---

#### `commit_changes(branch_name: str, file_path: str, content: str, commit_message: str, user_info: dict) -> dict`
**Purpose:** Commit changes to a draft branch

**Parameters:**
```json
{
  "branch_name": "draft-123-abc456",
  "file_path": "docs/getting-started.md",
  "content": "# Getting Started\n...",
  "commit_message": "Update getting started guide",
  "user_info": {
    "name": "John Doe",
    "email": "john@example.com"
  }
}
```

**Returns:**
```json
{
  "commit_hash": "abc123...",
  "success": true
}
```

**Error Codes:**
- `500` - Git operation failed
- `422` - Invalid file path or content
- `409` - Branch doesn't exist

---

#### `publish_draft(branch_name: str) -> dict`
**Purpose:** Merge draft branch to main and push to remote

**Process:**
1. Attempt merge of draft branch to main
2. If successful:
   - Write static files for main branch
   - Push to GitHub remote
   - Delete draft branch
   - Return success
3. If merge conflict:
   - Leave draft branch intact
   - Return conflict details
   - Do not push to remote

**Returns (Success):**
```json
{
  "success": true,
  "merged": true,
  "pushed": true,
  "commit_hash": "def456..."
}
```

**Returns (Conflict):**
```json
{
  "success": false,
  "merged": false,
  "conflicts": [
    {
      "file_path": "docs/page.md",
      "conflict_type": "content"
    }
  ]
}
```

**Error Codes:**
- `409` - Merge conflict detected
- `500` - Git operation failed
- `502` - GitHub push failed
- `404` - Branch not found

---

#### `get_conflicts() -> dict`
**Purpose:** Get list of all branches with merge conflicts

**Process:**
1. List all draft branches
2. For each branch, run dry-run merge against main
3. Detect conflicts without modifying repository
4. Return structured conflict information

**Returns:**
```json
{
  "conflicts": [
    {
      "branch_name": "draft-123-abc456",
      "file_path": "docs/page.md",
      "conflict_type": "content",
      "user_id": 123,
      "created_at": "2025-10-25T10:00:00Z"
    }
  ]
}
```

**Caching:** Results should be cached for 1-2 minutes to avoid expensive operations

**Error Codes:**
- `500` - Git repository error

---

#### `resolve_conflict(branch_name: str, file_path: str, resolution: dict) -> dict`
**Purpose:** Apply conflict resolution and retry merge

**Parameters:**
```json
{
  "branch_name": "draft-123-abc456",
  "file_path": "docs/page.md",
  "resolution": {
    "strategy": "manual",
    "content": "resolved content...",
    "user_id": 123
  }
}
```

**Returns:**
```json
{
  "success": true,
  "merged": true
}
```

**Error Codes:**
- `422` - Invalid resolution data
- `409` - Conflict has changed since resolution started
- `500` - Git operation failed

---

#### `get_file_history(file_path: str, branch: str = "main", limit: int = 50) -> dict`
**Purpose:** Get commit history for a specific file

**Returns:**
```json
{
  "file_path": "docs/page.md",
  "commits": [
    {
      "hash": "abc123",
      "author": "John Doe",
      "email": "john@example.com",
      "date": "2025-10-25T10:00:00Z",
      "message": "Update page",
      "changes": {
        "additions": 5,
        "deletions": 2
      }
    }
  ]
}
```

**Error Codes:**
- `404` - File not found
- `500` - Git operation failed

---

### GitHub Synchronization Operations

#### `pull_from_github() -> dict`
**Purpose:** Pull latest changes from GitHub remote

**Process:**
1. Git fetch from remote
2. Git pull (merge remote changes)
3. Regenerate static files if changes detected
4. Log operation

**Returns:**
```json
{
  "success": true,
  "changes_detected": true,
  "files_changed": ["docs/page1.md", "docs/page2.md"],
  "static_regenerated": true
}
```

**Error Codes:**
- `500` - Git operation failed
- `502` - GitHub connection failed
- `401` - SSH authentication failed

---

#### `push_to_github(branch: str = "main") -> dict`
**Purpose:** Push local changes to GitHub remote

**Returns:**
```json
{
  "success": true,
  "branch": "main",
  "commits_pushed": 3
}
```

**Error Codes:**
- `500` - Git operation failed
- `502` - GitHub connection failed
- `409` - Remote has changes, need to pull first
- `401` - SSH authentication failed

---

#### `webhook_handler() -> dict`
**Purpose:** Handle incoming GitHub webhooks

**Process:**
1. Rate limit check (max once per minute)
2. Trigger `pull_from_github()`
3. Return status

**Rate Limiting:**
- Maximum one pull per minute
- Additional webhook calls within rate limit return cached status
- Prevents DDoS via webhook abuse

**Returns:**
```json
{
  "success": true,
  "action": "pulled|rate_limited",
  "last_pull": "2025-10-25T10:00:00Z"
}
```

---

### Static File Generation

#### `write_branch_to_disk(branch_name: str) -> dict`
**Purpose:** Export complete branch state to static files

**Process:**
1. Create temporary directory
2. Git checkout branch to temporary directory
3. Copy all files to `/static/{branch_name}/`
4. Write metadata files (`.metadata` files for each content file)
5. Atomic move from temp to final location
6. Log operation

**Metadata File Format** (`.metadata` suffix):
```json
{
  "file_path": "docs/page.md",
  "last_commit": {
    "hash": "abc123",
    "author": "John Doe",
    "date": "2025-10-25T10:00:00Z",
    "message": "Update page"
  },
  "history_summary": {
    "total_commits": 15,
    "contributors": ["John Doe", "Jane Smith"],
    "created": "2025-01-01T00:00:00Z",
    "last_modified": "2025-10-25T10:00:00Z"
  }
}
```

**Atomic Operation:**
- Generate to `/static/.tmp-{uuid}/`
- Move atomically to `/static/{branch_name}/`
- Prevents inconsistent state during generation

**Triggers:**
- After successful merge to main
- After commit to draft branch
- After pull from GitHub
- Manual regeneration request

**Returns:**
```json
{
  "success": true,
  "branch_name": "main",
  "files_written": 47,
  "execution_time_ms": 1250
}
```

**Error Codes:**
- `500` - File system error
- `507` - Insufficient disk space

---

### Cleanup Operations

#### `cleanup_stale_branches(age_days: int = 7) -> dict`
**Purpose:** Remove old draft branches and their static files

**Process:**
1. List all draft branches
2. Check last commit date
3. Delete branches older than threshold
4. Remove associated static files
5. Log operation

**Execution:** Celery periodic task (daily)

**Returns:**
```json
{
  "success": true,
  "branches_deleted": 5,
  "disk_space_freed_mb": 150
}
```

---

#### `full_static_rebuild() -> dict`
**Purpose:** Complete regeneration of all static files

**Process:**
1. Delete all static directories except temp
2. Regenerate static files for main branch
3. Regenerate for any active draft branches
4. Verify integrity

**Execution:** 
- Celery periodic task (weekly recommended)
- Manual trigger via admin interface

**Returns:**
```json
{
  "success": true,
  "branches_regenerated": ["main", "draft-123-abc"],
  "total_files": 150,
  "execution_time_ms": 5000
}
```

---

## Editor Service API

### Editing Operations

#### `start_edit(user_id: int, file_path: str) -> dict`
**Purpose:** Begin editing a file

**Process:**
1. Create draft branch via Git Service
2. Create EditSession record
3. Load current file content
4. Return edit session details

**Returns:**
```json
{
  "session_id": 456,
  "branch_name": "draft-123-abc456",
  "file_path": "docs/page.md",
  "content": "# Page Title\nContent...",
  "markdown_valid": true
}
```

**Error Codes:**
- `500` - Failed to create branch
- `404` - File not found
- `422` - Invalid file path

---

#### `save_draft(session_id: int, content: str) -> dict`
**Purpose:** Save draft changes (auto-save)

**Process:**
1. Validate markdown syntax
2. Store in localStorage (client-side)
3. Update EditSession timestamp
4. Return validation status

**Note:** Does NOT commit to Git - this is client-side only

**Returns:**
```json
{
  "success": true,
  "saved_at": "2025-10-25T10:05:00Z",
  "markdown_valid": true,
  "validation_errors": []
}
```

---

#### `commit_draft(session_id: int, content: str, commit_message: str) -> dict`
**Purpose:** Commit draft to Git branch

**Process:**
1. Validate markdown
2. Call Git Service `commit_changes()`
3. Update EditSession
4. Return commit status

**Returns:**
```json
{
  "success": true,
  "commit_hash": "abc123",
  "branch_name": "draft-123-abc456"
}
```

**Error Codes:**
- `422` - Invalid markdown or content
- `500` - Git operation failed
- `404` - Session not found

---

#### `publish_edit(session_id: int) -> dict`
**Purpose:** Publish draft to main branch

**Process:**
1. Call Git Service `publish_draft()`
2. If successful:
   - Close EditSession
   - Return success
3. If conflict:
   - Keep EditSession active
   - Return conflict details for UI

**Returns (Success):**
```json
{
  "success": true,
  "published": true,
  "url": "/docs/page.html"
}
```

**Returns (Conflict):**
```json
{
  "success": false,
  "conflict": true,
  "conflict_details": {
    "file_path": "docs/page.md",
    "resolution_url": "/conflicts/resolve/draft-123-abc456"
  }
}
```

**Error Codes:**
- `409` - Merge conflict
- `500` - Git operation failed
- `502` - GitHub push failed

---

#### `validate_markdown(content: str) -> dict`
**Purpose:** Validate markdown syntax

**Process:**
1. Parse markdown with Python markdown library
2. Check for syntax errors
3. Return validation results

**Returns:**
```json
{
  "valid": true,
  "errors": [],
  "warnings": ["Line 15: Unclosed code block"]
}
```

**Error Codes:**
- `422` - Contains validation errors (still returns error details)

---

### Image Operations

#### `upload_image(session_id: int, image_file: file, alt_text: str = "") -> dict`
**Purpose:** Handle image upload from clipboard or file selection

**Process:**
1. Validate file type (PNG, WebP, JPG only)
2. Validate file size (max 10MB)
3. Generate unique filename
4. Save to `/images/{branch_name}/{filename}`
5. Commit image file to Git
6. Return markdown image syntax

**Returns:**
```json
{
  "success": true,
  "filename": "screenshot-20251025-100500.png",
  "path": "images/draft-123-abc456/screenshot-20251025-100500.png",
  "markdown": "![alt text](images/draft-123-abc456/screenshot-20251025-100500.png)",
  "file_size_bytes": 245000
}
```

**Error Codes:**
- `422` - Invalid file type or size
- `413` - File too large (>10MB)
- `500` - Save failed

**Supported Formats:**
- PNG (image/png)
- WebP (image/webp)
- JPG/JPEG (image/jpeg)

**Max File Size:** 10MB

---

## Display Service API

### Content Serving

#### `get_page(branch: str, file_path: str) -> HTML`
**Purpose:** Serve rendered markdown page

**Process:**
1. Read file from `/static/{branch}/{file_path}`
2. Parse markdown to HTML
3. Load metadata file if exists
4. Render template with content and metadata
5. Return HTML

**URL Pattern:** `/{branch}/{file_path}`  
**Example:** `/main/docs/getting-started` or `/draft-123-abc/docs/page`

**Response:** Rendered HTML page

---

#### `get_page_metadata(branch: str, file_path: str) -> JSON`
**Purpose:** Get page metadata for async loading

**Process:**
1. Read `.metadata` file
2. Return JSON

**URL Pattern:** `/api/metadata/{branch}/{file_path}`

**Returns:**
```json
{
  "file_path": "docs/page.md",
  "last_commit": {
    "hash": "abc123",
    "author": "John Doe",
    "date": "2025-10-25T10:00:00Z"
  },
  "history_summary": {
    "total_commits": 15,
    "contributors": ["John Doe", "Jane Smith"]
  }
}
```

---

#### `list_pages(branch: str, directory: str = "") -> JSON`
**Purpose:** Get directory listing for navigation

**Process:**
1. Read directory from static files
2. Return file tree structure

**Returns:**
```json
{
  "branch": "main",
  "path": "docs/",
  "files": [
    {
      "name": "getting-started.md",
      "type": "file",
      "url": "/main/docs/getting-started"
    },
    {
      "name": "api/",
      "type": "directory",
      "files": ["..."]
    }
  ]
}
```

---

### Enhanced Features (Optional Async)

These endpoints are called asynchronously by JavaScript for power-user features.

#### `get_detailed_history(branch: str, file_path: str) -> JSON`
**Purpose:** Get complete edit history with diffs

**Process:**
1. Call Git Service `get_file_history()`
2. Format for UI display
3. Return JSON

**Returns:**
```json
{
  "file_path": "docs/page.md",
  "commits": [
    {
      "hash": "abc123",
      "author": "John Doe",
      "date": "2025-10-25T10:00:00Z",
      "message": "Update page",
      "diff_url": "/api/diff/abc123"
    }
  ]
}
```

**UI:** Loads in modal or overlay

---

#### `get_user_contributions(user_id: int) -> JSON`
**Purpose:** Get all edits by a specific user

**Returns:**
```json
{
  "user_id": 123,
  "user_name": "John Doe",
  "contributions": [
    {
      "file_path": "docs/page.md",
      "commit_hash": "abc123",
      "date": "2025-10-25T10:00:00Z",
      "message": "Update page"
    }
  ]
}
```

**UI:** Special page or modal

---

## Conflict Resolution Interface

### Conflict Detection Page

**URL:** `/conflicts/`

**Purpose:** Dashboard showing all unresolved conflicts

**Process:**
1. Call Git Service `get_conflicts()`
2. Display table of conflicted branches and files
3. Provide links to resolution interface

**UI Elements:**
- Table with columns: Branch Name, File Path, User, Created Date, Action
- "Resolve" button for each conflict
- Auto-refresh every 30 seconds

---

### Conflict Resolution Page

**URL:** `/conflicts/resolve/{branch_name}/{file_path}`

**Purpose:** Interactive conflict resolution interface

**For Text Files:**
- Use Monaco Editor in diff mode
- Show three-pane view: base, theirs, ours
- Built-in conflict resolution controls
- Save button calls Git Service `resolve_conflict()`

**For Images:**
- Show both versions side-by-side
- Preview both images
- Radio buttons to choose: "Keep Mine" | "Keep Theirs"
- Apply button commits choice

**For Other Binary Files:**
- Show file name, size, SHA hash
- Download links for both versions
- Radio buttons to choose version
- Apply button commits choice

**UI Flow:**
1. Load conflicted file content
2. Display appropriate interface (Monaco/Image/Binary)
3. User resolves conflict
4. Submit resolution to Git Service
5. If successful, redirect to page
6. If failed, show error and allow retry

---

## Branch Taxonomy

### Branch Naming Conventions

**Draft Branches:**
- Format: `draft-{user_id}-{uuid_fragment}`
- Example: `draft-123-a8f3c2`
- Purpose: Work-in-progress edits
- Lifecycle: Created on edit start, deleted after successful publish or cleanup

**Main Branch:**
- Name: `main`
- Purpose: Published, production content
- Protection: All changes must come through draft branches

**UUID Fragment:**
- Use first 6-8 characters of UUID v4
- Ensures uniqueness even with timestamp collisions
- Example: `a8f3c2b5`

### Branch Operations

**Creating:**
```bash
git checkout -b draft-{user_id}-{uuid}
```

**Publishing (Merging):**
```bash
git checkout main
git merge draft-{user_id}-{uuid}
git push origin main
git branch -d draft-{user_id}-{uuid}
```

**Conflict Detection (Dry Run):**
```bash
git merge --no-commit --no-ff draft-{user_id}-{uuid}
# Check for conflicts
git merge --abort
```

### Pre-Commit Hooks

**Purpose:** Enforce branch naming taxonomy

**Hook Location:** `.git/hooks/pre-commit`

**Validation Rules:**
1. Draft branches must follow `draft-{number}-{alphanumeric}` pattern
2. Direct commits to `main` branch are blocked (must come through merges)
3. Branch names must not exceed 50 characters

**Installation:**
- Server: Automatically installed on repository initialization
- Client: Provided as installable script for users

**Example Hook:**
```bash
#!/bin/bash
branch=$(git symbolic-ref --short HEAD)

if [[ $branch == "main" ]]; then
  echo "Error: Direct commits to main are not allowed"
  echo "Please create a draft branch and publish through the web UI"
  exit 1
fi

if [[ $branch == draft-* ]]; then
  if [[ ! $branch =~ ^draft-[0-9]+-[a-z0-9]{6,8}$ ]]; then
    echo "Error: Invalid draft branch name: $branch"
    echo "Format must be: draft-{user_id}-{uuid}"
    exit 1
  fi
fi

exit 0
```

---

## Configuration & Permissions

### Permission Levels

#### Open (Fully Public)
- Anyone can view pages without login
- Anyone can edit and create pages without login
- Use case: Public collaborative wikis

#### Read-Only Public
- Anyone can view pages without login
- Login required to edit or create pages
- Use case: Public documentation with controlled editing

#### Private
- Login required to view any content
- Login required to edit or create pages
- Use case: Internal company wikis

**Configuration Storage:**
```python
# In Configuration model
{
  "key": "permission_level",
  "value": "read_only_public",  # or "open" or "private"
}
```

**Enforcement:**
- Display Service checks permission level before serving pages
- Editor Service checks before allowing edit session creation
- Django middleware handles authentication redirects

---

### GitHub Configuration

**Required Settings:**

```python
{
  "github_remote_url": "git@github.com:username/repo.git",
  "github_ssh_key_path": "/path/to/ssh/private/key",
  "auto_push_enabled": true,
  "webhook_secret": "optional_secret_for_verification"
}
```

**SSH Key Setup:**
1. Generate SSH key pair
2. Add public key to GitHub repository deploy keys
3. Store private key path in configuration
4. Ensure proper file permissions (600)

**Testing Configuration:**
```bash
ssh -T git@github.com -i /path/to/key
```

---

## Markdown Support

### Supported Markdown Features (MVP)

**Basic Formatting:**
- Headers (H1-H6)
- Paragraphs
- Bold, italic, strikethrough
- Inline code
- Code blocks with syntax highlighting
- Links (relative and absolute)
- Images

**Lists:**
- Unordered lists
- Ordered lists
- Nested lists
- Task lists

**Structure:**
- Blockquotes
- Horizontal rules
- Basic tables

**Special:**
- Relative wiki links
- Image embedding from repository

### NOT Supported in MVP

- HTML embedding (security risk)
- Custom CSS/styling
- Complex table features (sorting, filtering)
- Math/LaTeX equations
- Mermaid diagrams (post-MVP)
- Custom attributes
- Footnotes

### Markdown Validation

**Validator:** Python `markdown` library with error capture

**Validation Points:**
- On save draft (soft warning)
- On commit (hard error if invalid)
- Real-time in editor (optional)

**Error Handling:**
```json
{
  "valid": false,
  "errors": [
    {
      "line": 15,
      "message": "Unclosed code block",
      "severity": "error"
    }
  ]
}
```

---

## Error Handling Strategy

### HTTP Status Codes

**Success:**
- `200 OK` - Successful operation
- `201 Created` - Resource created successfully

**Client Errors:**
- `400 Bad Request` - Malformed request
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Permission denied
- `404 Not Found` - Resource doesn't exist
- `409 Conflict` - Merge conflict or resource conflict
- `413 Payload Too Large` - File too large
- `422 Unprocessable Entity` - Validation error

**Server Errors:**
- `500 Internal Server Error` - Git operation failed, general error
- `502 Bad Gateway` - GitHub connection failed
- `507 Insufficient Storage` - Disk space issues

### Operation Rollback

**Principle:** All operations must be atomic or rollbackable

**Git Operations:**
- Use Git worktrees or separate working directories
- Never modify main repository during merge attempts
- On failure, discard working tree, leave main repository untouched

**File System Operations:**
- Static generation uses temp directories
- Atomic move after complete generation
- Failed generation leaves existing static files intact

**Database Operations:**
- Use Django transactions
- Rollback on any failure in multi-step operations

### Cleanup After Failures

**Failed Merges:**
- Leave draft branch intact
- Add to conflict resolution queue
- Notify user via UI

**Failed Commits:**
- Preserve user content in EditSession
- Allow retry
- Log error for debugging

**Failed Pushes:**
- Keep local changes committed
- Retry push automatically on next operation
- Show warning in UI about unpushed changes

---

## Celery Tasks & Background Jobs

### Periodic Tasks

#### GitHub Pull
**Schedule:** Every 5 minutes  
**Task:** `pull_from_github()`  
**Purpose:** Backup sync in case webhooks fail

#### Branch Cleanup
**Schedule:** Daily at 2 AM  
**Task:** `cleanup_stale_branches(age_days=7)`  
**Purpose:** Remove old draft branches

#### Full Static Rebuild
**Schedule:** Weekly (Sunday at 3 AM)  
**Task:** `full_static_rebuild()`  
**Purpose:** Ensure static files are consistent

### Webhook Handler
**Trigger:** GitHub webhook POST  
**Task:** `pull_from_github()`  
**Rate Limit:** Maximum once per minute

### Manual Triggers
- Sync Now button → `pull_from_github()`
- Rebuild Static button → `full_static_rebuild()`

---

## File System Structure

### Repository Structure
```
/app/
├── repo/                          # Git repository
│   ├── .git/                      # Git internals
│   ├── docs/                      # Documentation files
│   │   ├── getting-started.md
│   │   └── api/
│   │       └── endpoints.md
│   └── images/                    # Images
│       ├── main/                  # Main branch images
│       └── draft-123-abc/         # Draft branch images
```

### Static Files Structure
```
/app/
├── static/                        # Generated static files
│   ├── main/                      # Main branch static
│   │   ├── docs/
│   │   │   ├── getting-started.html
│   │   │   ├── getting-started.md.metadata
│   │   │   └── api/
│   │   │       ├── endpoints.html
│   │   │       └── endpoints.md.metadata
│   │   └── images/
│   │       └── [image files]
│   ├── draft-123-abc/             # Draft branch static
│   │   └── [same structure]
│   └── .tmp-{uuid}/               # Temporary generation directory
```

### Django Project Structure
```
/app/
├── manage.py
├── config/                        # Django settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── git_service/                   # Git Service app
│   ├── models.py
│   ├── views.py
│   ├── api.py
│   ├── git_operations.py
│   └── tasks.py
├── editor/                        # Editor Service app
│   ├── models.py
│   ├── views.py
│   ├── api.py
│   └── templates/
├── display/                       # Display Service app
│   ├── views.py
│   ├── api.py
│   └── templates/
└── requirements.txt
```

---

## Implementation Phases

### Phase 1: Foundation (Weeks 1-2)
**Goal:** Basic Django project with Git Service

**Tasks:**
1. Create Django project structure
2. Set up three Django apps
3. Implement core models (User, EditSession, Configuration, GitOperation)
4. Implement basic Git Service operations:
   - create_draft_branch()
   - commit_changes()
   - publish_draft()
5. Write unit tests for Git operations
6. Set up GitPython integration
7. Implement operation logging

**Deliverable:** Working Git Service with API endpoints

---

### Phase 2: Editor Service (Weeks 3-4)
**Goal:** Web-based markdown editor

**Tasks:**
1. Create Editor Service app
2. Integrate markdown editor (SimpleMDE or Tui Editor)
3. Implement Editor API:
   - start_edit()
   - save_draft() (localStorage)
   - commit_draft()
   - publish_edit()
   - validate_markdown()
4. Implement image upload functionality
5. Add clipboard paste support for images
6. Create edit session UI
7. Add WYSIWYG/source mode toggle
8. Write tests for editor workflows

**Deliverable:** Functional web editor with draft/publish workflow

---

### Phase 3: Display Service (Week 5)
**Goal:** Static content serving

**Tasks:**
1. Create Display Service app
2. Implement static file generation:
   - write_branch_to_disk()
   - Metadata file generation
3. Create page rendering templates
4. Implement relative link resolution
5. Add navigation components
6. Implement branch switching UI
7. Create basic styling
8. Write tests for display functionality

**Deliverable:** Working static wiki viewer

---

### Phase 4: Conflict Resolution (Week 6)
**Goal:** Merge conflict handling

**Tasks:**
1. Implement conflict detection:
   - get_conflicts()
   - Dry-run merge testing
2. Create conflicts dashboard page
3. Integrate Monaco Editor for text conflicts
4. Implement image conflict resolution UI
5. Implement binary file conflict resolution UI
6. Add conflict resolution workflow:
   - resolve_conflict()
7. Write tests for conflict scenarios

**Deliverable:** Complete conflict resolution system

---

### Phase 5: GitHub Integration (Week 7)
**Goal:** Remote synchronization

**Tasks:**
1. Implement GitHub operations:
   - pull_from_github()
   - push_to_github()
2. Add SSH key configuration
3. Implement webhook handler
4. Add webhook rate limiting
5. Create Celery tasks:
   - Periodic pull
   - Branch cleanup
   - Static rebuild
6. Add "Sync Now" manual button
7. Write tests for GitHub sync

**Deliverable:** Full GitHub synchronization

---

### Phase 6: Configuration & Permissions (Week 8)
**Goal:** Complete configuration system

**Tasks:**
1. Implement permission levels:
   - Open
   - Read-only public
   - Private
2. Add configuration UI/admin interface
3. Implement authentication middleware
4. Add SSH key testing utility
5. Create setup documentation
6. Write tests for permissions

**Deliverable:** Configurable permission system

---

### Phase 7: Polish & Deployment (Weeks 9-10)
**Goal:** Production-ready application

**Tasks:**
1. Implement pre-commit hooks
2. Add comprehensive error handling
3. Improve UI/UX based on testing
4. Write deployment documentation
5. Set up production configuration
6. Perform security audit
7. Load testing
8. Bug fixes
9. Create user documentation

**Deliverable:** Production-ready wiki system

---

## Testing Strategy

### Unit Tests
- All Git Service operations
- All API endpoints
- Markdown validation
- Image upload handling
- Conflict detection logic

### Integration Tests
- Complete draft/publish workflow
- GitHub sync operations
- Conflict resolution workflow
- Permission enforcement

### End-to-End Tests
- User editing journey
- Multi-user concurrent editing
- Merge conflict resolution
- Image upload and display

### Performance Tests
- Static file generation time
- Large repository handling
- Concurrent user operations
- GitHub sync performance

---

## Security Considerations

### Authentication
- Django's built-in authentication system
- Session-based authentication for web UI
- SSH key authentication for GitHub

### Authorization
- Permission level enforcement at middleware level
- User-based branch ownership for drafts
- Admin-only access to configuration

### Input Validation
- Markdown content sanitization
- File upload validation (type, size)
- Path traversal prevention
- SQL injection prevention (Django ORM)

### Git Operations
- Separate working directories for merge attempts
- No direct shell command injection
- Use GitPython library's safe methods
- Validate all file paths

### File System
- Proper file permissions
- Atomic file operations
- Disk space monitoring
- Path sanitization

---

## Post-MVP Features

### Deferred to Later Versions

1. **Mermaid Diagram Support**
   - Add diagram rendering library
   - Extend markdown validation

2. **Advanced Permission System**
   - Page-level permissions
   - User roles (editor, viewer, admin)
   - Group-based access control

3. **Git LFS Support**
   - Handle large binary files efficiently
   - Reduce repository bloat

4. **Search Functionality**
   - Full-text search across all pages
   - Search within specific branches

5. **Version Comparison**
   - Side-by-side diff view for any two versions
   - Visual diff for images

6. **Collaborative Editing**
   - Real-time collaborative editing
   - Presence indicators

7. **Email Notifications**
   - Notify users of conflicts
   - Digest of recent changes
   - Mention notifications

8. **Export Functionality**
   - Export to PDF
   - Export to static site
   - Backup entire wiki

9. **Advanced Editor Features**
   - Auto-complete for wiki links
   - Template system for pages
   - Table of contents generation

10. **Analytics**
    - Page view tracking
    - Popular pages dashboard
    - Edit frequency analysis

11. **API for External Tools**
    - REST API for programmatic access
    - Webhook for external systems
    - CLI tool

12. **Mobile Optimization**
    - Responsive design improvements
    - Mobile-specific editor
    - Progressive Web App

---

## Technical Notes & Decisions

### Why Django Over Flask?
- Built-in admin interface
- Robust ORM
- Authentication system
- Better long-term scalability
- Template system for complex views

### Why Static File Generation?
- Extremely fast read performance
- Simple deployment
- No Git operations for page views
- Easy to cache and CDN-enable
- Clear separation of read/write paths

### Why Draft/Publish Over Direct Editing?
- Prevents lost work
- Clear "ready to publish" gate
- Easier conflict management
- Matches Git's natural workflow

### Why Monaco Editor for Conflicts?
- Industry-standard diff interface
- Three-way merge support
- Syntax highlighting included
- Widely understood by developers

### Why Not Git Hooks for Validation?
- Git hooks are for post-MVP
- Initial focus on web UI workflow
- Hooks add deployment complexity

### Storage Considerations
- Text files: minimal storage
- Images: assume reasonable documentation usage
- Vertical scaling acceptable for MVP
- Large repos: post-MVP optimization

---

## Success Criteria

### Functional Requirements Met
- ✅ Users can edit markdown via web UI
- ✅ Users can paste images from clipboard
- ✅ All changes tracked in Git with full history
- ✅ Merge conflicts detected and resolvable
- ✅ Static site generated for fast viewing
- ✅ GitHub synchronization working
- ✅ Draft/publish workflow implemented

### Performance Targets
- Page load time: < 200ms (static pages)
- Edit session start: < 2 seconds
- Image upload: < 5 seconds for 10MB
- Static generation: < 10 seconds for 100 pages
- Conflict detection: < 30 seconds for 20 branches

### Reliability Targets
- 99% uptime for read operations
- Git operations: 100% atomic (no corruption)
- Data loss: zero tolerance
- Conflict resolution: 100% detection rate

---

## Deployment Checklist

### Pre-Deployment
- [ ] All tests passing
- [ ] Security audit completed
- [ ] Performance testing completed
- [ ] Documentation completed
- [ ] SSH keys configured
- [ ] GitHub repository set up
- [ ] Pre-commit hooks installed

### Initial Deployment
- [ ] Django settings configured for production
- [ ] Database migrations run
- [ ] Static files generated
- [ ] Celery workers started
- [ ] Redis running
- [ ] Web server configured (Gunicorn)
- [ ] Reverse proxy configured (Nginx)
- [ ] SSL certificates installed
- [ ] GitHub webhook configured
- [ ] Backups configured

### Post-Deployment
- [ ] Health checks passing
- [ ] Logs being collected
- [ ] Monitoring alerts configured
- [ ] User documentation accessible
- [ ] Admin users created
- [ ] Initial content imported
- [ ] Test edit/publish workflow
- [ ] Test conflict resolution
- [ ] Test GitHub sync

---

## Open Questions & Decisions Needed

1. **Frontend Framework:** Use vanilla JavaScript or add React/Vue?
2. **Styling Framework:** Bootstrap, Tailwind, or custom CSS?
3. **Deployment Target:** AWS, DigitalOcean, self-hosted?
4. **Domain & Hosting:** URL and hosting provider?
5. **Backup Strategy:** How often? Where stored?
6. **Monitoring:** What monitoring tools?
7. **Error Tracking:** Sentry or alternative?
8. **Rate Limiting:** Beyond webhook rate limit?

---

## Appendix: Example Workflows

### Workflow 1: Simple Page Edit

1. User clicks "Edit" on a page
2. System creates draft branch: `draft-123-a8f3c2`
3. System creates EditSession record
4. Editor loads with current content
5. User makes changes
6. System auto-saves to localStorage every minute
7. User clicks "Publish"
8. System commits changes to draft branch
9. System attempts merge to main
10. Merge succeeds
11. System pushes to GitHub
12. System regenerates static files
13. System shows success message
14. User sees published changes

### Workflow 2: Conflicting Edits

1. User A starts editing page: draft-123-a8f3c2
2. User B starts editing same page: draft-456-b9g4d3
3. User A publishes successfully
4. User B attempts to publish
5. System detects merge conflict
6. System shows conflict notification
7. User B clicks "Resolve Conflict"
8. Monaco Editor shows three-way diff
9. User B resolves conflict
10. User B saves resolution
11. System applies resolution and merges
12. System pushes to GitHub
13. System regenerates static files
14. User B sees published changes

### Workflow 3: Image Upload

1. User editing a page
2. User takes screenshot
3. User pastes into editor (Ctrl+V)
4. System detects clipboard image
5. System validates image (type, size)
6. System uploads to `/images/draft-123-a8f3c2/`
7. System commits image to draft branch
8. System inserts markdown: `![](images/draft-123-a8f3c2/screenshot.png)`
9. User continues editing
10. User publishes page
11. System merges both markdown and image
12. Image displays on published page

### Workflow 4: GitHub Sync

1. External user pushes to GitHub repo
2. GitHub sends webhook to wiki
3. Wiki rate-limits (checks last pull time)
4. Wiki pulls latest changes
5. Wiki detects changed files
6. Wiki regenerates static files
7. Wiki logs operation
8. Users see updated content on next page load

---

## Contact & Support

**Project Lead:** [To be assigned]  
**Development Team:** [To be assigned]  
**Documentation:** This document  
**Repository:** [To be created]  

---

*Document Version: 1.0*  
*Last Updated: October 25, 2025*  
*Status: Ready for Implementation*
