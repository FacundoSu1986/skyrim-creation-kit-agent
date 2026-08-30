import { SiteShell } from "@/components/site-shell";
import { getDocumentBySlug, getLicenses } from "@/lib/queries";
import {
  DistributionAuthorizationStatus,
  isDistributionAuthorizationStatus,
} from "@/lib/research/licenses";

export const dynamic = "force-dynamic";

function renderDistributionBadge(status: unknown) {
  if (!isDistributionAuthorizationStatus(status)) {
    // Fail-closed fallback: unknown runtime data cannot be trusted.
    // Display as legal review required rather than silently hiding.
    return (
      <div>
        <span
          className="badge badge-legal"
          title="Unknown distribution authorization status — legal review required"
        >
          Distribution: Unknown — review required
        </span>
      </div>
    );
  }

  switch (status) {
    case "LEGAL_REVIEW_REQUIRED":
      return (
        <div>
          <span
            className="badge badge-legal"
            title="Distribution/integration model requires legal authorization"
          >
            Distribution: Legal review
          </span>
        </div>
      );
    case "DESCARTADO":
      return (
        <div>
          <span className="badge badge-rejected" title="Distribution is forbidden">
            Distribution: Forbidden
          </span>
        </div>
      );
    case "NOT_APPLICABLE":
      return null;
    default: {
      const _exhaustiveCheck: never = status;
      return (
        <div>
          <span
            className="badge badge-legal"
            title="Unhandled distribution authorization status — review required"
          >
            Distribution: Unknown — review required ({_exhaustiveCheck})
          </span>
        </div>
      );
    }
  }
}

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
                  <div className="mt-2 flex flex-col gap-1.5">
                    {row.legalReviewRequired ? (
                      <div>
                        <span
                          className="badge badge-legal"
                          title="Component license requires legal review"
                        >
                          Component: Legal review
                        </span>
                      </div>
                    ) : null}
                    {renderDistributionBadge(row.distributionAuthorizationStatus)}
                  </div>
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
