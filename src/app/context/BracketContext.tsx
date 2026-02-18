import {
  createContext,
  useContext,
  useReducer,
  useEffect,
  useCallback,
  useRef,
  type ReactNode,
} from "react";
import type {
  Team,
  Game,
  PlayerRecord,
  ViewMode,
  MatchupNarrative,
  BracketMatchupRaw,
} from "../types/bracket";
import { fetchTeams, fetchBracket, fetchAllPlayers, generateMatchup, fetchEspnLogos } from "../lib/api";
import { rawMatchupToGame, buildRegionRounds, getRegionWinner, encodePicks, decodePicks } from "../lib/bracketUtils";

// ── State ───────────────────────────────────────────────────────────────────

interface BracketState {
  teams: Record<string, Team>;
  r1Games: Record<string, Game[]>;
  players: Record<string, PlayerRecord[]>;
  logos: Record<string, string>;
  userPicks: Record<string, string>;
  narratives: Record<string, MatchupNarrative>;
  loadingNarratives: Record<string, boolean>;
  viewMode: ViewMode;
  dataLoaded: boolean;
  dataError: string | null;
  toastMessage: string | null;
}

const initialState: BracketState = {
  teams: {},
  r1Games: {},
  players: {},
  logos: {},
  userPicks: {},
  narratives: {},
  loadingNarratives: {},
  viewMode: "rotobot",
  dataLoaded: false,
  dataError: null,
  toastMessage: null,
};

// ── Actions ─────────────────────────────────────────────────────────────────

type Action =
  | { type: "LOAD_DATA"; teams: Record<string, Team>; r1Games: Record<string, Game[]>; players: Record<string, PlayerRecord[]> }
  | { type: "LOAD_LOGOS"; logos: Record<string, string> }
  | { type: "LOAD_ERROR"; error: string }
  | { type: "SET_PICK"; gameId: string; teamId: string }
  | { type: "CLEAR_PICKS" }
  | { type: "SET_VIEW_MODE"; mode: ViewMode }
  | { type: "SET_NARRATIVE"; key: string; narrative: MatchupNarrative }
  | { type: "SET_NARRATIVE_LOADING"; key: string; loading: boolean }
  | { type: "SET_TOAST"; message: string | null }
  | { type: "HYDRATE_PICKS"; picks: Record<string, string> };

function reducer(state: BracketState, action: Action): BracketState {
  switch (action.type) {
    case "LOAD_DATA":
      return {
        ...state,
        teams: action.teams,
        r1Games: action.r1Games,
        players: action.players,
        dataLoaded: true,
        dataError: null,
      };
    case "LOAD_LOGOS":
      return { ...state, logos: action.logos };
    case "LOAD_ERROR":
      return { ...state, dataError: action.error };
    case "SET_PICK":
      return {
        ...state,
        userPicks: { ...state.userPicks, [action.gameId]: action.teamId },
      };
    case "CLEAR_PICKS":
      return { ...state, userPicks: {} };
    case "SET_VIEW_MODE":
      return { ...state, viewMode: action.mode };
    case "SET_NARRATIVE":
      return {
        ...state,
        narratives: { ...state.narratives, [action.key]: action.narrative },
      };
    case "SET_NARRATIVE_LOADING":
      return {
        ...state,
        loadingNarratives: { ...state.loadingNarratives, [action.key]: action.loading },
      };
    case "SET_TOAST":
      return { ...state, toastMessage: action.message };
    case "HYDRATE_PICKS":
      return { ...state, userPicks: action.picks };
    default:
      return state;
  }
}

// ── Context ─────────────────────────────────────────────────────────────────

interface BracketContextValue {
  state: BracketState;
  makePick: (gameId: string, teamId: string) => void;
  clearPicks: () => void;
  setViewMode: (mode: ViewMode) => void;
  dismissToast: () => void;
  getRegionGames: (region: string) => {
    r1: Game[];
    r2: Game[];
    s16: Game[];
    e8: Game[];
  };
  getRegionWinnerTeam: (region: string) => Team | null;
  getFinalFourTeams: () => (Team | null)[];
  requestNarrative: (team1Slug: string, team2Slug: string, round: number, region: string) => void;
  getNarrative: (team1Slug: string, team2Slug: string) => MatchupNarrative | undefined;
  isNarrativeLoading: (team1Slug: string, team2Slug: string) => boolean;
  getShareURL: () => string;
  findGameById: (gameId: string) => Game | undefined;
}

const BracketContext = createContext<BracketContextValue | null>(null);

// ── Provider ────────────────────────────────────────────────────────────────

