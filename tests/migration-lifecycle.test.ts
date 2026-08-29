import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { drizzle } from "drizzle-orm/node-postgres";
import { Pool } from "pg";
import {
  EXPECTED_BASELINE_SCHEMA,
  adoptExistingDatabase,
  verifyBaselineFingerprint,
} from "../src/db/adopt";
import { runMigrations } from "../src/db/migrate";

const baseDatabaseUrl =
  process.env.TEST_DATABASE_URL ||
  process.env.DATABASE_URL ||
  "postgresql://postgres:password@127.0.0.1:5432/postgres";

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

  // 1. Run migrations on fresh database
  await runMigrations(dbUrl);

  // 2. Verify tables and enum exist
  const pool = new Pool({ connectionString: dbUrl });
  try {
    const tableRes = await pool.query<{ table_name: string }>(
      `SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'`,
    );
    const tableNames = new Set(tableRes.rows.map((r) => r.table_name));
    for (const expectedTable of Object.keys(EXPECTED_BASELINE_SCHEMA)) {
      if (!tableNames.has(expectedTable)) {
        throw new Error(`Fresh DB missing table: ${expectedTable}`);
      }
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
    await runMigrations(dbUrl);
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
    const baselineSql = fs.readFileSync(
      path.resolve(process.cwd(), "drizzle/0000_baseline.sql"),
      "utf8",
    );
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

    // Capture pre-migration primary keys
    const preRows = await pool.query<{ id: number; component: string }>(
      `SELECT id, component FROM "research_license_entries" ORDER BY sort_order`,
    );
    const preIdMap = new Map<string, number>();
    for (const row of preRows.rows) {
      preIdMap.set(row.component, row.id);
    }
    console.log("Pre-migration rows inserted. IDs recorded:", Array.from(preIdMap.entries()));

    // Verify deep schema fingerprint before adoption
    const preFingerprint = await verifyBaselineFingerprint(pool);
    if (!preFingerprint.valid) {
      throw new Error(`Pre-PR schema fingerprint mismatch: ${preFingerprint.errors.join("; ")}`);
    }
    console.log("Pre-PR deep schema fingerprint validated (13 tables, all columns & types match).");

    // 3. Adopt existing database
    await adoptExistingDatabase(dbUrl);

    // 4. Verify post-migration state, semantic backfill, and strict PK preservation
    const postRows = await pool.query<{
      id: number;
      component: string;
      distribution_authorization_status: string;
      legal_review_required: boolean;
    }>(
      `SELECT id, component, distribution_authorization_status, legal_review_required FROM "research_license_entries" ORDER BY sort_order`,
    );

    if (postRows.rows.length !== 6) {
      throw new Error(`Expected 6 preserved rows, got ${postRows.rows.length}`);
    }

    const rowMap = new Map(
      postRows.rows.map((r) => [r.component, r.distribution_authorization_status]),
    );

    // Explicit Primary Key Preservation assertion
    for (const postRow of postRows.rows) {
      const expectedId = preIdMap.get(postRow.component);
      if (expectedId === undefined) {
        throw new Error(`Unexpected post-migration component: ${postRow.component}`);
      }
      if (postRow.id !== expectedId) {
        throw new Error(
          `Primary key changed for ${postRow.component}: pre-id=${expectedId}, post-id=${postRow.id}`,
        );
      }
    }
    console.log("PRIMARY KEY PRESERVATION: Verified 100% (same component -> same id pre/post).");

    // Assert semantic backfill
    if (rowMap.get("Mutagen / Synthesis / Spriggit") !== "LEGAL_REVIEW_REQUIRED") {
      throw new Error(
        `Expected Mutagen to be LEGAL_REVIEW_REQUIRED, got ${rowMap.get("Mutagen / Synthesis / Spriggit")}`,
      );
    }
    if (rowMap.get("Creation Kit Platform Extended") !== "LEGAL_REVIEW_REQUIRED") {
      throw new Error(
        `Expected CKPE to be LEGAL_REVIEW_REQUIRED, got ${rowMap.get("Creation Kit Platform Extended")}`,
      );
    }
    if (rowMap.get("esper / esper-js / esper-cpp / balsa") !== "LEGAL_REVIEW_REQUIRED") {
      throw new Error(
        `Expected esper to be LEGAL_REVIEW_REQUIRED, got ${rowMap.get("esper / esper-js / esper-cpp / balsa")}`,
      );
    }
    if (rowMap.get("Skyrim Special Edition / Anniversary Edition") !== "DESCARTADO") {
      throw new Error(
        `Expected Skyrim to be DESCARTADO, got ${rowMap.get("Skyrim Special Edition / Anniversary Edition")}`,
      );
    }
    if (rowMap.get("LOOT / libloot") !== "NOT_APPLICABLE") {
      throw new Error(`Expected LOOT to be NOT_APPLICABLE, got ${rowMap.get("LOOT / libloot")}`);
    }
    // Fail-closed check for unknown row
    if (rowMap.get("Custom Operator Tool (Unknown)") !== "LEGAL_REVIEW_REQUIRED") {
      throw new Error(
        `Expected unknown row to fail-closed to LEGAL_REVIEW_REQUIRED, got ${rowMap.get("Custom Operator Tool (Unknown)")}`,
      );
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
      if (err.message.includes("invalid input value for enum distribution_authorization_status")) {
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
    await runMigrations(dbUrl);
    console.log("EXISTING DB ADOPTION: All checks passed.");
  } finally {
    await pool.end();
  }
}

async function runFingerprintMismatchNegativeTest() {
  console.log("\n========================================================");
  console.log("RUNNING TEST: Fingerprint Mismatch Fail-Closed Test");
  console.log("========================================================");

  const dbName = "test_mismatch_db";
  await createEmptyDatabase(dbName);
  const dbUrl = getDbUrl(dbName);

  const pool = new Pool({ connectionString: dbUrl });
  try {
    // Create incomplete database with 1 missing table
    await pool.query(`CREATE TABLE "research_documents" (id serial PRIMARY KEY, slug text NOT NULL)`);

    let adoptionFailed = false;
    try {
      await adoptExistingDatabase(dbUrl);
    } catch (err: any) {
      if (err.message.includes("Database baseline mismatch")) {
        adoptionFailed = true;
      } else {
        throw err;
      }
    }

    if (!adoptionFailed) {
      throw new Error("Database adoption succeeded on mismatched schema");
    }
    console.log("FINGERPRINT MISMATCH: Successfully blocked adoption on incomplete schema.");
  } finally {
    await pool.end();
  }
}

async function runHashMismatchNegativeTest() {
  console.log("\n========================================================");
  console.log("RUNNING TEST: Baseline Hash Mismatch Fail-Closed Test");
  console.log("========================================================");

  const dbName = "test_hash_mismatch_db";
  await createEmptyDatabase(dbName);
  const dbUrl = getDbUrl(dbName);

  const pool = new Pool({ connectionString: dbUrl });
  try {
    // 1. Instantiate baseline schema
    const baselineSql = fs.readFileSync(
      path.resolve(process.cwd(), "drizzle/0000_baseline.sql"),
      "utf8",
    );
    for (const stmt of baselineSql.split("--> statement-breakpoint")) {
      if (stmt.trim()) await pool.query(stmt);
    }

    // 2. Insert corrupted migration hash in drizzle.__drizzle_migrations
    const journal = JSON.parse(
      fs.readFileSync(path.resolve(process.cwd(), "drizzle/meta/_journal.json"), "utf8"),
    );
    const baselineEntry = journal.entries.find((e: { tag: string }) => e.tag === "0000_baseline");
    await pool.query(`CREATE SCHEMA IF NOT EXISTS "drizzle"`);
    await pool.query(`
      CREATE TABLE "drizzle"."__drizzle_migrations" (
        id SERIAL PRIMARY KEY,
        hash text NOT NULL,
        created_at bigint
      )
    `);
    await pool.query(
      `INSERT INTO "drizzle"."__drizzle_migrations" ("hash", "created_at") VALUES ($1, $2)`,
      ["corrupted_fake_hash_12345", baselineEntry.when],
    );

    let hashMismatchBlocked = false;
    try {
      await adoptExistingDatabase(dbUrl);
    } catch (err: any) {
      if (err.message.includes("DATABASE_BASELINE_MISMATCH: Recorded 0000_baseline hash")) {
        hashMismatchBlocked = true;
      } else {
        throw err;
      }
    }

    if (!hashMismatchBlocked) {
      throw new Error("Database adoption succeeded despite corrupted baseline hash");
    }
    console.log("HASH MISMATCH: Successfully blocked adoption on corrupted baseline hash.");
  } finally {
    await pool.end();
  }
}

async function main() {
  try {
    await runFreshDbTest();
    await runExistingDbAdoptionTest();
    await runFingerprintMismatchNegativeTest();
    await runHashMismatchNegativeTest();
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
