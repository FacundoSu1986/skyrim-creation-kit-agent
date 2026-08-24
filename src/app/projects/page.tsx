import { SiteShell } from "@/components/site-shell";
import { StatusBadge } from "@/components/status-badge";
import { getDocumentBySlug, getProjects } from "@/lib/queries";

export const dynamic = "force-dynamic";

export default async function ProjectsPage() {
  const [projects, intro] = await Promise.all([
    getProjects(),
    getDocumentBySlug("existing-projects"),
  ]);

  return (
    <SiteShell activeHref="/projects">
      <p className="kicker">{intro?.phase ?? "Phase 1"}</p>
      <h1 className="mt-3 text-5xl leading-none">Existing projects</h1>
      <p className="lede mt-5">{intro?.summary}</p>
      <div className="section-gap">
        {projects.map((project) => (
          <article key={project.id} className="paper">
            <div className="mb-2 flex flex-wrap items-center justify-between gap-3">
              <h2 className="m-0 text-3xl">{project.name}</h2>
              <StatusBadge status={project.projectStatus.includes("Active") ? "VERIFICADO" : "NO VERIFICADO"} />
            </div>
            <p className="mt-0 text-sm">
              <a className="source-link" href={project.url} target="_blank" rel="noreferrer">
                {project.url}
              </a>
            </p>
            <p>
              <strong>Last activity:</strong> {project.lastActivity}
            </p>
            <p>
              <strong>License / language:</strong> {project.license} · {project.language}
            </p>
            <p>
              <strong>Architecture:</strong> {project.architecture}
            </p>
            <p>
              <strong>Solves:</strong> {project.solves}
            </p>
            <p>
              <strong>Does not solve:</strong> {project.doesNotSolve}
            </p>
            <p>
              <strong>Reusable:</strong> {project.reusableCode}
            </p>
            <p>
              <strong>Risks:</strong> {project.risks}
            </p>
          </article>
        ))}
      </div>
    </SiteShell>
  );
}