export function BracketProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);

  // Load data on mount
  useEffect(() => {
    async function load() {
      try {
        const [teamsData, bracketData, playersData] = await Promise.all([
          fetchTeams(),
          fetchBracket(),
          fetchAllPlayers(),
        ]);

        // Group R1 matchups by region
        const r1ByRegion: Record<string, Game[]> = {};
        for (const raw of bracketData.matchups as BracketMatchupRaw[]) {
          if (raw.round !== 1) continue;
          const game = rawMatchupToGame(raw);
          if (!r1ByRegion[raw.region]) r1ByRegion[raw.region] = [];
          r1ByRegion[raw.region].push(game);
        }

        dispatch({ type: "LOAD_DATA", teams: teamsData, r1Games: r1ByRegion, players: playersData });

        fetchEspnLogos()
          .then((logos) => dispatch({ type: "LOAD_LOGOS", logos }))
          .catch(() => {});
      } catch (err) {
        dispatch({ type: "LOAD_ERROR", error: String(err) });
      }
    }
    load();
  }, []);

  // Hydrate picks from URL hash on mount
  useEffect(() => {
    const hash = window.location.hash.slice(1);
    if (hash) {
      const picks = decodePicks(hash);
      if (Object.keys(picks).length > 0) {
        dispatch({ type: "HYDRATE_PICKS", picks });
        dispatch({ type: "SET_VIEW_MODE", mode: "user" });
      }
    }
  }, []);

  const makePick = useCallback((gameId: string, teamId: string) => {
    dispatch({ type: "SET_PICK", gameId, teamId });
  }, []);

  const clearPicks = useCallback(() => {
    dispatch({ type: "CLEAR_PICKS" });
    window.location.hash = "";
  }, []);

  const setViewMode = useCallback((mode: ViewMode) => {
    dispatch({ type: "SET_VIEW_MODE", mode });
  }, []);

  const dismissToast = useCallback(() => {
    dispatch({ type: "SET_TOAST", message: null });
  }, []);

  const getRegionGames = useCallback(
    (region: string) => {
      const r1 = state.r1Games[region] ?? [];
      const { r2, s16, e8 } = buildRegionRounds(r1, region, state.userPicks, state.viewMode);

      const injectNarrative = (game: Game): Game => {
        if (game.analysis) return game;
        const key = narrativeKey(game.team1.id, game.team2.id);
        const n = state.narratives[key];
        if (!n) return game;
        return {
          ...game,
          analysis: n.analysis,
          proTeam1: n.proTeam1,
          proTeam2: n.proTeam2,
          rotobotPick: n.rotobotPick || game.rotobotPick,
          rotobotConfidence: n.rotobotConfidence || game.rotobotConfidence,
          pickReasoning: n.pickReasoning,
        };
      };

      return {
        r1,
        r2: r2.map(injectNarrative),
        s16: s16.map(injectNarrative),
        e8: e8.map(injectNarrative),
      };
    },
    [state.r1Games, state.userPicks, state.viewMode, state.narratives]
  );

  const getRegionWinnerTeam = useCallback(
    (region: string) => {
      const { e8 } = getRegionGames(region);
      return getRegionWinner(e8, state.userPicks, state.viewMode);
    },
    [getRegionGames, state.userPicks, state.viewMode]
  );

  const getFinalFourTeams = useCallback(() => {
    return ["East", "West", "South", "Midwest"].map((r) => getRegionWinnerTeam(r));
  }, [getRegionWinnerTeam]);

  const narrativeKey = (s1: string, s2: string) => `${s1}_vs_${s2}`;

  const pendingRef = useRef<Set<string>>(new Set());

  const requestNarrative = useCallback(
    async (team1Slug: string, team2Slug: string, round: number, region: string) => {
      const key = narrativeKey(team1Slug, team2Slug);
      if (pendingRef.current.has(key)) return;
      pendingRef.current.add(key);

      dispatch({ type: "SET_NARRATIVE_LOADING", key, loading: true });

      const team1Name = state.teams[team1Slug]?.shortName ?? team1Slug;
      const team2Name = state.teams[team2Slug]?.shortName ?? team2Slug;
      dispatch({
        type: "SET_TOAST",
        message: `RotoBot is analyzing ${team1Name} vs ${team2Name}...`,
      });

      try {
        const narrative = await generateMatchup(team1Slug, team2Slug, round, region);
        dispatch({ type: "SET_NARRATIVE", key, narrative });
      } catch (err) {
        console.error("Narrative generation failed:", err);
      } finally {
        dispatch({ type: "SET_NARRATIVE_LOADING", key, loading: false });
        setTimeout(() => dispatch({ type: "SET_TOAST", message: null }), 500);
      }
    },
    [state.teams]
  );

  const getNarrative = useCallback(
    (team1Slug: string, team2Slug: string) => state.narratives[narrativeKey(team1Slug, team2Slug)],
    [state.narratives]
  );

  const isNarrativeLoading = useCallback(
    (team1Slug: string, team2Slug: string) => !!state.loadingNarratives[narrativeKey(team1Slug, team2Slug)],
    [state.loadingNarratives]
  );

  const getShareURL = useCallback(() => {
    const hash = encodePicks(state.userPicks);
    return `${window.location.origin}/bracket#${hash}`;
  }, [state.userPicks]);

  const findGameById = useCallback(
    (gameId: string): Game | undefined => {
      for (const region of Object.keys(state.r1Games)) {
        const { r1, r2, s16, e8 } = getRegionGames(region);
        const all = [...r1, ...r2, ...s16, ...e8];
        const found = all.find((g) => g.id === gameId);
        if (found) return found;
      }
      return undefined;
    },
    [state.r1Games, getRegionGames]
  );

  const value: BracketContextValue = {
    state,
    makePick,
    clearPicks,
    setViewMode,
    dismissToast,
    getRegionGames,
    getRegionWinnerTeam,
    getFinalFourTeams,
    requestNarrative,
    getNarrative,
    isNarrativeLoading,
    getShareURL,
    findGameById,
  };

  return <BracketContext.Provider value={value}>{children}</BracketContext.Provider>;
}

// ── Hook ────────────────────────────────────────────────────────────────────

export function useBracket() {
  const ctx = useContext(BracketContext);
  if (!ctx) throw new Error("useBracket must be used within BracketProvider");
  return ctx;
}
