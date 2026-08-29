import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import dotenv from "dotenv";
import { drizzle } from "drizzle-orm/node-postgres";
import { migrate } from "drizzle-orm/node-postgres/migrator";
import { Pool } from "pg";

dotenv.config();

export interface ColumnSpec {
  name: string;
  dataType: string;
  isNullable: "YES" | "NO";
}

export interface BaselineFingerprintResult {
  valid: boolean;
  missingTables: string[];
  missingColumns: string[];
  unexpectedCriticalColumns: string[];
  typeMismatches: string[];
  nullabilityMismatches: string[];
  primaryKeyMismatches: string[];
  constraintMismatches: string[];
  errors: string[];
}

export const EXPECTED_BASELINE_SCHEMA: Record<string, ColumnSpec[]> = {
  research_architecture_options: [
    { name: "id", dataType: "integer", isNullable: "NO" },
    { name: "code", dataType: "text", isNullable: "NO" },
    { name: "name", dataType: "text", isNullable: "NO" },
    { name: "summary", dataType: "text", isNullable: "NO" },
    { name: "robustness", dataType: "integer", isNullable: "NO" },
    { name: "security", dataType: "integer", isNullable: "NO" },
    { name: "complexity", dataType: "integer", isNullable: "NO" },
    { name: "maintainability", dataType: "integer", isNullable: "NO" },
    { name: "license_fit", dataType: "integer", isNullable: "NO" },
    { name: "performance", dataType: "integer", isNullable: "NO" },
    { name: "automation", dataType: "integer", isNullable: "NO" },
    { name: "testability", dataType: "integer", isNullable: "NO" },
    { name: "compatibility", dataType: "integer", isNullable: "NO" },
    { name: "external_deps", dataType: "integer", isNullable: "NO" },
    { name: "corruption_risk", dataType: "integer", isNullable: "NO" },
    { name: "weighted_score", dataType: "integer", isNullable: "NO" },
    { name: "recommended", dataType: "boolean", isNullable: "NO" },
    { name: "notes", dataType: "text", isNullable: "NO" },
    { name: "sort_order", dataType: "integer", isNullable: "NO" },
  ],
  research_capabilities: [
    { name: "id", dataType: "integer", isNullable: "NO" },
    { name: "name", dataType: "text", isNullable: "NO" },
    { name: "mvp_class", dataType: "text", isNullable: "NO" },
    { name: "status", dataType: "text", isNullable: "NO" },
    { name: "backend", dataType: "text", isNullable: "NO" },
    { name: "risk", dataType: "text", isNullable: "NO" },
    { name: "notes", dataType: "text", isNullable: "NO" },
    { name: "sort_order", dataType: "integer", isNullable: "NO" },
  ],
  research_document_sections: [
    { name: "id", dataType: "integer", isNullable: "NO" },
    { name: "document_slug", dataType: "text", isNullable: "NO" },
    { name: "heading", dataType: "text", isNullable: "NO" },
    { name: "body", dataType: "text", isNullable: "NO" },
    { name: "status", dataType: "text", isNullable: "NO" },
    { name: "sort_order", dataType: "integer", isNullable: "NO" },
  ],
  research_documents: [
    { name: "id", dataType: "integer", isNullable: "NO" },
    { name: "slug", dataType: "text", isNullable: "NO" },
    { name: "title", dataType: "text", isNullable: "NO" },
    { name: "phase", dataType: "text", isNullable: "NO" },
    { name: "summary", dataType: "text", isNullable: "NO" },
    { name: "sort_order", dataType: "integer", isNullable: "NO" },
  ],
  research_existing_projects: [
    { name: "id", dataType: "integer", isNullable: "NO" },
    { name: "name", dataType: "text", isNullable: "NO" },
    { name: "url", dataType: "text", isNullable: "NO" },
    { name: "last_activity", dataType: "text", isNullable: "NO" },
    { name: "license", dataType: "text", isNullable: "NO" },
    { name: "language", dataType: "text", isNullable: "NO" },
    { name: "architecture", dataType: "text", isNullable: "NO" },
    { name: "solves", dataType: "text", isNullable: "NO" },
    { name: "does_not_solve", dataType: "text", isNullable: "NO" },
    { name: "project_status", dataType: "text", isNullable: "NO" },
    { name: "reusable_code", dataType: "text", isNullable: "NO" },
    { name: "risks", dataType: "text", isNullable: "NO" },
    { name: "sort_order", dataType: "integer", isNullable: "NO" },
  ],
  research_experiments: [
    { name: "id", dataType: "integer", isNullable: "NO" },
    { name: "code", dataType: "text", isNullable: "NO" },
    { name: "title", dataType: "text", isNullable: "NO" },
    { name: "hypothesis", dataType: "text", isNullable: "NO" },
    { name: "method", dataType: "text", isNullable: "NO" },
    { name: "success_criteria", dataType: "text", isNullable: "NO" },
    { name: "status", dataType: "text", isNullable: "NO" },
    { name: "blocked_by", dataType: "text", isNullable: "NO" },
    { name: "sort_order", dataType: "integer", isNullable: "NO" },
  ],
  research_findings: [
    { name: "id", dataType: "integer", isNullable: "NO" },
    { name: "category", dataType: "text", isNullable: "NO" },
    { name: "claim", dataType: "text", isNullable: "NO" },
    { name: "status", dataType: "text", isNullable: "NO" },
    { name: "evidence", dataType: "text", isNullable: "NO" },
    { name: "implication", dataType: "text", isNullable: "NO" },
    { name: "sort_order", dataType: "integer", isNullable: "NO" },
  ],
  research_gate_questions: [
    { name: "id", dataType: "integer", isNullable: "NO" },
    { name: "question", dataType: "text", isNullable: "NO" },
    { name: "answer", dataType: "text", isNullable: "NO" },
    { name: "status", dataType: "text", isNullable: "NO" },
    { name: "experiment_needed", dataType: "text", isNullable: "NO" },
    { name: "sort_order", dataType: "integer", isNullable: "NO" },
  ],
  research_license_entries: [
    { name: "id", dataType: "integer", isNullable: "NO" },
    { name: "component", dataType: "text", isNullable: "NO" },
    { name: "license", dataType: "text", isNullable: "NO" },
    { name: "intended_use", dataType: "text", isNullable: "NO" },
    { name: "modification", dataType: "text", isNullable: "NO" },
    { name: "distribution", dataType: "text", isNullable: "NO" },
    { name: "risk", dataType: "text", isNullable: "NO" },
    { name: "legal_review_required", dataType: "boolean", isNullable: "NO" },
    { name: "notes", dataType: "text", isNullable: "NO" },
    { name: "sort_order", dataType: "integer", isNullable: "NO" },
  ],
  research_name_candidates: [
    { name: "id", dataType: "integer", isNullable: "NO" },
    { name: "name", dataType: "text", isNullable: "NO" },
    { name: "memorability", dataType: "text", isNullable: "NO" },
    { name: "skyrim_relation", dataType: "text", isNullable: "NO" },
    { name: "ck_relation", dataType: "text", isNullable: "NO" },
    { name: "searchability", dataType: "text", isNullable: "NO" },
    { name: "collisions", dataType: "text", isNullable: "NO" },
    { name: "length", dataType: "text", isNullable: "NO" },
    { name: "pronunciation", dataType: "text", isNullable: "NO" },
    { name: "visual_identity", dataType: "text", isNullable: "NO" },
    { name: "trademark_risk", dataType: "text", isNullable: "NO" },
    { name: "recommendation", dataType: "text", isNullable: "NO" },
    { name: "sort_order", dataType: "integer", isNullable: "NO" },
  ],
  research_sources: [
    { name: "id", dataType: "integer", isNullable: "NO" },
    { name: "title", dataType: "text", isNullable: "NO" },
    { name: "url", dataType: "text", isNullable: "NO" },
    { name: "publisher", dataType: "text", isNullable: "NO" },
    { name: "accessed_on", dataType: "text", isNullable: "NO" },
    { name: "verification", dataType: "text", isNullable: "NO" },
    { name: "notes", dataType: "text", isNullable: "NO" },
  ],
  research_use_cases: [
    { name: "id", dataType: "integer", isNullable: "NO" },
    { name: "name", dataType: "text", isNullable: "NO" },
    { name: "description", dataType: "text", isNullable: "NO" },
    { name: "mvp_inclusion", dataType: "text", isNullable: "NO" },
    { name: "risk_level", dataType: "text", isNullable: "NO" },
    { name: "preferred_backend", dataType: "text", isNullable: "NO" },
    { name: "sort_order", dataType: "integer", isNullable: "NO" },
  ],
  research_verdicts: [
    { name: "id", dataType: "integer", isNullable: "NO" },
    { name: "verdict", dataType: "text", isNullable: "NO" },
    { name: "rationale", dataType: "text", isNullable: "NO" },
    { name: "recommended_architecture", dataType: "text", isNullable: "NO" },
    { name: "primary_backend", dataType: "text", isNullable: "NO" },
    { name: "fallback_backend", dataType: "text", isNullable: "NO" },
    { name: "highest_technical_risk", dataType: "text", isNullable: "NO" },
    { name: "highest_legal_risk", dataType: "text", isNullable: "NO" },
    { name: "first_experiment", dataType: "text", isNullable: "NO" },
    { name: "mvp_candidate", dataType: "text", isNullable: "NO" },
    { name: "next_step", dataType: "text", isNullable: "NO" },
    { name: "created_at", dataType: "timestamp with time zone", isNullable: "YES" },
  ],
};

