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

SERVICE_ACCOUNT_FILE = "sfg-discord-bot-50a4f11e3923.json"

# ✅ Update this after you convert the template into a Google Sheet
SPREADSHEET_ID = "1jxBjAM8BBobPgFsqwAKKl1XhhwtKPtE8D-EnFQOlrT8"

TAB_PLAYERSTATS = "PlayerStats"
TAB_QB = "QB"
TAB_WR = "WR"
TAB_DB = "DB"
TAB_DE = "DE"

DATA_START_ROW = 8  # rows 1-7 are your header/art rows

# ---------------- GLOBAL SINGLETONS ----------------
_GSPREAD_CLIENT = None
_SPREADSHEET = None
_WS_CACHE: dict[str, gspread.Worksheet] = {}


# ---------------- INTERNAL HELPERS ----------------
def _client() -> gspread.Client:
    global _GSPREAD_CLIENT
    if _GSPREAD_CLIENT is not None:
        return _GSPREAD_CLIENT

    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        raise FileNotFoundError(
            f"Service account file not found: '{SERVICE_ACCOUNT_FILE}'. "
            "Make sure it is in the same folder as your bot or use a full path."
        )

    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    _GSPREAD_CLIENT = gspread.authorize(creds)
    return _GSPREAD_CLIENT


def _book() -> gspread.Spreadsheet:
    global _SPREADSHEET
    if _SPREADSHEET is not None:
        return _SPREADSHEET
    _SPREADSHEET = _client().open_by_key(SPREADSHEET_ID)
    return _SPREADSHEET


def get_ws(title: str) -> gspread.Worksheet:
    if title in _WS_CACHE:
        return _WS_CACHE[title]

    book = _book()
    try:
        ws = book.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = book.add_worksheet(title=title, rows=2000, cols=30)

    _WS_CACHE[title] = ws
    return ws


def _now_str() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _to_int(x) -> int:
    try:
        if x is None:
            return 0
        s = str(x).strip()
        if s == "":
            return 0
        return int(float(s))
    except Exception:
        return 0


def _to_float(x) -> float:
    try:
        if x is None:
            return 0.0
        s = str(x).strip()
        if s == "":
            return 0.0
        return float(s)
    except Exception:
        return 0.0


def _safe(row: list, idx: int) -> str:
    return row[idx] if idx < len(row) else ""


def _append_rows(ws: gspread.Worksheet, rows: list[list], value_input_option: str = "USER_ENTERED") -> None:
    if not rows:
        return
    try:
        ws.append_rows(rows, value_input_option=value_input_option)
    except Exception:
        for r in rows:
            ws.append_row(r, value_input_option=value_input_option)


# ---------------- SHEET SETUP ----------------
def ensure_sheets_exist():
    """
    Just ensures tabs exist. Template already has formatting.
    """
    get_ws(TAB_PLAYERSTATS)
    get_ws(TAB_QB)
    get_ws(TAB_WR)
    get_ws(TAB_DB)
    get_ws(TAB_DE)


# ---------------- APPEND STATLINES ----------------
def append_qb_statline(game_id: int, discord_id: int, player: str, team: str,
                       qbr: float, comp: int, yds: int, tds: int, ints: int):
    ws = get_ws(TAB_QB)
    ws.append_row([
        player,     # Player
        team,       # Team
        qbr,        # QBR
        comp,       # Completions
        yds,        # Pass Yds
        tds,        # Pass TDs
        ints        # INTs
    ], value_input_option="USER_ENTERED")


def append_wr_statline(game_id: int, discord_id: int, player: str, team: str,
                       rec: int, yds: int, tds: int, fum: int):
    ws = get_ws(TAB_WR)
    ws.append_row([
        player,
        team,
        rec,
        yds,
        tds,
        fum
    ], value_input_option="USER_ENTERED")


def append_db_statline(game_id: int, discord_id: int, player: str, team: str,
                       swats: int, ints: int, dbr: float):
    ws = get_ws(TAB_DB)
    ws.append_row([
        player,
        team,
        swats,
        ints,
        dbr
    ], value_input_option="USER_ENTERED")


def append_de_statline(game_id: int, discord_id: int, player: str, team: str,
                       sacks: int, safeties: int, ff: int):
    ws = get_ws(TAB_DE)
    ws.append_row([
        player,
        team,
        sacks,
        safeties,
        ff
    ], value_input_option="USER_ENTERED")


