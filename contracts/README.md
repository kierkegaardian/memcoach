# MemCoach shared contracts

This directory is the cross-runtime source of truth for deterministic behavior
and the core-only portable library format. The web may optionally ask Ollama to
refine a deterministic `good` grade; that web-only result is not part of grading
parity.

## Deterministic grading and scheduling

- Grades are exactly `fail`, `good`, and `perfect`, mapped to SM-2 qualities
  `0`, `3`, and `4`.
- Recall text is trimmed and lowercased before normalized indel similarity is
  calculated. A substitution costs two; insertion and deletion cost one.
- Ratios at least `0.980000` are `perfect`; ratios at least `0.850000` are
  `good`; lower ratios and blank attempts are `fail`.
- Ease values in fixtures and portable packages use fixed six-decimal strings.
- Both engines clamp incoming intervals to at least one day and ease factors to
  at least `1.300000` before scheduling; portable parsers still reject values
  outside those bounds.
- The TSV files under `fixtures/` are consumed directly by Python and Kotlin
  tests. Any rule change requires a contract-version change and matching fixture
  updates in both runtimes.

## Portable library v1

`memcoach-backup-v1.schema.json` defines the core allow-list. Parsers must also
enforce the cross-object rules JSON Schema cannot express:

- every UUID is unique within its entity array;
- every reference resolves to the same package;
- counts exactly match array lengths;
- arrays are sorted by `portable_id`;
- an `extensions` member is rejected by the Android v1 preview as unsupported;
- a unique-name collision between different UUIDs hard-fails preview;
- no PIN, config, session, signing, corpus, or other machine-private material is
  accepted into the core graph.

Canonical digest input is the document with the top-level `integrity` member
removed. Recursively normalize strings to NFC, sort object keys, preserve array
order, and encode compact UTF-8 JSON with no trailing newline. Entity arrays are
sorted by portable ID before canonicalization. The SHA-256 is lowercase hex.

`valid/memcoach-backup-v1.json` is the readable golden document. The exact
digest input is the single JSON line in
`canonical/memcoach-backup-v1.payload.json`; its POSIX file newline is not part
of the canonical bytes. `invalid/invalid-cases-v1.json` defines deterministic
mutations against the golden document for parser rejection tests.