export async function verifyBaselineFingerprint(
  pool: Pool,
): Promise<BaselineFingerprintResult> {
  const missingTables: string[] = [];
  const missingColumns: string[] = [];
  const unexpectedCriticalColumns: string[] = [];
  const typeMismatches: string[] = [];
  const nullabilityMismatches: string[] = [];
  const primaryKeyMismatches: string[] = [];
  const constraintMismatches: string[] = [];
  const errors: string[] = [];

  // 1. Check table existence
  const tableResult = await pool.query<{ table_name: string }>(
    `SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'`,
  );
  const existingTables = new Set(tableResult.rows.map((r) => r.table_name));

  const expectedTableNames = Object.keys(EXPECTED_BASELINE_SCHEMA);
  for (const tableName of expectedTableNames) {
    if (!existingTables.has(tableName)) {
      missingTables.push(tableName);
      errors.push(`Missing table: ${tableName}`);
    }
  }

  // 2. Fetch all column definitions across public schema
  const columnResult = await pool.query<{
    table_name: string;
    column_name: string;
    data_type: string;
    is_nullable: string;
  }>(
    `SELECT table_name, column_name, data_type, is_nullable
     FROM information_schema.columns
     WHERE table_schema = 'public'
     ORDER BY table_name, ordinal_position`,
  );

  const columnsByTable = new Map<string, Map<string, { dataType: string; isNullable: string }>>();
  for (const row of columnResult.rows) {
    if (!columnsByTable.has(row.table_name)) {
      columnsByTable.set(row.table_name, new Map());
    }
    columnsByTable.get(row.table_name)!.set(row.column_name, {
      dataType: row.data_type,
      isNullable: row.is_nullable,
    });
  }

  // 3. Verify each expected table's column contract
  for (const [tableName, expectedCols] of Object.entries(EXPECTED_BASELINE_SCHEMA)) {
    const actualCols = columnsByTable.get(tableName);
    if (!actualCols) {
      // Missing table already recorded in step 1
      continue;
    }

    for (const expectedCol of expectedCols) {
      const actual = actualCols.get(expectedCol.name);
      if (!actual) {
        missingColumns.push(`${tableName}.${expectedCol.name}`);
        errors.push(`Table ${tableName} missing expected column: ${expectedCol.name}`);
        continue;
      }
      if (actual.dataType !== expectedCol.dataType) {
        typeMismatches.push(
          `${tableName}.${expectedCol.name}: expected ${expectedCol.dataType}, got ${actual.dataType}`,
        );
        errors.push(
          `Table ${tableName}.${expectedCol.name} data_type mismatch: expected ${expectedCol.dataType}, got ${actual.dataType}`,
        );
      }
      if (actual.isNullable !== expectedCol.isNullable) {
        nullabilityMismatches.push(
          `${tableName}.${expectedCol.name}: expected ${expectedCol.isNullable}, got ${actual.isNullable}`,
        );
        errors.push(
          `Table ${tableName}.${expectedCol.name} nullability mismatch: expected ${expectedCol.isNullable}, got ${actual.isNullable}`,
        );
      }
    }

    // Explicit constraint: distribution_authorization_status MUST NOT exist on pre-PR database
    if (tableName === "research_license_entries" && actualCols.has("distribution_authorization_status")) {
      unexpectedCriticalColumns.push("research_license_entries.distribution_authorization_status");
      errors.push(
        `Table research_license_entries already has distribution_authorization_status column. Pre-PR baseline adoption invalid.`,
      );
    }
  }

  // 4. Verify primary key constraints across all baseline tables
  const pkResult = await pool.query<{
    table_name: string;
    column_name: string;
  }>(
    `SELECT tc.table_name, kcu.column_name
     FROM information_schema.table_constraints tc
     JOIN information_schema.key_column_usage kcu
       ON tc.constraint_name = kcu.constraint_name
       AND tc.table_schema = kcu.table_schema
     WHERE tc.table_schema = 'public'
       AND tc.constraint_type = 'PRIMARY KEY'`,
  );
  const pksByTable = new Map<string, Set<string>>();
  for (const row of pkResult.rows) {
    if (!pksByTable.has(row.table_name)) {
      pksByTable.set(row.table_name, new Set());
    }
    pksByTable.get(row.table_name)!.add(row.column_name);
  }

  for (const tableName of expectedTableNames) {
    if (existingTables.has(tableName)) {
      const tablePks = pksByTable.get(tableName);
      if (!tablePks || !tablePks.has("id")) {
        primaryKeyMismatches.push(`${tableName}.id is not PRIMARY KEY`);
        errors.push(`Table ${tableName} missing PRIMARY KEY constraint on 'id'`);
      }
    }
  }

  // 5. Verify critical unique constraints (research_documents.slug UNIQUE)
  const uniqueResult = await pool.query<{
    table_name: string;
    column_name: string;
  }>(
    `SELECT tc.table_name, kcu.column_name
     FROM information_schema.table_constraints tc
     JOIN information_schema.key_column_usage kcu
       ON tc.constraint_name = kcu.constraint_name
       AND tc.table_schema = kcu.table_schema
     WHERE tc.table_schema = 'public'
       AND tc.constraint_type = 'UNIQUE'`,
  );
  const uniquesByTable = new Map<string, Set<string>>();
  for (const row of uniqueResult.rows) {
    if (!uniquesByTable.has(row.table_name)) {
      uniquesByTable.set(row.table_name, new Set());
    }
    uniquesByTable.get(row.table_name)!.add(row.column_name);
  }

  if (existingTables.has("research_documents")) {
    const docUniques = uniquesByTable.get("research_documents");
    if (!docUniques || !docUniques.has("slug")) {
      constraintMismatches.push("research_documents.slug missing UNIQUE constraint");
      errors.push("Table research_documents missing UNIQUE constraint on 'slug'");
    }
  }

  return {
    valid: errors.length === 0,
    missingTables,
    missingColumns,
    unexpectedCriticalColumns,
    typeMismatches,
    nullabilityMismatches,
    primaryKeyMismatches,
    constraintMismatches,
    errors,
  };
}

