import { useState, useEffect, useMemo } from "react";
import { useParams, Link } from "react-router";
import {
  Brain, ChevronLeft, TrendingUp, Target, Zap, BarChart2,
  CheckCircle2, Users, Newspaper, Shield, Loader2, History,
} from "lucide-react";
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer, Tooltip } from "recharts";
import { useBracket } from "../context/BracketContext";
import { fetchTeamPlayers, fetchEspnRoster, fetchTrends } from "../lib/api";
import { TeamLogo } from "./TeamLogo";
import type { Game, Team, PlayerRecord } from "../types/bracket";

const CYAN = "#00b8db";
const BLUE = "#3c84ff";

function cleanNewsText(raw: string): string[] {
  return raw
    .split(/\n|(?=- \*\*)/)
    .map((line) =>
      line
        .replace(/\[\d+\]/g, "")          // strip [1][2][3] citation refs
        .replace(/\*\*/g, "")             // strip bold markdown **
        .replace(/^[-•]\s*/, "")           // strip leading bullets
        .replace(/^\s+|\s+$/g, "")         // trim whitespace
    )
    .filter((line) => line.length > 5);
}

// ── Shared sub-components ───────────────────────────────────────────────────

function StatBar({ label, val1, val2, higherIsBetter = true }: {
  label: string; val1: number; val2: number; higherIsBetter?: boolean;
}) {
  const total = val1 + val2 || 1;
  const pct1 = (val1 / total) * 100;
  const winner1 = higherIsBetter ? val1 > val2 : val1 < val2;
  const winner2 = higherIsBetter ? val2 > val1 : val2 < val1;

  return (
    <div className="flex items-center gap-3">
      <div className="text-right" style={{ fontFamily: "Rubik, sans-serif", fontSize: 13, fontWeight: winner1 ? 700 : 400, color: winner1 ? CYAN : "rgba(255,255,255,0.55)", minWidth: 48 }}>
        {val1}
      </div>
      <div className="flex-1 flex flex-col gap-1">
        <div className="flex h-2 rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,0.07)" }}>
          <div style={{ width: `${pct1}%`, background: CYAN, borderRadius: "4px 0 0 4px" }} />
          <div style={{ flex: 1, background: BLUE, borderRadius: "0 4px 4px 0" }} />
        </div>
        <div className="text-center" style={{ fontFamily: "Rubik, sans-serif", fontSize: 10, color: "rgba(255,255,255,0.3)", textTransform: "uppercase", letterSpacing: "0.5px" }}>
          {label}
        </div>
      </div>
      <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 13, fontWeight: winner2 ? 700 : 400, color: winner2 ? BLUE : "rgba(255,255,255,0.55)", minWidth: 48, textAlign: "right" }}>
        {val2}
      </div>
    </div>
  );
}

function FormBadge({ result }: { result: "W" | "L" }) {
  return (
    <div className="w-6 h-6 rounded flex items-center justify-center" style={{
      background: result === "W" ? "rgba(34,197,94,0.15)" : "rgba(239,68,68,0.12)",
      border: `1px solid ${result === "W" ? "rgba(34,197,94,0.3)" : "rgba(239,68,68,0.25)"}`,
      fontFamily: "Rubik, sans-serif", fontSize: 10, fontWeight: 700,
      color: result === "W" ? "#22c55e" : "#ef4444",
    }}>
      {result}
    </div>
  );
}

function SectionCard({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`rounded-2xl p-5 ${className}`} style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)" }}>
      {children}
    </div>
  );
}

function SectionTitle({ icon: Icon, children, color = CYAN }: { icon: React.ElementType; children: React.ReactNode; color?: string }) {
  return (
    <div className="flex items-center gap-2 mb-4">
      <Icon size={14} color={color} />
      <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 13, fontWeight: 700, color: "white" }}>{children}</span>
    </div>
  );
}

// ── Tab Components ──────────────────────────────────────────────────────────

