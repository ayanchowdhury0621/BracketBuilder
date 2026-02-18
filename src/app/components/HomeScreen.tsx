import { useMemo } from "react";
import { Link } from "react-router";
import { Trophy, TrendingUp, Brain, Zap, ArrowRight, Star, Target, ChevronRight, Loader2 } from "lucide-react";
import { RotoBotLogo } from "./RotoBotLogo";
import { TeamLogo } from "./TeamLogo";
import { useBracket } from "../context/BracketContext";
import type { Game, Team } from "../types/bracket";

function ConfidenceBar({ value }: { value: number }) {
  const color = value >= 80 ? "#00b8db" : value >= 60 ? "#3c84ff" : value >= 40 ? "#f59e0b" : "#ef4444";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full" style={{ background: "rgba(255,255,255,0.1)" }}>
        <div className="h-full rounded-full transition-all" style={{ width: `${value}%`, background: color }} />
      </div>
      <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 11, fontWeight: 600, color, minWidth: 32, textAlign: "right" }}>
        {value}%
      </span>
    </div>
  );
}

function TeamSeedBadge({ seed, color }: { seed: number; color: string }) {
  return (
    <div
      className="flex items-center justify-center rounded-md shrink-0"
      style={{
        width: 22, height: 22,
        background: `${color}22`, border: `1px solid ${color}44`,
        fontFamily: "Rubik, sans-serif", fontSize: 11, fontWeight: 700, color,
      }}
    >
      {seed}
    </div>
  );
}

function isPickTeam(game: Game, teamId: string, teamName: string): boolean {
  return game.rotobotPick === teamId || game.rotobotPick === teamName;
}

function FeaturedMatchup({ game }: { game: Game }) {
  return (
    <Link
      to={`/matchup/${game.id}`}
      className="no-underline block rounded-2xl overflow-hidden transition-transform hover:-translate-y-0.5"
      style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)" }}
    >
      <div className="p-4">
        <div className="flex items-center gap-2 mb-3">
          <div
            className="px-2 py-0.5 rounded-full"
            style={{
              background: "rgba(0,184,219,0.12)", border: "1px solid rgba(0,184,219,0.2)",
              fontFamily: "Rubik, sans-serif", fontSize: 10, fontWeight: 600,
              color: "#00b8db", textTransform: "uppercase", letterSpacing: "0.5px",
            }}
          >
            {game.region} • R1
          </div>
        </div>

        <div className="flex flex-col gap-2 mb-3">
          {[game.team1, game.team2].map((team) => {
            const isPick = isPickTeam(game, team.id, team.name);
            return (
              <div key={team.id} className="flex items-center gap-2.5">
                <TeamSeedBadge seed={team.seed} color={isPick ? "#00b8db" : "rgba(255,255,255,0.3)"} />
                <TeamLogo teamSlug={team.id} teamShortName={team.shortName} teamColor={team.color} size={28} />
                <span style={{
                  fontFamily: "Rubik, sans-serif", fontSize: 13,
                  fontWeight: isPick ? 600 : 400,
                  color: isPick ? "white" : "rgba(255,255,255,0.6)", flex: 1,
                }}>
                  {team.shortName}
                </span>
                <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 11, color: "rgba(255,255,255,0.35)" }}>
                  {team.record}
                </span>
                {isPick && (
                  <div className="flex items-center gap-1 px-2 py-0.5 rounded-full"
                    style={{ background: "rgba(0,184,219,0.15)", border: "1px solid rgba(0,184,219,0.3)" }}>
                    <Brain size={9} color="#00b8db" />
                    <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 10, fontWeight: 600, color: "#00b8db" }}>PICK</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        <ConfidenceBar value={game.rotobotConfidence} />

        <p className="mt-3 line-clamp-2" style={{ fontFamily: "Rubik, sans-serif", fontSize: 12, color: "rgba(255,255,255,0.45)", lineHeight: 1.5 }}>
          {(game.analysis || "").slice(0, 120)}...
        </p>
      </div>
    </Link>
  );
}

function StatCard({ icon: Icon, value, label, sub, color }: {
  icon: React.ElementType; value: string; label: string; sub?: string; color: string;
}) {
  return (
    <div className="flex flex-col gap-2 p-4 rounded-2xl"
      style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)" }}>
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 rounded-xl flex items-center justify-center" style={{ background: `${color}18` }}>
          <Icon size={15} color={color} />
        </div>
        <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 11, color: "rgba(255,255,255,0.45)" }}>{label}</span>
      </div>
      <div>
        <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 26, fontWeight: 700, color: "white", lineHeight: 1 }}>{value}</div>
        {sub && <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 11, color, marginTop: 3 }}>{sub}</div>}
      </div>
    </div>
  );
}

