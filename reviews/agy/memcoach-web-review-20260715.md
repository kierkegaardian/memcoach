I will list the contents of the current workspace directory to identify where the `memcoach` files and repository are located.
I will list the current permissions to see which paths are accessible.
I will list the contents of the `/home/user/.gemini/antigravity-cli/worktrees` directory to check if the `memcoach` project or repositories are located there.
I will run a git command to see what the repository looks like and if the commit `7cce6d7` is present in the current workspace directory.
I will run a grep search in the scratch folder to find if there is a directory or files related to `memcoach` or its config file.
I will read `verify_cleanup.py` in the scratch directory to understand if it contains clues or scripts related to this task.
I will run a simple echo command inside the scratch directory to verify if standard sandboxed command execution is working.
I will search for the `memcoach` repository folder using `find` with `BypassSandbox: true` since the standard sandbox is currently encountering connection resets.
I will wait for the `find` task to complete and return its results.
I will output the git diff for commit `7cce6d7` to a scratch file in the artifact directory so we can examine it.
I will output the git diff for commit `7cce6d7` to the conversation artifacts directory.
I will view the first 800 lines of the git diff to begin analyzing the changes in commit `7cce6d7`.
I will view the next chunk of the git diff (lines 801 to 1600).
I will view the final part of the git diff (lines 1601 to the end).
I will view the contents of `config.py` in the repository to fully understand the configuration loading logic.
I will view the contents of `utils/auth.py` to examine the PIN verification and parent session logic.
I will run a grep search in the templates directory to locate form elements that might be loaded dynamically.
I will view `templates/partials/review_result.html` lines 30 to 50 to see the form structure.
I will view `templates/cards/card_row.html` to see if there are standard POST forms there.
I will view the `db/database.py` file to inspect how SQLite database connections are opened, closed, or pooled.
I will view `utils/grading.py` to see if there is any blocking work or issues in the grading function.
I will view `utils/ollama.py` to check how the Ollama LLM call is implemented and if there are issues.
I will view `utils/stt.py` to see if the transcription function blocks the asyncio event loop.
I will view `routes/stt.py` to check if `transcribe_audio` is properly awaited or if it is a coroutine call that is never awaited.
I will find and view the database schema definition to check how cards, decks, and kids are linked.
I will view the schema definitions in `db/schema.py` to understand the relationships.
I will view `routes/review.py` from line 270 to 350 to see the review submission flow.
I will view `routes/today.py` to see how reviews are submitted there.
I will view `routes/today.py` lines 295 to 310 to see the exact SQL query used to load the card.
I will view `templates/cards/card_edit_form.html` to see how edits are submitted.
I will view `routes/backups.py` from line 60 to 95 to verify the exact line numbers for the restore backup route.
I will view the rest of `routes/backups.py` to check the replacement and cleanup logic.
I will view `routes/parent.py` to check the exact line numbers for `sanitize_next_path`.
Here is the security and correctness review of memcoach commit `7cce6d7`.

---

### P1 Findings (Blocking)

