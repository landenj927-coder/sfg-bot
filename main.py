import os
import re
import unicodedata
import json
import time
import aiohttp
import asyncio
import datetime
from typing import Optional, Tuple, Any, Dict, List
from pathlib import Path

from dotenv import load_dotenv

import discord
from discord.ext import commands
from discord import app_commands

from stats_sheet import (
    append_qb_statline,
    append_wr_statline,
    append_db_statline,
    append_de_statline,
    update_playerstats_top15,
)
from utils.standings import NFL_TEAMS, STANDINGS_LOCK, load_standings, save_standings, post_or_update_standings
from utils.helpers import log_transaction, find_text_channel_fuzzy, normalize_channel_name
from utils.config import GUILD_ID

# ✅ Load .env file
load_dotenv()

# ✅ TOKENS / KEYS
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN env var not set")

BLOXLINK_API_KEY = "3946b012-4c9c-462f-9b1a-ec0cfbab9ede"  # can be "" to disable

# ✅ only block startup if user forgot to replace placeholders
if not DISCORD_TOKEN or DISCORD_TOKEN == "PASTE_YOUR_DISCORD_BOT_TOKEN_HERE":
    raise RuntimeError("You must set DISCORD_TOKEN in .env")

if not BLOXLINK_API_KEY or BLOXLINK_API_KEY == "PASTE_YOUR_BLOXLINK_API_KEY_HERE":
    print("⚠ WARNING: Missing BLOXLINK_API_KEY. Verification matching will fail.")
    BLOXLINK_API_KEY = ""

# =========================
# INTENTS
# =========================
intents = discord.Intents.default()
intents.members = True
intents.guilds = True

# =========================
# CONFIG
# =========================

GUILD_OBJ = discord.Object(id=GUILD_ID)

ACTIVE_GAMEREPORTS: set[int] = set()

ROBLOX_DISCORD_CACHE_FILE = "roblox_discord_cache.json"
APPLICATIONS_CHANNEL_ID = 1488379006733779046
TRANSACTIONS_CHANNEL = "transactions"
STREAMER_ROLE_NAME = "Streamer"
STREAMS_CHANNEL_NAME = "streams"  # the channel name you want (font/case-insensitive)
GAMETIMES_CHANNEL_NAME = "gametimes"  # target channel name (font/case-insensitive)
URL_REGEX = re.compile(r"^https?://", re.IGNORECASE)
ROSTER_LIMIT = 14

LOGS_CHANNEL_ID = 1448938805083246602
SCORES_CHANNEL_ID = 1448922961783558154

SFG_LOGO_URL = "https://media.discordapp.net/attachments/1448865755650330734/1448890098299965511/39515399-0233-4dfd-b76d-06b8a850fb3e.png?format=webp&quality=lossless&width=350&height=350"

NFL_TEAMS = [
    "Arizona","Atlanta","Baltimore","Buffalo","Carolina","Chicago","Cincinnati","Cleveland",
    "Dallas","Denver","Detroit","GreenBay","Houston","Indianapolis","Jacksonville","Chiefs",
    "LasVegas","Rams","Chargers","Miami","Minnesota","Patriots","Saints","Giants","Jets",
    "Philadelphia","Pittsburgh","49ers","Seattle","Tampa","Tennessee","Washington"
]

TEAM_COLORS = {
    "Arizona":0x97233F,"Atlanta":0xA71930,"Baltimore":0x241773,"Buffalo":0x00338D,
    "Carolina":0x0085CA,"Chicago":0x0B162A,"Cincinnati":0xFB4F14,"Cleveland":0x311D00,
    "Dallas":0x002244,"Denver":0xFB4F14,"Detroit":0x0076B6,"GreenBay":0x203731,
    "Houston":0x03202F,"Indianapolis":0x002C5F,"Jacksonville":0x006778,"Chiefs":0xE31837,
    "LasVegas":0x000000,"Rams":0x003594,"Chargers":0x0080C6,"Miami":0x008E97,
    "Minnesota":0x4F2683,"Patriots":0x002244,"Saints":0xD3BC8D,"Giants":0x0B2265,
    "Jets":0x125740,"Philadelphia":0x004C54,"Pittsburgh":0xFFB612,"49ers":0xAA0000,
    "Seattle":0x002244,"Tampa":0xFF0000,"Tennessee":0x4B92DB,"Washington":0x5A1414
}

TEAM_THUMBNAILS = {
    "Arizona":      "https://cdn.discordapp.com/emojis/1448881457106915509.webp?size=96&quality=lossless",
    "Atlanta":      "https://cdn.discordapp.com/emojis/1448881506905751653.webp?size=96&quality=lossless",
    "Baltimore":    "https://cdn.discordapp.com/emojis/1448881443865362562.webp?size=96&quality=lossless",
    "Buffalo":      "https://cdn.discordapp.com/emojis/1448881454640533504.webp?size=96&quality=lossless",
    "Carolina":     "https://cdn.discordapp.com/emojis/1448881511750438923.webp?size=96&quality=lossless",
    "Chicago":      "https://cdn.discordapp.com/emojis/1448881495694381218.webp?size=96&quality=lossless",
    "Cincinnati":   "https://cdn.discordapp.com/emojis/1448881436592570369.webp?size=96&quality=lossless",
    "Cleveland":    "https://cdn.discordapp.com/emojis/1448881438593122346.webp?size=96&quality=lossless",
    "Dallas":       "https://cdn.discordapp.com/emojis/1448881516422758565.webp?size=96&quality=lossless",
    "Denver":       "https://cdn.discordapp.com/emojis/1448881475821768785.webp?size=96&quality=lossless",
    "Detroit":      "https://cdn.discordapp.com/emojis/1448881504754204817.webp?size=96&quality=lossless",
    "GreenBay":     "https://cdn.discordapp.com/emojis/1448881501574926368.webp?size=96&quality=lossless",
    "Houston":      "https://cdn.discordapp.com/emojis/1448881477294100617.webp?size=96&quality=lossless",
    "Indianapolis": "https://cdn.discordapp.com/emojis/1448881486471364679.webp?size=96&quality=lossless",
    "Jacksonville": "https://cdn.discordapp.com/emojis/1448881484021895170.webp?size=96&quality=lossless",
    "Chiefs":       "https://cdn.discordapp.com/emojis/1448881473536004106.webp?size=96&quality=lossless",
    "LasVegas":     "https://cdn.discordapp.com/emojis/1448881471220617402.webp?size=96&quality=lossless",
    "Rams":         "https://cdn.discordapp.com/emojis/1448881461057814658.webp?size=96&quality=lossless",
    "Chargers":     "https://cdn.discordapp.com/emojis/1448881467492012032.webp?size=96&quality=lossless",
    "Miami":        "https://cdn.discordapp.com/emojis/1448881448982679678.webp?size=96&quality=lossless",
    "Minnesota":    "https://cdn.discordapp.com/emojis/1448881499213664498.webp?size=96&quality=lossless",
    "Patriots":     "https://cdn.discordapp.com/emojis/1448881447275335812.webp?size=96&quality=lossless",
    "Saints":       "https://cdn.discordapp.com/emojis/1448881509577658379.webp?size=96&quality=lossless",
    "Giants":       "https://cdn.discordapp.com/emojis/1448881491022053492.webp?size=96&quality=lossless",
    "Jets":         "https://cdn.discordapp.com/emojis/1448881451989995661.webp?size=96&quality=lossless",
    "Philadelphia": "https://cdn.discordapp.com/emojis/1448881488912187513.webp?size=96&quality=lossless",
    "Pittsburgh":   "https://cdn.discordapp.com/emojis/1448881441516687511.webp?size=96&quality=lossless",
    "49ers":        "https://cdn.discordapp.com/emojis/1448881463100702791.webp?size=96&quality=lossless",
    "Seattle":      "https://cdn.discordapp.com/emojis/1448881464950128843.webp?size=96&quality=lossless",
    "Tampa":        "https://cdn.discordapp.com/emojis/1448881513985736776.webp?size=96&quality=lossless",
    "Tennessee":    "https://cdn.discordapp.com/emojis/1448881481064644679.webp?size=96&quality=lossless",
    "Washington":   "https://cdn.discordapp.com/emojis/1448881493509144760.webp?size=96&quality=lossless"
}

# =========================
# BLOXLINK (CACHED) + ONE SHARED SESSION
# =========================
ROBLOX_BY_DISCORD_CACHE: dict[int, Tuple[int, float]] = {}
DISCORD_BY_ROBLOX_CACHE: dict[int, Tuple[int, float]] = {}
CACHE_TTL_SECONDS = 900  # 15 minutes

HTTP_SESSION: Optional[aiohttp.ClientSession] = None

async def get_http_session() -> aiohttp.ClientSession:
    global HTTP_SESSION
    if HTTP_SESSION is None or HTTP_SESSION.closed:
        timeout = aiohttp.ClientTimeout(total=15)
        HTTP_SESSION = aiohttp.ClientSession(timeout=timeout)
    return HTTP_SESSION

async def bloxlink_discord_to_roblox_id(guild_id: int, discord_id: int) -> Optional[int]:
    if not BLOXLINK_API_KEY:
        return None

    url = f"https://api.blox.link/v4/public/guilds/{guild_id}/discord-to-roblox/{discord_id}"
    session = await get_http_session()
    async with session.get(url, headers={"Authorization": BLOXLINK_API_KEY}) as resp:
        if resp.status != 200:
            return None
        data = await resp.json()

    for key in ("robloxID", "robloxId", "roblox_id"):
        if key in data and str(data[key]).isdigit():
            return int(data[key])

    user = data.get("user") or {}
    for key in ("robloxID", "robloxId", "id"):
        if key in user and str(user[key]).isdigit():
            return int(user[key])

    return None

async def bloxlink_roblox_to_discord_id(guild_id: int, roblox_id: int) -> Optional[int]:
    if not BLOXLINK_API_KEY:
        return None

    url = f"https://api.blox.link/v4/public/guilds/{guild_id}/roblox-to-discord/{roblox_id}"
    session = await get_http_session()
    async with session.get(url, headers={"Authorization": BLOXLINK_API_KEY}) as resp:
        if resp.status != 200:
            return None
        data = await resp.json()

    for key in ("discordID", "discordId", "discord_id"):
        if key in data and str(data[key]).isdigit():
            return int(data[key])

    user = data.get("user") or {}
    for key in ("discordID", "discordId", "id"):
        if key in user and str(user[key]).isdigit():
            return int(user[key])

    for key in ("discord", "discord_id"):
        if key in data and str(data[key]).isdigit():
            return int(data[key])

    return None

