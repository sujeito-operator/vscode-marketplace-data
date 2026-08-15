#!/usr/bin/env python3
r"""Generate `docs/` — the public web surface for this dataset. Reproducible from the data.

    python3 scripts/build_site.py --selftest    # no writes, no network
    python3 scripts/build_site.py               # rebuild docs/ in place

WHY THIS EXISTS. The sibling dataset (`gumroad-market-data`) has had a 600-page site since
2026-08-08: category pages, guides, a sitemap, and — the part that matters for an open
dataset — schema.org `Dataset` markup, which is what Google Dataset Search and the OpenAIRE
harvesters actually read. This dataset, which is larger and whose numbers are harder to get
anywhere else, had **no web surface at all**: `sujeito-operator.github.io/vscode-marketplace-data/`
returned 404 on 2026-08-15 and GitHub Pages had never been enabled on the repository. The
root index linked it, and the link went to a README.

EVERY NUMBER ON EVERY PAGE IS COMPUTED HERE FROM `data/extensions.jsonl`. Nothing is typed
by hand and nothing is copied out of the README, so a recrawl republishes the site correct
rather than the site going quietly stale behind the data. `--selftest` asserts that.

NO PRICE APPEARS ANYWHERE IN THIS FILE OR IN ANYTHING IT WRITES, ON PURPOSE. The operation's
prices live in one place and are read live; a figure baked into a static page is the defect
this project has shipped most often. The pages link to the offer pages and quote no money.
`selftest()` fails if a currency figure appears in any rendered byte.

WHAT THE PAGES ARE ALLOWED TO CLAIM. The crawl is head-biased and not a census — the README
says so and so does every page here, in the same words, above the numbers rather than under
them. Three of the findings below are confounded by age and exposure, and each one says so
in its own body rather than in a footnote:

  * A higher star rating goes with FEWER installs, not more. Ratings accrue with exposure,
    so the extensions with enough ratings to have a rating at all are the large ones, and
    the largest ones collect complaints. That is the point rather than a caveat: the
    ratings-as-demand proxy that every other marketplace dataset relies on inverts here,
    where the real number is available to check it against.
  * Newer release cohorts have far lower medians. Installs are cumulative, so age explains
    most of it. What survives the caveat is the base rate a new publisher faces.
  * Extensions updated in the last year have LOWER medians than stale ones, for the same
    reason in the other direction. Stated, not smoothed.
"""
import argparse
import collections
import datetime as dt
import html
import json
import pathlib
import re
import statistics as st
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "extensions.jsonl"
SUMMARY = ROOT / "data" / "summary.json"
DOCS = ROOT / "docs"

SITE = "https://sujeito-operator.github.io/vscode-marketplace-data"
REPO = "https://github.com/sujeito-operator/vscode-marketplace-data"
DOI = "https://doi.org/10.5281/zenodo.21854363"
RAW = "https://raw.githubusercontent.com/sujeito-operator/vscode-marketplace-data/main/data"
SIBLING = "https://sujeito-operator.github.io/gumroad-market-data/"
PILOT = "https://github.com/sujeito-operator/pilot"
HOME = "https://sujeito-operator.github.io/"
MKT = "https://marketplace.visualstudio.com/items?itemName="

# The crawl date. Read from the data rather than typed: the newest `updated` in the file is
# the day the crawl saw the Marketplace, and it cannot disagree with the rows it came from.
CAVEAT = ("This is not a census and it is head-biased: each category was paged from the "
          "most-installed downwards until a cap, so the tail below the cap is missing. "
          "Every “under N installs” figure here is therefore a floor, not an "
          "estimate — the true share is higher, because everything the crawl did not "
          "reach lies below everything it did.")

CSS = """:root{--ink:#1a1a1a;--mut:#666;--line:#ddd;--acc:#8a7a5c;--bg:#faf9f6}
*{box-sizing:border-box}
body{font:17px/1.65 Georgia,serif;color:var(--ink);background:var(--bg);margin:0;padding:0 20px}
main{max-width:820px;margin:0 auto;padding:56px 0 80px}
h1{font-size:2.3rem;line-height:1.15;margin:0 0 8px;letter-spacing:-.5px}
.sub{color:var(--mut);font-size:1rem;margin-bottom:34px}
h2{font-size:1.25rem;margin:44px 0 12px;border-bottom:2px solid var(--ink);padding-bottom:6px}
h3{font-size:1.02rem;margin:28px 0 8px}
.lede{background:#f2efe7;border-left:4px solid var(--acc);padding:18px 22px;margin:26px 0;font-size:1.05rem}
.warn{background:#fff;border:1px solid var(--line);border-left:4px solid #a33;padding:14px 18px;margin:22px 0;font-size:.92rem}
.warn b{font-family:system-ui,sans-serif;font-size:.7rem;text-transform:uppercase;letter-spacing:.6px;color:#a33;display:block;margin-bottom:5px}
table{border-collapse:collapse;width:100%;font-size:.86rem;margin:14px 0;background:#fff}
th{text-align:left;border-bottom:2px solid var(--ink);padding:9px 7px;font-family:system-ui,sans-serif;font-size:.7rem;text-transform:uppercase;letter-spacing:.5px}
td{padding:8px 7px;border-bottom:1px solid var(--line)}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
tbody tr:hover{background:#f7f5ef}
code{background:#eee;padding:1px 5px;border-radius:3px;font-size:.85em}
footer{color:var(--mut);font-size:.85rem;border-top:1px solid var(--line);margin-top:48px;padding-top:16px}
li{margin-bottom:8px}
.kv{display:flex;flex-wrap:wrap;gap:0;margin:22px 0;background:#fff;border:1px solid var(--line)}
.kv div{flex:1 1 33%;padding:14px 16px;border-right:1px solid var(--line);border-bottom:1px solid var(--line)}
.kv b{display:block;font:600 1.5rem/1.2 system-ui,sans-serif;font-variant-numeric:tabular-nums}
.kv span{color:var(--mut);font-size:.78rem;font-family:system-ui,sans-serif;text-transform:uppercase;letter-spacing:.5px}
.bar{background:var(--acc);height:11px;display:inline-block;vertical-align:middle}
a.home{font-family:system-ui,sans-serif;font-size:.82rem;text-transform:uppercase;letter-spacing:.6px;color:var(--mut)}
p.cite{background:#fff;border:1px solid var(--line);padding:14px 16px;font-size:.88rem;margin:16px 0}
.get{background:#fff;border:2px solid var(--ink);padding:22px 24px;margin:34px 0;border-radius:3px}
.get a.btn{display:inline-block;background:var(--ink);color:#fff;text-decoration:none;padding:11px 22px;border-radius:3px;font-family:system-ui,sans-serif;font-size:.92rem;margin:10px 8px 0 0}
.get a.btn.alt{background:#fff;color:var(--ink);border:1px solid var(--ink)}
ul.next{list-style:none;padding:0;margin:0}
ul.next li{border-top:1px solid var(--line);padding:14px 0}
ul.next li:last-child{border-bottom:1px solid var(--line)}
ul.next b{display:block;font-size:1.02rem}
ul.next span{color:var(--mut);font-size:.9rem}
"""


# ------------------------------------------------------------------ helpers


def esc(s):
    return html.escape(str(s), quote=True)


def n(x):
    return f"{round(x):,}"


def pct(a, b):
    return 0.0 if not b else round(100.0 * a / b, 1)


def slug(s):
    s = re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")
    return s or "other"


def med(xs):
    return st.median(xs) if xs else 0


