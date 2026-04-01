import os
import datetime
from collections import defaultdict

import gspread
from google.oauth2.service_account import Credentials

print("STATS_SHEET FILE LOADED")

# ---------------- CONFIG ----------------
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

SERVICE_ACCOUNT_FILE = "sfg-discord-bot-d8bb550b91fa.json"
SPREADSHEET_ID = "1jxBjAM8BBobPgFsqwAKKl1XhhwtKPtE8D-EnFQOlrT8"

TAB_PLAYERSTATS = "PlayerStats"
TAB_QB = "QB"
TAB_WR = "WR"
TAB_DB = "DB"
TAB_DE = "DE"
TAB_REPORTS = "Reports"

DATA_START_ROW = 8

_GSPREAD_CLIENT = None
_SPREADSHEET = None
_WS_CACHE = {}


# ---------------- CONNECTION ----------------
def _client():
    global _GSPREAD_CLIENT
    if _GSPREAD_CLIENT:
        return _GSPREAD_CLIENT

    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    _GSPREAD_CLIENT = gspread.authorize(creds)
    return _GSPREAD_CLIENT


def _book():
    global _SPREADSHEET
    if _SPREADSHEET:
        return _SPREADSHEET

    _SPREADSHEET = _client().open_by_key(SPREADSHEET_ID)
    return _SPREADSHEET


def get_ws(name):
    if name in _WS_CACHE:
        return _WS_CACHE[name]

    ws = _book().worksheet(name)
    _WS_CACHE[name] = ws
    return ws


# ---------------- STAT APPEND (UPDATED) ----------------

def append_qb_statline(name, team, qb):
    ws = get_ws(TAB_QB)

    ws.append_row([
        name,
        team,
        qb.get("rtng", 0),
        qb.get("comp", 0),
        qb.get("yds", 0),
        qb.get("td", 0),
        qb.get("int", 0)
    ])


def append_wr_statline(name, team, wr):
    ws = get_ws(TAB_WR)

    ws.append_row([
        name,
        team,
        wr.get("catch", 0),
        wr.get("yds", 0),
        wr.get("td", 0),
        wr.get("fum", 0)
    ])


def append_db_statline(name, team, db):
    ws = get_ws(TAB_DB)

    ws.append_row([
        name,
        team,
        db.get("defl", 0),
        db.get("int", 0),
        db.get("rtng", 0)
    ])


def append_de_statline(name, team, de):
    ws = get_ws(TAB_DE)

    ws.append_row([
        name,
        team,
        de.get("sack", 0),
        de.get("safe", 0),
        de.get("ffum", 0)
    ])


# ---------------- TOP 15 SYSTEM (UNCHANGED CORE) ----------------

def update_playerstats_top15():
    book = _book()
    ws_ps = get_ws(TAB_PLAYERSTATS)

    # QB
    qb_rows = get_ws(TAB_QB).get_all_values()[DATA_START_ROW-1:]
    qb_agg = defaultdict(lambda: {"player":"", "team":"", "qbr_sum":0, "n":0, "comp":0, "yds":0, "tds":0, "ints":0})

    for r in qb_rows:
        if not r:
            continue

        player = r[0]
        team = r[1]

        qb_agg[player]["player"] = player
        qb_agg[player]["team"] = team
        qb_agg[player]["qbr_sum"] += float(r[2])
        qb_agg[player]["n"] += 1
        qb_agg[player]["comp"] += int(r[3])
        qb_agg[player]["yds"] += int(r[4])
        qb_agg[player]["tds"] += int(r[5])
        qb_agg[player]["ints"] += int(r[6])

    qb_list = []
    for v in qb_agg.values():
        avg = v["qbr_sum"] / v["n"] if v["n"] else 0
        qb_list.append([v["player"], v["team"], round(avg,2), v["comp"], v["yds"], v["tds"], v["ints"]])

    qb_list.sort(key=lambda x: (x[2], x[4]), reverse=True)

    # WR
    wr_rows = get_ws(TAB_WR).get_all_values()[DATA_START_ROW-1:]
    wr_list = [r for r in wr_rows if r]
    wr_list.sort(key=lambda x: (int(x[3]), int(x[2])), reverse=True)

    # DB
    db_rows = get_ws(TAB_DB).get_all_values()[DATA_START_ROW-1:]
    db_list = [r for r in db_rows if r]
    db_list.sort(key=lambda x: (float(x[4]), int(x[3])), reverse=True)

    # DE
    de_rows = get_ws(TAB_DE).get_all_values()[DATA_START_ROW-1:]
    de_list = [r for r in de_rows if r]
    de_list.sort(key=lambda x: (int(x[2]), int(x[4])), reverse=True)

    # WRITE TOP 15
    ws_ps.update("A8:G22", qb_list[:15])
    ws_ps.update("I8:N22", wr_list[:15])
    ws_ps.update("A26:E40", db_list[:15])
    ws_ps.update("I26:M40", de_list[:15])


# ---------------- REPORT TRACKING ----------------

def report_already_processed(report_id):
    ws = get_ws(TAB_REPORTS)
    return report_id in [r[0] for r in ws.get_all_values()[1:]]


def log_processed_report(report_id, game_id, user_id, summary):
    ws = get_ws(TAB_REPORTS)

    ws.append_row([
        report_id,
        game_id,
        user_id,
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        summary
    ])