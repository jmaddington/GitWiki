# Commenting Guidelines

Use AIDEV-NOTE:, AIDEV-TODO:, or AIDEV-QUESTION: (all-caps prefix) for comments aimed at AI and developers.

Keep them concise (≤ 120 chars).

Important: Before scanning files, always first try to locate existing anchors AIDEV-* in relevant subdirectories.

Update relevant anchors when modifying associated code.

Do not remove AIDEV-NOTEs without explicit human instruction.

Make sure to add relevant anchor comments, whenever a file or piece of code is:

- too long, or
- too complex, or
- very important, or
- confusing, or
- could have a bug unrelated to the task you are currently working on.

Example:

```python
# AIDEV-NOTE: perf-hot-path; avoid extra allocations (see ADR-24)
async def render_feed(...):
    ...
```

## Commit discipline

Granular commits: One logical change per commit. Tag AI-generated commits: e.g., feat: optimise feed query [AI]. Clear commit messages: Explain the why; link to issues/ADRs if architectural. Use git worktree for parallel/long-running AI branches (e.g., git worktree add ../wip-foo -b wip-foo). Review AI-generated code: Never merge code you don't understand.

## Git Service Implementation Notes

### Repository Management

The git_service/git_operations.py module uses a singleton pattern via get_repository(). All Git operations go through the GitRepository class to ensure consistency.

Key AIDEV-NOTEs in codebase:

Configuration:
- `security-config` (settings.py:32) - Load SECRET_KEY and config from environment
- `repo-path-config` (settings.py:24) - Git repository location configuration
- `production-config` (settings_production.py:17) - Production-specific security settings
- `production-logging` (settings_production.py:62) - Centralized logging for production
- `api-utils` (config/api_utils.py:6) - Standardized error handling for all API endpoints

Git Service:
- `atomic-ops` (git_operations.py:12) - All operations must be atomic and rollback-safe
- `repo-singleton` (git_operations.py:43) - Single instance manages all git operations
- `dry-run-merge` (git_operations.py:271) - Uses --no-commit to test merge without modifying repo
- `binary-files` (git_operations.py:205) - is_binary flag for images/binary files already on disk
- `file-history` (git_operations.py:543) - Used for page history display
- `markdown-conversion` (git_operations.py:674) - Uses markdown library with extensions for tables, code, TOC
- `static-generation` (git_operations.py:709) - Atomic operation using temp directory
- `conflict-detection` (git_operations.py:840) - Caches results for 2min to avoid expensive operations
- `three-way-diff` (git_operations.py:931) - Extracts base, theirs, ours for Monaco Editor
- `conflict-resolution` (git_operations.py:1004) - Retries merge after applying resolution
- `github-pull` (git_operations.py:1137) - Handles conflicts during pull gracefully
- `github-push` (git_operations.py:1324) - Only pushes if local is ahead
- `branch-cleanup` (git_operations.py:1508) - Only removes inactive sessions
- `static-rebuild` (git_operations.py:1636) - Atomic operation, old files kept until complete
- `ssh-test` (utils.py:19) - Tests SSH authentication without modifying repository
- `webhook-handler` (views.py:34) - Rate-limited to 1 pull/minute
- `celery-config` (settings.py:201) - Background task configuration for GitHub sync
- `cache-config` (settings.py:214) - Redis cache for rate limiting and conflict caching
- `audit-trail` (git_service/models.py:80) - Complete history of all git operations for debugging
- `config-model` (git_service/models.py:14) - Provides get/set helpers for type-safe config access

Editor Service:
- `session-tracking` (editor/models.py:13) - Maps users to their draft branches
- `editor-serializers` (editor/serializers.py:5) - Validation for all editor API endpoints
- `path-validation` (editor/serializers.py:16) - Prevent directory traversal attacks
- `editor-api` (editor/api.py:10) - REST API for markdown editing workflow
- `image-path-structure` (editor/api.py:539) - Images stored in images/{branch_name}/
- `editor-views` (editor/views.py:4) - UI views for markdown editing
- `editor-client` (edit.html:225) - SimpleMDE editor with auto-save and clipboard paste

