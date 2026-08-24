# POC-002 — Synthetic TES4 inspection and safety pipeline

**Status:** `PASS`  
**Evidence:** `E2_REOPENED_ASSERTIONS_PASS` within the synthetic fixture scope.

## What it proves

- deterministic synthetic TES4 serialization/parsing;
- HEDR `1.70` fixture with FormVersion `44`;
- strict malformed-input rejection;
- closed operations and truthful capability routing;
- workspace/path containment;
- immutable original SHA invariant;
- candidate-only execution model;
- no-overwrite receipts;
- fail-closed orchestration;
- empty plans cannot produce vacuous `PASS/E2`;
- 43 automated tests.

## What it does not prove

- arbitrary real Skyrim plugin compatibility;
- header `1.71` support;
- Mutagen compatibility;
- Creation Kit behavior;
- xEdit/Papyrus behavior;
- in-game/runtime correctness;
- any write capability beyond the synthetic/read-only scope.

## Run

```bash
python -m compileall .
python -m unittest test_suite.py -v
```

Expected validated baseline:

```text
Ran 43 tests
OK
```
