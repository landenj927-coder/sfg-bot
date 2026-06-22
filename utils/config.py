from pathlib import Path
import re
from discord import app_commands

# =========================
# BASIC CONFIG
# =========================
GUILD_ID = 1194481657584042106

YOUTUBE_LOGO_URL = "https://cdn-icons-png.flaticon.com/512/1384/1384060.png"
TWITCH_LOGO_URL  = "https://cdn-icons-png.flaticon.com/512/5968/5968819.png"
SFG_LOGO_URL = "https://raw.githubusercontent.com/landenj927-coder/sfg-bot/main/assets/sfgblue.png"
STREAM_COOLDOWN_SECONDS = 86400
ROSTER_LIMIT = 14

# =========================
# CHANNELS / ROLES
# =========================
APPLICATION_PANEL_TITLE = "SFG Applications"
TRANSACTIONS_CHANNEL = "transactions"
STREAMER_ROLE_NAME = "Streamer"
STREAMS_CHANNEL_NAME = "streams"
GAMETIMES_CHANNEL_NAME = "gametimes"
STANDINGS_CHANNEL_NAME = "standings"
MEMBERS_CHANNEL_NAME = "members"

APPLICATIONS_RESULTS_CHANNEL_ID = 1488388680115687444
RULINGS_CHANNEL_ID = 1488380125149008046
GAMETIMES_CHANNEL_ID = 1488382045611622520
STREAMS_CHANNEL_ID = 1488381820939538464
APPLICATIONS_CHANNEL_ID = 1488379006733779046
STANDINGS_CHANNEL_ID = 1488382113240711189
LOGS_CHANNEL_ID = 1448938805083246602
SCORES_CHANNEL_ID = 1448922961783558154
RESULTS_CHANNEL_ID = 1450267610821431458

SUSPENDED_ROLE_NAME = "Suspended"
BLACKLIST_ROLE_NAME = "Blacklisted"
RULINGS_CHANNEL_NAME = "Judgements"

YOUTUBE_COLOR = 0xFF0000
TWITCH_COLOR = 0x9146FF

# =========================
# FILES
# =========================
STANDINGS_FILE = Path("standings.json")

# =========================
# REGEX
# =========================
URL_REGEX = re.compile(r"^https?://", re.IGNORECASE)

# =========================
# TEAMS
# These MUST match your Discord role names exactly.
# =========================
NFL_TEAMS = [
    "Arizona Cardinals",
    "San Franciso 49ers",
    "Atlanta Falcons",
    "Tampa Buccaneers",
    "Cleveland Browns",
    "Newark",
    "New York Giants",
    "New England Patriots",
    "Indianapolis Colts",
    "Jacksonville Jaguars",
    "Washington Commanders",
    "Cincinnati Bengals",
    "Miami Dolphins",
    "New Orleans Saints",
    "Green Bay Packers",
    "Houston Texans",
    "Dallas Cowboys",
    "Las Vegas Raiders",
    "Los Angeles Rams",
    "Kansas City Chiefs",
    "Los Angeles Chargers",
    "Minnesota Vikings",
    "Seattle Seahawks",
    "Detroit Lions",
    "Denver Broncos",
    "Philadelphia Eagles",
    "Pittsburgh Steelers",
    "Tennessee Titans",
    "Baltimore Ravens",
    "Carolina Panthers",
    "Chicago Bears",
    "Buffalo Bills",
]

TEAM_COLORS = {
    "Arizona Cardinals": 0x97233F,
    "San Franciso 49ers": 0xAA0000,
    "Atlanta Falcons": 0xA71930,
    "Tampa Buccaneers": 0xFF0000,
    "Cleveland Browns": 0x311D00,
    "Newark": 0x125740,
    "New York Giants": 0x0B2265,
    "New England Patriots": 0x002244,
    "Indianapolis Colts": 0x002C5F,
    "Jacksonville Jaguars": 0x006778,
    "Washington Commanders": 0x5A1414,
    "Cincinnati Bengals": 0xFB4F14,
    "Miami Dolphins": 0x008E97,
    "New Orleans Saints": 0xD3BC8D,
    "Green Bay Packers": 0x203731,
    "Houston Texans": 0x03202F,
    "Dallas Cowboys": 0x002244,
    "Las Vegas Raiders": 0x000000,
    "Los Angeles Rams": 0x003594,
    "Kansas City Chiefs": 0xE31837,
    "Los Angeles Chargers": 0x0080C6,
    "Minnesota Vikings": 0x4F2683,
    "Seattle Seahawks": 0x002244,
    "Detroit Lions": 0x0076B6,
    "Denver Broncos": 0xFB4F14,
    "Philadelphia Eagles": 0x004C54,
    "Pittsburgh Steelers": 0xFFB612,
    "Tennessee Titans": 0x4B92DB,
    "Baltimore Ravens": 0x241773,
    "Carolina Panthers": 0x0085CA,
    "Chicago Bears": 0x0B162A,
    "Buffalo Bills": 0x00338D,
}

TEAM_THUMBNAILS = {}

TEAM_EMOJI_NAME = {}

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