# Agent Instructions (GEMINI.md)

## Global Engineering Rules
- Build modular first: no code file longer than 300 lines.
- If a task needs more code, split into multiple files/modules/functions.
- Think ahead: keep entrypoints stable and isolate logic likely to change.
- Do not add default fallbacks during development; let failures surface so they can be fixed.
- Do not leave empty try/catch blocks.
- Prefer existing open-source, self-hosted libraries; ask the user to confirm selections.
- Design UI for end users, not for the schema.

## Testing & Quality
- **Typesafety:** Use robust typesafety (TypeScript, Zod, etc.) in all applications to facilitate ease of testing and maintenance.
- **Sync:** Ensure `AGENTS.md` and `GEMINI.md` remain in sync. When modifying one, modify the other.

## Delegating to Codex
To assign coding tasks or reviews to the `codex` agent with full permissions (bypassing approvals):
- Use `codex exec "YOUR_PROMPT" -a never`
- **Warning:** This bypasses safety checks. Use only when confident in the prompt's scope.
- Example: `codex exec "Review backend/src/auth.ts for security flaws" -a never`
- **Reviews:** When asking Codex for a code review, instruct it to save the output to `reviews/codex/latest.md` (create the directory if needed).