export async function adoptExistingDatabase(customDatabaseUrl?: string) {
  const databaseUrl = customDatabaseUrl || process.env.DATABASE_URL;
  if (!databaseUrl) {
    console.error("ERROR: DATABASE_URL environment variable is required for baseline adoption.");
    throw new Error("DATABASE_URL environment variable is required for baseline adoption.");
  }

  console.log("Verifying existing database for baseline adoption...");
  const pool = new Pool({ connectionString: databaseUrl });
  const db = drizzle(pool);

  try {
    // 1. Verify schema fingerprint across all 13 baseline tables, columns, types, PKs, and constraints
    const fingerprint = await verifyBaselineFingerprint(pool);
    if (!fingerprint.valid) {
      console.error("STATUS: DATABASE_BASELINE_MISMATCH");
      console.error("Cannot adopt baseline. Schema fingerprint mismatches:\n", fingerprint.errors.join("\n"));
      throw new Error(
        `Database baseline mismatch. Errors: ${fingerprint.errors.join("; ")}`,
      );
    }

    console.log("Schema fingerprint verified. All 13 expected baseline tables, columns, types, PKs, and unique constraints match.");

    // 2. Read baseline migration metadata
    const drizzleDir = path.resolve(process.cwd(), "drizzle");
    const journalPath = path.join(drizzleDir, "meta", "_journal.json");
    const baselineSqlPath = path.join(drizzleDir, "0000_baseline.sql");

    if (!fs.existsSync(journalPath) || !fs.existsSync(baselineSqlPath)) {
      throw new Error("Missing drizzle journal or 0000_baseline.sql in drizzle/ folder");
    }

    const journal = JSON.parse(fs.readFileSync(journalPath, "utf8"));
    const baselineEntry = journal.entries.find(
      (e: { tag: string }) => e.tag === "0000_baseline",
    );
    if (!baselineEntry) {
      throw new Error("0000_baseline entry not found in _journal.json");
    }

    const baselineSql = fs.readFileSync(baselineSqlPath, "utf8");
    const baselineHash = crypto.createHash("sha256").update(baselineSql).digest("hex");

    // 3. Ensure drizzle migration table exists and check baseline record & hash
    await pool.query(`CREATE SCHEMA IF NOT EXISTS "drizzle"`);
    await pool.query(`
      CREATE TABLE IF NOT EXISTS "drizzle"."__drizzle_migrations" (
        id SERIAL PRIMARY KEY,
        hash text NOT NULL,
        created_at bigint
      )
    `);

    const existingMigrations = await pool.query<{ hash: string; created_at: string }>(
      `SELECT hash, created_at FROM "drizzle"."__drizzle_migrations" WHERE created_at = $1`,
      [baselineEntry.when],
    );

    if (existingMigrations.rows.length === 0) {
      console.log(`Marking baseline migration 0000_baseline (${baselineEntry.when}) as applied...`);
      await pool.query(
        `INSERT INTO "drizzle"."__drizzle_migrations" ("hash", "created_at") VALUES ($1, $2)`,
        [baselineHash, baselineEntry.when],
      );
      console.log("Baseline marked successfully.");
    } else if (existingMigrations.rows.length === 1) {
      // Validate recorded hash against canonical baseline hash
      const recordedHash = existingMigrations.rows[0].hash;
      if (recordedHash !== baselineHash) {
        console.error("STATUS: DATABASE_BASELINE_MISMATCH");
        console.error(`Recorded baseline hash (${recordedHash}) does not match canonical hash (${baselineHash})`);
        throw new Error(
          `DATABASE_BASELINE_MISMATCH: Recorded 0000_baseline hash (${recordedHash}) mismatch with canonical hash (${baselineHash})`,
        );
      }
      console.log("Baseline migration 0000_baseline was already recorded with matching hash.");
    } else {
      // Multiple records with same baseline created_at -> fail closed
      console.error("STATUS: DATABASE_BASELINE_MISMATCH");
      console.error(`Multiple migration records (${existingMigrations.rows.length}) found for baseline timestamp ${baselineEntry.when}`);
      throw new Error(
        `DATABASE_BASELINE_MISMATCH: Multiple migration records (${existingMigrations.rows.length}) found for baseline timestamp ${baselineEntry.when}`,
      );
    }

    // 4. Run pending migrations (0001_add_distribution_authorization_status)
    console.log("Applying pending migrations...");
    await migrate(db, { migrationsFolder: drizzleDir });
    console.log("Database adoption and migration complete.");
  } finally {
    await pool.end();
  }
}

if (
  process.argv[1] &&
  (process.argv[1].endsWith("adopt.ts") || process.argv[1].endsWith("adopt.js"))
) {
  adoptExistingDatabase().catch((err) => {
    console.error("Adoption failed:", err);
    process.exit(1);
  });
}
