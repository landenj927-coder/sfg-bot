import discord
import asyncio
import json
import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

GITHUB_RAW_URL = "https://raw.githubusercontent.com/landenj927-coder/sfg-bot/main/data/standings.json"
GITHUB_API_URL = "https://api.github.com/repos/landenj927-coder/sfg-bot/contents/data/standings.json"

from pathlib import Path
from typing import Dict, Any, List

SCHEDULE_FILE = Path("schedule.json")

# =========================================================
# CONFIG
# =========================================================

STANDINGS_CHANNEL_ID = 1488382113240711189
STANDINGS_FILE = Path("standings.json")
STANDINGS_LOCK = asyncio.Lock()

NFL_TEAMS: List[str] = [
    "Arizona", "Atlanta", "Baltimore", "Buffalo", "Carolina", "Chicago", "Cincinnati", "Cleveland",
    "Dallas", "Denver", "Detroit", "GreenBay", "Houston", "Indianapolis", "Jacksonville", "Chiefs",
    "LasVegas", "Rams", "Chargers", "Miami", "Minnesota", "Patriots", "Saints", "Giants", "Jets",
    "Philadelphia", "Pittsburgh", "49ers", "Seattle", "Tampa", "Tennessee", "Washington"
]

TEAM_EMOJIS = {
    "Arizona": "<:ArizonaCardinals:1488398835481837609>",
    "Atlanta": "<:AtlantaFalcons:1448881506905751653>",
    "Baltimore": "<:BaltimoreRavens:1488398920437600306>",
    "Buffalo": "<:BuffaloBills:1448881454640533504>",
    "Carolina": "<:CarolinaPanthers:1488398978545483888>",
    "Chicago": "<:ChicagoBears:1448881495694381218>",
    "Cincinnati": "<:CincinnatiBengals:1488399039366955081>",
    "Cleveland": "<:ClevelandBrowns:1488399104865472532>",
    "Dallas": "<:DallasCowboys:1488399171118567544>",
    "Denver": "<:DenverBroncos:1448881475821768785>",
    "Detroit": "<:DetroitLions:1488399241570156677>",
    "GreenBay": "<:GreenBayPackers:1488399331630518364>",
    "Houston": "<:HoustonTexans:1488392844904235058>",
    "Indianapolis": "<:IndianapolisColts:1488399437012275250>",
    "Jacksonville": "<:JacksonvilleJaguars:1488399459586015302>",
    "Chiefs": "<:KansasCityChiefs:1488399480838688808>",
    "LasVegas": "<:LasVegasRaiders:1488399504582381659>",
    "Rams": "<:LosAngelesRams:1448881461057814658>",
    "Chargers": "<:LosAngelesChargers:1488399527861030952>",
    "Miami": "<:MiamiDolphins:1488399669599141959>",
    "Minnesota": "<:MinnesotaVikings:1488399693028524082>",
    "Patriots": "<:NewEnglandPatriots:1488399780416851968>",
    "Saints": "<:NewOrleansSaints:1488399800264036383>",
    "Giants": "<:NewYorkGiants:1488399822645104693>",
    "Jets": "<:NewYorkJets:1488400218075566211>",
    "Philadelphia": "<:PhiladelphiaEagles:1488400260085841940>",
    "Pittsburgh": "<:PittsburghSteelers:1488400288921419827>",
    "49ers": "<:SanFrancisco49ers:1488400308441714782>",
    "Seattle": "<:SeattleSeahawks:1488400334371033139>",
    "Tampa": "<:TampaBayBucaneers:1448881513985736776>",
    "Tennessee": "<:TennesseeTitans:1488400447948460042>",
    "Washington": "<:WashingtonFootballTeam:1488400469221969970>",
}


SCHEDULE_FILE = Path("schedule.json")

def get_active_teams():
    if not SCHEDULE_FILE.exists():
        return None

    try:
        with open(SCHEDULE_FILE, "r") as f:
            data = json.load(f)
            return data.get("teams", None)
    except:
        return None

# =========================================================
# FILE HANDLING
# =========================================================

def _fresh_standings_data(season: int = 1, standings_message_id=None) -> Dict[str, Any]:
    return {
        "season": season,
        "standings_message_id": standings_message_id,
        "teams": {
            team: {"wins": 0, "losses": 0, "pf": 0, "pa": 0, "streak": 0}
            for team in NFL_TEAMS
        }
    }


