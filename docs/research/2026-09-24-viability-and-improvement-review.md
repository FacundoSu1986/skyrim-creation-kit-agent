# Viability and improvement review — 2026-09-24

**PHASE:** Gate-1 follow-up review of the repository state (not a new experiment).
**STATUS of this document:** analysis of `VERIFICADO` in-repo evidence plus `NO VERIFICADO`
external claims, each labeled. Nothing here raises or lowers any experiment status.
**Does not authorize implementation.**

## 1. Question asked

"Is this agent viable, and what should be improved?" Two separate answers follow: (1) the
viability of the product the research points at, and (2) the state of the repository as
engineering. They diverge, and conflating them is how research projects become indefinite.

## 2. What is actually true today

```text
Product implemented:   nothing user-facing. There is no planner, no ModPlan executor,
                       no writer, no CLI, no package, no release.
Validated primitives:  POC-002 (synthetic TES4 inspect + safety pipeline) PASS;
                       POC-IPC-001 (isolated worker IPC contract) PASS.
Executed, not passed:  POC-003 (PapyrusCompiler dry-invoke) NO VERIFICADO, 13/15
                       mandatory criteria, criteria 12 and 14 FAIL.
Not started:           POC-001 (CK UIA inspect), POC-004 (xEdit validator),
                       POC-MUTAGEN-001 (BLOQUEADO by ADR-003).
```

The "agent" is therefore currently a **safety and evidence harness with two verified
read-only primitives**. That is an honest position and it is also the reason the word
"viable" needs to be split into three different questions.

## 3. Viability, split by claim

| # | Claim | Verdict | Basis |
| --- | --- | --- | --- |
| V1 | "An agent that drives Creation Kit" | **not viable as designed** | `VERIFICADO` (Gate 1): no supported CK authoring API; UIA untested and POC-001 `BLOQUEADO`; CKPE `LEGAL_REVIEW_REQUIRED`. Coordinate automation is excluded by policy, and correctly so. |
| V2 | "A general headless mod-authoring agent (records, quests, scripts)" | **technically viable, commercially weak** | The backends exist (Mutagen, xEdit, official compiler) and the repo's own `existing-projects.md` records that the target product "already exists in substantial form". See §4. |
| V3 | "A license-clean, evidence-first verification/gate layer for Skyrim artifacts" | **viable, and the differentiated niche** | The only findings in this repository that no competitor is documented to have are the negative results: non-reproducible `.pex` output, undeclared `.pas` residue, host identity embedded in compiled artifacts, vacuous-success detection (`exit 0` + no artifact). These are properties of the *toolchain*, not of a missing feature. |

`VIABLE WITH LIMITATIONS` remains the correct overall verdict, but the limiting factor has
changed since Gate 1: it is no longer "can we do it safely", it is **"is what we can do safely
worth doing here, given what already ships"**.

## 4. External landscape at review date

Sources are listed in §9. Everything in this section is `NO VERIFICADO` here: nothing was
installed, run, or benchmarked; these are readings of public descriptions.

