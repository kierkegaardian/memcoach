# Repo Agent Notes

<!-- GOVERNANCE_BASELINE_START -->
## Governance Baseline (Canonical)
- Project ID (portable): `memcoach`
- Path (current environment): `/home/user/projects/memcoach`
- Canonical origin (current): `git@github-memcoach:kierkegaardian/memcoach.git`
- Default branch (current): `main`
- Stack / language (canonical): Python FastAPI + Jinja/HTMX application.
- File-size rule (enforced target): keep new files and heavily modified files (`>100` non-comment LOC changed or `>25%` of file touched) at `<= 300` LOC where practical; split into modules when larger. Exceptions are allowed for generated files, lockfiles, or legacy files when splitting would reduce clarity.
- Heavily-modified response (enforced): if modular splitting clearly improves maintainability, propose a split plan first; otherwise pause for user acknowledgement before committing any file that would exceed `400` LOC, and record the exception rationale in the handoff.
- Typesafety rule (enforced): apply stack-appropriate strict typing in every change (strict TypeScript for TS, Python type hints + pyright/mypy where configured, ShellCheck/input validation for shell, explicit declarations for Fortran/C# where applicable).
- Remote/push rule (enforced): do not change remotes or push destinations without explicit user confirmation; treat `origin` as canonical by default. This applies to human-in-the-loop agent actions and does not override already-approved CI automation.
<!-- GOVERNANCE_BASELINE_END -->

## Precedence
- Follow `/home/user/AGENTS.md` for workspace-wide rules and credential handling.

## Repo Summary
- Project ID (portable): `memcoach`
- Path (current environment): `/home/user/projects/memcoach`
- Stack: FastAPI + Jinja + HTMX; SQLite at `~/.memcoach/memcoach.db`.
- Entry point: `main.py`.

## Common Commands (from README.md)
- Install dependencies: `pip install -r requirements.txt`.
- Run API/UI: `uvicorn main:app --reload --port 8000`.

## Notes
- Config file: `~/.memcoach/config.toml`.
- Uses local Ollama for grading; see README for model choices.
- UI/API runs on `http://127.0.0.1:8000`.

## Quality
- **Typesafety (Request):** Enforce robust, stack-appropriate typesafety in all changes (Python type hints + pyright/mypy when applicable).