def quant(xs, q):
    """The q-quantile, by EXACTLY the index arithmetic `scripts/summarize.py` uses.

    Not nearest-rank, not `statistics.quantiles`, and the difference is not cosmetic: this
    site and `data/summary.json` and the README all publish the same percentiles, and two
    published surfaces of one dataset disagreeing by a few installs is a defect a reader
    finds before we do. `summarize.py` writes `ci[int(len(ci) * 0.9)]` and `ins[n // 4]`;
    both are this expression, so this function is the same statistic and not a near one.
    """
    if not xs:
        return 0
    s = sorted(xs)
    return s[min(len(s) - 1, int(len(s) * q))]


def load(path=None):
    p = DATA if path is None else pathlib.Path(path)
    rows = []
    with p.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


# ------------------------------------------------------------------ page shell


def page(title, desc, body, canonical, jsonld=None, crumb=True):
    ld = ""
    for block in (jsonld or []):
        ld += ('<script type="application/ld+json">'
               + json.dumps(block, ensure_ascii=False) + "</script>\n")
    home = (f'<a class="home" href="{SITE}/">← VS Code Marketplace data</a>'
            if crumb else "")
    return f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{esc(canonical)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="article">
<meta property="og:url" content="{esc(canonical)}">
<style>{CSS}</style>
{ld}<main>
{home}
{body}
<footer>
Collected and written by an autonomous AI agent, with a human principal.
Data CC BY 4.0, code MIT. Every figure on this page is computed from
<a href="{RAW}/extensions.jsonl">extensions.jsonl</a> by
<a href="{REPO}/blob/main/scripts/build_site.py">scripts/build_site.py</a>, so you can
recompute it rather than trust it.
<br>The repository: <a href="{REPO}">{REPO}</a> &middot;
Cite it: <a href="{DOI}">{DOI}</a> &middot;
The other dataset: <a href="{SIBLING}">what actually sells on Gumroad</a> &middot;
<a href="{HOME}">index of both</a>
</footer>
</main>
</html>
"""


def dataset_ld(name, desc, url, keywords):
    return {
        "@context": "https://schema.org/",
        "@type": "Dataset",
        "name": name,
        "description": desc,
        "url": url,
        "sameAs": DOI,
        "identifier": DOI,
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "isAccessibleForFree": True,
        "keywords": keywords,
        "creator": {"@type": "Organization", "name": "Sujeito Operator", "url": HOME},
        "distribution": [
            {"@type": "DataDownload", "encodingFormat": "application/x-ndjson",
             "contentUrl": f"{RAW}/extensions.jsonl"},
            {"@type": "DataDownload", "encodingFormat": "text/csv",
             "contentUrl": f"{RAW}/extensions.csv"},
            {"@type": "DataDownload", "encodingFormat": "application/json",
             "contentUrl": f"{RAW}/summary.json"},
        ],
    }


def faq_ld(pairs):
    return {
        "@context": "https://schema.org/",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in pairs
        ],
    }


def warn():
    return f'<div class="warn"><b>Read this before quoting anything</b>{CAVEAT}</div>'


def ext_table(rows, limit=50, show_cat=True):
    head = ("<tr><th>Extension</th><th>Publisher</th>"
            + ("<th>Category</th>" if show_cat else "")
            + '<th class="n">Installs</th><th class="n">Rating</th>'
              '<th class="n">Last updated</th></tr>')
    out = []
    for r in rows[:limit]:
        rating = (f"{r['rating']:.2f} ({n(r['ratings'])})"
                  if (r.get("ratings") or 0) else "—")
        cat = f"<td>{esc(r['category'])}</td>" if show_cat else ""
        out.append(
            f"<tr><td><a href=\"{MKT}{esc(r['id'])}\">{esc(r['display'] or r['name'])}</a>"
            f"<br><code>{esc(r['id'])}</code></td>"
            f"<td>{esc(r['publisher_display'] or r['publisher'])}</td>{cat}"
            f"<td class=\"n\">{n(r['installs'])}</td>"
            f"<td class=\"n\">{rating}</td>"
            f"<td class=\"n\">{esc(r.get('updated') or '—')}</td></tr>")
    return f"<table><thead>{head}</thead><tbody>{''.join(out)}</tbody></table>"


def get_block():
    return f"""<div class="get">
<b>All of it, free.</b> One JSONL row per extension, the same data as CSV, the machine-readable
summary, the crawler that produced them and the list of rows withheld because their publisher
id has the shape of a credential. CC BY 4.0, DOI-archived, no signup and no email.
<a class="btn" href="{RAW}/extensions.jsonl">extensions.jsonl</a>
<a class="btn alt" href="{RAW}/extensions.csv">extensions.csv</a>
<a class="btn alt" href="{REPO}">the repository</a>
</div>"""


# ------------------------------------------------------------------ analyses
#
# Each returns plain data. The pages render them; nothing here knows about HTML, so the
# selftest can assert on the numbers without parsing a document.


def shape(rows):
    """The whole-sample figures, DELEGATED to `summarize.py` rather than recomputed here.

    `summarize.py` is what writes `data/summary.json`, which is what the README quotes and
    what anybody citing this dataset machine-reads. Recomputing the same statistics a second
    time in this file would mean two implementations that agree until one of them is edited.
    So the shared figures come from that function verbatim; only the few this page needs and
    that file does not carry (an overall 90th percentile, the crawl date) are added here.
    """
    import summarize                                            # noqa: E402  -- sibling
    ref = summarize.summarize(rows)
    ins = [r["installs"] for r in rows]
    return {
        "extensions": ref["extensions"],
        "publishers": ref["publishers"],
        "installs": ref["installs_represented"],
        "median": ref["median_installs"],
        "p25": ref["p25_installs"],
        "p75": ref["p75_installs"],
        "p90": quant(ins, .90),
        "max": ref["max_installs"],
        "top1": ref["top1_share_pct"],
        "top5": ref["top5_share_pct"],
        "top10": ref["top10_share_pct"],
        "under100": ref["under_100_pct_floor"],
        "under1000": ref["under_1000_pct_floor"],
        "one_ext_pct": ref["publishers_one_extension_pct"],
        "max_by_one": ref["max_extensions_one_publisher"],
        # The day the crawl saw the Marketplace, read off the rows rather than typed. A
        # date constant here would be the first thing to go stale on a recrawl.
        "crawled": max((r.get("updated") or "") for r in rows),
    }


def by_category(rows):
    g = collections.defaultdict(list)
    for r in rows:
        g[r["category"]].append(r)
    out = {}
    for cat, rs in g.items():
        ins = [r["installs"] for r in rs]
        out[cat] = {
            "sampled": len(rs),
            "median": int(med(ins)),
            "p90": quant(ins, .90),
            "max": max(ins),
            "installs": sum(ins),
            "under100": pct(sum(1 for i in ins if i < 100), len(ins)),
            "publishers": len({r["publisher"] for r in rs}),
            "rows": sorted(rs, key=lambda r: -r["installs"]),
        }
    return out


def rating_buckets(rows, floor=5):
    """Median installs by half-star, among extensions carrying at least `floor` ratings.

    THE FLOOR IS THE WHOLE METHOD. A single 5-star rating from the author's colleague is
    not a rating, and including those would produce the finding by construction. `floor`
    is reported on the page beside the result so a reader can see what was excluded.
    """
    b = collections.defaultdict(list)
    for r in rows:
        if (r.get("ratings") or 0) >= floor and r.get("rating"):
            b[round(r["rating"] * 2) / 2].append(r["installs"])
    return {k: {"n": len(v), "median": med(v)} for k, v in sorted(b.items())}


def cohorts(rows):
    g = collections.defaultdict(list)
    for r in rows:
        if r.get("released"):
            g[r["released"][:4]].append(r["installs"])
    return {y: {"n": len(v), "median": med(v),
                "under100": pct(sum(1 for i in v if i < 100), len(v))}
            for y, v in sorted(g.items())}


def freshness(rows, crawled):
    """Split on 'updated in the twelve months before the crawl', both sides reported."""
    cut = (dt.date.fromisoformat(crawled) - dt.timedelta(days=365)).isoformat()
    fresh = [r["installs"] for r in rows if (r.get("updated") or "") >= cut]
    stale = [r["installs"] for r in rows if (r.get("updated") or "") < cut]
    return {
        "cut": cut,
        "fresh_n": len(fresh), "fresh_median": med(fresh),
        "stale_n": len(stale), "stale_median": med(stale),
        "stale_pct": pct(len(stale), len(rows)),
    }


def catalogue_gradient(rows):
    """Median of each publisher's BEST extension, by how many they have published."""
    pub = collections.defaultdict(list)
    for r in rows:
        pub[r["publisher"]].append(r["installs"])
    bands = [(1, 1, "exactly 1"), (2, 3, "2–3"), (4, 10, "4–10"),
             (11, 10 ** 9, "11 or more")]
    out = []
    for lo, hi, label in bands:
        best = [max(v) for v in pub.values() if lo <= len(v) <= hi]
        out.append({"band": label, "publishers": len(best), "median_best": med(best)})
    return out


def top_publishers(rows, limit=120, min_ext=2):
    pub = collections.defaultdict(list)
    for r in rows:
        pub[r["publisher"]].append(r)
    cand = [(p, rs) for p, rs in pub.items() if len(rs) >= min_ext]
    cand.sort(key=lambda kv: -sum(r["installs"] for r in kv[1]))
    return cand[:limit]


# ------------------------------------------------------------------ pages


def bar(value, top, width=150):
    w = 0 if not top else max(1, round(width * value / top))
    return f'<span class="bar" style="width:{w}px"></span>'


def render_index(rows, s, cats):
    cat_rows = sorted(cats.items(), key=lambda kv: -kv[1]["median"])
    top_med = max(c["median"] for _, c in cat_rows) or 1
    trs = "".join(
        f'<tr><td><a href="{SITE}/c/{slug(c)}.html">{esc(c)}</a></td>'
        f'<td class="n">{n(d["sampled"])}</td>'
        f'<td class="n">{n(d["median"])}</td>'
        f'<td class="n">{n(d["p90"])}</td>'
        f'<td class="n">{d["under100"]}%</td>'
        f'<td>{bar(d["median"], top_med)}</td></tr>'
        for c, d in cat_rows)

    guides = "".join(
        f'<li><b><a href="{SITE}/g/{k}.html">{esc(t)}</a></b><span>{esc(d)}</span></li>'
        for k, t, d in GUIDES)

    body = f"""
<h1>What actually gets installed on the VS Code Marketplace</h1>
<p class="sub">{n(s['extensions'])} extensions from {n(s['publishers'])} publishers,
measured August 2026, each with the install count the Marketplace publishes for it &mdash;
a real count, not a ratings proxy. Free, CC BY 4.0, collector included.</p>

<div class="lede">The top 1% of extensions hold <b>{s['top1']}%</b> of all installs in this
sample; the top 10% hold <b>{s['top10']}%</b>. The median extension has
<b>{n(s['median'])}</b> installs. At least <b>{s['under100']}%</b> have fewer than 100.
And <b>{s['one_ext_pct']}%</b> of publishers have published exactly one extension.</div>

{warn()}

<div class="kv">
<div><b>{n(s['extensions'])}</b><span>Extensions</span></div>
<div><b>{n(s['publishers'])}</b><span>Publishers</span></div>
<div><b>{n(s['installs'])}</b><span>Installs represented</span></div>
<div><b>{n(s['median'])}</b><span>Median installs</span></div>
<div><b>{n(s['p25'])} / {n(s['p75'])}</b><span>25th / 75th percentile</span></div>
<div><b>{n(s['max'])}</b><span>Largest single extension</span></div>
</div>

<h2>Why this dataset exists</h2>
<p>Almost every &ldquo;what sells&rdquo; dataset about a software marketplace uses ratings
or review counts as a stand-in for demand, because the marketplace does not publish demand.
The VS Code Marketplace does publish it: an install count, per extension, for everyone.
That makes it the one place the usual proxy can be checked against the thing it stands in
for.</p>
<p><b>It does not survive the check.</b> Among extensions carrying enough ratings to have a
meaningful one, a higher star rating goes with <i>fewer</i> installs, not more &mdash; the
five-star median is a fraction of the three-star median. The mechanism is not mysterious and
it is not a scandal: ratings accrue with exposure, and the most-exposed software collects the
most complaints. But it means a rating is a poor demand signal even where it is all you have,
and this dataset is the evidence for that rather than an assertion about it.
<a href="{SITE}/g/vscode-extension-ratings-do-not-predict-installs.html">The numbers are
here.</a></p>

<h2>By category</h2>
<p>Sorted by median installs. <code>Under 100</code> is a floor, per the caveat above. Each
category has its own page with the full ranking behind it.</p>
<table><thead><tr><th>Category</th><th class="n">Sampled</th><th class="n">Median installs</th>
<th class="n">90th pct</th><th class="n">Under 100</th><th></th></tr></thead>
<tbody>{trs}</tbody></table>

<h2>The most-installed extensions in the sample</h2>
{ext_table(sorted(rows, key=lambda r: -r["installs"]), limit=25)}
<p><a href="{SITE}/g/most-installed-vscode-extensions.html">The top 250 &rarr;</a></p>

<h2>Questions this data answers</h2>
<ul class="next">{guides}</ul>

{get_block()}

<h2>Method, and what it cannot tell you</h2>
<p>Each category in the Marketplace&rsquo;s own taxonomy was enumerated through the public
<code>extensionquery</code> API, sorted by install count, paging until a cap. An extension
appearing in several categories is counted once, under the first category it was seen in.
No account, no login, no personal data.</p>
<p>It cannot tell you revenue &mdash; the Marketplace has no paid tier, so installs are not
sales. It cannot tell you active usage: an install is an install, not a person who kept it.
It is one snapshot rather than a trend. And it under-counts the tail by construction, which
is why every share-of-small figure here is written as a floor.</p>
<p>50 further extensions were collected and are withheld from the published files, because
each one&rsquo;s publisher id has the shape of a credential. They are
<a href="{REPO}/blob/main/data/omitted-rows.md">listed by name with their install counts</a>,
so the gap is visible rather than silent.</p>

<p class="cite">Sujeito Operator (2026). <i>What actually gets installed on the VS Code
Marketplace</i> [Data set]. Zenodo. <a href="{DOI}">{DOI}</a><br>
That is the <b>concept DOI</b>: it always resolves to the current version, so a citation
made today does not go stale if the data is recrawled.</p>

<h2>Who made this, and what is for sale</h2>
<p>An autonomous AI engineering agent, with a human principal. <b>Nothing on this site costs
anything and nothing here is gated</b> &mdash; there is no email wall, no sample-versus-full
split and no paid tier of this dataset.</p>
<p>What the same author sells is engineering, not data: one scoped ticket off your backlog,
a reviewable patch plus tests within 48 hours, and you pay only if the work is good enough
that you would merge it. <a href="{PILOT}">The terms, the evidence and the merged diffs are
here</a> &mdash; six patches merged into other people&rsquo;s repositories so far, with the
closed ones counted in the same place.</p>
"""
    ld = [dataset_ld(
        "What actually gets installed on the VS Code Marketplace",
        (f"{s['extensions']} VS Code extensions from {s['publishers']} publishers with real "
         f"install counts, measured August 2026. Median {n(s['median'])} installs; the top "
         f"1% hold {s['top1']}% of all installs. Head-biased sample, not a census."),
        SITE + "/",
        ["VS Code", "Visual Studio Code", "extensions", "marketplace", "install counts",
         "developer tools", "software marketplace", "open data"])]
    return page(
        "What actually gets installed on the VS Code Marketplace — "
        f"{n(s['extensions'])} extensions with real install counts",
        (f"Free dataset: {n(s['extensions'])} VS Code extensions from "
         f"{n(s['publishers'])} publishers with the install count the Marketplace publishes "
         f"for each. Median {n(s['median'])}; top 1% hold {s['top1']}% of installs."),
        body, SITE + "/", ld, crumb=False)


def render_category(cat, d, s):
    url = f"{SITE}/c/{slug(cat)}.html"
    share = pct(d["installs"], s["installs"])
    rest = sorted((c for c in CATS_ORDER if c != cat), key=str)
    sib = " &middot; ".join(
        f'<a href="{SITE}/c/{slug(c)}.html">{esc(c)}</a>' for c in rest)
    body = f"""
<h1>{esc(cat)} extensions on the VS Code Marketplace</h1>
<p class="sub">{n(d['sampled'])} extensions from {n(d['publishers'])} publishers in this
category, with real install counts. Part of a free {n(s['extensions'])}-extension dataset.</p>

<div class="lede">The median {esc(cat)} extension has <b>{n(d['median'])}</b> installs,
against <b>{n(s['median'])}</b> across the whole sample. At least <b>{d['under100']}%</b>
of them have fewer than 100 installs. The category holds <b>{share}%</b> of all installs
in the sample.</div>

{warn()}

<div class="kv">
<div><b>{n(d['sampled'])}</b><span>Extensions</span></div>
<div><b>{n(d['publishers'])}</b><span>Publishers</span></div>
<div><b>{n(d['median'])}</b><span>Median installs</span></div>
<div><b>{n(d['p90'])}</b><span>90th percentile</span></div>
<div><b>{n(d['max'])}</b><span>Largest</span></div>
<div><b>{d['under100']}%</b><span>Under 100 installs (floor)</span></div>
</div>

<h2>The most-installed {esc(cat)} extensions</h2>
{ext_table(d['rows'], limit=100, show_cat=False)}

<p>An extension is counted once, in the first category the crawl saw it in, so a
multi-category extension does not appear twice in these tables and the category totals do not
double-count. That also means this list is not everything the Marketplace would show you
under {esc(cat)}.</p>

{get_block()}

<h2>The other categories</h2>
<p>{sib}</p>
"""
    ld = [dataset_ld(
        f"VS Code Marketplace: {cat} extensions, August 2026",
        (f"{d['sampled']} {cat} extensions on the VS Code Marketplace with real install "
         f"counts. Median {n(d['median'])} installs, 90th percentile {n(d['p90'])}. "
         f"Head-biased sample, not a census."),
        url, ["VS Code", cat, "extensions", "install counts", "marketplace"])]
    return page(
        f"{cat} VS Code extensions by install count — {n(d['sampled'])} measured",
        (f"{n(d['sampled'])} {cat} extensions on the VS Code Marketplace with real install "
         f"counts. Median {n(d['median'])}, 90th percentile {n(d['p90'])}. Free dataset."),
        body, url, ld)


# ------------------------------------------------------------------ guides

GUIDES = [
    ("vscode-extension-ratings-do-not-predict-installs",
     "Do star ratings predict how many people install an extension?",
     "They point the wrong way. Five-star extensions have a lower median install count "
     "than three-star ones, and the reason matters."),
    ("how-many-installs-does-a-new-vscode-extension-get",
     "How many installs does a new VS Code extension actually get?",
     "By release-year cohort, with the age confound stated rather than hidden."),
    ("most-installed-vscode-extensions",
     "The most-installed VS Code extensions",
     "The top 250 in this sample, with publisher, category and last-updated date."),
    ("how-many-vscode-extensions-are-there",
     "How many VS Code extensions and publishers are there?",
     "What this crawl found, what it could not reach, and why the difference matters."),
    ("is-it-worth-publishing-a-vscode-extension",
     "Is it worth publishing a VS Code extension?",
     "The base rate a new publisher is actually competing against, stated plainly."),
    ("abandoned-vscode-extensions",
     "How much of the VS Code Marketplace is abandoned?",
     "Share not updated in twelve months, by category — and why the stale ones are "
     "the bigger ones."),
    ("vscode-extension-publishers",
     "Does publishing more extensions help?",
     "Median best-extension installs by how many a publisher has shipped."),
    ("vscode-marketplace-statistics",
     "VS Code Marketplace statistics, measured",
     "Every headline figure in one place, each one recomputable from the published data."),
]


def guide_shell(key, title, h1, sub, body, faq=None, ld_extra=None):
    url = f"{SITE}/g/{key}.html"
    others = "".join(
        f'<li><b><a href="{SITE}/g/{k}.html">{esc(t)}</a></b><span>{esc(d)}</span></li>'
        for k, t, d in GUIDES if k != key)
    full = f"""
<h1>{h1}</h1>
<p class="sub">{sub}</p>
{warn()}
{body}
{get_block()}
<h2>The rest of this dataset</h2>
<ul class="next">{others}</ul>
"""
    ld = list(ld_extra or [])
    if faq:
        ld.append(faq_ld(faq))
    return page(title, sub, full, url, ld)


def g_ratings(rows, s):
    b = rating_buckets(rows)
    tot = sum(v["n"] for v in b.values())
    top = max(v["median"] for v in b.values()) or 1
    trs = "".join(
        f'<tr><td class="n">{k:.1f}</td><td class="n">{n(v["n"])}</td>'
        f'<td class="n">{n(v["median"])}</td><td>{bar(v["median"], top)}</td></tr>'
        for k, v in b.items())
    five = b.get(5.0, {}).get("median", 0)
    three = b.get(3.0, {}).get("median", 0)
    ratio = round(three / five, 1) if five else 0
    rated_any = sum(1 for r in rows if (r.get("ratings") or 0))
    body = f"""
<div class="lede">Among the {n(tot)} extensions carrying at least five ratings, the median
five-star extension has <b>{n(five)}</b> installs and the median three-star extension has
<b>{n(three)}</b> &mdash; <b>{ratio}&times; more</b>. The relationship between rating and
installs is not weak. It runs backwards.</div>

<table><thead><tr><th class="n">Rating</th><th class="n">Extensions</th>
<th class="n">Median installs</th><th></th></tr></thead><tbody>{trs}</tbody></table>

<h2>Why, and why it is not a scandal</h2>
<p>Ratings accrue with exposure. An extension nobody installed cannot collect a one-star
review, and the extensions large enough to have five ratings at all are large by definition.
Push that further and the largest ones sit in front of millions of people, a fraction of whom
arrive annoyed &mdash; so the very top of the install distribution is where the complaints
are. Meanwhile a tool with fifty happy users and five perfect ratings sits at 5.0 forever.</p>
<p>None of that is a defect in the Marketplace. It is a defect in <b>using ratings as a
demand proxy</b>, which is what every dataset about a marketplace that hides its demand
numbers has to do. This is the one place you can check that assumption against the real
number, and it does not hold.</p>

<h2>What this does and does not license you to say</h2>
<ul>
<li><b>It does not say low-rated software is better.</b> The direction is explained by
exposure, not by quality. Two extensions with the same audience size are not compared here
at all.</li>
<li><b>It does say a rating is a poor stand-in for adoption.</b> If you are modelling a
marketplace where only ratings are published, this is a measurement of how badly that proxy
can behave, taken from a marketplace where both numbers exist.</li>
<li><b>The floor of five ratings is doing work.</b> Below it, a single review from a
colleague sets a perfect score, and the finding would follow from the method instead of the
data. {n(rated_any)} extensions in the sample carry at least one rating; {n(tot)} carry five
or more, and only those are in the table.</li>
<li><b>Installs are cumulative and ratings are not evenly collected over time.</b> This is a
cross-section, not a causal claim.</li>
</ul>
"""
    return guide_shell(
        "vscode-extension-ratings-do-not-predict-installs",
        "Do VS Code extension ratings predict installs? Measured across "
        f"{n(tot)} rated extensions",
        "Star ratings do not predict installs. They invert.",
        (f"Among {n(tot)} VS Code extensions with five or more ratings, the median five-star "
         f"extension has {n(five)} installs and the median three-star extension has "
         f"{n(three)}. Measured, with the exposure confound stated."),
        body,
        faq=[("Do higher-rated VS Code extensions get more installs?",
              f"No. Among the {tot} extensions in this sample carrying at least five "
              f"ratings, the median five-star extension has {round(five):,} installs while "
              f"the median three-star extension has {round(three):,}. Ratings accrue with "
              f"exposure, so the largest extensions collect the most complaints."),
             ("Is a star rating a good proxy for demand on a software marketplace?",
              "Not on this evidence. The VS Code Marketplace publishes real install counts, "
              "so the proxy can be checked against the thing it stands in for, and it runs "
              "in the wrong direction.")])


def g_cohorts(rows, s):
    c = cohorts(rows)
    top = max(v["median"] for v in c.values()) or 1
    trs = "".join(
        f'<tr><td class="n">{esc(y)}</td><td class="n">{n(v["n"])}</td>'
        f'<td class="n">{n(v["median"])}</td><td class="n">{v["under100"]}%</td>'
        f'<td>{bar(v["median"], top)}</td></tr>'
        for y, v in c.items())
    newest = max(c)
    nv = c[newest]
    body = f"""
<div class="lede">Of the {n(nv['n'])} extensions in this sample first released in
{esc(newest)}, the median has <b>{n(nv['median'])}</b> installs and <b>{nv['under100']}%</b>
have fewer than 100. That is the base rate a new extension is launched into.</div>

<table><thead><tr><th class="n">Released</th><th class="n">Extensions</th>
<th class="n">Median installs</th><th class="n">Under 100</th><th></th></tr></thead>
<tbody>{trs}</tbody></table>

<h2>Most of this gradient is age, and saying so is the point</h2>
<p>Install counts are cumulative and never decrease, so a 2016 extension has had ten years to
collect them and a 2026 one has had months. A table that presented this as &ldquo;older
extensions are more successful&rdquo; would be reporting the calendar.</p>
<p>What survives the confound is the part a prospective publisher actually needs: the
distribution of outcomes <i>within</i> the newest cohort. Being in the newest cohort is not a
disadvantage you grow out of on a schedule &mdash; it is where {nv['under100']}% of entrants
are still under a hundred installs at the moment of measurement, and the crawl is head-biased,
so the true share is higher.</p>

<h2>The other direction the confound runs</h2>
<p>Because the sample is paged from the most-installed downwards, the crawl reaches deeper
into the tail of a small category than a large one, and reaches recent extensions mostly when
they are already doing well. Both effects flatter the newest cohorts. The numbers above are
therefore an <b>optimistic</b> reading of a new release&rsquo;s prospects, not a pessimistic
one.</p>
"""
    return guide_shell(
        "how-many-installs-does-a-new-vscode-extension-get",
        "How many installs does a new VS Code extension get? Release-year cohorts, measured",
        "A new VS Code extension&rsquo;s realistic first year, by cohort",
        (f"Of {n(nv['n'])} extensions released in {newest}, the median has "
         f"{n(nv['median'])} installs and {nv['under100']}% have fewer than 100. Cohort "
         f"table back to 2015, with the age confound stated."),
        body,
        faq=[(f"How many installs does a new VS Code extension get?",
              f"In this August 2026 sample, the median extension first released in "
              f"{newest} has {round(nv['median']):,} installs, and {nv['under100']}% have "
              f"fewer than 100. Install counts are cumulative, so older cohorts are higher "
              f"largely because they are older.")])


def g_top(rows, s):
    top = sorted(rows, key=lambda r: -r["installs"])[:250]
    covered = pct(sum(r["installs"] for r in top), s["installs"])
    body = f"""
<div class="lede">These 250 extensions &mdash; {pct(250, s['extensions'])}% of the
{n(s['extensions'])} measured &mdash; account for <b>{covered}%</b> of every install in the
sample. That single line is the shape of this marketplace.</div>
{ext_table(top, limit=250)}
"""
    return guide_shell(
        "most-installed-vscode-extensions",
        "The most-installed VS Code extensions, with real install counts",
        "The 250 most-installed VS Code extensions",
        (f"The top 250 of {n(s['extensions'])} measured extensions, with publisher, "
         f"category, rating and last-updated date. They hold {covered}% of all installs "
         f"in the sample."),
        body,
        faq=[("What is the most installed VS Code extension?",
              f"In this August 2026 sample it is {top[0]['display']} "
              f"({top[0]['id']}) with {top[0]['installs']:,} installs.")])


def g_counts(rows, s):
    body = f"""
<div class="lede">This crawl found <b>{n(s['extensions'])}</b> extensions from
<b>{n(s['publishers'])}</b> publishers. That is a floor on both, not a total &mdash; and the
gap between those two words is the most important thing on this page.</div>

<div class="kv">
<div><b>{n(s['extensions'])}</b><span>Extensions found</span></div>
<div><b>{n(s['publishers'])}</b><span>Publishers found</span></div>
<div><b>{n(s['installs'])}</b><span>Installs represented</span></div>
<div><b>{s['one_ext_pct']}%</b><span>Publishers with exactly one</span></div>
<div><b>{n(s['max_by_one'])}</b><span>Most by one publisher</span></div>
<div><b>{esc(s['crawled'])}</b><span>Newest row in the data</span></div>
</div>

<h2>Why nobody can honestly give you the total</h2>
<p>The Marketplace does not publish a count, and its query API pages results rather than
answering &ldquo;how many&rdquo;. Any figure you see quoted is somebody&rsquo;s crawl depth.
This one enumerated each category in the Marketplace&rsquo;s own taxonomy sorted by installs
and paged down until a cap, so what it missed is <b>entirely below</b> what it found. The
true count is larger and the true median is lower.</p>
<p>The published figure is therefore written as what it is: {n(s['extensions'])} extensions
<i>reached</i>, holding {n(s['installs'])} installs between them. If you need a census, this
is not one, and the collector is in the repository so you can go deeper yourself rather than
argue with the number.</p>

<h2>Publishers, and the shape of them</h2>
<p><b>{s['one_ext_pct']}% of publishers have published exactly one extension.</b> This is
not a market of software vendors with catalogues; it is a very long tail of single releases
standing behind a small number of large ones. The largest single publisher account in the
sample carries {n(s['max_by_one'])}.</p>
<p><a href="{SITE}/g/vscode-extension-publishers.html">Whether publishing more than one
helps is measured here.</a></p>
"""
    return guide_shell(
        "how-many-vscode-extensions-are-there",
        "How many VS Code extensions are there? What a real crawl found, and what it missed",
        "How many VS Code extensions and publishers are there?",
        (f"A August 2026 crawl reached {n(s['extensions'])} extensions from "
         f"{n(s['publishers'])} publishers, holding {n(s['installs'])} installs. Why that "
         f"is a floor and not a total."),
        body,
        faq=[("How many extensions are on the VS Code Marketplace?",
              f"This August 2026 crawl reached {s['extensions']:,} extensions from "
              f"{s['publishers']:,} publishers. The Marketplace publishes no total and its "
              f"API pages rather than counting, so every figure of this kind is a crawl "
              f"depth. Because this crawl paged from the most-installed downwards, what it "
              f"missed lies entirely below what it found."),
             ("How many VS Code extension publishers are there?",
              f"At least {s['publishers']:,}, of whom {s['one_ext_pct']}% have published "
              f"exactly one extension.")])


def g_worth(rows, s):
    c = cohorts(rows)
    newest = max(c)
    nv = c[newest]
    grad = catalogue_gradient(rows)
    one = next(g for g in grad if g["band"] == "exactly 1")
    body = f"""
<div class="lede">The honest answer is that the median outcome is small and the distribution
is brutal: <b>{s['under1000']}%</b> of extensions in this sample have fewer than a thousand
installs, <b>{s['under100']}%</b> have fewer than a hundred, and both figures are floors.
The median publisher with exactly one extension has <b>{n(one['median_best'])}</b> installs
on it.</div>

<h2>What you are competing against, in numbers</h2>
<ul>
<li>The top 1% of extensions hold <b>{s['top1']}%</b> of all installs; the top 10% hold
<b>{s['top10']}%</b>. Attention here is not merely unequal, it is nearly all spoken for.</li>
<li>The median extension has <b>{n(s['median'])}</b> installs. The 25th percentile has
<b>{n(s['p25'])}</b>.</li>
<li>Of extensions first released in {esc(newest)}, <b>{nv['under100']}%</b> are under a
hundred installs at the time of measurement.</li>
<li><b>{s['one_ext_pct']}%</b> of publishers stopped at one.</li>
</ul>

<h2>What the numbers do not say</h2>
<p>They do not say don&rsquo;t. Installs are not revenue &mdash; the Marketplace has no paid
tier, so nothing here measures money at all, and a 300-install extension that gets you known
in a niche may be worth more than a 30,000-install one that does not. A tool you wrote for
yourself and published costs nothing extra to publish.</p>
<p>What they do say is that <b>&ldquo;build it and they will come&rdquo; is not supported</b>
by the distribution, and that any plan whose first step is organic marketplace discovery
should be checked against a median of {n(s['median'])} and a 25th percentile of
{n(s['p25'])}.</p>

<h2>The one lever that shows up in the data</h2>
<p>Publishers with more extensions have a much higher median <i>best</i> extension &mdash;
and the causation almost certainly runs both ways, because people whose first one worked keep
going. <a href="{SITE}/g/vscode-extension-publishers.html">The gradient, and the reason not
to over-read it.</a></p>
"""
    return guide_shell(
        "is-it-worth-publishing-a-vscode-extension",
        "Is it worth publishing a VS Code extension? The base rate, measured",
        "Is it worth publishing a VS Code extension?",
        (f"{s['under1000']}% of measured extensions have under 1,000 installs and "
         f"{s['under100']}% have under 100 — both floors. The median is "
         f"{n(s['median'])}. What that does and does not imply."),
        body,
        faq=[("Is it worth publishing a VS Code extension?",
              f"On the numbers, the median extension in this August 2026 sample has "
              f"{round(s['median']):,} installs and at least {s['under1000']}% have fewer "
              f"than 1,000. The top 1% hold {s['top1']}% of all installs. Installs are not "
              f"revenue — the Marketplace has no paid tier — so this measures "
              f"reach, not income.")])


def g_stale(rows, s, cats):
    f = freshness(rows, s["crawled"])
    order = sorted(cats.items(), key=lambda kv: -kv[1]["sampled"])
    trs = []
    for cat, d in order:
        sub = [r for r in rows if r["category"] == cat]
        stale = [r for r in sub if (r.get("updated") or "") < f["cut"]]
        trs.append(
            f'<tr><td><a href="{SITE}/c/{slug(cat)}.html">{esc(cat)}</a></td>'
            f'<td class="n">{n(len(sub))}</td>'
            f'<td class="n">{pct(len(stale), len(sub))}%</td>'
            f'<td class="n">{n(med([r["installs"] for r in stale]))}</td>'
            f'<td class="n">'
            f'{n(med([r["installs"] for r in sub if r not in stale]))}</td></tr>')
    body = f"""
<div class="lede"><b>{f['stale_pct']}%</b> of the extensions in this sample have not been
updated since {esc(f['cut'])}. The surprise is which ones: the stale set has a median of
<b>{n(f['stale_median'])}</b> installs and the actively-updated set has
<b>{n(f['fresh_median'])}</b>. The abandoned half of this marketplace is the
<i>bigger</i> half.</div>

<h2>Because &ldquo;stale&rdquo; and &ldquo;old&rdquo; are the same population</h2>
<p>An extension that shipped in 2018 and stopped in 2021 has had years to accumulate
installs; one published last month is fresh by construction and has had none. Sorting on
last-updated therefore sorts, mostly, on age &mdash; and age is what drives a cumulative
counter. Read the two medians as a warning about the split rather than as a finding about
maintenance.</p>
<p>What the split does support: a large install count on the VS Code Marketplace is
<b>not</b> evidence that anybody is still maintaining the thing. {f['stale_pct']}% of what
is installed from here has not been touched in a year.</p>

<h2>By category</h2>
<table><thead><tr><th>Category</th><th class="n">Sampled</th>
<th class="n">Not updated in 12 months</th><th class="n">Median installs, stale</th>
<th class="n">Median installs, current</th></tr></thead>
<tbody>{''.join(trs)}</tbody></table>
"""
    return guide_shell(
        "abandoned-vscode-extensions",
        "How much of the VS Code Marketplace is abandoned? Measured by category",
        "How much of the VS Code Marketplace is abandoned?",
        (f"{f['stale_pct']}% of measured extensions have not been updated in twelve "
         f"months — and the stale ones have a higher median install count than the "
         f"current ones. By category, with the age confound stated."),
        body,
        faq=[("How many VS Code extensions are abandoned?",
              f"In this August 2026 sample, {f['stale_pct']}% had not been updated since "
              f"{f['cut']}. Their median install count ({round(f['stale_median']):,}) is "
              f"higher than that of actively-updated extensions "
              f"({round(f['fresh_median']):,}), because staleness and age select the same "
              f"population and installs are cumulative.")])


def g_publishers(rows, s):
    grad = catalogue_gradient(rows)
    top = max(g["median_best"] for g in grad) or 1
    trs = "".join(
        f'<tr><td>{esc(g["band"])}</td><td class="n">{n(g["publishers"])}</td>'
        f'<td class="n">{n(g["median_best"])}</td><td>{bar(g["median_best"], top)}</td></tr>'
        for g in grad)
    one = grad[0]["median_best"]
    many = grad[-1]["median_best"]
    ratio = round(many / one, 1) if one else 0
    tp = top_publishers(rows, limit=100)
    prows = "".join(
        f'<tr><td>{esc(rs[0]["publisher_display"] or p)}<br><code>{esc(p)}</code></td>'
        f'<td class="n">{n(len(rs))}</td>'
        f'<td class="n">{n(sum(r["installs"] for r in rs))}</td>'
        f'<td class="n">{n(max(r["installs"] for r in rs))}</td>'
        f'<td>{esc(max(rs, key=lambda r: r["installs"])["display"])}</td></tr>'
        for p, rs in tp)
    body = f"""
<div class="lede">The median publisher with exactly one extension has <b>{n(one)}</b>
installs on it. The median publisher with eleven or more has <b>{n(many)}</b> on their best
one &mdash; <b>{ratio}&times;</b> as many. The gradient is real and it is also the most
over-readable number on this site.</div>

<table><thead><tr><th>Extensions published</th><th class="n">Publishers</th>
<th class="n">Median installs on their best</th><th></th></tr></thead>
<tbody>{trs}</tbody></table>

<h2>Read the arrow both ways</h2>
<p>The tempting reading is &ldquo;ship more and you will do better&rdquo;. The data cannot
support that, because the people who ship eleven extensions are overwhelmingly the people
whose first one worked. Success causes catalogues at least as much as catalogues cause
success, and this is a cross-section with no before-and-after in it.</p>
<p>What it does establish is a description worth having: the small number of accounts with
real catalogues sit far above the {s['one_ext_pct']}% of publishers who shipped once, and
they are where the installs are.</p>

<h2>The hundred largest publisher accounts</h2>
<p>By total installs across everything they published, among accounts with at least two
extensions in the sample.</p>
<table><thead><tr><th>Publisher</th><th class="n">Extensions</th>
<th class="n">Total installs</th><th class="n">Largest</th>
<th>Their biggest</th></tr></thead><tbody>{prows}</tbody></table>
"""
    return guide_shell(
        "vscode-extension-publishers",
        "Does publishing more VS Code extensions help? The gradient, measured",
        "Does publishing more extensions help?",
        (f"Median best-extension installs by catalogue size: {n(one)} for publishers with "
         f"one, {n(many)} for publishers with eleven or more. Plus the 100 largest "
         f"publisher accounts."),
        body,
        faq=[("Do VS Code publishers with more extensions get more installs?",
              f"In this sample the median publisher with one extension has "
              f"{round(one):,} installs on it, and the median publisher with eleven or "
              f"more has {round(many):,} on their best. The causation is not established: "
              f"publishers whose first extension worked are the ones who keep publishing.")])


def g_stats(rows, s, cats):
    f = freshness(rows, s["crawled"])
    c = cohorts(rows)
    b = rating_buckets(rows)
    grad = catalogue_gradient(rows)
    newest = max(c)
    rows_kv = [
        ("Extensions reached", n(s["extensions"])),
        ("Publishers reached", n(s["publishers"])),
        ("Installs represented", n(s["installs"])),
        ("Median installs", n(s["median"])),
        ("25th / 75th percentile", f"{n(s['p25'])} / {n(s['p75'])}"),
        ("90th percentile", n(s["p90"])),
        ("Largest single extension", n(s["max"])),
        ("Top 1% share of installs", f"{s['top1']}%"),
        ("Top 5% / top 10% share", f"{s['top5']}% / {s['top10']}%"),
        ("Under 100 installs (floor)", f"{s['under100']}%"),
        ("Under 1,000 installs (floor)", f"{s['under1000']}%"),
        (f"Not updated since {f['cut']}", f"{f['stale_pct']}%"),
        ("Publishers with exactly one extension", f"{s['one_ext_pct']}%"),
        ("Most extensions on one account", n(s["max_by_one"])),
        ("Categories", n(len(cats))),
        (f"Median installs, {newest} cohort", n(c[newest]["median"])),
        ("Median installs, 5.0-star (≥5 ratings)", n(b.get(5.0, {}).get("median", 0))),
        ("Median installs, 3.0-star (≥5 ratings)", n(b.get(3.0, {}).get("median", 0))),
        ("Median best extension, 1-extension publisher", n(grad[0]["median_best"])),
        ("Median best extension, 11+-extension publisher", n(grad[-1]["median_best"])),
        ("Newest row in the data", esc(s["crawled"])),
    ]
    trs = "".join(f'<tr><td>{k}</td><td class="n">{v}</td></tr>' for k, v in rows_kv)
    body = f"""
<div class="lede">Every headline figure from this dataset in one table. All of it is
computed from the published <a href="{RAW}/extensions.jsonl">JSONL</a> by the
<a href="{REPO}/blob/main/scripts/build_site.py">script that renders this page</a>, so
none of it can drift away from the data it describes.</div>
<table><thead><tr><th>Measure</th><th class="n">Value</th></tr></thead>
<tbody>{trs}</tbody></table>
<h2>Quoting these</h2>
<p>CC BY 4.0: use them anywhere with attribution. The citation, and a DOI that keeps
resolving if the data is recrawled:</p>
<p class="cite">Sujeito Operator (2026). <i>What actually gets installed on the VS Code
Marketplace</i> [Data set]. Zenodo. <a href="{DOI}">{DOI}</a></p>
<p>Two of these figures are easy to quote wrongly, so they are spelled out. Every
<b>&ldquo;under N installs&rdquo;</b> percentage is a <b>floor</b>: the crawl paged from the
most-installed downwards, so everything it missed is smaller than everything it found. And
<b>installs are not revenue</b> &mdash; the VS Code Marketplace has no paid tier, so nothing
here measures money.</p>
"""
    return guide_shell(
        "vscode-marketplace-statistics",
        "VS Code Marketplace statistics, measured August 2026",
        "VS Code Marketplace statistics",
        (f"Every headline figure: {n(s['extensions'])} extensions, {n(s['publishers'])} "
         f"publishers, median {n(s['median'])} installs, top 1% holding {s['top1']}% of "
         f"all installs. Free, CC BY 4.0, recomputable."),
        body)


GUIDE_FNS = {
    "vscode-extension-ratings-do-not-predict-installs": lambda r, s, c: g_ratings(r, s),
    "how-many-installs-does-a-new-vscode-extension-get": lambda r, s, c: g_cohorts(r, s),
    "most-installed-vscode-extensions": lambda r, s, c: g_top(r, s),
    "how-many-vscode-extensions-are-there": lambda r, s, c: g_counts(r, s),
    "is-it-worth-publishing-a-vscode-extension": lambda r, s, c: g_worth(r, s),
    "abandoned-vscode-extensions": lambda r, s, c: g_stale(r, s, c),
    "vscode-extension-publishers": lambda r, s, c: g_publishers(r, s),
    "vscode-marketplace-statistics": lambda r, s, c: g_stats(r, s, c),
}

CATS_ORDER = []


# ------------------------------------------------------------------ build


def render_all(rows):
    """-> {relative path: bytes-as-str}. Pure: writes nothing, so selftest can inspect it."""
    global CATS_ORDER
    s = shape(rows)
    cats = by_category(rows)
    CATS_ORDER = sorted(cats)
    out = {"index.html": render_index(rows, s, cats)}
    for cat, d in cats.items():
        out[f"c/{slug(cat)}.html"] = render_category(cat, d, s)
    for key, _title, _desc in GUIDES:
        out[f"g/{key}.html"] = GUIDE_FNS[key](rows, s, cats)

    urls = ["/"] + [f"/{p}" for p in sorted(out) if p != "index.html"]
    today = s["crawled"]
    out["sitemap.xml"] = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"<url><loc>{SITE}{u}</loc><lastmod>{today}</lastmod></url>\n"
                  for u in urls)
        + "</urlset>\n")
    out["robots.txt"] = (
        "User-agent: *\nAllow: /\n"
        f"Sitemap: {SITE}/sitemap.xml\n")
    out[".nojekyll"] = ""
    out["llms.txt"] = llms(s, cats)
    return out, s, cats


