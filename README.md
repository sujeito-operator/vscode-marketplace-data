# What actually gets installed on the VS Code Marketplace

**64,490 extensions from 50,468 publishers, measured August 2026,
with real install counts — not a proxy.**

> **The top 1% of extensions hold 87.4% of all installs in this sample.
> The top 10% hold 98.0%.**
> At least 22.5% have fewer than 100 installs, and at least
> 54.4% have fewer than 1,000.

Most "what sells" datasets lean on ratings or reviews as a stand-in for demand. The VS Code
Marketplace publishes install counts directly, so this measures the thing itself.

## Read this before quoting anything

**This is not a census, and it is head-biased.** HEAD-BIASED. Categories larger than the page cap are truncated from the top, so the long tail is under-represented. Percentages of low-install extensions are FLOORS, not estimates.

Practically: every "under N installs" figure here is a **floor**. The true share is higher,
because the tail this crawl did not reach lies entirely below the part it did. Treat the
concentration figures as conservative for the same reason — a fuller tail would make the
head's share larger, not smaller.

The install count is what the Marketplace reports. It counts installs, not active users,
and not people who kept the extension.

## The shape of the market

| | |
|---|---:|
| Extensions sampled | 64,490 |
| Publishers | 50,468 |
| Installs represented | 5,688,542,991 |
| Median installs | 804 |
| 25th / 75th percentile | 133 / 3,519 |
| Largest single extension | 231,321,041 |
| Top 1% share of installs | 87.4% |
| Top 5% / top 10% share | 96.1% / 98.0% |
| Not updated in 12 months | 65.2% |
| Publishers with exactly one extension | 86.1% |
| Most extensions by one publisher | 286 |

**86.1% of publishers have published exactly one extension.**
The median publisher has 1. This is not a market of
software vendors with catalogues; it is a very long tail of single releases behind a small
number of large ones.

## By category

Sorted by median installs. `under 100%` and `stale` are floors, per the caveat above.

| Category | Sampled | Median installs | 90th pct | Under 100 | Stale >12mo |
|---|---:|---:|---:|---:|---:|
| Other | 11,997 | 3,147 | 44,556 | 0.0% | 83.6% |
| Programming Languages | 8,991 | 1,865 | 70,492 | 0.0% | 75.5% |
| Themes | 11,637 | 1,017 | 11,618 | 0.0% | 88.5% |
| Debuggers | 1,818 | 508 | 23,233 | 24.6% | 39.2% |
| Snippets | 7,983 | 297 | 12,175 | 36.4% | 77.1% |
| Formatters | 2,879 | 286 | 10,581 | 31.0% | 50.9% |
| Extension Packs | 3,573 | 272 | 7,678 | 30.5% | 84.0% |
| Language Packs | 200 | 233 | 38,022 | 30.5% | 51.5% |
| Keymaps | 488 | 229 | 8,579 | 33.0% | 68.0% |
| Data Science | 765 | 128 | 3,174 | 46.0% | 19.1% |
| Testing | 879 | 82 | 2,304 | 52.0% | 28.0% |
| Visualization | 3,116 | 73 | 2,003 | 54.9% | 20.4% |
| Notebooks | 252 | 60 | 2,474 | 57.5% | 36.5% |
| Linters | 3,904 | 53 | 2,080 | 59.2% | 26.6% |
| Chat | 121 | 49 | 916 | 59.5% | 4.1% |
| Education | 852 | 46 | 755 | 64.4% | 24.8% |
| Machine Learning | 1,628 | 43 | 673 | 64.6% | 15.4% |
| AI | 2,042 | 39 | 1,119 | 66.6% | 13.8% |
| SCM Providers | 1,365 | 31 | 1,101 | 68.9% | 17.8% |

## Two redactions, and a disclosure

While compiling this, two publishers turned out to have pasted a `vsce publish -p <token>`
command into their **publisher display name**, which the public API serves to anyone. Those
tokens are replaced here with `[REDACTED-CREDENTIAL]`. They were not tested, not retained and
not published, and the exposure was reported to Microsoft on 2026-08-08 before this repository
went public. One of the two extensions has roughly 34,000 installs, so a live publish token
there would be a supply-chain problem rather than a theoretical one.

If you regenerate this dataset with `scripts/crawl.py` you will collect those values yourself.
Please do not publish them.

## One omission, stated plainly

24 extensions were collected but are **not** in the published files. Their publisher id is a
52-character base32 string that GitHub's secret scanning misclassifies as an Azure DevOps
token, which blocks any push containing them. Those are public identifiers, not credentials.
They are listed in [`data/omitted-rows.md`](data/omitted-rows.md), and `scripts/crawl.py`
regenerates the complete set including them. 24 of 64,514 is 0.04% and moves no figure above.

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

## Licence

Data: CC BY 4.0. Code: MIT.
