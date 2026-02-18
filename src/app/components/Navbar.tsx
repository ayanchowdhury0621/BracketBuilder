import { Link, useLocation } from "react-router";
import { Trophy, BarChart2, Home } from "lucide-react";
import { RotoBotLogo } from "./RotoBotLogo";

const NAV_ITEMS = [
  { to: "/", label: "Home", icon: Home },
  { to: "/bracket", label: "Bracket", icon: Trophy },
  { to: "/analysis", label: "Analysis", icon: BarChart2 },
];

export function Navbar() {
  const location = useLocation();

  return (
    <nav
      className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 py-3 border-b"
      style={{
        background: "rgba(1, 16, 62, 0.92)",
        backdropFilter: "blur(20px)",
        borderColor: "rgba(255,255,255,0.08)",
      }}
    >
      {/* Logo + Brand */}
      <Link to="/" className="flex items-center gap-3 no-underline">
        <RotoBotLogo size={38} />
        <div className="flex flex-col leading-none">
          <span
            className="text-white"
            style={{ fontFamily: "Rubik, sans-serif", fontWeight: 700, fontSize: 17, letterSpacing: "-0.3px" }}
          >
            RotoBot
          </span>
          <span style={{ fontFamily: "Rubik, sans-serif", fontWeight: 400, fontSize: 10, color: "#00b8db", letterSpacing: "1.5px", textTransform: "uppercase" }}>
            March Madness
          </span>
        </div>
      </Link>

      {/* Center nav links (desktop) */}
      <div className="hidden md:flex items-center gap-1">
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => {
          const active = location.pathname === to;
          return (
            <Link
              key={to}
              to={to}
              className="flex items-center gap-2 px-4 py-2 rounded-xl no-underline transition-all"
              style={{
                fontFamily: "Rubik, sans-serif",
                fontWeight: 500,
                fontSize: 14,
                color: active ? "#00b8db" : "rgba(255,255,255,0.6)",
                background: active ? "rgba(0,184,219,0.12)" : "transparent",
                border: active ? "1px solid rgba(0,184,219,0.3)" : "1px solid transparent",
              }}
            >
              <Icon size={15} />
              {label}
            </Link>
          );
        })}
      </div>

      {/* Right: CTA */}
      <div className="flex items-center gap-3">
        <div
          className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full"
          style={{ background: "rgba(0,184,219,0.1)", border: "1px solid rgba(0,184,219,0.25)" }}
        >
          <div className="w-2 h-2 rounded-full animate-pulse" style={{ background: "#00b8db" }} />
          <span style={{ fontFamily: "Rubik, sans-serif", fontWeight: 500, fontSize: 12, color: "#00b8db" }}>
            Live Analysis
          </span>
        </div>
        <Link
          to="/bracket"
          className="no-underline px-4 py-2 rounded-xl transition-all"
          style={{
            fontFamily: "Rubik, sans-serif",
            fontWeight: 600,
            fontSize: 13,
            background: "linear-gradient(135deg, #00b8db 0%, #3c84ff 100%)",
            color: "white",
          }}
        >
          Build Bracket
        </Link>
      </div>
    </nav>
  );
}

// Mobile bottom nav
export function BottomNav() {
  const location = useLocation();
  return (
    <div
      className="fixed bottom-0 left-0 right-0 md:hidden flex items-center justify-around px-2 py-2 z-50"
      style={{
        background: "rgba(1, 16, 62, 0.97)",
        backdropFilter: "blur(20px)",
        borderTop: "1px solid rgba(255,255,255,0.08)",
      }}
    >
      {NAV_ITEMS.map(({ to, label, icon: Icon }) => {
        const active = location.pathname === to;
        return (
          <Link
            key={to}
            to={to}
            className="flex flex-col items-center gap-0.5 px-4 py-1.5 rounded-xl no-underline"
            style={{ color: active ? "#00b8db" : "rgba(255,255,255,0.4)" }}
          >
            <Icon size={20} />
            <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 10, fontWeight: 500 }}>{label}</span>
          </Link>
        );
      })}
    </div>
  );
}
