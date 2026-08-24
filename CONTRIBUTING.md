# Contributing

This repository is pre-alpha research. Contributions should make uncertainty smaller, not merely add features.

## Workflow

1. Create a focused branch.
2. Keep one architectural or experimental concern per PR.
3. Add or update tests for behavioral changes.
4. Record evidence and limitations explicitly.
5. Prefer a draft PR while a proof is still `CHANGES_REQUIRED`.

## Pull-request requirements

A PR should state:

- scope;
- files changed;
- commands executed;
- raw test result;
- new/changed evidence level;
- security or data-integrity impact;
- licensing impact;
- remaining risks;
- exact next unit of work.

Do not report a test count manually: copy it from the actual runner output.

## Integrity manifest

`MANIFEST.sha256` pins SHA-256 hashes for the governance, architecture/research, and POC-002
baseline files listed inside it (paths relative to the repository root, `./`-prefixed,
`sha256sum` text format). If an intentionally changed file is covered by the manifest,
regenerate the affected entries in the same change; never leave stale hashes behind:

```bash
# from the repository root, for each covered file:
sha256sum ./path/to/file >> MANIFEST.sha256
```

A hash mismatch means the pinned baseline drifted; resolve it explicitly, do not ignore it.

## Safety

No PR may introduce:

- arbitrary shell execution driven by model output;
- direct writes to a live game `Data/` directory;
- coordinate-based GUI automation as a critical path;
- bundled Bethesda binaries/assets;
- hidden automatic retries for potentially non-idempotent writes.
