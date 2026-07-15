### Actionable P0/P1 Findings
No actionable P0/P1 findings were identified in this review.

---

### Verification Summary
1. **SQLite Online Backup Restore and WAL Safety**: Verified. The backup and restore routines in [db/database.py](file:///db/database.py) and [routes/backups.py](file:///routes/backups.py) utilize the native `sqlite3` online backup API (`source_conn.backup(destination_conn)`). Overwriting the database file via the backup API handles WAL file invalidation safely and runs within an atomic transaction.
2. **Row Conversions**: Verified. Both assignment rows (via `[dict(row) for row in ...]` in [routes/today.py](file:///routes/today.py)) and card rows (via `dict(card_row)` in [routes/review.py](file:///routes/review.py) and [routes/today.py](file:///routes/today.py)) are converted to dictionaries before keys are accessed.
3. **No-PIN Recitation Flow**: Verified. When no PIN is configured, starting a recitation review successfully links to the parent PIN setup page while preserving the `next_path` redirect parameter. Saving the PIN unlocks the session, sets the session cookie, and returns the user to the review page with active parent supervision.
4. **Dynamic Form CSRF**: Verified. The event listener in [templates/base.html](file:///templates/base.html) correctly uses `form.getAttribute("method")` rather than the clobberable `form.method` property, and handles case insensitivity and missing attributes safely.

### Conclusion
**All earlier web P1 blockers are resolved.**