function OverviewTab({ game }: { game: Game }) {
  const t1 = game.team1, t2 = game.team2;
  const isPick1 = game.rotobotPick === t1.name || game.rotobotPick === t1.id;
  const pick = isPick1 ? t1 : t2;
  const conf = game.rotobotConfidence;

  return (
    <div className="flex flex-col gap-5">
      {/* Win probability */}
      <SectionCard>
        <SectionTitle icon={Target}>Win Probability</SectionTitle>
        <div className="flex items-center gap-4">
          <div className="flex-1 text-center">
            <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 28, fontWeight: 800, color: CYAN }}>
              {isPick1 ? conf : 100 - conf}%
            </div>
            <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 12, color: "rgba(255,255,255,0.5)" }}>{t1.shortName}</div>
          </div>
          <div className="flex-1 h-3 rounded-full overflow-hidden flex" style={{ background: "rgba(255,255,255,0.07)" }}>
            <div style={{ width: `${isPick1 ? conf : 100 - conf}%`, background: CYAN }} />
            <div style={{ flex: 1, background: BLUE }} />
          </div>
          <div className="flex-1 text-center">
            <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 28, fontWeight: 800, color: BLUE }}>
              {isPick1 ? 100 - conf : conf}%
            </div>
            <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 12, color: "rgba(255,255,255,0.5)" }}>{t2.shortName}</div>
          </div>
        </div>
      </SectionCard>

      {/* Pick + reasoning (the concise verdict) */}
      <SectionCard className="border-l-4" style={{ borderLeftColor: "#22c55e" }}>
        <div className="flex items-center gap-2 mb-2">
          <CheckCircle2 size={16} color="#22c55e" />
          <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 15, fontWeight: 700, color: "white" }}>
            RotoBot picks {pick.shortName} ({conf}%)
          </span>
        </div>
        {game.pickReasoning && (
          <p style={{ fontFamily: "Rubik, sans-serif", fontSize: 13, color: "rgba(255,255,255,0.6)", lineHeight: 1.7 }}>
            {game.pickReasoning}
          </p>
        )}
      </SectionCard>

      {/* Key edges — quick pro bullets for each team */}
      {(game.proTeam1?.length > 0 || game.proTeam2?.length > 0) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[
            { team: t1, pros: game.proTeam1, color: CYAN },
            { team: t2, pros: game.proTeam2, color: BLUE },
          ].map(({ team, pros, color }) => (
            <SectionCard key={team.id}>
              <div className="flex items-center gap-2 mb-2">
                <Zap size={12} color={color} />
                <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 12, fontWeight: 600, color: "white" }}>
                  {team.shortName} Edges
                </span>
              </div>
              <div className="flex flex-col gap-1.5">
                {(pros || []).slice(0, 2).map((pro, i) => (
                  <div key={i} className="flex items-start gap-2">
                    <CheckCircle2 size={10} color={color} className="mt-0.5 shrink-0" />
                    <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 11, color: "rgba(255,255,255,0.55)", lineHeight: 1.5 }}>
                      {pro}
                    </span>
                  </div>
                ))}
              </div>
            </SectionCard>
          ))}
        </div>
      )}

      {/* Recent form */}
      <div className="grid grid-cols-2 gap-4">
        {[t1, t2].map((team, i) => (
          <SectionCard key={team.id}>
            <div className="flex items-center gap-2 mb-3">
              <TeamLogo teamSlug={team.id} teamShortName={team.shortName} teamColor={team.color} size={16} />
              <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 12, fontWeight: 600, color: "white" }}>{team.shortName} Form</span>
            </div>
            <div className="flex gap-1.5">
              {team.recentForm.map((r, j) => <FormBadge key={j} result={r} />)}
            </div>
          </SectionCard>
        ))}
      </div>

      {!game.analysis && (
        <div className="text-center py-4" style={{ fontFamily: "Rubik, sans-serif", fontSize: 12, color: "rgba(255,255,255,0.3)" }}>
          Full analysis available in the RotoBot tab
        </div>
      )}
    </div>
  );
}

