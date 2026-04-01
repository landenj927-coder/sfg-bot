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

SPREADSHEET_ID = "1jxBjAM8BBobPgFsqwAKKl1XhhwtKPtE8D-EnFQOlrT8"

_client_cache = None


def _client():
    global _client_cache

    if _client_cache:
        return _client_cache

    creds_json = os.getenv("GOOGLE_CREDENTIALS")

    if not creds_json:
        raise Exception("GOOGLE_CREDENTIALS not set in Railway")

    creds_dict = json.loads(creds_json)

    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    _client_cache = gspread.authorize(creds)

    return _client_cache


def _book():
    return _client().open_by_key(SPREADSHEET_ID)


# =========================
# IN-MEMORY STORAGE
# =========================
QB_DATA = {}
WR_DATA = {}
DB_DATA = {}
DE_DATA = {}


# =========================
# APPEND / MERGE FUNCTIONS
# =========================
def append_qb_statline(name, team, qb):
    p = QB_DATA.setdefault(name, {
        "team": team,
        "qbr": 0,
        "comp": 0,
        "yds": 0,
        "td": 0,
        "int": 0
    })

    p["qbr"] = float(qb.get("rtng", 0) or 0)
    p["comp"] += int(qb.get("comp", 0) or 0)
    p["yds"] += int(qb.get("yds", 0) or 0)
    p["td"] += int(qb.get("td", 0) or 0)
    p["int"] += int(qb.get("int", 0) or 0)


def append_wr_statline(name, team, wr):
    p = WR_DATA.setdefault(name, {
        "team": team,
        "rec": 0,
        "yds": 0,
        "td": 0,
        "fum": 0
    })

    p["rec"] += int(wr.get("catch", 0) or 0)
    p["yds"] += int(wr.get("yds", 0) or 0)
    p["td"] += int(wr.get("td", 0) or 0)
    p["fum"] += int(wr.get("fum", 0) or 0)


def append_db_statline(name, team, db):
    p = DB_DATA.setdefault(name, {
        "team": team,
        "defl": 0,
        "int": 0,
        "rtng": 0
    })

    p["defl"] += int(db.get("defl", 0) or 0)
    p["int"] += int(db.get("int", 0) or 0)
    p["rtng"] += float(db.get("rtng", 0) or 0)


def append_de_statline(name, team, de):
    p = DE_DATA.setdefault(name, {
        "team": team,
        "sack": 0,
        "safe": 0,
        "ff": 0
    })

    p["sack"] += int(de.get("sack", 0) or 0)
    p["safe"] += int(de.get("safe", 0) or 0)
    p["ff"] += int(de.get("ffum", 0) or 0)


# =========================
# WRITE FUNCTION (FIXED)
# =========================
def _write_sheet(sheet_name, start_row, rows):
    sheet = _book().worksheet(sheet_name)

    # clear only data area
    sheet.batch_clear([f"A{start_row}:Z100"])

    if not rows:
        return

    sheet.update(f"A{start_row}", rows)


# =========================
# COMMIT ALL STATS
# =========================
def commit_all_stats():
    qb_rows = [
        [name, p["team"], p["qbr"], p["comp"], p["yds"], p["td"], p["int"]]
        for name, p in QB_DATA.items()
    ]

    wr_rows = [
        [name, p["team"], p["rec"], p["yds"], p["td"], p["fum"]]
        for name, p in WR_DATA.items()
    ]

    db_rows = [
        [name, p["team"], p["defl"], p["int"], p["rtng"]]
        for name, p in DB_DATA.items()
    ]

    de_rows = [
        [name, p["team"], p["sack"], p["safe"], p["ff"]]
        for name, p in DE_DATA.items()
    ]

    # 🔥 WRITE TO CORRECT POSITIONS
    _write_sheet("QB", 8, qb_rows)
    _write_sheet("WR", 8, wr_rows)
    _write_sheet("DB", 15, db_rows)
    _write_sheet("DE", 8, de_rows)

    update_playerstats_top15()


# =========================
# LEADERBOARD
# =========================
def update_playerstats_top15():
    sheet = _book().worksheet("PlayerStats")

    sheet.batch_clear(["A5:Z100"])

    def top(data, key):
        return sorted(data.items(), key=lambda x: x[1][key], reverse=True)[:15]

    qb_top = top(QB_DATA, "yds")
    wr_top = top(WR_DATA, "yds")
    db_top = top(DB_DATA, "int")
    de_top = top(DE_DATA, "sack")

    row = 5

    def write_section(title, players):
        nonlocal row

        sheet.update(f"A{row}", [[title]])
        row += 1

        for name, p in players:
            sheet.update(f"A{row}", [[name, p["team"]]])
            row += 1

        row += 2

    write_section("QB LEADERS", qb_top)
    write_section("WR LEADERS", wr_top)
    write_section("DB LEADERS", db_top)
    write_section("DE LEADERS", de_top)