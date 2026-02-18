import { useState, useEffect } from "react";
import { useSearchParams } from "react-router";
import { Download, Brain, CheckCircle, Share2, Loader2, Trophy } from "lucide-react";
import { BracketGameCard, BracketConnector } from "./BracketGame";
import { useBracket } from "../context/BracketContext";
import type { Game, ViewMode } from "../types/bracket";

// ── Sub-components ──────────────────────────────────────────────────────────

function RoundColumn({
  games,
  label,
  userPicks,
  onPick,
  totalHeight,
  loadingIds,
  viewMode,
}: {
  games: Game[];
  label: string;
  userPicks: Record<string, string>;
  onPick: (gameId: string, teamId: string) => void;
  totalHeight: number;
  loadingIds?: Set<string>;
  viewMode: ViewMode;
}) {
  if (games.length === 0) {
    return (
      <div className="flex flex-col" style={{ height: totalHeight, width: 210 }}>
        <div className="text-center pb-2">
          <span style={{
            fontFamily: "Rubik, sans-serif", fontSize: 10, fontWeight: 700,
            color: "rgba(255,255,255,0.15)", textTransform: "uppercase", letterSpacing: "1px",
          }}>
            {label}
          </span>
        </div>
        <div className="flex flex-col flex-1 items-center justify-center">
          <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 11, color: "rgba(255,255,255,0.15)" }}>
            Pick winners to advance
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col" style={{ height: totalHeight, width: 210 }}>
      <div className="text-center pb-2">
        <span style={{
          fontFamily: "Rubik, sans-serif", fontSize: 10, fontWeight: 700,
          color: "rgba(255,255,255,0.3)", textTransform: "uppercase", letterSpacing: "1px",
        }}>
          {label}
        </span>
      </div>
      <div className="flex flex-col flex-1" style={{ justifyContent: "space-around", gap: 0 }}>
        {games.map((game) => (
          <div key={game.id} className="flex items-center justify-center">
            <BracketGameCard
              game={game}
              userPick={userPicks[game.id]}
              onPick={onPick}
              isLoading={loadingIds?.has(game.id)}
              viewMode={viewMode}
            />
          </div>
        ))}
      </div>
    </div>
  );
}

function ConnectorColumn({ fromCount, totalHeight }: { fromCount: number; totalHeight: number }) {
  if (fromCount === 0) return <div style={{ width: 32, height: totalHeight }} />;
  return (
    <div style={{ height: totalHeight, paddingTop: 24 }}>
      <BracketConnector count={fromCount} height={totalHeight - 24} />
    </div>
  );
}

function RegionBracket({
  region,
  userPicks,
  onPick,
  viewMode,
}: {
  region: string;
  userPicks: Record<string, string>;
  onPick: (gameId: string, teamId: string) => void;
  viewMode: ViewMode;
}) {
  const { getRegionGames, getRegionWinnerTeam, state } = useBracket();
  const { r1, r2, s16, e8 } = getRegionGames(region);
  const winner = getRegionWinnerTeam(region);
  const BRACKET_H = 780;

  return (
    <div className="overflow-x-auto pb-4">
      <div style={{ display: "flex", gap: 0, alignItems: "stretch", minWidth: 1000, paddingBottom: 8 }}>
        <RoundColumn games={r1} label="First Round (R64)" userPicks={userPicks} onPick={onPick} totalHeight={BRACKET_H} viewMode={viewMode} />
        <ConnectorColumn fromCount={r1.length} totalHeight={BRACKET_H} />

        <RoundColumn games={r2} label="Second Round" userPicks={userPicks} onPick={onPick} totalHeight={BRACKET_H} viewMode={viewMode} />
        <ConnectorColumn fromCount={r2.length} totalHeight={BRACKET_H} />

        <RoundColumn games={s16} label="Sweet 16" userPicks={userPicks} onPick={onPick} totalHeight={BRACKET_H} viewMode={viewMode} />
        <ConnectorColumn fromCount={s16.length} totalHeight={BRACKET_H} />

        <div className="flex flex-col" style={{ height: BRACKET_H, width: 210 }}>
          <div className="text-center pb-2">
            <span style={{
              fontFamily: "Rubik, sans-serif", fontSize: 10, fontWeight: 700,
              color: "#00b8db", textTransform: "uppercase", letterSpacing: "1px",
            }}>
              Elite 8
            </span>
          </div>
          <div className="flex flex-col flex-1 items-center justify-center">
            {e8.length > 0 ? (
              <>
                <BracketGameCard game={e8[0]} userPick={userPicks[e8[0].id]} onPick={onPick} viewMode={viewMode} />
                {winner && (
                  <div className="mt-3 px-3 py-2 rounded-xl" style={{
                    background: "rgba(0,184,219,0.08)",
                    border: "1px solid rgba(0,184,219,0.2)",
                    maxWidth: 210,
                  }}>
                    <div className="flex items-center gap-1.5 mb-1">
                      <Trophy size={10} color="#00b8db" />
                      <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 10, color: "#00b8db", fontWeight: 600 }}>
                        Regional Champion
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 rounded shrink-0" style={{ background: `${winner.color}33` }} />
                      <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 12, fontWeight: 700, color: "white" }}>
                        {winner.shortName}
                      </span>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 11, color: "rgba(255,255,255,0.15)" }}>
                Pick winners to advance
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Main Component ──────────────────────────────────────────────────────────

