import { SiteShell } from "@/components/site-shell";
import { StatusBadge } from "@/components/status-badge";
import { getExperiments, getFindings } from "@/lib/queries";

export const dynamic = "force-dynamic";

export default async function ExperimentsPage() {
  const [experiments, findings] = await Promise.all([getExperiments(), getFindings()]);

  return (
    <SiteShell activeHref="/experiments">
      <p className="kicker">Evidence-gated, partly executed</p>
      <h1 className="mt-3 text-5xl leading-none">Experiments and findings</h1>
      <p className="lede mt-5">
        Two executable proofs have been run and passed their gates (POC-002, POC-IPC-001); one
        was run and failed two mandatory criteria (POC-003). The remaining cards are protocols,
        not results. No Creation Kit, xEdit, or PapyrusCompiler binary is committed here, and CI
        never runs one.
      </p>
      <div className="section-gap">
        {experiments.map((row) => (
          <article key={row.id} className="panel">
            <div className="mb-2 flex items-center justify-between gap-3">
              <h2 className="m-0 text-2xl">
                {row.code}: {row.title}
              </h2>
              <StatusBadge status={row.status} />
            </div>
            <p className="text-[var(--muted)]">
              <strong className="text-[var(--parchment)]">Hypothesis.</strong> {row.hypothesis}
            </p>
            <p className="text-[var(--muted)]">
              <strong className="text-[var(--parchment)]">Method.</strong> {row.method}
            </p>
            <p className="text-[var(--muted)]">
              <strong className="text-[var(--parchment)]">Success.</strong> {row.successCriteria}
            </p>
            <p className="text-sm text-[var(--copper-2)]">Blocked by: {row.blockedBy}</p>
          </article>
        ))}
      </div>
      <h2 className="mt-10 text-3xl">Key findings</h2>
      <div className="section-gap">
        {findings.map((row) => (
          <article key={row.id} className="paper">
            <div className="mb-2 flex items-center justify-between gap-3">
              <p className="m-0 text-sm uppercase tracking-[0.14em]">{row.category}</p>
              <StatusBadge status={row.status} />
            </div>
            <h3 className="mt-0 text-2xl">{row.claim}</h3>
            <p>
              <strong>Evidence.</strong> {row.evidence}
            </p>
            <p>
              <strong>Implication.</strong> {row.implication}
            </p>
          </article>
        ))}
      </div>
    </SiteShell>
  );
}
