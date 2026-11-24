# Safe Git Rollback Guide

- Always inspect `git log -n 5` and `git show <commit_hash>` before reverting.
- Prefer `git revert <commit_hash>` over `git reset --hard` on shared branches.
- Include root cause, affected orders, and rollback verification steps in the post-mortem.
