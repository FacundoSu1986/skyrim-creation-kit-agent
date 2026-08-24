import { asc, eq } from "drizzle-orm";
import { db } from "@/db";
import {
  architectureOptions,
  capabilities,
  documentSections,
  documents,
  existingProjects,
  experiments,
  findings,
  gateQuestions,
  licenseEntries,
  nameCandidates,
  sources,
  useCases,
  verdicts,
} from "@/db/schema";
import { seedResearch } from "@/db/seed";

export async function ensureResearchSeeded() {
  await seedResearch(false);
}

export async function getVerdict() {
  await ensureResearchSeeded();
  const rows = await db.select().from(verdicts).limit(1);
  return rows[0] ?? null;
}

export async function getDocuments() {
  await ensureResearchSeeded();
  return db.select().from(documents).orderBy(asc(documents.sortOrder));
}

export async function getDocumentBySlug(slug: string) {
  await ensureResearchSeeded();
  const docs = await db.select().from(documents).where(eq(documents.slug, slug)).limit(1);
  const doc = docs[0];
  if (!doc) return null;
  const sections = await db
    .select()
    .from(documentSections)
    .where(eq(documentSections.documentSlug, slug))
    .orderBy(asc(documentSections.sortOrder));
  return { ...doc, sections };
}

export async function getFindings() {
  await ensureResearchSeeded();
  return db.select().from(findings).orderBy(asc(findings.sortOrder));
}

export async function getProjects() {
  await ensureResearchSeeded();
  return db.select().from(existingProjects).orderBy(asc(existingProjects.sortOrder));
}

export async function getLicenses() {
  await ensureResearchSeeded();
  return db.select().from(licenseEntries).orderBy(asc(licenseEntries.sortOrder));
}

export async function getArchitectures() {
  await ensureResearchSeeded();
  return db.select().from(architectureOptions).orderBy(asc(architectureOptions.sortOrder));
}

export async function getCapabilities() {
  await ensureResearchSeeded();
  return db.select().from(capabilities).orderBy(asc(capabilities.sortOrder));
}

export async function getGates() {
  await ensureResearchSeeded();
  return db.select().from(gateQuestions).orderBy(asc(gateQuestions.sortOrder));
}

export async function getNames() {
  await ensureResearchSeeded();
  return db.select().from(nameCandidates).orderBy(asc(nameCandidates.sortOrder));
}

export async function getExperiments() {
  await ensureResearchSeeded();
  return db.select().from(experiments).orderBy(asc(experiments.sortOrder));
}

export async function getUseCases() {
  await ensureResearchSeeded();
  return db.select().from(useCases).orderBy(asc(useCases.sortOrder));
}

export async function getSources() {
  await ensureResearchSeeded();
  return db.select().from(sources).orderBy(asc(sources.id));
}

export async function getDashboard() {
  const [verdict, docs, findingList, gates, experimentsList, architectures] = await Promise.all([
    getVerdict(),
    getDocuments(),
    getFindings(),
    getGates(),
    getExperiments(),
    getArchitectures(),
  ]);

  const statusCounts = findingList.reduce<Record<string, number>>((acc, row) => {
    acc[row.status] = (acc[row.status] ?? 0) + 1;
    return acc;
  }, {});

  return {
    verdict,
    documents: docs,
    findings: findingList,
    gates,
    experiments: experimentsList,
    architectures,
    statusCounts,
  };
}
