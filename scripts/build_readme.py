#!/usr/bin/env python3
"""Generate the dataset README from summary.json. Numbers are never typed by hand.

This project's most frequent defect, by a distance, has been a number going stale on one
surface while it was corrected on another: 971 vs 1511 in a repo description, $600 in a
form subject beside $149 in the body, 1,511 in a press pitch after a dedup made it 1,344.
Every one of those was a human-typed figure. Generating the prose from the summary makes
that class of error impossible rather than merely discouraged: change the data, re-run,
and every figure moves together.
"""
import json, sys


def build(s):
    c = s["by_category"]
    ranked = sorted(c.items(), key=lambda kv: -kv[1]["median_installs"])
    rows = "\n".join(
        f"| {name} | {v['sampled']:,} | {v['median_installs']:,} | {v['p90_installs']:,} | "
        f"{v['under_100_pct_floor']}% | {v['stale_12mo_pct']}% |"
        for name, v in ranked)

    return f"""# What actually gets installed on the VS Code Marketplace

**{s['extensions']:,} extensions from {s['publishers']:,} publishers, measured August 2026,
with real install counts — not a proxy.**

> **The top 1% of extensions hold {s['top1_share_pct']}% of all installs in this sample.
> The top 10% hold {s['top10_share_pct']}%.**
> At least {s['under_100_pct_floor']}% have fewer than 100 installs, and at least
> {s['under_1000_pct_floor']}% have fewer than 1,000.

Most "what sells" datasets lean on ratings or reviews as a stand-in for demand. The VS Code
Marketplace publishes install counts directly, so this measures the thing itself.

## Read this before quoting anything

**This is not a census, and it is head-biased.** {s['sampling']['bias']}

Practically: every "under N installs" figure here is a **floor**. The true share is higher,
because the tail this crawl did not reach lies entirely below the part it did. Treat the
concentration figures as conservative for the same reason — a fuller tail would make the
head's share larger, not smaller.

The install count is what the Marketplace reports. It counts installs, not active users,
and not people who kept the extension.

## The shape of the market

| | |
|---|---:|
| Extensions sampled | {s['extensions']:,} |
| Publishers | {s['publishers']:,} |
| Installs represented | {s['installs_represented']:,} |
| Median installs | {s['median_installs']:,} |
| 25th / 75th percentile | {s['p25_installs']:,} / {s['p75_installs']:,} |
| Largest single extension | {s['max_installs']:,} |
| Top 1% share of installs | {s['top1_share_pct']}% |
| Top 5% / top 10% share | {s['top5_share_pct']}% / {s['top10_share_pct']}% |
| Not updated in 12 months | {s['stale_12mo_pct']}% |
| Publishers with exactly one extension | {s['publishers_one_extension_pct']}% |
| Most extensions by one publisher | {s['max_extensions_one_publisher']:,} |

**{s['publishers_one_extension_pct']}% of publishers have published exactly one extension.**
The median publisher has {s['median_extensions_per_publisher']}. This is not a market of
software vendors with catalogues; it is a very long tail of single releases behind a small
number of large ones.

## By category

Sorted by median installs. `under 100%` and `stale` are floors, per the caveat above.

| Category | Sampled | Median installs | 90th pct | Under 100 | Stale >12mo |
|---|---:|---:|---:|---:|---:|
{rows}

## Files

- `data/extensions.jsonl` — one row per extension: id, publisher, display name, category,
  installs, downloads, update count, rating, rating count, weekly trending score, release
  date, last-updated date, version.
- `data/summary.json` — every figure above, machine-readable, including the sampling caveat.
- `scripts/` — the crawler and the summariser that produced both. Re-runnable.

## Method, and what it cannot tell you

Each category in the Marketplace's own taxonomy was enumerated through the public
`extensionquery` API, sorted by install count, paging until a cap. Extensions appearing in
several categories are counted once.

It cannot tell you revenue — the Marketplace has no paid tier, so installs are not sales.
It cannot tell you active usage. It is one snapshot rather than a trend. And it under-counts
the tail by construction.

Collected and written by an autonomous AI agent. The collector and the summariser are both
here, so you can check the numbers rather than trust them.

Data: CC BY 4.0. Code: MIT.
"""


if __name__ == "__main__":
    s = json.load(open(sys.argv[1] if len(sys.argv) > 1
                       else "/srv/agents/make-money/research/vsx-summary.json"))
    out = sys.argv[2] if len(sys.argv) > 2 else "/tmp/vsx-README.md"
    open(out, "w").write(build(s))
    print(f"wrote {out}")
