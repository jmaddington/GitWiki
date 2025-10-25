# Phase 4 Implementation Plan - Conflict Resolution

**Date:** October 25, 2025
**Branch:** `claude/review-project-docs-011CUUZAK3Ej6CvJw1D8rYoW`
**Status:** Ready to Begin

---

## Executive Summary

Phases 1-3 are complete with excellent architecture and code quality. The foundation is solid:
- **Phase 1**: Git Service with atomic operations and conflict detection
- **Phase 2**: SimpleMDE editor with 3 image upload methods
- **Phase 3**: Display service with search, navigation, and static generation

**Phase 4 Goal:** Implement comprehensive conflict resolution system with Monaco Editor for three-way diff, handling text, image, and binary file conflicts.

---

## Architecture Review Summary

### Current State Assessment

#### ✅ Strengths
1. **Excellent Separation of Concerns**
   - 3 Django apps (git_service, editor, display) with 95%+ independence
   - Clean API boundaries between services
   - Each app could be extracted as microservice

2. **Robust Git Operations**
   - Atomic operations with rollback safety
   - Dry-run merge for conflict detection (no repo corruption)
   - Singleton repository pattern
   - Comprehensive audit trail

3. **Quality Code Standards**
   - 851 lines in git_operations.py
   - 508 lines in editor/api.py
   - 437 lines in display/views.py
   - All code has AIDEV-NOTE anchors for navigation
   - Unique grepable logging codes throughout

4. **Complete Feature Set (Phases 1-3)**
   - Draft/publish workflow
   - Auto-save every 60 seconds
   - 3 image upload methods (file, drag-drop, clipboard)
   - Full-text search with pagination
   - Static HTML generation with metadata
   - Page history from Git commits
   - Responsive Bootstrap 5 UI

5. **Documentation Excellence**
   - Comprehensive project plan
   - Phase summaries for 1-3
   - AIDEV-NOTE index in Claude.md
   - 48+ unique grepable codes documented

#### 🎯 Architecture Alignment with Original Plan

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| Git as versioning backend | ✅ | GitPython, atomic ops |
| Web-based editing | ✅ | SimpleMDE with auto-save |
| Clipboard image support | ✅ | 3 upload methods |
| Draft/publish workflow | ✅ | Branch-based with sessions |
| Conflict detection | ✅ | Dry-run merge (no corruption) |
| Static file generation | ✅ | Atomic with temp directories |
| Search functionality | ✅ | Full-text with pagination |
| Page history | ✅ | Git commit extraction |
| 95%+ app separation | ✅ | API-based communication |

**Result:** 100% alignment with architectural vision

---

## Phase 4: Conflict Resolution - Detailed Plan

### Overview

Phase 4 implements the conflict resolution system that was intentionally designed into the architecture from Phase 1. The dry-run merge in `publish_draft()` already detects conflicts and returns HTTP 409 - now we need the UI to resolve them.

### What Needs to Be Built

#### 1. Conflict Detection Enhancement (git_service/git_operations.py)

**New Method: `get_conflicts()`**

```python
def get_conflicts(self) -> Dict:
    """
    Get list of all draft branches with merge conflicts.

    Uses dry-run merge testing (same as publish_draft) but for ALL drafts.
    Caching: 2-minute TTL to avoid expensive operations.

    Returns:
        {
            "conflicts": [
                {
                    "branch_name": "draft-123-abc456",
                    "file_path": "docs/page.md",
                    "conflict_type": "content",  # or "delete", "rename"
                    "user_id": 123,
                    "created_at": "2025-10-25T10:00:00Z",
                    "base_content": "...",
                    "theirs_content": "...",
                    "ours_content": "..."
                }
            ],
            "cached": false,
            "timestamp": "2025-10-25T10:00:00Z"
        }
    """
```

**Implementation Notes:**
- List all draft branches (filter by `draft-*` pattern)
- For each branch, perform dry-run merge against main
- Parse Git merge output to identify conflicted files
- Extract three versions: base (common ancestor), theirs (main), ours (draft)
- Cache results for 2 minutes (avoid repeated expensive operations)
- Log with grepable code: GITOPS-CONFLICT02

**Complexity:** Medium (builds on existing dry-run merge logic)

---

