import { NavLink, Outlet } from "react-router-dom";

const navItems = [
  { path: "/analysis", label: "Analysis" },
  { path: "/events", label: "Events" },
  { path: "/dashboard", label: "Dashboard" },
  { path: "/parsers", label: "Parsers" },
  { path: "/store", label: "Store" },
  { path: "/system", label: "System" }
];

export function NavShell() {
  return (
    <div className="min-h-screen bg-bg text-ink">
      <div className="pointer-events-none fixed inset-0 bg-radial" aria-hidden />
      <header className="sticky top-0 z-20 border-b border-white/10 bg-panel/80 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6">
          <div>
            <h1 className="font-display text-xl tracking-widest text-accent">SMARTLOG CONTROL ROOM</h1>
            <p className="text-xs uppercase tracking-[0.2em] text-inkSoft">Observe. Parse. Decide.</p>
          </div>
          <nav className="flex flex-wrap gap-2">
            {navItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `rounded-full px-3 py-1 text-sm transition ${
                    isActive ? "bg-accent text-black" : "bg-white/5 text-inkSoft hover:bg-white/10"
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto grid max-w-7xl gap-4 px-4 py-6 sm:px-6">
        <Outlet />
      </main>
    </div>
  );
}