function StatsTab({ game }: { game: Game }) {
  const t1 = game.team1, t2 = game.team2;

  const radarData = [
    { stat: "PPG", t1: t1.ppg, t2: t2.ppg },
    { stat: "Def", t1: 100 - (t1.oppg / 1), t2: 100 - (t2.oppg / 1) },
    { stat: "eFG%", t1: t1.eFGPct, t2: t2.eFGPct },
    { stat: "Pace", t1: t1.pace, t2: t2.pace },
    { stat: "SOS", t1: Math.max(0, 100 - t1.sosRank / 3.6), t2: Math.max(0, 100 - t2.sosRank / 3.6) },
    { stat: "OREB%", t1: t1.orebPct, t2: t2.orebPct },
    { stat: "TOV%", t1: 100 - t1.tovPct, t2: 100 - t2.tovPct },
  ];

  const stats1 = t1.stats, stats2 = t2.stats;

  return (
    <div className="flex flex-col gap-5">
      {/* Radar */}
      <SectionCard>
        <SectionTitle icon={BarChart2}>Radar Comparison</SectionTitle>
        <div style={{ height: 280 }}>
          <ResponsiveContainer>
            <RadarChart data={radarData}>
              <PolarGrid stroke="rgba(255,255,255,0.1)" />
              <PolarAngleAxis dataKey="stat" tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 11, fontFamily: "Rubik" }} />
              <Radar name={t1.shortName} dataKey="t1" stroke={CYAN} fill={CYAN} fillOpacity={0.15} strokeWidth={2} />
              <Radar name={t2.shortName} dataKey="t2" stroke={BLUE} fill={BLUE} fillOpacity={0.15} strokeWidth={2} />
              <Tooltip contentStyle={{ background: "#0a0f1e", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, fontFamily: "Rubik" }} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </SectionCard>

      {/* Stat bars */}
      <SectionCard>
        <SectionTitle icon={Zap}>Head-to-Head Stats</SectionTitle>
        <div className="flex items-center justify-between mb-4">
          <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 12, fontWeight: 600, color: CYAN }}>{t1.shortName}</span>
          <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 12, fontWeight: 600, color: BLUE }}>{t2.shortName}</span>
        </div>
        <div className="flex flex-col gap-3">
          <StatBar label="PPG" val1={t1.ppg} val2={t2.ppg} />
          <StatBar label="Opp PPG" val1={t1.oppg} val2={t2.oppg} higherIsBetter={false} />
          <StatBar label="eFG%" val1={t1.eFGPct} val2={t2.eFGPct} />
          <StatBar label="Pace" val1={t1.pace} val2={t2.pace} />
          {stats1 && stats2 && (
            <>
              <StatBar label="FG% Def" val1={stats1.shooting.fgPctDefense} val2={stats2.shooting.fgPctDefense} higherIsBetter={false} />
              <StatBar label="3PT%" val1={stats1.shooting.threePtPct} val2={stats2.shooting.threePtPct} />
              <StatBar label="FT%" val1={stats1.shooting.ftPct} val2={stats2.shooting.ftPct} />
              <StatBar label="RPG" val1={stats1.rebounding.rpg} val2={stats2.rebounding.rpg} />
              <StatBar label="APG" val1={stats1.ballControl.apg} val2={stats2.ballControl.apg} />
              <StatBar label="A/TO" val1={stats1.ballControl.astToRatio} val2={stats2.ballControl.astToRatio} />
              <StatBar label="BPG" val1={stats1.defense.bpg} val2={stats2.defense.bpg} />
              <StatBar label="SPG" val1={stats1.defense.spg} val2={stats2.defense.spg} />
              <StatBar label="Bench PPG" val1={stats1.scoring.benchPPG} val2={stats2.scoring.benchPPG} />
            </>
          )}
          <StatBar label="NET Rank" val1={t1.netRank} val2={t2.netRank} higherIsBetter={false} />
          <StatBar label="SOS Rank" val1={t1.sosRank} val2={t2.sosRank} higherIsBetter={false} />
        </div>
      </SectionCard>
    </div>
  );
}

