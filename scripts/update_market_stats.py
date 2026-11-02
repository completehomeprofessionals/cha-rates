"""Refresh monthly/data.json from the Market Stats database in Notion.

Needs a GitHub secret NOTION_TOKEN: a Notion internal integration key that has
been given access to the Market Stats database. Without it, the script does
nothing and the page keeps its current numbers.
"""
import json, os, sys, time, urllib.request
from datetime import date
from pathlib import Path

DATA_SOURCE_ID = "bfc17018-2122-4dce-98b8-f85bfcb6ec1d"   # Market Stats (CHA Marketing)
OUT = Path(__file__).resolve().parent.parent / "monthly" / "data.json"
FIELDS = {  # Notion property -> short key used by the page
    "New Listings": "nl", "Homes Sold": "sold", "Pending": "pend",
    "Avg Sale Price": "avg", "Median Sale Price": "med", "Sale-to-List Ratio": "stl",
    "Avg DOM (Sold)": "dom", "Median DOM (Sold)": "mdom", "Active Listings": "act",
}


def call(token, body):
    req = urllib.request.Request(
        f"https://api.notion.com/v1/data_sources/{DATA_SOURCE_ID}/query",
        data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": f"Bearer {token}", "Notion-Version": "2025-09-03",
                 "Content-Type": "application/json"})
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (401, 403, 404):
                sys.exit(f"Notion refused the request ({e.code}). Check that the key is right "
                         "and the Market Stats database is shared with the integration.")
            err = e
        except Exception as e:
            err = e
        time.sleep(10 * attempt)
    sys.exit(f"Could not reach Notion: {err}")


def value(prop):
    t = prop.get("type")
    if t == "number":
        return prop["number"]
    if t == "select":
        return (prop["select"] or {}).get("name")
    if t == "date":
        return ((prop["date"] or {}).get("start") or "")[:7] or None
    return None


def main():
    token = os.environ.get("NOTION_TOKEN", "").strip()
    if not token:
        print("No NOTION_TOKEN secret yet; leaving monthly/data.json as it is.")
        return
    rows, cursor = [], None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        res = call(token, body)
        for page in res.get("results", []):
            p = page.get("properties", {})
            market, month = value(p.get("Market", {})), value(p.get("Month", {}))
            if not market or not month:
                continue
            row = {"market": market, "month": month}
            for name, key in FIELDS.items():
                row[key] = value(p[name]) if name in p else None
            rows.append(row)
        if not res.get("has_more"):
            break
        cursor = res.get("next_cursor")
    if not rows:
        sys.exit("Notion returned no rows; leaving monthly/data.json unchanged.")
    rows.sort(key=lambda r: (r["market"], r["month"]))
    old = json.loads(OUT.read_text()) if OUT.exists() else {}
    if old.get("rows") == rows:
        print("No change.")
        return
    OUT.write_text(json.dumps({"source": "Complete Home Advisors Market Stats (Notion)",
                               "updated": date.today().isoformat(), "rows": rows}, indent=1))
    print(f"Updated monthly/data.json with {len(rows)} rows.")


if __name__ == "__main__":
    main()
