"""Prompt payload markdown builders."""

from __future__ import annotations

from typing import Any


def build_team_markdown(team: dict[str, Any], news: str = "") -> str:
    """Render a compact markdown data block for one team."""
    name = team.get("name", "")
    conf = team.get("conference", "")
    record = team.get("record", "")
    seed = team.get("seed", 0)
    net = team.get("netRank", 999)
    score = team.get("rotobotScore", 50)
    seed_str = f", #{seed} seed" if seed and seed > 0 else ""
    header = f"## {name} ({conf}) - {record}, NET #{net}{seed_str}, RotoBot Score: {score}"

    identity = team.get("styleIdentity", "")
    weakness = team.get("styleWeakness", "")
    bullets = team.get("styleBullets", "")
    key_player = team.get("keyPlayer", "")
    key_stat = team.get("keyPlayerStat", "")
    stats = team.get("stats", {})
    scoring = stats.get("scoring", {})
    shooting = stats.get("shooting", {})
    reb = stats.get("rebounding", {})
    ball = stats.get("ballControl", {})
    defense = stats.get("defense", {})
    tempo = stats.get("tempo", {})

    stat_line = " | ".join(
        filter(
            None,
            [
                f"{scoring.get('ppg', 0)} PPG",
                f"{scoring.get('oppg', 0)} OPPG",
                f"{tempo.get('pace', 0)} pace",
                f"{shooting.get('eFGPct', 0)}% eFG",
                f"{defense.get('fgPctDefense', 0)}% opp FG",
                f"{shooting.get('threePtPct', 0)}% 3P",
                f"{shooting.get('threePtAttemptsPG', 0)} 3PA/G",
                f"{ball.get('turnoversForcedPG', 0)} TO forced/G",
                f"{reb.get('orebPG', 0)} OREB/G",
                f"{shooting.get('ftPct', 0)}% FT",
                f"{scoring.get('benchPPG', 0)} bench PPG",
                f"{ball.get('astToRatio', 0)} A/TO",
            ],
        )
    )

    parts = [header, ""]
    if identity:
        parts.append(f"**Identity:** {identity}")
    parts.append(f"**Key Stats:** {stat_line}")
    if bullets:
        parts.append(f"**Scouting Bullets:** {bullets}")
    if weakness:
        parts.append(f"**Weakness:** {weakness}")
    if key_player:
        parts.append(f"**Key Player:** {key_player} - {key_stat}")
    if news:
        parts.append(f"**Recent News:** {news}")
    return "\n".join(parts)


def build_matchup_markdown(
    game: dict[str, Any],
    team1: dict[str, Any],
    team2: dict[str, Any],
    news1: str,
    news2: str,
    edges: list[dict[str, Any]],
) -> str:
    """Render a full matchup markdown block for one game."""
    region = game.get("region", "")
    seed1 = game.get("team1Seed", 0)
    seed2 = game.get("team2Seed", 0)
    name1 = team1.get("name", game.get("team1", ""))
    name2 = team2.get("name", game.get("team2", ""))
    header = f"## {region} Region, Round of 64: ({seed1}) {name1} vs ({seed2}) {name2}"

    t1_md = build_team_markdown(team1, news1).replace("## ", "### ", 1)
    t2_md = build_team_markdown(team2, news2).replace("## ", "### ", 1)
    edge_lines = ["### Head-to-Head Edges:"]
    for e in edges:
        label = e.get("label", "")
        v1 = e.get("team1Value", 0)
        v2 = e.get("team2Value", 0)
        winner = e.get("edge", "even")
        arrow = name1 if winner == "team1" else (name2 if winner == "team2" else "Even")
        edge_lines.append(f"- {label}: {name1} {v1} vs {name2} {v2} -> {arrow}")
    return "\n\n".join([header, t1_md, t2_md, "\n".join(edge_lines)])
