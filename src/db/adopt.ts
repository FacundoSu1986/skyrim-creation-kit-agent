import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import dotenv from "dotenv";
import { drizzle } from "drizzle-orm/node-postgres";
import { migrate } from "drizzle-orm/node-postgres/migrator";
import { Pool } from "pg";

dotenv.config();

const databaseUrl = process.env.DATABASE_URL;

if (!databaseUrl) {
  console.error("ERROR: DATABASE_URL environment variable is required for baseline adoption.");
  process.exit(1);
}

export const EXPECTED_BASELINE_TABLES = [
  "research_architecture_options",
  "research_capabilities",
  "research_document_sections",
  "research_documents",
  "research_existing_projects",
  "research_experiments",
  "research_findings",
  "research_gate_questions",
  "research_license_entries",
  "research_name_candidates",
  "research_sources",
  "research_use_cases",
  "research_verdicts",
] as const;

export async function verifyBaselineFingerprint(
  pool: Pool,
): Promise<{ valid: boolean; missingTables: string[] }> {
  const result = await pool.query<{ table_name: string }>(
    `SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'`,
  );
  const existingTables = new Set(result.rows.map((r) => r.table_name));
  const missingTables = EXPECTED_BASELINE_TABLES.filter((t) => !existingTables.has(t));

  return {
    valid: missingTables.length === 0,
    missingTables,
  };
}

export async function adoptExistingDatabase() {
  console.log("Verifying existing database for baseline adoption...");
  const pool = new Pool({ connectionString: databaseUrl });
  const db = drizzle(pool);

  try {
    // 1. Verify schema fingerprint
    const fingerprint = await verifyBaselineFingerprint(pool);
    if (!fingerprint.valid) {
      console.error("STATUS: DATABASE_BASELINE_MISMATCH");
      console.error("Cannot adopt baseline. Missing expected tables:", fingerprint.missingTables);
      throw new Error(
        `Database baseline mismatch. Missing tables: ${fingerprint.missingTables.join(", ")}`,
      );
    }

    console.log("Schema fingerprint verified. All 13 expected baseline tables exist.");

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

    // 3. Ensure drizzle migration table exists and check if baseline is recorded
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
    } else {
      console.log("Baseline migration 0000_baseline was already recorded.");
    }

    // 4. Run any remaining migrations (0001_add_distribution_authorization_status)
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
