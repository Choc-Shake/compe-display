"""Guided setup: asks for the sheet link, robot key, calendar and Linktree, then tests the connection.

Run with:  .venv/bin/python -m server.configure
Only asks about things that are missing; pass --all to change everything.
"""
import glob
import json
import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config.toml"
KEY = ROOT / "robot-key.json"

PINK, TEAL, RED, DIM, END = "\033[1;35m", "\033[1;36m", "\033[1;31m", "\033[2m", "\033[0m"


def ask(prompt, current=""):
    hint = f" {DIM}[Enter keeps: {current}]{END}" if current else f" {DIM}[Enter to skip]{END}"
    try:
        v = input(f"{prompt}{hint}\n> ").strip()
    except EOFError:
        v = ""
    return v or current


def get(text, section, key):
    m = re.search(rf"^\[{section}\][^\[]*?^{key}\s*=\s*\"([^\"]*)\"", text, re.M | re.S)
    return m.group(1) if m else ""


def put(text, section, key, value):
    value = value.replace("\\", "\\\\").replace('"', '\\"')
    return re.sub(rf"(^\[{section}\][^\[]*?^{key}\s*=\s*)\"[^\"]*\"",
                  lambda m: f'{m.group(1)}"{value}"', text, count=1, flags=re.M | re.S)


def robot_email():
    try:
        return json.loads(KEY.read_text())["client_email"]
    except Exception:
        return ""


def find_key():
    """Copy a downloaded robot key into place. Offers the newest service-account file in Downloads."""
    found = []
    for f in sorted(glob.glob(os.path.expanduser("~/Downloads/*.json")), key=os.path.getmtime, reverse=True):
        try:
            if json.loads(Path(f).read_text()).get("type") == "service_account":
                found.append(f)
        except Exception:
            pass
    if found:
        print(f"Found a robot key in Downloads: {TEAL}{os.path.basename(found[0])}{END}")
        if ask("Use it? (y/n)", "y").lower().startswith("y"):
            shutil.copy(found[0], KEY)
            return
    path = ask("Drag the robot key .json file into this window (or paste its path)")
    path = os.path.expanduser(path.strip().strip("'\"").replace("\\ ", " "))
    if path and os.path.isfile(path):
        shutil.copy(path, KEY)
    elif path:
        print(f"{RED}Couldn't find that file — skipping. Run setup again later.{END}")


def test_sheet(sheet_id, tab):
    import gspread

    try:
        book = gspread.service_account(filename=str(KEY)).open_by_key(sheet_id)
        ws = book.worksheet(tab) if tab else book.sheet1
        n = len([r for r in ws.get_all_records() if str(r.get("Item", "")).strip()])
        print(f"{TEAL}✔ Connected! Reading {n} snacks from the '{ws.title}' tab.{END}")
        return True
    except gspread.exceptions.WorksheetNotFound:
        print(f"{RED}✘ No tab named '{tab}'. Tabs in this sheet: {', '.join(w.title for w in book.worksheets())}{END}")
    except Exception as e:
        msg = str(e.__cause__ or e)
        if "has not been used" in msg or "disabled" in msg:
            print(f"{RED}✘ The Google Sheets/Drive API is off for the robot's project.{END}\n"
                  "  Turn on both at console.cloud.google.com → APIs & Services → Enable APIs.")
        elif isinstance(e, PermissionError) or "403" in msg or "PERMISSION" in msg:
            print(f"{RED}✘ The robot isn't allowed to open the sheet.{END}\n"
                  f"  Share the sheet (Viewer) with: {TEAL}{robot_email()}{END}")
        elif "404" in msg:
            print(f"{RED}✘ No sheet found with that link — double-check it.{END}")
        else:
            print(f"{RED}✘ Couldn't read the sheet: {msg[:200]}{END}")
    return False


def main():
    everything = "--all" in sys.argv
    if not CONFIG.exists():
        shutil.copy(ROOT / "config.example.toml", CONFIG)
    text = CONFIG.read_text()
    print(f"\n{PINK}━━ CompE Display setup ━━{END}")

    # 1. Robot key
    if everything or not KEY.exists():
        print(f"\n{PINK}1. Robot key{END} — the .json file you downloaded from Google Cloud")
        find_key()
    if KEY.exists():
        print(f"Robot account: {TEAL}{robot_email()}{END}")

    # 2. Snack sheet
    sheet_id = get(text, "sheet", "id")
    if everything or not sheet_id:
        print(f"\n{PINK}2. Snack spreadsheet{END} — paste the link from your browser's address bar")
        link = ask("Sheet link", sheet_id)
        m = re.search(r"/d/([a-zA-Z0-9_-]{20,})", link)
        sheet_id = m.group(1) if m else link
        text = put(text, "sheet", "id", sheet_id)
    tab = get(text, "sheet", "tab")
    if not tab:  # older installs left this blank, which reads the Sales tab
        tab = "Inventory"
        text = put(text, "sheet", "tab", tab)
    if everything:
        tab = ask("Name of the tab with the snack list", tab)
        text = put(text, "sheet", "tab", tab)

    # 3. Calendar
    ical = get(text, "calendar", "ical_url")
    if everything or not ical:
        print(f"\n{PINK}3. Club calendar{END} — Google Calendar → ⋮ → Settings and sharing → "
              "'Secret address in iCal format'")
        text = put(text, "calendar", "ical_url", ask("Calendar address", ical))

    # 4. Linktree
    if everything:
        print(f"\n{PINK}4. Linktree{END} (for the QR code)")
        text = put(text, "display", "linktree", ask("Linktree link", get(text, "display", "linktree")))

    CONFIG.write_text(text)

    print(f"\n{PINK}Testing the snack sheet…{END}")
    if not sheet_id:
        print("Skipped — no sheet yet, so the display shows sample snacks.")
    elif not KEY.exists():
        print(f"{RED}✘ No robot key yet, so the display shows sample snacks.{END}")
    elif not test_sheet(sheet_id, tab):
        print(f"\nFix that, then run setup again:  {TEAL}~/compe-display/setup{END}")


if __name__ == "__main__":
    main()
