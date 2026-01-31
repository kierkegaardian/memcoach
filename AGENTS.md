# Repo Agent Notes

## Precedence
- Follow `/home/user/AGENTS.md` for workspace-wide rules and credential handling.

## Repo Summary
- Path: `/home/user/projects/memcoach`.
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
