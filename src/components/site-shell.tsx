import Link from "next/link";
import type { ReactNode } from "react";

const NAV = [
  ["00", "Desk", "/"],
  ["01", "Problem", "/problem"],
  ["02", "Creation Kit", "/creation-kit"],
  ["03", "Automation", "/automation"],
  ["04", "Prior art", "/projects"],
  ["05", "Licenses", "/licensing"],
  ["06", "Threats", "/threats"],
  ["07", "Architecture", "/architecture"],
  ["08", "Gate 1", "/feasibility"],
  ["09", "Capabilities", "/capabilities"],
  ["10", "Experiments", "/experiments"],
  ["11", "Names", "/names"],
  ["12", "Sources", "/sources"],
] as const;

export function SiteShell({
  children,
  activeHref,
}: {
  children: ReactNode;
  activeHref: string;
}) {
  return (
    <div className="desk-shell">
      <aside className="desk-rail">
        <p className="brand-kicker">Phase 0 + 1</p>
        <h1 className="brand-title">Discovery Desk</h1>
        <p className="brand-sub">
          Research archive for a safe Skyrim SE/AE Creation Kit agent. Not a product. Not affiliated
          with Bethesda.
        </p>
        <nav className="rail-nav" aria-label="Research navigation">
          {NAV.map(([index, label, href]) => (
            <Link
              key={href}
              href={href}
              className={`rail-link${activeHref === href ? " active" : ""}`}
            >
              <span>{label}</span>
              <span className="rail-index">{index}</span>
            </Link>
          ))}
        </nav>
      </aside>
      <div className="desk-main">{children}</div>
    </div>
  );
}
