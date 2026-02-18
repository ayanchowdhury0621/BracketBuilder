# Gemini Prompting Layer — Plan

**Goal:** Use Gemini to generate **team blurbs** (rotobotBlurb), **matchup analysis** (analysis), and **pro/con bullets** (proTeam1, proTeam2) from the existing data packet so copy is specific, scout-like, and bracket-ready.

---

## 1. Scope: What We Generate

| Output | Where it lives | Length / format |
|--------|----------------|-----------------|
| **rotobotBlurb** | Per-team (Team.rotobotBlurb) | 1–3 sentences: identity + key player + one weakness or X-factor. |
| **analysis** | Per-game (Game.analysis) | 2–4 sentences: style clash, key edge, and why one team might win. |
| **proTeam1** / **proTeam2** | Per-game (Game.proTeam1, Game.proTeam2) | 3–5 short bullets each; data-backed (pace, defense, matchup, narrative). |
| **rotobotPick** + **rotobotConfidence** | Per-game | Optional in v1: can stay rule-based (power score / NET) and let Gemini only do narrative; or let Gemini suggest pick + confidence and compare to rule-based. |

**Out of scope for v1:** Full bracket story, daily updates, or real-time API. We generate once per pipeline run (after export + bracket).

---

## 2. Data Inputs: What We Send to Gemini

**Per team (for blurbs):**
- `name`, `shortName`, `conference`, `record`, `seed` (if in bracket), `netRank`, `sosRank`
- `styleIdentity`, `styleBullets`, `styleWeakness`, `styleTags`, `styleSummary`
- `rotobotScore`, `keyPlayer`, `keyPlayerStat`
- Condensed `stats`: pace, ppg, oppg, eFG%, tovPct, orebPct, fgPctDefense, turnoversForcedPG, astToRatio, benchPPG
- Optional: `percentiles` (top stats only, e.g. pace_pctl, oppg_pctl, efg_pct_pctl) so the model can say "top-10% defense" when we already encoded it in styleIdentity

**Per matchup (for analysis + pro/cons):**
- Same team payload for team1 and team2 (abbreviated: name, record, styleIdentity, styleWeakness, key stats, keyPlayer)
- Game context: round (1), region, seed1 vs seed2 (e.g. "1 vs 16")
- Optional: pre-computed "edges" (e.g. "Team A has better defense, Team B has better pace") so Gemini can turn them into prose instead of recalculating

**Design choice:** Prefer **structured JSON** in the prompt (or a small schema) so output can be parsed reliably (e.g. `{"rotobotBlurb": "...", "analysis": "...", "proTeam1": [...], "proTeam2": [...]}`).

---

## 3. Prompt Design

### 3.1 System prompt (shared)
- Role: NCAAB scout / bracket analyst; tone: specific, data-driven, no fluff.
- Rules: Use the provided stats and style copy; don’t invent numbers; mention key player and one weakness or X-factor per team when relevant; keep blurbs short (1–3 sentences).
- Output: Strict JSON only (no markdown fences if the API strips them), keys as specified.

### 3.2 Team blurb (one call per team, or batched)
- **Input:** Single JSON object for one team (name, conference, record, styleIdentity, styleBullets, styleWeakness, keyPlayer, keyPlayerStat, rotobotScore, and a few key stats).
- **Output:** `{ "rotobotBlurb": "1-3 sentence blurb" }`
- **Few-shot:** 2–3 examples: e.g. high seed (Duke), mid-major (Gonzaga), bubble (e.g. 9-seed). Each example: same JSON shape in, example blurb out.

### 3.3 Matchup analysis + pro/cons (one call per game)
- **Input:** JSON with team1, team2 (each with name, record, styleIdentity, styleWeakness, key stats, keyPlayer), plus round, region, seed1, seed2.
- **Output:** `{ "analysis": "2-4 sentences", "proTeam1": ["bullet", ...], "proTeam2": ["bullet", ...] }`
- **Few-shot:** 1–2 examples (e.g. 1v16, 5v12) so the model sees the desired bullet style (e.g. "Elite defense (64 opp PPG) will slow down [opponent]’s pace.").

### 3.4 Batching and cost
- **Blurbs:** 68 teams → 68 calls, or batch in groups of 5–10 teams per request with a single JSON array in and array of blurbs out (reduces round-trips).
- **Matchups:** 32 Round-of-64 games → 32 calls, or 2–4 games per request (batch by region) to balance context length vs number of calls.
- **Caching:** Cache by (team_id or game_id) + hash of input stats so re-runs with same data don’t re-call Gemini. Optional: write cache to `data/gemini_cache/` (e.g. `teams/<id>.json`, `games/<id>.json`).

---

## 4. Integration: Where It Sits in the Pipeline

**Recommended flow:**

