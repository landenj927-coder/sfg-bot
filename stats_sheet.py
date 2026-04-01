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
# MEMORY (AGGREGATED STATS)
# =========================
QB_DATA = {}
WR_DATA = {}
DB_DATA = {}
DE_DATA = {}

# =========================
# HELPERS
# =========================
def _get_player(store, name, team):
    if name not in store:
        store[name] = {
            "team": team,
            "qbr": 0, "comp": 0, "yds": 0, "td": 0, "int": 0,
            "rec": 0, "fum": 0,
            "defl": 0, "rtng": 0,
            "sack": 0, "safe": 0, "ff": 0
        }
    return store[name]

# =========================
# ADD STATS (AGGREGATED)
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
# COMMIT TO SHEETS (FAST)
# =========================
def commit_all_stats():
    book = _book()

    qb_sheet = book.worksheet("QB")
    wr_sheet = book.worksheet("WR")
    db_sheet = book.worksheet("DB")
    de_sheet = book.worksheet("DE")

    # CLEAR ONLY DATA AREAS
    qb_sheet.batch_clear(["A8:G100"])
    wr_sheet.batch_clear(["A8:F100"])
    db_sheet.batch_clear(["A8:E100"])
    de_sheet.batch_clear(["A8:E100"])

    # QB
    qb_rows = [
        [n, p["team"], p["qbr"], p["comp"], p["yds"], p["td"], p["int"]]
        for n, p in QB_DATA.items()
    ]
    if qb_rows:
        qb_sheet.update("A8", qb_rows)

    # WR
    wr_rows = [
        [n, p["team"], p["rec"], p["yds"], p["td"], p["fum"]]
        for n, p in WR_DATA.items()
    ]
    if wr_rows:
        wr_sheet.update("A8", wr_rows)

    # DB
    db_rows = [
        [n, p["team"], p["defl"], p["int"], p["rtng"]]
        for n, p in DB_DATA.items()
    ]
    if db_rows:
        db_sheet.update("A8", db_rows)

    # DE
    de_rows = [
        [n, p["team"], p["sack"], p["safe"], p["ff"]]
        for n, p in DE_DATA.items()
    ]
    if de_rows:
        de_sheet.update("A8", de_rows)

    update_playerstats_top15()

# =========================
# PLAYERSTATS TOP 15 (PERFECT LAYOUT)
# =========================
def update_playerstats_top15():
    sheet = _book().worksheet("PlayerStats")

    # clear ONLY data zones
    sheet.batch_clear([
        "A8:F22",   # QB
        "H8:M22",   # WR
        "A26:F40",  # DB
        "H26:M40"   # DE
    ])

    def top(data, key):
        return sorted(data.items(), key=lambda x: x[1][key], reverse=True)[:15]

    qb_top = top(QB_DATA, "yds")
    wr_top = top(WR_DATA, "yds")
    db_top = top(DB_DATA, "int")
    de_top = top(DE_DATA, "sack")

    # QB (LEFT TOP)
    qb_rows = [
        [n, p["team"], p["qbr"], p["comp"], p["yds"], p["td"], p["int"]]
        for n, p in qb_top
    ]
    if qb_rows:
        sheet.update("A8", qb_rows)

    # WR (RIGHT TOP)
    wr_rows = [
        [n, p["team"], p["rec"], p["yds"], p["td"], p["fum"]]
        for n, p in wr_top
    ]
    if wr_rows:
        sheet.update("H8", wr_rows)

    # DB (LEFT BOTTOM)
    db_rows = [
        [n, p["team"], p["defl"], p["int"], p["rtng"]]
        for n, p in db_top
    ]
    if db_rows:
        sheet.update("A26", db_rows)

    # DE (RIGHT BOTTOM)
    de_rows = [
        [n, p["team"], p["sack"], p["safe"], p["ff"]]
        for n, p in de_top
    ]
    if de_rows:
        sheet.update("H26", de_rows)