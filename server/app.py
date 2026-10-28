"""CompE Snack Bar display server.

Serves the display page and one JSON endpoint, /api/state, built from:
  - the snack Google Sheet (via a read-only service account)
  - the club Google Calendar (via its iCal link)
  - Open-Meteo weather for Edmonton (no key needed)
With no sheet configured it runs in demo mode with sample snacks.
"""
import io
import threading
import time
import tomllib
from datetime import date, datetime, timedelta
from pathlib import Path

import requests
import segno
from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.toml"
CONFIG = tomllib.loads(CONFIG_PATH.read_text()) if CONFIG_PATH.exists() else {}

SHEET = CONFIG.get("sheet", {})
CAL = CONFIG.get("calendar", {})
WX = CONFIG.get("weather", {})
LINKTREE = CONFIG.get("display", {}).get("linktree", "https://linktr.ee/")

SAMPLE_SNACKS = [
    ("Ferrero Rocher", 0.75, 15, 5), ("Buldak", 4.00, 1, 5), ("Chips (Variety)", 0.75, 66, 10),
    ("Diet Pop (355 ml)", 1.50, 19, 5), ("Gatorade Zero (591 ml)", 2.00, 17, 5),
    ("Jones Zero (355ml)", 2.00, 5, 5), ("Gummies", 0.25, 72, 10), ("Protein Bars", 2.50, 8, 5),
    ("Granola Bars", 1.50, 44, 5), ("Ice Cream Sandwich", 1.50, 20, 5),
    ("Mini Chocolate Bars", 0.50, 71, 10), ("Ramen (Kimchi)", 3.00, 14, 5), ("Tea", 0.25, 280, 10),
    ("Monster Variety (473 ml)", 2.99, 13, 5), ("Oatmeal (Chocolate)", 0.75, 52, 5),
    ("Ritz", 0.99, 33, 5), ("Builders Protein", 3.00, 16, 5),
]


# ---------- Snacks (Google Sheet) ----------

def _num(v, default=0.0):
    try:
        return float(str(v).replace("$", "").replace(",", "").strip())
    except ValueError:
        return default


def fetch_snacks():
    if not SHEET.get("id"):
        return [{"item": n, "price": p, "stock": s, "lowAt": l, "sold": 0} for n, p, s, l in SAMPLE_SNACKS]
    import gspread  # only needed when a sheet is configured

    gc = gspread.service_account(filename=str(ROOT / SHEET.get("key_file", "robot-key.json")))
    book = gc.open_by_key(SHEET["id"])
    ws = book.worksheet(SHEET["tab"]) if SHEET.get("tab") else book.sheet1
    snacks = []
    # Only the public columns are read; cost, profit and exec-taken never leave the sheet.
    for row in ws.get_all_records():
        name = str(row.get("Item", "")).strip()
        if not name:
            continue
        snacks.append({
            "item": name,
            "price": _num(row.get("Sell Price")),
            "stock": int(_num(row.get("Stock"))),
            "lowAt": int(_num(row.get("Low Stock At"), 5)),
            "sold": int(_num(row.get("Units Sold"))),
        })
    return snacks


# ---------- Events (Google Calendar iCal) ----------

def fetch_events():
    if not CAL.get("ical_url"):
        today = date.today()
        return [
            {"date": (today + timedelta(days=3)).isoformat(), "title": "Arduino Workshop"},
            {"date": (today + timedelta(days=8)).isoformat(), "title": "Exec Meeting"},
            {"date": (today + timedelta(days=12)).isoformat(), "title": "Hack Night"},
        ]
    import icalendar
    import recurring_ical_events

    cal = icalendar.Calendar.from_ical(requests.get(CAL["ical_url"], timeout=15).content)
    start = date.today()
    events = []
    for ev in recurring_ical_events.of(cal).between(start, start + timedelta(days=60)):
        d = ev.get("DTSTART").dt
        if isinstance(d, datetime):
            d = d.astimezone().date() if d.tzinfo else d.date()
        events.append({"date": d.isoformat(), "title": str(ev.get("SUMMARY", "Event"))})
    events.sort(key=lambda e: e["date"])
    return events[:8]


