import { SiteShell } from "@/components/site-shell";
import { StatusBadge } from "@/components/status-badge";
import { getSources } from "@/lib/queries";

export const dynamic = "force-dynamic";

export default async function SourcesPage() {
  const rows = await getSources();

  return (
    <SiteShell activeHref="/sources">
      <p className="kicker">Bibliography</p>
      <h1 className="mt-3 text-5xl leading-none">Sources retrieved for Phase 0 + 1</h1>
      <p className="lede mt-5">
        Accessed 2026-03-22. Community wikis are labeled as such. Absence of an official API is
        treated as evidence only when paired with primary EULA and vendor docs.
      </p>
      <div className="section-gap">
        {rows.map((row) => (
          <article key={row.id} className="panel">
            <div className="mb-2 flex items-center justify-between gap-3">
              <h2 className="m-0 text-xl">{row.title}</h2>
              <StatusBadge status={row.verification} />
            </div>
            <p className="m-0 text-sm text-[var(--copper-2)]">
              {row.publisher} · {row.accessedOn}
            </p>
            <p>
              <a href={row.url} target="_blank" rel="noreferrer">
                {row.url}
              </a>
            </p>
            <p className="text-[var(--muted)]">{row.notes}</p>
          </article>
        ))}
      </div>
    </SiteShell>
  );
}
