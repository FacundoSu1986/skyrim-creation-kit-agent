import { SiteShell } from "@/components/site-shell";
import { StatusBadge } from "@/components/status-badge";
import { getDocumentBySlug, getLicenses } from "@/lib/queries";

export const dynamic = "force-dynamic";

export default async function LicensingPage() {
  const [rows, intro] = await Promise.all([getLicenses(), getDocumentBySlug("licensing")]);

  return (
    <SiteShell activeHref="/licensing">
      <p className="kicker">{intro?.phase ?? "Phase 2"}</p>
      <h1 className="mt-3 text-5xl leading-none">Licensing matrix</h1>
      <p className="lede mt-5">{intro?.summary}</p>
      <div className="table-wrap mt-8">
        <table>
          <thead>
            <tr>
              <th>Component</th>
              <th>License</th>
              <th>Use</th>
              <th>Modify</th>
              <th>Distribute</th>
              <th>Risk</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                <td>
                  <div className="font-medium">{row.component}</div>
                  {row.legalReviewRequired ? (
                    <div className="mt-2">
                      <StatusBadge status="LEGAL_REVIEW_REQUIRED" />
                    </div>
                  ) : null}
                </td>
                <td>{row.license}</td>
                <td className="text-[var(--muted)]">{row.intendedUse}</td>
                <td className="text-[var(--muted)]">{row.modification}</td>
                <td className="text-[var(--muted)]">{row.distribution}</td>
                <td>
                  {row.risk}
                  <p className="mt-2 text-[13px] text-[var(--muted)]">{row.notes}</p>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </SiteShell>
  );
}
