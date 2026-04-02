from pathlib import Path
import re
from discord import app_commands

# =========================
# BASIC CONFIG
# =========================
GUILD_ID = 1194481657584042106

SFG_LOGO_URL = "https://cdn.discordapp.com/attachments/1488380244237750412/1488996490662641884/sfgblue.png?ex=69cecf8b&is=69cd7e0b&hm=e61d9dc84c14639b2fe81789485534b39a98432a3d1291c71b1abee6332fc8c2&"

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

APPLICATIONS_CHANNEL_ID = 1488379006733779046
STANDINGS_CHANNEL_ID = 1488382113240711189
LOGS_CHANNEL_ID = 1448938805083246602
SCORES_CHANNEL_ID = 1448922961783558154
RESULTS_CHANNEL_ID = 1450267610821431458

SUSPENDED_ROLE_NAME = "Suspended"
BLACKLIST_ROLE_NAME = "Blacklisted"
RULINGS_CHANNEL_NAME = "Judgements"

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
# =========================
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

TEAM_THUMBNAILS = {}  # paste yours here if needed

TEAM_EMOJI_NAME = {}  # paste yours here if needed