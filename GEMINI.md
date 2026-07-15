# Gemini Agent Notes

<!-- MANAGED: sync_agent_docs.py -->
This file is intentionally short to avoid drift.

Repo-specific rules live in `AGENTS.md` in this repository.
Workspace-level rules are loaded from `/home/user/AGENTS.md` when that path exists in this environment.
If the workspace file is unavailable, use only this repo's `AGENTS.md`.
If local `AGENTS.md` resolves to the same file as `/home/user/AGENTS.md`, do not load the global file again.
Load depth rule: do not follow pointer chains beyond this repo's `AGENTS.md` plus the optional `/home/user/AGENTS.md` once.
Fallback baseline if AGENTS files are missing or unreadable: keep changes minimal, never bypass safety/sandbox constraints, ask before remote/push changes, and report the missing policy file.
Fast path: for trivial, self-contained requests that do not touch files, secrets, infrastructure, active project state, or prior context, answer directly and skip continuity-ledger reads/updates, broad repo scans, discovery docs, and second-agent review.
## Gemini Role
- Act as a strict second-opinion reviewer / sanity-checker.
- Findings first; treat P0/P1 findings as blocking unless explicitly waived.

## Guardrails
- Follow review trigger/output rules from this repo's `AGENTS.md` and the workspace file when available.
- Keep recommendations consistent with this repo's canonical origin/stack/typesafety constraints in `AGENTS.md`.
- If `homeops-gemini-review` reports `Failure type: auth`, inspect the sibling stderr log; on this workstation the wrapper already attempted one local browser-auth recovery pass before failing.
- Do not use bypass flags or dangerous sandbox bypass options unless the user explicitly requests it.
