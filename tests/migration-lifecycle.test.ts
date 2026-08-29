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

    // 5. Verify serial sequence remains usable without collision
    const seqInsertRes = await pool.query<{ id: number }>(`
      INSERT INTO "research_license_entries"
      ("component", "license", "intended_use", "modification", "distribution", "risk", "legal_review_required", "distribution_authorization_status", "notes", "sort_order")
      VALUES
      ('Post-Migration Sequenced Component', 'MIT', 'Intended', 'Allowed', 'Allowed', 'Low', false, 'NOT_APPLICABLE', 'Sequence test', 7)
      RETURNING id
    `);
    const newId = seqInsertRes.rows[0].id;
    if (newId !== 7) {
      throw new Error(`Expected new auto-generated id to be 7, got ${newId}`);
    }
    console.log(`SERIAL SEQUENCE: Verified post-migration insert generated non-colliding ID ${newId}.`);

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

    // 6. Test rejection of invalid enum values
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

    // 7. Verify second migration is clean no-op
    await runMigrations(dbUrl);
    console.log("EXISTING DB ADOPTION: All checks passed.");
  } finally {
    await pool.end();
  }
}

async function instantiateBaselineSql(pool: Pool) {
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
}

async function assertNoBaselineRecorded(pool: Pool) {
  const migTableRes = await pool.query<{ exists: boolean }>(
    `SELECT EXISTS (
       SELECT FROM information_schema.tables
       WHERE table_schema = 'drizzle' AND table_name = '__drizzle_migrations'
     ) as exists`,
  );
  if (migTableRes.rows[0]?.exists) {
    const journal = JSON.parse(
      fs.readFileSync(path.resolve(process.cwd(), "drizzle/meta/_journal.json"), "utf8"),
    );
    const baselineEntry = journal.entries.find((e: { tag: string }) => e.tag === "0000_baseline");
    const migRows = await pool.query(
      `SELECT * FROM "drizzle"."__drizzle_migrations" WHERE created_at = $1`,
      [baselineEntry.when],
    );
    if (migRows.rows.length > 0) {
      throw new Error("False 0000_baseline record was created in drizzle.__drizzle_migrations on drifted DB");
    }
  }
}

