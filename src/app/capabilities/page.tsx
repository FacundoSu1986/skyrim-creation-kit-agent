import { SiteShell } from "@/components/site-shell";
import { StatusBadge } from "@/components/status-badge";
import { getCapabilities, getUseCases } from "@/lib/queries";
import { riskClass } from "@/lib/status";

export const dynamic = "force-dynamic";

export default async function CapabilitiesPage() {
  const [capabilities, useCases] = await Promise.all([getCapabilities(), getUseCases()]);

  return (
    <SiteShell activeHref="/capabilities">
      <p className="kicker">Capability matrix</p>
      <h1 className="mt-3 text-5xl leading-none">What can be automated, and what must not</h1>
      <p className="lede mt-5">
        Status here means research status, not a shipping feature. Nothing in this table has been
        implemented by this project.
      </p>
      <div className="table-wrap mt-8">
        <table>
          <thead>
            <tr>
              <th>Capability</th>
              <th>MVP class</th>
              <th>Status</th>
              <th>Backend</th>
              <th>Risk</th>
            </tr>
          </thead>
          <tbody>
            {capabilities.map((row) => (
              <tr key={row.id}>
                <td>
                  <div className="font-medium">{row.name}</div>
                  <div className="mt-1 text-[13px] text-[var(--muted)]">{row.notes}</div>
                </td>
                <td>{row.mvpClass}</td>
                <td>
                  <StatusBadge status={row.status.includes("NO VERIFICADO") ? "NO VERIFICADO" : row.status.includes("BLOQUEADO") ? "BLOQUEADO" : row.status.includes("Unsupported") ? "DESCARTADO" : "HIPOTESIS"} />
                </td>
                <td>{row.backend}</td>
                <td>
                  <span className={riskClass(row.risk)}>{row.risk}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <h2 className="mt-10 text-3xl">Use-case triage</h2>
      <div className="table-wrap mt-4">
        <table>
          <thead>
            <tr>
              <th>Use case</th>
              <th>MVP</th>
              <th>Risk</th>
              <th>Preferred backend</th>
            </tr>
          </thead>
          <tbody>
            {useCases.map((row) => (
              <tr key={row.id}>
                <td>
                  <div className="font-medium">{row.name}</div>
                  <div className="mt-1 text-[13px] text-[var(--muted)]">{row.description}</div>
                </td>
                <td>{row.mvpInclusion}</td>
                <td>
                  <span className={riskClass(row.riskLevel)}>{row.riskLevel}</span>
                </td>
                <td>{row.preferredBackend}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </SiteShell>
  );
}