- **houseCARL** (GPL-3.0, C#/.NET, MCP). Described as covering the whole load-order data layer:
  record read/author, dialogue and quest authoring with the CK bookkeeping steps included,
  BSA/texture paths, MO2 profile reads, and Papyrus decompile with a claimed ~98.8% byte-exact
  recompile rate. Its activity window (mid/late 2026) is *after* this repository's Gate 1.
- **Skyrim Forge** (Python, MCP + CLI + GUI). Described as already shipping the "safety fabric"
  this repository was designed around: typed JSON jobs, workspace snapshots, allowlisted hashed
  xEdit scripts, stale-PEX rejection, audit trails, deterministic release building, narrow
  transactional record creation. Standalone repo reported frozen at 5.2.1 (2026-08) with work
  moved into a bundle.
- **SkyrimCK-MCP** (MIT, C#, esper+balsa): QUST/VMAD/aliases without opening CK.

Consequences for this project:

1. **The safety fabric is prior art, not a moat.** `existing-projects.md` already concluded
   this ("do not claim novelty for receipts and hashes"); the 2026-09 check strengthens it.
2. **Competing on capability means chasing a GPL C# stack that is further along** — and ADR-003
   currently forbids the dependency that would make that possible. That combination (must use
   the best backend + cannot use the best backend) is the structural deadlock of V2.
3. **The genuinely unowned ground is verification, generation is taken.** Auditing an artifact
   that another tool produced (or that a user produced in CK) needs no Mutagen, no CK, no xEdit
   binary in-process, keeps the license surface clean, and is exactly what POC-002 and
   POC-IPC-001 already implement.

## 5. Technical risks that decide the outcome

| Risk | Status today | Why it gates the product |
| --- | --- | --- |
| Byte-reproducible compile output | measured FAIL (POC-003 criterion 14) | No content-addressable artifact store, no "same input ⇒ same bytes" caching, no trustworthy rebuild. `DETERMINISTIC_OUTPUT`: `NO VERIFICADO`. |
| Undeclared intermediate artifacts | measured FAIL (criterion 12) | Any claim of "workspace contains exactly the declared outputs" is false for interrupted runs until the profile declares them or cleanup is enforced. |
| Host identity in compiled artifacts | measured (every produced `.pex`) | A public release pipeline would leak usernames/machine names unless a redaction gate exists. Nobody in the surveyed landscape documents such a gate. |
| Real-plugin parsing compatibility | `NO VERIFICADO` | POC-002 proves the *pipeline*, not the format: `Skyrim.esm`/ESL-flags/1.71 headers/large subrecords are untested. |
| Runtime semantic correctness (VMAD, SEQ, FaceGen, aliases) | out of reach here | Requires CK and in-game validation; the highest-value claims a mod author cares about are the ones this environment can never make. |
| OS-level confinement | `NO VERIFICADO` | Workers are trusted code with host privileges; a product exposed to third-party plans needs more than a typed protocol. |
| Windows dependency of all decisive experiments | `BLOQUEADO` off-Windows | Every remaining question (POC-001, POC-004, ADR-003) needs a real Windows host with legally installed tools. |

## 6. Recommendation

**Reposition the product target from authoring to verification-and-release gating, and stop
before the fourth POC of the same shape.** Concretely:

1. **Keep the harness as the asset.** It is well-engineered — 44 and 181 tests pass on this Linux
   host, with the 105-test POC-003 suite running in full only on its Windows CI matrix — and it is
   the part that transfers to any other risky toolchain.
2. **Narrow the next two executable units to the verification wedge** (no license blocker):
   - `POC-VERIFY-001`: read-only, real-plugin header/master/CNAM/DELE inventory against a
     *user-supplied* plugin, plus the strict-format findings POC-002's parser cannot yet
     represent (1.71 headers, `0xFFFF` extended subrecord sizes, ESL/ESM flags). Output: a
     typed defect report + receipt. This converts "synthetic fixture" evidence into real-format
     evidence without any write path.
   - `POC-PEX-001`: a `.pex` structural reader + a **privacy redaction gate** and a
     **semantic** (not byte) equivalence check for rebuild comparison. This is where POC-003's
     two failures turn into product surface, and it needs no compiler to be *verified*: only to
     be *reproduced*.
3. **Do not build the LLM planner first.** With two read-only primitives, a planner would have
   nothing to plan over and would become the demo that hides the missing 90%. Build the plan
   schema, policy engine and capability router against those two primitives first; the model is
   the last, most replaceable layer.
4. **Resolve ADR-003 or close the authoring track.** The license decision, not engineering,
   gates V2. If copyleft distribution is unacceptable, say so in an ADR and fold the authoring
   ambition into "verify + gate + report", which does not need it.
5. **Retire or derive the Discovery Desk.** It is a second, hand-maintained copy of the
   research state and it had already drifted at review date (see §7). Generate it from `docs/`,
   or drop it; do not keep a mirror that needs its own policing.

### What would change the verdict

- A `PASS` for POC-001 (CK UIA is automatable read-only, reproducibly) would reopen the CK path.
- A permissive, maintained SE/AE record writer (or an accepted ADR-003 outcome) would reopen V2.
- A `PASS` for a semantic `.pex` equivalence gate would make "rebuild and prove" viable despite
  the byte-determinism failure.

## 7. Repository findings fixed by this review

Each was verified locally on Linux (Python 3.11) on 2026-09-24; commands are in the entries.

1. **Integrity gate had a mechanical hole (real).** `sha256sum -c MANIFEST.sha256` only checks
   rows present in the manifest; `research/poc_ipc_001/tests/helper_workers/*.py` — 13 tracked
   files inside the declared `research/**` perimeter — were never pinned, which is exactly the
   PR #15 failure mode `CONTRIBUTING.md` forbids. Fixed by
   `tools/check_manifest_coverage.py` (perimeter-vs-manifest diff, duplicate/stale/malformed/
   hash-drain detection, `--update` re-pin) plus a CI job; the 13 rows are now pinned.
2. **Declared Python tooling did not run (real).** `pyproject.toml` declared `ruff`, `mypy` and
   `pytest`, no workflow executed them, and `mypy` could not start at all: duplicate module names
   across POC roots (`orchestrator.py` in both `poc_002` and `poc_ipc_001`) aborted the run, so
   "typecheck passes" was vacuous. `research/poc_002` is mypy-clean; the tree carries 35 recorded
   findings: 17 ruff (13 unused imports `F401`, 2 redefinitions `F811`, 1 `F541`, 1 `B007`) and
   18 mypy (12 `attr-defined` on Windows-only `ctypes` access, 5 `call-overload`, 1 `arg-type`).
   Fixed by `tools/quality_ratchet.py` + `tools/quality-baseline.txt` (debt grandfathered, new
   findings fail) and namespace-package resolution in `[tool.mypy]`.
3. **POC suites are not co-importable (hazard, verified).** `python -m pytest -q
   research/poc_002 research/poc_ipc_001/tests` makes `poc_ipc_001`'s tests import
   `poc_002/orchestrator.py` and `poc_002/protocol.py`. It only failed loudly because the symbol
   names differ. A single combined collection run — which a future test runner or product import
   would naturally do — silently mixes implementations across safety boundaries. Documented in
   `pyproject.toml`, with per-suite invocation as the rule; productization needs real package
   namespaces first.
4. **POC-003's hermetic suite is Windows-only by import, silently (documentation gap).** On
   Linux it reports `Ran 64 tests ... FAILED (errors=3)` (61 real tests + 3 loader errors), not a
   skip; the 41 Windows-only tests never run. Now stated in `research/poc_003/README.md`, and the
   ratchet runs on Linux only so cross-platform finding counts are not compared as if equivalent.
5. **The Discovery Desk misrepresented project state (real, claim-integrity).**
   `src/lib/research/experiments.ts` still described POC-003 as blocked by "Compiler binary not
   present here" — after two executed Windows runs whose measured failures are the reason it is
   `NO VERIFICADO` — and `research/poc_003/README.md` said only criterion 14 failed when both 12
   and 14 did. The desk also omitted POC-IPC-001 and POC-MUTAGEN-001 entirely, and its
   experiments page announced "Designed, not executed" over executed proofs. Fixed, and
   `tests/desk-docs-consistency.test.ts` now fails CI if the desk and `docs/research/experiments.md`
   disagree on a status, if either side gains a row the other lacks, if a status leaves the
   canonical vocabulary, or if a desk row presents a dated execution as pending (the exact class
   of drift found here).
6. **Canonical experiment index was incomplete.** `docs/research/experiments.md` documented no
   POC-IPC-001 or POC-MUTAGEN-001 entry although both are `PASS`/`BLOQUEADO` states carried by
   `README.md`, `docs/status.md` and `docs/roadmap.md`. Added, recording the intentional index
   migration that `AGENTS.md`'s identifier rule allows.

## 8. Effort and options, stated plainly

| Option | Cost to reach a defensible claim | Ceiling | Recommendation |
| --- | --- | --- | --- |
| A. Verification/gate layer (V3) | ~2 POCs + one thin CLI on top of existing code; no Windows box needed for `.pex`/plugin *reading* if a user supplies files | Niche but real; useful to authors and to the surveyed tools | **Do this.** It is the only option where this repo's evidence style is an advantage rather than overhead. |
| B. Authoring agent (V2) | ADR-003 decision + a writer POC + real-plugin parser work + per-record semantic validation, on Windows, against a mature GPL competitor | Crowded; you start behind on capability and even on safety | Only with a decision that copyleft distribution is acceptable *and* a target the competitors do not serve. |
| C. CK automation (V1) | POC-001 on a dedicated Windows host, then a fragile UI contract against an EULA you may not reverse-engineer | Blocked legally and technically | Do not pursue as a spine. |
| D. Methodology artifact | Write up pre-registration + evidence tiers + ratchets as a reusable protocol | Small, durable, citable | Cheap by-product of A; do it in the same pass. |

## 9. Sources for §4 (read, not executed)

- `https://github.com/Avick3110/houseCARL` and its Nexus page (`skyrimspecialedition/mods/181738`).
- `https://github.com/ShugokiFable/SkyrimForge` (standalone frozen at 5.2.1; moved into
  `Ultimate-AI-Starter-Bundle`), and `https://mcpmarket.com/server/skyrim-forge-1`.
- `https://github.com/Pyrhame/SkyrimCK-MCP`.
- `https://github.com/Mutagen-Modding/Mutagen`, `https://www.nuget.org/packages/Mutagen.Bethesda.Skyrim`
  (GPL-3.0-only confirmed on the NuGet package metadata).
- This repository: `docs/research/existing-projects.md` (2026-08), which already recorded the same
  conclusion with less recent data.

Descriptive claims about third-party tools are `NO VERIFICADO` by this repository's own rules:
they are marketing/README statements, not reproduced measurements. They are used only as a
"someone else may already ship this" signal, never as evidence that a feature is safe or correct.