1. **Export** (existing): `teams.json`, `players_top3.json`, etc. from CSVs.
2. **Bracketology** (existing): `bracket.json` with `matchups` (team slugs, seeds, records, no narrative).
3. **Gemini step (new):**
   - Load `teams.json` and `bracket.json` (or `bracket_shuffle_<n>.json`).
   - For each team in `teams.json` that appears in the bracket (or all 68), call Gemini for **rotobotBlurb**; merge back into team objects.
   - For each game in `bracket.matchups`, build the matchup payload from team data, call Gemini for **analysis** + **proTeam1** + **proTeam2**; attach to game.
   - Write either:
     - **Option A:** Updated `teams.json` (with blurbs) + `bracket_with_narrative.json` (matchups with analysis, proTeam1, proTeam2, and full team1/team2 objects for the frontend), or
     - **Option B:** Separate `narratives.json` (blurbs by team id, analysis + proTeam by game id) and a small merge script or export step that builds the final Game[] for the app.

**Recommendation:** **Option A** — single "bracket with narrative" export so the frontend can consume one file for the bracket view (games with full Team objects + analysis + proTeam arrays). Keep `teams.json` as the canonical team list (with blurbs); bracket export enriches matchup objects with narrative.

**CLI:** e.g. `python -m pipeline.gemini_narrative` (or `prompts`) that:
- Reads `data/export/teams.json` and `data/export/bracket.json`.
- Uses `GEMINI_API_KEY` (or similar) from env.
- Writes back `teams.json` (with rotobotBlurb) and `bracket.json` (with analysis, proTeam1, proTeam2, and full team1/team2 if we embed them).

---

## 5. Implementation Tasks (Order)

| # | Task | Notes |
|---|------|--------|
| 1 | **Config / env** | Add Gemini API key (env), model name (e.g. `gemini-1.5-flash`), and optional cache dir in `config.py` or `gemini_narrative.py`. |
| 2 | **Client** | Thin wrapper: call Gemini API (REST or SDK) with system + user prompt, parse JSON from response. Handle rate limits (e.g. 1 req/s) and retries. |
| 3 | **Payload builders** | Functions: `team_payload_for_blurb(team: dict) -> dict`, `matchup_payload_for_analysis(game: dict, teams: dict) -> dict`. Keep payloads small (no full percentiles dump). |
| 4 | **Prompts** | Define system prompt, blurb user prompt + 2–3 few-shot examples, matchup user prompt + 1–2 few-shot examples. Store as constants or small JSON/markdown in `pipeline/prompts/` (optional). |
| 5 | **Blurb generation** | Loop over teams (or batch), call Gemini, parse `rotobotBlurb`, assign to team; optional cache. |
| 6 | **Matchup generation** | Loop over bracket matchups, resolve team1/team2 from `teams.json` by slug, build payload, call Gemini, parse analysis + proTeam1/proTeam2; optional cache. |
| 7 | **Merge and write** | Update team objects with rotobotBlurb; build game objects with full team1/team2 (from teams.json) + analysis, proTeam1, proTeam2; write `teams.json` and `bracket.json` (or `bracket_with_narrative.json`). |
| 8 | **Export alignment** | Ensure bracketology or export can produce a Game[] shape (id, round, region, team1, team2, rotobotPick, rotobotConfidence, analysis, proTeam1, proTeam2) so the frontend’s Game interface is satisfied. |

---

## 6. Optional: rotobotPick and Confidence

- **v1:** Leave **rotobotPick** and **rotobotConfidence** to rule-based logic (e.g. power score or NET comparison); Gemini only does narrative.
- **v2:** Add an optional Gemini call per game: "Given this matchup and stats, who do you pick and with what confidence (0–100)?" and compare to rule-based pick for display (e.g. "Rotobot: Duke (85%)" vs "Gemini: Duke (78%)").

---

## 7. Files to Add / Touch

| Path | Purpose |
|------|--------|
| `pipeline/gemini_narrative.py` | Entrypoint: load teams + bracket, run blurb + matchup loops, merge, write. |
| `pipeline/prompts.py` or `pipeline/prompts/blurb.txt` + `matchup.txt` | System/user prompt text and few-shot examples. |
| `pipeline/config.py` | Optional: GEMINI_MODEL, GEMINI_CACHE_DIR, or read from env only in gemini_narrative. |
| `pipeline/export.py` or `bracketology.py` | Minor: ensure bracket output has game id and team slugs so Gemini step can join to teams and write full Game objects. |
| `docs/GEMINI_PROMPTING_PLAN.md` | This plan. |

---

## 8. Success Criteria

- Running `python -m pipeline.gemini_narrative` after export + bracketology produces:
  - `teams.json` with every bracket team having a non-empty, specific **rotobotBlurb**.
  - A bracket file (e.g. `bracket.json`) where each Round-of-64 game has **analysis**, **proTeam1**, **proTeam2**, and full **team1**/**team2** objects (so the app can render without a separate teams fetch if desired).
- Blurbs and analysis reference real stats and style copy (pace, opp PPG, key player, weakness); no generic filler.
- Output is valid JSON and parseable; no markdown or extra prose outside the specified keys.

---

**Next step:** Implement tasks 1–4 (config, client, payload builders, prompts), then 5–7 (blurb loop, matchup loop, merge/write), then 8 (export alignment). Task 6 (matchup generation) can stub analysis/proTeam with empty values if API key is missing so the pipeline still runs.
