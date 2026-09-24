/**
 * Desk/docs consistency check.
 *
 * Why this exists
 * ---------------
 * The Discovery Desk mirrors research state in `src/lib/research/experiments.ts`
 * while the canonical record lives in `docs/research/experiments.md` and
 * `docs/status.md`. Nothing enforced agreement, so the desk drifted: POC-003 was
 * presented as "Compiler binary not present here" (a missing-environment blocker)
 * after it had actually been executed twice on Windows and failed two mandatory
 * criteria. In a repository whose whole product is honest status reporting, an
 * unverified mirror of the status is a defect, not a cosmetic issue.
 *
 * This test does not restate any status. It parses the canonical documents, parses
 * the desk data, and asserts they agree. Update the documents, then the desk.
 *
 * Run: npx tsx tests/desk-docs-consistency.test.ts
 */
import fs from "node:fs";
import path from "node:path";
import { experimentRows } from "../src/lib/research/experiments";
import { EVIDENCE_STATUSES } from "../src/lib/status";
import { verdictRow } from "../src/lib/research/verdict";

const ROOT = path.resolve(__dirname, "..");
const failures: string[] = [];
const checks: string[] = [];

function fail(message: string) {
  failures.push(message);
}

function ok(message: string) {
  checks.push(message);
}

/** Canonical status vocabulary, longest first so "NO VERIFICADO" wins over "VERIFICADO". */
const VOCABULARY: string[] = [...EVIDENCE_STATUSES].sort((a, b) => b.length - a.length);

function firstStatus(text: string): string | null {
  let best: { status: string; index: number } | null = null;
  for (const status of VOCABULARY) {
    const index = text.indexOf(status);
    if (index === -1) continue;
    if (best === null || index < best.index || (index === best.index && status.length > best.status.length)) {
      best = { status, index };
    }
  }
  return best?.status ?? null;
}

/** Parse `## CODE — title` sections of the canonical experiments index. */
function parseDocumentedStatuses(): Map<string, string> {
  const file = path.join(ROOT, "docs/research/experiments.md");
  if (!fs.existsSync(file)) {
    fail(`missing canonical document: docs/research/experiments.md`);
    return new Map();
  }
  const statuses = new Map<string, string>();
  let current: string | null = null;
  for (const line of fs.readFileSync(file, "utf8").split(/\r?\n/)) {
    const heading = /^## ([A-Z0-9][A-Z0-9-]{2,})\s+—/.exec(line);
    if (heading) {
      current = heading[1];
      continue;
    }
    if (!current) continue;
    const statusLine = /^\*\*(?:Current repository )?[Ss]tatus:\*\*\s*(.+)$/.exec(line.trim());
    if (statusLine && !statuses.has(current)) {
      const status = firstStatus(statusLine[1]);
      if (status === null) {
        fail(`${current}: status line carries no canonical identifier: "${statusLine[1]}"`);
      } else {
        statuses.set(current, status);
      }
    }
  }
  return statuses;
}

/** Overall verdict block from docs/status.md (```text fenced```). */
function documentedOverall(): string | null {
  const file = path.join(ROOT, "docs/status.md");
  if (!fs.existsSync(file)) return null;
  const match = /## Overall\s+```text\s+([^\n]+)\n```/.exec(fs.readFileSync(file, "utf8"));
  return match ? match[1].trim() : null;
}

const documented = parseDocumentedStatuses();

// 1. Every desk experiment must exist in the canonical index, with the same status.
for (const row of experimentRows) {
  const code = row.code;
  if (!VOCABULARY.includes(row.status)) {
    fail(`desk row ${code} uses a non-canonical status "${row.status}"`);
    continue;
  }
  const docStatus = documented.get(code);
  if (docStatus === undefined) {
    fail(`desk advertises ${code}, but docs/research/experiments.md has no such experiment section`);
    continue;
  }
  if (docStatus !== row.status) {
    fail(`drift on ${code}: desk says "${row.status}", canonical document says "${docStatus}"`);
    continue;
  }
  ok(`${code}: ${row.status} (desk == document)`);
}

