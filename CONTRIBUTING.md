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

`MANIFEST.sha256` pins SHA-256 hashes for the governance, architecture/research, and POC
baseline files listed inside it (paths relative to the repository root, `./`-prefixed,
`sha256sum` text format). Two commands cover the whole workflow:

```bash
# verify: coverage of the declared perimeter + hashes of every row
python3 tools/check_manifest_coverage.py --check
sha256sum -c MANIFEST.sha256

# after any intentional change inside the perimeter, re-pin in one step
python3 tools/check_manifest_coverage.py --update
```

`--update` refreshes hashes for files already pinned, appends missing in-scope paths, and
drops rows whose file is gone or outside the perimeter; existing row order is preserved so
the diff stays reviewable. It re-runs `--check` afterwards, so a successful update is
self-verifying. Prefer it over hand-editing: appending with `>>` without removing the old
row leaves a stale entry, and a hand-edit can silently omit a file.

A hash mismatch means the pinned baseline drifted; resolve it explicitly, do not ignore it.

### Why a coverage gate exists

`sha256sum -c` only validates rows that are already in the manifest, so an in-scope file
that was **never added** produces no error at all — it simply is not pinned. That is the
PR #15 failure mode (`docs/research/2026-08-28-mutagen-feasibility.md` was unpinned while
the ADR citing it was pinned). `tools/check_manifest_coverage.py` makes it a build failure
by enumerating the perimeter from git and diffing it against the manifest rows; it also
rejects duplicate rows, malformed rows, stale rows, out-of-perimeter rows, and hash
mismatches. CI runs it in `.github/workflows/governance.yml`.

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
- integrity/quality gates themselves: `tools/**`;
- Python tooling contract: `pyproject.toml`.
- distribution notices: `public/licenses/**`, including font license texts and source records.

Out of scope (deliberately not pinned):

- the Discovery Desk application (`src/**`) and its root-level tests (`tests/**`),
  covered by typecheck, lint, build, the migration-lifecycle job and the
  desk/docs consistency job;
- `package*.json`, covered by `npm ci` and `npm audit`;
- generated artifacts and dependency lockfiles, which are governed by their native
  package and tooling workflows plus the CI checks that consume them. Note that
  `npm ci` installs *from* `package-lock.json`; it does not regenerate it, so the
  lockfile is a reviewed input rather than a derived output.

**Adding any new file within the declared in-scope perimeter (`docs/**`, `research/**`,
`public/licenses/**`, `.github/**`, `tools/**`, or explicit root-pinned files: `AGENTS.md`,
`CONTRIBUTING.md`, `SECURITY.md`, `README.md`, `.gitignore`, `pyproject.toml`) requires
pinning it in the same change** — run `python3 tools/check_manifest_coverage.py --update`.
Because `sha256sum -c` only validates entries explicitly listed in the manifest, omitting a
new in-scope file would silently bypass the integrity gate. PR #15 missed this for
`docs/research/2026-08-28-mutagen-feasibility.md` while pinning the ADR it was based on;
the coverage gate now makes that omission a CI failure instead of a rule to remember.

Extending the perimeter — for example to migrations or other safety-critical SQL —
requires an explicit decision recorded in this section. Do not widen it file by file.

The 2026-09-06 licensing review explicitly adds `public/licenses/**` to the perimeter:
silent changes to distributed legal notices are not covered by application typechecking.

The 2026-09-24 review explicitly adds `tools/**` to the perimeter. Rationale: `tools/`
holds the gates that enforce the claims above (`check_manifest_coverage.py`,
`quality_ratchet.py`, `quality-baseline.txt`); a gate outside the pin perimeter could be
weakened, or its debt ledger relaxed, with no pinned-baseline change to review.

## Quality gates

`.github/workflows/governance.yml` runs two gates that no other workflow covers:

1. **Manifest coverage** — `python3 tools/check_manifest_coverage.py --check`, then
   `sha256sum -c MANIFEST.sha256`.
2. **Static analysis ratchet** — `python3 tools/quality_ratchet.py --check`, running
   `ruff` (`E4,E7,E9,F,B`) and `mypy` over `research/**` and `tools/**` and comparing the
   result against the debt ledger `tools/quality-baseline.txt`.

The gate is a **ratchet, not a sweep**. Existing findings are recorded debt, so pinned
research baselines are never churned for cosmetic reasons; any finding *beyond* the ledger
fails CI. Shrinking the ledger is welcome (`--update` banks the improvement). Editing the
ledger upward is allowed only as an explicit, separately justified change — and because
`tools/**` is inside the pin perimeter, it cannot be done quietly. Rules are deliberately
bug-shaped; `ruff format` is not gated at all. A missing analyzer is a hard error (exit 2),
never a silent pass.

Two platform facts the gates assume, so nobody reads them as defects:

- the POC-003 hermetic suite imports `ctypes.WinDLL` at module scope, so on Linux/macOS
  `test_probe.py`, `test_proctree.py` and `test_runner.py` fail to *import*. CI runs that
  suite on `windows-latest` only; a non-Windows run of the full directory is not evidence
  about POC-003 in either direction.
- the ratchet runs on Linux only, because on Windows `ctypes.WinDLL` resolves and mypy
  legitimately reports fewer errors than the ledger; comparing those numbers across
  platforms would compare different measurements.

`src/**` and `tests/**` are covered by the Discovery Desk workflow (typecheck, lint, build,
migration lifecycle, desk/docs consistency). The POC suites are covered by their own
workflows.

## Third-party material

For new or updated dependencies, refresh `docs/research/npm-license-inventory.md` from
the committed lockfile and review changed licenses. Preserve actual upstream license
and NOTICE files in shipped artifacts; the inventory does not replace them.
Keep `public/licenses/` in deployments, including standalone packaging that copies
Next.js public assets separately. Recheck font source records when changing fonts.

For imported or AI-generated material, record the generator if known, supplied source
material, copied/adapted portions, and the evidence of permission. Never infer ownership
or third-party clearance from a prompt, generated answer, ZIP hash, or MIT header.
Current unresolved imports are recorded in `docs/research/source-manifest.md`.

## Safety

No PR may introduce:

- arbitrary shell execution driven by model output;
- direct writes to a live game `Data/` directory;
- coordinate-based GUI automation as a critical path;
- bundled Bethesda binaries/assets;
- hidden automatic retries for potentially non-idempotent writes.