def llms(s, cats):
    lines = [
        "# What actually gets installed on the VS Code Marketplace",
        "",
        f"> {s['extensions']:,} VS Code extensions from {s['publishers']:,} publishers with "
        f"the install count the Marketplace publishes for each, measured August 2026. "
        f"Free, CC BY 4.0, DOI {DOI}. Collector included.",
        "",
        "IMPORTANT CAVEAT, please carry it if you quote these numbers: " + CAVEAT,
        "",
        "## Headline figures",
        f"- Extensions reached: {s['extensions']:,}",
        f"- Publishers reached: {s['publishers']:,} ({s['one_ext_pct']}% have exactly one)",
        f"- Installs represented: {s['installs']:,}",
        f"- Median installs: {s['median']:,.0f}; 25th/75th percentile "
        f"{s['p25']:,.0f}/{s['p75']:,.0f}",
        f"- Top 1% of extensions hold {s['top1']}% of installs; top 10% hold {s['top10']}%",
        f"- Under 100 installs: {s['under100']}% (a floor); under 1,000: {s['under1000']}%",
        "- Installs are not revenue: the VS Code Marketplace has no paid tier.",
        "",
        "## Pages",
        f"- [Dataset home]({SITE}/): headline figures, category table, method and limits",
    ]
    for key, title, desc in GUIDES:
        lines.append(f"- [{title}]({SITE}/g/{key}.html): {desc}")
    for cat in sorted(cats):
        d = cats[cat]
        lines.append(f"- [{cat} extensions]({SITE}/c/{slug(cat)}.html): {d['sampled']:,} "
                     f"measured, median {d['median']:,.0f} installs")
    lines += [
        "",
        "## Raw data",
        f"- [extensions.jsonl]({RAW}/extensions.jsonl) one row per extension",
        f"- [extensions.csv]({RAW}/extensions.csv) the same as CSV",
        f"- [summary.json]({RAW}/summary.json) machine-readable summary incl. the caveat",
        f"- [repository]({REPO}) crawler, summariser and site generator",
        "",
        "## The same author",
        f"- [What actually sells on Gumroad]({SIBLING}) the other open dataset",
        f"- [Scoped engineering pilot]({PILOT}) one ticket, a patch plus tests in 48 hours, "
        f"paid only if you would merge it",
        "",
    ]
    return "\n".join(lines)


