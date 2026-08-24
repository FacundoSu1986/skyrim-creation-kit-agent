import { DocumentView } from "@/components/document-view";
import { SiteShell } from "@/components/site-shell";
import { getDocumentBySlug } from "@/lib/queries";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

export default async function ProblemPage() {
  const doc = await getDocumentBySlug("problem-definition");
  if (!doc) notFound();
  return (
    <SiteShell activeHref="/problem">
      <DocumentView title={doc.title} phase={doc.phase} summary={doc.summary} sections={doc.sections} />
    </SiteShell>
  );
}
