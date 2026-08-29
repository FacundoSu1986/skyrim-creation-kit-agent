import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { drizzle } from "drizzle-orm/node-postgres";
import { migrate } from "drizzle-orm/node-postgres/migrator";
import { Pool } from "pg";
import { adoptExistingDatabase, verifyBaselineFingerprint } from "../src/db/adopt";
import { runMigrations } from "../src/db/migrate";

const baseDatabaseUrl = process.env.TEST_DATABASE_URL || process.env.DATABASE_URL || "postgresql://postgres:password@127.0.0.1:5432/postgres";

function getDbUrl(dbName: string): string {
  const url = new URL(baseDatabaseUrl);
  url.pathname = `/${dbName}`;
  return url.toString();
}

async function createEmptyDatabase(dbName: string) {
  const adminPool = new Pool({ connectionString: baseDatabaseUrl });
  try {
    await adminPool.query(`DROP DATABASE IF EXISTS ${dbName}`);
    await adminPool.query(`CREATE DATABASE ${dbName}`);
  } finally {
    await adminPool.end();
  }
}

async function runFreshDbTest() {
  console.log("\n==========================================");
  console.log("RUNNING TEST: Fresh DB Migration Lifecycle");
  console.log("==========================================");

  const dbName = "test_fresh_db";
  await createEmptyDatabase(dbName);
  const dbUrl = getDbUrl(dbName);

  // Set env var for migration runner
  process.env.DATABASE_URL = dbUrl;

  // 1. Run migrations
  await runMigrations();

  // 2. Verify tables and enum exist
  const pool = new Pool({ connectionString: dbUrl });
  try {
    const fingerprint = await verifyBaselineFingerprint(pool);
    if (!fingerprint.valid) {
      throw new Error(`Fresh DB missing expected tables: ${fingerprint.missingTables.join(", ")}`);
    }

    const colRes = await pool.query(
      `SELECT column_name, data_type, udt_name, is_nullable, column_default 
       FROM information_schema.columns 
       WHERE table_name = 'research_license_entries' AND column_name = 'distribution_authorization_status'`,
    );
    if (colRes.rows.length === 0) {
      throw new Error("Column distribution_authorization_status missing in fresh DB");
    }
    const col = colRes.rows[0];
    if (col.udt_name !== "distribution_authorization_status") {
      throw new Error(`Expected udt_name distribution_authorization_status, got ${col.udt_name}`);
    }
    if (col.is_nullable !== "NO") {
      throw new Error("Expected column to be NOT NULL");
    }

    // 3. Verify second migration is clean no-op
    await runMigrations();
    console.log("FRESH DB: All checks passed.");
  } finally {
    await pool.end();
  }
}

