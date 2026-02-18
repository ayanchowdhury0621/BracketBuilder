// ── Stat Sub-types ──────────────────────────────────────────────────────────

export interface ScoringStats {
  ppg: number;
  oppg: number;
  scoringMargin: number;
  benchPPG: number;
  fastbreakPPG: number;
}

export interface ShootingStats {
  fgPct: number;
  fgPctDefense: number;
  threePtPct: number;
  threePtPctDefense: number;
  threePG: number;
  threePtAttemptsPG: number;
  ftPct: number;
  ftMadePG: number;
  eFGPct: number;
}

export interface ReboundingStats {
  rpg: number;
  rebMargin: number;
  orebPG: number;
  drebPG: number;
  orebPct: number;
}

export interface BallControlStats {
  apg: number;
  topg: number;
  astToRatio: number;
  tovPct: number;
  turnoverMargin: number;
  turnoversForcedPG: number;
}

export interface DefenseStats {
  spg: number;
  bpg: number;
  fpg: number;
  oppg: number;
  fgPctDefense: number;
  threePtPctDefense: number;
}

export interface TempoStats {
  pace: number;
  winPct: number;
}

export interface RankingStats {
  netRank: number;
  apRank: number | null;
  sosRank: number;
  powerScore: number;
}

export interface ScheduleStats {
  q1Record: string;
  q2Record: string;
  q3Record: string;
  q4Record: string;
}

export interface TeamStats {
  scoring: ScoringStats;
  shooting: ShootingStats;
  rebounding: ReboundingStats;
  ballControl: BallControlStats;
  defense: DefenseStats;
  tempo: TempoStats;
  rankings: RankingStats;
  schedule: ScheduleStats;
  percentiles: Record<string, number>;
}

// ── Team ────────────────────────────────────────────────────────────────────

export interface Team {
  id: string;
  name: string;
  shortName: string;
  seed: number;
  record: string;
  conference: string;
  ppg: number;
  oppg: number;
  pace: number;
  eFGPct: number;
  tovPct: number;
  orebPct: number;
  sosRank: number;
  netRank: number;
  recentForm: ("W" | "L")[];
  color: string;
  rotobotScore: number;
  rotobotBlurb: string;
  keyPlayer: string;
  keyPlayerStat: string;
  styleTags: string[];
  styleSummary: string;
  styleIdentity: string;
  styleBullets: string;
  styleWeakness: string;
  stats: TeamStats;
}

// ── Player ──────────────────────────────────────────────────────────────────

export interface PlayerStats {
  ppg: number;
  rpg: number;
  apg: number;
  spg: number;
  bpg: number;
  topg: number;
  mpg: number;
  fgPct: number | null;
  ftPct: number | null;
  threePtPct: number | null;
  eFGPct: number | null;
}

export interface PlayerPerGame {
  fgm: number;
  fga: number;
  ftm: number;
  fta: number;
  threePM: number;
  threePA: number;
  oreb: number;
}

export interface PlayerTotals {
  pts: number;
  reb: number;
  ast: number;
  stl: number;
  blk: number;
  fgm: number;
  fga: number;
}

export interface PlayerRecord {
  name: string;
  team: string;
  teamSlug: string;
  position: string;
  class: string;
  height: string;
  gamesPlayed: number;
  gamesStarted: number;
  stats: PlayerStats;
  perGame: PlayerPerGame;
  totals: PlayerTotals;
  statSummary: string;
}

// ── Game / Matchup ──────────────────────────────────────────────────────────

export interface Game {
  id: string;
  round: number;
  region: string;
  team1: Team;
  team2: Team;
  rotobotPick: string;
  rotobotConfidence: number;
  analysis: string;
  proTeam1: string[];
  proTeam2: string[];
  pickReasoning: string;
  userPick?: string;
  isLive?: boolean;
}

export interface MatchupNarrative {
  analysis: string;
  proTeam1: string[];
  proTeam2: string[];
  rotobotPick: string;
  rotobotConfidence: number;
  pickReasoning: string;
}

// ── Bracket API response ────────────────────────────────────────────────────

export interface BracketRegionTeam {
  team_name_normalized: string;
  team_name: string;
  team_slug: string;
  overall_rank: number;
  seed: number;
  committee_score: number;
  net_rank: number;
  conference: string;
  record: string;
  is_auto_bid: boolean;
}

export interface BracketMatchupRaw {
  id: string;
  round: number;
  region: string;
  team1Seed: number;
  team2Seed: number;
  team1: string;
  team1Slug: string;
  team1NetRank: number;
  team1Score: number;
  team1Record: string;
  team1Conference: string;
  team1AutoBid: boolean;
  team2: string;
  team2Slug: string;
  team2NetRank: number;
  team2Score: number;
  team2Record: string;
  team2Conference: string;
  team2AutoBid: boolean;
  analysis: string;
  proTeam1: string[];
  proTeam2: string[];
  rotobotPick: string;
  rotobotConfidence: number;
  pickReasoning: string;
  team1Full: Team;
  team2Full: Team;
}

export interface BracketResponse {
  mode: string;
  variance: number;
  seed: number;
  field: unknown[];
  regions: Record<string, { teams: BracketRegionTeam[] }>;
  matchups: BracketMatchupRaw[];
  seedList: unknown[];
  conferenceBids: unknown[];
}

// ── View Mode ───────────────────────────────────────────────────────────────

export type ViewMode = "rotobot" | "user";

export const REGIONS = ["East", "West", "South", "Midwest"] as const;
export type Region = (typeof REGIONS)[number];

export const ROUND_LABELS: Record<number, string> = {
  1: "Round of 64",
  2: "Round of 32",
  3: "Sweet 16",
  4: "Elite 8",
  5: "Final Four",
  6: "Championship",
};
