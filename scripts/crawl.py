#!/usr/bin/env python3
"""Enumerate the VS Code Marketplace by category and record REAL install counts.

Why this dataset is worth making: every "what sells" dataset this operation has published
so far leans on rating counts as a demand *proxy*. The Marketplace publishes install counts
directly, so this measures the thing itself. Nobody publishes a comprehensive dump of it.

It also feeds V7 directly. The first extension went into a niche picked by guesswork and
turned out to be thin; the second was picked from a 12-term search scan that proved to be
badly polluted (the top "dotenv" hits were language packs). Category enumeration is the
honest version of that measurement: it is the marketplace's own taxonomy, not a relevance
algorithm's opinion.

Politeness: one request at a time, a real gap between pages, and it stops on repeated
failures rather than hammering. Read-only public API, no auth.
"""
import json, sys, time, urllib.error, urllib.request

URL = "https://marketplace.visualstudio.com/_apis/public/gallery/extensionquery"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/126.0 Safari/537.36")
PAGE = 100
FLAGS = 914          # statistics + versions
GAP = 0.6

CATEGORIES = [
    "Programming Languages", "Snippets", "Linters", "Themes", "Debuggers", "Formatters",
    "Keymaps", "SCM Providers", "Other", "Extension Packs", "Language Packs",
    "Data Science", "Machine Learning", "Visualization", "Notebooks", "Education",
    "Testing", "AI", "Chat",
]


def query(category, page):
    body = {"filters": [{"criteria": [
                {"filterType": 5, "value": category},
                {"filterType": 12, "value": "4096"},     # exclude unpublished
            ], "pageNumber": page, "pageSize": PAGE, "sortBy": 4, "sortOrder": 2}],
            "flags": FLAGS}
    req = urllib.request.Request(URL, method="POST", data=json.dumps(body).encode(),
        headers={"Accept": "application/json;api-version=7.2-preview.1",
                 "Content-Type": "application/json", "User-Agent": UA})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt < 3:
                time.sleep(8 * (attempt + 1)); continue
            raise
        except Exception:
            if attempt < 3:
                time.sleep(5 * (attempt + 1)); continue
            raise
    return None


def row(e, category):
    st = {s["statisticName"]: s["value"] for s in e.get("statistics", [])}
    ver = (e.get("versions") or [{}])[0]
    return {
        "id": e["publisher"]["publisherName"] + "." + e["extensionName"],
        "publisher": e["publisher"]["publisherName"],
        "publisher_display": e["publisher"].get("displayName", ""),
        "name": e["extensionName"],
        "display": e.get("displayName", ""),
        "category": category,
        "installs": int(st.get("install", 0)),
        "updates": int(st.get("updateCount", 0)),
        "downloads": int(st.get("downloadCount", 0)),
        "rating": round(float(st.get("averagerating", 0)), 3),
        "ratings": int(st.get("ratingcount", 0)),
        "trending_weekly": round(float(st.get("trendingweekly", 0)), 4),
        "released": (e.get("releaseDate") or "")[:10],
        "updated": (ver.get("lastUpdated") or e.get("lastUpdated") or "")[:10],
        "version": ver.get("version", ""),
    }


def main(out_path, max_pages=40):
    seen, rows, totals = set(), [], {}
    for cat in CATEGORIES:
        got = 0
        for page in range(1, max_pages + 1):
            try:
                d = query(cat, page)
            except Exception as e:
                print(f"  {cat} p{page}: giving up ({str(e)[:60]})", flush=True)
                break
            res = (d or {}).get("results", [{}])[0]
            if page == 1:
                meta = [m for m in res.get("resultMetadata", [])
                        if m["metadataType"] == "ResultCount"]
                totals[cat] = meta[0]["metadataItems"][0]["count"] if meta else None
            exts = res.get("extensions", [])
            if not exts:
                break
            for e in exts:
                r = row(e, cat)
                got += 1
                if r["id"] in seen:
                    continue          # an extension can sit in several categories
                seen.add(r["id"])
                rows.append(r)
            time.sleep(GAP)
        print(f"{cat:22} total={totals.get(cat)} scanned={got} distinct_so_far={len(seen)}",
              flush=True)

    with open(out_path, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    print(f"\nwrote {len(rows)} distinct extensions -> {out_path}")
    return rows


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1
         else "/srv/agents/make-money/research/vsx-marketplace.jsonl")
