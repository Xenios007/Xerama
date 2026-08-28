import { NavLink, Outlet } from "react-router-dom";
import { ChatPanel } from "../chat/ChatPanel";
import "./AppShell.css";

// Only routes that need no ID belong here - everything else (Story,
// Characters, Production, Review, Library) is reached contextually from
// ProjectDetailPage once a project is selected, since each needs a
// project/series/episode id that only exists once one is picked.
const NAV_ITEMS = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/settings", label: "Settings" },
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
      <ChatPanel />
    </div>
  );
}
