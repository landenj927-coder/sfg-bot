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
# CONNECT TO GOOGLE SHEETS (ENV VERSION)
# =========================
def _client():
    global _GSPREAD_CLIENT

    if _GSPREAD_CLIENT:
        return _GSPREAD_CLIENT

    creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))

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
def append_qb_statline(player):
    ws = _book().worksheet("QB")

    ws.append_row([
        player.get("name"),
        player.get("team"),
        player["qb"].get("rtng", 0),
        player["qb"].get("comp", 0),
        player["qb"].get("yds", 0),
        player["qb"].get("td", 0),
        player["qb"].get("int", 0),
    ])


def append_wr_statline(player):
    ws = _book().worksheet("WR")

    ws.append_row([
        player.get("name"),
        player.get("team"),
        player["wr"].get("rec", 0),
        player["wr"].get("yds", 0),
        player["wr"].get("td", 0),
        player["wr"].get("fum", 0),
    ])


def append_db_statline(player):
    ws = _book().worksheet("DB")

    ws.append_row([
        player.get("name"),
        player.get("team"),
        player["db"].get("defl", 0),
        player["db"].get("int", 0),
        player["db"].get("rtng", 0),
    ])


def append_de_statline(player):
    ws = _book().worksheet("DE")

    ws.append_row([
        player.get("name"),
        player.get("team"),
        player["def"].get("sack", 0),
        player["def"].get("safe", 0),
        player["def"].get("ffum", 0),
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

    # get all values
    qb_data = qb_ws.get_all_values()[1:]
    wr_data = wr_ws.get_all_values()[1:]
    db_data = db_ws.get_all_values()[1:]
    de_data = de_ws.get_all_values()[1:]

    # sort (example logic — can upgrade later)
    qb_sorted = sorted(qb_data, key=lambda x: float(x[4]), reverse=True)[:15]
    wr_sorted = sorted(wr_data, key=lambda x: float(x[3]), reverse=True)[:15]
    db_sorted = sorted(db_data, key=lambda x: float(x[2]), reverse=True)[:15]
    de_sorted = sorted(de_data, key=lambda x: float(x[2]), reverse=True)[:15]

    ws.clear()

    # QB section
    ws.append_row(["QB LEADERS"])
    for row in qb_sorted:
        ws.append_row(row)

    ws.append_row([""])

    # WR section
    ws.append_row(["WR LEADERS"])
    for row in wr_sorted:
        ws.append_row(row)

    ws.append_row([""])

    # DB section
    ws.append_row(["DB LEADERS"])
    for row in db_sorted:
        ws.append_row(row)

    ws.append_row([""])

    # DE section
    ws.append_row(["DE LEADERS"])
    for row in de_sorted:
        ws.append_row(row)