async function runFingerprintDriftTests() {
  console.log("\n========================================================");
  console.log("RUNNING TESTS: Fingerprint Drift & Fail-Closed Scenarios");
  console.log("========================================================");

  // 1. Missing table
  {
    const dbName = "test_drift_missing_table";
    await createEmptyDatabase(dbName);
    const dbUrl = getDbUrl(dbName);
    const pool = new Pool({ connectionString: dbUrl });
    try {
      await pool.query(`CREATE TABLE "research_documents" (id serial PRIMARY KEY, slug text NOT NULL)`);
      let failed = false;
      try {
        await adoptExistingDatabase(dbUrl);
      } catch (err: any) {
        if (err.message.includes("Database baseline mismatch") && err.message.includes("Missing table")) {
          failed = true;
        } else {
          throw err;
        }
      }
      if (!failed) throw new Error("Adoption unexpectedly succeeded with missing tables");
      await assertNoBaselineRecorded(pool);
      console.log("DRIFT (Missing Table): Blocked fail-closed; no false baseline record created.");
    } finally {
      await pool.end();
    }
  }

  // 2. Missing required column
  {
    const dbName = "test_drift_missing_column";
    await createEmptyDatabase(dbName);
    const dbUrl = getDbUrl(dbName);
    const pool = new Pool({ connectionString: dbUrl });
    try {
      await instantiateBaselineSql(pool);
      await pool.query(`ALTER TABLE "research_license_entries" DROP COLUMN "modification"`);
      let failed = false;
      try {
        await adoptExistingDatabase(dbUrl);
      } catch (err: any) {
        if (err.message.includes("Database baseline mismatch") && err.message.includes("missing expected column: modification")) {
          failed = true;
        } else {
          throw err;
        }
      }
      if (!failed) throw new Error("Adoption unexpectedly succeeded with missing column");
      await assertNoBaselineRecorded(pool);
      console.log("DRIFT (Missing Column): Blocked fail-closed; no false baseline record created.");
    } finally {
      await pool.end();
    }
  }

  // 3. Column type mismatch
  {
    const dbName = "test_drift_type_mismatch";
    await createEmptyDatabase(dbName);
    const dbUrl = getDbUrl(dbName);
    const pool = new Pool({ connectionString: dbUrl });
    try {
      await instantiateBaselineSql(pool);
      await pool.query(`ALTER TABLE "research_license_entries" ALTER COLUMN "sort_order" TYPE text USING sort_order::text`);
      let failed = false;
      try {
        await adoptExistingDatabase(dbUrl);
      } catch (err: any) {
        if (err.message.includes("Database baseline mismatch") && err.message.includes("data_type mismatch")) {
          failed = true;
        } else {
          throw err;
        }
      }
      if (!failed) throw new Error("Adoption unexpectedly succeeded with column type mismatch");
      await assertNoBaselineRecorded(pool);
      console.log("DRIFT (Type Mismatch): Blocked fail-closed; no false baseline record created.");
    } finally {
      await pool.end();
    }
  }

  // 4. Column nullability mismatch
  {
    const dbName = "test_drift_nullability_mismatch";
    await createEmptyDatabase(dbName);
    const dbUrl = getDbUrl(dbName);
    const pool = new Pool({ connectionString: dbUrl });
    try {
      await instantiateBaselineSql(pool);
      await pool.query(`ALTER TABLE "research_license_entries" ALTER COLUMN "notes" DROP NOT NULL`);
      let failed = false;
      try {
        await adoptExistingDatabase(dbUrl);
      } catch (err: any) {
        if (err.message.includes("Database baseline mismatch") && err.message.includes("nullability mismatch")) {
          failed = true;
        } else {
          throw err;
        }
      }
      if (!failed) throw new Error("Adoption unexpectedly succeeded with nullability mismatch");
      await assertNoBaselineRecorded(pool);
      console.log("DRIFT (Nullability Mismatch): Blocked fail-closed; no false baseline record created.");
    } finally {
      await pool.end();
    }
  }

  // 5. Missing Primary Key on research_license_entries
  {
    const dbName = "test_drift_missing_pk";
    await createEmptyDatabase(dbName);
    const dbUrl = getDbUrl(dbName);
    const pool = new Pool({ connectionString: dbUrl });
    try {
      await instantiateBaselineSql(pool);
      await pool.query(`ALTER TABLE "research_license_entries" DROP CONSTRAINT "research_license_entries_pkey"`);
      let failed = false;
      try {
        await adoptExistingDatabase(dbUrl);
      } catch (err: any) {
        if (err.message.includes("Database baseline mismatch") && err.message.includes("missing PRIMARY KEY constraint")) {
          failed = true;
        } else {
          throw err;
        }
      }
      if (!failed) throw new Error("Adoption unexpectedly succeeded with missing PRIMARY KEY");
      await assertNoBaselineRecorded(pool);
      console.log("DRIFT (Missing Primary Key): Blocked fail-closed; no false baseline record created.");
    } finally {
      await pool.end();
    }
  }

  // 6. Pre-existing distribution_authorization_status column (Critical Negative Invariant)
  {
    const dbName = "test_drift_pre_existing_status";
    await createEmptyDatabase(dbName);
    const dbUrl = getDbUrl(dbName);
    const pool = new Pool({ connectionString: dbUrl });
    try {
      await instantiateBaselineSql(pool);
      await pool.query(`ALTER TABLE "research_license_entries" ADD COLUMN "distribution_authorization_status" text`);
      let failed = false;
      try {
        await adoptExistingDatabase(dbUrl);
      } catch (err: any) {
        if (err.message.includes("Database baseline mismatch") && err.message.includes("already has distribution_authorization_status column")) {
          failed = true;
        } else {
          throw err;
        }
      }
      if (!failed) throw new Error("Adoption unexpectedly succeeded with pre-existing distribution_authorization_status");
      await assertNoBaselineRecorded(pool);
      console.log("DRIFT (Pre-existing Status Column): Blocked fail-closed; negative invariant enforced.");
    } finally {
      await pool.end();
    }
  }

  // 7. Missing Unique Constraint on research_documents.slug
  {
    const dbName = "test_drift_missing_unique";
    await createEmptyDatabase(dbName);
    const dbUrl = getDbUrl(dbName);
    const pool = new Pool({ connectionString: dbUrl });
    try {
      await instantiateBaselineSql(pool);
      await pool.query(`ALTER TABLE "research_documents" DROP CONSTRAINT "research_documents_slug_unique"`);
      let failed = false;
      try {
        await adoptExistingDatabase(dbUrl);
      } catch (err: any) {
        if (err.message.includes("Database baseline mismatch") && err.message.includes("missing UNIQUE constraint")) {
          failed = true;
        } else {
          throw err;
        }
      }
      if (!failed) throw new Error("Adoption unexpectedly succeeded with missing UNIQUE constraint");
      await assertNoBaselineRecorded(pool);
      console.log("DRIFT (Missing Unique Constraint): Blocked fail-closed; slug unique enforced.");
    } finally {
      await pool.end();
    }
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
    await instantiateBaselineSql(pool);

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

    // Ensure 0001 was not applied
    const colRes = await pool.query(
      `SELECT column_name FROM information_schema.columns
       WHERE table_schema = 'public' AND table_name = 'research_license_entries'
         AND column_name = 'distribution_authorization_status'`,
    );
    if (colRes.rows.length > 0) {
      throw new Error("Migration 0001 was applied despite hash mismatch");
    }

    console.log("HASH MISMATCH: Successfully blocked adoption on corrupted baseline hash.");
  } finally {
    await pool.end();
  }
}