export function HomeScreen() {
  const { state, getRegionGames } = useBracket();

  const { featuredGames, topTeams } = useMemo(() => {
    if (!state.dataLoaded) return { featuredGames: [], topTeams: [] };

    const allR1: Game[] = [];
    for (const region of ["East", "West", "South", "Midwest"]) {
      allR1.push(...getRegionGames(region).r1);
    }

    // Featured: closest matchups (low confidence = high intrigue)
    const sorted = [...allR1].sort((a, b) => a.rotobotConfidence - b.rotobotConfidence);
    const featured = sorted.slice(0, 4);

    // Top 4 teams by rotobotScore across all regions
    const teams: Team[] = [];
    for (const region of ["East", "West", "South", "Midwest"]) {
      const { r1 } = getRegionGames(region);
      if (r1.length > 0) {
        const regionTeams = r1.map((g) => [g.team1, g.team2]).flat();
        const best = regionTeams.reduce((a, b) => (a.rotobotScore >= b.rotobotScore ? a : b));
        teams.push(best);
      }
    }

    return { featuredGames: featured, topTeams: teams };
  }, [state.dataLoaded, getRegionGames]);

  const teamCount = Object.keys(state.teams).length;

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
      <div className="fixed pointer-events-none" style={{ top: 0, left: "30%", width: 600, height: 400, background: "radial-gradient(ellipse, rgba(0,184,219,0.08) 0%, transparent 70%)" }} />
      <div className="fixed pointer-events-none" style={{ top: "40%", left: "-5%", width: 400, height: 400, background: "radial-gradient(ellipse, rgba(60,132,255,0.06) 0%, transparent 70%)" }} />

      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 relative">
        {/* Hero */}
        <div className="flex flex-col md:flex-row md:items-center gap-8 mb-10">
          <div className="flex-1">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full mb-4"
              style={{ background: "rgba(0,184,219,0.1)", border: "1px solid rgba(0,184,219,0.25)" }}>
              <div className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: "#00b8db" }} />
              <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 12, fontWeight: 600, color: "#00b8db" }}>
                2025-26 March Madness • Bracket Preview
              </span>
            </div>

            <h1 style={{
              fontFamily: "Rubik, sans-serif", fontSize: "clamp(32px, 5vw, 54px)",
              fontWeight: 800, color: "white", lineHeight: 1.1, letterSpacing: "-1px", marginBottom: 16,
            }}>
              Build Your <br />
              <span style={{ background: "linear-gradient(90deg, #00b8db, #3c84ff)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
                Smarter Bracket
              </span>
            </h1>

            <p style={{ fontFamily: "Rubik, sans-serif", fontSize: 16, color: "rgba(255,255,255,0.55)", lineHeight: 1.6, maxWidth: 480, marginBottom: 24 }}>
              RotoBot analyzes {teamCount} teams across {Object.keys(state.players).length} rosters — efficiency ratings, pace, recent form, and full-season player stats — to power every pick with AI.
            </p>

            <div className="flex flex-wrap gap-3">
              <Link to="/bracket" className="no-underline flex items-center gap-2 px-5 py-3 rounded-xl transition-all hover:opacity-90"
                style={{ background: "linear-gradient(135deg, #00b8db 0%, #3c84ff 100%)", fontFamily: "Rubik, sans-serif", fontWeight: 600, fontSize: 15, color: "white" }}>
                <Trophy size={16} /> Build My Bracket
              </Link>
              <Link to="/analysis" className="no-underline flex items-center gap-2 px-5 py-3 rounded-xl transition-all"
                style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)", fontFamily: "Rubik, sans-serif", fontWeight: 500, fontSize: 15, color: "rgba(255,255,255,0.8)" }}>
                <Brain size={16} /> Explore Analysis
              </Link>
            </div>
          </div>

          {/* Top team card */}
          {topTeams.length > 0 && (
            <div className="md:w-80 shrink-0 rounded-2xl overflow-hidden"
              style={{ background: "linear-gradient(135deg, rgba(0,184,219,0.08) 0%, rgba(60,132,255,0.08) 100%)", border: "1px solid rgba(0,184,219,0.2)" }}>
              <div className="px-5 pt-5 pb-4">
                <div className="flex items-center gap-2 mb-4">
                  <Star size={14} color="#00b8db" />
                  <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 11, fontWeight: 700, color: "#00b8db", textTransform: "uppercase", letterSpacing: "1px" }}>
                    RotoBot's #1 Overall
                  </span>
                </div>
                {topTeams[0] && (
                  <>
                    <div className="flex items-center gap-3 mb-3">
                      <TeamLogo teamSlug={topTeams[0].id} teamShortName={topTeams[0].shortName} teamColor={topTeams[0].color} size={40} />
                      <div>
                        <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 16, fontWeight: 700, color: "white" }}>
                          {topTeams[0].shortName}
                        </div>
                        <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 11, color: "rgba(255,255,255,0.4)" }}>
                          {topTeams[0].record} • {topTeams[0].conference} • NET #{topTeams[0].netRank}
                        </div>
                      </div>
                      <div className="ml-auto flex items-center justify-center rounded-full"
                        style={{ width: 48, height: 48, background: "linear-gradient(135deg, #00b8db22, #3c84ff22)", border: "2px solid rgba(0,184,219,0.4)" }}>
                        <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 14, fontWeight: 800, color: "#00b8db" }}>
                          {topTeams[0].rotobotScore}
                        </span>
                      </div>
                    </div>
                    <p style={{ fontFamily: "Rubik, sans-serif", fontSize: 12, color: "rgba(255,255,255,0.45)", lineHeight: 1.5 }}>
                      {(topTeams[0].rotobotBlurb || "").slice(0, 150)}...
                    </p>
                  </>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-10">
          <StatCard icon={Trophy} value={String(teamCount)} label="Teams Analyzed" sub="full D1 field" color="#00b8db" />
          <StatCard icon={Brain} value="30+" label="Stats per Team" sub="percentile-ranked" color="#3c84ff" />
          <StatCard icon={Target} value="4,889" label="Games Tracked" sub="full season boxscores" color="#22c55e" />
          <StatCard icon={Zap} value="32" label="R1 Matchups" sub="AI-analyzed" color="#f59e0b" />
        </div>

        {/* Projected Final Four */}
        {topTeams.length >= 4 && (
          <div className="mb-10">
            <div className="flex items-center justify-between mb-4">
              <h2 style={{ fontFamily: "Rubik, sans-serif", fontSize: 18, fontWeight: 700, color: "white" }}>
                Projected Regional Champions
              </h2>
              <Link to="/bracket" className="no-underline flex items-center gap-1"
                style={{ fontFamily: "Rubik, sans-serif", fontSize: 13, color: "#00b8db", fontWeight: 500 }}>
                Full bracket <ArrowRight size={13} />
              </Link>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {["East", "West", "South", "Midwest"].map((region, i) => {
                const team = topTeams[i];
                if (!team) return null;
                const regionColors: Record<string, string> = { East: "#00b8db", West: "#3c84ff", South: "#ef4444", Midwest: "#f59e0b" };
                const rc = regionColors[region] || "#00b8db";
                const blurb = team.styleSummary || team.styleIdentity || team.rotobotBlurb || "";
                return (
                  <Link key={region} to={`/bracket?region=${region}`} className="no-underline block rounded-2xl overflow-hidden transition-all hover:-translate-y-0.5 hover:border-[rgba(0,184,219,0.25)]"
                    style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)" }}>
                    <div className="p-4">
                      <div className="flex items-center justify-between mb-3">
                        <div className="inline-block px-2 py-0.5 rounded-full"
                          style={{ background: `${rc}18`, border: `1px solid ${rc}33`, fontFamily: "Rubik, sans-serif", fontSize: 10, fontWeight: 600, color: rc }}>
                          {region}
                        </div>
                        <div className="flex items-center gap-0.5">
                          {(team.recentForm || []).slice(-5).map((r, j) => (
                            <div key={j} className="w-1.5 h-1.5 rounded-full" style={{ background: r === "W" ? "#22c55e" : "#ef4444" }} />
                          ))}
                        </div>
                      </div>

                      <div className="flex items-center gap-2.5 mb-3">
                        <TeamLogo teamSlug={team.id} teamShortName={team.shortName} teamColor={team.color} size={36} />
                        <div className="flex-1 min-w-0">
                          <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 14, fontWeight: 600, color: "white" }}>
                            {team.shortName}
                          </div>
                          <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 10, color: "rgba(255,255,255,0.4)" }}>
                            #{team.seed} • {team.record} • {team.conference}
                          </div>
                        </div>
                        <div className="flex items-center justify-center rounded-full shrink-0"
                          style={{ width: 38, height: 38, background: `${rc}15`, border: `2px solid ${rc}40` }}>
                          <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 13, fontWeight: 800, color: rc }}>
                            {Math.round(team.rotobotScore)}
                          </span>
                        </div>
                      </div>

                      {/* Key stats grid */}
                      <div className="grid grid-cols-3 gap-1.5 mb-3">
                        <div className="rounded-lg px-2 py-1.5 text-center" style={{ background: "rgba(255,255,255,0.04)" }}>
                          <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 13, fontWeight: 700, color: "white" }}>{team.ppg}</div>
                          <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 8, color: "rgba(255,255,255,0.35)", textTransform: "uppercase", letterSpacing: "0.5px" }}>PPG</div>
                        </div>
                        <div className="rounded-lg px-2 py-1.5 text-center" style={{ background: "rgba(255,255,255,0.04)" }}>
                          <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 13, fontWeight: 700, color: "white" }}>{team.oppg}</div>
                          <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 8, color: "rgba(255,255,255,0.35)", textTransform: "uppercase", letterSpacing: "0.5px" }}>OPPG</div>
                        </div>
                        <div className="rounded-lg px-2 py-1.5 text-center" style={{ background: "rgba(255,255,255,0.04)" }}>
                          <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 13, fontWeight: 700, color: "white" }}>{team.eFGPct}%</div>
                          <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 8, color: "rgba(255,255,255,0.35)", textTransform: "uppercase", letterSpacing: "0.5px" }}>eFG%</div>
                        </div>
                      </div>

                      <div className="grid grid-cols-3 gap-1.5 mb-3">
                        <div className="rounded-lg px-2 py-1.5 text-center" style={{ background: "rgba(255,255,255,0.04)" }}>
                          <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 13, fontWeight: 700, color: "white" }}>
                            {team.stats?.schedule?.q1Record || "—"}
                          </div>
                          <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 8, color: "rgba(255,255,255,0.35)", textTransform: "uppercase", letterSpacing: "0.5px" }}>Q1 Rec</div>
                        </div>
                        <div className="rounded-lg px-2 py-1.5 text-center" style={{ background: "rgba(255,255,255,0.04)" }}>
                          <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 13, fontWeight: 700, color: "white" }}>#{team.netRank}</div>
                          <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 8, color: "rgba(255,255,255,0.35)", textTransform: "uppercase", letterSpacing: "0.5px" }}>NET</div>
                        </div>
                        <div className="rounded-lg px-2 py-1.5 text-center" style={{ background: "rgba(255,255,255,0.04)" }}>
                          <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 13, fontWeight: 700, color: "white" }}>#{team.sosRank}</div>
                          <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 8, color: "rgba(255,255,255,0.35)", textTransform: "uppercase", letterSpacing: "0.5px" }}>SOS</div>
                        </div>
                      </div>

                      {/* Key player */}
                      {team.keyPlayer && (
                        <div className="flex items-center gap-2 mb-2.5 px-2 py-1.5 rounded-lg"
                          style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.05)" }}>
                          <Star size={10} color={rc} className="shrink-0" />
                          <div className="min-w-0">
                            <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 10, fontWeight: 600, color: "rgba(255,255,255,0.7)" }}>
                              {team.keyPlayer}
                            </div>
                            <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 9, color: "rgba(255,255,255,0.35)" }}>
                              {team.keyPlayerStat}
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Style tags */}
                      {team.styleTags?.length > 0 && (
                        <div className="flex flex-wrap gap-1 mb-2.5">
                          {team.styleTags.filter(t => t && t !== "nan").slice(0, 3).map((tag) => (
                            <span key={tag} className="px-1.5 py-0.5 rounded"
                              style={{ fontFamily: "Rubik, sans-serif", fontSize: 9, fontWeight: 500, color: "rgba(255,255,255,0.5)", background: "rgba(255,255,255,0.06)" }}>
                              {tag}
                            </span>
                          ))}
                        </div>
                      )}

                      {blurb && (
                        <p className="mt-0 line-clamp-2" style={{ fontFamily: "Rubik, sans-serif", fontSize: 10, color: "rgba(255,255,255,0.4)", lineHeight: 1.5, margin: 0 }}>
                          {blurb.slice(0, 120)}{blurb.length > 120 ? "..." : ""}
                        </p>
                      )}

                      <div className="flex items-center gap-1 mt-2.5"
                        style={{ fontFamily: "Rubik, sans-serif", fontSize: 10, color: rc, fontWeight: 500 }}>
                        View region <ChevronRight size={11} />
                      </div>
                    </div>
                  </Link>
                );
              })}
            </div>
          </div>
        )}

        {/* Featured Matchups */}
        {featuredGames.length > 0 && (
          <div className="mb-10">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 style={{ fontFamily: "Rubik, sans-serif", fontSize: 18, fontWeight: 700, color: "white" }}>
                  Games to Watch
                </h2>
                <p style={{ fontFamily: "Rubik, sans-serif", fontSize: 12, color: "rgba(255,255,255,0.35)", marginTop: 2 }}>
                  RotoBot's highest-intrigue first-round matchups
                </p>
              </div>
              <Link to="/bracket" className="no-underline flex items-center gap-1"
                style={{ fontFamily: "Rubik, sans-serif", fontSize: 13, color: "#00b8db", fontWeight: 500 }}>
                View all <ArrowRight size={13} />
              </Link>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {featuredGames.map((game) => (
                <FeaturedMatchup key={game.id} game={game} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
