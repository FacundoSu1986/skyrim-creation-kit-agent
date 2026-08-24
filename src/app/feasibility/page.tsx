import { DocumentView } from "@/components/document-view";
import { SiteShell } from "@/components/site-shell";
import { StatusBadge } from "@/components/status-badge";
import { getDocumentBySlug, getGates, getVerdict } from "@/lib/queries";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

export default async function FeasibilityPage() {
  const [doc, verdict, gates] = await Promise.all([
    getDocumentBySlug("feasibility-report"),
    getVerdict(),
    getGates(),
  ]);
  if (!doc || !verdict) notFound();

  return (
    <SiteShell activeHref="/feasibility">
      <DocumentView title={doc.title} phase={doc.phase} summary={doc.summary} sections={doc.sections} />
      <section className="hero-panel mt-8">
        <div className="hero-copy">
          <p className="kicker">Required closing fields</p>
          <h2 className="mt-2 text-4xl">{verdict.verdict}</h2>
          <div className="card-grid mt-6">
            <div className="panel">
              <p className="kicker">Recommended architecture</p>
              <p>{verdict.recommendedArchitecture}</p>
            </div>
            <div className="panel">
              <p className="kicker">Primary backend</p>
              <p>{verdict.primaryBackend}</p>
            </div>
            <div className="panel">
              <p className="kicker">Fallback backend</p>
              <p>{verdict.fallbackBackend}</p>
            </div>
            <div className="panel">
              <p className="kicker">Highest technical risk</p>
              <p>{verdict.highestTechnicalRisk}</p>
            </div>
            <div className="panel">
              <p className="kicker">Highest legal risk</p>
              <p>{verdict.highestLegalRisk}</p>
            </div>
            <div className="panel">
              <p className="kicker">First experiment</p>
              <p>{verdict.firstExperiment}</p>
            </div>
            <div className="panel">
              <p className="kicker">MVP candidate</p>
              <p>{verdict.mvpCandidate}</p>
            </div>
            <div className="panel">
              <p className="kicker">Next step</p>
              <p>{verdict.nextStep}</p>
            </div>
          </div>
        </div>
      </section>
      <section className="mt-8">
        <h2 className="text-3xl">Gate 1 answers</h2>
        <div className="section-gap">
          {gates.map((gate) => (
            <article key={gate.id} className="panel">
              <div className="mb-2 flex items-center justify-between gap-3">
                <h3 className="m-0 text-xl">{gate.question}</h3>
                <StatusBadge status={gate.status} />
              </div>
              <p className="text-[var(--muted)]">{gate.answer}</p>
              <p className="text-sm text-[var(--copper-2)]">Experiment: {gate.experimentNeeded}</p>
            </article>
          ))}
        </div>
      </section>
    </SiteShell>
  );
}