Display Service:
- `display-views` (display/views.py:6) - Wiki page rendering and search functionality
- `display-urls` (display/urls.py:6) - Wiki page URLs and search routing
- `error-handlers` (display/views.py:441) - Custom error pages (404, 500, 403)

URL Configuration:
- `error-handlers` (config/urls.py:35) - Error handler configuration for production

### Testing

All git operations have GPG signing disabled via repository config to avoid signing issues in test environments.

Tests use temporary directories that are cleaned up after each test.

## Other

Do not use emoji's in logger statements.

All logging statements should have a UNIQUE grepable code at the end of them, like: logger.error('demo error [IZNPOP]') it can be explanatory like: logger.error('demo error [DEMO-FUNC12]') AS long as it is unique and allows sys admins to grep for it after seeing it in the logs.

### Existing Grepable Codes

Git Service:
- CONFIG-GET01, CONFIG-SET01, CONFIG-SET02, CONFIG-INIT01
- GITOP-LOG01, GITOP-LOG02
- GITREPO-INIT01, GITREPO-INIT02, GITREPO-INIT03, GITREPO-LOAD01, GITREPO-MAIN01
- GITOPS-BRANCH01, GITOPS-BRANCH02
- GITOPS-COMMIT01, GITOPS-COMMIT02
- GITOPS-CONFLICT01, GITOPS-CONFLICT02, GITOPS-CONFLICT03, GITOPS-CONFLICT04, GITOPS-CONFLICT05, GITOPS-CONFLICT06, GITOPS-CONFLICT07, GITOPS-CONFLICT08, GITOPS-CONFLICT09
- GITOPS-RESOLVE01, GITOPS-RESOLVE02, GITOPS-RESOLVE03, GITOPS-RESOLVE04, GITOPS-RESOLVE05
- GITOPS-PUBLISH01, GITOPS-PUBLISH02, GITOPS-PUBLISH03, GITOPS-PUBLISH04, GITOPS-PUBLISH05
- GITOPS-READ01, GITOPS-LIST01
- GITOPS-HISTORY01, GITOPS-HISTORY02
- GITOPS-META01
- GITOPS-MARKDOWN01
- GITOPS-STATIC01, GITOPS-STATIC02, GITOPS-STATIC03
- GITOPS-PULL01, GITOPS-PULL02, GITOPS-PULL03, GITOPS-PULL04, GITOPS-PULL05, GITOPS-PULL06, GITOPS-PULL07, GITOPS-PULL08, GITOPS-PULL09, GITOPS-PULL10
- GITOPS-PUSH01, GITOPS-PUSH02, GITOPS-PUSH03, GITOPS-PUSH04, GITOPS-PUSH05, GITOPS-PUSH06, GITOPS-PUSH07, GITOPS-PUSH08, GITOPS-PUSH09, GITOPS-PUSH10, GITOPS-PUSH11
- GITOPS-CLEANUP01, GITOPS-CLEANUP02, GITOPS-CLEANUP03, GITOPS-CLEANUP04, GITOPS-CLEANUP05, GITOPS-CLEANUP06, GITOPS-CLEANUP07, GITOPS-CLEANUP08
- GITOPS-REBUILD01, GITOPS-REBUILD02, GITOPS-REBUILD03, GITOPS-REBUILD04, GITOPS-REBUILD05, GITOPS-REBUILD06, GITOPS-REBUILD07, GITOPS-REBUILD08, GITOPS-REBUILD09
- API-BRANCH01, API-BRANCH02, API-BRANCH-VAL01
- API-COMMIT01, API-COMMIT02, API-COMMIT-VAL01
- API-PUBLISH01, API-PUBLISH02, API-PUBLISH03, API-PUBLISH-VAL01, API-PUBLISH-CONFLICT
- API-FILE01, API-FILE02, API-FILE-VAL01, API-FILE-NOTFOUND
- API-BRANCHES01
- UTILS-SSH01, UTILS-SSH02, UTILS-SSH03, UTILS-SSH04, UTILS-SSH05, UTILS-SSH06, UTILS-SSH07
- WEBHOOK-01, WEBHOOK-02, WEBHOOK-03, WEBHOOK-04, WEBHOOK-05, WEBHOOK-06, WEBHOOK-07
- SYNC-01, SYNC-02, SYNC-03, SYNC-04, SYNC-05, SYNC-06, SYNC-07, SYNC-08, SYNC-09
- SETTINGS-01, SETTINGS-02, SETTINGS-03
- TASK-PULL01, TASK-PULL02, TASK-PULL03, TASK-PULL04, TASK-PULL05
- TASK-CLEANUP01, TASK-CLEANUP02, TASK-CLEANUP03, TASK-CLEANUP04
- TASK-REBUILD01, TASK-REBUILD02, TASK-REBUILD03, TASK-REBUILD04
- TASK-TEST01

