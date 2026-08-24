export const gateRows = [
  {
    question: "Does Creation Kit expose sufficient interfaces?",
    answer:
      "No official authoring API, RPC, or general CLI was found. CK is a GUI editor. FO4 has batch precombine flags; that is not an SSE create-record API. CKPE PluginAPI exists but QueryInterface implements no authoring interfaces.",
    status: "VERIFICADO",
    experimentNeeded:
      "EXP-CK-CLI on a real CreationKit.exe to list any undocumented switches. Do not block Gate 1 on that — absence of a public API is already enough to reject a CK-API-first design.",
  },
  {
    question: "Does UI Automation detect useful CK controls?",
    answer:
      "Unknown. No inspect dump of SSE CK 1.6.x was located. Not tested here because this environment has no Windows CK.",
    status: "NO VERIFICADO",
    experimentNeeded: "POC-001 — read-only Inspect.exe / Accessibility Insights session.",
  },
  {
    question: "Does CKPE offer a viable plugin path?",
    answer:
      "Technically: a DLL can load. Practically: no high-level Editor object model. Legally: conflicts with the CK EULA reverse-engineering clause. Operationally: winhttp proxy is a DLL-search-order pattern.",
    status: "LEGAL_REVIEW_REQUIRED",
    experimentNeeded:
      "EXP-CKPE-QIFACE after counsel. Until then CKPE is out of the MVP critical path.",
  },
  {
    question: "Which operations can avoid CK entirely?",
    answer:
      "Header inspect, record create/edit for many types (MISC, WEAP, ARMO, SPEL, KYWD, GLOB, FLST, OTFT, NPC_ base, even QUST/INFO in other projects), Papyrus compile, static validation, Spriggit diffs. CK remains necessary for FaceGen export, navmesh, Render Window, lip gen, and some visual placement.",
    status: "VERIFICADO",
    experimentNeeded:
      "Capability-by-capability contract tests on a candidate plugin — not a single yes/no.",
  },
  {
    question: "Which licenses shape the architecture?",
    answer:
      "CK EULA forbids RE/modify of the Editor. Mutagen is GPL-3.0-only (forces worker license). xEdit is MPL-2.0 and should be executed, not vendored. CKPE is LGPLv3 plus a legal overlay. Vanilla assets cannot be committed.",
    status: "VERIFICADO",
    experimentNeeded: "EXP-ESPER-LICENSE if a non-GPL parser is desired.",
  },
  {
    question: "What is the first reproducible PoC?",
    answer:
      "POC-002 synthetic TES4 header parse. Executed and passed: 43/43 tests, evidence E2_REOPENED_ASSERTIONS_PASS on the synthetic fixture. POC-001 (read-only CK window inspect) remains designed-only, BLOQUEADO outside a Windows CK machine.",
    status: "VERIFICADO",
    experimentNeeded:
      "Done for POC-002 (research/poc_002/). Next executable proofs: POC-003 and POC-004 on a Windows runner with legal tool installs.",
  },
  {
    question: "How do we avoid corruption?",
    answer:
      "Never write the user's only plugin. Workspace with originals (hashed, read-only), candidates, backups, reports, logs. Typed operations only. Fail-fast on unexpected dialogs, hash mismatch, or missing completion markers. No arbitrary shell.",
    status: "VERIFICADO",
    experimentNeeded:
      "Design is specified. Implementation comes after ADR. Pattern already used by SkyrimForge.",
  },
  {
    question: "How do we rollback?",
    answer:
      "Candidates are new files. Originals are never overwritten. Each write snapshots input hash → output hash. Rollback = discard candidate. In-place edit of a user's plugin is forbidden in MVP (houseCARL's opt-in in-place lane is explicitly rejected).",
    status: "VERIFICADO",
    experimentNeeded: "None for the policy. Tests later.",
  },
  {
    question: "How do we validate a result?",
    answer:
      "Layered evidence: (1) schema validation of the plan, (2) writer receipt + hashes, (3) reopen candidate and assert EditorID/fields, (4) optional xEdit check-for-errors, (5) human approval, (6) later in-game test. Never claim (4) or (6) from (2).",
    status: "VERIFICADO",
    experimentNeeded: "Contract tests per adapter after a backend is chosen in ADR-001.",
  },
];
