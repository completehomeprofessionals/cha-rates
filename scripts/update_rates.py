"""Refresh data.json for the Complete Home Advisors mortgage rate dashboard.

Downloads the Optimal Blue 30-year fixed rate indices from FRED (no API key
needed), then writes:
  current  - latest daily rate per loan type, plus the rate ~1 month and ~1 year earlier
  monthly  - monthly averages since 2017 (the current month is month-to-date)
Uses only the Python standard library.
"""
import csv, io, json, os, sys, time, urllib.request
from datetime import date, timedelta
from pathlib import Path

SERIES = {"conv": "OBMMIC30YF", "fha": "OBMMIFHA30YF", "va": "OBMMIVA30YF", "usda": "OBMMIUSDA30YF"}
START = "2017-01-01"
OUT = Path(__file__).resolve().parent.parent / "data.json"


def fetch(series_id):
    """Download one series. Uses the FRED API if a FRED_API_KEY secret is set,
    otherwise FRED's public CSV download. Retries because FRED can be slow."""
    key = os.environ.get("FRED_API_KEY", "").strip()
    if key:
        url = ("https://api.stlouisfed.org/fred/series/observations?series_id="
               f"{series_id}&observation_start={START}&file_type=json&api_key={key}")
    else:
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}&cosd={START}"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; cha-rate-dashboard/1.1)", "Accept": "*/*"}
    last_err = None
    for attempt in range(1, 5):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=120) as r:
                text = r.read().decode("utf-8")
            return parse_api(text) if key else parse(text)
        except Exception as e:  # network hiccup: wait and try again
            last_err = e
            print(f"{series_id}: attempt {attempt} failed ({e}); retrying...")
            time.sleep(15 * attempt)
    raise SystemExit(f"Could not download {series_id} from FRED: {last_err}")


def parse_api(text):
    out = {}
    for ob in json.loads(text)["observations"]:
        if ob["value"] not in ("", "."):
            out[date.fromisoformat(ob["date"])] = float(ob["value"])
    return out


def parse(text):
    """Return {date: float} from a FRED CSV, skipping blank / '.' values."""
    out = {}
    rows = csv.reader(io.StringIO(text))
    next(rows, None)  # header
    for row in rows:
        if len(row) < 2 or row[1].strip() in ("", "."):
            continue
        out[date.fromisoformat(row[0].strip())] = float(row[1])
    return out


def on_or_before(series, d):
    """Value on date d, or the closest earlier date with data."""
    for i in range(0, 15):
        dd = d - timedelta(days=i)
        if dd in series:
            return dd, series[dd]
    raise ValueError(f"no data near {d}")


def shift_months(d, months):
    y, m = divmod(d.month - 1 + months, 12)
    y += d.year
    m += 1
    for day in (d.day, 30, 29, 28):
        try:
            return date(y, m, day)
        except ValueError:
            continue


def build(data):
    # latest date where every series has a value
    common = set.intersection(*(set(s) for s in data.values()))
    as_of = max(common)
    month_ago = shift_months(as_of, -1)
    year_ago = shift_months(as_of, -12)

    current = {"asOf": as_of.isoformat(), "rate": {}, "monthAgo": {}, "yearAgo": {}}
    for key, s in data.items():
        current["rate"][key] = round(s[as_of], 3)
        d1, v1 = on_or_before(s, month_ago)
        d2, v2 = on_or_before(s, year_ago)
        current["monthAgo"][key] = round(v1, 3)
        current["yearAgo"][key] = round(v2, 3)
        current["monthAgoDate"], current["yearAgoDate"] = d1.isoformat(), d2.isoformat()

    months = sorted({d.strftime("%Y-%m") for d in common})
    monthly = []
    for ym in months:
        row = [ym]
        for key in SERIES:
            vals = [v for d, v in data[key].items() if d.strftime("%Y-%m") == ym]
            row.append(round(sum(vals) / len(vals), 2))
        monthly.append(row)

    return {"source": "Optimal Blue Mortgage Market Indices via FRED, Federal Reserve Bank of St. Louis",
            "series": SERIES, "current": current, "monthly": monthly}


def main():
    data = {key: fetch(sid) for key, sid in SERIES.items()}
    if any(len(v) < 100 for v in data.values()):
        sys.exit("FRED returned too little data; leaving data.json unchanged.")
    result = build(data)
    new = json.dumps(result, indent=1)
    if OUT.exists() and OUT.read_text() == new:
        print("No change.")
        return
    OUT.write_text(new)
    print("Updated data.json, as of", result["current"]["asOf"])


if __name__ == "__main__":
    main()
