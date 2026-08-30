CREATE TABLE "research_architecture_options" (
	"id" serial PRIMARY KEY NOT NULL,
	"code" text NOT NULL,
	"name" text NOT NULL,
	"summary" text NOT NULL,
	"robustness" integer NOT NULL,
	"security" integer NOT NULL,
	"complexity" integer NOT NULL,
	"maintainability" integer NOT NULL,
	"license_fit" integer NOT NULL,
	"performance" integer NOT NULL,
	"automation" integer NOT NULL,
	"testability" integer NOT NULL,
	"compatibility" integer NOT NULL,
	"external_deps" integer NOT NULL,
	"corruption_risk" integer NOT NULL,
	"weighted_score" integer NOT NULL,
	"recommended" boolean NOT NULL,
	"notes" text NOT NULL,
	"sort_order" integer NOT NULL
);
--> statement-breakpoint
CREATE TABLE "research_capabilities" (
	"id" serial PRIMARY KEY NOT NULL,
	"name" text NOT NULL,
	"mvp_class" text NOT NULL,
	"status" text NOT NULL,
	"backend" text NOT NULL,
	"risk" text NOT NULL,
	"notes" text NOT NULL,
	"sort_order" integer NOT NULL
);
--> statement-breakpoint
CREATE TABLE "research_document_sections" (
	"id" serial PRIMARY KEY NOT NULL,
	"document_slug" text NOT NULL,
	"heading" text NOT NULL,
	"body" text NOT NULL,
	"status" text NOT NULL,
	"sort_order" integer NOT NULL
);
--> statement-breakpoint
CREATE TABLE "research_documents" (
	"id" serial PRIMARY KEY NOT NULL,
	"slug" text NOT NULL,
	"title" text NOT NULL,
	"phase" text NOT NULL,
	"summary" text NOT NULL,
	"sort_order" integer NOT NULL,
	CONSTRAINT "research_documents_slug_unique" UNIQUE("slug")
);
--> statement-breakpoint
CREATE TABLE "research_existing_projects" (
	"id" serial PRIMARY KEY NOT NULL,
	"name" text NOT NULL,
	"url" text NOT NULL,
	"last_activity" text NOT NULL,
	"license" text NOT NULL,
	"language" text NOT NULL,
	"architecture" text NOT NULL,
	"solves" text NOT NULL,
	"does_not_solve" text NOT NULL,
	"project_status" text NOT NULL,
	"reusable_code" text NOT NULL,
	"risks" text NOT NULL,
	"sort_order" integer NOT NULL
);
--> statement-breakpoint
CREATE TABLE "research_experiments" (
	"id" serial PRIMARY KEY NOT NULL,
	"code" text NOT NULL,
	"title" text NOT NULL,
	"hypothesis" text NOT NULL,
	"method" text NOT NULL,
	"success_criteria" text NOT NULL,
	"status" text NOT NULL,
	"blocked_by" text NOT NULL,
	"sort_order" integer NOT NULL
);
--> statement-breakpoint
CREATE TABLE "research_findings" (
	"id" serial PRIMARY KEY NOT NULL,
	"category" text NOT NULL,
	"claim" text NOT NULL,
	"status" text NOT NULL,
	"evidence" text NOT NULL,
	"implication" text NOT NULL,
	"sort_order" integer NOT NULL
);
--> statement-breakpoint
CREATE TABLE "research_gate_questions" (
	"id" serial PRIMARY KEY NOT NULL,
	"question" text NOT NULL,
	"answer" text NOT NULL,
	"status" text NOT NULL,
	"experiment_needed" text NOT NULL,
	"sort_order" integer NOT NULL
);
--> statement-breakpoint
CREATE TABLE "research_license_entries" (
	"id" serial PRIMARY KEY NOT NULL,
	"component" text NOT NULL,
	"license" text NOT NULL,
	"intended_use" text NOT NULL,
	"modification" text NOT NULL,
	"distribution" text NOT NULL,
	"risk" text NOT NULL,
	"legal_review_required" boolean NOT NULL,
	"notes" text NOT NULL,
	"sort_order" integer NOT NULL
);
--> statement-breakpoint
CREATE TABLE "research_name_candidates" (
	"id" serial PRIMARY KEY NOT NULL,
	"name" text NOT NULL,
	"memorability" text NOT NULL,
	"skyrim_relation" text NOT NULL,
	"ck_relation" text NOT NULL,
	"searchability" text NOT NULL,
	"collisions" text NOT NULL,
	"length" text NOT NULL,
	"pronunciation" text NOT NULL,
	"visual_identity" text NOT NULL,
	"trademark_risk" text NOT NULL,
	"recommendation" text NOT NULL,
	"sort_order" integer NOT NULL
);
--> statement-breakpoint
CREATE TABLE "research_sources" (
	"id" serial PRIMARY KEY NOT NULL,
	"title" text NOT NULL,
	"url" text NOT NULL,
	"publisher" text NOT NULL,
	"accessed_on" text NOT NULL,
	"verification" text NOT NULL,
	"notes" text NOT NULL
);
--> statement-breakpoint
CREATE TABLE "research_use_cases" (
	"id" serial PRIMARY KEY NOT NULL,
	"name" text NOT NULL,
	"description" text NOT NULL,
	"mvp_inclusion" text NOT NULL,
	"risk_level" text NOT NULL,
	"preferred_backend" text NOT NULL,
	"sort_order" integer NOT NULL
);
--> statement-breakpoint
CREATE TABLE "research_verdicts" (
	"id" serial PRIMARY KEY NOT NULL,
	"verdict" text NOT NULL,
	"rationale" text NOT NULL,
	"recommended_architecture" text NOT NULL,
	"primary_backend" text NOT NULL,
	"fallback_backend" text NOT NULL,
	"highest_technical_risk" text NOT NULL,
	"highest_legal_risk" text NOT NULL,
	"first_experiment" text NOT NULL,
	"mvp_candidate" text NOT NULL,
	"next_step" text NOT NULL,
	"created_at" timestamp with time zone DEFAULT now()
);
