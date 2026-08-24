export const EVIDENCE_STATUSES = [
  "VERIFICADO",
  "PASS",
  "NO VERIFICADO",
  "HIPOTESIS",
  "EXPERIMENTAL",
  "BLOQUEADO",
  "DESCARTADO",
  "LEGAL_REVIEW_REQUIRED",
] as const;

export type EvidenceStatus = (typeof EVIDENCE_STATUSES)[number];

export const STATUS_LABELS: Record<string, string> = {
  VERIFICADO: "Verified",
  // Canonical state for an experiment that was executed and passed its own
  // gate (for example POC-002: 43/43 tests, E2 evidence).
  PASS: "Pass",
  "NO VERIFICADO": "Unverified",
  HIPOTESIS: "Hypothesis",
  EXPERIMENTAL: "Experimental",
  BLOQUEADO: "Blocked",
  DESCARTADO: "Rejected",
  LEGAL_REVIEW_REQUIRED: "Legal review",
};

export function statusClass(status: string): string {
  switch (status) {
    case "VERIFICADO":
      return "badge-verified";
    case "PASS":
      return "badge-pass";
    case "NO VERIFICADO":
      return "badge-unverified";
    case "HIPOTESIS":
      return "badge-hypothesis";
    case "EXPERIMENTAL":
      return "badge-experimental";
    case "BLOQUEADO":
      return "badge-blocked";
    case "DESCARTADO":
      return "badge-rejected";
    case "LEGAL_REVIEW_REQUIRED":
      return "badge-legal";
    default:
      return "badge-unverified";
  }
}

export function riskClass(risk: string): string {
  const value = risk.toLowerCase();
  if (value.includes("critical") || value.includes("high")) return "risk-high";
  if (value.includes("medium")) return "risk-medium";
  if (value.includes("low")) return "risk-low";
  return "risk-unknown";
}