Editor Service:
- EDITSESS-INACTIVE01, EDITSESS-MULTI01
- EDITOR-START01, EDITOR-START02, EDITOR-START03
- EDITOR-SAVE01, EDITOR-SAVE02, EDITOR-SAVE03
- EDITOR-COMMIT01, EDITOR-COMMIT02, EDITOR-COMMIT03, EDITOR-COMMIT04
- EDITOR-PUBLISH01, EDITOR-PUBLISH02, EDITOR-PUBLISH03, EDITOR-PUBLISH04, EDITOR-PUBLISH05
- EDITOR-UPLOAD01, EDITOR-UPLOAD02, EDITOR-UPLOAD03
- EDITOR-VIEW01, EDITOR-VIEW02, EDITOR-VIEW03, EDITOR-VIEW04, EDITOR-VIEW05, EDITOR-VIEW06, EDITOR-VIEW07, EDITOR-VIEW08, EDITOR-VIEW09
- EDITOR-CONFLICT01, EDITOR-CONFLICT02, EDITOR-CONFLICT03, EDITOR-CONFLICT04, EDITOR-CONFLICT05, EDITOR-CONFLICT06, EDITOR-CONFLICT07, EDITOR-CONFLICT08, EDITOR-CONFLICT09

Display Service:
- DISPLAY-META01
- DISPLAY-DIR01
- DISPLAY-HOME01, DISPLAY-HOME02, DISPLAY-HOME03
- DISPLAY-PAGE01, DISPLAY-PAGE02, DISPLAY-PAGE03, DISPLAY-PAGE04
- DISPLAY-SEARCH01, DISPLAY-SEARCH02, DISPLAY-SEARCH03
- DISPLAY-HISTORY01, DISPLAY-HISTORY02

Security (Phase 7):
- SECURITY-01: DEBUG mode enabled (development only)
- SECURITY-02: Production mode enabled with DEBUG=False
- SECURITY-03: Using default SECRET_KEY (must change for production)
- SECURITY-04: Production settings loaded
- SECURITY-05: HTTPS redirect enabled
- SECURITY-06: HSTS enabled
- SECURITY-07: Using PostgreSQL database
- SECURITY-08: Using SQLite (PostgreSQL recommended for production)
- SECURITY-09: Created logs directory
- SECURITY-10: Email configuration loaded
- SECURITY-11: Email not configured (console backend)
- SECURITY-12: Sentry error tracking enabled
- SECURITY-13: Redis cache configured
- SECURITY-14: ALLOWED_HOSTS not configured
- SECURITY-15: ALLOWED_HOSTS configured successfully
- SECURITY-16: Production settings loaded successfully

Error Handlers (Phase 7):
- ERROR-404: Page not found (404 error)
- ERROR-500: Server error (500 error)
- ERROR-403: Permission denied (403 error)

Settings:
- SETTINGS-LOG01