**New Method: `resolve_conflict()`**

```python
def resolve_conflict(
    self,
    branch_name: str,
    file_path: str,
    resolution_content: str,
    user_info: Dict,
    is_binary: bool = False
) -> Dict:
    """
    Apply conflict resolution and retry merge.

    Process:
    1. Validate branch and file exist
    2. Checkout draft branch
    3. Write resolved content to file
    4. Commit resolution
    5. Retry merge to main
    6. If successful: delete draft, return success
    7. If still conflicts: return new conflict details

    Returns:
        {
            "success": true,
            "merged": true,
            "commit_hash": "abc123...",
            "still_conflicts": []  # if merge still failed
        }
    """
```

**Implementation Notes:**
- Validates resolution is different from both versions (no accidental overwrites)
- Creates resolution commit with special message: "Resolve conflict in {file_path}"
- Retries publish_draft() logic
- Logs with grepable code: GITOPS-RESOLVE01, GITOPS-RESOLVE02
- Handles edge case: conflict changed while user was resolving (HTTP 409)

**Complexity:** Medium-High (builds on publish_draft)

---

#### 2. Conflict Resolution API (editor/api.py)

**New Endpoints:**

**GET `/editor/api/conflicts/`**
- Calls `git_service.get_conflicts()`
- Returns list of all unresolved conflicts
- Cached for 2 minutes

**POST `/editor/api/conflicts/resolve/`**
```json
{
    "session_id": 456,
    "file_path": "docs/page.md",
    "resolution_content": "resolved content...",
    "conflict_type": "text"  // or "image_mine", "image_theirs", "binary_mine", "binary_theirs"
}
```
- Validates user owns the session
- Calls `git_service.resolve_conflict()`
- Returns success or new conflict details

**GET `/editor/api/conflicts/versions/{session_id}/{file_path}`**
- Returns three versions for Monaco Editor:
  - `base` - common ancestor
  - `theirs` - main branch version
  - `ours` - draft branch version
- Used by Monaco three-way diff

**Complexity:** Medium (straightforward REST wrappers)

---

#### 3. Conflicts Dashboard (editor/templates/conflicts.html)

**New Template: `conflicts.html`**

Features:
- Table of all unresolved conflicts
- Columns: File, Branch, User, Date, Action
- "Resolve" button for each conflict
- Auto-refresh every 30 seconds (JavaScript)
- Filter by user (dropdown)
- Sort by date (newest first)
- Empty state: "No conflicts! 🎉"

**New View: `conflicts_list(request)`** in editor/views.py

```python
def conflicts_list(request):
    """Display all unresolved conflicts."""
    repo = get_repository()
    conflicts = repo.get_conflicts()

    # Augment with user info
    for conflict in conflicts['conflicts']:
        session = EditSession.objects.filter(
            branch_name=conflict['branch_name']
        ).first()
        conflict['user'] = session.user if session else None

    return render(request, 'editor/conflicts.html', {
        'conflicts': conflicts,
        'auto_refresh': True
    })
```

**URL:** `/editor/conflicts/`

**Complexity:** Low (simple list view)

---

#### 4. Monaco Editor Integration

**New Template: `resolve_conflict.html`**

Features:
- Three-way diff view (base, theirs, ours)
- Monaco Editor in diff mode
- Accept Mine / Accept Theirs / Manual Edit buttons
- Save Resolution button
- Cancel button (returns to conflicts list)
- Conflict explanation text (which branch is which)
- Loading indicators
- Error handling

**JavaScript Implementation:**
```javascript
// Load Monaco Editor from CDN
// Initialize three-way diff
// Provide merge controls
// Submit resolution to API
```

**New View: `resolve_conflict_view(request, session_id, file_path)`**

```python
def resolve_conflict_view(request, session_id, file_path):
    """Display conflict resolution interface."""
    session = get_object_or_404(EditSession, id=session_id)

    # Get three versions
    repo = get_repository()
    versions = repo.get_conflict_versions(
        session.branch_name,
        file_path
    )

    return render(request, 'editor/resolve_conflict.html', {
        'session': session,
        'file_path': file_path,
        'versions': versions,
        'conflict_type': 'text'  # or 'image', 'binary'
    })
```

