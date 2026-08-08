#!/usr/bin/env python3
"""Turn the marketplace crawl into a summary, with the sampling bias stated in the output.

The single most important thing in this file is `sampling`. The crawl walks each category
sorted by install count and stops at a page cap, so what comes back is the HEAD of every
category, not a random sample. Any statement of the form "X% of extensions have fewer than
N installs" is therefore a FLOOR — the true share is higher, because the tail we did not
reach is all below the part we did. That caveat is emitted into the summary itself rather
than being left in a README somewhere, because the summary is what gets quoted.
"""
import collections, json, statistics, sys


def pct(part, whole):
    return round(100.0 * part / whole, 1) if whole else 0.0


def summarize(rows):
    ins = sorted(r["installs"] for r in rows)
    n, tot = len(ins), sum(ins)
    pub = collections.Counter(r["publisher"] for r in rows)

    def share(frac):
        k = max(1, int(n * frac))
        return round(100.0 * sum(ins[-k:]) / tot, 1) if tot else 0.0

    by_cat = {}
    cats = collections.defaultdict(list)
    for r in rows:
        cats[r["category"]].append(r)
    for c, rs in sorted(cats.items()):
        ci = sorted(x["installs"] for x in rs)
        by_cat[c] = {
            "sampled": len(rs),
            "median_installs": int(statistics.median(ci)),
            "p90_installs": ci[int(len(ci) * 0.9)],
            "max_installs": ci[-1],
            "under_100_pct_floor": pct(sum(1 for x in ci if x < 100), len(ci)),
            "stale_12mo_pct": pct(sum(1 for x in rs if x["updated"] and
                                      x["updated"] < "2025-08-08"), len(rs)),
        }

    return {
        "sampling": {
            "method": "Enumerated the Marketplace's own category taxonomy via the public "
                      "extensionquery API, sorted by install count, paging until a cap.",
            "bias": "HEAD-BIASED. Categories larger than the page cap are truncated from "
                    "the top, so the long tail is under-represented. Percentages of "
                    "low-install extensions are FLOORS, not estimates.",
            "not_a_census": True,
            "deduplicated": "An extension appearing in several categories is counted once, "
                            "under the first category it was seen in.",
        },
        "extensions": n,
        "publishers": len(pub),
        "installs_represented": tot,
        "median_installs": int(statistics.median(ins)),
        "p25_installs": ins[n // 4],
        "p75_installs": ins[3 * n // 4],
        "max_installs": ins[-1],
        "top1_share_pct": share(0.01),
        "top5_share_pct": share(0.05),
        "top10_share_pct": share(0.10),
        "under_100_pct_floor": pct(sum(1 for x in ins if x < 100), n),
        "under_1000_pct_floor": pct(sum(1 for x in ins if x < 1000), n),
        "stale_12mo_pct": pct(sum(1 for r in rows if r["updated"] and
                                  r["updated"] < "2025-08-08"), n),
        "publishers_one_extension_pct": pct(sum(1 for v in pub.values() if v == 1), len(pub)),
        "median_extensions_per_publisher": int(statistics.median(pub.values())),
        "max_extensions_one_publisher": max(pub.values()),
        "by_category": by_cat,
    }


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else \
        "/srv/agents/make-money/research/vsx-marketplace.jsonl"
    rows = [json.loads(l) for l in open(src)]
    s = summarize(rows)
    out = sys.argv[2] if len(sys.argv) > 2 else \
        "/srv/agents/make-money/research/vsx-summary.json"
    json.dump(s, open(out, "w"), indent=1)
    print(json.dumps({k: v for k, v in s.items() if k != "by_category"}, indent=1))
    print(f"\n-> {out}")
