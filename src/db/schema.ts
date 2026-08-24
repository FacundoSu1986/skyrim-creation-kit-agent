import {
  boolean,
  integer,
  pgTable,
  serial,
  text,
  timestamp,
} from "drizzle-orm/pg-core";

export const sources = pgTable("research_sources", {
  id: serial("id").primaryKey(),
  title: text("title").notNull(),
  url: text("url").notNull(),
  publisher: text("publisher").notNull(),
  accessedOn: text("accessed_on").notNull(),
  verification: text("verification").notNull(),
  notes: text("notes").notNull(),
});

export const documents = pgTable("research_documents", {
  id: serial("id").primaryKey(),
  slug: text("slug").notNull().unique(),
  title: text("title").notNull(),
  phase: text("phase").notNull(),
  summary: text("summary").notNull(),
  sortOrder: integer("sort_order").notNull(),
});

export const documentSections = pgTable("research_document_sections", {
  id: serial("id").primaryKey(),
  documentSlug: text("document_slug").notNull(),
  heading: text("heading").notNull(),
  body: text("body").notNull(),
  status: text("status").notNull(),
  sortOrder: integer("sort_order").notNull(),
});

export const findings = pgTable("research_findings", {
  id: serial("id").primaryKey(),
  category: text("category").notNull(),
  claim: text("claim").notNull(),
  status: text("status").notNull(),
  evidence: text("evidence").notNull(),
  implication: text("implication").notNull(),
  sortOrder: integer("sort_order").notNull(),
});

export const existingProjects = pgTable("research_existing_projects", {
  id: serial("id").primaryKey(),
  name: text("name").notNull(),
  url: text("url").notNull(),
  lastActivity: text("last_activity").notNull(),
  license: text("license").notNull(),
  language: text("language").notNull(),
  architecture: text("architecture").notNull(),
  solves: text("solves").notNull(),
  doesNotSolve: text("does_not_solve").notNull(),
  projectStatus: text("project_status").notNull(),
  reusableCode: text("reusable_code").notNull(),
  risks: text("risks").notNull(),
  sortOrder: integer("sort_order").notNull(),
});

export const licenseEntries = pgTable("research_license_entries", {
  id: serial("id").primaryKey(),
  component: text("component").notNull(),
  license: text("license").notNull(),
  intendedUse: text("intended_use").notNull(),
  modification: text("modification").notNull(),
  distribution: text("distribution").notNull(),
  risk: text("risk").notNull(),
  legalReviewRequired: boolean("legal_review_required").notNull(),
  notes: text("notes").notNull(),
  sortOrder: integer("sort_order").notNull(),
});

export const architectureOptions = pgTable("research_architecture_options", {
  id: serial("id").primaryKey(),
  code: text("code").notNull(),
  name: text("name").notNull(),
  summary: text("summary").notNull(),
  robustness: integer("robustness").notNull(),
  security: integer("security").notNull(),
  complexity: integer("complexity").notNull(),
  maintainability: integer("maintainability").notNull(),
  licenseFit: integer("license_fit").notNull(),
  performance: integer("performance").notNull(),
  automation: integer("automation").notNull(),
  testability: integer("testability").notNull(),
  compatibility: integer("compatibility").notNull(),
  externalDeps: integer("external_deps").notNull(),
  corruptionRisk: integer("corruption_risk").notNull(),
  weightedScore: integer("weighted_score").notNull(),
  recommended: boolean("recommended").notNull(),
  notes: text("notes").notNull(),
  sortOrder: integer("sort_order").notNull(),
});

export const capabilities = pgTable("research_capabilities", {
  id: serial("id").primaryKey(),
  name: text("name").notNull(),
  mvpClass: text("mvp_class").notNull(),
  status: text("status").notNull(),
  backend: text("backend").notNull(),
  risk: text("risk").notNull(),
  notes: text("notes").notNull(),
  sortOrder: integer("sort_order").notNull(),
});

export const gateQuestions = pgTable("research_gate_questions", {
  id: serial("id").primaryKey(),
  question: text("question").notNull(),
  answer: text("answer").notNull(),
  status: text("status").notNull(),
  experimentNeeded: text("experiment_needed").notNull(),
  sortOrder: integer("sort_order").notNull(),
});

export const nameCandidates = pgTable("research_name_candidates", {
  id: serial("id").primaryKey(),
  name: text("name").notNull(),
  memorability: text("memorability").notNull(),
  skyrimRelation: text("skyrim_relation").notNull(),
  ckRelation: text("ck_relation").notNull(),
  searchability: text("searchability").notNull(),
  collisions: text("collisions").notNull(),
  length: text("length").notNull(),
  pronunciation: text("pronunciation").notNull(),
  visualIdentity: text("visual_identity").notNull(),
  trademarkRisk: text("trademark_risk").notNull(),
  recommendation: text("recommendation").notNull(),
  sortOrder: integer("sort_order").notNull(),
});

export const experiments = pgTable("research_experiments", {
  id: serial("id").primaryKey(),
  code: text("code").notNull(),
  title: text("title").notNull(),
  hypothesis: text("hypothesis").notNull(),
  method: text("method").notNull(),
  successCriteria: text("success_criteria").notNull(),
  status: text("status").notNull(),
  blockedBy: text("blocked_by").notNull(),
  sortOrder: integer("sort_order").notNull(),
});

export const useCases = pgTable("research_use_cases", {
  id: serial("id").primaryKey(),
  name: text("name").notNull(),
  description: text("description").notNull(),
  mvpInclusion: text("mvp_inclusion").notNull(),
  riskLevel: text("risk_level").notNull(),
  preferredBackend: text("preferred_backend").notNull(),
  sortOrder: integer("sort_order").notNull(),
});

export const verdicts = pgTable("research_verdicts", {
  id: serial("id").primaryKey(),
  verdict: text("verdict").notNull(),
  rationale: text("rationale").notNull(),
  recommendedArchitecture: text("recommended_architecture").notNull(),
  primaryBackend: text("primary_backend").notNull(),
  fallbackBackend: text("fallback_backend").notNull(),
  highestTechnicalRisk: text("highest_technical_risk").notNull(),
  highestLegalRisk: text("highest_legal_risk").notNull(),
  firstExperiment: text("first_experiment").notNull(),
  mvpCandidate: text("mvp_candidate").notNull(),
  nextStep: text("next_step").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
});
