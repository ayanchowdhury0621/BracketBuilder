import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { Brain, Loader2, ChevronDown, ChevronUp, Zap } from "lucide-react";
import type { Game, ViewMode } from "../types/bracket";
import { TeamLogo } from "./TeamLogo";

interface BracketGameProps {
  game: Game;
  userPick?: string;
  onPick?: (gameId: string, teamId: string) => void;
  compact?: boolean;
  isLoading?: boolean;
  viewMode?: ViewMode;
}

function isRotobotPick(game: Game, teamId: string, teamName: string): boolean {
  const pick = game.rotobotPick;
  return pick === teamId || pick === teamName;
}

export function BracketGameCard({ game, userPick, onPick, compact = false, isLoading = false, viewMode = "user" }: BracketGameProps) {
  const [expanded, setExpanded] = useState(false);
  const navigate = useNavigate();
  const hasAnalysis = !!(game.analysis || game.pickReasoning);
  const isRotoMode = viewMode === "rotobot";

  const handleTeamClick = (e: React.MouseEvent, teamId: string) => {
    e.preventDefault();
    e.stopPropagation();
    if (isRotoMode) {
      navigate(`/matchup/${game.id}`);
    } else {
      onPick?.(game.id, teamId);
    }
  };

  return (
    <div className="flex flex-col" style={{ minWidth: compact ? 160 : 200 }}>
      <Link
        to={`/matchup/${game.id}`}
        className="no-underline block"
        onClick={(e) => {
          if (!isRotoMode) e.preventDefault();
        }}
      >
        <div
          className="rounded-xl overflow-hidden transition-all hover:border-[rgba(0,184,219,0.3)] group"
          style={{
            background: game.isLive ? "rgba(0,184,219,0.03)" : "rgba(255,255,255,0.03)",
            border: game.isLive
              ? "1px solid rgba(0,184,219,0.15)"
              : "1px solid rgba(255,255,255,0.08)",
          }}
        >
          {[game.team1, game.team2].map((team, idx) => {
            const isRotoPick = isRotobotPick(game, team.id, team.name);
            const isUserPick = team.id === userPick || team.name === userPick;
            const isTop = idx === 0;

            return (
              <div
                key={team.id}
                onClick={(e) => handleTeamClick(e, team.id)}
                className="flex items-center gap-2 px-2.5 py-2 cursor-pointer transition-all hover:bg-white/5"
                style={{
                  borderBottom: isTop ? "1px solid rgba(255,255,255,0.06)" : "none",
                  background: isUserPick ? "rgba(0,184,219,0.08)" : "transparent",
                }}
              >
                <div
                  className="flex items-center justify-center rounded shrink-0"
                  style={{
                    width: 20, height: 20,
                    background: isRotoPick ? "rgba(0,184,219,0.18)" : "rgba(255,255,255,0.06)",
                    fontFamily: "Rubik, sans-serif", fontSize: 10, fontWeight: 700,
                    color: isRotoPick ? "#00b8db" : "rgba(255,255,255,0.4)",
                  }}
                >
                  {team.seed}
                </div>

                <TeamLogo teamSlug={team.id} teamShortName={team.shortName} teamColor={team.color} size={18} />

                <span
                  className="flex-1 truncate"
                  style={{
                    fontFamily: "Rubik, sans-serif", fontSize: compact ? 11 : 12,
                    fontWeight: isRotoPick || isUserPick ? 600 : 400,
                    color: isRotoPick || isUserPick ? "white" : "rgba(255,255,255,0.55)",
                  }}
                >
                  {compact ? team.shortName.slice(0, 12) : team.shortName}
                </span>

                <div className="flex items-center gap-1">
                  {isUserPick && (
                    <div className="w-1.5 h-1.5 rounded-full" style={{ background: "#22c55e" }} />
                  )}
                  {isRotoPick && !compact && (
                    <Brain size={9} color="#00b8db" />
                  )}
                </div>
              </div>
            );
          })}

          {!compact && (
            <div className="px-2.5 py-1.5 flex items-center gap-1" style={{ borderTop: "1px solid rgba(255,255,255,0.05)" }}>
              {isLoading ? (
                <div className="flex items-center gap-1.5 w-full">
                  <Loader2 size={9} className="animate-spin" color="#00b8db" />
                  <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 9, color: "rgba(0,184,219,0.6)" }}>Analyzing...</span>
                </div>
              ) : (
                <>
                  <div className="flex-1 h-0.5 rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,0.07)" }}>
                    <div className="h-full rounded-full" style={{
                      width: `${game.rotobotConfidence}%`,
                      background: game.rotobotConfidence >= 80 ? "#00b8db" : game.rotobotConfidence >= 60 ? "#3c84ff" : "#f59e0b",
                    }} />
                  </div>
                  <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 9, color: "rgba(255,255,255,0.3)", minWidth: 24, textAlign: "right" }}>
                    {game.rotobotConfidence}%
                  </span>
                  {hasAnalysis && (
                    <button
                      onClick={(e) => { e.preventDefault(); e.stopPropagation(); setExpanded(!expanded); }}
                      className="ml-0.5 p-0.5 rounded transition-all hover:bg-white/10"
                      style={{ background: "none", border: "none", cursor: "pointer", lineHeight: 0 }}
                    >
                      {expanded ? <ChevronUp size={10} color="rgba(255,255,255,0.4)" /> : <ChevronDown size={10} color="rgba(255,255,255,0.4)" />}
                    </button>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      </Link>

      {expanded && hasAnalysis && !compact && (
        <div className="mt-1 rounded-lg px-2.5 py-2" style={{
          background: "rgba(0,184,219,0.04)", border: "1px solid rgba(0,184,219,0.12)", maxWidth: 200,
        }}>
          {game.rotobotPick && (
            <div className="flex items-center gap-1 mb-1.5">
              <Zap size={8} color="#00b8db" />
              <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 9, fontWeight: 600, color: "#00b8db" }}>
                Pick: {game.rotobotPick}
              </span>
            </div>
          )}
          <p style={{
            fontFamily: "Rubik, sans-serif", fontSize: 9, color: "rgba(255,255,255,0.5)",
            lineHeight: 1.4, margin: 0,
            display: "-webkit-box", WebkitLineClamp: 3, WebkitBoxOrient: "vertical", overflow: "hidden",
          }}>
            {game.pickReasoning || game.analysis}
          </p>
          {(game.team1.styleTags?.length > 0 || game.team2.styleTags?.length > 0) && (
            <div className="flex flex-wrap gap-1 mt-1.5">
              {[game.team1, game.team2].map((team) =>
                (team.styleTags || []).slice(0, 1).filter(t => t && t !== "nan").map((tag) => (
                  <span key={`${team.id}-${tag}`} style={{
                    fontFamily: "Rubik, sans-serif", fontSize: 8, color: "rgba(255,255,255,0.4)",
                    background: "rgba(255,255,255,0.05)", padding: "1px 4px", borderRadius: 4,
                  }}>
                    {team.shortName}: {tag}
                  </span>
                ))
              )}
            </div>
          )}
          <Link to={`/matchup/${game.id}`} className="no-underline block mt-1.5"
            style={{ fontFamily: "Rubik, sans-serif", fontSize: 9, color: "#00b8db", fontWeight: 500 }}>
            Full analysis →
          </Link>
        </div>
      )}
    </div>
  );
}

export function BracketConnector({ count, height }: { count: number; height: number }) {
  const segmentH = height / count;
  const lines: React.ReactNode[] = [];

  for (let i = 0; i < count / 2; i++) {
    const topY = segmentH * (2 * i) + segmentH / 2;
    const bottomY = segmentH * (2 * i + 1) + segmentH / 2;
    const midY = (topY + bottomY) / 2;

    lines.push(
      <g key={i}>
        <line x1="0" y1={topY} x2="16" y2={topY} stroke="rgba(255,255,255,0.12)" strokeWidth="1" />
        <line x1="0" y1={bottomY} x2="16" y2={bottomY} stroke="rgba(255,255,255,0.12)" strokeWidth="1" />
        <line x1="16" y1={topY} x2="16" y2={bottomY} stroke="rgba(255,255,255,0.12)" strokeWidth="1" />
        <line x1="16" y1={midY} x2="32" y2={midY} stroke="rgba(255,255,255,0.12)" strokeWidth="1" />
      </g>
    );
  }

  return (
    <svg width="32" height={height} style={{ display: "block", flexShrink: 0 }}>
      {lines}
    </svg>
  );
}
