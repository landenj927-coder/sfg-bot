import os
import json
import gspread
from google.oauth2.service_account import Credentials

# =========================
# GOOGLE SETUP
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
        raise Exception("GOOGLE_CREDENTIALS not set in Railway.")

    creds_dict = json.loads(creds_json)

    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    _client_cache = gspread.authorize(creds)

    return _client_cache


def _book():
    return _client().open_by_key(SPREADSHEET_ID)


# =========================
# STAT STORAGE (IN MEMORY)
# =========================
QB_DATA = {}
WR_DATA = {}
DB_DATA = {}
DE_DATA = {}


# =========================
# ADD / MERGE STATS
# =========================
def append_qb_statline(name, team, qb):
    player = QB_DATA.setdefault(name, {
        "team": team,
        "qbr": 0,
        "comp": 0,
        "yds": 0,
        "td": 0,
        "int": 0
    })

    player["qbr"] = float(qb.get("rtng", 0) or 0)
    player["comp"] += int(qb.get("comp", 0) or 0)
    player["yds"] += int(qb.get("yds", 0) or 0)
    player["td"] += int(qb.get("td", 0) or 0)
    player["int"] += int(qb.get("int", 0) or 0)


def append_wr_statline(name, team, wr):
    player = WR_DATA.setdefault(name, {
        "team": team,
        "rec": 0,
        "yds": 0,
        "td": 0,
        "fum": 0
    })

    player["rec"] += int(wr.get("catch", 0) or 0)
    player["yds"] += int(wr.get("yds", 0) or 0)
    player["td"] += int(wr.get("td", 0) or 0)
    player["fum"] += int(wr.get("fum", 0) or 0)


def append_db_statline(name, team, db):
    player = DB_DATA.setdefault(name, {
        "team": team,
        "defl": 0,
        "int": 0,
        "rtng": 0
    })

    player["defl"] += int(db.get("defl", 0) or 0)
    player["int"] += int(db.get("int", 0) or 0)
    player["rtng"] += float(db.get("rtng", 0) or 0)


def append_de_statline(name, team, de):
    player = DE_DATA.setdefault(name, {
        "team": team,
        "sack": 0,
        "safe": 0,
        "ff": 0
    })

    player["sack"] += int(de.get("sack", 0) or 0)
    player["safe"] += int(de.get("safe", 0) or 0)
    player["ff"] += int(de.get("ffum", 0) or 0)


# =========================
# BULK WRITE FUNCTION
# =========================
def _write_sheet(sheet_name, headers, rows):
    sheet = _book().worksheet(sheet_name)

    sheet.clear()

    sheet.update("A1", [headers] + rows)


# =========================
# PUSH ALL DATA (FAST)
# =========================
def commit_all_stats():
    # QB
    qb_rows = [
        [name, p["team"], p["qbr"], p["comp"], p["yds"], p["td"], p["int"]]
        for name, p in QB_DATA.items()
    ]

    # WR
    wr_rows = [
        [name, p["team"], p["rec"], p["yds"], p["td"], p["fum"]]
        for name, p in WR_DATA.items()
    ]

    # DB
    db_rows = [
        [name, p["team"], p["defl"], p["int"], p["rtng"]]
        for name, p in DB_DATA.items()
    ]

    # DE
    de_rows = [
        [name, p["team"], p["sack"], p["safe"], p["ff"]]
        for name, p in DE_DATA.items()
    ]

    _write_sheet("QB", ["Player", "Team", "QBR", "Comp", "Yds", "TD", "INT"], qb_rows)
    _write_sheet("WR", ["Player", "Team", "REC", "Yds", "TD", "FUM"], wr_rows)
    _write_sheet("DB", ["Player", "Team", "Defl", "INT", "RTNG"], db_rows)
    _write_sheet("DE", ["Player", "Team", "Sack", "Safe", "FF"], de_rows)

    update_playerstats_top15()


# =========================
# LEADERBOARD SYSTEM
# =========================
def update_playerstats_top15():
    sheet = _book().worksheet("PlayerStats")

    sheet.clear()

    def top(data, key):
        return sorted(data.items(), key=lambda x: x[1][key], reverse=True)[:15]

    qb_top = top(QB_DATA, "yds")
    wr_top = top(WR_DATA, "yds")
    db_top = top(DB_DATA, "int")
    de_top = top(DE_DATA, "sack")

    rows = [["QB LEADERS"]]
    for name, p in qb_top:
        rows.append([name, p["team"], p["yds"], p["td"]])

    rows.append([])
    rows.append(["WR LEADERS"])
    for name, p in wr_top:
        rows.append([name, p["team"], p["yds"], p["td"]])

    rows.append([])
    rows.append(["DB LEADERS"])
    for name, p in db_top:
        rows.append([name, p["team"], p["int"]])

    rows.append([])
    rows.append(["DE LEADERS"])
    for name, p in de_top:
        rows.append([name, p["team"], p["sack"]])

    sheet.update("A1", rows)