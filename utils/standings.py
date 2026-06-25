import discord
import asyncio
import json
import os
import base64
import requests
from dotenv import load_dotenv
from pathlib import Path
from typing import Dict, Any

from utils.config import NFL_TEAMS, STANDINGS_CHANNEL_ID

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_API_URL = "https://api.github.com/repos/landenj927-coder/sfg-bot/contents/data/standings.json"

BASE_DIR = Path(__file__).resolve().parent.parent
SCHEDULE_FILE = BASE_DIR / "data" / "schedule.json"
STANDINGS_FILE = BASE_DIR / "data" / "standings.json"

STANDINGS_LOCK = asyncio.Lock()

TEAM_EMOJIS = {
    "Arizona Cardinals": "<:ArizonaCardinals:1488398835481837609>",
    "Atlanta Falcons": "<:AtlantaFalcons:1448881506905751653>",
    "Baltimore Ravens": "<:BaltimoreRavens:1488398920437600306>",
    "Buffalo Bills": "<:BuffaloBills:1448881454640533504>",
    "Carolina Panthers": "<:CarolinaPanthers:1488398978545483888>",
    "Chicago Bears": "<:ChicagoBears:1448881495694381218>",
    "Cincinnati Bengals": "<:CincinnatiBengals:1488399039366955081>",
    "Cleveland Browns": "<:ClevelandBrowns:1488399104865472532>",
    "Dallas Cowboys": "<:DallasCowboys:1488399171118567544>",
    "Denver Broncos": "<:DenverBroncos:1448881475821768785>",
    "Detroit Lions": "<:DetroitLions:1488399241570156677>",
    "Green Bay Packers": "<:GreenBayPackers:1488399331630518364>",
    "Houston Texans": "<:HoustonTexans:1488392844904235058>",
    "Indianapolis Colts": "<:IndianapolisColts:1488399437012275250>",
    "Jacksonville Jaguars": "<:JacksonvilleJaguars:1488399459586015302>",
    "Kansas City Chiefs": "<:KansasCityChiefs:1488399480838688808>",
    "Las Vegas Raiders": "<:LasVegasRaiders:1488399504582381659>",
    "Los Angeles Rams": "<:LosAngelesRams:1448881461057814658>",
    "Los Angeles Chargers": "<:LosAngelesChargers:1488399527861030952>",
    "Miami Dolphins": "<:MiamiDolphins:1488399669599141959>",
    "Minnesota Vikings": "<:MinnesotaVikings:1488399693028524082>",
    "New England Patriots": "<:NewEnglandPatriots:1488399780416851968>",
    "New Orleans Saints": "<:NewOrleansSaints:1488399800264036383>",
    "New York Giants": "<:NewYorkGiants:1488399822645104693>",
    "Philadelphia Eagles": "<:PhiladelphiaEagles:1488400260085841940>",
    "Pittsburgh Steelers": "<:PittsburghSteelers:1488400288921419827>",
    "San Francisco 49ers": "<:SanFrancisco49ers:1488400308441714782>",
    "Seattle Seahawks": "<:SeattleSeahawks:1488400334371033139>",
    "Tampa Buccaneers": "<:TampaBayBucaneers:1448881513985736776>",
    "Tennessee Titans": "<:TennesseeTitans:1488400447948460042>",
    "Washington Commanders": "<:WashingtonFootballTeam:1488400469221969970>",
    "Newark": "<:NewYorkJets:1488400218075566211>",
}


def get_schedule_teams() -> list[str]:
    if not SCHEDULE_FILE.exists():
        return list(NFL_TEAMS)

    try:
        with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        teams = []
        for games in data.get("weeks", {}).values():
            for team1, team2 in games:
                if team1 not in teams:
                    teams.append(team1)
                if team2 not in teams:
                    teams.append(team2)

        return teams or list(NFL_TEAMS)

    except Exception as e:
        print(f"Error loading schedule teams: {e}")
        return list(NFL_TEAMS)


def get_active_teams():
    return get_schedule_teams()


def _fresh_standings_data(season: int = 1, standings_message_id=None) -> Dict[str, Any]:
    teams = get_schedule_teams()

    return {
        "season": season,
        "standings_message_id": standings_message_id,
        "teams": {
            team: {"wins": 0, "losses": 0, "pf": 0, "pa": 0, "streak": 0}
            for team in teams
        }
    }


def load_standings() -> Dict[str, Any]:
    if not STANDINGS_FILE.exists():
        return _fresh_standings_data()

    with open(STANDINGS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    data.setdefault("season", 1)
    data.setdefault("standings_message_id", None)
    data.setdefault("teams", {})

    for team in get_schedule_teams():
        if team not in data["teams"]:
            data["teams"][team] = {
                "wins": 0,
                "losses": 0,
                "pf": 0,
                "pa": 0,
                "streak": 0,
            }
        else:
            data["teams"][team].setdefault("wins", 0)
            data["teams"][team].setdefault("losses", 0)
            data["teams"][team].setdefault("pf", 0)
            data["teams"][team].setdefault("pa", 0)
            data["teams"][team].setdefault("streak", 0)

    return data


def push_standings_to_github(data: Dict[str, Any]):
    if not GITHUB_TOKEN:
        print("⚠️ GITHUB_TOKEN not set. Standings saved locally only.")
        return

    try:
        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
        }

        get_resp = requests.get(GITHUB_API_URL, headers=headers, timeout=15)
        sha = None

        if get_resp.status_code == 200:
            sha = get_resp.json().get("sha")

        content = json.dumps(data, indent=4).encode("utf-8")
        encoded_content = base64.b64encode(content).decode("utf-8")

        payload = {
            "message": "Update standings.json",
            "content": encoded_content,
            "branch": "main",
        }

        if sha:
            payload["sha"] = sha

        put_resp = requests.put(
            GITHUB_API_URL,
            headers=headers,
            json=payload,
            timeout=15,
        )

        if put_resp.status_code in (200, 201):
            print("✅ standings.json pushed to GitHub")
        else:
            print(f"⚠️ GitHub standings push failed: {put_resp.status_code} {put_resp.text[:300]}")

    except Exception as e:
        print(f"⚠️ GitHub standings push error: {type(e).__name__}: {e}")


