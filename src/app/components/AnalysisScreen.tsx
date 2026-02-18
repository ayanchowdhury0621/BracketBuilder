import { useState, useMemo } from "react";
import { Link } from "react-router";
import { Brain, Search, TrendingUp, Zap, ChevronRight, BarChart2, Loader2 } from "lucide-react";
import { useBracket } from "../context/BracketContext";
import type { Game } from "../types/bracket";

function ConfidenceGauge({ value }: { value: number }) {
  const color = value >= 80 ? "#00b8db" : value >= 60 ? "#3c84ff" : value >= 50 ? "#f59e0b" : "#ef4444";
  const angle = (value / 100) * 180 - 90;
  const rad = (angle * Math.PI) / 180;
  const cx = 50, cy = 50, r = 36;
  const x = cx + r * Math.cos(rad);
  const y = cy + r * Math.sin(rad);

  return (
    <div className="flex flex-col items-center">
      <svg width="100" height="60" viewBox="0 0 100 60">
        <path d="M 14 50 A 36 36 0 0 1 86 50" stroke="rgba(255,255,255,0.08)" strokeWidth="6" fill="none" strokeLinecap="round" />
        <path d="M 14 50 A 36 36 0 0 1 86 50" stroke={color} strokeWidth="6" fill="none" strokeLinecap="round"
          strokeDasharray={`${value * 1.131} 200`}
        />
        <line x1={cx} y1={cy} x2={x} y2={y} stroke="white" strokeWidth="1.5" strokeLinecap="round" />
        <circle cx={cx} cy={cy} r="3" fill="white" />
        <text x={cx} y={58} textAnchor="middle" fill={color} fontSize="11" fontFamily="Rubik, sans-serif" fontWeight="700">
          {value}%
        </text>
      </svg>
    </div>
  );
}

function isRotobotPickTeam(game: Game, teamId: string, teamName: string): boolean {
  return game.rotobotPick === teamId || game.rotobotPick === teamName;
}

