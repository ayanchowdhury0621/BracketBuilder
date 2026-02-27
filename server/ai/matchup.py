"""Gemini matchup narrative generation logic."""

from __future__ import annotations

import hashlib
from typing import Any

from .cache import _read_cache, _write_cache
from .clients.gemini_client import GeminiClient
from .markdown import build_matchup_markdown

SYSTEM_PROMPT_MATCHUP = """You are RotoBot, a veteran NCAAB analyst writing matchup previews for a March Madness bracket app.

**Rules:**
- `analysis`: 3-5 sentences. Name both key players. Identify the style clash and the decisive edge. Every sentence must have at least one number.
- `proTeam1` and `proTeam2`: 3-5 bullets each. Every bullet MUST contain at least one stat. Frame as reasons that team wins.
- `rotobotPick`: The team name you pick to win.
- `rotobotConfidence`: 55-99. Use the stat edges to calibrate - a 1-vs-16 with massive edges = 95+, a toss-up 8-vs-9 = 55-62.
- `pickReasoning`: 1-2 sentences explaining the pick with specific numbers.
- Do NOT hedge with "could go either way" - commit to a pick and justify it.
- Even for heavy favorites, give the underdog real, stat-backed bullets.

**Output format:** Return ONLY a JSON object with keys: analysis, proTeam1, proTeam2, rotobotPick, rotobotConfidence, pickReasoning

---

### Example: 1 vs 16

**Input:**

## East Region, Round of 64: (1) Michigan vs (16) Portland St.

### Michigan (Big Ten) - 24-1, NET #1, RotoBot Score: 97.4

**Identity:** Plays at 73.1 poss/40 (top 25% nationally) and scores 90.6 PPG. Heavy three-point attack (26.1 3PA/G at 35.4%). Defense is the identity: 68.3 opp PPG, 37.1% opponent FG. One of the Big Ten's most efficient offenses.

**Key Stats:** 90.6 PPG | 68.3 OPPG | 73.1 pace | 58.9% eFG | 37.1% opp FG | 26.1 3PA/G | 32.5 bench PPG

**Weakness:** No glaring weakness; balanced profile.

**Key Player:** Jeremy Fears Jr. - 16.5 PPG / 1.8 RPG / 12.0 APG / 1.5 SPG

### Portland St. (Big Sky) - 14-7, NET #130, RotoBot Score: 28.0

**Identity:** Averages 77.8 PPG at 69.3 poss/40. Stout defensively (69.8 opp PPG). Top-3 in Big Sky defensive efficiency.

**Key Stats:** 77.8 PPG | 69.8 OPPG | 69.3 pace | 53.1% eFG | 40.7% opp FG | 15.3 bench PPG

**Weakness:** Thin bench - starters carry the load.

**Key Player:** Terri Miller Jr. - 22.3 PPG / 5.3 RPG / 2.3 APG

### Head-to-Head Edges:
- PPG: Michigan 90.6 vs Portland St. 77.8 -> Michigan
- OPPG: Michigan 68.3 vs Portland St. 69.8 -> Michigan
- eFG%: Michigan 58.9% vs Portland St. 53.1% -> Michigan
- Opp FG%: Michigan 37.1% vs Portland St. 40.7% -> Michigan
- Pace: Michigan 73.1 vs Portland St. 69.3 -> Michigan (faster)
- Bench PPG: Michigan 32.5 vs Portland St. 15.3 -> Michigan
- NET: Michigan #1 vs Portland St. #130 -> Michigan

**Output:**

{"analysis": "Michigan's 90.6 PPG and 58.9% eFG will overwhelm a Portland St. defense allowing 40.7% FG. Jeremy Fears Jr. (12.0 APG) will dissect the Big Sky defense, and Michigan's 32.5 bench PPG means the Wolverines can run 10 deep while Portland St.'s 15.3 bench PPG leaves Terri Miller Jr. (22.3 PPG) shouldering the load for 35+ minutes. The pace gap (73.1 vs 69.3) favors Michigan's transition game, and their 37.1% opponent FG should limit Portland St.'s half-court efficiency.", "proTeam1": ["90.6 PPG and 58.9% eFG - best offense Portland St. has faced all year", "37.1% opponent FG shuts down half-court attacks", "32.5 bench PPG means fresh legs all game vs Portland St.'s 15.3", "Jeremy Fears Jr.'s 12.0 APG will find open shooters against a 40.7% opp FG defense", "26.1 3PA/G at 35.4% stretches the floor beyond Big Sky defensive schemes"], "proTeam2": ["Terri Miller Jr. (22.3 PPG / 5.3 RPG) is a legit scorer who can get his own shot", "69.8 opp PPG shows Portland St. can defend - top-3 in the Big Sky", "53.1% eFG is respectable and could keep it competitive in spurts", "Slower pace (69.3) could limit Michigan's transition opportunities if Portland St. controls tempo"], "rotobotPick": "Michigan", "rotobotConfidence": 97, "pickReasoning": "Michigan is better in every measurable category - 90.6 PPG vs 77.8, 37.1% vs 40.7% opp FG, 32.5 vs 15.3 bench PPG. The talent and depth gap is historic-level; Portland St. would need Michigan to shoot below 30% from three to have a chance."}

---

Now write a matchup analysis for the following game:"""