# ---------- Weather (Open-Meteo) ----------

# WMO weather codes -> words the page's icon picker understands
WMO = {0: "Sunny", 1: "Mostly Sunny", 2: "Partly Cloudy", 3: "Overcast", 45: "Fog", 48: "Fog",
       51: "Drizzle", 53: "Drizzle", 55: "Drizzle", 56: "Freezing Drizzle", 57: "Freezing Drizzle",
       61: "Light Rain", 63: "Rain", 65: "Heavy Rain", 66: "Freezing Rain", 67: "Freezing Rain",
       71: "Light Snow", 73: "Snow", 75: "Heavy Snow", 77: "Snow Grains", 80: "Showers", 81: "Showers",
       82: "Heavy Showers", 85: "Snow Showers", 86: "Snow Showers", 95: "Thunderstorm",
       96: "Thunderstorm", 99: "Thunderstorm"}


def fetch_weather():
    r = requests.get("https://api.open-meteo.com/v1/forecast", timeout=15, params={
        "latitude": WX.get("lat", 53.5232), "longitude": WX.get("lon", -113.5263),
        "current": "temperature_2m,weather_code", "daily": "temperature_2m_max,weather_code",
        "timezone": "auto", "forecast_days": 4,
    }).json()
    cur, daily = r["current"], r["daily"]
    forecast = []
    for i in range(1, 4):
        day = datetime.strptime(daily["time"][i], "%Y-%m-%d").strftime("%a")
        forecast.append({"day": day, "tempC": daily["temperature_2m_max"][i],
                         "condition": WMO.get(daily["weather_code"][i], "Cloudy")})
    return {"tempC": cur["temperature_2m"], "condition": WMO.get(cur["weather_code"], "Cloudy"),
            "forecast": forecast}


# ---------- Background refresh ----------

STATE = {"snacks": [], "events": [], "weather": None, "linktree": LINKTREE,
         "source": "sheet" if SHEET.get("id") else "sample", "updated": None}
SOURCES = [  # (key, fetcher, seconds between refreshes)
    ("snacks", fetch_snacks, SHEET.get("refresh_seconds", 30)),
    ("events", fetch_events, 600),
    ("weather", fetch_weather, 900),
]


def refresher(key, fn, every):
    while True:
        try:
            STATE[key] = fn()
            if key == "snacks":
                STATE["updated"] = time.time()  # shown on screen as "synced Xs ago"
        except Exception as e:  # keep last good data on any failure
            print(f"[{key}] refresh failed: {e}", flush=True)
            time.sleep(min(every, 60))
            continue
        time.sleep(every)


for key, fn, every in SOURCES:
    threading.Thread(target=refresher, args=(key, fn, every), daemon=True).start()

# Changes whenever the page files change; the open display reloads itself when it sees a new value.
VERSION = str(max(int(f.stat().st_mtime) for f in (ROOT / "static").rglob("*") if f.is_file()))

app = FastAPI()


@app.middleware("http")
async def no_cache(request, call_next):
    # Kiosk browsers otherwise keep showing an old copy of the page after an update.
    resp = await call_next(request)
    if not request.url.path.startswith("/fonts/"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


@app.get("/api/state")
def state():
    return {k: v for k, v in STATE.items() if v is not None} | {"version": VERSION}


@app.get("/qr.svg")
def qr():
    buf = io.BytesIO()
    segno.make(LINKTREE, error="m").save(buf, kind="svg", scale=10, border=1, dark="#1a0b2e")
    return Response(buf.getvalue(), media_type="image/svg+xml")


app.mount("/", StaticFiles(directory=ROOT / "static", html=True), name="static")