async def get_cached_roblox_id(guild_id: int, discord_id: int) -> Optional[int]:
    now = time.time()
    cached = ROBLOX_BY_DISCORD_CACHE.get(discord_id)
    if cached and cached[1] > now:
        return cached[0]
    rid = await bloxlink_discord_to_roblox_id(guild_id, discord_id)
    if rid:
        ROBLOX_BY_DISCORD_CACHE[discord_id] = (rid, now + CACHE_TTL_SECONDS)
    return rid

async def get_cached_discord_id(guild_id: int, roblox_id: int) -> Optional[int]:
    now = time.time()
    cached = DISCORD_BY_ROBLOX_CACHE.get(roblox_id)
    if cached and cached[1] > now:
        return cached[0]
    did = await bloxlink_roblox_to_discord_id(guild_id, roblox_id)
    if did:
        DISCORD_BY_ROBLOX_CACHE[roblox_id] = (did, now + CACHE_TTL_SECONDS)
    return did

# =========================
# BOT CLASS (GUILD SYNC)
# =========================

class SFGBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents
        )

    async def setup_hook(self):
        print("🔄 Loading cogs...")

        # =========================
        # LOAD COGS
        # =========================

        try:
            await self.load_extension("cogs.offer")
            print("✅ Loaded cog: offer.py")
        except Exception as e:
            print(f"❌ Failed to load offer.py: {e}")

        try:
            await self.load_extension("cogs.team")
            print("✅ Loaded cog: team.py")
        except Exception as e:
            import traceback
            print(f"❌ Failed to load team.py: {e}")
            traceback.print_exc()

        try:
            await self.load_extension("cogs.rulebook")
            print("✅ Loaded cog: rulebook.py")
        except Exception as e:
            print(f"❌ Failed to load rulebook.py: {e}")

        try:
            await self.load_extension("cogs.standings")
            print("✅ Loaded cog: standings.py")
        except Exception as e:
            import traceback
            print(f"❌ Failed to load standings.py: {e}")
            traceback.print_exc()

        try:
            await self.load_extension("cogs.members")
            print("✅ Loaded cog: members.py")
        except Exception as e:
            import traceback
            print(f"❌ Failed to load members.py: {e}")
            traceback.print_exc()

        try:
            await self.load_extension("cogs.lfp")
            print("✅ Loaded cog: lfp.py")
        except Exception as e:
            import traceback
            print(f"❌ Failed to load lfp.py: {e}")
            traceback.print_exc()

        try:
            await self.load_extension("cogs.gamereport")
            print("✅ Loaded cog: gamereport.py")
        except Exception as e:
            import traceback
            print(f"❌ Failed to load gamereport.py: {e}")
            traceback.print_exc()

        try:
            await self.load_extension("cogs.panel")
            print("✅ Loaded cog: panel.py")
        except Exception as e:
            import traceback
            print(f"❌ Failed to load panel.py: {e}")
            traceback.print_exc()

        try:
            await self.load_extension("cogs.roster")
            print("✅ Loaded cog: roster.py")
        except Exception as e:
            import traceback
            print(f"❌ Failed to load roster.py: {e}")
            traceback.print_exc()
        
        try:
            await self.load_extension("cogs.applications")
            print("✅ Loaded cog: applications.py")
        except Exception as e:
            import traceback
            print(f"❌ Failed to load applications.py: {e}")
            traceback.print_exc()

        try:
            await self.load_extension("cogs.disband")
            print("✅ Loaded cog: disband.py")
        except Exception as e:
            import traceback
            print(f"❌ Failed to load disband.py: {e}")
            traceback.print_exc()

        try:
            await self.load_extension("cogs.appoint")
            print("✅ Loaded cog: appoint.py")
        except Exception as e:
            import traceback
            print(f"❌ Failed to load appoint.py: {e}")
            traceback.print_exc()

        try:
            await self.load_extension("cogs.folist")
            print("✅ Loaded cog: folist.py")
        except Exception as e:
            import traceback
            print(f"❌ Failed to load folist.py: {e}")
            traceback.print_exc()

# =========================
# CREATE BOT INSTANCE
# =========================

bot = SFGBot()


# =========================
# ON READY (SYNC COMMANDS)
# =========================

@bot.event
async def on_ready():
    print("ON_READY_TRIGGERED")
    print(f"🚀 Logged in as {bot.user}")

    guild = discord.Object(id=GUILD_ID)

    synced = await bot.tree.sync(guild=guild)

    print(f"🏠 Guild Synced: {len(synced)} commands")

# =========================================================
# TEAM KEY NORMALIZATION (emoji/case/font insensitive)
# =========================================================

_INVISIBLE = dict.fromkeys([0x200D, 0xFE0F, 0xFE0E], None)

def normalize_team_key(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s)
    s = s.translate(_INVISIBLE)
    # keep letters/numbers/spaces only (drops emojis/symbols)
    s = "".join(ch if (ch.isalnum() or ch.isspace()) else " " for ch in s)
    s = re.sub(r"\s+", " ", s).strip().casefold()
    return s

# Build canonical key mapping ONCE from your NFL_TEAMS list
TEAM_KEY_TO_CANONICAL: dict[str, str] = {normalize_team_key(t): t for t in NFL_TEAMS}

def canonical_team_name(team_any: str) -> str:
    """
    Takes any team string (emoji/fancy/case/etc) and returns the canonical team name
    used inside standings.json (one of NFL_TEAMS), if possible.
    If unknown, returns original string (but normalized-ish).
    """
    key = normalize_team_key(team_any)
    return TEAM_KEY_TO_CANONICAL.get(key, team_any.strip())

def _fresh_standings() -> Dict[str, Any]:
    return {
        "teams": {t: {"wins": 0, "losses": 0, "pf": 0, "pa": 0} for t in NFL_TEAMS},
        "standings_message_id": None,
        "season": 1,
    }

def ensure_team(data: Dict[str, Any], team: str) -> None:
    if "teams" not in data:
        data["teams"] = {}
    team = canonical_team_name(team)
    if team not in data["teams"]:
        data["teams"][team] = {"wins": 0, "losses": 0, "pf": 0, "pa": 0}

def update_game_result(data: Dict[str, Any], team_a: str, score_a: int, team_b: str, score_b: int) -> None:
    team_a = canonical_team_name(team_a)
    team_b = canonical_team_name(team_b)

    ensure_team(data, team_a)
    ensure_team(data, team_b)

    score_a = int(score_a)
    score_b = int(score_b)

    data["teams"][team_a]["pf"] += score_a
    data["teams"][team_a]["pa"] += score_b
    data["teams"][team_b]["pf"] += score_b
    data["teams"][team_b]["pa"] += score_a

    if score_a > score_b:
        data["teams"][team_a]["wins"] += 1
        data["teams"][team_b]["losses"] += 1
    elif score_b > score_a:
        data["teams"][team_b]["wins"] += 1
        data["teams"][team_a]["losses"] += 1
    else:
        # ties: if you want ties tracked, add "ties" fields
        pass

def _sorted_rows(data: Dict[str, Any]):
    rows = []
    for team, s in data["teams"].items():
        w = int(s.get("wins", 0))
        l = int(s.get("losses", 0))
        games = w + l
        winpct = (w / games) if games > 0 else 0.0
        pd = int(s.get("pf", 0)) - int(s.get("pa", 0))
        rows.append((team, s, winpct, pd))

    # best record first, then best PD, then wins
    rows.sort(key=lambda x: (x[2], x[3], int(x[1].get("wins", 0))), reverse=True)
    return rows

def _record_line(rank: int, guild: discord.Guild, team: str, s: Dict[str, Any]) -> str:
    w = int(s.get("wins", 0))
    l = int(s.get("losses", 0))
    pf = int(s.get("pf", 0))
    pa = int(s.get("pa", 0))
    pd = pf - pa

    emoji = get_team_emoji(guild, team) if guild else ""
    prefix = f"{emoji} " if emoji else ""

    return f"**{rank}.) {prefix}{team}** — **{w}-{l}** | **PD:** {pd:+d}"

def build_standings_embed(guild: discord.Guild, data: Dict[str, Any]) -> discord.Embed:
    rows = _sorted_rows(data)

    emb = discord.Embed(
        title=f"SFG Season {data.get('season', 1)} Standings",
        description="Sorted by **Record**, then **Point Differential (PD)**.",
        color=discord.Color.blue(),
    )
    if SFG_LOGO_URL:
        emb.set_thumbnail(url=SFG_LOGO_URL)

    slices = [
        ("Division 1 — Seeds 1-8",   0,  8,  1),
        ("Division 2 — Seeds 9-16",  8, 16,  9),
        ("Division 3 — Seeds 17-24", 16, 24, 17),
        ("Division 4 — Seeds 25-32", 24, 32, 25),
    ]

    for name, a, b, start_rank in slices:
        seg = rows[a:b]
        lines = [
            _record_line(rank, guild, team, s)
            for rank, (team, s, _, _) in enumerate(seg, start=start_rank)
        ]
        emb.add_field(
            name=name,
            value="\n".join(lines) if lines else "*No teams.*",
            inline=False,
        )

    emb.set_footer(text="PD = Points For - Points Against")
    return emb

# =========================================================
# TEAM DETECTION (best-effort)
# =========================================================
def _flatten_strings(obj: Any) -> List[str]:
    out: List[str] = []
    if isinstance(obj, dict):
        for v in obj.values():
            out.extend(_flatten_strings(v))
    elif isinstance(obj, list):
        for v in obj:
            out.extend(_flatten_strings(v))
    elif isinstance(obj, str):
        out.append(obj)
    return out

def _detect_teams_from_report(report: Any) -> Tuple[Optional[str], Optional[str]]:
    """
    Searches the JSON payload for NFL team names and returns the top 2 matches.
    Works if the export contains team names anywhere as strings.
    """
    strings = _flatten_strings(report)
    if not strings:
        return None, None

    counts: Dict[str, int] = {t: 0 for t in NFL_TEAMS}
    for s in strings:
        s_low = s.lower()
        for t in NFL_TEAMS:
            if t.lower() in s_low:
                counts[t] += 1

    hits = [(t, c) for t, c in counts.items() if c > 0]
    hits.sort(key=lambda x: x[1], reverse=True)

    if len(hits) >= 2:
        return hits[0][0], hits[1][0]
    if len(hits) == 1:
        return hits[0][0], None
    return None, None