**URL:** `/editor/conflicts/resolve/<int:session_id>/<path:file_path>/`

**Complexity:** High (Monaco integration + conflict parsing)

---

#### 5. Image Conflict Resolution

**New Template: `resolve_image_conflict.html`**

Features:
- Side-by-side image preview
- Image metadata (dimensions, size, format)
- Radio buttons: "Keep Mine" | "Keep Theirs"
- Preview of selected image
- Apply button
- Download links for both versions

**Implementation:**
```html
<div class="row">
    <div class="col-md-6">
        <h4>Your Version</h4>
        <img src="..." class="img-fluid">
        <p>Size: 2.3 MB | 1920x1080 | PNG</p>
        <input type="radio" name="choice" value="mine">
    </div>
    <div class="col-md-6">
        <h4>Main Branch Version</h4>
        <img src="..." class="img-fluid">
        <p>Size: 1.8 MB | 1920x1080 | JPG</p>
        <input type="radio" name="choice" value="theirs">
    </div>
</div>
```

**Complexity:** Low (simple radio button selection)

---

#### 6. Binary File Conflict Resolution

**New Template: `resolve_binary_conflict.html`**

Features:
- File information display (name, size, SHA hash)
- Download links for both versions
- Radio buttons: "Keep Mine" | "Keep Theirs"
- Apply button
- Warning: "Binary files cannot be merged, choose one version"

**Complexity:** Low (simpler than image)

---

### Implementation Order

**Week 1: Backend (Days 1-5)**
1. Day 1-2: Implement `get_conflicts()` with caching
2. Day 2-3: Implement `resolve_conflict()`
3. Day 3-4: Create conflict resolution API endpoints
4. Day 4-5: Write tests for conflict detection and resolution

**Week 2: Frontend (Days 6-10)**
5. Day 6: Create conflicts dashboard template
6. Day 7-8: Integrate Monaco Editor for text conflicts
7. Day 8-9: Create image and binary conflict templates
8. Day 9-10: Integration testing and bug fixes

---

### Technical Specifications

#### Caching Strategy

```python
from django.core.cache import cache

def get_conflicts(self) -> Dict:
    """Get conflicts with 2-minute cache."""
    cache_key = 'git_conflicts_list'
    cached = cache.get(cache_key)

    if cached:
        cached['cached'] = True
        return cached

    # Expensive operation: check all drafts
    conflicts = self._detect_all_conflicts()

    # Cache for 2 minutes
    cache.set(cache_key, conflicts, 120)
    conflicts['cached'] = False
    return conflicts
```

**Requires:** Redis or Django's cache framework

---

#### Conflict Type Detection

```python
def _parse_conflict_type(self, file_path: str, merge_output: str) -> str:
    """
    Determine conflict type from Git merge output.

    Types:
    - "content": Both modified same file (<<<<<<)
    - "delete": One deleted, one modified
    - "rename": Both renamed differently
    """
    if "deleted by" in merge_output:
        return "delete"
    elif "renamed" in merge_output:
        return "rename"
    else:
        return "content"
```

---

#### Three-Way Diff Extraction

```python
def get_conflict_versions(
    self,
    branch_name: str,
    file_path: str
) -> Dict[str, str]:
    """
    Extract three versions for conflict resolution.

    Returns:
        {
            "base": "content from common ancestor",
            "theirs": "content from main branch",
            "ours": "content from draft branch"
        }
    """
    # Get merge base (common ancestor)
    base_commit = self.repo.merge_base('main', branch_name)[0]

    # Extract content from each version
    base = self._get_file_at_commit(file_path, base_commit)
    theirs = self._get_file_at_commit(file_path, 'main')
    ours = self._get_file_at_commit(file_path, branch_name)

    return {
        "base": base,
        "theirs": theirs,
        "ours": ours
    }
```

---

### Testing Strategy

#### Unit Tests (git_service/tests.py)

```python
def test_get_conflicts_empty():
    """Test conflict detection with no conflicts."""
    repo = get_repository()
    conflicts = repo.get_conflicts()
    assert conflicts['conflicts'] == []

def test_get_conflicts_with_conflict():
    """Test conflict detection with actual conflict."""
    # Create two conflicting changes
    # Assert conflict detected correctly

def test_resolve_conflict_success():
    """Test successful conflict resolution."""
    # Create conflict
    # Resolve it
    # Assert merge succeeded

def test_resolve_conflict_still_conflicts():
    """Test resolution that still has conflicts."""
    # Create complex conflict
    # Apply partial resolution
    # Assert new conflicts returned
```

