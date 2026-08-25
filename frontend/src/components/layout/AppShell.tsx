import { NavLink, Outlet } from "react-router-dom";
import "./AppShell.css";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/story", label: "Story Studio" },
  { to: "/characters", label: "Character Studio" },
  { to: "/production", label: "Production Studio" },
  { to: "/review", label: "Review & Approval" },
];

export function AppShell() {
  return (
    <div className="xr-shell">
      <header className="xr-shell__header">
        <span className="xr-shell__brand">Xerama Studio</span>
        <nav className="xr-shell__nav">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => `xr-shell__link${isActive ? " xr-shell__link--active" : ""}`}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="xr-shell__content">
        <Outlet />
      </main>
    </div>
  );
}