// 2. Every documented experiment must be advertised by the desk, in either direction.
for (const code of documented.keys()) {
  if (!experimentRows.some((row) => row.code === code)) {
    fail(`docs/research/experiments.md documents ${code}, but the desk omits it`);
  }
}
if (documented.size > 0) {
  ok(`${documented.size} documented experiments all present in the desk`);
}

// 3. The verdict string must match the canonical overall verdict.
const overall = documentedOverall();
if (overall === null) {
  fail('could not read "## Overall" verdict from docs/status.md');
} else if (overall !== verdictRow.verdict) {
  fail(`verdict drift: desk says "${verdictRow.verdict}", docs/status.md says "${overall}"`);
} else {
  ok(`overall verdict: ${overall} (desk == document)`);
}

// 4. Execution-evidence symmetry. The status field alone is not enough: the POC-003
// drift that motivated this file kept `status: "NO VERIFICADO"` (correct) while its
// prose described a missing compiler (wrong, after two executed runs). So the desk
// must agree with the document about *whether the experiment was executed at all*.
// The canonical record marks an executed run with an ISO date, so the desk must
// carry one too — and must not claim an execution the record does not.
const EXECUTED_WITH_DATE = /(?:executed|re-executed)\s+\d{4}-\d{2}-\d{2}|\(\s*\d{4}-\d{2}-\d{2}\s*(?:,|\))/i;
const MISSING_ENVIRONMENT_EXCUSE =
  /not present here|not available here|no such binary|This sandbox is Linux|not run in this environment|binary not present/i;

function sectionsByCode(): Map<string, string> {
  const file = path.join(ROOT, "docs/research/experiments.md");
  const text = fs.readFileSync(file, "utf8");
  const sections = new Map<string, string>();
  let current: string | null = null;
  let buffer: string[] = [];
  for (const line of text.split(/\r?\n/)) {
    const heading = /^## ([A-Z0-9][A-Z0-9-]{2,})\s+—/.exec(line);
    if (heading) {
      if (current) sections.set(current, buffer.join("\n"));
      current = heading[1];
      buffer = [];
      continue;
    }
    if (current) buffer.push(line);
  }
  if (current) sections.set(current, buffer.join("\n"));
  return sections;
}

const sections = sectionsByCode();
for (const row of experimentRows) {
  const section = sections.get(row.code);
  if (section === undefined) continue;
  const deskProse = `${row.method} ${row.successCriteria} ${row.blockedBy}`;
  const docExecuted = EXECUTED_WITH_DATE.test(section);
  const deskExecuted = EXECUTED_WITH_DATE.test(deskProse);
  if (docExecuted && !deskExecuted) {
    fail(
      `${row.code}: the canonical record dates an executed run, but the desk presents it as pending. ` +
        `Mirror the execution (and its outcome) in the desk row.`,
    );
    continue;
  }
  if (deskExecuted && !docExecuted) {
    fail(`${row.code}: the desk claims a dated execution that docs/research/experiments.md does not record.`);
    continue;
  }
  if (docExecuted && MISSING_ENVIRONMENT_EXCUSE.test(row.blockedBy)) {
    fail(
      `${row.code}: the experiment was executed, so "blocked by missing environment" is misleading prose ` +
        `(this is the exact POC-003 drift). State the measured outcome instead.`,
    );
    continue;
  }
  ok(`${row.code}: execution evidence agrees with the canonical record`);
}

console.log("\n==========================================");
console.log("RUNNING CHECK: Discovery Desk / documents consistency");
console.log("==========================================\n");
for (const line of checks) console.log(`  ok   ${line}`);
for (const line of failures) console.log(`  FAIL ${line}`);

if (failures.length > 0) {
  console.log(
    `\nCONSISTENCY: FAIL (${failures.length} problem(s)). ` +
      `The canonical documents in docs/ are the record; update the desk data to match them, ` +
      `or change the documents through their own evidence rules — never the reverse.`,
  );
  process.exit(1);
}
console.log(`\nCONSISTENCY: PASS (${checks.length} checks)`);