async function runDuplicateHistoryNegativeTest() {
  console.log("\n========================================================");
  console.log("RUNNING TEST: Duplicate Baseline History Fail-Closed Test");
  console.log("========================================================");

  const dbName = "test_duplicate_history_db";
  await createEmptyDatabase(dbName);
  const dbUrl = getDbUrl(dbName);

  const pool = new Pool({ connectionString: dbUrl });
  try {
    // 1. Instantiate baseline schema
    await instantiateBaselineSql(pool);

    // 2. Insert duplicate migration records in drizzle.__drizzle_migrations
    const journal = JSON.parse(
      fs.readFileSync(path.resolve(process.cwd(), "drizzle/meta/_journal.json"), "utf8"),
    );
    const baselineEntry = journal.entries.find((e: { tag: string }) => e.tag === "0000_baseline");
    const baselineSql = fs.readFileSync(
      path.resolve(process.cwd(), "drizzle/0000_baseline.sql"),
      "utf8",
    );
    const canonicalHash = crypto.createHash("sha256").update(baselineSql).digest("hex");

    await pool.query(`CREATE SCHEMA IF NOT EXISTS "drizzle"`);
    await pool.query(`
      CREATE TABLE "drizzle"."__drizzle_migrations" (
        id SERIAL PRIMARY KEY,
        hash text NOT NULL,
        created_at bigint
      )
    `);
    await pool.query(
      `INSERT INTO "drizzle"."__drizzle_migrations" ("hash", "created_at") VALUES ($1, $2), ($3, $4)`,
      [canonicalHash, baselineEntry.when, canonicalHash, baselineEntry.when],
    );

    let duplicateBlocked = false;
    try {
      await adoptExistingDatabase(dbUrl);
    } catch (err: any) {
      if (err.message.includes("DATABASE_BASELINE_MISMATCH: Multiple migration records")) {
        duplicateBlocked = true;
      } else {
        throw err;
      }
    }

    if (!duplicateBlocked) {
      throw new Error("Database adoption succeeded despite duplicate baseline records");
    }

    // Ensure 0001 was not applied
    const colRes = await pool.query(
      `SELECT column_name FROM information_schema.columns
       WHERE table_schema = 'public' AND table_name = 'research_license_entries'
         AND column_name = 'distribution_authorization_status'`,
    );
    if (colRes.rows.length > 0) {
      throw new Error("Migration 0001 was applied despite duplicate baseline records");
    }

    console.log("DUPLICATE HISTORY: Successfully blocked adoption on duplicate migration records.");
  } finally {
    await pool.end();
  }
}

async function main() {
  try {
    await runFreshDbTest();
    await runExistingDbAdoptionTest();
    await runFingerprintDriftTests();
    await runHashMismatchNegativeTest();
    await runDuplicateHistoryNegativeTest();
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