# ---------------- TOP 15 DASHBOARD ----------------
def update_playerstats_top15():
    """
    Reads QB/WR/DB/DE tabs and writes Top 15 blocks into PlayerStats.
    Sorting rules:
      QB: avg QBR (desc), then total YDS
      WR: total YDS (desc), then total REC
      DB: avg DBR (desc), then total INTS
      DE: total SACKS (desc), then total FF
    """
    book = _book()
    ws_ps = get_ws(TAB_PLAYERSTATS)

    # ---------- QB ----------
    ws_qb = get_ws(TAB_QB)
    qb_rows = ws_qb.get_all_values()[DATA_START_ROW-1:]  # row8 -> index7
    qb_agg = defaultdict(lambda: {"player":"", "team":"", "qbr_sum":0.0, "qbr_n":0, "comp":0, "yds":0, "tds":0, "ints":0})
    for r in qb_rows:
        player = _safe(r, 3).strip()
        if not player:
            continue
        did = _safe(r, 2).strip() or player  # fallback key
        qb_agg[did]["player"] = player
        qb_agg[did]["team"] = _safe(r, 4).strip()
        qb_agg[did]["qbr_sum"] += _to_float(_safe(r, 5))
        qb_agg[did]["qbr_n"] += 1
        qb_agg[did]["comp"] += _to_int(_safe(r, 6))
        qb_agg[did]["yds"] += _to_int(_safe(r, 7))
        qb_agg[did]["tds"] += _to_int(_safe(r, 8))
        qb_agg[did]["ints"] += _to_int(_safe(r, 9))

    qb_list = []
    for v in qb_agg.values():
        avg_qbr = (v["qbr_sum"] / v["qbr_n"]) if v["qbr_n"] else 0.0
        qb_list.append([v["player"], v["team"], round(avg_qbr, 2), v["comp"], v["yds"], v["tds"], v["ints"]])
    qb_list.sort(key=lambda x: (x[2], x[4]), reverse=True)
    qb_top = qb_list[:15]

    # ---------- WR ----------
    ws_wr = get_ws(TAB_WR)
    wr_rows = ws_wr.get_all_values()[DATA_START_ROW-1:]
    wr_agg = defaultdict(lambda: {"player":"", "team":"", "rec":0, "yds":0, "tds":0, "fum":0})
    for r in wr_rows:
        player = _safe(r, 3).strip()
        if not player:
            continue
        did = _safe(r, 2).strip() or player
        wr_agg[did]["player"] = player
        wr_agg[did]["team"] = _safe(r, 4).strip()
        wr_agg[did]["rec"] += _to_int(_safe(r, 5))
        wr_agg[did]["yds"] += _to_int(_safe(r, 6))
        wr_agg[did]["tds"] += _to_int(_safe(r, 7))
        wr_agg[did]["fum"] += _to_int(_safe(r, 8))

    wr_list = [[v["player"], v["team"], v["rec"], v["yds"], v["tds"], v["fum"]] for v in wr_agg.values()]
    wr_list.sort(key=lambda x: (x[3], x[2]), reverse=True)
    wr_top = wr_list[:15]

    # ---------- DB ----------
    ws_db = get_ws(TAB_DB)
    db_rows = ws_db.get_all_values()[DATA_START_ROW-1:]
    db_agg = defaultdict(lambda: {"player":"", "team":"", "swats":0, "ints":0, "dbr_sum":0.0, "dbr_n":0})
    for r in db_rows:
        player = _safe(r, 3).strip()
        if not player:
            continue
        did = _safe(r, 2).strip() or player
        db_agg[did]["player"] = player
        db_agg[did]["team"] = _safe(r, 4).strip()
        db_agg[did]["swats"] += _to_int(_safe(r, 5))
        db_agg[did]["ints"] += _to_int(_safe(r, 6))
        db_agg[did]["dbr_sum"] += _to_float(_safe(r, 7))
        db_agg[did]["dbr_n"] += 1

    db_list = []
    for v in db_agg.values():
        avg_dbr = (v["dbr_sum"] / v["dbr_n"]) if v["dbr_n"] else 0.0
        db_list.append([v["player"], v["team"], v["swats"], v["ints"], round(avg_dbr, 2)])
    db_list.sort(key=lambda x: (x[4], x[3]), reverse=True)
    db_top = db_list[:15]

    # ---------- DE ----------
    ws_de = get_ws(TAB_DE)
    de_rows = ws_de.get_all_values()[DATA_START_ROW-1:]
    de_agg = defaultdict(lambda: {"player":"", "team":"", "sacks":0, "safeties":0, "ff":0})
    for r in de_rows:
        player = _safe(r, 3).strip()
        if not player:
            continue
        did = _safe(r, 2).strip() or player
        de_agg[did]["player"] = player
        de_agg[did]["team"] = _safe(r, 4).strip()
        de_agg[did]["sacks"] += _to_int(_safe(r, 5))
        de_agg[did]["safeties"] += _to_int(_safe(r, 6))
        de_agg[did]["ff"] += _to_int(_safe(r, 7))

    de_list = [[v["player"], v["team"], v["sacks"], v["safeties"], v["ff"]] for v in de_agg.values()]
    de_list.sort(key=lambda x: (x[2], x[4]), reverse=True)
    de_top = de_list[:15]

    # ---------- WRITE TO PLAYERSTATS ----------
    def pad(rows, n, cols):
        out = rows[:n]
        while len(out) < n:
            out.append([""] * cols)
        return out

    qb_block = pad(qb_top, 15, 7)  # A8:G22
    wr_block = pad(wr_top, 15, 6)  # I8:N22
    db_block = pad(db_top, 15, 5)  # A26:E40
    de_block = pad(de_top, 15, 5)  # I26:M40

    ws_ps.update("A8:G22", qb_block, value_input_option="USER_ENTERED")
    ws_ps.update("I8:N22", wr_block, value_input_option="USER_ENTERED")
    ws_ps.update("A26:E40", db_block, value_input_option="USER_ENTERED")
    ws_ps.update("I26:M40", de_block, value_input_option="USER_ENTERED")


if __name__ == "__main__":
    book = _book()
    print("Opened spreadsheet:", book.title)
    ensure_sheets_exist()
    print("Tabs ensured.")
