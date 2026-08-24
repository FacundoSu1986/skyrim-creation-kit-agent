import { DocumentView } from "@/components/document-view";
import { SiteShell } from "@/components/site-shell";
import { getDocumentBySlug } from "@/lib/queries";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

export default async function AutomationPage() {
  const doc = await getDocumentBySlug("automation-options");
  if (!doc) notFound();
  return (
    <SiteShell activeHref="/automation">
      <DocumentView title={doc.title} phase={doc.phase} summary={doc.summary} sections={doc.sections} />
    </SiteShell>
  );
}