function PlayerCard({ p, color, isBench, headshot }: { p: PlayerRecord; color: string; isBench: boolean; headshot?: string }) {
  const [imgErr, setImgErr] = useState(false);
  return (
    <div className="flex items-start gap-3 p-3 rounded-xl" style={{
      background: isBench ? "rgba(255,255,255,0.015)" : "rgba(255,255,255,0.03)",
      border: `1px solid ${isBench ? "rgba(255,255,255,0.03)" : "rgba(255,255,255,0.05)"}`,
    }}>
      {headshot && !imgErr ? (
        <img src={headshot} alt={p.name} onError={() => setImgErr(true)} loading="lazy"
          className="w-10 h-10 rounded-lg object-cover shrink-0"
          style={{ background: `${color}18`, border: `1px solid ${color}33` }} />
      ) : (
        <div className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0" style={{ background: `${color}18`, border: `1px solid ${color}33` }}>
          <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 10, fontWeight: 700, color }}>{p.position || "?"}</span>
        </div>
      )}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 13, fontWeight: 600, color: "white" }}>{p.name}</span>
          {isBench && <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 9, color: "rgba(245,158,11,0.7)", background: "rgba(245,158,11,0.1)", padding: "1px 5px", borderRadius: 4 }}>BENCH</span>}
        </div>
        <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 10, color: "rgba(255,255,255,0.4)" }}>
          {p.height ? `${p.height} • ` : ""}{p.class ? `${p.class} • ` : ""}{p.gamesPlayed} GP • {p.stats.mpg} MPG
        </div>
        <div className="flex gap-2.5 mt-1.5">
          {[
            { label: "PPG", val: p.stats.ppg },
            { label: "RPG", val: p.stats.rpg },
            { label: "APG", val: p.stats.apg },
            { label: "FG%", val: p.stats.fgPct },
            { label: "3P%", val: p.stats.threePtPct },
            { label: "FT%", val: p.stats.ftPct },
          ].map(({ label, val }) => (
            <div key={label} className="text-center">
              <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 12, fontWeight: 700, color: "white" }}>
                {val ?? "-"}
              </div>
              <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 8, color: "rgba(255,255,255,0.3)" }}>{label}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function PlayersTab({ game }: { game: Game }) {
  const [players1, setPlayers1] = useState<PlayerRecord[]>([]);
  const [players2, setPlayers2] = useState<PlayerRecord[]>([]);
  const [headshots, setHeadshots] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetchTeamPlayers(game.team1.id).catch(() => []),
      fetchTeamPlayers(game.team2.id).catch(() => []),
    ]).then(([p1, p2]) => {
      setPlayers1(p1);
      setPlayers2(p2);
      setLoading(false);
    });

    Promise.all([
      fetchEspnRoster(game.team1.id).catch(() => []),
      fetchEspnRoster(game.team2.id).catch(() => []),
    ]).then(([r1, r2]) => {
      const map: Record<string, string> = {};
      for (const a of [...r1, ...r2]) {
        if (a.headshot) map[a.name.toLowerCase()] = a.headshot;
      }
      setHeadshots(map);
    });
  }, [game.team1.id, game.team2.id]);

  const getHeadshot = (name: string) => {
    const lower = name.toLowerCase();
    if (headshots[lower]) return headshots[lower];
    const lastName = lower.split(" ").pop() || "";
    for (const [k, v] of Object.entries(headshots)) {
      if (k.endsWith(lastName) || k.includes(lastName)) return v;
    }
    return undefined;
  };

  if (loading) {
    return <div className="flex justify-center py-12"><Loader2 size={24} className="animate-spin" color={CYAN} /></div>;
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
      {[
        { team: game.team1, players: players1, color: CYAN },
        { team: game.team2, players: players2, color: BLUE },
      ].map(({ team, players, color }) => {
        const starters = players.filter(p => p.gamesStarted > (p.gamesPlayed * 0.4));
        const bench = players.filter(p => p.gamesStarted <= (p.gamesPlayed * 0.4));

        return (
          <SectionCard key={team.id}>
            <div className="flex items-center gap-2 mb-4">
              <TeamLogo teamSlug={team.id} teamShortName={team.shortName} teamColor={team.color} size={20} />
              <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 13, fontWeight: 700, color: "white" }}>
                {team.shortName} Roster ({players.length})
              </span>
            </div>
            {players.length === 0 ? (
              <p style={{ fontFamily: "Rubik, sans-serif", fontSize: 12, color: "rgba(255,255,255,0.3)" }}>No player data available</p>
            ) : (
              <div className="flex flex-col gap-2">
                {starters.length > 0 && (
                  <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 10, fontWeight: 600, color: "rgba(255,255,255,0.3)", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: 2 }}>
                    Starters
                  </div>
                )}
                {starters.map((p) => <PlayerCard key={p.name} p={p} color={color} isBench={false} headshot={getHeadshot(p.name)} />)}
                {bench.length > 0 && (
                  <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 10, fontWeight: 600, color: "rgba(245,158,11,0.6)", textTransform: "uppercase", letterSpacing: "0.5px", marginTop: 4, marginBottom: 2 }}>
                    Key Bench
                  </div>
                )}
                {bench.map((p) => <PlayerCard key={p.name} p={p} color={color} isBench={true} headshot={getHeadshot(p.name)} />)}
              </div>
            )}
          </SectionCard>
        );
      })}
    </div>
  );
}

function StyleTab({ game }: { game: Game }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
      {[
        { team: game.team1, color: CYAN },
        { team: game.team2, color: BLUE },
      ].map(({ team, color }) => (
        <SectionCard key={team.id}>
          <div className="flex items-center gap-2 mb-4">
            <div className="w-3 h-3 rounded-full" style={{ background: color }} />
            <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 13, fontWeight: 700, color: "white" }}>
              {team.shortName}
            </span>
          </div>

          {/* Style tags */}
          {team.styleTags && team.styleTags.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-4">
              {team.styleTags.filter(t => t && t !== "nan").map((tag) => (
                <span key={tag} className="px-2.5 py-1 rounded-full" style={{
                  background: `${color}15`, border: `1px solid ${color}30`,
                  fontFamily: "Rubik, sans-serif", fontSize: 11, fontWeight: 500, color,
                }}>
                  {tag}
                </span>
              ))}
            </div>
          )}

          {/* Identity */}
          {team.styleIdentity && (
            <div className="mb-3">
              <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 10, fontWeight: 600, color: "rgba(255,255,255,0.35)", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: 4 }}>Identity</div>
              <p style={{ fontFamily: "Rubik, sans-serif", fontSize: 13, color: "rgba(255,255,255,0.7)", lineHeight: 1.6 }}>
                {team.styleIdentity}
              </p>
            </div>
          )}

          {/* Bullets */}
          {team.styleBullets && (
            <div className="mb-3">
              <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 10, fontWeight: 600, color: "rgba(255,255,255,0.35)", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: 4 }}>Key Numbers</div>
              <p style={{ fontFamily: "Rubik, sans-serif", fontSize: 12, color: "rgba(255,255,255,0.55)", lineHeight: 1.6 }}>
                {team.styleBullets}
              </p>
            </div>
          )}

          {/* Weakness */}
          {team.styleWeakness && (
            <div className="p-3 rounded-xl" style={{ background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.15)" }}>
              <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 10, fontWeight: 600, color: "#ef4444", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: 4 }}>Weakness</div>
              <p style={{ fontFamily: "Rubik, sans-serif", fontSize: 12, color: "rgba(255,255,255,0.55)", lineHeight: 1.5 }}>
                {team.styleWeakness}
              </p>
            </div>
          )}

          {/* Schedule */}
          {team.stats?.schedule && (
            <div className="mt-3 flex gap-2">
              {Object.entries(team.stats.schedule).map(([key, val]) => (
                <div key={key} className="flex-1 text-center p-2 rounded-lg" style={{ background: "rgba(255,255,255,0.03)" }}>
                  <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 12, fontWeight: 600, color: "white" }}>{val || "0-0"}</div>
                  <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 9, color: "rgba(255,255,255,0.3)" }}>{key.replace("Record", "")}</div>
                </div>
              ))}
            </div>
          )}
        </SectionCard>
      ))}
    </div>
  );
}

