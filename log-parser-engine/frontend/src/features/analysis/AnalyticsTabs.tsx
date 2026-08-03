import { NavLink } from "react-router-dom";

const tabs = [
  { to: "/analytics", label: "Genel görünüm", end: true },
  { to: "/analytics/compare", label: "Dönem karşılaştırma", end: false }
] as const;

export function AnalyticsTabs() {
  return (
    <nav aria-label="İstatistiksel analiz modları" className="flex flex-wrap gap-2">
      {tabs.map((tab) => (
        <NavLink
          key={tab.to}
          to={tab.to}
          end={tab.end}
          className={({ isActive }) =>
            `rounded-full border px-3 py-1.5 text-sm font-medium transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent ${
              isActive
                ? "border-accent/50 bg-accent/15 text-accent"
                : "border-white/10 bg-white/5 text-inkSoft hover:border-white/25 hover:text-ink"
            }`
          }
        >
          {tab.label}
        </NavLink>
      ))}
    </nav>
  );
}
