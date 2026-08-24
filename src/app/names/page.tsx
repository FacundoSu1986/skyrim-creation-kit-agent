import { SiteShell } from "@/components/site-shell";
import { getNames } from "@/lib/queries";

export const dynamic = "force-dynamic";

export default async function NamesPage() {
  const rows = await getNames();

  return (
    <SiteShell activeHref="/names">
      <p className="kicker">Branding research only</p>
      <h1 className="mt-3 text-5xl leading-none">Name candidates</h1>
      <p className="lede mt-5">
        No name is chosen. Avoid anything that looks Bethesda-official or collides with SkyrimForge,
        houseCARL, or SkyClaw.
      </p>
      <div className="section-gap">
        {rows.map((row) => (
          <article key={row.id} className="paper">
            <h2 className="mt-0 text-3xl">{row.name}</h2>
            <p>
              <strong>Recommendation:</strong> {row.recommendation}
            </p>
            <p>
              <strong>Collisions:</strong> {row.collisions}
            </p>
            <p>
              <strong>Search / identity:</strong> {row.searchability} {row.visualIdentity}
            </p>
            <p>
              <strong>Skyrim / CK relation:</strong> {row.skyrimRelation} / {row.ckRelation}
            </p>
            <p>
              <strong>Trademark risk:</strong> {row.trademarkRisk}
            </p>
          </article>
        ))}
      </div>
    </SiteShell>
  );
}
