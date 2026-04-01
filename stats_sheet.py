import os
import json
import gspread
from google.oauth2.service_account import Credentials

print("STATS_SHEET FILE LOADED")

# =========================
# CONFIG
# =========================
SPREADSHEET_ID = "1jxBjAM8BBobPgFsqwAKKl1XhhwtKPtE8D-EnFQOlrT8"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_GSPREAD_CLIENT = None
_SPREADSHEET = None


# =========================
# SAFE NUMBER HELPERS
# =========================
def _to_int(value):
    try:
        if value is None or str(value).strip() == "":
            return 0
        return int(float(value))
    except Exception:
        return 0


def _to_float(value):
    try:
        if value is None or str(value).strip() == "":
            return 0.0
        return float(value)
    except Exception:
        return 0.0


# =========================
# CONNECT TO GOOGLE SHEETS
# =========================
def _client():
    global _GSPREAD_CLIENT

    if _GSPREAD_CLIENT:
        return _GSPREAD_CLIENT

    raw = os.getenv("GOOGLE_CREDENTIALS")
    if not raw:
        raise ValueError("GOOGLE_CREDENTIALS environment variable is missing.")

    creds_dict = json.loads(raw)

    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=SCOPES
    )

    _GSPREAD_CLIENT = gspread.authorize(creds)
    return _GSPREAD_CLIENT


def _book():
    global _SPREADSHEET

    if _SPREADSHEET:
        return _SPREADSHEET

    _SPREADSHEET = _client().open_by_key(SPREADSHEET_ID)
    return _SPREADSHEET


# =========================
# ENSURE SHEETS EXIST
# =========================
def ensure_sheets():
    book = _book()
    required = ["QB", "WR", "DB", "DE", "PlayerStats"]

    existing = [ws.title for ws in book.worksheets()]

    for name in required:
        if name not in existing:
            book.add_worksheet(title=name, rows=1000, cols=20)


# =========================
# APPEND STAT FUNCTIONS
# =========================
def append_qb_statline(name, team, qb):
    ws = _book().worksheet("QB")
    ws.append_row([
        name,
        team,
        qb.get("rtng", 0),
        qb.get("comp", 0),
        qb.get("yds", 0),
        qb.get("td", 0),
        qb.get("int", 0),
    ])


def append_wr_statline(name, team, wr):
    ws = _book().worksheet("WR")
    ws.append_row([
        name,
        team,
        wr.get("catch", 0),
        wr.get("yds", 0),
        wr.get("td", 0),
        wr.get("fum", 0),
    ])


def append_db_statline(name, team, db):
    ws = _book().worksheet("DB")
    ws.append_row([
        name,
        team,
        db.get("defl", 0),
        db.get("int", 0),
        db.get("rtng", 0),
    ])


def append_de_statline(name, team, de):
    ws = _book().worksheet("DE")
    ws.append_row([
        name,
        team,
        de.get("sack", 0),
        de.get("safe", 0),
        de.get("ffum", 0),
    ])


# =========================
# UPDATE TOP 15 LEADERBOARD
# =========================
def update_playerstats_top15():
    book = _book()
    ws = book.worksheet("PlayerStats")

    qb_ws = book.worksheet("QB")
    wr_ws = book.worksheet("WR")
    db_ws = book.worksheet("DB")
    de_ws = book.worksheet("DE")

    qb_data = [row for row in qb_ws.get_all_values()[1:] if row and any(cell.strip() for cell in row)]
    wr_data = [row for row in wr_ws.get_all_values()[1:] if row and any(cell.strip() for cell in row)]
    db_data = [row for row in db_ws.get_all_values()[1:] if row and any(cell.strip() for cell in row)]
    de_data = [row for row in de_ws.get_all_values()[1:] if row and any(cell.strip() for cell in row)]

    qb_sorted = sorted(qb_data, key=lambda x: _to_float(x[4] if len(x) > 4 else 0), reverse=True)[:15]
    wr_sorted = sorted(wr_data, key=lambda x: _to_float(x[3] if len(x) > 3 else 0), reverse=True)[:15]
    db_sorted = sorted(db_data, key=lambda x: _to_float(x[2] if len(x) > 2 else 0), reverse=True)[:15]
    de_sorted = sorted(de_data, key=lambda x: _to_float(x[2] if len(x) > 2 else 0), reverse=True)[:15]

    ws.clear()

    ws.append_row(["QB LEADERS"])
    ws.append_row(["Player", "Team", "QBR", "COMP", "YDS", "TDS", "INTS"])
    for row in qb_sorted:
        ws.append_row(row)

    ws.append_row([""])
    ws.append_row(["WR LEADERS"])
    ws.append_row(["Player", "Team", "REC", "YDS", "TDS", "FUM"])
    for row in wr_sorted:
        ws.append_row(row)

    ws.append_row([""])
    ws.append_row(["DB LEADERS"])
    ws.append_row(["Player", "Team", "SWATS", "INTS", "DBR"])
    for row in db_sorted:
        ws.append_row(row)

    ws.append_row([""])
    ws.append_row(["DE LEADERS"])
    ws.append_row(["Player", "Team", "SACKS", "SAFETIES", "FF"])
    for row in de_sorted:
        ws.append_row(row)