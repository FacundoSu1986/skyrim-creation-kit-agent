import { SiteShell } from "@/components/site-shell";
import { StatusBadge } from "@/components/status-badge";
import { getArchitectures, getDocumentBySlug } from "@/lib/queries";
import { SCORE_WEIGHTS } from "@/lib/research";

export const dynamic = "force-dynamic";

export default async function ArchitecturePage() {
  const [rows, intro] = await Promise.all([
    getArchitectures(),
    getDocumentBySlug("architecture-options"),
  ]);

  return (
    <SiteShell activeHref="/architecture">
      <p className="kicker">{intro?.phase ?? "Phase 3"}</p>
      <h1 className="mt-3 text-5xl leading-none">Architecture options</h1>
      <p className="lede mt-5">{intro?.summary}</p>
      <p className="mt-4 text-sm text-[var(--muted)]">
        Weights: robustness {SCORE_WEIGHTS.robustness}, security {SCORE_WEIGHTS.security},
        testability {SCORE_WEIGHTS.testability}, low corruption {SCORE_WEIGHTS.corruptionRisk},
        maintainability {SCORE_WEIGHTS.maintainability}, license {SCORE_WEIGHTS.licenseFit}. Higher
        axis scores are better.
      </p>
      <div className="table-wrap mt-6">
        <table>
          <thead>
            <tr>
              <th>Option</th>
              <th>Score</th>
              <th>Rob</th>
              <th>Sec</th>
              <th>Test</th>
              <th>Safe</th>
              <th>Lic</th>
              <th>Pick</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                <td>
                  <div className="font-medium">
                    {row.code}. {row.name}
                  </div>
                  <div className="mt-1 text-[13px] text-[var(--muted)]">{row.summary}</div>
                </td>
                <td className="score">{row.weightedScore}</td>
                <td>{row.robustness}</td>
                <td>{row.security}</td>
                <td>{row.testability}</td>
                <td>{row.corruptionRisk}</td>
                <td>{row.licenseFit}</td>
                <td>
                  {row.recommended ? (
                    <StatusBadge status="VERIFICADO" />
                  ) : (
                    <StatusBadge status="DESCARTADO" />
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="section-gap">
        {rows.map((row) => (
          <article key={`${row.code}-note`} className="paper">
            <h2 className="mt-0 text-2xl">
              {row.code}. {row.name}
            </h2>
            <p>{row.notes}</p>
          </article>
        ))}
      </div>
    </SiteShell>
  );
}