function NewsTab({ game }: { game: Game }) {
  const [news, setNews] = useState<Record<string, string>>({});
  const [fetching, setFetching] = useState<Record<string, boolean>>({});

  const loadNews = async (slug: string) => {
    if (news[slug] || fetching[slug]) return;
    setFetching((f) => ({ ...f, [slug]: true }));
    try {
      const { fetchNewsLive } = await import("../lib/api");
      const res = await fetchNewsLive(slug);
      if (res.news) setNews((n) => ({ ...n, [slug]: res.news }));
    } catch (err) {
      console.error("News fetch failed:", err);
    } finally {
      setFetching((f) => ({ ...f, [slug]: false }));
    }
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
      {[
        { team: game.team1, color: CYAN },
        { team: game.team2, color: BLUE },
      ].map(({ team, color }) => (
        <SectionCard key={team.id}>
          <div className="flex items-center gap-2 mb-4">
            <Newspaper size={14} color={color} />
            <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 13, fontWeight: 700, color: "white" }}>{team.shortName} Context</span>
          </div>

          <div className="flex flex-col gap-3">
            {/* Recent form */}
            <div>
              <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 10, fontWeight: 600, color: "rgba(255,255,255,0.35)", textTransform: "uppercase", marginBottom: 6 }}>Recent Form</div>
              <div className="flex gap-1.5">
                {team.recentForm.map((r, i) => <FormBadge key={i} result={r} />)}
              </div>
            </div>

            {/* Key player */}
            {team.keyPlayer && (
              <div>
                <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 10, fontWeight: 600, color: "rgba(255,255,255,0.35)", textTransform: "uppercase", marginBottom: 4 }}>Star Player</div>
                <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 13, fontWeight: 600, color: "white" }}>{team.keyPlayer}</div>
                <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 11, color: "rgba(255,255,255,0.5)" }}>{team.keyPlayerStat}</div>
              </div>
            )}

            {/* Perplexity news */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 10, fontWeight: 600, color: "rgba(255,255,255,0.35)", textTransform: "uppercase" }}>
                  Real-Time News & Injuries
                </div>
                {!news[team.id] && !fetching[team.id] && (
                  <button
                    onClick={() => loadNews(team.id)}
                    className="px-2 py-1 rounded-lg transition-all hover:opacity-80"
                    style={{
                      background: "rgba(0,184,219,0.1)", border: "1px solid rgba(0,184,219,0.2)",
                      fontFamily: "Rubik, sans-serif", fontSize: 10, fontWeight: 600, color: "#00b8db", cursor: "pointer",
                    }}
                  >
                    Fetch from Perplexity
                  </button>
                )}
              </div>
              {fetching[team.id] && (
                <div className="flex items-center gap-2 py-2">
                  <Loader2 size={12} className="animate-spin" color={color} />
                  <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 11, color: "rgba(255,255,255,0.4)" }}>Searching latest news...</span>
                </div>
              )}
              {news[team.id] && (
                <div className="flex flex-col gap-2">
                  {cleanNewsText(news[team.id]).map((line, i) => (
                    <div key={i} className="flex items-start gap-2 py-1.5 px-2.5 rounded-lg"
                      style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.04)" }}>
                      <Newspaper size={10} color={color} className="mt-0.5 shrink-0" />
                      <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 12, color: "rgba(255,255,255,0.65)", lineHeight: 1.6 }}>
                        {line}
                      </span>
                    </div>
                  ))}
                </div>
              )}
              {!news[team.id] && !fetching[team.id] && (
                <p style={{ fontFamily: "Rubik, sans-serif", fontSize: 11, color: "rgba(255,255,255,0.25)" }}>
                  Click "Fetch from Perplexity" to get the latest injury reports and news.
                </p>
              )}
            </div>

            {/* RotoBot blurb */}
            {team.rotobotBlurb && (
              <div>
                <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 10, fontWeight: 600, color: "rgba(255,255,255,0.35)", textTransform: "uppercase", marginBottom: 4 }}>Scouting Report</div>
                <p style={{ fontFamily: "Rubik, sans-serif", fontSize: 12, color: "rgba(255,255,255,0.55)", lineHeight: 1.6 }}>
                  {team.rotobotBlurb}
                </p>
              </div>
            )}
          </div>
        </SectionCard>
      ))}
    </div>
  );
}