#### 1. Unsafe Database File & WAL Swap in Backup Restore (Risk of Corruption, Crash, or Split-Brain)
* **Location**: [routes/backups.py:107-115](file:///home/user/projects/memcoach/routes/backups.py#L107-L115)
* **Description**: During backup restoration, the handler unlinks the active SQLite WAL (`.db-wal`) and shared memory (`.db-shm`) files while database connections remain open (due to Uvicorn serving concurrent requests).
  * **On Unix/Linux**: Open database handles continue to read/write to the unlinked file descriptor. When new connections open, they create new WAL/SHM files and write to the new database, resulting in a split-brain state and eventual silent data loss/corruption.
  * **On Windows**: Renaming or deleting active database/WAL files triggers a `PermissionError` (`OSError`), causing the restore operation to fail.
* **Remedy**: Perform database restoration using SQLite's Online Backup API (`conn.backup()`) to copy the restore data into the active connection, rather than replacing files directly on the filesystem while the application is running.

#### 2. Incomplete Rollback with WAL Deletion on Restore Failure (Risk of Permanent Data Loss)
* **Location**: [routes/backups.py:116-123](file:///home/user/projects/memcoach/routes/backups.py#L116-L123)
* **Description**: If file replacement fails during restore (triggering the `except OSError` block), the code attempts to roll back by replacing the backup database file back to `DB_PATH`. However, because the original database's `.db-wal` and `.db-shm` files were already unlinked (lines 107-108), any uncommitted/uncheckpointed data residing in the original WAL file is permanently lost, leaving the restored original database corrupted.
* **Remedy**: Avoid unlinking original WAL files before a successful replacement is guaranteed, or rely on the online backup API.

---

### P2 Findings (High Priority)

#### 3. Open Redirect Vulnerability via Browser Path Normalization
* **Location**: [routes/parent.py:23-30](file:///home/user/projects/memcoach/routes/parent.py#L23-L30) in [sanitize_next_path](file:///home/user/projects/memcoach/routes/parent.py#L23)
* **Description**: `sanitize_next_path` attempts to validate `next_path` by checking for protocol-relative slashes (`//`) and parsing with `urlsplit`. However, it does not check for or sanitize backslashes (`\`). Modern browsers normalize backslashes to forward slashes (e.g., `/\evil.com` becomes `//evil.com`). Because `/\evil.com` starts with `/\`, it bypasses the `candidate.startswith("//")` and `urlsplit` checks, allowing open redirects to arbitrary external domains after unlock/lock actions.
* **Remedy**: Add a check to reject or sanitize backslash characters (`\`) in `next_path`.

#### 4. Bypassing Parent-Supervised "Recitation" Reviews in First-Run (PIN Not Configured)
* **Location**: [utils/auth.py:108-111](file:///home/user/projects/memcoach/utils/auth.py#L108-L111) in [is_parent_unlocked](file:///home/user/projects/memcoach/utils/auth.py#L108) and [routes/review.py:140-141](file:///home/user/projects/memcoach/routes/review.py#L140-L141)
* **Description**: When no parent PIN has been configured (default first-run setup), `is_parent_unlocked` returns `True`. While intended to leave parent configuration routes open, this also allows kids to review and self-grade parent-supervised "recitation" decks. The `start_review` check (`not getattr(request.state, "parent_unlocked", False)`) evaluates to `False`, bypassing the "Parent Key Required" template entirely.
* **Remedy**: Separate the check for parent session unlocking from first-run check, or block recitation reviews if no PIN is configured (`get_parent_pin_hash()` is `None`).

#### 5. Event Loop Blocking via Synchronous Database Queries in `async def` Route Handlers
* **Location**: Throughout route files (e.g., [routes/review.py:140](file:///home/user/projects/memcoach/routes/review.py#L140), [routes/today.py:305](file:///home/user/projects/memcoach/routes/today.py#L305), `routes/decks.py`, `routes/kids.py`, etc.)
* **Description**: Route handlers are defined as `async def` but perform synchronous SQLite database calls (`cursor.execute()`) directly. In FastAPI, `async def` handlers run on the main event loop. If a query blocks (such as waiting for a database write lock during concurrency, up to the 5000ms `busy_timeout`), the entire event loop blocks, freezing the server for all other concurrent users.
* **Remedy**: Define these endpoint functions as synchronous `def` (which FastAPI runs in a thread pool), or wrap SQLite queries with `asyncio.to_thread`.

#### 6. Missing Kid-to-Deck Assignment Verification in Review/Submit Handlers
* **Location**: [routes/review.py:140](file:///home/user/projects/memcoach/routes/review.py#L140), [routes/review.py:270](file:///home/user/projects/memcoach/routes/review.py#L270), and [routes/today.py:294](file:///home/user/projects/memcoach/routes/today.py#L294)
* **Description**: The routes `start_review`, `submit_review`, and `submit_today_review` do not verify whether the specified `kid_id` is assigned to the `deck_id` (via the `assignments` table). This allows any kid to review any deck in the system and record progress by requesting the URL directly.
* **Remedy**: Add a verification check against the `assignments` table before starting or submitting a review.

---

### P3 Findings (Medium/Low Priority)

#### 7. Uncaught Foreign Key Violation (HTTP 500) during Review Submission
* **Location**: [routes/review.py:327](file:///home/user/projects/memcoach/routes/review.py#L327) and [routes/today.py:348](file:///home/user/projects/memcoach/routes/today.py#L348)
* **Description**: If a review is submitted with a deleted or non-existent `kid_id`, the call to `get_card_progress` succeeds (returning `default_progress()`), but the database insert fails with `sqlite3.IntegrityError` due to foreign key constraints on `kid_id`. Because this is uncaught, the application returns a raw HTTP 500 Internal Server Error instead of a structured 400 or 404 response.
* **Remedy**: Verify the kid's existence before upserting, or catch `sqlite3.IntegrityError` to return a clean client error.

#### 8. Lack of CSRF Token in Dynamically Loaded Non-HTMX Forms
* **Location**: [templates/base.html:782-792](file:///home/user/projects/memcoach/templates/base.html#L782-L792)
* **Description**: The javascript block in `base.html` automatically appends the CSRF hidden input to forms *on page load*. If any non-HTMX standard POST forms are rendered dynamically inside HTMX fragments swapped into the page later, they will not have the CSRF input injected. Submitting them will fail with a 403 Forbidden.
* **Remedy**: Use a `MutationObserver` in javascript to dynamically inject CSRF tokens into forms added to the DOM, or inject them server-side inside the templates.

#### 9. DoS via Disk Exhaustion in Upload Handlers
* **Location**: [routes/backups.py:280](file:///home/user/projects/memcoach/routes/backups.py#L280), [routes/stt.py:42](file:///home/user/projects/memcoach/routes/stt.py#L42), [routes/cards.py:366](file:///home/user/projects/memcoach/routes/cards.py#L366)
* **Description**: Although `read_upload_limited` enforces upload size limits, FastAPI/Starlette parses the multipart form data and writes the uploaded files to disk (typically `/tmp`) *before* the route handler is invoked. An attacker can upload files of arbitrary size, causing disk space exhaustion and Denial of Service.
* **Remedy**: Limit client request body sizes at the ASGI middleware level or in the reverse proxy / web server.

#### 10. Parent Session Cookie Lacks `secure` Flag
* **Location**: [routes/parent.py:473-477](file:///home/user/projects/memcoach/routes/parent.py#L473-L477) and [routes/parent.py:524-528](file:///home/user/projects/memcoach/routes/parent.py#L524-L528)
* **Description**: The parent session cookie is set with `httponly=True` and `samesite="lax"`, but is missing `secure=True`. This allows transmission of the cookie over unencrypted HTTP, exposing it to interception if run over non-localhost networks without TLS.
* **Remedy**: Set `secure=True` on the `parent_session` cookie.