def _payload_hash(payload: str) -> str:
    return hashlib.md5(payload.encode()).hexdigest()[:12]


def _compute_edges(team1: dict[str, Any], team2: dict[str, Any]) -> list[dict[str, Any]]:
    categories = [
        ("PPG", "ppg", True),
        ("Opp PPG", "oppg", False),
        ("eFG%", "eFGPct", True),
        ("Opp FG%", None, False),
        ("Pace", "pace", None),
        ("OREB/G", "orebPct", True),
        ("Turnover %", "tovPct", False),
        ("SOS Rank", "sosRank", False),
        ("NET Rank", "netRank", False),
        ("RotoBot Score", "rotobotScore", True),
    ]

    edges: list[dict[str, Any]] = []
    for label, key, higher_is_better in categories:
        if key is None:
            v1 = team1.get("stats", {}).get("defense", {}).get("fgPctDefense", 0)
            v2 = team2.get("stats", {}).get("defense", {}).get("fgPctDefense", 0)
            higher_is_better = False
        else:
            v1 = team1.get(key, 0) or 0
            v2 = team2.get(key, 0) or 0

        if higher_is_better is None:
            edge = "neutral"
        elif higher_is_better:
            edge = "team1" if v1 > v2 else ("team2" if v2 > v1 else "even")
        else:
            edge = "team1" if v1 < v2 else ("team2" if v2 < v1 else "even")
        edges.append({"label": label, "team1Value": v1, "team2Value": v2, "edge": edge})
    return edges


def _fallback_pick(team1: dict[str, Any], team2: dict[str, Any]) -> dict[str, Any]:
    s1 = float(team1.get("rotobotScore", 50) or 50)
    s2 = float(team2.get("rotobotScore", 50) or 50)
    t1_name = str(team1.get("name", team1.get("id", "Team 1")))
    t2_name = str(team2.get("name", team2.get("id", "Team 2")))
    pick = t1_name if s1 >= s2 else t2_name
    conf = int(min(92, max(55, 55 + abs(s1 - s2) * 2.0)))
    return {
        "analysis": f"{t1_name} ({s1:.1f}) vs {t2_name} ({s2:.1f}) based on model and efficiency profile.",
        "proTeam1": [f"Model score {s1:.1f}", f"PPG {team1.get('ppg', 0)}", f"NET #{team1.get('netRank', 999)}"],
        "proTeam2": [f"Model score {s2:.1f}", f"PPG {team2.get('ppg', 0)}", f"NET #{team2.get('netRank', 999)}"],
        "rotobotPick": pick,
        "rotobotConfidence": conf,
        "pickReasoning": f"Picked {pick} from higher blended model score.",
    }


def generate_matchup_narrative(
    gemini: GeminiClient,
    game: dict[str, Any],
    team1: dict[str, Any],
    team2: dict[str, Any],
    news1: str,
    news2: str,
) -> dict[str, Any]:
    game_id = game.get("id", "unknown")
    edges = _compute_edges(team1, team2)
    user_md = build_matchup_markdown(game, team1, team2, news1, news2, edges)
    payload_h = _payload_hash(user_md)

    cached = _read_cache("matchups", game_id)
    if cached and cached.get("_hash") == payload_h and cached.get("analysis"):
        return {k: v for k, v in cached.items() if not k.startswith("_")}

    result = gemini.generate(SYSTEM_PROMPT_MATCHUP, user_md)
    if not result:
        return _fallback_pick(team1, team2)

    if result.get("analysis"):
        _write_cache("matchups", game_id, {"_hash": payload_h, **result})
    result.setdefault("proTeam1", [])
    result.setdefault("proTeam2", [])
    result.setdefault("rotobotPick", _fallback_pick(team1, team2)["rotobotPick"])
    result["rotobotConfidence"] = int(result.get("rotobotConfidence", 60) or 60)
    result.setdefault("pickReasoning", "")
    return result