function RotoBotTab({ game }: { game: Game }) {
  const { requestNarrative, isNarrativeLoading } = useBracket();
  const isPick1 = game.rotobotPick === game.team1.name || game.rotobotPick === game.team1.id;
  const pick = isPick1 ? game.team1 : game.team2;
  const loading = isNarrativeLoading(game.team1.id, game.team2.id);
  const hasAnalysis = !!game.analysis;

  return (
    <div className="flex flex-col gap-5">
      {/* Loading state for live games */}
      {!hasAnalysis && loading && (
        <SectionCard>
          <div className="flex items-center gap-3 py-4">
            <Loader2 size={18} className="animate-spin" color={CYAN} />
            <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 13, color: "rgba(0,184,219,0.7)" }}>
              RotoBot is generating analysis for this matchup...
            </span>
          </div>
        </SectionCard>
      )}

      {/* Generate button for live games without analysis */}
      {!hasAnalysis && !loading && (
        <SectionCard>
          <div className="flex flex-col items-center gap-3 py-4">
            <Brain size={24} color="rgba(255,255,255,0.2)" />
            <p style={{ fontFamily: "Rubik, sans-serif", fontSize: 12, color: "rgba(255,255,255,0.4)", textAlign: "center" }}>
              This matchup was created from your picks. Generate AI analysis?
            </p>
            <button
              onClick={() => requestNarrative(game.team1.id, game.team2.id, game.round, game.region)}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl transition-all hover:opacity-90"
              style={{ background: "linear-gradient(135deg, #00b8db 0%, #3c84ff 100%)", border: "none", cursor: "pointer", fontFamily: "Rubik, sans-serif", fontSize: 12, fontWeight: 600, color: "white" }}>
              <Brain size={13} /> Generate Matchup Analysis
            </button>
          </div>
        </SectionCard>
      )}

      {/* Full analysis */}
      {hasAnalysis && (
        <SectionCard>
          <SectionTitle icon={Brain}>Full Matchup Analysis</SectionTitle>
          <p style={{ fontFamily: "Rubik, sans-serif", fontSize: 14, color: "rgba(255,255,255,0.7)", lineHeight: 1.8 }}>
            {game.analysis}
          </p>
        </SectionCard>
      )}

      {/* Pros/cons */}
      {(game.proTeam1?.length > 0 || game.proTeam2?.length > 0) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {[
            { team: game.team1, pros: game.proTeam1, color: CYAN },
            { team: game.team2, pros: game.proTeam2, color: BLUE },
          ].map(({ team, pros, color }) => (
            <SectionCard key={team.id}>
              <div className="flex items-center gap-2 mb-3">
                <TeamLogo teamSlug={team.id} teamShortName={team.shortName} teamColor={team.color} size={16} />
                <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 13, fontWeight: 700, color: "white" }}>
                  Why {team.shortName} Wins
                </span>
              </div>
              <div className="flex flex-col gap-2">
                {(pros || []).map((pro, i) => (
                  <div key={i} className="flex items-start gap-2">
                    <CheckCircle2 size={12} color={color} className="mt-0.5 shrink-0" />
                    <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 12, color: "rgba(255,255,255,0.6)", lineHeight: 1.5 }}>
                      {pro}
                    </span>
                  </div>
                ))}
              </div>
            </SectionCard>
          ))}
        </div>
      )}

      {/* Pick + reasoning */}
      {hasAnalysis && (
        <SectionCard className="border-l-4" style={{ borderLeftColor: "#22c55e" }}>
          <div className="flex items-center gap-2 mb-3">
            <CheckCircle2 size={16} color="#22c55e" />
            <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 15, fontWeight: 700, color: "white" }}>
              RotoBot picks {pick.shortName} ({game.rotobotConfidence}% confidence)
            </span>
          </div>
          {game.pickReasoning && (
            <p style={{ fontFamily: "Rubik, sans-serif", fontSize: 13, color: "rgba(255,255,255,0.6)", lineHeight: 1.7 }}>
              {game.pickReasoning}
            </p>
          )}
        </SectionCard>
      )}
    </div>
  );
}

