const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8002";
const DATA_BASE = import.meta.env.VITE_DATA_BASE || API_BASE;

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${detail}`);
  }
  return res.json();
}

function apiUrl(path: string) {
  return `${API_BASE}${path}`;
}

function dataUrl(filename: string) {
  if (DATA_BASE === API_BASE) {
    return `${API_BASE}/api/${filename.replace(".json", "")}`;
  }
  return `${DATA_BASE}/${filename}`;
}

// ── Static data (served from S3 in production, API in dev) ──────────────────

export function fetchTeams() {
  return fetchJSON<Record<string, import("../types/bracket").Team>>(dataUrl("teams.json"));
}

export function fetchBracket() {
  return fetchJSON<import("../types/bracket").BracketResponse>(dataUrl("bracket.json"));
}

export function fetchAllPlayers() {
  if (DATA_BASE !== API_BASE) {
    return fetchJSON<Record<string, import("../types/bracket").PlayerRecord[]>>(
      dataUrl("players_full.json")
    );
  }
  return fetchJSON<Record<string, import("../types/bracket").PlayerRecord[]>>(
    apiUrl("/api/players")
  );
}

export function fetchTeamPlayers(slug: string) {
  return fetchJSON<import("../types/bracket").PlayerRecord[]>(apiUrl(`/api/players/${slug}`));
}

export function fetchEspnLogos() {
  if (DATA_BASE !== API_BASE) {
    return fetchJSON<Record<string, string>>(dataUrl("espn_manifest.json")).then(
      (m: any) => m.logos || m
    );
  }
  return fetchJSON<Record<string, string>>(apiUrl("/api/espn/logos"));
}

export function fetchEspnRoster(teamSlug: string) {
  if (DATA_BASE !== API_BASE) {
    return fetchJSON<Record<string, Record<string, string>>>(dataUrl("espn_manifest.json")).then(
      (m: any) => {
        const hs = m.headshots?.[teamSlug] || {};
        return Object.entries(hs).map(([name, url]) => ({
          espnId: "",
          name,
          headshot: url as string,
          position: "",
          jersey: "",
        }));
      }
    );
  }
  return fetchJSON<{ espnId: string; name: string; headshot: string; position: string; jersey: string }[]>(
    apiUrl(`/api/espn/roster/${teamSlug}`)
  );
}

// ── Dynamic AI endpoints (always go through the backend) ────────────────────

export function generateMatchup(team1Slug: string, team2Slug: string, round: number, region: string) {
  return fetchJSON<import("../types/bracket").MatchupNarrative>(apiUrl("/api/matchup"), {
    method: "POST",
    body: JSON.stringify({ team1Slug, team2Slug, round, region }),
  });
}

export function fetchAllNews() {
  return fetchJSON<Record<string, string>>(apiUrl("/api/news"));
}

export function fetchTeamNews(slug: string) {
  return fetchJSON<{ slug: string; news: string }>(apiUrl(`/api/news/${slug}`));
}

export function fetchNewsLive(teamSlug: string, force = false) {
  return fetchJSON<{ slug: string; news: string; cached: boolean }>(apiUrl("/api/news/fetch"), {
    method: "POST",
    body: JSON.stringify({ teamSlug, force }),
  });
}

export function fetchTrends(team1Slug: string, team2Slug: string) {
  return fetchJSON<{ key: string; trends: string; cached: boolean }>(apiUrl("/api/trends/fetch"), {
    method: "POST",
    body: JSON.stringify({ team1Slug, team2Slug }),
  });
}