const REGIONS = ["East", "West", "South", "Midwest"];
const REGION_COLORS: Record<string, string> = {
  East: "#00b8db",
  West: "#3c84ff",
  South: "#22c55e",
  Midwest: "#f59e0b",
};

export function BracketScreen() {
  const {
    state,
    makePick,
    clearPicks,
    setViewMode,
    getShareURL,
    getFinalFourTeams,
    requestNarrative,
    getRegionGames,
  } = useBracket();

  const [searchParams] = useSearchParams();
  const initialRegion = searchParams.get("region") || "East";
  const [activeRegion, setActiveRegion] = useState(initialRegion);
  const [copied, setCopied] = useState(false);

  const { userPicks, viewMode, dataLoaded, dataError } = state;

  const pickedCount = Object.keys(userPicks).length;
  const totalGames = 63;
  const progress = Math.round((pickedCount / totalGames) * 100);

  const ffTeams = getFinalFourTeams();
  const ffUnlocked = ffTeams.every((t) => t !== null);

  // Auto-request narratives for newly formed later-round games
  const { r2, s16, e8 } = getRegionGames(activeRegion);
  useEffect(() => {
    const liveGames = [...r2, ...s16, ...e8].filter((g) => g.isLive);
    for (const g of liveGames) {
      if (g.team1?.id && g.team2?.id && !g.analysis) {
        requestNarrative(g.team1.id, g.team2.id, g.round, g.region);
      }
    }
  }, [r2, s16, e8, requestNarrative]);

  const handlePick = (gameId: string, teamId: string) => {
    if (viewMode === "rotobot") {
      setViewMode("user");
    }
    makePick(gameId, teamId);
  };

  const handleShare = async () => {
    const url = getShareURL();
    await navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!dataLoaded) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: "#030712" }}>
        <div className="flex flex-col items-center gap-4">
          <Loader2 size={32} className="animate-spin" color="#00b8db" />
          <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 14, color: "rgba(255,255,255,0.5)" }}>
            Loading bracket data...
          </span>
        </div>
      </div>
    );
  }

  if (dataError) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: "#030712" }}>
        <div className="flex flex-col items-center gap-4 max-w-md text-center">
          <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 16, fontWeight: 700, color: "#ef4444" }}>
            Failed to load data
          </span>
          <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 13, color: "rgba(255,255,255,0.5)" }}>
            {dataError}
          </span>
          <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 12, color: "rgba(255,255,255,0.3)" }}>
            Make sure the API server is running on port 8002
          </span>
        </div>
      </div>
    );
  }

  return (
    <div
      className="min-h-screen pt-16 pb-20 md:pb-8"
      style={{ background: "linear-gradient(160deg, #010c2a 0%, #030712 40%, #00081e 100%)" }}
    >
      <div
        className="fixed pointer-events-none"
        style={{
          top: "10%", right: "0%", width: 500, height: 500,
          background: "radial-gradient(ellipse, rgba(60,132,255,0.07) 0%, transparent 70%)",
        }}
      />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 relative">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center gap-4 mb-6">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-1">
              <h1 style={{ fontFamily: "Rubik, sans-serif", fontSize: 24, fontWeight: 800, color: "white", margin: 0 }}>
                2026 NCAA Tournament Bracket
              </h1>
              <div
                className="px-2 py-0.5 rounded-full"
                style={{
                  background: "rgba(245,158,11,0.15)",
                  border: "1px solid rgba(245,158,11,0.3)",
                  fontFamily: "Rubik, sans-serif", fontSize: 10, fontWeight: 700,
                  color: "#f59e0b", textTransform: "uppercase", letterSpacing: "0.5px",
                }}
              >
                Projections
              </div>
            </div>
            <p style={{ fontFamily: "Rubik, sans-serif", fontSize: 13, color: "rgba(255,255,255,0.4)" }}>
              {viewMode === "user"
                ? "Make your picks — click a team to advance them."
                : "Viewing RotoBot's AI-generated bracket predictions."}
            </p>
          </div>

          {/* Progress */}
          <div
            className="flex items-center gap-4 px-4 py-3 rounded-xl"
            style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)" }}
          >
            <div className="flex flex-col gap-1">
              <div className="flex items-center justify-between gap-6">
                <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 11, color: "rgba(255,255,255,0.4)" }}>
                  My Picks
                </span>
                <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 11, fontWeight: 700, color: "#00b8db" }}>
                  {pickedCount}/{totalGames}
                </span>
              </div>
              <div className="h-1.5 w-40 rounded-full" style={{ background: "rgba(255,255,255,0.08)" }}>
                <div
                  className="h-full rounded-full transition-all"
                  style={{
                    width: `${progress}%`,
                    background: "linear-gradient(90deg, #00b8db, #3c84ff)",
                  }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Controls row */}
        <div className="flex flex-col sm:flex-row gap-3 mb-6">
          {/* Region tabs */}
          <div
            className="flex gap-1 p-1 rounded-xl flex-wrap"
            style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.07)" }}
          >
            {REGIONS.map((region) => (
              <button
                key={region}
                onClick={() => setActiveRegion(region)}
                className="flex items-center gap-2 px-4 py-2 rounded-lg transition-all"
                style={{
                  fontFamily: "Rubik, sans-serif", fontSize: 13,
                  fontWeight: activeRegion === region ? 700 : 400,
                  color: activeRegion === region ? "white" : "rgba(255,255,255,0.45)",
                  background: activeRegion === region ? `${REGION_COLORS[region]}22` : "transparent",
                  border: activeRegion === region ? `1px solid ${REGION_COLORS[region]}44` : "1px solid transparent",
                  cursor: "pointer",
                }}
              >
                <div
                  className="w-2 h-2 rounded-full"
                  style={{ background: REGION_COLORS[region], opacity: activeRegion === region ? 1 : 0.3 }}
                />
                {region}
              </button>
            ))}

            {ffUnlocked && (
              <button
                onClick={() => setActiveRegion("FinalFour")}
                className="flex items-center gap-2 px-4 py-2 rounded-lg transition-all"
                style={{
                  fontFamily: "Rubik, sans-serif", fontSize: 13,
                  fontWeight: activeRegion === "FinalFour" ? 700 : 400,
                  color: activeRegion === "FinalFour" ? "white" : "#f59e0b",
                  background: activeRegion === "FinalFour" ? "rgba(245,158,11,0.2)" : "transparent",
                  border: activeRegion === "FinalFour" ? "1px solid rgba(245,158,11,0.4)" : "1px solid transparent",
                  cursor: "pointer",
                }}
              >
                <Trophy size={12} />
                Final Four
              </button>
            )}
          </div>

          {/* View mode toggle */}
          <div
            className="flex gap-1 p-1 rounded-xl ml-auto"
            style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.07)" }}
          >
            {([
              { id: "rotobot" as ViewMode, label: "RotoBot", icon: Brain },
              { id: "user" as ViewMode, label: "My Bracket", icon: CheckCircle },
            ]).map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setViewMode(id)}
                className="flex items-center gap-1.5 px-3 py-2 rounded-lg transition-all"
                style={{
                  fontFamily: "Rubik, sans-serif", fontSize: 12,
                  fontWeight: viewMode === id ? 600 : 400,
                  color: viewMode === id ? "white" : "rgba(255,255,255,0.4)",
                  background: viewMode === id ? "rgba(255,255,255,0.1)" : "transparent",
                  border: "none", cursor: "pointer",
                }}
              >
                <Icon size={12} />
                <span className="hidden sm:block">{label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Region header */}
        {activeRegion !== "FinalFour" && (
          <div
            className="flex items-center gap-3 mb-5 px-4 py-3 rounded-xl"
            style={{
              background: `${REGION_COLORS[activeRegion]}08`,
              border: `1px solid ${REGION_COLORS[activeRegion]}20`,
            }}
          >
            <div className="w-2 h-2 rounded-full" style={{ background: REGION_COLORS[activeRegion] }} />
            <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 15, fontWeight: 700, color: "white" }}>
              {activeRegion} Region
            </span>
            <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 12, color: "rgba(255,255,255,0.35)" }}>
              {viewMode === "user"
                ? "Click a team name to pick them"
                : "RotoBot's projected bracket"}
            </span>
            <div className="ml-auto flex items-center gap-2">
              <Brain size={12} color="#00b8db" />
              <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 11, color: "#00b8db" }}>
                Click any game for AI analysis
              </span>
            </div>
          </div>
        )}

        {/* Bracket content */}
        <div
          className="rounded-2xl p-4 overflow-hidden"
          style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)" }}
        >
          {activeRegion === "FinalFour" ? (
            <FinalFourView />
          ) : (
            <RegionBracket
              region={activeRegion}
              userPicks={userPicks}
              onPick={handlePick}
              viewMode={viewMode}
            />
          )}
        </div>

        {/* Legend + actions */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 mt-4">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Brain size={11} color="#00b8db" />
              <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 11, color: "rgba(255,255,255,0.4)" }}>
                RotoBot's pick
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full" style={{ background: "#22c55e" }} />
              <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 11, color: "rgba(255,255,255,0.4)" }}>
                Your pick
              </span>
            </div>
          </div>
          <div className="ml-auto flex gap-2">
            {pickedCount > 0 && (
              <button
                onClick={clearPicks}
                className="flex items-center gap-2 px-4 py-2 rounded-xl transition-all hover:opacity-80"
                style={{
                  background: "rgba(239,68,68,0.1)",
                  border: "1px solid rgba(239,68,68,0.2)",
                  fontFamily: "Rubik, sans-serif", fontSize: 12, fontWeight: 500,
                  color: "#ef4444", cursor: "pointer",
                }}
              >
                Clear Picks
              </button>
            )}
            <button
              onClick={handleShare}
              className="flex items-center gap-2 px-4 py-2 rounded-xl transition-all hover:opacity-80"
              style={{
                background: "rgba(255,255,255,0.05)",
                border: "1px solid rgba(255,255,255,0.1)",
                fontFamily: "Rubik, sans-serif", fontSize: 12, fontWeight: 500,
                color: "rgba(255,255,255,0.7)", cursor: "pointer",
              }}
            >
              <Share2 size={13} />
              {copied ? "Copied!" : "Share Bracket"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Final Four View ─────────────────────────────────────────────────────────

function FinalFourView() {
  const { getFinalFourTeams, state, makePick } = useBracket();
  const teams = getFinalFourTeams();
  const [east, west, south, midwest] = teams;

  if (!east || !west || !south || !midwest) {
    return (
      <div className="flex items-center justify-center py-20">
        <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 14, color: "rgba(255,255,255,0.3)" }}>
          Pick all four regional champions to unlock the Final Four
        </span>
      </div>
    );
  }

  const semis: Game[] = [
    {
      id: "ff-semi-1",
      round: 5,
      region: "Final Four",
      team1: east,
      team2: west,
      rotobotPick: east.rotobotScore >= west.rotobotScore ? east.name : west.name,
      rotobotConfidence: Math.min(85, Math.max(52, 50 + Math.abs(east.rotobotScore - west.rotobotScore) * 2)),
      analysis: "",
      proTeam1: [],
      proTeam2: [],
      pickReasoning: "",
      isLive: true,
    },
    {
      id: "ff-semi-2",
      round: 5,
      region: "Final Four",
      team1: south,
      team2: midwest,
      rotobotPick: south.rotobotScore >= midwest.rotobotScore ? south.name : midwest.name,
      rotobotConfidence: Math.min(85, Math.max(52, 50 + Math.abs(south.rotobotScore - midwest.rotobotScore) * 2)),
      analysis: "",
      proTeam1: [],
      proTeam2: [],
      pickReasoning: "",
      isLive: true,
    },
  ];

  return (
    <div className="flex flex-col items-center gap-8 py-8">
      <div className="flex items-center gap-2">
        <Trophy size={18} color="#f59e0b" />
        <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 18, fontWeight: 800, color: "white" }}>
          Final Four
        </span>
      </div>
      <div className="flex gap-8 flex-wrap justify-center">
        {semis.map((game) => (
          <div key={game.id} className="flex flex-col items-center gap-2">
            <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 11, color: "rgba(255,255,255,0.3)", textTransform: "uppercase" }}>
              {game.id === "ff-semi-1" ? "East vs West" : "South vs Midwest"}
            </span>
            <BracketGameCard
              game={game}
              userPick={state.userPicks[game.id]}
              onPick={(gid, tid) => makePick(gid, tid)}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
