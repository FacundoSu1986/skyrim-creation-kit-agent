import { StatusBadge } from "@/components/status-badge";

type Section = {
  heading: string;
  body: string;
  status: string;
};

export function DocumentView({
  title,
  phase,
  summary,
  sections,
}: {
  title: string;
  phase: string;
  summary: string;
  sections: Section[];
}) {
  return (
    <article>
      <p className="kicker">{phase}</p>
      <h1 className="mt-3 text-5xl leading-none">{title}</h1>
      <p className="lede mt-5">{summary}</p>
      <div className="section-gap">
        {sections.map((section) => (
          <section key={section.heading} className="paper">
            <div className="mb-3 flex items-center justify-between gap-3">
              <h2 className="m-0 text-2xl">{section.heading}</h2>
              <StatusBadge status={section.status} />
            </div>
            <div className="prose-split text-[15px]">{section.body}</div>
          </section>
        ))}
      </div>
    </article>
  );
}