async function runExistingDbAdoptionTest() {
  console.log("\n========================================================");
  console.log("RUNNING TEST: Existing Pre-Migration DB Adoption & Backfill");
  console.log("========================================================");

  const dbName = "test_existing_db";
  await createEmptyDatabase(dbName);
  const dbUrl = getDbUrl(dbName);

  const pool = new Pool({ connectionString: dbUrl });
  try {
    // 1. Instantiate pre-PR schema by executing 0000_baseline.sql directly
    const baselineSql = fs.readFileSync(path.resolve(process.cwd(), "drizzle/0000_baseline.sql"), "utf8");
    const stmts = baselineSql.split("--> statement-breakpoint");
    for (const stmt of stmts) {
      if (stmt.trim()) {
        await pool.query(stmt);
      }
    }

    // 2. Insert sample rows into pre-PR table (without distribution_authorization_status)
    await pool.query(`
      INSERT INTO "research_license_entries" 
      ("component", "license", "intended_use", "modification", "distribution", "risk", "legal_review_required", "notes", "sort_order")
      VALUES
      ('Mutagen / Synthesis / Spriggit', 'GPL-3.0-only', 'Intended', 'Allowed', 'Source required', 'High', false, 'Notes', 1),
      ('Creation Kit Platform Extended', 'LGPLv3', 'Intended', 'Allowed', 'No bundle', 'Critical', true, 'Notes', 2),
      ('esper / esper-js / esper-cpp / balsa', 'MIT', 'Intended', 'Allowed', 'Allowed', 'Medium', true, 'Notes', 3),
      ('Skyrim Special Edition / Anniversary Edition', 'EULA', 'Intended', 'Forbidden', 'Forbidden', 'Critical', true, 'Notes', 4),
      ('LOOT / libloot', 'GPL-3.0', 'Intended', 'None', 'None', 'Low', false, 'Notes', 5),
      ('Custom Operator Tool (Unknown)', 'Custom', 'Intended', 'None', 'None', 'Unknown', false, 'Unknown row', 6)
    `);

    console.log("Inserted 6 sample rows into pre-PR database without migration history.");

    // Verify baseline fingerprint before adoption
    const preFingerprint = await verifyBaselineFingerprint(pool);
    if (!preFingerprint.valid) {
      throw new Error("Pre-PR schema instantiation failed fingerprint verification");
    }

    // 3. Adopt existing database
    process.env.DATABASE_URL = dbUrl;
    await adoptExistingDatabase();

    // 4. Verify post-migration state and semantic backfill
    const rows = await pool.query<{
      component: string;
      distribution_authorization_status: string;
      legal_review_required: boolean;
    }>(`SELECT component, distribution_authorization_status, legal_review_required FROM "research_license_entries" ORDER BY sort_order`);

    if (rows.rows.length !== 6) {
      throw new Error(`Expected 6 preserved rows, got ${rows.rows.length}`);
    }

    const rowMap = new Map(rows.rows.map((r) => [r.component, r.distribution_authorization_status]));

    // Assert semantic backfill
    if (rowMap.get("Mutagen / Synthesis / Spriggit") !== "LEGAL_REVIEW_REQUIRED") {
      throw new Error(`Expected Mutagen to be LEGAL_REVIEW_REQUIRED, got ${rowMap.get("Mutagen / Synthesis / Spriggit")}`);
    }
    if (rowMap.get("Creation Kit Platform Extended") !== "LEGAL_REVIEW_REQUIRED") {
      throw new Error(`Expected CKPE to be LEGAL_REVIEW_REQUIRED, got ${rowMap.get("Creation Kit Platform Extended")}`);
    }
    if (rowMap.get("esper / esper-js / esper-cpp / balsa") !== "LEGAL_REVIEW_REQUIRED") {
      throw new Error(`Expected esper to be LEGAL_REVIEW_REQUIRED, got ${rowMap.get("esper / esper-js / esper-cpp / balsa")}`);
    }
    if (rowMap.get("Skyrim Special Edition / Anniversary Edition") !== "DESCARTADO") {
      throw new Error(`Expected Skyrim to be DESCARTADO, got ${rowMap.get("Skyrim Special Edition / Anniversary Edition")}`);
    }
    if (rowMap.get("LOOT / libloot") !== "NOT_APPLICABLE") {
      throw new Error(`Expected LOOT to be NOT_APPLICABLE, got ${rowMap.get("LOOT / libloot")}`);
    }
    // Fail-closed check for unknown row
    if (rowMap.get("Custom Operator Tool (Unknown)") !== "LEGAL_REVIEW_REQUIRED") {
      throw new Error(`Expected unknown row to fail-closed to LEGAL_REVIEW_REQUIRED, got ${rowMap.get("Custom Operator Tool (Unknown)")}`);
    }

    console.log("SEMANTIC BACKFILL: All rows verified with exact expected legal statuses.");

    // 5. Test rejection of invalid enum values
    let invalidRejected = false;
    try {
      await pool.query(`
        INSERT INTO "research_license_entries" 
        ("component", "license", "intended_use", "modification", "distribution", "risk", "legal_review_required", "distribution_authorization_status", "notes", "sort_order")
        VALUES
        ('Bad Row', 'MIT', 'Intended', 'Allowed', 'Allowed', 'Low', false, 'INVALID_ENUM_VALUE', 'Notes', 99)
      `);
    } catch (err: any) {
      if (err.message.includes('invalid input value for enum distribution_authorization_status')) {
        invalidRejected = true;
      } else {
        throw err;
      }
    }

    if (!invalidRejected) {
      throw new Error("PostgreSQL failed to reject invalid enum value");
    }
    console.log("DATABASE CONSTRAINT: Invalid enum value successfully rejected.");

    // 6. Verify second migration is clean no-op
    await runMigrations();
    console.log("EXISTING DB ADOPTION: All checks passed.");
  } finally {
    await pool.end();
  }
}

async function main() {
  try {
    await runFreshDbTest();
    await runExistingDbAdoptionTest();
    console.log("\n==========================================");
    console.log("ALL MIGRATION LIFECYCLE TESTS PASSED (100%)");
    console.log("==========================================\n");
    process.exit(0);
  } catch (err) {
    console.error("Migration test suite failed:", err);
    process.exit(1);
  }
}

main();
