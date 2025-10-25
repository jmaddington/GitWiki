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

## Other

Do not use emoji's in logger statements.

All logging statements should have a UNIQUE grepable code at the end of them, like: logger.error('demo error [IZNPOP]') it can be explanatory like: logger.error('demo error [DEMO-FUNC12]') AS long as it is unique and allows sys admins to grep for it after seeing it in the logs.