function TrendsTab({ game }: { game: Game }) {
  const [trends, setTrends] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [fetched, setFetched] = useState(false);

  const handleFetch = async () => {
    setLoading(true);
    try {
      const res = await fetchTrends(game.team1.id, game.team2.id);
      setTrends(res.trends || "No trend data available.");
      setFetched(true);
    } catch (err) {
      setTrends("Failed to fetch trends. Check your Perplexity API key.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <SectionCard>
      <div className="flex items-center gap-2 mb-4">
        <History size={14} color={CYAN} />
        <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 14, fontWeight: 700, color: "white" }}>
          Historical Tournament Trends
        </span>
      </div>
      <p className="mb-4" style={{ fontFamily: "Rubik, sans-serif", fontSize: 11, color: "rgba(255,255,255,0.45)", lineHeight: 1.5 }}>
        Perplexity searches the web for historical NCAA Tournament data relevant to this specific matchup — seed-line win rates, conference trends, style-clash history, and upset patterns.
      </p>
      {!fetched && !loading && (
        <button onClick={handleFetch} className="flex items-center gap-2 px-4 py-2.5 rounded-xl transition-all hover:opacity-90"
          style={{ background: "linear-gradient(135deg, #00b8db 0%, #3c84ff 100%)", border: "none", cursor: "pointer", fontFamily: "Rubik, sans-serif", fontSize: 12, fontWeight: 600, color: "white" }}>
          <History size={13} /> Research Tournament Trends
        </button>
      )}
      {loading && (
        <div className="flex items-center gap-2 py-6">
          <Loader2 size={16} className="animate-spin" color={CYAN} />
          <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 12, color: "rgba(0,184,219,0.7)" }}>
            Searching tournament history...
          </span>
        </div>
      )}
      {fetched && trends && (
        <div className="flex flex-col gap-2 mt-2">
          {cleanNewsText(trends).map((line, i) => (
            <div key={i} className="flex items-start gap-2 py-1.5 px-2.5 rounded-lg"
              style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.04)" }}>
              <TrendingUp size={10} color={CYAN} className="mt-0.5 shrink-0" />
              <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 12, color: "rgba(255,255,255,0.65)", lineHeight: 1.6 }}>
                {line}
              </span>
            </div>
          ))}
        </div>
      )}
    </SectionCard>
  );
}

// ── Tabs Config ─────────────────────────────────────────────────────────────

const TABS = [
  { id: "overview", label: "Overview", icon: Target },
  { id: "stats", label: "Stats", icon: BarChart2 },
  { id: "players", label: "Players", icon: Users },
  { id: "style", label: "Style", icon: Shield },
  { id: "news", label: "News", icon: Newspaper },
  { id: "trends", label: "Trends", icon: History },
  { id: "rotobot", label: "RotoBot", icon: Brain },
] as const;

type TabId = (typeof TABS)[number]["id"];

// ── Main Component ──────────────────────────────────────────────────────────

