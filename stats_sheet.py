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

_client_cache = None
_book_cache = None


# =========================
# SAFE CONVERSIONS
# =========================
def _to_int(v):
    try:
        if not v or str(v).strip() == "":
            return 0
        return int(float(v))
    except:
        return 0


def _to_float(v):
    try:
        if not v or str(v).strip() == "":
            return 0.0
        return float(v)
    except:
        return 0.0


# =========================
# GOOGLE CONNECTION
# =========================
def _client():
    global _client_cache

    if _client_cache:
        return _client_cache

    raw = os.getenv("GOOGLE_CREDENTIALS")
    if not raw:
        raise ValueError("GOOGLE_CREDENTIALS missing")

    creds_dict = json.loads(raw)

    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=SCOPES
    )

    _client_cache = gspread.authorize(creds)
    return _client_cache


def _book():
    global _book_cache

    if _book_cache:
        return _book_cache

    _book_cache = _client().open_by_key(SPREADSHEET_ID)
    return _book_cache


# =========================
# ENSURE SHEETS
# =========================
def ensure_sheets():
    book = _book()
    names = ["QB", "WR", "DB", "DE", "PlayerStats"]

    existing = [ws.title for ws in book.worksheets()]

    for n in names:
        if n not in existing:
            book.add_worksheet(title=n, rows=1000, cols=20)


# =========================
# CORE UPDATE FUNCTION
# =========================
def _update_or_insert(ws, name, team, stat_values):
    data = ws.get_all_values()

    headers = data[0] if data else []

    # find player row
    for i, row in enumerate(data[1:], start=2):
        if row and row[0] == name:
            # update existing row (aggregate)
            new_row = [name, team]

            for j in range(len(stat_values)):
                old = _to_float(row[j + 2]) if len(row) > j + 2 else 0
                new = _to_float(stat_values[j])
                new_row.append(old + new)

            ws.update(f"A{i}", [new_row])
            return

    # insert new row
    ws.append_row([name, team] + stat_values)


# =========================
# APPEND (NOW AGGREGATED)
# =========================
def append_qb_statline(name, team, qb):
    ws = _book().worksheet("QB")

    stats = [
        qb.get("rtng", 0),
        qb.get("comp", 0),
        qb.get("yds", 0),
        qb.get("td", 0),
        qb.get("int", 0),
    ]

    _update_or_insert(ws, name, team, stats)


def append_wr_statline(name, team, wr):
    ws = _book().worksheet("WR")

    stats = [
        wr.get("catch", 0),
        wr.get("yds", 0),
        wr.get("td", 0),
        wr.get("fum", 0),
    ]

    _update_or_insert(ws, name, team, stats)


def append_db_statline(name, team, db):
    ws = _book().worksheet("DB")

    stats = [
        db.get("defl", 0),
        db.get("int", 0),
        db.get("rtng", 0),
    ]

    _update_or_insert(ws, name, team, stats)


def append_de_statline(name, team, de):
    ws = _book().worksheet("DE")

    stats = [
        de.get("sack", 0),
        de.get("safe", 0),
        de.get("ffum", 0),
    ]

    _update_or_insert(ws, name, team, stats)


# =========================
# TRUE LEADERBOARD SYSTEM
# =========================
def update_playerstats_top15():
    book = _book()
    ws = book.worksheet("PlayerStats")

    qb_ws = book.worksheet("QB")
    wr_ws = book.worksheet("WR")
    db_ws = book.worksheet("DB")
    de_ws = book.worksheet("DE")

    qb = qb_ws.get_all_values()[1:]
    wr = wr_ws.get_all_values()[1:]
    db = db_ws.get_all_values()[1:]
    de = de_ws.get_all_values()[1:]

    qb = [r for r in qb if any(r)]
    wr = [r for r in wr if any(r)]
    db = [r for r in db if any(r)]
    de = [r for r in de if any(r)]

    # 🔥 REAL METRICS
    qb_sorted = sorted(qb, key=lambda x: _to_float(x[4]), reverse=True)[:15]  # yards
    wr_sorted = sorted(wr, key=lambda x: _to_float(x[3]), reverse=True)[:15]  # yards
    db_sorted = sorted(db, key=lambda x: _to_float(x[2]), reverse=True)[:15]  # swats
    de_sorted = sorted(de, key=lambda x: _to_float(x[2]), reverse=True)[:15]  # sacks

    ws.clear()

    row = 1

    def section(title, headers, data):
        nonlocal row

        ws.update(f"A{row}", [[title]])
        row += 1

        ws.update(f"A{row}", [headers])
        row += 1

        for r in data:
            ws.update(f"A{row}", [r])
            row += 1

        row += 2

    section("QB LEADERS", ["Player","Team","QBR","COMP","YDS","TDS","INTS"], qb_sorted)
    section("WR LEADERS", ["Player","Team","REC","YDS","TDS","FUM"], wr_sorted)
    section("DB LEADERS", ["Player","Team","SWATS","INTS","DBR"], db_sorted)
    section("DE LEADERS", ["Player","Team","SACKS","SAFETIES","FF"], de_sorted)