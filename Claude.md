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
- `repo-path-config` (settings.py:20) - Git repository location configuration
- `atomic-ops` (git_operations.py:12) - All operations must be atomic and rollback-safe
- `repo-singleton` (git_operations.py:43) - Single instance manages all git operations
- `dry-run-merge` (git_operations.py:271) - Uses --no-commit to test merge without modifying repo
- `binary-files` (git_operations.py:205) - is_binary flag for images/binary files already on disk
- `audit-trail` (git_service/models.py:80) - Complete history of all git operations for debugging
- `config-model` (git_service/models.py:14) - Provides get/set helpers for type-safe config access
- `session-tracking` (editor/models.py:13) - Maps users to their draft branches
- `editor-serializers` (editor/serializers.py:5) - Validation for all editor API endpoints
- `path-validation` (editor/serializers.py:16) - Prevent directory traversal attacks
- `editor-api` (editor/api.py:10) - REST API for markdown editing workflow
- `image-path-structure` (editor/api.py:539) - Images stored in images/{branch_name}/
- `editor-views` (editor/views.py:4) - UI views for markdown editing
- `editor-client` (edit.html:225) - SimpleMDE editor with auto-save and clipboard paste

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
- GITOPS-CONFLICT01
- GITOPS-PUBLISH01, GITOPS-PUBLISH02, GITOPS-PUBLISH03
- GITOPS-READ01, GITOPS-LIST01
- API-BRANCH01, API-BRANCH02
- API-COMMIT01, API-COMMIT02
- API-PUBLISH01, API-PUBLISH02, API-PUBLISH03
- API-FILE01, API-BRANCHES01

Editor Service:
- EDITSESS-INACTIVE01, EDITSESS-MULTI01
- EDITOR-START01, EDITOR-START02, EDITOR-START03
- EDITOR-SAVE01, EDITOR-SAVE02, EDITOR-SAVE03
- EDITOR-COMMIT01, EDITOR-COMMIT02, EDITOR-COMMIT03, EDITOR-COMMIT04
- EDITOR-PUBLISH01, EDITOR-PUBLISH02, EDITOR-PUBLISH03, EDITOR-PUBLISH04, EDITOR-PUBLISH05
- EDITOR-UPLOAD01, EDITOR-UPLOAD02, EDITOR-UPLOAD03
- EDITOR-VIEW01, EDITOR-VIEW02, EDITOR-VIEW03, EDITOR-VIEW04

Settings:
- SETTINGS-LOG01
