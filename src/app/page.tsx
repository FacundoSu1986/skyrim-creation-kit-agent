import Link from "next/link";
import { SiteShell } from "@/components/site-shell";
import { StatusBadge } from "@/components/status-badge";
import { getDashboard } from "@/lib/queries";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const data = await getDashboard();
  const verdict = data.verdict;

  return (
    <SiteShell activeHref="/">
      <section className="hero-panel">
        <img
          src="/images/research-desk.jpg"
          alt="Copper instruments and notes on a dark research desk"
          className="hero-art"
        />
        <div className="hero-copy">
          <p className="kicker">Gate 1 research desk</p>
          <h1 className="mt-3 max-w-4xl text-5xl leading-[0.92]">
            Can an agent touch Creation Kit without inventing an API?
          </h1>
          <p className="lede mt-5">
            Phase 0 and Phase 1 only. Primary sources, license constraints, prior art, and a scored
            architecture matrix. No quest generator. No click bot. No claimed test that was not run.
          </p>
          {verdict ? (
            <div className="verdict-banner">
              <div>
                <p className="kicker">Verdict</p>
                <p className="verdict-word">{verdict.verdict}</p>
              </div>
              <p className="m-0 text-[15px] leading-7 text-[var(--muted)]">{verdict.rationale}</p>
            </div>
          ) : null}
        </div>
      </section>

      <div className="meta-grid">
        <div className="panel stat">
          Findings
          <strong>{data.findings.length}</strong>
        </div>
        <div className="panel stat">
          Verified claims
          <strong>{data.statusCounts.VERIFICADO ?? 0}</strong>
        </div>
        <div className="panel stat">
          Still unverified
          <strong>{(data.statusCounts["NO VERIFICADO"] ?? 0) + (data.statusCounts.HIPOTESIS ?? 0)}</strong>
        </div>
        <div className="panel stat">
          Designed experiments
          <strong>{data.experiments.length}</strong>
        </div>
      </div>

      <div className="card-grid mt-8">
        <section className="panel">
          <p className="kicker">Recommended spine</p>
          <h2 className="mt-2 text-3xl">Hybrid, headless-first</h2>
          <p className="text-[var(--muted)]">
            {verdict?.recommendedArchitecture}
          </p>
          <p className="text-[var(--muted)]">Primary backend: {verdict?.primaryBackend}</p>
        </section>
        <section className="panel">
          <p className="kicker">Single next step</p>
          <h2 className="mt-2 text-3xl">ADR, then POC-002</h2>
          <p className="text-[var(--muted)]">{verdict?.nextStep}</p>
          <Link href="/experiments" className="mt-4 inline-block text-[var(--copper-2)]">
            Open experiment board →
          </Link>
        </section>
      </div>

      <section className="mt-8">
        <div className="mb-3 flex items-end justify-between">
          <h2 className="text-3xl">Gate 1 questions</h2>
          <Link href="/feasibility" className="text-sm text-[var(--copper-2)]">
            Full report
          </Link>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Question</th>
                <th>Status</th>
                <th>Answer</th>
              </tr>
            </thead>
            <tbody>
              {data.gates.map((gate) => (
                <tr key={gate.id}>
                  <td className="font-medium">{gate.question}</td>
                  <td>
                    <StatusBadge status={gate.status} />
                  </td>
                  <td className="text-[var(--muted)]">{gate.answer}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </SiteShell>
  );
}