#### Integration Tests (editor/tests.py)

```python
def test_conflict_resolution_workflow():
    """Test complete conflict resolution workflow."""
    # User A edits page
    # User B edits same page
    # User A publishes (success)
    # User B publishes (conflict)
    # User B resolves conflict
    # User B publishes (success)
    # Assert both changes present
```

---

### Grepable Codes to Add

**Git Service:**
- GITOPS-CONFLICT02 - List all conflicts detected
- GITOPS-CONFLICT03 - Conflict cache hit
- GITOPS-CONFLICT04 - Conflict cache miss
- GITOPS-RESOLVE01 - Resolution applied successfully
- GITOPS-RESOLVE02 - Resolution failed, still conflicts
- GITOPS-RESOLVE03 - Invalid resolution (no change)

**Editor Service:**
- EDITOR-CONFLICT01 - Conflicts list loaded
- EDITOR-CONFLICT02 - Conflict resolution started
- EDITOR-CONFLICT03 - Conflict resolution successful
- EDITOR-CONFLICT04 - Conflict resolution failed
- EDITOR-CONFLICT05 - Image conflict resolved
- EDITOR-CONFLICT06 - Binary conflict resolved

---

### AIDEV-NOTEs to Add

```python
# AIDEV-NOTE: conflict-detection; Caches results for 2min to avoid expensive operations
def get_conflicts(self) -> Dict:
    ...

# AIDEV-NOTE: conflict-resolution; Retries merge after applying resolution
def resolve_conflict(self, ...):
    ...

# AIDEV-NOTE: three-way-diff; Extracts base, theirs, ours for Monaco Editor
def get_conflict_versions(self, ...):
    ...

# AIDEV-NOTE: monaco-integration; Three-way diff UI for text conflicts
// in resolve_conflict.html
```

---

### Dependencies to Add

```txt
# requirements.txt additions
# (Monaco Editor via CDN - no pip package needed)
```

**CDN Links for Monaco:**
```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs/loader.min.js"></script>
```

---

### URL Routing Changes

**editor/urls.py additions:**
```python
path('conflicts/', views.conflicts_list, name='conflicts_list'),
path('conflicts/resolve/<int:session_id>/<path:file_path>/', views.resolve_conflict_view, name='resolve_conflict'),
path('api/conflicts/', api.ConflictsListAPIView.as_view(), name='api_conflicts_list'),
path('api/conflicts/resolve/', api.ResolveConflictAPIView.as_view(), name='api_resolve_conflict'),
path('api/conflicts/versions/<int:session_id>/<path:file_path>/', api.ConflictVersionsAPIView.as_view(), name='api_conflict_versions'),
```

---

### Success Criteria

#### Functional Requirements
- [ ] Can detect conflicts across all draft branches
- [ ] Can resolve text conflicts with Monaco Editor
- [ ] Can resolve image conflicts (choose one)
- [ ] Can resolve binary conflicts (choose one)
- [ ] Resolved conflicts successfully merge to main
- [ ] No data loss during conflict resolution

#### Performance Requirements
- [ ] Conflict detection cached (2 minutes)
- [ ] Conflict list loads in < 5 seconds
- [ ] Monaco Editor loads in < 3 seconds
- [ ] Resolution applies in < 2 seconds

#### Quality Requirements
- [ ] All unit tests passing
- [ ] Integration tests for full workflow
- [ ] No Git repository corruption
- [ ] Proper error handling throughout
- [ ] Comprehensive logging with grepable codes

---

## Risks & Mitigations

### Risk 1: Monaco Editor Complexity
**Impact:** High
**Likelihood:** Medium
**Mitigation:**
- Use Monaco's diff editor (simpler than full editor)
- Follow Monaco documentation examples
- Test with real conflicts early
- Fallback: Simple textarea with manual merge