def save_standings(data: Dict[str, Any]):
    STANDINGS_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(STANDINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

    push_standings_to_github(data)


def reset_standings(season: int = 1, standings_message_id=None):
    data = _fresh_standings_data(
        season=season,
        standings_message_id=standings_message_id,
    )
    save_standings(data)


def update_game_result(team1: str, team2: str, score1: int, score2: int):
    data = load_standings()

    if team1 not in data["teams"] or team2 not in data["teams"]:
        raise ValueError(
            f"One or both team names are invalid: '{team1}' vs '{team2}'"
        )

    t1 = data["teams"][team1]
    t2 = data["teams"][team2]

    score1 = int(score1)
    score2 = int(score2)

    t1["pf"] += score1
    t1["pa"] += score2
    t2["pf"] += score2
    t2["pa"] += score1

    if score1 > score2:
        t1["wins"] += 1
        t2["losses"] += 1
        t1["streak"] = t1["streak"] + 1 if t1["streak"] >= 0 else 1
        t2["streak"] = t2["streak"] - 1 if t2["streak"] <= 0 else -1
    elif score2 > score1:
        t2["wins"] += 1
        t1["losses"] += 1
        t2["streak"] = t2["streak"] + 1 if t2["streak"] >= 0 else 1
        t1["streak"] = t1["streak"] - 1 if t1["streak"] <= 0 else -1

    save_standings(data)


def _rank_display(rank: int) -> str:
    if rank == 1:
        return "🥇"
    if rank == 2:
        return "🥈"
    if rank == 3:
        return "🥉"
    return f"#{rank}"


def _streak_display(streak: int) -> str:
    if streak > 0:
        return f"W{streak}"
    if streak < 0:
        return f"L{abs(streak)}"
    return "–"


def format_team_line(rank: int, name: str, stats: Dict[str, Any]) -> str:
    wins = int(stats.get("wins", 0))
    losses = int(stats.get("losses", 0))
    pf = int(stats.get("pf", 0))
    pa = int(stats.get("pa", 0))
    streak = int(stats.get("streak", 0))

    pd = pf - pa
    emoji = TEAM_EMOJIS.get(name, "🏈")
    rank_display = _rank_display(rank)
    streak_display = _streak_display(streak)

    return f"{rank_display} {emoji} **{name}** `{wins}-{losses}` `({pd:+})` `{streak_display}`"


def sort_key(item):
    name, stats = item
    wins = int(stats.get("wins", 0))
    losses = int(stats.get("losses", 0))
    pf = int(stats.get("pf", 0))
    pa = int(stats.get("pa", 0))

    games = wins + losses
    win_pct = wins / games if games > 0 else 0.0
    pd = pf - pa

    return (win_pct, pd, wins)


def build_standings_embed(data: Dict[str, Any]) -> discord.Embed:
    season = data.get("season", 1)
    schedule_teams = get_schedule_teams()

    teams = {
        team: data["teams"].get(
            team,
            {"wins": 0, "losses": 0, "pf": 0, "pa": 0, "streak": 0},
        )
        for team in schedule_teams
    }

    sorted_teams = sorted(
        teams.items(),
        key=sort_key,
        reverse=True,
    )

    embed = discord.Embed(
        title=f"🏆 SFG Season {season} Standings",
        description="🏈 *Official SFG League Standings*\nSorted by Win % → PD → Wins",
        color=discord.Color.blue(),
    )

    chunk_size = 4
    rank = 1

    for i in range(0, len(sorted_teams), chunk_size):
        group = sorted_teams[i:i + chunk_size]
        start = i + 1
        end = i + len(group)

        lines = []

        for team_name, stats in group:
            if rank == 11:
                lines.append("🔴 **PLAYOFF CUT** ─────────")

            lines.append(format_team_line(rank, team_name, stats))
            rank += 1

        embed.add_field(
            name=f"📊 Division {(i // chunk_size) + 1} ({start}–{end})",
            value="\n".join(lines) if lines else "No teams",
            inline=False,
        )

    embed.set_footer(
        text="Sorted by Win% → Point Differential → Wins • PD = PF - PA"
    )

    return embed


async def post_or_update_standings(guild: discord.Guild):
    async with STANDINGS_LOCK:
        data = load_standings()

        channel = guild.get_channel(STANDINGS_CHANNEL_ID)
        if channel is None:
            try:
                channel = await guild.fetch_channel(STANDINGS_CHANNEL_ID)
            except Exception:
                print("❌ Invalid standings channel ID")
                return

        embed = build_standings_embed(data)
        msg_id = data.get("standings_message_id")

        if msg_id:
            try:
                msg = await channel.fetch_message(int(msg_id))
                await msg.edit(embed=embed)
                print("✅ Standings updated by editing existing message")
                return
            except discord.NotFound:
                print("⚠️ Stored standings message was not found; creating a new one")
            except Exception as e:
                print(f"⚠️ Could not edit standings message: {e}")

        msg = await channel.send(embed=embed)
        data["standings_message_id"] = msg.id
        save_standings(data)

        print("🆕 New standings message created and saved")