def load_standings() -> Dict[str, Any]:
    if not STANDINGS_FILE.exists():
        return _fresh_standings_data()

    with open(STANDINGS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # backfill missing keys safely
    if "season" not in data:
        data["season"] = 1
    if "standings_message_id" not in data:
        data["standings_message_id"] = None
    if "teams" not in data:
        data["teams"] = {}

    for team in NFL_TEAMS:
        if team not in data["teams"]:
            data["teams"][team] = {"wins": 0, "losses": 0, "pf": 0, "pa": 0, "streak": 0}
        else:
            data["teams"][team].setdefault("wins", 0)
            data["teams"][team].setdefault("losses", 0)
            data["teams"][team].setdefault("pf", 0)
            data["teams"][team].setdefault("pa", 0)
            data["teams"][team].setdefault("streak", 0)

    return data


def save_standings(data: Dict[str, Any]):
    with open(STANDINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def reset_standings(season: int = 1, standings_message_id=None):
    data = _fresh_standings_data(season=season, standings_message_id=standings_message_id)
    save_standings(data)

# =========================================================
# UPDATE GAME RESULT
# =========================================================

def update_game_result(team1: str, team2: str, score1: int, score2: int):
    data = load_standings()

    if team1 not in data["teams"] or team2 not in data["teams"]:
        raise ValueError("One or both team names are invalid.")

    t1 = data["teams"][team1]
    t2 = data["teams"][team2]

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
    else:
        # if ties are not allowed, you can raise instead
        pass

    save_standings(data)

# =========================================================
# FORMATTING
# =========================================================

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


def format_team_line(rank: int, name: str, wins: int, losses: int, pd: int, streak: int) -> str:
    emoji = TEAM_EMOJIS.get(name, "🏈")
    rank_display = _rank_display(rank)
    streak_display = _streak_display(streak)

    # keeps that compact look from your screenshot
    return f"{rank_display} {emoji} **{name}** `{wins}-{losses}` `({pd:+})` `{streak_display}`"

# =========================================================
# EMBED BUILDER
# =========================================================

def build_standings_embed(data: Dict[str, Any]) -> discord.Embed:
    season = data.get("season", 1)
    active_teams = get_active_teams()

    if active_teams:
        teams = {k: v for k, v in data["teams"].items() if k in active_teams}
    else:
        teams = data["teams"]

    sorted_teams = sorted(
        teams.items(),
        key=lambda x: (
            -(x[1]["wins"] / max(1, (x[1]["wins"] + x[1]["losses"]))),
            -((x[1]["pf"] - x[1]["pa"])),
            -x[1]["wins"]
        )
    )

    embed = discord.Embed(
        title=f"🏆 SFG Season {season} Standings",
        description="🏈 *Official SFG League Standings*\nSorted by Win % → PD → Wins",
        color=discord.Color.blue()
    )

    divisions = []
    chunk_size = 8

    for i in range(0, len(sorted_teams), chunk_size):
        start = i + 1
        end = i +len(sorted_teams[i:i+chunk_size])

        divisions.append(
            (f"📊 Division {(i // chunk_size) + 1} ({start}–{end})",
             sorted_teams[i:i + chunk_size])
        )


    rank = 1

    for division_name, group in divisions:
        lines = []

        for team_name, stats in group:
            if rank == 15:
                lines.append("🔴 **PLAYOFF CUT** ─────────")

            wins = stats["wins"]
            losses = stats["losses"]
            pd = stats["pf"] - stats["pa"]
            streak = stats.get("streak", 0)

            lines.append(format_team_line(rank, team_name, wins, losses, pd, streak))
            rank += 1

        embed.add_field(
            name=division_name,
            value="\n".join(lines) if lines else "No teams",
            inline=False
        )

    embed.set_footer(
        text="Sorted by Win% → Point Differential → Wins • PD = PF - PA"
    )
    return embed

# =========================================================
# POST / UPDATE
# =========================================================

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
                msg = await channel.fetch_message(msg_id)
                await msg.edit(embed=embed)
                print("✅ Standings updated by editing existing message")
                return
            except discord.NotFound:
                print("⚠️ Stored standings message was not found; creating a new one")
            except Exception as e:
                print(f"⚠️ Could not edit standings message: {e}")

        # cleanup old bot standings messages if needed
        me = guild.me or guild.guild.me if hasattr(guild, "guild") else None
        async for m in channel.history(limit=20):
            try:
                if m.author.id == guild.me.id:
                    if m.embeds and "Standings" in (m.embeds[0].title or ""):
                        await m.delete()
            except Exception:
                pass

        msg = await channel.send(embed=embed)
        data["standings_message_id"] = msg.id
        save_standings(data)
        print("🆕 New standings message created and saved")