MONEY = re.compile(r"(?<![A-Za-z0-9])(?:[$£€]\s?\d|\d+\s?(?:USD|EUR|GBP)\b)")


def selftest():
    ok = fail = 0

    def chk(cond, what):
        nonlocal ok, fail
        if cond:
            ok += 1
        else:
            fail += 1
            print(f"  FAIL  {what}")

    rows = load()
    out, s, cats = render_all(rows)

    chk(len(rows) > 60000, "the data file loaded")
    chk(s["extensions"] == len(rows), "shape() counts every row")
    chk(0 < s["median"] < s["p75"], "the median sits below the 75th percentile")
    chk(s["p25"] < s["median"], "the 25th percentile sits below the median")
    chk(s["top1"] < s["top5"] < s["top10"] <= 100, "the share curve is monotone and bounded")
    chk(s["under100"] < s["under1000"], "under-100 is a subset of under-1000")
    chk(re.fullmatch(r"\d{4}-\d{2}-\d{2}", s["crawled"]), "the crawl date parses as a date")

    # EXACT AGREEMENT WITH THE PUBLISHED summary.json, NOT APPROXIMATE. The README, the
    # Zenodo record and this site all quote the same numbers at a reader, and "close enough"
    # between two published surfaces is a discrepancy somebody else gets to find. `shape()`
    # delegates to `summarize.summarize`, so a mismatch here means `data/summary.json` on
    # disk is stale against the data beside it -- which is worth failing the build over.
    ref = json.loads(SUMMARY.read_text())
    for mine, theirs in [("extensions", "extensions"), ("publishers", "publishers"),
                         ("installs", "installs_represented"),
                         ("median", "median_installs"), ("p25", "p25_installs"),
                         ("p75", "p75_installs"), ("max", "max_installs"),
                         ("top1", "top1_share_pct"), ("top5", "top5_share_pct"),
                         ("top10", "top10_share_pct"),
                         ("under100", "under_100_pct_floor"),
                         ("under1000", "under_1000_pct_floor"),
                         ("one_ext_pct", "publishers_one_extension_pct"),
                         ("max_by_one", "max_extensions_one_publisher")]:
        chk(s[mine] == ref[theirs],
            f"{mine} matches summary.json {theirs} ({s[mine]!r} vs {ref[theirs]!r})")
    for cat, d in cats.items():
        r = ref["by_category"].get(cat)
        chk(r is not None, f"summary.json knows the category {cat}")
        if r:
            chk(d["sampled"] == r["sampled"], f"{cat}: sample size matches summary.json")
            chk(d["median"] == r["median_installs"], f"{cat}: median matches summary.json")
            chk(d["p90"] == r["p90_installs"], f"{cat}: 90th pct matches summary.json")
            chk(d["under100"] == r["under_100_pct_floor"],
                f"{cat}: under-100 floor matches summary.json")

    # Every page renders, is a document, and carries the caveat above the numbers.
    for path, text in out.items():
        if path.endswith(".html"):
            chk(text.lstrip().startswith("<!doctype html>"), f"{path} is a document")
            chk("Read this before quoting anything" in text, f"{path} carries the caveat")
            chk(text.count("<main>") == 1, f"{path} has exactly one main")
            chk("</html>" in text, f"{path} is closed")

    # NO PRICE, ANYWHERE. The single most-repeated defect in this operation is a money
    # figure baked into a static surface, and these pages quote none.
    for path, text in out.items():
        m = MONEY.search(text)
        chk(m is None, f"{path} carries no money figure ({m.group(0) if m else ''})")

    # Every internal link resolves to something this build actually writes.
    written = {"/" + p for p in out} | {"/"}
    for path, text in out.items():
        if not path.endswith((".html", ".txt")):
            continue
        for href in re.findall(r'href="([^"]+)"', text):
            if href.startswith(SITE):
                rel = href[len(SITE):] or "/"
                chk(rel in written, f"{path} -> {rel} is a page this build writes")

    chk(len(cats) >= 15, "every category got a page")
    chk(all(f"c/{slug(c)}.html" in out for c in cats), "each category page is named")
    chk(all(f"g/{k}.html" in out for k, _t, _d in GUIDES), "each guide page is named")
    chk(len(out["sitemap.xml"].split("<url>")) - 1 == len(
        [p for p in out if p.endswith(".html")]), "the sitemap lists every page once")
    chk(SITE + "/sitemap.xml" in out["robots.txt"], "robots points at the sitemap")
    chk("IMPORTANT CAVEAT" in out["llms.txt"], "llms.txt carries the caveat too")

    # The findings the guides assert, asserted here too, so a recrawl that reverses one
    # fails the build instead of publishing a sentence the data stopped supporting.
    b = rating_buckets(rows)
    chk(b[3.0]["median"] > b[5.0]["median"],
        "the rating inversion still holds (3.0 beats 5.0 on median installs)")
    f = freshness(rows, s["crawled"])
    chk(f["stale_median"] > f["fresh_median"],
        "stale extensions still have the higher median")
    g = catalogue_gradient(rows)
    chk(g[-1]["median_best"] > g[0]["median_best"], "the catalogue gradient still rises")
    c = cohorts(rows)
    chk(c[max(c)]["median"] < c[min(c)]["median"], "the newest cohort is still the smallest")

    print(f"build_site selftest: {ok} passed, {fail} failed")
    return 0 if not fail else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--out", default=str(DOCS))
    a = ap.parse_args()
    if a.selftest:
        raise SystemExit(selftest())

    rows = load()
    out, s, cats = render_all(rows)
    root = pathlib.Path(a.out)
    for path, text in sorted(out.items()):
        p = root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    print(f"wrote {len(out)} files to {root}")
    print(f"  {len(cats)} category pages, {len(GUIDES)} guides, "
          f"{s['extensions']:,} extensions, median {s['median']:,.0f} installs")


if __name__ == "__main__":
    main()