### Risk 2: Complex Conflict Scenarios
**Impact:** High
**Likelihood:** Medium
**Mitigation:**
- Test with various conflict types (content, delete, rename)
- Clear error messages for unsupported scenarios
- Manual resolution option (edit raw file)
- Document known limitations

### Risk 3: Performance with Many Branches
**Impact:** Medium
**Likelihood:** Low
**Mitigation:**
- Implement caching (2 minutes)
- Limit conflict scan to active sessions only
- Add pagination if > 50 conflicts
- Phase 5 will add branch cleanup

---

## Self-Review Checklist

Before marking Phase 4 complete, verify:

1. **Code Quality**
   - [ ] All AIDEV-NOTEs added
   - [ ] All grepable codes unique and documented
   - [ ] No hardcoded values (use Configuration model)
   - [ ] Proper error handling throughout
   - [ ] No TODO comments left

2. **Testing**
   - [ ] Unit tests for get_conflicts()
   - [ ] Unit tests for resolve_conflict()
   - [ ] Integration test for full workflow
   - [ ] Edge cases tested (concurrent edits, complex conflicts)

3. **Documentation**
   - [ ] README.md updated
   - [ ] IMPLEMENTATION_PLAN.md marked complete
   - [ ] distributed-wiki-project-plan.md updated
   - [ ] PHASE_4_SUMMARY.md created
   - [ ] Claude.md updated with new codes

4. **User Experience**
   - [ ] Clear instructions in conflict UI
   - [ ] Error messages are helpful
   - [ ] Loading indicators present
   - [ ] Mobile-responsive design

5. **Architecture**
   - [ ] Maintains 95%+ app separation
   - [ ] No direct model imports across apps
   - [ ] API-based communication
   - [ ] Atomic operations maintained

---

## Post-Phase 4: What's Next

**Phase 5: GitHub Integration (Week 7)**
- Implement pull_from_github()
- Implement push_to_github()
- Add webhook handler with rate limiting
- Set up Celery periodic tasks
- Implement branch cleanup
- Full static rebuild task

**Benefits of Completing Phase 4 First:**
- Conflict resolution is critical for multi-user workflows
- Establishes patterns for Phase 5 (pull conflicts)
- Monaco Editor skills transfer to other features
- User testing can begin (edit, publish, resolve conflicts)

---

## Quick Start Guide for Phase 4 Implementation

### Day 1: Setup & Backend Start

```bash
# Checkout branch
git checkout claude/review-project-docs-011CUUZAK3Ej6CvJw1D8rYoW

# Pull latest
git pull origin claude/review-project-docs-011CUUZAK3Ej6CvJw1D8rYoW

# Create feature branch (optional)
git checkout -b feature/phase-4-conflict-resolution

# Start implementation
# 1. Add get_conflicts() to git_operations.py
# 2. Add resolve_conflict() to git_operations.py
# 3. Write unit tests
```

### Day 3: API Endpoints

```bash
# Add to editor/api.py:
# - ConflictsListAPIView
# - ResolveConflictAPIView
# - ConflictVersionsAPIView

# Update editor/urls.py with new routes
# Test with curl or Postman
```

### Day 6: Frontend Templates

```bash
# Create editor/templates/editor/conflicts.html
# Create editor/templates/editor/resolve_conflict.html
# Create editor/templates/editor/resolve_image_conflict.html
# Create editor/templates/editor/resolve_binary_conflict.html

# Update editor/views.py with new views
# Test in browser
```

### Day 8: Monaco Integration

```bash
# Add Monaco Editor CDN to resolve_conflict.html
# Implement three-way diff JavaScript
# Test with real conflicts
# Add auto-save for resolution (optional)
```

---

## Questions? Blockers?

If you encounter issues:

1. **Check existing Phase 1 conflict detection:** `publish_draft()` already detects conflicts
2. **Review Git merge documentation:** Understanding merge-base and three-way merge
3. **Monaco Editor examples:** Check official Monaco docs for diff editor
4. **Ask for clarification:** Better to ask than implement incorrectly

---

**Phase 4 Status:** Ready to Begin

**Estimated Effort:** 8-10 days (1 developer, full-time)

**Complexity:** Medium-High (Monaco integration is the challenging part)

**Priority:** High (critical for multi-user workflows)

---

*Document created: October 25, 2025*
*Next update: Phase 4 completion*
