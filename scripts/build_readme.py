#!/usr/bin/env python3
"""Generate the dataset README from summary.json. Numbers are never typed by hand.

This project's most frequent defect, by a distance, has been a number going stale on one
surface while it was corrected on another: 971 vs 1511 in a repo description, $600 in a
form subject beside $149 in the body, 1,511 in a press pitch after a dedup made it 1,344.
Every one of those was a human-typed figure. Generating the prose from the summary makes
that class of error impossible rather than merely discouraged: change the data, re-run,
and every figure moves together.
"""
import csv, json, pathlib, re, sys

REPO = pathlib.Path(__file__).resolve().parent.parent

# THE DEFAULT USED TO BE `/srv/agents/make-money/research/vsx-summary.json`, AND THAT FILE IS
# THE PRE-OMISSION CRAWL. Twenty-four rows were withheld after it was written (GitHub secret
# scanning misclassifies their base32 publisher ids), so it says 64,514 / 50,484 while the
# files this repo actually publishes hold 64,490 / 50,468. Running the documented command
# therefore rewrote twenty figures back to a crawl that does not match the download — which
# is the exact defect the repo description was corrected for on 2026-08-08: *a reader was
# told they would get 24 more extensions than they get.* The default is the published
# summary now, and `gate()` re-derives the two headline figures from the published CSV so a
# summary that has drifted from the files cannot pass either.
DEFAULT_SUMMARY = REPO / "data" / "summary.json"
PUBLISHED_CSV = REPO / "data" / "extensions.csv"


# A README for a free dataset that also advertises something for sale reads as bait, and a
# maintainer said so in as many words when a dataset PR pointing here was closed on
# 2026-08-11: "a dataset whose metadata pointed at a page I sell from ... this looks way too
# much like a scam." The commercial block was deleted from README.md that day and left in
# THIS FILE, so the next person to regenerate the README would have restored it without
# noticing. Absence is checked here rather than trusted.
NOT_FOR_SALE = ["gumroad.com/l/", "affiliate", "revenue share", "checkout", "coupon",
                "discount", "paid report", "buy it", "purchase"]
MONEY = re.compile(r"\$\s?\d")


def no_offer(text):
    hits = [m for m in NOT_FOR_SALE if m in text.lower()] + \
           [m.group(0) for m in [MONEY.search(text)] if m]
    if hits:
        raise SystemExit(f"REFUSING to write a README carrying a commercial offer: {hits}. "
                         "This repository publishes free data and links to free data.")


def gate(s):
    """The published FILES are the authority, not the summary and not this script."""
    if not PUBLISHED_CSV.exists():
        raise SystemExit(f"{PUBLISHED_CSV} is missing — cannot check the summary against "
                         "what the repository actually publishes.")
    with PUBLISHED_CSV.open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    pubcol = "publisher" if "publisher" in rows[0] else "publisher_id"
    real = {"extensions": len(rows), "publishers": len({r[pubcol] for r in rows})}
    bad = {k: (s[k], v) for k, v in real.items() if s[k] != v}
    if bad:
        raise SystemExit(
            "summary disagrees with the published CSV — " + ", ".join(
                f"{k}: summary says {a:,}, {PUBLISHED_CSV.name} holds {b:,}"
                for k, (a, b) in bad.items()) +
            ". The files a reader downloads are the authority; fix the summary, not this.")
    return real


def build(s):
    o = s["omitted"]
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

## What was withheld, stated plainly

**{o['display_names_redacted']} redacted display names.** That many publishers had pasted a
`vsce publish -p <token>` command into their **publisher display name**, which the public API
serves to anyone. Those values are replaced here with `[REDACTED-CREDENTIAL]`. They were not
tested, not retained and not published, and the exposure was reported to Microsoft on
2026-08-08 before this repository went public. One of those extensions has roughly 34,000
installs, so a live publish token there would be a supply-chain problem rather than a
theoretical one.

**{o['rows']} omitted rows** of {o['crawl_total']:,} collected — {o['rows'] / o['crawl_total'] * 100:.2f}%,
{o['installs']:,} installs, and it moves no figure above. Every one is omitted for the same
reason: **its publisher id has the shape of a secret**, so a file containing it is a
credential dump whether or not the string is live. {o['base32_publisher']} are 52-character
base32 strings, which GitHub's scanner reads as an Azure DevOps token;
{o['uuid_publisher']} are bare UUIDs, which it reads as an **Open VSX access token**. The
UUIDs were **not tested against Open VSX** — that would mean using somebody else's
credential, and the decision to withhold them does not depend on the answer.

Nothing is hidden by being removed: all {o['rows']} are listed with their category and
install count in [`data/omitted-rows.md`](data/omitted-rows.md). `scripts/crawl.py`
regenerates the complete set including them, and `scripts/scrub.py` reproduces exactly the
files published here — it refuses to write if a secret-shaped token survives anywhere in
any of them.

If you regenerate this dataset yourself you will collect these values. Please do not
publish them.

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

## Citing this

Archived on Zenodo with a DOI, so it can be cited and so dataset indexes that read DOIs
can find it. The link below is the **concept DOI** — it always resolves to the current
version, and will keep doing so if this data is recrawled.

> Sujeito Operator (2026). *What actually gets installed on the VS Code Marketplace*
> [Data set]. Zenodo. https://doi.org/10.5281/zenodo.21854363

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21854363.svg)](https://doi.org/10.5281/zenodo.21854363)

## Related, by the same author

The same question asked of a different marketplace, where the answer is harder to get
because the platform does not publish it:

- **[Gumroad Market Data 2026](https://github.com/sujeito-operator/gumroad-market-data)** —
  live Gumroad products and sellers, including the subset that publishes a real unit-sales
  count rather than a rating. Free CSVs, CC BY 4.0, DOI-archived, collector included.

*(Deliberately no figures in this section: it describes another repository whose numbers
move when that dataset is recrawled, and a sentence with no number in it cannot go stale.)*

## Licence

Data: CC BY 4.0. Code: MIT.
"""


if __name__ == "__main__":
    s = json.load(open(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SUMMARY))
    real = gate(s)
    out = sys.argv[2] if len(sys.argv) > 2 else REPO / "README.md"
    text = build(s)
    no_offer(text)
    open(out, "w").write(text)
    print(f"wrote {out} — checked against {PUBLISHED_CSV.name}: "
          f"{real['extensions']:,} extensions, {real['publishers']:,} publishers")