export function AnalysisScreen() {
  const { state, getRegionGames } = useBracket();
  const [search, setSearch] = useState("");
  const [regionFilter, setRegionFilter] = useState("All");

  const allGames = useMemo(() => {
    if (!state.dataLoaded) return [];
    const games: Game[] = [];
    for (const region of ["East", "West", "South", "Midwest"]) {
      const { r1 } = getRegionGames(region);
      games.push(...r1);
    }
    return games;
  }, [state.dataLoaded, getRegionGames]);

  const filtered = allGames.filter((g) => {
    const matchSearch =
      search === "" ||
      g.team1.name.toLowerCase().includes(search.toLowerCase()) ||
      g.team2.name.toLowerCase().includes(search.toLowerCase()) ||
      g.team1.shortName.toLowerCase().includes(search.toLowerCase()) ||
      g.team2.shortName.toLowerCase().includes(search.toLowerCase());
    const matchRegion = regionFilter === "All" || g.region === regionFilter;
    return matchSearch && matchRegion;
  });

  if (!state.dataLoaded) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: "#030712" }}>
        <Loader2 size={32} className="animate-spin" color="#00b8db" />
      </div>
    );
  }

  return (
    <div
      className="min-h-screen pt-16 pb-20 md:pb-8"
      style={{ background: "linear-gradient(160deg, #010c2a 0%, #030712 40%, #00081e 100%)" }}
    >
      <div className="fixed pointer-events-none" style={{ top: 80, right: "10%", width: 500, height: 400, background: "radial-gradient(ellipse, rgba(0,184,219,0.06) 0%, transparent 70%)" }} />

      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6 relative">
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-8 h-8 rounded-xl flex items-center justify-center" style={{ background: "rgba(0,184,219,0.15)" }}>
              <Brain size={16} color="#00b8db" />
            </div>
            <h1 style={{ fontFamily: "Rubik, sans-serif", fontSize: 24, fontWeight: 800, color: "white" }}>
              AI Game Analysis
            </h1>
            <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 13, color: "rgba(255,255,255,0.35)", marginLeft: 8 }}>
              {allGames.length} matchups
            </span>
          </div>
          <p style={{ fontFamily: "Rubik, sans-serif", fontSize: 14, color: "rgba(255,255,255,0.45)" }}>
            Deep-dive into every matchup with RotoBot's statistical models and insights.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 mb-6">
          <div
            className="flex items-center gap-2 flex-1 px-4 py-2.5 rounded-xl"
            style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)" }}
          >
            <Search size={15} color="rgba(255,255,255,0.3)" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search teams..."
              className="bg-transparent flex-1 outline-none"
              style={{ fontFamily: "Rubik, sans-serif", fontSize: 14, color: "white" }}
            />
          </div>
          <div className="flex gap-1 p-1 rounded-xl" style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.07)" }}>
            {["All", "East", "West", "South", "Midwest"].map((r) => (
              <button
                key={r}
                onClick={() => setRegionFilter(r)}
                className="px-3 py-1.5 rounded-lg transition-all"
                style={{
                  fontFamily: "Rubik, sans-serif", fontSize: 12,
                  fontWeight: regionFilter === r ? 600 : 400,
                  color: regionFilter === r ? "white" : "rgba(255,255,255,0.4)",
                  background: regionFilter === r ? "rgba(0,184,219,0.15)" : "transparent",
                  border: "none", cursor: "pointer",
                }}
              >
                {r}
              </button>
            ))}
          </div>
        </div>

        <div className="flex flex-col gap-3">
          {filtered.map((game) => {
            const isPick1 = isRotobotPickTeam(game, game.team1.id, game.team1.name);
            const pick = isPick1 ? game.team1 : game.team2;
            const other = isPick1 ? game.team2 : game.team1;

            return (
              <Link
                key={game.id}
                to={`/matchup/${game.id}`}
                className="no-underline block rounded-2xl overflow-hidden transition-all hover:border-[rgba(0,184,219,0.25)] group"
                style={{ background: "rgba(255,255,255,0.025)", border: "1px solid rgba(255,255,255,0.07)" }}
              >
                <div className="flex items-center gap-4 p-4">
                  <div className="flex flex-col items-center gap-1 shrink-0">
                    <div
                      className="px-2 py-0.5 rounded-full"
                      style={{
                        background: "rgba(0,184,219,0.1)", border: "1px solid rgba(0,184,219,0.2)",
                        fontFamily: "Rubik, sans-serif", fontSize: 9, fontWeight: 700,
                        color: "#00b8db", textTransform: "uppercase", letterSpacing: "0.5px",
                      }}
                    >
                      {game.region}
                    </div>
                    <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 9, color: "rgba(255,255,255,0.3)" }}>R1</span>
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex flex-col gap-1.5">
                      {[game.team1, game.team2].map((team) => {
                        const isPick = isRotobotPickTeam(game, team.id, team.name);
                        return (
                          <div key={team.id} className="flex items-center gap-2">
                            <div
                              className="w-5 h-5 rounded flex items-center justify-center shrink-0"
                              style={{
                                background: isPick ? "rgba(0,184,219,0.18)" : "rgba(255,255,255,0.06)",
                                fontFamily: "Rubik, sans-serif", fontSize: 9, fontWeight: 700,
                                color: isPick ? "#00b8db" : "rgba(255,255,255,0.4)",
                              }}
                            >
                              {team.seed}
                            </div>
                            <span className="truncate" style={{
                              fontFamily: "Rubik, sans-serif", fontSize: 13,
                              fontWeight: isPick ? 600 : 400,
                              color: isPick ? "white" : "rgba(255,255,255,0.5)",
                            }}>
                              {team.shortName}
                            </span>
                            <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 10, color: "rgba(255,255,255,0.25)" }}>
                              {team.record}
                            </span>
                            {isPick && <Brain size={10} color="#00b8db" />}
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  <div className="shrink-0 hidden sm:block">
                    <ConfidenceGauge value={game.rotobotConfidence} />
                  </div>

                  <div className="hidden md:block flex-1 max-w-xs">
                    <p className="line-clamp-2" style={{ fontFamily: "Rubik, sans-serif", fontSize: 12, color: "rgba(255,255,255,0.4)", lineHeight: 1.5 }}>
                      {(game.analysis || "").slice(0, 100)}
                    </p>
                  </div>

                  <div className="flex items-center gap-1 shrink-0" style={{ color: "#00b8db" }}>
                    <BarChart2 size={14} />
                    <ChevronRight size={14} className="group-hover:translate-x-0.5 transition-transform" />
                  </div>
                </div>

                <div
                  className="flex items-center gap-4 px-4 py-2.5"
                  style={{ borderTop: "1px solid rgba(255,255,255,0.04)", background: "rgba(0,0,0,0.2)" }}
                >
                  <div className="flex items-center gap-1.5">
                    <Zap size={10} color="#f59e0b" />
                    <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 10, color: "rgba(255,255,255,0.35)" }}>
                      {pick.shortName} +{(pick.ppg - other.ppg).toFixed(1)} PPG
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <TrendingUp size={10} color="#22c55e" />
                    <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 10, color: "rgba(255,255,255,0.35)" }}>
                      {pick.recentForm.filter((f) => f === "W").length}-{pick.recentForm.filter((f) => f === "L").length} last 5
                    </span>
                  </div>
                  <div className="ml-auto">
                    <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 10, color: "rgba(255,255,255,0.25)" }}>
                      NET #{pick.netRank}
                    </span>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
