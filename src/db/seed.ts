import { db } from "./index";
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
} from "./schema";
import {
  architectureRows,
  capabilityRows,
  documentRows,
  documentSectionRows,
  experimentRows,
  findingRows,
  gateRows,
  licenseRows,
  nameRows,
  projectRows,
  sourceRows,
  useCaseRows,
  verdictRow,
} from "@/lib/research";

export async function seedResearch(force = false) {
  const existing = await db.select({ id: verdicts.id }).from(verdicts).limit(1);
  if (existing.length > 0 && !force) {
    return { seeded: false };
  }

  if (force) {
    await db.delete(documentSections);
    await db.delete(documents);
    await db.delete(findings);
    await db.delete(existingProjects);
    await db.delete(licenseEntries);
    await db.delete(architectureOptions);
    await db.delete(capabilities);
    await db.delete(gateQuestions);
    await db.delete(nameCandidates);
    await db.delete(experiments);
    await db.delete(useCases);
    await db.delete(sources);
    await db.delete(verdicts);
  }

  await db.insert(sources).values(sourceRows);
  await db.insert(documents).values(documentRows);
  await db.insert(documentSections).values(documentSectionRows);
  await db.insert(findings).values(
    findingRows.map((row, index) => ({ ...row, sortOrder: index + 1 })),
  );
  await db.insert(existingProjects).values(
    projectRows.map((row, index) => ({ ...row, sortOrder: index + 1 })),
  );
  await db.insert(licenseEntries).values(
    licenseRows.map((row, index) => ({ ...row, sortOrder: index + 1 })),
  );
  await db.insert(architectureOptions).values(
    architectureRows.map((row, index) => ({ ...row, sortOrder: index + 1 })),
  );
  await db.insert(capabilities).values(
    capabilityRows.map((row, index) => ({ ...row, sortOrder: index + 1 })),
  );
  await db.insert(gateQuestions).values(
    gateRows.map((row, index) => ({ ...row, sortOrder: index + 1 })),
  );
  await db.insert(nameCandidates).values(
    nameRows.map((row, index) => ({ ...row, sortOrder: index + 1 })),
  );
  await db.insert(experiments).values(
    experimentRows.map((row, index) => ({ ...row, sortOrder: index + 1 })),
  );
  await db.insert(useCases).values(
    useCaseRows.map((row, index) => ({ ...row, sortOrder: index + 1 })),
  );
  await db.insert(verdicts).values(verdictRow);

  return { seeded: true };
}

async function main() {
  const result = await seedResearch(process.argv.includes("--force"));
  console.log(result);
}

if (process.argv[1] && process.argv[1].includes("seed")) {
  main()
    .then(() => process.exit(0))
    .catch((error) => {
      console.error(error);
      process.exit(1);
    });
}
