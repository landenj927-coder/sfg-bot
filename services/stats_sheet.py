import os
import json
import gspread
from google.oauth2.service_account import Credentials

# =========================
# GOOGLE CONFIG
# =========================
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

# =========================
# CLIENT / BOOK
# =========================
def _client():
    creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)

def _book():
    return _client().open_by_key(SPREADSHEET_ID)

# =========================
# MEMORY
# =========================
QB_DATA = {}
WR_DATA = {}
DB_DATA = {}
DE_DATA = {}

# =========================
# HELPERS
# =========================
def _short_team(team):
    if not team:
        return team
    return team.split()[-1]

def _get_player(store, name, team):
    if name not in store:
        store[name] = {
            "player": name,
            "team": _short_team(team),
            "qbr": 0, "comp": 0, "yds": 0, "td": 0, "int": 0,
            "rec": 0, "fum": 0,
            "defl": 0, "rtng": 0,
            "sack": 0, "safe": 0, "ff": 0
        }
    return store[name]

# =========================
# ADD STATS
# =========================
def append_qb_statline(player, team, qbr, comp, yds, td, ints):
    p = _get_player(QB_DATA, player, team)
    p["qbr"] = qbr
    p["comp"] += comp
    p["yds"] += yds
    p["td"] += td
    p["int"] += ints

def append_wr_statline(player, team, rec, yds, td, fum):
    p = _get_player(WR_DATA, player, team)
    p["rec"] += rec
    p["yds"] += yds
    p["td"] += td
    p["fum"] += fum

def append_db_statline(player, team, defl, ints, rtng):
    p = _get_player(DB_DATA, player, team)
    p["defl"] += defl
    p["int"] += ints
    p["rtng"] = rtng

def append_de_statline(player, team, sack, safe, ff):
    p = _get_player(DE_DATA, player, team)
    p["sack"] += sack
    p["safe"] += safe
    p["ff"] += ff

# =========================
# COMMIT TO SHEETS
# =========================
def commit_all_stats():
    book = _book()

    qb_sheet = book.worksheet("QB")
    wr_sheet = book.worksheet("WR")
    db_sheet = book.worksheet("DB")
    de_sheet = book.worksheet("DE")

    # CLEAR
    qb_sheet.batch_clear(["D8:J100"])
    wr_sheet.batch_clear(["D8:I100"])
    db_sheet.batch_clear(["D8:H100"])
    de_sheet.batch_clear(["D8:H100"])

    # QB
    qb_rows = [
        [p["player"], p["team"], p["qbr"], p["comp"], p["yds"], p["td"], p["int"]]
        for p in QB_DATA.values()
    ]
    if qb_rows:
        qb_sheet.update("D8", qb_rows, value_input_option="USER_ENTERED")

    # WR
    wr_rows = [
        [p["player"], p["team"], p["rec"], p["yds"], p["td"], p["fum"]]
        for p in WR_DATA.values()
    ]
    if wr_rows:
        wr_sheet.update("D8", wr_rows, value_input_option="USER_ENTERED")

    # DB
    db_rows = [
        [p["player"], p["team"], p["defl"], p["int"], p["rtng"]]
        for p in DB_DATA.values()
    ]
    if db_rows:
        db_sheet.update("D8", db_rows, value_input_option="USER_ENTERED")

    # DE
    de_rows = [
        [p["player"], p["team"], p["sack"], p["safe"], p["ff"]]
        for p in DE_DATA.values()
    ]
    if de_rows:
        de_sheet.update("D8", de_rows, value_input_option="USER_ENTERED")

    update_playerstats_top15()

# =========================
# PLAYERSTATS
# =========================
def update_playerstats_top15():
    sheet = _book().worksheet("PlayerStats")

    sheet.batch_clear([
        "A8:F22",
        "I8:N22",
        "A26:F40",
        "I26:N40"
    ])

    def top(data, key):
        return sorted(data.items(), key=lambda x: x[1][key], reverse=True)[:15]

    qb_top = top(QB_DATA, "yds")
    wr_top = top(WR_DATA, "yds")
    db_top = top(DB_DATA, "int")
    de_top = top(DE_DATA, "sack")

    # QB
    qb_rows = [
        [p["player"], p["team"], p["qbr"], p["comp"], p["yds"], p["td"], p["int"]]
        for _, p in qb_top
    ]
    if qb_rows:
        sheet.update("A8", qb_rows, value_input_option="USER_ENTERED")

    # WR (RIGHT SIDE - COLUMN I)
    wr_rows = [
        [p["player"], p["team"], p["rec"], p["yds"], p["td"], p["fum"]]
        for _, p in wr_top
    ]
    if wr_rows:
        sheet.update("I8", wr_rows, value_input_option="USER_ENTERED")

    # DB
    db_rows = [
        [p["player"], p["team"], p["defl"], p["int"], p["rtng"]]
        for _, p in db_top
    ]
    if db_rows:
        sheet.update("A26", db_rows, value_input_option="USER_ENTERED")

    # DE (RIGHT SIDE - COLUMN I)
    de_rows = [
        [p["player"], p["team"], p["sack"], p["safe"], p["ff"]]
        for _, p in de_top
    ]
    if de_rows:
        sheet.update("I26", de_rows, value_input_option="USER_ENTERED")