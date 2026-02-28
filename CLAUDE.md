# Claude Agent Notes

<!-- MANAGED: sync_agent_docs.py -->
This file is intentionally short to avoid drift.

Repo-specific rules live in `AGENTS.md` in this repository.
Workspace-level rules are loaded from `/home/user/AGENTS.md` when that path exists in this environment.
If the workspace file is unavailable, use only this repo's `AGENTS.md`.
If local `AGENTS.md` resolves to the same file as `/home/user/AGENTS.md`, do not load the global file again.
Load depth rule: do not follow pointer chains beyond this repo's `AGENTS.md` plus the optional `/home/user/AGENTS.md` once.
Fallback baseline if AGENTS files are missing or unreadable: keep changes minimal, never bypass safety/sandbox constraints, ask before remote/push changes, and report the missing policy file.
No additional Claude-specific policy is defined here.
