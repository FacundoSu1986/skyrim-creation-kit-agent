export const DISTRIBUTION_AUTHORIZATION_STATUSES = [
  "LEGAL_REVIEW_REQUIRED",
  "DESCARTADO",
  "NOT_APPLICABLE",
] as const;

export type DistributionAuthorizationStatus =
  (typeof DISTRIBUTION_AUTHORIZATION_STATUSES)[number];

export function isDistributionAuthorizationStatus(
  value: unknown,
): value is DistributionAuthorizationStatus {
  return (
    typeof value === "string" &&
    (DISTRIBUTION_AUTHORIZATION_STATUSES as readonly string[]).includes(value)
  );
}

export interface LicenseRow {
  component: string;
  license: string;
  intendedUse: string;
  modification: string;
  distribution: string;
  risk: string;
  legalReviewRequired: boolean;
  distributionAuthorizationStatus: DistributionAuthorizationStatus;
  notes: string;
}

export const licenseRows: LicenseRow[] = [
  {
    component: "Skyrim Special Edition / Anniversary Edition",
    license: "Proprietary Bethesda / ZeniMax game EULA",
    intendedUse: "User already owns a legal copy. Read Data as input. Never copy vanilla assets into this repo.",
    modification: "Game files must not be modified by this project.",
    distribution: "Forbidden.",
    risk: "Critical if assets or executables are redistributed",
    legalReviewRequired: true,
    distributionAuthorizationStatus: "DESCARTADO",
    notes: "LEGAL_REVIEW_REQUIRED for any fixture that is a real Bethesda plugin or script header.",
  },
  {
    component: "Creation Kit (Steam 1946180)",
    license: "ZeniMax Creation Kit Editor EULA",
    intendedUse: "Execute the user's installed Editor locally, if an experiment requires it.",
    modification: "EULA forbids reverse engineering, decompile, modify, derivative works of the Editor.",
    distribution: "Forbidden. Never bundle CreationKit.exe, steam_api, or CK resources.",
    risk: "Critical — in-process hooks and patches may breach 1.C",
    legalReviewRequired: true,
    distributionAuthorizationStatus: "DESCARTADO",
    notes:
      "Executing the official tool the user already licensed is different from linking against it or distributing it. Those three acts are not equivalent.",
  },
  {
    component: "Steam / steam_api64.dll",
    license: "Valve / Steam subscriber agreement + game files",
    intendedUse: "Present on the user's machine because CK requires it.",
    modification: "Do not ship replacement Steam DLLs.",
    distribution: "Forbidden.",
    risk: "High",
    legalReviewRequired: true,
    distributionAuthorizationStatus: "DESCARTADO",
    notes: "Community CK installs juggle steam_api64.dll. This project must not automate DLL swapping.",
  },
  {
    component: "Creation Kit Platform Extended",
    license: "LGPLv3 since v0.6; GPLv3 earlier; some proprietary resource blobs",
    intendedUse: "Optional user-installed CK host. Study PluginAPI. Do not vendor.",
    modification: "LGPL allows modification with obligations. EULA may still forbid patching CK.",
    distribution: "Do not redistribute CKPE binaries or proprietary pak/d3dcompiler files.",
    risk: "Critical legal overlay (LGPL + CK EULA + DLL proxy)",
    legalReviewRequired: true,
    distributionAuthorizationStatus: "LEGAL_REVIEW_REQUIRED",
    notes:
      "Two licenses apply at once: CKPE's LGPL and Bethesda's prohibition on modifying the Editor. That conflict is the highest legal risk.",
  },
  {
    component: "Mutagen / Synthesis / Spriggit",
    license: "GPL-3.0-only (no linking exception observed)",
    intendedUse: "Preferred headless record engine if the worker can be GPL.",
    modification: "Allowed under GPL.",
    distribution: "Source must be offered if a linked binary is distributed.",
    risk: "High product-license impact, not a Bethesda EULA issue",
    legalReviewRequired: false,
    distributionAuthorizationStatus: "LEGAL_REVIEW_REQUIRED",
    notes:
      "MIT code may be combined with GPL code, but distributing the combined work requires GPL compliance, including corresponding source and notices; MIT alone is insufficient. ADR-003 L3 distribution model still requires legal authorization.",
  },
  {
    component: "xEdit / SSEEdit",
    license: "MPL-2.0 (repository). Site text still mentions MPL 1.1.",
    intendedUse: "Execute the user's copy as an external validator / allowlisted script host.",
    modification: "Not required. Do not fork unless necessary.",
    distribution: "Do not bundle the executable. Linking as a library is not the public API.",
    risk: "Medium (license inconsistency + script execution)",
    legalReviewRequired: false,
    distributionAuthorizationStatus: "NOT_APPLICABLE",
    notes: "Executing an external MPL tool is generally cleaner than linking. Confirm MPL 2.0 vs 1.1 before any code reuse.",
  },
  {
    component: "LOOT / libloot",
    license: "GPL-3.0",
    intendedUse: "Optional later load-order adapter.",
    modification: "Not planned.",
    distribution: "Do not bundle.",
    risk: "Medium if linked; low if executed as a separate app",
    legalReviewRequired: false,
    distributionAuthorizationStatus: "NOT_APPLICABLE",
    notes: "Not needed for Gate 1 or MVP authoring.",
  },
  {
    component: "esper / esper-js / esper-cpp / balsa",
    license: "esper-js MIT; esper-cpp MIT; C# esper not confirmed",
    intendedUse: "Possible permissively licensed plugin parser alternative to Mutagen.",
    modification: "Only after LICENSE file is read.",
    distribution: "Only after LICENSE file is read.",
    risk: "Medium until C# esper license is confirmed",
    legalReviewRequired: true,
    distributionAuthorizationStatus: "LEGAL_REVIEW_REQUIRED",
    notes: "LEGAL_REVIEW_REQUIRED on matortheeternal/esper C#. Do not link yet.",
  },
  {
    component: "PapyrusCompiler.exe / TESV_Papyrus_Flags.flg / vanilla .psc",
    license: "ZeniMax proprietary, shipped with CK",
    intendedUse: "Invoke the user's compiler. Never commit headers or the compiler.",
    modification: "Forbidden.",
    distribution: "Forbidden.",
    risk: "High if fixtures include Bethesda sources",
    legalReviewRequired: true,
    distributionAuthorizationStatus: "DESCARTADO",
    notes: "Spooky's toolkit correctly warns: do not commit .psc headers.",
  },
  {
    component: "FlaUI",
    license: "MIT",
    intendedUse: "Possible later Windows UIA worker.",
    modification: "Not required.",
    distribution: "Permissive.",
    risk: "Low license; high operational if used against CK",
    legalReviewRequired: false,
    distributionAuthorizationStatus: "NOT_APPLICABLE",
    notes: "Preferred UIA library if PoC-001 shows useful controls.",
  },
  {
    component: "pywinauto",
    license: "BSD-style (verify exact text before pin)",
    intendedUse: "Possible Python UIA/win32 inspector.",
    modification: "Not required.",
    distribution: "Permissive if BSD confirmed.",
    risk: "Low license",
    legalReviewRequired: false,
    distributionAuthorizationStatus: "NOT_APPLICABLE",
    notes: "Confirm LICENSE file when adding the dependency. Not needed until PoC-001.",
  },
  {
    component: "WinAppDriver",
    license: "Microsoft; server source unpublished",
    intendedUse: "None.",
    modification: "Impossible — server is closed.",
    distribution: "Do not adopt.",
    risk: "Abandoned",
    legalReviewRequired: false,
    distributionAuthorizationStatus: "DESCARTADO",
    notes: "DESCARTADO as a new dependency.",
  },
  {
    component: "This research portal (Next.js app)",
    license: "MIT for material the licensor has authority to license; third-party licenses remain separate.",
    intendedUse: "Publish Phase 0+1 findings. No CK binaries.",
    modification: "N/A",
    distribution: "Source of this desk only.",
    risk: "Imported research provenance unresolved",
    legalReviewRequired: true,
    distributionAuthorizationStatus: "LEGAL_REVIEW_REQUIRED",
    notes:
      "The maintainer reports probable AI generation, not verified authorship or third-party permissions. See docs/research/source-manifest.md and /licenses/THIRD_PARTY_NOTICES.md. ADR-003 remains unresolved.",
  },
  {
    component: "Discovery Desk npm dependencies",
    license: "MIT, Apache-2.0 and other licenses; see exact lockfile inventory.",
    intendedUse: "Next.js research portal and development tooling.",
    modification: "Subject to each package license.",
    distribution: "Preserve upstream licenses, copyright and applicable NOTICE files for shipped components.",
    risk: "Release contents require review",
    legalReviewRequired: false,
    distributionAuthorizationStatus: "LEGAL_REVIEW_REQUIRED",
    notes: "docs/research/npm-license-inventory.md includes development and optional packages; it is not an inventory of a shipped artifact.",
  },
  {
    component: "sharp / libvips platform packages",
    license: "Apache-2.0 / LGPL-3.0-or-later; combined expressions vary by platform.",
    intendedUse: "Optional native image processing dependency of Next.js.",
    modification: "Subject to the licenses of the affected code and native libraries.",
    distribution: "Retain notices; satisfy applicable LGPL source and replacement/relinking requirements.",
    risk: "Inspect actual native binaries in each release",
    legalReviewRequired: false,
    distributionAuthorizationStatus: "LEGAL_REVIEW_REQUIRED",
    notes: "LGPL dependencies do not automatically convert the whole MIT application to GPL. See /licenses/THIRD_PARTY_NOTICES.md.",
  },
  {
    component: "lightningcss / axe-core / caniuse-lite",
    license: "MPL-2.0 (lightningcss, axe-core); CC-BY-4.0 (caniuse-lite).",
    intendedUse: "CSS/lint development tooling and browser compatibility data.",
    modification: "Observe covered-source, attribution and change-notice conditions as applicable.",
    distribution: "Review covered code/data actually shipped; generated CSS is not automatically MPL.",
    risk: "Do not confuse development dependencies with browser delivery",
    legalReviewRequired: false,
    distributionAuthorizationStatus: "LEGAL_REVIEW_REQUIRED",
    notes: "Preserve upstream notices and satisfy source/attribution requirements when distributing covered material.",
  },
  {
    component: "Fraunces / IBM Plex Sans / IBM Plex Mono",
    license: "SIL Open Font License 1.1",
    intendedUse: "Fonts downloaded and self-hosted by next/font/google.",
    modification: "Subject to OFL terms, including reserved font names where applicable.",
    distribution: "Include copyright and full OFL texts supplied in public/licenses/ with the fonts.",
    risk: "Verify notices against the actual font binaries in a release",
    legalReviewRequired: false,
    distributionAuthorizationStatus: "LEGAL_REVIEW_REQUIRED",
    notes: "Fraunces Project Authors; IBM Corp. (reserved name Plex). License-text origins/hashes are in /licenses/font-sources.json; font binaries are not pinned by those hashes.",
  },
];
