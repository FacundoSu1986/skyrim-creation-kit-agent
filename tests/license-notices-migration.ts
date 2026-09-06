import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { licenseRows } from "../src/lib/research/licenses";
import { documentSectionRows } from "../src/lib/research/documents";

interface SqlClient {
  query(sql: string, values?: unknown[]): Promise<{ rows: Record<string, unknown>[] }>;
}

// Run against an empty, disposable PostgreSQL database (or embedded PostgreSQL for local QA).
export async function verifyLicenseNoticesMigration(client: SqlClient) {
  const apply = async (name: string) => {
    const sql = fs.readFileSync(path.resolve("drizzle", name), "utf8");
    for (const statement of sql.split("--> statement-breakpoint")) {
      if (statement.trim()) await client.query(statement);
    }
  };
  await apply("0000_baseline.sql");
  await apply("0001_add_distribution_authorization_status.sql");
  await apply("0002_licensing_notices.sql");
  assert.equal((await client.query("SELECT * FROM research_license_entries")).rows.length, 0,
    "A fresh desk must remain empty for the normal seed, avoiding duplicate rows");

  await client.query(`INSERT INTO research_license_entries
    (component, license, intended_use, modification, distribution, risk,
     legal_review_required, distribution_authorization_status, notes, sort_order)
    VALUES
    ('Mutagen / Synthesis / Spriggit', 'GPL-3.0-only', 'Keep use', 'Keep modification',
     'Keep distribution', 'Keep risk', false, 'LEGAL_REVIEW_REQUIRED', 'Old notes', 1),
    ('This research portal (Next.js app)', 'To be chosen', 'Keep use', 'Keep modification',
     'Keep distribution', 'Low', false, 'NOT_APPLICABLE', 'Old notes', 2),
    ('Operator custom row', 'Custom', 'Custom', 'Custom', 'Custom', 'Custom',
     true, 'LEGAL_REVIEW_REQUIRED', 'Preserve this exactly', 3)`);
  const before = (await client.query("SELECT * FROM research_license_entries ORDER BY id")).rows;
  // Use the same seeded-state sentinel as seedResearch, without a live app connection.
  await client.query(`INSERT INTO research_verdicts
    (verdict, rationale, recommended_architecture, primary_backend, fallback_backend,
     highest_technical_risk, highest_legal_risk, first_experiment, mvp_candidate, next_step)
    VALUES ('fixture', 'fixture', 'fixture', 'fixture', 'fixture', 'fixture', 'fixture',
     'fixture', 'fixture', 'fixture')`);
  const currentBody = documentSectionRows.find(
    row => row.documentSlug === "licensing" && row.heading === "Three different acts",
  )!.body;
  const oldParagraph = "These are not equivalent. Executing the user's PapyrusCompiler is aligned with how CK itself works. Linking Mutagen makes our worker GPL-3.0. Distributing CreationKit.exe or vanilla .psc is forbidden.";
  await client.query(`INSERT INTO research_document_sections
    (document_slug, heading, body, status, sort_order) VALUES ('licensing',
     'Three different acts', $1, 'VERIFICADO', 1)`, ["Operator preface\n" + oldParagraph]);

  await apply("0002_licensing_notices.sql");
  const after = (await client.query("SELECT * FROM research_license_entries ORDER BY id")).rows;
  assert.equal(after.length, 7);
  assert.deepEqual(after[2], before[2], "Custom rows must remain intact");
  for (let i = 0; i < 2; i++) {
    assert.equal(after[i].id, before[i].id, "Existing IDs must survive");
    assert.equal(after[i].intended_use, before[i].intended_use);
    assert.equal(after[i].distribution, before[i].distribution);
    const expected = licenseRows.find(row => row.component === after[i].component)!;
    assert.equal(after[i].notes, expected.notes);
    assert.equal(after[i].distribution_authorization_status, expected.distributionAuthorizationStatus);
  }
  const fields = {
    component: "component", license: "license", intendedUse: "intended_use",
    modification: "modification", distribution: "distribution", risk: "risk",
    legalReviewRequired: "legal_review_required",
    distributionAuthorizationStatus: "distribution_authorization_status", notes: "notes",
  } as const;
  for (const expected of licenseRows.slice(-4)) {
    const actual = after.find(row => row.component === expected.component)!;
    assert.ok(actual, `Missing dependency row ${expected.component}`);
    for (const [sourceKey, column] of Object.entries(fields)) {
      assert.equal(actual[column], expected[sourceKey as keyof typeof fields]);
    }
  }
  const body = (await client.query("SELECT body FROM research_document_sections")).rows[0].body;
  const correctedParagraph = currentBody.split("\n\n")[1];
  assert.equal(body, "Operator preface\n" + correctedParagraph);
  await apply("0002_licensing_notices.sql");
  assert.deepEqual((await client.query("SELECT * FROM research_license_entries ORDER BY id")).rows, after,
    "Reapplying the content migration must neither duplicate rows nor alter IDs");
  console.log("LICENSING NOTICES: fresh seed boundary, populated update, custom data, source parity and repeat safety passed.");
}
