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
replace or regenerate its entry in the same change; never leave stale hashes or duplicate
rows behind (appending with `>>` without removing the old row leaves a stale entry that
fails `sha256sum -c` verification):

```bash
# from the repository root, replace an existing entry (do not append duplicate rows):
grep -v ' \./path/to/file$' MANIFEST.sha256 > MANIFEST.tmp && mv MANIFEST.tmp MANIFEST.sha256
sha256sum ./path/to/file >> MANIFEST.sha256

# for a newly added covered file, append its entry:
sha256sum ./path/to/new-file >> MANIFEST.sha256

# verify all entries pass:
sha256sum -c MANIFEST.sha256
```

A hash mismatch means the pinned baseline drifted; resolve it explicitly, do not ignore it.

### Manifest scope

The manifest is an **additional** gate, not a replacement for Git or CI. Git provides
content-addressed version history; CI validates selected executable invariants. Neither
makes the other unnecessary, and CI does not prove correctness — it proves the
properties it was written to check. The manifest pins the files whose **silent change
would be caught by neither**, because they are governance or evidence claims rather
than executable behaviour.

In scope (pinned):

- governance: `AGENTS.md`, `CONTRIBUTING.md`, `SECURITY.md`, `README.md`, `.gitignore`;
- architecture and research claims: `docs/**` (ADRs, roadmap, status, research);
- research POC baselines: `research/**`;
- CI definitions: `.github/**`;
- Python tooling contract: `pyproject.toml`.

Out of scope (deliberately not pinned):

- the Discovery Desk application (`src/**`) and its root-level tests (`tests/**`),
  covered by typecheck, lint, build and the migration-lifecycle job;
- `package*.json`, covered by `npm ci` and `npm audit`;
- generated artifacts and dependency lockfiles, which are governed by their native
  package and tooling workflows plus the CI checks that consume them. Note that
  `npm ci` installs *from* `package-lock.json`; it does not regenerate it, so the
  lockfile is a reviewed input rather than a derived output.

**Adding any new file within the declared in-scope perimeter (`docs/**`, `research/**`,
`.github/**`, or root governance/tooling files) requires adding its manifest entry in the
same change.** Because `sha256sum -c` only validates entries explicitly listed in the
manifest, omitting a new in-scope file would silently bypass the integrity gate.
PR #15 missed this for `docs/research/2026-08-28-mutagen-feasibility.md` while pinning
the ADR it was based on; this rule ensures all new covered files across any declared scope
are pinned at introduction.

Extending the perimeter — for example to migrations or other safety-critical SQL —
requires an explicit decision recorded in this section. Do not widen it file by file.

## Safety

No PR may introduce:

- arbitrary shell execution driven by model output;
- direct writes to a live game `Data/` directory;
- coordinate-based GUI automation as a critical path;
- bundled Bethesda binaries/assets;
- hidden automatic retries for potentially non-idempotent writes.
