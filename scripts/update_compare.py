"""Refresh compare/data.json: Realtor.com monthly housing inventory data, via FRED,
for Lawrence (metro), Kansas City (metro), Johnson County KS and the U.S.
Same source and definitions for all four places, so they compare fairly.
"""
import csv, io, json, sys, time, urllib.request
from datetime import date
from pathlib import Path

START = "2017-01-01"
OUT = Path(__file__).resolve().parent.parent / "compare" / "data.json"
GEOS = {"law": "29940", "kc": "28140", "jo": "20091", "us": "US"}
METRICS = {  # key -> FRED series prefix (Realtor.com)
    "price": "MEDLISPRI",   # median listing price
    "active": "ACTLISCOU",  # active listings
    "new": "NEWLISCOU",     # new listings
    "pending": "PENLISCOU", # pending listings
    "dom": "MEDDAYONMAR",   # median days on market
    "cuts": "PRIREDCOU",    # listings with a price reduction
}


def fetch(series_id):
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}&cosd={START}"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; cha-rate-dashboard/1.1)", "Accept": "*/*"}
    err = None
    for attempt in range(1, 5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=120) as r:
                text = r.read().decode("utf-8")
            out = {}
            rows = csv.reader(io.StringIO(text))
            next(rows, None)
            for row in rows:
                if len(row) >= 2 and row[1].strip() not in ("", "."):
                    out[row[0][:7]] = float(row[1])
            return out
        except Exception as e:
            err = e
            print(f"{series_id}: attempt {attempt} failed ({e}); retrying...")
            time.sleep(15 * attempt)
    sys.exit(f"Could not download {series_id}: {err}")


def main():
    series = {m: {g: fetch(p + code) for g, code in GEOS.items()} for m, p in METRICS.items()}
    months = sorted(set().union(*(s.keys() for g in series.values() for s in g.values())))
    if len(months) < 24:
        sys.exit("Too little data returned; leaving compare/data.json unchanged.")
    table = {g: [[m] + [series[k][g].get(m) for k in METRICS] for m in months] for g in GEOS}
    result = {"source": "Realtor.com Economic Research, via FRED (Federal Reserve Bank of St. Louis)",
              "columns": ["month"] + list(METRICS), "latest": months[-1], "geos": table}
    new = json.dumps(result, separators=(",", ":"))
    if OUT.exists() and json.loads(OUT.read_text()).get("geos") == result["geos"]:
        print("No change.")
        return
    OUT.write_text(new)
    print("Updated compare/data.json through", months[-1])


if __name__ == "__main__":
    main()
