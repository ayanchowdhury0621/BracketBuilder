# NCAA API Research Report

**API Base URL:** `https://ncaa-api.henrygd.me`  
**Source:** https://github.com/henrygd/ncaa-api  
**Rate Limit:** 5 requests/second per IP (public demo)  
**Self-hostable:** Yes, via Docker  

---

## Table of Contents

1. [General Principles](#general-principles)
2. [Scoreboard Endpoint](#1-scoreboard)
3. [Rankings Endpoints](#2-rankings)
4. [Stats Endpoints](#3-stats)
5. [Standings Endpoint](#4-standings)
6. [Game Detail Endpoints](#5-game-details)
7. [Schedule Endpoint](#6-schedule)
8. [Schools Index](#7-schools-index)
9. [History Endpoint](#8-history)
10. [Casebook Endpoint](#9-casebook)
11. [Complete Team Stat ID Reference](#10-team-stat-id-reference)
12. [Individual Stat ID Reference](#11-individual-stat-id-reference)
13. [Historical / Season Data](#12-historical-data)
14. [Pagination](#13-pagination)
15. [Quirks and Gotchas](#14-quirks-and-gotchas)

---

## General Principles

- Routes mirror the URL paths on `ncaa.com`. If the NCAA website URL is `https://www.ncaa.com/stats/basketball-men/d1/current/team/145`, the API path is `/stats/basketball-men/d1/current/team/145`.
- Sport codes for basketball: `basketball-men` (MBB), `basketball-women` (WBB)
- Division codes: `d1`, `d2`, `d3`, `fbs`, `fcs`
- All responses are JSON
- Only query parameter: `?page=N` (defaults to 1)

---

## 1. Scoreboard

**Endpoint:** `GET /scoreboard/basketball-men/d1`

Returns today's live scores. Can also specify date: `/scoreboard/basketball-men/d1/YYYY/WW/all-conf` (for football-style week format) but for basketball the default returns today's games.

### Exact Response Shape

```json
{
  "inputMD5Sum": "string",
  "instanceId": "string",
  "updated_at": "string (YYYY-MM-DD HH:MM:SS)",
  "games": [
    {
      "game": {
        "gameID": "string (numeric ID, e.g. '6502230')",
        "away": {
          "score": "string (numeric or empty if pre-game)",
          "names": {
            "char6": "string (6-char abbreviation, e.g. 'MICH')",
            "short": "string (e.g. 'Michigan')",
            "seo": "string (URL slug, e.g. 'michigan')",
            "full": "string (full name, often empty!)"
          },
          "winner": "boolean",
          "seed": "string (empty or tournament seed)",
          "description": "string (record like '(24-1)' or empty)",
          "rank": "string (AP rank or empty)",
          "conferences": [
            {
              "conferenceName": "string (often empty!)",
              "conferenceSeo": "string (e.g. 'big-ten')"
            }
          ]
        },
        "home": {
          "score": "string",
          "names": { /* same shape as away.names */ },
          "winner": "boolean",
          "seed": "string",
          "description": "string",
          "rank": "string",
          "conferences": [ /* same shape */ ]
        },
        "finalMessage": "string ('FINAL', '2ND HALF', '1ST HALF', 'HALF', or empty)",
        "bracketRound": "string",
        "title": "string (e.g. 'Michigan Purdue')",
        "contestName": "string",
        "url": "string (e.g. '/game/6502230')",
        "network": "string (TV network or empty)",
        "liveVideoEnabled": "boolean",
        "startTime": "string (e.g. '6:30 PM ET')",
        "startTimeEpoch": "string (Unix timestamp as string)",
        "bracketId": "string",
        "gameState": "string ('final' | 'live' | 'pre')",
        "startDate": "string (MM/DD/YYYY)",
        "currentPeriod": "string ('FINAL' | '1st' | '2nd' | 'HALFTIME' | empty)",
        "videoState": "string",
        "bracketRegion": "string",
        "contestClock": "string (e.g. '09:42' or '0:00')"
      }
    }
  ]
}
```

### Key Fields for Bracket Builder
- `gameState`: `"pre"` (not started), `"live"` (in progress), `"final"` (completed)
- `currentPeriod`: `"1st"`, `"2nd"`, `"HALFTIME"`, `"FINAL"`, or empty (pre-game)
- `contestClock`: Live game clock (e.g. `"09:42"`)
- `away.rank` / `home.rank`: AP ranking as string (empty if unranked)
- `url`: Use to construct game detail URL (e.g. `/game/6502230`)

### Gotchas
- `names.full` is **frequently empty** for basketball. Use `names.short` instead.
- `conferenceName` is **often empty**; rely on `conferenceSeo` for conference identification.
- `score` is a **string**, not a number. Empty string for pre-game.
- `startTimeEpoch` is a **string**, not a number.
- `hideRank` field from README example was not present in live basketball data.
- No pagination on scoreboard.

---

## 2. Rankings

### AP Top 25

**Endpoint:** `GET /rankings/basketball-men/d1/associated-press`

**NOTE:** The slug is `associated-press`, NOT `ap-top-25`. The URL path must match the ncaa.com URL.

```json
{
  "sport": "Men's Basketball",
  "title": "Associated Press",
  "updated": "Through Games FEB. 15, 2026",
  "page": 1,
  "pages": 1,
  "data": [
    {
      "RANK": "1",
      "SCHOOL (1ST VOTES)": "Michigan (60)",
      "RECORD": "24-1",
      "POINTS": "1524",
      "PREVIOUS": "2"
    }
  ]
}
```

**Field Notes:**
- Column header is `"SCHOOL (1ST VOTES)"` — first-place votes are embedded in the school name string (e.g. `"Michigan (60)"`)
- `PREVIOUS` can be `"NR"` (not ranked) or a number string
- All values are strings
- Single page (25 teams)

### NET Rankings

**Endpoint:** `GET /rankings/basketball-men/d1/ncaa-mens-basketball-net-rankings`

```json
{
  "sport": "Men's Basketball",
  "title": "NCAA Men's Basketball NET Rankings",
  "updated": "Through Games Feb. 16 2026",
  "page": 1,
  "pages": 1,
  "data": [
    {
      "Rank": "1",
      "School": "Michigan",
      "Record": "24-1",
      "Conf": "Big Ten",
      "Road": "8-0",
      "Neutral": "4-0",
      "Home": "12-1",
      "Non-Div I": "0-0",
      "Prev": "1",
      "Quad 1": "9-0",
      "Quad 2": "9-1",
      "Quad 3": "5-0",
      "Quad 4": "1-0"
    }
  ]
}
```

**Field Notes:**
- Contains ALL 362 D1 teams on a single page (`pages: 1`)
- Quadrant records are crucial for bracket selection
- `Conf` gives conference name
- Note different casing: AP uses `RANK`/`SCHOOL`, NET uses `Rank`/`School`

---

## 3. Stats

**Endpoint pattern:** `GET /stats/basketball-men/d1/current/team/{statId}`  
**Endpoint pattern:** `GET /stats/basketball-men/d1/current/individual/{statId}`

**CRITICAL:** The path must include `current` between the division and `team`/`individual`. The path `/stats/basketball-men/d1/team/145` does NOT work.

### Team Stat Response Shape

```json
{
  "sport": "Men's Basketball",
  "title": "Scoring Offense",
  "updated": "Monday, February 16, 2026 11:02 pm - Through games Monday, February 16, 2026",
  "page": 1,
  "pages": 8,
  "data": [
    {
      "Rank": "1",
      "Team": "Miami (OH)",
      "GM": "25",
      "PTS": "2315",
      "PPG": "92.6"
    }
  ]
}
```

### Pagination
- Stats are paginated: `pages: 8` means 8 pages of 50 teams each (~362 D1 teams)
- Use `?page=2`, `?page=3`, etc.
- Each page returns 50 entries
- `page` and `pages` fields tell you current page and total pages

### Confirmed Team Stat IDs (basketball-men)

| Stat ID | Title | Data Fields |
|---------|-------|-------------|
| **145** | Scoring Offense | Rank, Team, GM, PTS, PPG |
| **146** | Scoring Defense | Rank, Team, GM, OPP PTS, OPP PPG |
| **147** | Scoring Margin | Rank, Team, GM, PTS, PPG, OPP PTS, OPP PPG, SCR MAR |
| **148** | Field Goal Percentage | Rank, Team, GM, FGM, FGA, FG% |
| **149** | Field Goal Percentage Defense | Rank, Team, GM, OPP FG, OPP FGA, OPP FG% |
| **150** | Free Throw Percentage | Rank, Team, GM, FT, FTA, FT% |
| **151** | Rebound Margin | Rank, Team, GM, REB, RPG, OPP REB, OPP RPG, REB MAR |
| **152** | Three Point Percentage | Rank, Team, GM, 3FG, 3FGA, 3FG% |
| **518** | Three Point Percentage Defense | Rank, Team, GM, Opp 3FGA, Opp 3FG, Pct |

### Additional Team Stat IDs (from NCAA website dropdown)

These are the stat categories listed on the NCAA stats page. The IDs need to be discovered by checking the NCAA website URLs, but based on the pattern:

| Category | Likely ID | Notes |
|----------|-----------|-------|
| Assist/Turnover Ratio | TBD | Team stat |
| Assists Per Game | TBD | Team stat |
| Bench Points per game | TBD | Team stat |
| Blocks Per Game | TBD | Team stat |
| Effective FG pct | TBD | Team stat |
| Fastbreak Points | TBD | Team stat |
| Fouls Per Game | TBD | Team stat |
| Free Throw Attempts Per Game | TBD | Team stat |
| Free Throws Made Per Game | TBD | Team stat |
| Rebounds (Defensive) Per Game | TBD | Team stat |
| Rebounds (Offensive) Per Game | TBD | Team stat |
| Rebounds Per Game | TBD | Team stat |
| Steals Per Game | TBD | Team stat |
| Three Point Attempts Per Game | TBD | Team stat |
| Three Pointers Per Game | TBD | Team stat |
| Turnover Margin | TBD | Team stat |
| Turnovers Forced Per Game | TBD | Team stat |
| Turnovers Per Game | TBD | Team stat |
| Winning Percentage | TBD | Team stat |

### Confirmed Individual Stat IDs (from NCAA website)

| Stat ID | Title |
|---------|-------|
| **137** | Rebounds Per Game |
| **140** | Assists Per Game |
| **750** | Rushing TDs (football, for reference) |

### Individual Stat Categories Available (from NCAA website dropdown)

- Assist/Turnover Ratio
- Assists / Assists Per Game
- Blocks / Blocks Per Game
- Double Doubles
- Field Goal Attempts / Field Goal Percentage / Field Goals
- Free Throw Attempts / Free Throw Percentage / Free Throws
- Minutes Per Game
- Points / Points Per Game
- Rebounds / Rebounds Per Game / Rebounds (Defensive) Per Game / Rebounds (Offensive) Per Game
- Steals / Steals Per Game
- Three Point Attempts / Three Point Percentage / Three Pointers Per Game / Total 3-point FGM
- Triple Doubles

---

## 4. Standings

**Endpoint:** `GET /standings/basketball-men/d1`

```json
{
  "sport": "Men's Basketball",
  "title": "ALL CONFERENCES",
  "updated": "Feb 17, 2026 04:21 AM EDT",
  "page": 1,
  "pages": 1,
  "data": [
    {
      "conference": "ACC",
      "standings": [
        {
          "School": "Duke",
          "Conference W": "13",
          "Conference L": "1",
          "Conference PCT": "0.929",
          "Overall W": "24",
          "Overall L": "2",
          "Overall PCT": "0.923",
          "Overall STREAK": "Won 3"
        }
      ]
    },
    {
      "conference": "Big Ten",
      "standings": [ /* same shape */ ]
    }
  ]
}
```

**Field Notes:**
- All conferences returned on a single page (`pages: 1`)
- Conferences are sorted alphabetically
- Each conference contains a `standings` array sorted by conference win percentage
- All values are strings
- `Overall STREAK` format: `"Won N"` or `"Lost N"`

---

## 5. Game Details

### Game Info

**Endpoint:** `GET /game/{gameId}`

```json
{
  "contests": [
    {
      "__typename": "Contest",
      "id": "6502230",
      "sportCode": "MBB",
      "sportUrl": "basketball-men",
      "division": 1,
      "clock": "",
      "currentPeriod": "FINAL",
      "finalMessage": "FINAL",
      "gameState": "F",
      "statusCodeDisplay": "final",
      "network": null,
      "startTime": "18:30",
      "startTimeEpoch": 1771371000,
      "week": null,
      "seasonYear": 2025,
      "winner": 1845,
      "hasStartTime": true,
      "hasBoxscore": true,
      "hasPbp": true,
      "hasScoringSummary": false,
      "hasPreview": false,
      "hasRecap": false,
      "hasTeamStats": true,
      "linescores": [
        {
          "__typename": "Linescore",
          "period": "1",
          "home": "32",
          "visit": "48"
        },
        {
          "__typename": "Linescore",
          "period": "2",
          "home": "48",
          "visit": "43"
        }
      ],
      "teams": [
        {
          "__typename": "ContestTeam",
          "teamId": "243",
          "isHome": true,
          "color": "#010101",
          "seoname": "purdue",
          "nameFull": "Purdue University",
          "nameShort": "Purdue",
          "name6Char": "PURDUE",
          "teamRank": 7,
          "gameRank": 7,
          "score": 80,
          "seed": null,
          "record": "(21-4)",
          "divisionName": "d1",
          "division": 1,
          "isWinner": false
        },
        {
          "__typename": "ContestTeam",
          "teamId": "1845",
          "isHome": false,
          "color": "#041E42",
          "seoname": "michigan",
          "nameFull": "University of Michigan",
          "nameShort": "Michigan",
          "name6Char": "MICH",
          "teamRank": 1,
          "gameRank": 1,
          "score": 91,
          "seed": null,
          "record": "(24-1)",
          "divisionName": "d1",
          "division": 1,
          "isWinner": true
        }
      ],
      "liveVideos": [],
      "championship": null,
      "championshipGame": null,
      "links": [],
      "location": {
        "__typename": "Location",
        "venue": "Mackey Arena",
        "city": "West Lafayette",
        "stateUsps": "IN"
      },
      "stats": null
    }
  ]
}
```

**Key Fields:**
- `gameState`: `"F"` (final), `"I"` (in progress), `"P"` (pre-game) — different from scoreboard!
- `winner`: numeric teamId of winning team
- `hasBoxscore`, `hasPbp`, `hasTeamStats`: booleans indicating available sub-endpoints
- `linescores`: half-by-half scoring
- `teams[].color`: hex color for team branding
- `teams[].teamId`: numeric string, used in boxscore to match teams
- `seasonYear`: 2025 means the 2025-26 season
- `startTimeEpoch`: actual number here (not string like scoreboard)

### Box Score

**Endpoint:** `GET /game/{gameId}/boxscore`

```json
{
  "__typename": "Boxscore",
  "title": "MBB Boxscore",
  "contestId": 6502230,
  "description": "Purdue vs Michigan",
  "division": 1,
  "divisionName": "d1",
  "status": "F",
  "period": "FINAL",
  "sportCode": "MBB",
  "teams": [
    {
      "__typename": "ContestTeam",
      "isHome": true,
      "teamId": "243",
      "seoname": "purdue",
      "name6Char": "PURDUE",
      "nameFull": "Purdue University",
      "nameShort": "Purdue",
      "teamName": "Boilermakers",
      "color": "#010101"
    }
  ],
  "teamBoxscore": [
    {
      "__typename": "BoxscoreDetails",
      "teamId": 243,
      "playerStats": [
        {
          "__typename": "PlayerStatsBasketball",
          "id": 4,
          "number": 4,
          "firstName": "Trey",
          "lastName": "Kaufman-Renn",
          "position": "F",
          "minutesPlayed": "36.1",
          "year": "",
          "elig": "",
          "starter": true,
          "fieldGoalsMade": "12",
          "fieldGoalsAttempted": "26",
          "freeThrowsMade": "3",
          "freeThrowsAttempted": "3",
          "threePointsMade": "0",
          "threePointsAttempted": "2",
          "offensiveRebounds": "7",
          "totalRebounds": "12",
          "assists": "0",
          "turnovers": "0",
          "personalFouls": "2",
          "steals": "0",
          "blockedShots": "0",
          "points": "3"
        }
      ],
      "teamStats": {
        "__typename": "TeamStatsBasketball",
        "fieldGoalsMade": "27",
        "fieldGoalsAttempted": "69",
        "freeThrowsMade": "18",
        "freeThrowsAttempted": "20",
        "threePointsMade": "8",
        "threePointsAttempted": "26",
        "offensiveRebounds": "14",
        "totalRebounds": "31",
        "assists": "12",
        "turnovers": "6",
        "personalFouls": "17",
        "steals": "10",
        "blockedShots": "3",
        "points": "80",
        "fieldGoalPercentage": "39.1%",
        "threePointPercentage": "30.8%",
        "freeThrowPercentage": "90.0%"
      }
    }
  ]
}
```

**Player Stats Fields (PlayerStatsBasketball):**
- `id`, `number`: jersey number
- `firstName`, `lastName`
- `position`: "G", "F", "C"
- `minutesPlayed`: string (decimal, e.g. "36.1")
- `year`, `elig`: usually empty strings
- `starter`: boolean
- `fieldGoalsMade`, `fieldGoalsAttempted`: strings
- `freeThrowsMade`, `freeThrowsAttempted`: strings
- `threePointsMade`, `threePointsAttempted`: strings
- `offensiveRebounds`, `totalRebounds`: strings
- `assists`, `turnovers`, `personalFouls`, `steals`, `blockedShots`, `points`: strings

**Team Stats Fields (TeamStatsBasketball):**
- Same counting stats as player stats
- Plus percentage fields: `fieldGoalPercentage`, `threePointPercentage`, `freeThrowPercentage` (strings with % sign)

### Team Stats (Game)

**Endpoint:** `GET /game/{gameId}/team-stats`

Same structure as boxscore but **without `playerStats`** — only `teamStats` per team.

### Play-by-Play

**Endpoint:** `GET /game/{gameId}/play-by-play`

```json
{
  "__typename": "PlayByPlay",
  "contestId": 6502230,
  "title": "MBB PLAY-BY-PLAY",
  "description": "Purdue vs Michigan",
  "divisionName": "d1",
  "status": "final",
  "period": 2,
  "teams": [ /* ContestTeam array */ ],
  "periods": [
    {
      "__typename": "PlayByPlayDetails",
      "periodNumber": 1,
      "periodDisplay": "1st Half",
      "playbyplayStats": [
        {
          "__typename": "PlayByPlayBasketball",
          "teamId": 1845,
          "score": "(0-0)",
          "homeScore": 0,
          "visitorScore": 0,
          "visitorText": "Aday Mara vs Oscar Cluff (Michigan gains possesion)",
          "homeText": "",
          "clock": "20:00",
          "firstName": "",
          "lastName": "",
          "eventId": -99,
          "eventDescription": "Aday Mara vs Oscar Cluff (Michigan gains possesion)",
          "isHome": false
        }
      ]
    }
  ]
}
```

**Play-by-Play Fields:**
- `score`: format `"(visitor-home)"` e.g. `"(48-32)"`
- `homeScore`, `visitorScore`: numbers
- `homeText`, `visitorText`: description of play (one is populated, other is empty)
- `clock`: game clock as string (e.g. `"20:00"`, `"14:37"`)
- `eventDescription`: same as the populated text field
- `isHome`: boolean indicating which team the play belongs to
- `eventId`: always `-99` in observed data

**Gotcha:** Play-by-play events are often **duplicated** — the same play appears twice in sequence with slightly different formatting (e.g. with/without spaces in names). Filter for unique entries.

### Scoring Summary

**Endpoint:** `GET /game/{gameId}/scoring-summary`

Available for some sports (football). For basketball, `hasScoringSummary` is typically `false`.

---

## 6. Schedule

**Endpoint:** `GET /schedule/basketball-men/d1/{YYYY}/{MM}`

Returns game dates (not individual games) for a given month.

```json
{
  "division": "d1",
  "inputMD5Sum": "string",
  "month": "02",
  "gameDates": [
    {
      "contest_date": "02-05-2025",
      "year": "2025",
      "weekday": "Wed",
      "games": 24,
      "season": "2024",
      "day": "05"
    },
    {
      "contest_date": "02-06-2025",
      "year": "2025",
      "weekday": "Thu",
      "games": 91,
      "season": "2024",
      "day": "06"
    }
  ],
  "conference_name": "all-conf",
  "created_at": "05-15-2025 11:00:16",
  "season": "2024",
  "sport": "WSB"
}
```

**Key Notes:**
- `season` field: `"2024"` means the 2024-25 season (academic year convention)
- `games`: count of games on that date (number, not string)
- This only gives you dates and game counts, NOT individual game details
- To get actual games for a date, use the scoreboard endpoint with that date

---

## 7. Schools Index

**Endpoint:** `GET /schools-index`

Returns ALL NCAA schools (all divisions, all sports).

```json
[
  {
    "slug": "duke",
    "name": "Duke",
    "long": "Duke University"
  },
  {
    "slug": "michigan",
    "name": "Michigan",
    "long": "University of Michigan"
  }
]
```

**Notes:**
- Returns a flat array (not paginated)
- ~2,500+ schools
- `slug` is the SEO-friendly identifier used in other endpoints
- `name` is the short display name
- `long` is the full official name

---

## 8. History

**Endpoint:** `GET /history/{sport}/{division}`

Example: `GET /history/basketball-men/d1`

Returns championship history. Structure varies by sport.

---

## 9. Casebook Endpoint

**Status:** The `/casebook/basketball-men/d1/{school-slug}` endpoint was tested but returned errors. This endpoint may not be available for basketball or may require a different path format. The README does not document this endpoint.

**Alternative for school info:** Use the `/schools-index` endpoint for school names/slugs, and team colors are available in the `/game/{id}` response (`teams[].color`).

---

## 10. Team Stat ID Reference

### Confirmed Working IDs (basketball-men/d1)

| ID | Stat Name | Key Data Fields |
|----|-----------|-----------------|
| 145 | Scoring Offense | GM, PTS, PPG |
| 146 | Scoring Defense | GM, OPP PTS, OPP PPG |
| 147 | Scoring Margin | GM, PTS, PPG, OPP PTS, OPP PPG, SCR MAR |
| 148 | Field Goal Percentage | GM, FGM, FGA, FG% |
| 149 | FG Percentage Defense | GM, OPP FG, OPP FGA, OPP FG% |
| 150 | Free Throw Percentage | GM, FT, FTA, FT% |
| 151 | Rebound Margin | GM, REB, RPG, OPP REB, OPP RPG, REB MAR |
| 152 | Three Point Percentage | GM, 3FG, 3FGA, 3FG% |
| 518 | 3PT Percentage Defense | GM, Opp 3FGA, Opp 3FG, Pct |

### Full List of Available Team Stats (from NCAA website dropdown)

To discover IDs, visit `https://www.ncaa.com/stats/basketball-men/d1` and inspect the links. Known pattern: IDs are in the URL path. Here are all categories available:

1. Assist/Turnover Ratio
2. Assists Per Game
3. Bench Points per game
4. Blocks Per Game
5. Effective FG pct
6. Fastbreak Points
7. Field Goal Percentage (148)
8. Field Goal Percentage Defense (149)
9. Fouls Per Game
10. Free Throw Attempts Per Game
11. Free Throw Percentage (150)
12. Free Throws Made Per Game
13. Rebound Margin (151)
14. Rebounds (Defensive) Per Game
15. Rebounds (Offensive) Per Game
16. Rebounds Per Game
17. Scoring Defense (146)
18. Scoring Margin (147)
19. Scoring Offense (145)
20. Steals Per Game
21. Three Point Attempts Per Game
22. Three Point Percentage (152)
23. Three Point Percentage Defense (518)
24. Three Pointers Per Game
25. Turnover Margin
26. Turnovers Forced Per Game
27. Turnovers Per Game
28. Winning Percentage

**To discover remaining IDs:** Visit `https://www.ncaa.com/stats/basketball-men/d1` in a browser, select each stat from the dropdown, and note the numeric ID in the resulting URL.

---

## 11. Individual Stat ID Reference

### Known IDs

| ID | Stat Name |
|----|-----------|
| 137 | Rebounds Per Game |
| 140 | Assists Per Game |

### All Available Individual Stats (from NCAA website)

- Assist/Turnover Ratio
- Assists / Assists Per Game (140)
- Blocks / Blocks Per Game
- Double Doubles
- Field Goal Attempts / Field Goal Percentage / Field Goals
- Free Throw Attempts / Free Throw Percentage / Free Throws
- Minutes Per Game
- Points / Points Per Game
- Rebounds / Rebounds Per Game (137) / Rebounds (Defensive) Per Game / Rebounds (Offensive) Per Game
- Steals / Steals Per Game
- Three Point Attempts / Three Point Percentage / Three Pointers Per Game / Total 3-point FGM
- Triple Doubles

Individual stat endpoint: `/stats/basketball-men/d1/current/individual/{statId}`

---

## 12. Historical Data

### Accessing Past Seasons

The `current` keyword in the stats URL refers to the current season. For historical data:

- **Stats:** Replace `current` with a specific season. The NCAA website uses URLs like `/stats/basketball-men/d1/2024/team/145` for the 2023-24 season. Try the same pattern with the API.
- **Schedule:** Use past year/month: `/schedule/basketball-men/d1/2025/02` returns February 2025 game dates (2024-25 season). This was confirmed working.
- **Scoreboard:** Historical scoreboards may work with date-specific paths.
- **Game details:** Game IDs are permanent. If you have a game ID from a past season, `/game/{id}`, `/game/{id}/boxscore`, etc. should still work.

### Season Naming Convention
- `season: "2024"` in the schedule response = the 2024-25 academic year
- `seasonYear: 2025` in the game response = the 2025-26 academic year (different convention!)

---

## 13. Pagination

### How It Works

- Query parameter: `?page=N` (1-indexed)
- Response includes `page` (current) and `pages` (total)
- Default: page 1
- Page size: ~50 entries for stats
- Standings and rankings: typically 1 page (all data)
- Scoreboard: no pagination (all games for the day)

### Example

```
GET /stats/basketball-men/d1/current/team/145?page=2
→ { "page": 2, "pages": 8, "data": [...50 teams...] }
```

To get all teams: loop from page 1 to `pages`.

---

## 14. Quirks and Gotchas

### Data Type Inconsistencies
1. **Almost everything is a string** in stats/rankings/standings, even numeric values like scores, ranks, and percentages.
2. **Game detail endpoint** uses actual numbers for `score`, `teamRank`, `startTimeEpoch` — inconsistent with scoreboard.
3. **Boxscore player stats** are all strings despite being numeric.

### Naming Inconsistencies
4. **Column names vary by endpoint:**
   - AP Rankings: `RANK`, `SCHOOL (1ST VOTES)` (ALL CAPS)
   - NET Rankings: `Rank`, `School` (Title Case)
   - Stats: `Rank`, `Team` (Title Case)
5. **Team names vary across endpoints:**
   - Scoreboard: `names.short` = "Michigan"
   - Stats: `Team` = "Michigan"
   - Game: `nameShort` = "Michigan", `nameFull` = "University of Michigan"
   - Schools: `name` = "Michigan", `slug` = "michigan"

### Missing/Empty Fields
6. `names.full` in scoreboard is **frequently empty** for basketball
7. `conferenceName` in scoreboard is **frequently empty**
8. `year` and `elig` in boxscore player stats are **always empty strings**
9. `description` in scoreboard (team record) is **sometimes empty**

### Play-by-Play Duplication
10. PBP events appear **twice** — once with spaces in names, once without (e.g. "Trey Kaufman-Renn misses" and "Trey Kaufman-Rennmisses"). Deduplicate by checking consecutive entries.

### Rank Ties
11. In stats, tied ranks show as `"-"` for the tied entries after the first.

### Casebook/Logo
12. The `/casebook/` endpoint does not appear to work for basketball. No documented way to get team logos through this API. Team colors are available in game detail responses.

### Rate Limiting
13. Public API: 5 requests/second per IP. Self-host for higher throughput.

### Game IDs
14. Game IDs from the scoreboard (`game.url` field like `/game/6502230`) can be used directly with the game detail endpoints.
15. The `gameID` in scoreboard is the same as the contest ID in game details.

### Season Data
16. The `seasonYear` in game responses and `season` in schedule responses use **different conventions** (off by one year).

---

## Summary: Key Endpoints for Bracket Builder

| Need | Endpoint | Notes |
|------|----------|-------|
| Live scores | `/scoreboard/basketball-men/d1` | All today's games |
| AP Rankings | `/rankings/basketball-men/d1/associated-press` | Top 25 |
| NET Rankings | `/rankings/basketball-men/d1/ncaa-mens-basketball-net-rankings` | All 362 teams, quad records |
| Team stats | `/stats/basketball-men/d1/current/team/{id}` | Paginated, 50/page |
| Conference standings | `/standings/basketball-men/d1` | All conferences, single page |
| Game box score | `/game/{id}/boxscore` | Full player + team stats |
| Game play-by-play | `/game/{id}/play-by-play` | Every play with clock/score |
| Game overview | `/game/{id}` | Linescores, venue, teams |
| Game team stats | `/game/{id}/team-stats` | Aggregate team stats only |
| Schedule dates | `/schedule/basketball-men/d1/{YYYY}/{MM}` | Game counts per date |
| All schools | `/schools-index` | Names, slugs for all NCAA schools |