def _detect_user_team_from_roles(guild: discord.Guild, member: discord.Member) -> Optional[str]:
    """
    Finds the user's team role even if the role name has emojis/fancy fonts/case differences.
    Returns the canonical team name from NFL_TEAMS.
    """
    role_keys = {normalize_team_key(r.name): r.name for r in member.roles}

    for t in NFL_TEAMS:
        if normalize_team_key(t) in role_keys:
            return t  # canonical
    return None


# =========================
# HELPERS
# =========================
def load_roblox_discord_cache():
    if not os.path.exists(ROBLOX_DISCORD_CACHE_FILE):
        return {
            "discord_to_roblox": {},
            "roblox_to_discord": {}
        }

    try:
        with open(ROBLOX_DISCORD_CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        return {
            "discord_to_roblox": data.get("discord_to_roblox", {}),
            "roblox_to_discord": data.get("roblox_to_discord", {})
        }
    except Exception:
        return {
            "discord_to_roblox": {},
            "roblox_to_discord": {}
        }


def save_roblox_discord_cache(cache):
    with open(ROBLOX_DISCORD_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)

roblox_discord_cache = load_roblox_discord_cache()

def update_roblox_discord_cache(discord_member, roblox_id, roblox_username, roblox_display_name=None):
    discord_id = str(discord_member.id)
    roblox_id_str = str(roblox_id)

    roblox_discord_cache["discord_to_roblox"][discord_id] = {
        "discord_id": discord_member.id,
        "discord_name": discord_member.name,
        "discord_display_name": getattr(discord_member, "display_name", discord_member.name),
        "roblox_id": roblox_id,
        "roblox_username": roblox_username,
        "roblox_display_name": roblox_display_name or roblox_username
    }

    roblox_discord_cache["roblox_to_discord"][roblox_id_str] = discord_member.id
    save_roblox_discord_cache(roblox_discord_cache)

def resolve_discord_member_from_roblox(guild, roblox_id=None, roblox_username=None, roblox_display_name=None):
    if guild is None:
        return None

    # 1. Roblox ID cache lookup
    if roblox_id is not None:
        cached_discord_id = roblox_discord_cache["roblox_to_discord"].get(str(roblox_id))
        if cached_discord_id:
            member = guild.get_member(int(cached_discord_id))
            if member:
                return member

    # 2. Cached username/display name lookup
    for discord_id, entry in roblox_discord_cache["discord_to_roblox"].items():
        cached_username = str(entry.get("roblox_username", "")).lower()
        cached_display = str(entry.get("roblox_display_name", "")).lower()

        if roblox_username and cached_username == roblox_username.lower():
            member = guild.get_member(int(discord_id))
            if member:
                return member

        if roblox_display_name and cached_display == roblox_display_name.lower():
            member = guild.get_member(int(discord_id))
            if member:
                return member

    # 3. Live Discord fallback
    search_values = set()
    if roblox_username:
        search_values.add(roblox_username.lower())
    if roblox_display_name:
        search_values.add(roblox_display_name.lower())

    for member in guild.members:
        names_to_check = {
            member.name.lower(),
            member.display_name.lower()
        }

        if search_values & names_to_check:
            return member

    return None


async def nfl_team_autocomplete(interaction: discord.Interaction, current: str):
    current = (current or "").lower().strip()
    matches = [t for t in NFL_TEAMS if current in t.lower()]
    # Discord allows max 25 suggestions returned
    return [app_commands.Choice(name=t, value=t) for t in matches[:25]]

async def nfl_team_autocomplete(interaction: discord.Interaction, current: str):
    current = (current or "").lower().strip()
    matches = [t for t in NFL_TEAMS if current in t.lower()]
    return [app_commands.Choice(name=t, value=t) for t in matches[:25]]

APPLICATION_BRANCHES = {
    "Justice": {
        "role": "Justice",
        "options": [
            "Investigation Staff",
            "Referee Staff",
        ],
    },
    "Community": {
        "role": "Community",
        "options": [
            "Media Analyst",
            "Media Owner",
            "Streamer",
            "Host",
        ],
    },
    "Franchise": {
        "role": "Franchise",
        "options": [
            "Franchise Owner",
        ],
    },
    "Awards Committee": {
        "role": "Awards Committee",
        "options": [
            "Stat Analyst",
        ],
    },
}

def get_member_team_role(member: discord.Member) -> Optional[discord.Role]:
    return next((r for r in member.roles if r.name in NFL_TEAMS), None)

def get_team_role(guild: discord.Guild, team_name: str) -> discord.Role | None:
    if not guild:
        return None
    return discord.utils.get(guild.roles, name=team_name)

def get_team_emoji(guild: discord.Guild, team_name: str) -> str:
    """
    Uses TEAM_EMOJI_NAME mapping, e.g.:
    "Detroit" -> "DetroitLions"
    """
    if not guild:
        return ""

    emoji_name = TEAM_EMOJI_NAME.get(team_name)
    if not emoji_name:
        return ""

    emoji = discord.utils.get(guild.emojis, name=emoji_name)
    return str(emoji) if emoji else ""

def get_member_team_name(member: discord.Member) -> str:
    r = get_member_team_role(member)
    return r.name if r else ""

def has_any_management_role(guild: discord.Guild, member: discord.Member) -> bool:
    for name in ("Franchise Owner", "Team President", "General Manager"):
        role = discord.utils.get(guild.roles, name=name)
        if role and role in member.roles:
            return True
    return False


def normalize_team_name(name: str) -> str:
    return (
        name.replace(" ", "")
            .replace(".", "")
            .replace("-", "")
            .lower()
    )

TEAM_EMOJI_NAME = {
    "Arizona": "ArizonaCardinals",
    "Atlanta": "AtlantaFalcons",
    "Baltimore": "BaltimoreRavens",
    "Buffalo": "BuffaloBills",
    "Carolina": "CarolinaPanthers",
    "Chicago": "ChicagoBears",
    "Cincinnati": "CincinnatiBengals",
    "Cleveland": "ClevelandBrowns",
    "Dallas": "DallasCowboys",
    "Denver": "DenverBroncos",
    "Detroit": "DetroitLions",
    "GreenBay": "GreenBayPackers",
    "Houston": "HoustonTexans",
    "Indianapolis": "IndianapolisColts",
    "Jacksonville": "JacksonvilleJaguars",
    "Chiefs": "KansasCityChiefs",
    "LasVegas": "LasVegasRaiders",
    "Rams": "LosAngelesRams",
    "Chargers": "LosAngelesChargers",
    "Miami": "MiamiDolphins",
    "Minnesota": "MinnesotaVikings",
    "Patriots": "NewEnglandPatriots",
    "Saints": "NewOrleansSaints",
    "Giants": "NewYorkGiants",
    "Jets": "NewYorkJets",
    "Philadelphia": "PhiladelphiaEagles",
    "Pittsburgh": "PittsburghSteelers",
    "49ers": "SanFrancisco49ers",
    "Seattle": "SeattleSeahawks",
    "Tampa": "TampaBayBucaneers",
    "Tennessee": "TennesseeTitans",
    "Washington": "WashingtonFootballTeam",
}

def get_team_emoji(guild: discord.Guild, team_name: str) -> str:
    if not guild:
        return ""

    lookup = TEAM_EMOJI_NAME.get(team_name, team_name)
    normalized_lookup = normalize_team_name(lookup)

    # DEBUG: print a few emoji names the bot can see
    print("EMOJIS BOT SEES (first 25):", [e.name for e in guild.emojis[:25]])
    print("LOOKING FOR:", lookup, "=>", normalized_lookup)

    for emoji in guild.emojis:
        if normalize_team_name(emoji.name) == normalized_lookup:
            print("MATCHED EMOJI:", emoji.name)
            return str(emoji)

    print("NO EMOJI MATCH FOR:", team_name)
    return ""

def can_submit_gamereport(guild: discord.Guild, member: discord.Member) -> bool:
    for name in ("Franchise Owner", "Team President"):
        role = discord.utils.get(guild.roles, name=name)
        if role and role in member.roles:
            return True
    return False

def resolve_text_channel_by_id(guild: discord.Guild, channel_id: int) -> Optional[discord.TextChannel]:
    ch = guild.get_channel(channel_id)
    return ch if isinstance(ch, discord.TextChannel) else None

async def send_logs(guild: discord.Guild, message: str):
    ch = resolve_text_channel_by_id(guild, LOGS_CHANNEL_ID)
    if ch:
        await ch.send(message)

def _norm_name(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[^a-z0-9_\.]", "", s)
    return s

def build_member_name_index(guild: discord.Guild) -> dict[str, int]:
    idx: dict[str, int] = {}
    for m in guild.members:
        idx[_norm_name(m.display_name)] = m.id
        idx[_norm_name(m.name)] = m.id
        gn = getattr(m, "global_name", None)
        if gn:
            idx[_norm_name(str(gn))] = m.id
    return idx

def get_team_emoji_obj(guild: discord.Guild, team_name: str) -> Optional[discord.Emoji]:
    """
    Returns the discord.Emoji object for the team so we can add it as a reaction.
    Uses TEAM_EMOJI_NAME + normalize_team_name() like your get_team_emoji().
    """
    if not guild:
        return None

    lookup = TEAM_EMOJI_NAME.get(team_name, team_name)
    normalized_lookup = normalize_team_name(lookup)

    for emoji in guild.emojis:
        if normalize_team_name(emoji.name) == normalized_lookup:
            return emoji

    return None

def find_streams_channel(guild: discord.Guild, target_name: str) -> Optional[discord.TextChannel]:
    target_norm = normalize_channel_name(target_name)
    for ch in guild.text_channels:
        if normalize_channel_name(ch.name) == target_norm:
            return ch
    return None

def has_role_name(member: discord.Member, role_name: str) -> bool:
    return any(r.name == role_name for r in member.roles)

from datetime import datetime, timedelta, timezone

BOT_TZ = timezone(timedelta(hours=-5))  # your default (-0500)

def _parse_when_to_dt(when: str) -> datetime:
    """
    Accepts:
      - "YYYY-MM-DD HH:MM" (24h)   ex: 2025-12-27 22:00
      - "YYYY-MM-DD HH:MM AM/PM"  ex: 2025-12-27 10:00 PM
      - "HH:MM AM/PM"             ex: 10:00 PM (assumes next occurrence in BOT_TZ)
    """
    s = (when or "").strip()

    # with date
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %I:%M %p", "%Y-%m-%d %I:%M%p"):
        try:
            dt = datetime.strptime(s, fmt).replace(tzinfo=BOT_TZ)
            return dt
        except ValueError:
            pass

    # time only (assume next occurrence)
    for fmt in ("%I:%M %p", "%I:%M%p"):
        try:
            t = datetime.strptime(s, fmt).time()
            now = datetime.now(BOT_TZ)
            dt = datetime(now.year, now.month, now.day, t.hour, t.minute, tzinfo=BOT_TZ)
            if dt <= now:
                dt += timedelta(days=1)
            return dt
        except ValueError:
            pass

    raise ValueError("Invalid time format. Use `10:00 PM` or `2025-12-27 22:00`.")


# Put this near your other constants/helpers (once)
GAMETIME_TIME_CHOICES = [
    app_commands.Choice(name="7:00 PM", value="7:00 PM"),
    app_commands.Choice(name="7:15 PM", value="7:15 PM"),
    app_commands.Choice(name="7:30 PM", value="7:30 PM"),
    app_commands.Choice(name="7:45 PM", value="7:45 PM"),
    app_commands.Choice(name="8:00 PM", value="8:00 PM"),
    app_commands.Choice(name="8:15 PM", value="8:15 PM"),
    app_commands.Choice(name="8:30 PM", value="8:30 PM"),
    app_commands.Choice(name="8:45 PM", value="8:45 PM"),
    app_commands.Choice(name="9:00 PM", value="9:00 PM"),
    app_commands.Choice(name="9:15 PM", value="9:15 PM"),
    app_commands.Choice(name="9:30 PM", value="9:30 PM"),
    app_commands.Choice(name="9:45 PM", value="9:45 PM"),
    app_commands.Choice(name="10:00 PM", value="10:00 PM"),
    app_commands.Choice(name="10:15 PM", value="10:15 PM"),
    app_commands.Choice(name="10:30 PM", value="10:30 PM"),
    app_commands.Choice(name="10:45 PM", value="10:45 PM"),
    app_commands.Choice(name="11:00 PM", value="11:00 PM"),
]

STREAMER_ROLE_NAME = "Streamer"  # match your server role name exactly

def _has_role(member: discord.Member, role_name: str) -> bool:
    return any(r.name == role_name for r in member.roles)

def _set_streamer_field(embed: discord.Embed, streamer_mention: str) -> discord.Embed:
    """
    Adds/updates a 'Streamer:' section on the embed.
    """
    # Look for an existing field that contains "Streamer:"
    for i, f in enumerate(embed.fields):
        if "Streamer:" in (f.value or ""):
            embed.set_field_at(i, name=f.name, value=f"**Streamer:** {streamer_mention}", inline=False)
            return embed

    # Otherwise add a new section at the bottom
    embed.add_field(name="\u200b", value=f"**Streamer:** {streamer_mention}", inline=False)
    return embed


class StreamClaimView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # stays until restart (non-persistent, but no auto-timeout)
        self.claimed_by: Optional[int] = None

    @discord.ui.button(label="Claim Stream", style=discord.ButtonStyle.primary, emoji="🎥")
    async def claim_stream(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("Server-only.", ephemeral=True)

        # Must have Streamer role
        if not _has_role(interaction.user, STREAMER_ROLE_NAME):
            return await interaction.response.send_message(
                f"❌ You need the **{STREAMER_ROLE_NAME}** role to claim streams.",
                ephemeral=True
            )

        # Already claimed
        if self.claimed_by is not None:
            return await interaction.response.send_message("❌ This game is already claimed.", ephemeral=True)

        self.claimed_by = interaction.user.id

        # Disable button after claim
        button.disabled = True
        button.label = "Claimed"

        # Edit the original message embed to add Streamer line
        msg = interaction.message
        if not msg or not msg.embeds:
            return await interaction.response.send_message("❌ Couldn’t edit the embed.", ephemeral=True)

        embed = msg.embeds[0]
        embed = _set_streamer_field(embed, interaction.user.mention)

        await interaction.response.edit_message(embed=embed, view=self)

# =========================
# STREAM COOLDOWN (add once in helpers)
# =========================
STREAM_COOLDOWN_SECONDS = 24 * 60 * 60
stream_cooldowns: dict[int, float] = {}  # key = discord user id, value = last-used unix time

# =========================
# JOIN / LEAVE MESSAGES (Members channel)
# =========================

MEMBERS_CHANNEL_NAME = "members"  # channel name in your server

def _find_text_channel_by_name(guild: discord.Guild, name: str) -> discord.TextChannel | None:
    # Uses your normalize_channel_name if you already have it; otherwise simple match.
    try:
        target = normalize_channel_name(name)
        for ch in guild.text_channels:
            if normalize_channel_name(ch.name) == target:
                return ch
    except NameError:
        for ch in guild.text_channels:
            if ch.name.lower() == name.lower():
                return ch
    return None

@bot.event
async def on_member_join(member: discord.Member):
    guild = member.guild
    ch = _find_text_channel_by_name(guild, MEMBERS_CHANNEL_NAME)
    if not ch:
        return

    # member_count is updated on join/leave
    count = guild.member_count or len(guild.members)

    msg = (
        f"Welcome to Storcity's Football Gridiron {member.mention}. "
        f"We now have **{count}** in the community."
    )

    try:
        await ch.send(msg)
    except discord.Forbidden:
        pass

@bot.event
async def on_member_remove(member: discord.Member):
    guild = member.guild
    ch = _find_text_channel_by_name(guild, MEMBERS_CHANNEL_NAME)
    if not ch:
        return

    count = guild.member_count or len(guild.members)

    msg = (
        f"({member.display_name}) has left Storcity's Football Gridiron. "
        f"We now have **{count}** in the community."
    )

    try:
        await ch.send(msg)
    except discord.Forbidden:
        pass

# =========================
# Applications (FINAL)
# =========================

INVESTIGATION_QUESTIONS = [
    "1.) Are you able to determine when a player is injecting?",
    "2.) Have you ever done something like this position?",
    "3.) What would you do If you aren't sure if a player is cheating, but you're the only Justice staff online? You are also being pushed for an answer by both teams.",
]

REFEREE_QUESTIONS = [
    "1.) Have you read and understood the game rules?",
    "2.) Are you able to make an unbiased honest call in a stressful situation?",
    "3.) Have you been a Ref in another league before?",
]

MEDIA_ANALYST_QUESTIONS = [
    "1.) Do you understand you have to follow the media channels guidelines? (No bringing in irrelevant posts or segments that dont fit the media)",
    "2.) Provide a small example segment of your choice.",
    "3.) Have you posted segments in a league before?",
]

MEDIA_OWNER_QUESTIONS = [
    "1.) What kind of media are you looking to own? (Types of segments, Who will be helping you, How often you will post.)",
    "2.) What will the media be named?",
    "3.) Do you have any special requests for the media?",
]

STREAMER_QUESTIONS = [
    "1.) Have you streamed before? If yes provide a link to your channel.",
    "2.) Do you have vods turned on? (If not turn them on this is a requirement)",
    "3.) How active will you be able to be on a scale of 1-10?",
]

HOST_QUESTIONS = [
    "1.) Are you a starting qb within the league? (if So provide what team you start for.)",
    "2.) Do you understand that all normal rules still apply in pickups?",
    "3.) Are you able to follow the cooldown for posting?",
    "4.) Why do you believe you should have captain?",
]

FRANCHISE_OWNER_QUESTIONS = [
    "1.) Have you ever owned a team in a league before? (if so provide league names)",
    "2.) Do you have a team of players ready to play for you? (Either name some or provide a team chat link)",
    "3.) Have you read and understand all of the rules in the rulebook?",
    "4.) Is there any team you wish for in particular?",
]

STAT_ANALYST_QUESTIONS = [
    "1.) Are you able to be completly unbiased when called upon?",
    "2.) Do you understand the values of stats and impact?",
    "3.) Have you any experience with this sort of thing?",
]

RESULTS_CHANNEL_ID = 1450267610821431458      # where submitted apps get posted
APPLICATIONS_CHANNEL_ID = 1488379006733779046
APPLICATION_PANEL_TITLE = "SFG Various Applications"


# =========================
# EMBED HELPERS
# =========================

def _make_app_embed(title: str, description: str) -> discord.Embed:
    e = discord.Embed(
        title=title,
        description=description,
        color=0x3498DB,
        timestamp=datetime.utcnow()
    )
    e.set_thumbnail(url=SFG_LOGO_URL)
    e.set_footer(text="SFG Bot")
    return e


def _make_results_embed(app_title: str, applicant: discord.User, questions: list[str], answers: list[str]) -> discord.Embed:
    e = discord.Embed(
        title=f"New Application: {app_title}",
        color=0x3498DB,
        timestamp=datetime.utcnow()
    )
    e.set_thumbnail(url=SFG_LOGO_URL)
    e.add_field(name="Applicant", value=f"{applicant.mention} (`{applicant.id}`)", inline=False)

    for i, q in enumerate(questions):
        ans = answers[i] if i < len(answers) else "N/A"
        e.add_field(name=q, value=ans[:1024], inline=False)

    e.set_footer(text="SFG Bot")
    return e


# =========================================================
# GENERIC APPLICATION FLOW (used for ALL roles)
# =========================================================

class GenericAnswerModal(discord.ui.Modal):
    def __init__(self, parent_view: "GenericQuestionView", q_index: int):
        super().__init__(title=f"Question {q_index + 1} / {len(parent_view.questions)}")
        self.parent_view = parent_view
        self.q_index = q_index

        self.answer = discord.ui.TextInput(
            label="Your Answer",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=900,
            placeholder="Type your answer here..."
        )
        self.add_item(self.answer)

    async def on_submit(self, interaction: discord.Interaction):
        self.parent_view.answers.append(str(self.answer.value).strip())

        if self.parent_view.q_index + 1 >= len(self.parent_view.questions):
            await self.parent_view.finish(interaction)
        else:
            self.parent_view.q_index += 1
            await self.parent_view.show_question(interaction)


class GenericStartView(discord.ui.View):
    def __init__(self, bot: commands.Bot, guild_id: int, applicant: discord.User, app_title: str, questions: list[str]):
        super().__init__(timeout=600)
        self.bot = bot
        self.guild_id = guild_id
        self.applicant = applicant
        self.app_title = app_title
        self.questions = questions

    @discord.ui.button(label="Continue", style=discord.ButtonStyle.green)
    async def continue_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.applicant.id:
            return await interaction.response.send_message("❌ This is not for you.", ephemeral=True)

        q_view = GenericQuestionView(self.bot, self.guild_id, self.applicant, self.app_title, self.questions)
        await interaction.response.edit_message(embed=q_view.current_embed(), view=q_view)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.applicant.id:
            return await interaction.response.send_message("❌ This is not for you.", ephemeral=True)

        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content="✅ Application cancelled.", embed=None, view=self)
        self.stop()


class GenericQuestionView(discord.ui.View):
    def __init__(self, bot: commands.Bot, guild_id: int, applicant: discord.User, app_title: str, questions: list[str]):
        super().__init__(timeout=1200)
        self.bot = bot
        self.guild_id = guild_id
        self.applicant = applicant
        self.app_title = app_title
        self.questions = questions
        self.q_index = 0
        self.answers: list[str] = []

    def current_embed(self) -> discord.Embed:
        q = self.questions[self.q_index]
        return _make_app_embed(
            f"SFG {self.app_title} Application",
            f"**{q}**\n\nClick **Answer** to respond."
        )

    async def show_question(self, interaction: discord.Interaction):
        await interaction.response.edit_message(embed=self.current_embed(), view=self)
    async def show_question(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            embed=self.current_embed(),
            view=self
        )

    async def finish(self, interaction: discord.Interaction):
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            embed=_make_app_embed(
                f"SFG {self.app_title} Application",
                "✅ Thank you! Your application has been submitted."
            ),
            view=self
        )

        # Fetch guild safely
        guild = self.bot.get_guild(self.guild_id)
        if guild is None:
            try:
                guild = await self.bot.fetch_guild(self.guild_id)
            except Exception:
                guild = None

        if guild:

            sfg_pings = " ".join(
                [r.mention for r in guild.roles if r.name == "SFG"]
            ) or None

            results_ch = guild.get_channel(RESULTS_CHANNEL_ID)

            results_embed = _make_results_embed(
                self.app_title,
                self.applicant,
                self.questions,
                self.answers
            )

            if results_ch:
                await results_ch.send(
                    content=sfg_pings,
                    embed=results_embed
                )

        self.stop()

    @discord.ui.button(label="Answer", style=discord.ButtonStyle.primary)
    async def answer_btn(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if interaction.user.id != self.applicant.id:
            return await interaction.response.send_message(
                "❌ This is not for you.",
                ephemeral=True
            )

        await interaction.response.send_modal(GenericAnswerModal(self, self.q_index))

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.applicant.id:
            return await interaction.response.send_message("❌ This is not for you.", ephemeral=True)

        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content="✅ Application cancelled.", embed=None, view=self)
        self.stop()


async def start_generic_application(
    bot: commands.Bot,
    guild: discord.Guild,
    applicant: discord.User,
    app_title: str,
    questions: list[str],
) -> bool:
    start_embed = _make_app_embed(
        f"SFG {app_title} Application",
        "Please answer all the questions to the best of your ability.\n\n"
        "Click the **Continue** button when you're ready to begin, or **Cancel** to quit."
    )

    try:
        await applicant.send(
            embed=start_embed,
            view=GenericStartView(bot, guild.id, applicant, app_title, questions)
        )
        return True
    except discord.Forbidden:
        return False
    except discord.HTTPException:
        return False


# =========================================================
# START FUNCTIONS (kept for compatibility with your old names)
# =========================================================

async def start_investigation_application(bot: commands.Bot, guild: discord.Guild, applicant: discord.User) -> bool:
    return await start_generic_application(bot, guild, applicant, "Investigation Staff", INVESTIGATION_QUESTIONS)

async def start_referee_application(bot: commands.Bot, guild: discord.Guild, applicant: discord.User) -> bool:
    return await start_generic_application(bot, guild, applicant, "Referee Staff", REFEREE_QUESTIONS)


# =========================================================
# PANEL SELECTS
# =========================================================

class ApplicationBranchView(discord.ui.View):
    """Shown on the PUBLIC panel message. Never changes."""
    def __init__(self, guild: discord.Guild | None = None):
        super().__init__(timeout=None)
        self.guild = guild
        self.add_item(ApplicationBranchSelect())


class ApplicationBranchSelect(discord.ui.Select):
    """Public dropdown. Opens a PRIVATE (ephemeral) menu."""
    def __init__(self):
        options = [discord.SelectOption(label=name, value=name) for name in APPLICATION_BRANCHES.keys()]
        super().__init__(
            placeholder="Select an application branch",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        branch = self.values[0]
        data = APPLICATION_BRANCHES[branch]

        # ✅ Private menu (only the clicker sees it)
        return await interaction.response.send_message(
            content=f"**{branch} Applications**\nSelect what you want to apply for:",
            ephemeral=True,
            view=ApplicationRoleView(branch, data),
        )


class EphemeralBranchPickerView(discord.ui.View):
    """Used when someone hits Back (still private/ephemeral)."""
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(EphemeralBranchPickerSelect())


class EphemeralBranchPickerSelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=name, value=name) for name in APPLICATION_BRANCHES.keys()]
        super().__init__(
            placeholder="Select an application branch",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        branch = self.values[0]
        data = APPLICATION_BRANCHES[branch]

        return await interaction.response.edit_message(
            content=f"**{branch} Applications**\nSelect what you want to apply for:",
            view=ApplicationRoleView(branch, data),
        )


class ApplicationRoleView(discord.ui.View):
    """Ephemeral role picker + Back button."""
    def __init__(self, branch_name: str, data: dict):
        super().__init__(timeout=300)
        self.branch_name = branch_name
        self.data = data
        self.add_item(ApplicationRoleSelect(branch_name, data))

    @discord.ui.button(label="⬅ Back", style=discord.ButtonStyle.secondary)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        return await interaction.response.edit_message(
            content="Select an application branch:",
            view=EphemeralBranchPickerView(),
        )


class ApplicationRoleSelect(discord.ui.Select):
    def __init__(self, branch_name: str, data: dict):
        options = [discord.SelectOption(label=opt, value=opt) for opt in data["options"]]
        super().__init__(
            placeholder=f"{branch_name} Applications",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        choice = (self.values[0] or "").strip()

        async def _dm_result(ok: bool, label: str):
            if not ok:
                return await interaction.response.edit_message(
                    content="❌ I couldn't DM you. Please enable DMs from server members and try again.",
                    view=None
                )
            return await interaction.response.edit_message(
                content=f"✅ Check your DMs to continue the **{label}** application.",
                view=None
            )

        # ✅ Justice
        if choice == "Investigation Staff":
            ok = await start_investigation_application(interaction.client, interaction.guild, interaction.user)  # type: ignore
            return await _dm_result(ok, "Investigation Staff")

        if choice == "Referee Staff":
            ok = await start_referee_application(interaction.client, interaction.guild, interaction.user)  # type: ignore
            return await _dm_result(ok, "Referee Staff")

        # ✅ Community
        if choice == "Media Analyst":
            ok = await start_generic_application(interaction.client, interaction.guild, interaction.user, "Media Analyst", MEDIA_ANALYST_QUESTIONS)  # type: ignore
            return await _dm_result(ok, "Media Analyst")

        if choice == "Media Owner":
            ok = await start_generic_application(interaction.client, interaction.guild, interaction.user, "Media Owner", MEDIA_OWNER_QUESTIONS)  # type: ignore
            return await _dm_result(ok, "Media Owner")

        if choice == "Streamer":
            ok = await start_generic_application(interaction.client, interaction.guild, interaction.user, "Streamer", STREAMER_QUESTIONS)  # type: ignore
            return await _dm_result(ok, "Streamer")

        if choice == "Host":
            ok = await start_generic_application(interaction.client, interaction.guild, interaction.user, "Host", HOST_QUESTIONS)  # type: ignore
            return await _dm_result(ok, "Host")

        # ✅ Franchise
        if choice == "Franchise Owner":
            ok = await start_generic_application(interaction.client, interaction.guild, interaction.user, "Franchise Owner", FRANCHISE_OWNER_QUESTIONS)  # type: ignore
            return await _dm_result(ok, "Franchise Owner")

        # ✅ Awards Committee
        if choice == "Stat Analyst":
            ok = await start_generic_application(interaction.client, interaction.guild, interaction.user, "Stat Analyst", STAT_ANALYST_QUESTIONS)  # type: ignore
            return await _dm_result(ok, "Stat Analyst")

        return await interaction.response.edit_message(content=f"✅ You selected **{choice}**.", view=None)
# =========================
# /ruling (Admin Punishments)
# =========================

SUSPENDED_ROLE_NAME = "Suspended"
BLACKLIST_ROLE_NAME = "Blacklisted"
RULINGS_CHANNEL_NAME = "Judgements"


@bot.tree.command(
    name="ruling",
    description="Admin: punish a player (Suspension / Blacklist / Ban)"
)
@app_commands.describe(
    user="User being punished",
    punishment="Type of punishment",
    bail_price="Bail price",
    description="What happened"
)
@app_commands.choices(
    punishment=[
        app_commands.Choice(name="Suspension", value="Suspension"),
        app_commands.Choice(name="Blacklist", value="Blacklist"),
        app_commands.Choice(name="Ban", value="Ban"),
    ]
)
async def ruling(
    interaction: discord.Interaction,
    user: discord.Member,
    punishment: app_commands.Choice[str],
    bail_price: app_commands.Range[int, 0, 1_000_000],
    description: str
):

    guild = interaction.guild
    issuer = interaction.user

    if not guild:
        return await interaction.response.send_message(
            "Server only command.",
            ephemeral=True
        )

    # Permission check
    perms = issuer.guild_permissions
    if not (perms.administrator or perms.ban_members or perms.manage_guild):
        return await interaction.response.send_message(
            "No permission.",
            ephemeral=True
        )

    if user.id == issuer.id:
        return await interaction.response.send_message(
            "You can't punish yourself.",
            ephemeral=True
        )

    # -------------------
    # Build embed
    # -------------------

    embed = discord.Embed(
        title="SFG – Judgement",
        description=f"**Punishment:** {punishment.value}",
        color=0xED4245,
        timestamp=datetime.utcnow()
    )

    embed.set_thumbnail(url=SFG_LOGO_URL)

    embed.add_field(name="Offender", value=user.mention, inline=True)
    embed.add_field(name="Issued By", value=issuer.mention, inline=True)
    embed.add_field(name="Bail Price", value=f"${bail_price:,}", inline=True)
    embed.add_field(name="Details", value=description[:1024], inline=False)

    action_taken = ""

    # -------------------
    # DM USER FIRST (important for bans)
    # -------------------

    try:
        await user.send(embed=embed)
    except discord.Forbidden:
        pass

    # -------------------
    # APPLY PUNISHMENT
    # -------------------

    try:

        if punishment.value == "Suspension":

            role = discord.utils.get(guild.roles, name=SUSPENDED_ROLE_NAME)

            if not role:
                return await interaction.response.send_message(
                    "Suspended role missing.",
                    ephemeral=True
                )

            await user.add_roles(role)
            action_taken = f"{user.mention} Suspended"


        elif punishment.value == "Blacklist":

            role = discord.utils.get(guild.roles, name=BLACKLIST_ROLE_NAME)

            if not role:
                return await interaction.response.send_message(
                    "Blacklisted role missing.",
                    ephemeral=True
                )

            await user.add_roles(role)
            action_taken = f"{user.mention} Blacklisted"


        elif punishment.value == "Ban":

            await guild.ban(
                user,
                reason=f"Ruling | {description}",
                delete_message_days=0
            )

            action_taken = f"{user.mention} Banned"


    except discord.Forbidden:

        return await interaction.response.send_message(
            "Permission error.",
            ephemeral=True
        )

    except Exception as e:

        return await interaction.response.send_message(
            f"Error: {e}",
            ephemeral=True
        )


    # -------------------
    # SEND TO JUDGEMENTS CHANNEL
    # -------------------

    judgements_ch = discord.utils.get(
        guild.text_channels,
        name=RULINGS_CHANNEL_NAME.lower()
    )

    await interaction.response.send_message(
        action_taken,
        ephemeral=True
    )

    if judgements_ch:
        await judgements_ch.send(embed=embed)
# =========================
# /GAMETIME
# =========================

@bot.tree.command(
    name="gametime",
    description="Post a scheduled game time between two NFL teams."
)
@app_commands.describe(
    team1="First NFL team",
    team2="Second NFL team",
    when="Start time (7:00 PM – 11:00 PM, 15-min intervals)"
)
@app_commands.autocomplete(team1=nfl_team_autocomplete, team2=nfl_team_autocomplete)
@app_commands.choices(when=GAMETIME_TIME_CHOICES)
async def gametime(
    interaction: discord.Interaction,
    team1: str,
    team2: str,
    when: app_commands.Choice[str],
):
    guild = interaction.guild
    if not guild:
        return await interaction.response.send_message("Server-only command.", ephemeral=True)

    if not isinstance(interaction.user, discord.Member):
        return await interaction.response.send_message("Couldn’t verify roles.", ephemeral=True)

    # Validate teams
    if team1 not in NFL_TEAMS or team2 not in NFL_TEAMS:
        return await interaction.response.send_message("❌ Invalid NFL teams.", ephemeral=True)

    if team1 == team2:
        return await interaction.response.send_message("❌ Teams can’t be the same.", ephemeral=True)

    role1 = get_team_role(guild, team1)
    role2 = get_team_role(guild, team2)
    if not role1 or not role2:
        return await interaction.response.send_message("❌ Team roles missing in server.", ephemeral=True)

    # Must be on one of the teams
    user_team = get_member_team_name(interaction.user)
    if user_team not in (team1, team2):
        return await interaction.response.send_message(
            f"❌ You must be on {role1.mention} or {role2.mention} to post this.",
            ephemeral=True
        )

    # Must have one of the allowed management roles
    allowed_roles = {"Franchise Owner", "Team President", "General Manager"}
    if not any(r.name in allowed_roles for r in interaction.user.roles):
        return await interaction.response.send_message(
            "❌ Only **Franchise Owners**, **Team Presidents**, or **General Managers** can post game times.",
            ephemeral=True
        )

    # Find Gametimes channel (font + case insensitive)
    gametimes_ch = find_text_channel_fuzzy(guild, "gametimes")
    if not gametimes_ch:
        return await interaction.response.send_message("❌ Gametimes channel not found.", ephemeral=True)

    # Parse selected time
    try:
        dt = _parse_when_to_dt(when.value)
    except Exception as e:
        return await interaction.response.send_message(f"❌ {e}", ephemeral=True)

    unix = int(dt.timestamp())
    time_full = f"<t:{unix}:t>"
    time_relative = f"<t:{unix}:R>"

    # Embed color = submitting team
    color = TEAM_COLORS.get(user_team, 0x2F3136)

    e1 = get_team_emoji(guild, team1)
    e2 = get_team_emoji(guild, team2)

    left = f"{e1} {role1.mention}".strip()
    right = f"{e2} {role2.mention}".strip()

    embed = discord.Embed(
        title="SFG Scheduling",
        description=f"**Scheduled @ {time_full}**",
        color=color
    )

    # SFG logo (top-right)
    embed.set_thumbnail(url=SFG_LOGO_URL)

    embed.add_field(name="\u200b", value=f"{left} vs {right}", inline=False)

    # Start + Coach combined (no gap)
    embed.add_field(
        name="\u200b",
        value=(
            f"⏰ **Start:** {time_relative}\n"
            f"**Coach:** {interaction.user.mention} ({user_team})"
        ),
        inline=False
    )

    embed.set_footer(
        text=interaction.user.display_name,
        icon_url=interaction.user.display_avatar.url
    )

    # ✅ Send with claim button view
    view = StreamClaimView()
    await gametimes_ch.send(embed=embed, view=view)

    await interaction.response.send_message(
        f"✅ Posted in {gametimes_ch.mention}.",
        ephemeral=True
    )

# =========================
# STREAM HELPERS (add once)
# =========================

YOUTUBE_COLOR = 0xFF0000
TWITCH_COLOR  = 0x9146FF  # Twitch purple

YOUTUBE_LOGO_URL = "https://cdn-icons-png.flaticon.com/512/1384/1384060.png"
TWITCH_LOGO_URL  = "https://cdn-icons-png.flaticon.com/512/5968/5968819.png"

async def nfl_team_autocomplete(interaction: discord.Interaction, current: str):
    current = (current or "").lower().strip()
    matches = [t for t in NFL_TEAMS if current in t.lower()]
    return [app_commands.Choice(name=t, value=t) for t in matches[:25]]

# =========================
# STREAM
# =========================

@bot.tree.command(
    name="stream",
    description="Streamer-only: post a stream link + matchup in the Streams channel."
)
@app_commands.describe(
    team1="First NFL team",
    team2="Second NFL team",
    platform="Streaming platform",
    link="Stream URL (must start with http:// or https://)"
)
@app_commands.autocomplete(team1=nfl_team_autocomplete, team2=nfl_team_autocomplete)
@app_commands.choices(
    platform=[
        app_commands.Choice(name="YouTube", value="YouTube"),
        app_commands.Choice(name="Twitch", value="Twitch"),
    ]
)
async def stream(
    interaction: discord.Interaction,
    team1: str,
    team2: str,
    platform: app_commands.Choice[str],
    link: str
):
    guild = interaction.guild
    if not guild:
        return await interaction.response.send_message("Server-only command.", ephemeral=True)

    member = interaction.user
    if not isinstance(member, discord.Member):
        return await interaction.response.send_message("Couldn’t verify roles.", ephemeral=True)

    # Streamer role gate
    if not has_role_name(member, STREAMER_ROLE_NAME):
        return await interaction.response.send_message(
            f"❌ You need the **{STREAMER_ROLE_NAME}** role to use `/stream`.",
            ephemeral=True
        )

    # 24h cooldown
    now = time.time()
    last = stream_cooldowns.get(member.id, 0)
    if now - last < STREAM_COOLDOWN_SECONDS:
        remaining = int(STREAM_COOLDOWN_SECONDS - (now - last))
        h, m = divmod(remaining // 60, 60)
        return await interaction.response.send_message(
            f"⏳ You must wait **{h}h {m}m** before using `/stream` again.",
            ephemeral=True
        )

    # Validate teams
    if team1 not in NFL_TEAMS or team2 not in NFL_TEAMS or team1 == team2:
        return await interaction.response.send_message("❌ Invalid team selection.", ephemeral=True)

    if not URL_REGEX.match(link.strip()):
        return await interaction.response.send_message(
            "❌ Link must start with **http://** or **https://**.",
            ephemeral=True
        )

    streams_ch = find_streams_channel(guild, STREAMS_CHANNEL_NAME)
    if not streams_ch:
        return await interaction.response.send_message("❌ Streams channel not found.", ephemeral=True)

    role1 = get_team_role(guild, team1)
    role2 = get_team_role(guild, team2)
    if not role1 or not role2:
        return await interaction.response.send_message("❌ Team roles missing.", ephemeral=True)

    # Emojis (string + object)
    e1 = get_team_emoji(guild, team1)
    e2 = get_team_emoji(guild, team2)
    e1_obj = get_team_emoji_obj(guild, team1)
    e2_obj = get_team_emoji_obj(guild, team2)

    left = f"{e1} {role1.mention}".strip()
    right = f"{e2} {role2.mention}".strip()

    # Platform styling
    if platform.value == "YouTube":
        color = YOUTUBE_COLOR
        logo = YOUTUBE_LOGO_URL
    else:
        color = TWITCH_COLOR
        logo = TWITCH_LOGO_URL

    embed = discord.Embed(
        title="📺 Live Stream",
        description=(
            f"**Matchup:** {left} vs {right}\n"
            f"**Platform:** {platform.value}\n"
            f"**Link:** {link}"
        ),
        color=color
    )
    embed.set_thumbnail(url=logo)
    embed.set_footer(text=f"Posted by {member.display_name}")

    # Send message with @here
    msg = await streams_ch.send(
        content=f"@here\n{left} {right}",
        embed=embed
    )

    # Add voting reactions
    if e1_obj:
        await msg.add_reaction(e1_obj)
    if e2_obj:
        await msg.add_reaction(e2_obj)

    # Set cooldown after success
    stream_cooldowns[member.id] = now

    await interaction.response.send_message(
        f"✅ Stream posted in {streams_ch.mention}.",
        ephemeral=True
    )

# =========================
# FOOTBALL FUSION PARSING
# =========================
_SCORE_RE = re.compile(r"(\d{1,3})\s*-\s*(\d{1,3})")

import hashlib
import json

def make_report_id(report: dict) -> str:
    raw = json.dumps(report, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

def extract_score_from_prefix(raw: str) -> Optional[Tuple[int, int]]:
    raw = raw.strip().lstrip("\ufeff")
    brace = raw.find("{")
    head = raw[:brace] if brace != -1 else raw[:250]
    m = _SCORE_RE.search(head)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))

def extract_json_object(raw: str) -> dict:
    raw = (raw or "").strip().lstrip("\ufeff")
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in file/text.")
    return json.loads(raw[start:end + 1])

def extract_players(report: dict) -> list[dict]:
    """
    Football Fusion export format:
      top-level dict keyed by Roblox userId strings ("123456789": {...})
    """
    players: list[dict] = []
    if not isinstance(report, dict):
        return players

    for roblox_id_str, pdata in report.items():
        if not isinstance(pdata, dict):
            continue
        if not str(roblox_id_str).isdigit():
            continue

        roblox_id = int(roblox_id_str)

        other = pdata.get("other", {}) if isinstance(pdata.get("other"), dict) else {}
        qb = pdata.get("qb", {}) if isinstance(pdata.get("qb"), dict) else {}
        wr = pdata.get("wr", {}) if isinstance(pdata.get("wr"), dict) else {}
        db = pdata.get("db", {}) if isinstance(pdata.get("db"), dict) else {}
        de = pdata.get("def", {}) if isinstance(pdata.get("def"), dict) else {}

        name = str(other.get("name", "")).strip()
        display = str(other.get("display", "")).strip()
        roblox_username = name or display or str(roblox_id)

        players.append({
            "roblox_id": roblox_id,
            "roblox_username": roblox_username,
            "roblox_display": display or name or roblox_username,

            # QB
            "qb_qbr": float(qb.get("rtng", 0) or 0),
            "qb_comp": int(qb.get("comp", 0) or 0),
            "qb_yds": int(qb.get("yds", 0) or 0),
            "qb_td": int(qb.get("td", 0) or 0),
            "qb_int": int(qb.get("int", 0) or 0),

            # WR
            "wr_rec": int(wr.get("catch", 0) or 0),
            "wr_yds": int(wr.get("yds", 0) or 0),
            "wr_td": int(wr.get("td", 0) or 0),
            "wr_fum": int(wr.get("fum", 0) or wr.get("fumble", 0) or 0),

            # DB
            "db_swats": int(db.get("defl", 0) or 0),
            "db_int": int(db.get("int", 0) or 0),
            "db_dbr": float(db.get("rtng", 0) or 0),

            # DE
            "de_sacks": int(de.get("sack", 0) or 0),
            "de_safeties": int(de.get("safe", 0) or 0),
            "de_ff": int(de.get("ffum", 0) or 0),
        })
    return players

async def process_stats_to_sheets(interaction: discord.Interaction, report: dict, game_id: int) -> int:
    guild = interaction.guild
    players = extract_players(report)

    updated = 0
    missing: list[str] = []
    errors: list[str] = []

    if not BLOXLINK_API_KEY:
        await send_logs(
            guild,
            "⚠ **Bloxlink API Key missing**\n"
            "Roblox IDs cannot be mapped to Discord users without BLOXLINK_API_KEY.\n"
            "Fallback name-matching is enabled (less accurate)."
        )

    for p in players:
        rid = p["roblox_id"]
        try:
            roblox_username = p.get("roblox_username", "")
            roblox_display_name = p.get("roblox_display", "")

            member = None

            discord_id = await get_cached_discord_id(guild.id, rid)
            if discord_id:
                member = guild.get_member(discord_id)
                if member is None:
                    try:
                        member = await guild.fetch_member(discord_id)
                    except discord.NotFound:
                        member = None

            if member is None:
                member = resolve_discord_member_from_roblox(
                    guild,
                    roblox_id=rid,
                    roblox_username=roblox_username,
                    roblox_display_name=roblox_display_name
                )

            if member:
                update_roblox_discord_cache(
                    member,
                    roblox_id=rid,
                    roblox_username=roblox_username,
                    roblox_display_name=roblox_display_name
                )
            
            if not member:
                missing.append(roblox_username or str(rid))
                continue

            team_name = get_member_team_name(member) or "Free Agent"
            wrote_any = False

            # QB
            if (p["qb_comp"] > 0 or p["qb_yds"] > 0 or p["qb_td"] > 0 or p["qb_int"] > 0 or p["qb_qbr"] > 0):
                await asyncio.to_thread(
                    append_qb_statline,
                    game_id, member.id, member.display_name, team_name,
                    p["qb_qbr"], p["qb_comp"], p["qb_yds"], p["qb_td"], p["qb_int"]
                )
                wrote_any = True

            # WR
            if (p["wr_rec"] > 0 or p["wr_yds"] > 0 or p["wr_td"] > 0 or p["wr_fum"] > 0):
                await asyncio.to_thread(
                    append_wr_statline,
                    game_id, member.id, member.display_name, team_name,
                    p["wr_rec"], p["wr_yds"], p["wr_td"], p["wr_fum"]
                )
                wrote_any = True

            # DB
            if (p["db_swats"] > 0 or p["db_int"] > 0 or p["db_dbr"] > 0):
                await asyncio.to_thread(
                    append_db_statline,
                    game_id, member.id, member.display_name, team_name,
                    p["db_swats"], p["db_int"], p["db_dbr"]
                )
                wrote_any = True

            # DE
            if (p["de_sacks"] > 0 or p["de_safeties"] > 0 or p["de_ff"] > 0):
                await asyncio.to_thread(
                    append_de_statline,
                    game_id, member.id, member.display_name, team_name,
                    p["de_sacks"], p["de_safeties"], p["de_ff"]
                )
                wrote_any = True

            if wrote_any:
                updated += 1

        except Exception as e:
            errors.append(f"{p.get('roblox_username') or rid}: {type(e).__name__}: {e}")

    if missing:
        await send_logs(
            guild,
            "⚠ **Game Report – No Discord match for these players**\n"
            "```\n" + "\n".join(missing[:50]) + "\n```"
        )

    if errors:
        await send_logs(
            guild,
            "❌ **Game Report – Sheet update errors**\n"
            "```\n" + "\n".join(errors[:15]) + "\n```"
        )

    # refresh PlayerStats Top 15
    try:
        await asyncio.to_thread(update_playerstats_top15)
    except Exception as e:
        await send_logs(
            guild,
            f"⚠ PlayerStats update failed: {type(e).__name__}: {e}"
        )

    return updated

# =========================
# 2-STEP OPPONENT DROPDOWN (never >25)
# =========================

def team_groups(teams: list[str]) -> dict[str, list[str]]:
    return {"Group 1": teams[:16], "Group 2": teams[16:]}


class TeamPickView(discord.ui.View):
    def __init__(
        self,
        submitter: discord.Member,
        images: dict,
        your_score: int,
        opp_score: int,
        teams: list[str],
        your_team: str | None = None,   # carry detected submitter team through
    ):
        super().__init__(timeout=180)
        self.submitter = submitter
        self.images = images
        self.your_score = int(your_score)
        self.opp_score = int(opp_score)
        self.teams = teams
        self.your_team = your_team
        self.posted = False
        self.add_item(TeamSelect(self))

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


class TeamSelect(discord.ui.Select):
    def __init__(self, view: TeamPickView):
        self.parent_view = view
        teams = self.parent_view.teams[:25]
        super().__init__(
            placeholder="Select the team you faced",
            min_values=1,
            max_values=1,
            options=[discord.SelectOption(label=t, value=t) for t in teams],
        )

    async def callback(self, interaction: discord.Interaction):
        # Only the original submitter can use the menu
        if interaction.user.id != self.parent_view.submitter.id:
            return await interaction.response.send_message(
                "❌ Only the person who ran **/gamereport** can select the opponent.",
                ephemeral=True,
            )

        # Prevent re-posting / re-running
        if self.parent_view.posted:
            return await interaction.response.send_message("✅ Already posted.", ephemeral=True)

        self.parent_view.posted = True

        opponent = self.values[0]
        opponent = canonical_team_name(opponent)

        guild = interaction.guild
        if not guild:
            self.parent_view.posted = False
            return await interaction.response.send_message("Server-only.", ephemeral=True)

        # Prefer the detected team passed down; fallback to role-based detection
        your_team = (
            (self.parent_view.your_team or "").strip()
            or get_member_team_name(self.parent_view.submitter)
            or "Your Team"
        )

        # Only canonicalize if we actually detected a team
        if your_team != "Your Team":
            your_team = canonical_team_name(your_team)

        your_score = int(self.parent_view.your_score)
        opp_score = int(self.parent_view.opp_score)

        # =========================
        # UPDATE STANDINGS (NO DEADLOCK)
        # =========================
        standings = None
        if your_team != "Your Team":
            async with STANDINGS_LOCK:
                standings = load_standings()
                update_game_result(standings, your_team, your_score, opponent, opp_score)  # <-- comma, not ;
                save_standings(standings)

            # ✅ IMPORTANT: Discord API call OUTSIDE the lock
            try:
                await post_or_update_standings(guild, standings)
            except Exception as e:
                await send_logs(
                    guild,
                    f"⚠ Standings post/update failed: {type(e).__name__}: {e}"
                )
        else:
            await send_logs(
                guild,
                "⚠ Standings not updated: could not detect submitter team name."
            )

        scores_ch = resolve_text_channel_by_id(guild, SCORES_CHANNEL_ID)
        if not scores_ch:
            self.parent_view.posted = False
            return await interaction.response.edit_message(
                content="❌ Scores channel not found.",
                view=None,
            )

        # Disable menu immediately so it can’t be clicked again
        for item in self.parent_view.children:
            item.disabled = True

        # Safely edit the interaction message
        try:
            await interaction.response.edit_message(
                content=f"⏳ Posting to Scores vs **{opponent}**...",
                view=self.parent_view,
            )
        except discord.InteractionResponded:
            await interaction.edit_original_response(
                content=f"⏳ Posting to Scores vs **{opponent}**...",
                view=self.parent_view,
            )

        try:
            # keep the SAME canonical your_team we already computed above
            embed_team = your_team  # already canonical if detected

            your_emoji = get_team_emoji(guild, embed_team)
            opp_emoji = get_team_emoji(guild, opponent)

            your_trophy = " 🏆" if your_score > opp_score else ""
            opp_trophy = " 🏆" if opp_score > your_score else ""

            your_team_role = get_team_role(guild, embed_team)
            opp_team_role = get_team_role(guild, opponent)

            your_team_mention = (
                your_team_role.mention if your_team_role else f"@{embed_team}"
            )
            opp_team_mention = (
                opp_team_role.mention if opp_team_role else f"@{opponent}"
            )

            # Safe UTC timestamp regardless of datetime import style
            ts = datetime.datetime.utcnow() if hasattr(datetime, "datetime") else datetime.utcnow()

            embed = discord.Embed(
                title="Matchup Report",
                description=(
                    f"{your_emoji} {your_team_mention} **{your_score}**{your_trophy}\n"
                    f"{opp_emoji} {opp_team_mention} **{opp_score}**{opp_trophy}\n\n"
                    "**Final Score**"
                ),
                color=0x2ECC71,
                timestamp=ts,
            )

            embed.set_footer(
                text=f"Submitted by {self.parent_view.submitter}",
                icon_url=self.parent_view.submitter.display_avatar.url,
            )

            files = [await att.to_file() for att in self.parent_view.images.values()]
            await scores_ch.send(embed=embed, files=files)

            # Remove the UI entirely so it can’t be used again
            await interaction.edit_original_response(
                content=f"✅ Posted to Scores vs **{opponent}**.",
                view=None,
            )

            self.parent_view.stop()

        except Exception as e:
            self.parent_view.posted = False
            await interaction.edit_original_response(
                content=f"❌ Failed to post.\n```{type(e).__name__}: {e}```",
                view=None,
            )
            self.parent_view.stop()


class GroupPickView(discord.ui.View):
    def __init__(
        self,
        submitter: discord.Member,
        images: dict,
        your_score: int,
        opp_score: int,
        your_team: str | None = None,
    ):
        super().__init__(timeout=180)
        self.submitter = submitter
        self.images = images
        self.your_score = int(your_score)
        self.opp_score = int(opp_score)
        self.your_team = your_team

        self.groups = team_groups(NFL_TEAMS)

        # If we don't know your team, make you pick it first.
        if not self.your_team:
            self.add_item(YourTeamSelect(self))
        else:
            self.add_item(GroupSelect(self))

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


class YourTeamSelect(discord.ui.Select):
    def __init__(self, parent_view: "GroupPickView"):
        self.parent_view = parent_view  # ✅ renamed (don't use .parent)

        options: list[discord.SelectOption] = []
        for group_name, teams in self.parent_view.groups.items():
            preview = ", ".join(teams[:4]) + ("..." if len(teams) > 4 else "")
            options.append(
                discord.SelectOption(
                    label=group_name,
                    description=preview,
                    value=group_name,
                )
            )

        super().__init__(
            placeholder="Select YOUR team group first",
            min_values=1,
            max_values=1,
            options=options[:25],
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.parent_view.submitter.id:
            return await interaction.response.send_message(
                "❌ Only the person who ran **/gamereport** can select this.",
                ephemeral=True,
            )

        picked_group = self.values[0]
        group_teams = list(self.parent_view.groups.get(picked_group, []))

        await interaction.response.edit_message(
            content="Pick **YOUR exact team**:",
            view=PickYourTeamView(
                submitter=self.parent_view.submitter,
                images=self.parent_view.images,
                your_score=self.parent_view.your_score,
                opp_score=self.parent_view.opp_score,
                teams=group_teams,
            ),
        )



class PickYourTeamView(discord.ui.View):
    def __init__(
        self,
        submitter: discord.Member,
        images: dict,
        your_score: int,
        opp_score: int,
        teams: list[str],
    ):
        super().__init__(timeout=180)
        self.submitter = submitter
        self.images = images
        self.your_score = int(your_score)
        self.opp_score = int(opp_score)
        self.teams = teams
        self.add_item(PickYourTeamSelect(self))

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


class PickYourTeamSelect(discord.ui.Select):
    def __init__(self, view: PickYourTeamView):
        self.parent_view = view
        teams = self.parent_view.teams[:25]

        super().__init__(
            placeholder="Select YOUR team",
            min_values=1,
            max_values=1,
            options=[discord.SelectOption(label=t, value=t) for t in teams],
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.parent_view.submitter.id:
            return await interaction.response.send_message(
                "❌ Only the person who ran **/gamereport** can select this.",
                ephemeral=True,
            )

        chosen_team = self.values[0]

        await interaction.response.edit_message(
            content="Pick the opponent group:",
            view=GroupPickView(
                submitter=self.parent_view.submitter,
                images=self.parent_view.images,
                your_score=self.parent_view.your_score,
                opp_score=self.parent_view.opp_score,
                your_team=chosen_team,
            ),
        )


class GroupSelect(discord.ui.Select):
    def __init__(self, parent_view: GroupPickView):
        self.parent_view = parent_view  # ✅ renamed (don't use .parent)

        options = []
        for group_name, teams in self.parent_view.groups.items():
            preview = ", ".join(teams[:4]) + ("..." if len(teams) > 4 else "")
            options.append(
                discord.SelectOption(
                    label=group_name,
                    description=preview,
                    value=group_name,
                )
            )

        super().__init__(
            placeholder="Select the opponent group",
            min_values=1,
            max_values=1,
            options=options[:25],
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.parent_view.submitter.id:
            return await interaction.response.send_message(
                "❌ Only the person who ran **/gamereport** can select this.",
                ephemeral=True,
            )

        picked_group = self.values[0]
        group_teams = list(self.parent_view.groups.get(picked_group, []))

        # If your_team is known, remove it from the opponent list (so you can’t pick yourself)
        if self.parent_view.your_team and self.parent_view.your_team in group_teams:
            group_teams = [t for t in group_teams if t != self.parent_view.your_team]

        await interaction.response.edit_message(
            content="Pick the **exact team** you faced:",
            view=TeamPickView(
                submitter=self.parent_view.submitter,
                images=self.parent_view.images,
                your_score=self.parent_view.your_score,
                opp_score=self.parent_view.opp_score,
                teams=group_teams,
                your_team=self.parent_view.your_team,
            ),
        )
# =========================
# /gamereport (FO/TP ONLY)
# =========================

@bot.tree.command(
    name="gamereport",
    description="Submit Football Fusion game report (FO/TP only)."
)
@app_commands.describe(
    json_file="Football Fusion export (.txt or .json)",
    your_score="Your team's final score",
    qb_stats="QB stats image",
    wr_stats="WR stats image",
    db_stats="DB stats image",
    de_stats="DE stats image",
)
async def gamereport(
    interaction: discord.Interaction,
    json_file: discord.Attachment,
    your_score: int,
    qb_stats: discord.Attachment,
    wr_stats: discord.Attachment,
    db_stats: discord.Attachment,
    de_stats: discord.Attachment,
):
    # ── Permission check ─────────────────────────────
    if not can_submit_gamereport(interaction.guild, interaction.user):
        return await interaction.response.send_message(
            "Only **Franchise Owners** and **Team Presidents** may submit game reports.",
            ephemeral=True
        )

    # ── Defer (creates the ONE ephemeral message we will edit) ──
    try:
        await interaction.response.defer(ephemeral=True)
    except (discord.NotFound, discord.InteractionResponded):
        return

    try:
        raw = await json_file.read()
        text = raw.decode("utf-8", errors="replace")

        prefix_pair = extract_score_from_prefix(text)
        report = extract_json_object(text)
        report_id = make_report_id(report)
        

        game_id = int(time.time())
        updated = await process_stats_to_sheets(interaction, report, game_id)

        # ── Determine opponent score ──────────────────
        opp_score = 0
        if prefix_pair:
            a, b = prefix_pair
            if your_score == a:
                opp_score = b
            elif your_score == b:
                opp_score = a
            else:
                # fallback: still use detected "b" but log mismatch
                opp_score = b
                await send_logs(
                    interaction.guild,
                    f"⚠ **Score mismatch**\nTyped your_score={your_score}\nPrefix score={a}-{b}"
                )
        else:
            await send_logs(
                interaction.guild,
                "⚠ **Score auto-detect failed**: No 'XX - YY' score prefix found before JSON."
            )

        images = {"QB": qb_stats, "WR": wr_stats, "DB": db_stats, "DE": de_stats}

        # ── Best-effort detect submitter team (for removing it from opponent list) ──
        your_team: str | None = None
        if isinstance(interaction.user, discord.Member):
            your_team = _detect_user_team_from_roles(interaction.guild, interaction.user)

        # (Optional) show what the export seems to contain (does NOT update standings here)
        r1, r2 = _detect_teams_from_report(report)
        detected_line = ""
        if r1 or r2:
            detected_line = f"\n\n*(Detected teams in export: {r1 or 'Unknown'} vs {r2 or 'Unknown'})*"


        # ✅ IMPORTANT: edit the ORIGINAL deferred response (no followup)
        # Standings are updated later (in TeamSelect.callback) once the exact opponent team is chosen.
        await interaction.edit_original_response(
            content=(
                f"✅ Game report processed.\n"
                f"Wrote stat rows for **{updated}** matched player(s).\n"
                f"Detected score: **{your_score}-{opp_score}**\n\n"
                "Pick the opponent group:"
                + detected_line
            ),
            view=GroupPickView(
                interaction.user,
                images,
                your_score,
                opp_score,
                your_team=your_team,
            ),
        )

    except Exception as e:
        await interaction.edit_original_response(
            content=(
                "❌ Game report failed.\n"
                f"```{type(e).__name__}: {e}```"
            ),
            view=None
        )

# =========================
# RUN
# =========================

bot.run(os.getenv("DISCORD_TOKEN"))