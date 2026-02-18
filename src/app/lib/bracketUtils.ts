import type { Team, Game, BracketMatchupRaw, ViewMode } from "../types/bracket";

/**
 * Convert a raw matchup from the API (with team1Full/team2Full) into a Game.
 * Patches seeds from matchup-level (bracketology) into team objects.
 */
export function rawMatchupToGame(raw: BracketMatchupRaw): Game {
  const team1 = { ...raw.team1Full, seed: raw.team1Seed || raw.team1Full.seed };
  const team2 = { ...raw.team2Full, seed: raw.team2Seed || raw.team2Full.seed };
  return {
    id: raw.id,
    round: raw.round,
    region: raw.region,
    team1,
    team2,
    rotobotPick: raw.rotobotPick,
    rotobotConfidence: raw.rotobotConfidence,
    analysis: raw.analysis ?? "",
    proTeam1: raw.proTeam1 ?? [],
    proTeam2: raw.proTeam2 ?? [],
    pickReasoning: raw.pickReasoning ?? "",
  };
}

/**
 * Get the winner of a game based on picks and view mode.
 * Returns null if the game hasn't been decided yet.
 */
export function getGameWinner(
  game: Game,
  userPicks: Record<string, string>,
  viewMode: ViewMode
): Team | null {
  if (viewMode === "user") {
    const pickId = userPicks[game.id];
    if (!pickId) return null;
    if (game.team1.id === pickId) return game.team1;
    if (game.team2.id === pickId) return game.team2;
    return null;
  }
  // rotobot mode: always has a pick
  const pickName = game.rotobotPick;
  if (game.team1.name === pickName || game.team1.id === pickName) return game.team1;
  if (game.team2.name === pickName || game.team2.id === pickName) return game.team2;
  return game.team1.rotobotScore >= game.team2.rotobotScore ? game.team1 : game.team2;
}

/**
 * Build a game stub for a later round from two teams.
 * Analysis/pros will be filled by Gemini later.
 */
export function makeGameStub(
  team1: Team,
  team2: Team,
  round: number,
  region: string,
  idx: number
): Game {
  const roundPrefix = ["r1", "r2", "s16", "e8", "ff", "ch"][round - 1] ?? `r${round}`;
  return {
    id: `${region.toLowerCase()}-${roundPrefix}-${idx + 1}`,
    round,
    region,
    team1,
    team2,
    rotobotPick: team1.rotobotScore >= team2.rotobotScore ? team1.name : team2.name,
    rotobotConfidence: Math.min(
      92,
      Math.max(52, 50 + Math.abs(team1.rotobotScore - team2.rotobotScore) * 2.2)
    ),
    analysis: "",
    proTeam1: [],
    proTeam2: [],
    pickReasoning: "",
    isLive: true,
  };
}

/**
 * Build later rounds from R1 games based on picks.
 * Returns arrays of games for R2, S16, E8.
 */
export function buildRegionRounds(
  r1Games: Game[],
  region: string,
  userPicks: Record<string, string>,
  viewMode: ViewMode
): { r2: Game[]; s16: Game[]; e8: Game[] } {
  const r2Games: Game[] = [];
  for (let i = 0; i < r1Games.length; i += 2) {
    const w1 = getGameWinner(r1Games[i], userPicks, viewMode);
    const w2 = getGameWinner(r1Games[i + 1], userPicks, viewMode);
    if (w1 && w2) {
      r2Games.push(makeGameStub(w1, w2, 2, region, i / 2));
    }
  }

  const s16Games: Game[] = [];
  for (let i = 0; i < r2Games.length; i += 2) {
    const w1 = getGameWinner(r2Games[i], userPicks, viewMode);
    const w2 = i + 1 < r2Games.length ? getGameWinner(r2Games[i + 1], userPicks, viewMode) : null;
    if (w1 && w2) {
      s16Games.push(makeGameStub(w1, w2, 3, region, i / 2));
    }
  }

  const e8Games: Game[] = [];
  if (s16Games.length >= 2) {
    const w1 = getGameWinner(s16Games[0], userPicks, viewMode);
    const w2 = getGameWinner(s16Games[1], userPicks, viewMode);
    if (w1 && w2) {
      e8Games.push(makeGameStub(w1, w2, 4, region, 0));
    }
  }

  return { r2: r2Games, s16: s16Games, e8: e8Games };
}

/**
 * Get region winner (E8 winner) if decided.
 */
export function getRegionWinner(
  e8Games: Game[],
  userPicks: Record<string, string>,
  viewMode: ViewMode
): Team | null {
  if (e8Games.length === 0) return null;
  return getGameWinner(e8Games[0], userPicks, viewMode);
}

/**
 * Encode picks as base64 for URL sharing.
 */
export function encodePicks(picks: Record<string, string>): string {
  return btoa(JSON.stringify(picks));
}

/**
 * Decode picks from base64 URL hash.
 */
export function decodePicks(hash: string): Record<string, string> {
  try {
    return JSON.parse(atob(hash));
  } catch {
    return {};
  }
}