export function MatchupScreen() {
  const { id } = useParams();
  const { findGameById, makePick, state } = useBracket();
  const [activeTab, setActiveTab] = useState<TabId>("overview");

  const game = id ? findGameById(id) : undefined;

  if (!state.dataLoaded) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: "#030712" }}>
        <Loader2 size={32} className="animate-spin" color={CYAN} />
      </div>
    );
  }

  if (!game) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4" style={{ background: "#030712" }}>
        <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 18, fontWeight: 700, color: "white" }}>
          Matchup not found
        </span>
        <Link to="/bracket" className="no-underline" style={{ fontFamily: "Rubik, sans-serif", fontSize: 14, color: CYAN }}>
          Back to bracket
        </Link>
      </div>
    );
  }

  const t1 = game.team1, t2 = game.team2;
  const isPick1 = game.rotobotPick === t1.name || game.rotobotPick === t1.id;

  return (
    <div className="min-h-screen pt-16 pb-20 md:pb-8"
      style={{ background: "linear-gradient(160deg, #010c2a 0%, #030712 40%, #00081e 100%)" }}>
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6 relative">
        {/* Back */}
        <Link to="/bracket" className="no-underline flex items-center gap-1.5 mb-6"
          style={{ fontFamily: "Rubik, sans-serif", fontSize: 13, color: "rgba(255,255,255,0.5)" }}>
          <ChevronLeft size={14} /> Back to bracket
        </Link>

        {/* Team headers */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          {[
            { team: t1, color: CYAN, isPick: isPick1, side: "left" as const },
            { team: t2, color: BLUE, isPick: !isPick1, side: "right" as const },
          ].map(({ team, color, isPick, side }) => (
            <div key={team.id} className="rounded-2xl p-5" style={{
              background: `linear-gradient(135deg, ${color}08, ${color}03)`,
              border: `1px solid ${color}22`,
            }}>
              <div className={`flex items-center gap-3 ${side === "right" ? "flex-row-reverse" : ""}`}>
                <TeamLogo teamSlug={team.id} teamShortName={team.shortName} teamColor={team.color} size={56} />
                <div style={{ textAlign: side === "right" ? "right" : "left" }}>
                  <div className="flex items-center gap-2" style={{ justifyContent: side === "right" ? "flex-end" : "flex-start" }}>
                    <span className="px-1.5 py-0.5 rounded" style={{
                      background: `${color}22`, fontFamily: "Rubik, sans-serif", fontSize: 11, fontWeight: 700, color,
                    }}>
                      #{team.seed}
                    </span>
                    <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 18, fontWeight: 800, color: "white" }}>
                      {team.shortName}
                    </span>
                    {isPick && <Brain size={14} color={color} />}
                  </div>
                  <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 12, color: "rgba(255,255,255,0.4)" }}>
                    {team.record} • {team.conference} • NET #{team.netRank}
                  </div>
                </div>
              </div>

              {/* Quick stats row */}
              <div className="flex items-center gap-2 mt-3 flex-wrap">
                <div className="flex items-center gap-1 px-2 py-1 rounded-lg" style={{ background: "rgba(255,255,255,0.04)" }}>
                  <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 10, color: "rgba(255,255,255,0.35)" }}>PPG</span>
                  <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 11, fontWeight: 700, color: "white" }}>{team.ppg}</span>
                </div>
                <div className="flex items-center gap-1 px-2 py-1 rounded-lg" style={{ background: "rgba(255,255,255,0.04)" }}>
                  <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 10, color: "rgba(255,255,255,0.35)" }}>eFG%</span>
                  <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 11, fontWeight: 700, color: "white" }}>{team.eFGPct}</span>
                </div>
                <div className="flex items-center gap-1 px-2 py-1 rounded-lg" style={{ background: "rgba(255,255,255,0.04)" }}>
                  <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 10, color: "rgba(255,255,255,0.35)" }}>Score</span>
                  <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 11, fontWeight: 700, color }}>{team.rotobotScore}</span>
                </div>
              </div>

              {/* Style tags */}
              {team.styleTags && team.styleTags.filter(t => t && t !== "nan").length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {team.styleTags.filter(t => t && t !== "nan").map((tag) => (
                    <span key={tag} className="px-2 py-0.5 rounded-full" style={{
                      background: `${color}10`, border: `1px solid ${color}25`,
                      fontFamily: "Rubik, sans-serif", fontSize: 10, color: `${color}cc`,
                    }}>
                      {tag}
                    </span>
                  ))}
                </div>
              )}

              {/* Make your pick */}
              <button
                onClick={() => makePick(game.id, team.id)}
                className="w-full mt-3 py-2 rounded-xl transition-all hover:opacity-80"
                style={{
                  background: state.userPicks[game.id] === team.id ? `${color}33` : "rgba(255,255,255,0.05)",
                  border: state.userPicks[game.id] === team.id ? `1px solid ${color}55` : "1px solid rgba(255,255,255,0.1)",
                  fontFamily: "Rubik, sans-serif", fontSize: 12, fontWeight: 600,
                  color: state.userPicks[game.id] === team.id ? color : "rgba(255,255,255,0.5)",
                  cursor: "pointer",
                }}
              >
                {state.userPicks[game.id] === team.id ? "Your Pick" : "Pick " + team.shortName}
              </button>
            </div>
          ))}
        </div>

        {/* Tabs */}
        <div className="flex gap-1 p-1 rounded-xl mb-6 overflow-x-auto"
          style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.07)" }}>
          {TABS.map(({ id: tabId, label, icon: Icon }) => (
            <button
              key={tabId}
              onClick={() => setActiveTab(tabId)}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg transition-all whitespace-nowrap"
              style={{
                fontFamily: "Rubik, sans-serif", fontSize: 12,
                fontWeight: activeTab === tabId ? 600 : 400,
                color: activeTab === tabId ? "white" : "rgba(255,255,255,0.4)",
                background: activeTab === tabId ? "rgba(0,184,219,0.12)" : "transparent",
                border: activeTab === tabId ? "1px solid rgba(0,184,219,0.2)" : "1px solid transparent",
                cursor: "pointer",
              }}
            >
              <Icon size={12} />
              {label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        {activeTab === "overview" && <OverviewTab game={game} />}
        {activeTab === "stats" && <StatsTab game={game} />}
        {activeTab === "players" && <PlayersTab game={game} />}
        {activeTab === "style" && <StyleTab game={game} />}
        {activeTab === "news" && <NewsTab game={game} />}
        {activeTab === "trends" && <TrendsTab game={game} />}
        {activeTab === "rotobot" && <RotoBotTab game={game} />}
      </div>
    </div>
  );
}
