# Security Guidelines for GitWiki

This document outlines security best practices for developing GitWiki. Follow these guidelines to prevent common vulnerabilities and maintain a secure codebase.

## Table of Contents

1. [XSS (Cross-Site Scripting) Prevention](#xss-prevention)
2. [Filename Sanitization](#filename-sanitization)
3. [Path Traversal Prevention](#path-traversal-prevention)
4. [File Upload Security](#file-upload-security)
5. [Authentication and Authorization](#authentication-and-authorization)
6. [Rate Limiting](#rate-limiting)
7. [Code Review Checklist](#code-review-checklist)

---

## XSS Prevention

### Overview

Cross-Site Scripting (XSS) occurs when untrusted user input is inserted into HTML without proper escaping, allowing attackers to inject malicious JavaScript.

### JavaScript: Use `escapeHtml()` Utility

**Location**: `static/js/utils.js`

**When to use**:
- Before inserting user input into HTML
- In `confirm()` or `alert()` dialogs with user data
- When building HTML strings with user content

**Example - Correct**:
```javascript
// Import is automatic - loaded in base.html
const userFileName = getUserInput(); // Could be malicious like: <script>alert('xss')</script>
const safe = escapeHtml(userFileName);
confirm(`Delete ${safe}?`); // Safe: Delete &lt;script&gt;alert('xss')&lt;/script&gt;?
```

**Example - Incorrect** (DO NOT DO THIS):
```javascript
const userFileName = getUserInput();
confirm(`Delete ${userFileName}?`); // DANGEROUS: Can execute arbitrary JavaScript
```

### Django Templates: Use `escapejs` Filter

**When to use**:
- When embedding user data in `<script>` blocks
- For string literals in JavaScript

**Example - Correct**:
```django
<script>
const fileName = '{{ file_name|escapejs }}';  // Server-side escaping
const safe = escapeHtml(fileName);             // Additional client-side escaping
</script>
```

### Prefer `textContent` Over `innerHTML`

**Correct**:
```javascript
element.textContent = userInput; // Always safe - treats as text
```

**Incorrect**:
```javascript
element.innerHTML = userInput; // DANGEROUS: Executes scripts
```

### Real Attack Examples Prevented

1. **Script injection**:
   - Input: `<script>alert('xss')</script>`
   - Escaped: `&lt;script&gt;alert('xss')&lt;/script&gt;`

2. **Event handler injection**:
   - Input: `'><img src=x onerror=alert(1)>`
   - Escaped: `&#x27;&gt;&lt;img src=x onerror=alert(1)&gt;`

3. **JavaScript string escape**:
   - Input: `"; alert(document.cookie); //`
   - Escaped: `&quot;; alert(document.cookie); //`

---

## Filename Sanitization

### Overview

User-provided filenames can contain dangerous characters or patterns that enable:
- Directory traversal (`../../etc/passwd`)
- Double-extension attacks (`malware.exe.txt`)
- Special character injection (`; rm -rf /`)

### Python: Use `filename_utils` Module

**Location**: `git_service/filename_utils.py`

**Required imports**:
```python
from git_service.filename_utils import sanitize_filename, get_safe_extension
```

**Example - Correct**:
```python
from datetime import datetime
import uuid

# User uploaded a file named: "../../malware.exe.txt"
user_filename = request.FILES['file'].name

# Sanitize base name (removes dots to prevent double-extension attacks)
base_name = sanitize_filename(user_filename, fallback='file')
# Result: "______malware_exe_txt"

# Extract safe extension
ext = get_safe_extension(user_filename)
# Result: "txt"

# Generate unique filename
timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
unique_id = str(uuid.uuid4())[:8]
safe_filename = f"{base_name}-{timestamp}-{unique_id}.{ext}"
# Result: "______malware_exe_txt-20250104-143000-abc123.txt"
```

**Example - Incorrect** (DO NOT DO THIS):
```python
# DANGEROUS: Allows double-extension and special characters
filename = request.FILES['file'].name
# If filename is "../../malware.exe.txt", this creates a security hole
```

### Dangerous Extensions Blacklist

**Location**: `git_service/filename_utils.py` (constant `DANGEROUS_EXTENSIONS`)

**Usage**:
```python
from git_service.filename_utils import DANGEROUS_EXTENSIONS, get_safe_extension

ext = get_safe_extension(filename)
if ext in DANGEROUS_EXTENSIONS:
    raise ValueError(f"Dangerous file type: {ext}")
```

**Blocked extensions** (30+ types):
- **Windows**: `exe`, `bat`, `cmd`, `com`, `pif`, `scr`, `vbs`, `msi`, `msp`, `gadget`, `scf`, `lnk`, `inf`, `reg`
- **Unix/Linux**: `sh`, `bash`, `csh`, `ksh`, `zsh`, `run`, `out`, `elf`, `bin`
- **macOS**: `app`, `dmg`, `pkg`
- **Package formats**: `deb`, `rpm`
- **Cross-platform**: `js`, `jar`

### Why Remove Dots from Base Names?

**Attack**: User uploads file named `malware.exe.txt`
- **Without dot removal**: System sees extension as `.txt` (safe)
- **Actual content**: Could be a Windows executable that runs when user downloads
- **Browser/OS**: May execute based on first extension (`.exe`)

**Solution**: Remove all dots from base name, only allow dots before the final extension.

---

## Path Traversal Prevention

### Overview

Path traversal attacks use special sequences like `../` to access files outside intended directories.

### Django Models/Serializers: Validate Paths

**Example - Correct**:
```python
def validate_file_path(self, value):
    """Prevent directory traversal attacks."""
    if '..' in value or value.startswith('/'):
        raise serializers.ValidationError(
            "Invalid path: no absolute paths or parent directory references allowed"
        )
    return value
```

### Backend: Use Path Operations Safely

**Example - Correct**:
```python
from pathlib import Path
from django.conf import settings

user_path = "../../etc/passwd"

# Build safe path
base_dir = settings.WIKI_REPO_PATH
safe_path = base_dir / user_path

# Verify path stays within base directory
if not str(safe_path.resolve()).startswith(str(base_dir.resolve())):
    raise SecurityError("Path traversal detected")
```

### Real Attack Examples Prevented

1. **Unix path traversal**: `../../etc/passwd`
2. **Windows path traversal**: `..\..\Windows\System32\config`
3. **Absolute paths**: `/etc/shadow`
4. **Mixed separators**: `../.\../etc/passwd`

---

## File Upload Security

### Complete Upload Workflow

```python
from git_service.filename_utils import (
    sanitize_filename,
    get_safe_extension,
    DANGEROUS_EXTENSIONS
)
from datetime import datetime
import uuid

def handle_file_upload(uploaded_file):
    # 1. Validate file size (in serializer)
    # Already handled by UploadFileSerializer with 100MB limit

    # 2. Sanitize filename
    base_name = sanitize_filename(uploaded_file.name, fallback='file')

    # 3. Extract and validate extension
    ext = get_safe_extension(uploaded_file.name)
    if ext and ext in DANGEROUS_EXTENSIONS:
        raise ValueError(f"File type '{ext}' not allowed")

    # 4. Generate unique filename
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    unique_id = str(uuid.uuid4())[:8]
    filename = f"{base_name}-{timestamp}-{unique_id}.{ext}" if ext else f"{base_name}-{timestamp}-{unique_id}"

    # 5. Validate target path (no traversal)
    target_path = validate_safe_path(target_directory)

    # 6. Construct final path
    file_path = target_path / filename

    # 7. Save file
    with open(file_path, 'wb') as f:
        for chunk in uploaded_file.chunks():
            f.write(chunk)

    return file_path
```

### File Size Limits

**Configuration** (`config/settings.py`):
```python
DATA_UPLOAD_MAX_MEMORY_SIZE = 104857600  # 100MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 104857600  # 100MB
```

**Validation** (in serializer):
```python
max_size = 100 * 1024 * 1024  # 100MB
if value.size > max_size:
    raise serializers.ValidationError(f"File too large. Maximum: 100MB")
```

---

## Authentication and Authorization

### Require Authentication for Destructive Operations

**Rule**: ALL destructive operations (create, update, delete, publish, upload) MUST use `IsAuthenticated` permission class.

**Example - Correct**:
```python
from rest_framework.permissions import IsAuthenticated

class DeleteFileAPIView(APIView):
    permission_classes = [IsAuthenticated]  # Enforces authentication

    def post(self, request):
        # User is guaranteed to be authenticated
        user = request.user
        # ... perform deletion
```

**Example - Incorrect** (DO NOT DO THIS):
```python
from rest_framework.permissions import IsAuthenticatedOrReadOnly

class DeleteFileAPIView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]  # WRONG for POST/DELETE
    # This allows unauthenticated POST requests in read-only mode!
```

**When to use `IsAuthenticated` vs `IsAuthenticatedOrReadOnly`**:
- `IsAuthenticated`: For ALL write operations (POST, PUT, PATCH, DELETE)
- `IsAuthenticatedOrReadOnly`: ONLY for read-only endpoints (GET, HEAD, OPTIONS)

**Fixed endpoints** (Issue #60):

Editor API (`editor/api.py`):
- `StartEditAPIView` - Start edit sessions
- `SaveDraftAPIView` - Save draft and update timestamp
- `CommitDraftAPIView` - Commit to draft branches
- `PublishEditAPIView` - Publish to main branch (CRITICAL)
- `UploadImageAPIView` - Upload images
- `UploadFileAPIView` - Upload files
- `QuickUploadFileAPIView` - Quick upload to main
- `DeleteFileAPIView` - Delete files
- `ResolveConflictAPIView` - Resolve merge conflicts
- `DiscardDraftAPIView` - Discard draft sessions

Git Service API (`git_service/api.py`):
- `CreateBranchAPIView` - Create draft branches
- `CommitChangesAPIView` - Commit changes to branches (CRITICAL)
- `PublishDraftAPIView` - Publish draft to main (CRITICAL)

### Never Trust User-Provided User IDs

**Example - Incorrect** (DO NOT DO THIS):
```python
# DANGEROUS: User can impersonate others
user_id = request.data.get('user_id')
user = User.objects.get(id=user_id)
```

**Example - Correct**:
```python
# Always use authenticated user from request
user = request.user
```

### User Attribution in Git Commits

**Rule**: Use the standardized `get_user_info_for_commit()` function for ALL git operations to ensure consistent user attribution.

**Helper Function** (`config/api_utils.py`):
```python
def get_user_info_for_commit(user):
    """
    Get standardized user info for git commits.

    This is the SINGLE source of truth for user attribution in git commits.
    All git operations should use this function to ensure consistent authorship.
    """
    return {
        'name': user.get_full_name() or user.username,
        'email': user.email or f'{user.username}@gitwiki.local'
    }
```

**Usage**: Pass any Django User instance to the function.

**Email Fallback Pattern**: Always provides `{username}@gitwiki.local` as fallback for users without configured email addresses.

**Example - Correct**:
```python
# Direct from request.user
repo.commit_changes(
    branch_name='main',
    file_path=file_path,
    content=content,
    commit_message=commit_message,
    user_info=get_user_info_for_commit(request.user),  # Simple and consistent
    user=request.user
)

# From EditSession
repo.commit_changes(
    branch_name=session.branch_name,
    file_path=session.file_path,
    content=content,
    commit_message=commit_message,
    user_info=get_user_info_for_commit(session.user),  # Same function!
    user=session.user
)
```

**Example - Incorrect** (DO NOT DO THIS):
```python
# Manual construction - inconsistent pattern
user_info = {
    'name': user.username,  # Missing get_full_name() fallback
    'email': user.email or 'unknown@example.com'  # Wrong domain
}
```

### Session-Based Operations Security (IDOR Prevention)

**CRITICAL**: Session-based operations use TWO layers of security to prevent Insecure Direct Object Reference (IDOR) attacks:
1. **Authentication requirement**: `IsAuthenticated` permission class
2. **Session ownership verification**: MUST filter by `user=request.user` in ALL session queries

**Why both layers are required**:
- Authentication prevents unauthenticated access
- User ownership filtering prevents authenticated users from accessing others' sessions (IDOR prevention)
- Even if session_id is leaked/guessed, attacker cannot access the session without being the owner

**Example - Correct** (IDOR-Safe):
```python
class CommitDraftAPIView(APIView):
    permission_classes = [IsAuthenticated]  # Layer 1: Require authentication

    def post(self, request):
        session_id = request.data.get('session_id')

        # Layer 2: MUST filter by user to prevent IDOR attacks
        session = EditSession.objects.get(
            id=session_id,
            is_active=True,
            user=request.user  # ← CRITICAL: Prevents cross-user session access
        )
        # If session belongs to different user, raises DoesNotExist (return 404)
```

**Example - Incorrect** (VULNERABLE TO IDOR):
```python
# DANGEROUS: Missing user ownership check
session = EditSession.objects.get(id=session_id, is_active=True)
# Attacker can access ANY session by guessing/leaking session_id
```

**Attack Scenarios Prevented**:
1. **IDOR Attacks**: User B cannot access/modify User A's session even with valid session_id
2. **Session ID Leakage**: Leaked session_id cannot be exploited by other authenticated users
3. **CSRF Attacks**: Combined with CSRF tokens and ownership checks
4. **Privilege Escalation**: Cannot impersonate users via session hijacking

**All Session-Based Endpoints MUST Include User Filter**:
- `SaveDraftAPIView` - Save draft content
- `CommitDraftAPIView` - Commit to branch
- `PublishEditAPIView` - Publish to main
- `UploadImageAPIView` - Upload images to session
- `UploadFileAPIView` - Upload files to session
- `ResolveConflictAPIView` - Resolve merge conflicts
- `DiscardDraftAPIView` - Discard draft session
- `ConflictVersionsAPIView` - Get conflict versions

**Testing IDOR Prevention**:
See `editor/tests.py::SessionOwnershipSecurityTest` for comprehensive IDOR attack simulation tests.

**Best Practices**:
- Never accept `user_id` in request data for authenticated operations
- Always use `request.user` for user attribution
- **CRITICAL**: Always filter EditSession queries by `user=request.user` to prevent IDOR
- Return 404 (not 403) when session doesn't belong to user (prevents session enumeration)
- Sessions automatically track which user created them via `EditSession.user`
- Log user ID and username for audit trails
- Use `get_user_info_for_commit()` helper for consistent git attribution

---

## Rate Limiting

### Purpose

Prevent abuse by limiting the number of requests per user/IP within a time window.

### Usage

**Location**: `config/rate_limit.py`

**Example**:
```python
from config.rate_limit import rate_limit

class DeleteFileAPIView(APIView):
    @rate_limit(max_requests=10, window_seconds=60)
    def post(self, request):
        # Max 10 deletes per minute per user/IP
        # ...
```

### Recommended Limits

- **Destructive operations** (delete): 10 requests/minute
- **File uploads**: 5 requests/minute
- **Read operations**: 60 requests/minute (if needed)

### Response on Rate Limit Exceeded

```json
{
  "success": false,
  "error": {
    "message": "Rate limit exceeded. Maximum 10 requests per 60 seconds.",
    "code": "RATE_LIMIT_EXCEEDED",
    "retry_after": 45
  }
}
```

**Headers**:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Requests remaining in window
- `X-RateLimit-Reset`: Unix timestamp when limit resets

---

## Code Review Checklist

Use this checklist when reviewing pull requests:

### XSS Prevention
- [ ] User input in JavaScript uses `escapeHtml()` from utils.js
- [ ] User input in Django templates uses appropriate filters (`escapejs`, `escape`)
- [ ] Prefer `textContent` over `innerHTML` when displaying user data
- [ ] Confirm dialogs with user data are properly escaped

### Filename Security
- [ ] Filenames are sanitized using `sanitize_filename()` from filename_utils
- [ ] Extensions are validated against `DANGEROUS_EXTENSIONS`
- [ ] Dots are removed from base filenames (prevents double-extension attacks)
- [ ] File paths are validated for traversal attempts

### Path Security
- [ ] No user input in file paths without validation
- [ ] Path traversal patterns (`..`, absolute paths) are blocked
- [ ] Paths are resolved and checked to stay within base directory

### File Uploads
- [ ] File size limits are enforced (100MB max)
- [ ] Dangerous file extensions are blocked
- [ ] Filenames are sanitized before storage
- [ ] Uploaded files are stored in controlled locations

### Authentication
- [ ] ALL destructive API endpoints use `IsAuthenticated` permission class
- [ ] No `user_id` accepted in request data for authenticated operations
- [ ] User identity comes from `request.user`, not request data
- [ ] User attribution uses standardized helper function `get_user_info_for_commit(user)`
- [ ] Permissions are checked before sensitive operations
- [ ] Session-based operations verified to be tied to authenticated user
- [ ] Audit logging includes user ID and username for destructive operations

### Rate Limiting
- [ ] Destructive endpoints have rate limiting
- [ ] Upload endpoints have rate limiting
- [ ] Limits are appropriate for the operation type

### General Security
- [ ] No secrets (keys, passwords) in code or templates
- [ ] Error messages don't leak sensitive information
- [ ] Logging doesn't include PII or sensitive data
- [ ] All database queries use parameterized queries (ORM does this)

---

## Reporting Security Issues

If you discover a security vulnerability in GitWiki:

1. **DO NOT** open a public GitHub issue
2. Email the maintainer directly with:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if available)

---

## Additional Resources

- **OWASP Top 10**: https://owasp.org/www-project-top-ten/
- **Django Security**: https://docs.djangoproject.com/en/4.2/topics/security/
- **CSP (Content Security Policy)**: https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP

---

**Last Updated**: January 2025
**Version**: 1.0.0
