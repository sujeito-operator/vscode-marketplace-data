#!/usr/bin/env python3
"""Apply the publication omissions to a crawl, and refuse to write if one survives.

Two classes of row are collected by `crawl.py` and not published here. Both are the same
underlying problem — **a public identifier that has the shape of a secret** — and neither is
a judgement that the row is bad data:

  base32   The publisher id is a 52-character base32 string. GitHub's secret scanner reads
           that as an Azure DevOps personal access token and blocks the push. 24 rows.
           Handled since 2026-08-08.

  uuid     The publisher id is a bare UUID. GitHub's partner pattern for an **Open VSX
           access token** matches exactly that, and it is also the shape the field ends up
           with when a token reaches the slot a namespace should occupy. GitHub opened an
           alert against this repository on 2026-08-08 and against a fork of it on
           2026-08-11, six minutes after that fork was pushed. 26 rows.

Whether those UUIDs are live tokens or publishers who genuinely registered a UUID-shaped
namespace does not change what to do, and is not worth resolving by firing somebody else's
credential at Open VSX. A dataset that ships them is a credential dump either way, and
26 of 64,490 rows is 0.04% of the crawl.

The rows are dropped **after** the file-to-file fidelity checks pass, so faithfulness to the
crawl is proved before anything is excluded, and the omission is then shown to be immaterial
by reconciling every published figure against the previous one.

`scan()` is the rail: after everything is written, every shipped file is searched for a
surviving secret-shaped token and the script exits non-zero if one is found. This is the
check GitHub's scanner does, run before GitHub does it. It used to be a comment saying the
`publisher` field ought to be checked one day. A comment is not a rail.
"""
import csv, json, pathlib, re, sys

REPO = pathlib.Path(__file__).resolve().parent.parent
DATA = REPO / "data"

# A field that is nothing but the secret shape. Anchored: a publisher id that merely
# contains a hex run is not one of these.
UUID_FIELD = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
                        r"[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
B32_FIELD = re.compile(r"^[a-z2-7]{52}$", re.I)

# The same shapes anywhere inside a written file. Delimited rather than anchored, because
# the `id` column is `publisher.name` and a UUID publisher therefore appears there too —
# dropping the row on `publisher` alone while leaving the `id` behind would ship the token
# in a different column. Measured after the drop: zero occurrences survive.
UUID_ANYWHERE = re.compile(r"(?<![0-9A-Za-z-])[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
                           r"[0-9a-f]{4}-[0-9a-f]{12}(?![0-9A-Za-z-])", re.I)
B32_ANYWHERE = re.compile(r"(?<![0-9A-Za-z])[a-z2-7]{52}(?![0-9A-Za-z])")

# Display names are served to anyone by the public API and two publishers pasted a publish
# command into theirs. Those are redacted in place rather than dropped -- the extension is
# real and its install count is real. The README says so.
REDACTION = "[REDACTED-CREDENTIAL]"
# A publish command *with a secret attached*, not the phrase "vsce publish". The README has
# to be able to say what it redacted and why; a rail that forbids naming the problem makes
# the disclosure unwritable. `<token>` is a placeholder and is 7 characters, so the length
# floor is what separates the explanation from the thing being explained.
CREDENTIAL_CMD = re.compile(r"(?:vsce|ovsx)\s+publish\s+(?:-p|--pat)\s+\S{15,}"
                            r"|(?:^|\s)(?:-p|--pat)\s+[A-Za-z0-9._~+/=-]{20,}", re.I)


def omission_class(row):
    """Which omission class this row falls in, or None if it is publishable."""
    for k, v in row.items():
        v = str(v).strip()
        if UUID_FIELD.match(v):
            return "uuid"
        if B32_FIELD.match(v):
            return "base32"
    return None


def scan(paths):
    """Refuse to ship if a secret-shaped token survived anywhere in any written file."""
    for p in sorted(paths):
        text = p.read_text(encoding="utf-8", errors="replace")
        for label, rx in (("UUID / Open VSX token", UUID_ANYWHERE),
                          ("base32 / Azure DevOps PAT", B32_ANYWHERE)):
            hits = rx.findall(text)
            if hits:
                line = text[:text.index(hits[0])].count("\n") + 1
                sys.exit(f"REFUSING: {p.name}:{line} still carries a {label} shaped token "
                         f"({len(hits)} in this file). Nothing was published.")
        if CREDENTIAL_CMD.search(text.replace(REDACTION, "")):
            sys.exit(f"REFUSING: {p.name} carries a publish command with a secret beside it.")
    print(f"  OK  no secret-shaped token in any of {len(paths)} shipped files")


def load():
    """Both published files, checked against each other before anything is removed."""
    with (DATA / "extensions.csv").open(newline="", encoding="utf-8") as fh:
        csv_rows = list(csv.DictReader(fh))
    json_rows = [json.loads(l) for l in (DATA / "extensions.jsonl").open(encoding="utf-8")]

    if len(csv_rows) != len(json_rows):
        sys.exit(f"REFUSING: csv has {len(csv_rows):,} rows, jsonl has {len(json_rows):,}. "
                 "The two published files do not describe the same crawl.")
    if [r["id"] for r in csv_rows] != [r["id"] for r in json_rows]:
        sys.exit("REFUSING: csv and jsonl disagree on the id column, row for row.")
    if list(csv_rows[0]) != list(json_rows[0]):
        sys.exit(f"REFUSING: field sets differ — csv {list(csv_rows[0])}, "
                 f"jsonl {list(json_rows[0])}.")
    print(f"  ok  csv and jsonl agree: {len(json_rows):,} rows, "
          f"{len(json_rows[0])} fields, ids identical row for row")
    return json_rows          # typed; the csv is written back out from these


def write(rows, fields):
    with (DATA / "extensions.jsonl").open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    with (DATA / "extensions.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


ROW_RE = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([\d,]+)\s*\|$", re.M)


def previously_omitted():
    """The rows an earlier run already withheld, read back out of the document itself.

    They are gone from the published files, so this document is the only surviving record
    of them. Regenerating it from the published files alone would silently drop 24 rows
    from the list of dropped rows, which is the failure this whole file exists to avoid.

    Each row keeps the class it was withheld under. Reading them all back as one bucket
    would work on the first run and mislabel every UUID row as base32 on the second, which
    is a lie that only appears when the script is run twice -- so it is parsed per section.
    """
    doc = DATA / "omitted-rows.md"
    if not doc.exists():
        return {}
    text = doc.read_text(encoding="utf-8")

    def rows(chunk):
        return [{"name": n, "category": c, "installs": int(i.replace(",", ""))}
                for n, c, i in ROW_RE.findall(chunk) if n != "Extension"]

    out = {"uuid": [], "base32": []}
    sections = text.split("\n## ")[1:]
    if not sections:
        # The document this replaced had one unsectioned table, and every row in it was
        # withheld for the base32 reason -- its own title says so.
        out["base32"] = rows(text)
        return out
    for chunk in sections:
        out["uuid" if "UUID" in chunk.split("\n", 1)[0] else "base32"] += rows(chunk)
    return out


def omitted_doc(by_class, crawl_total):
    """The omissions, listed so that nothing is hidden by being removed."""
    n = sum(len(v) for v in by_class.values())
    installs = sum(int(r["installs"]) for v in by_class.values() for r in v)

    def table(rs):
        rs = sorted(rs, key=lambda r: -int(r["installs"]))
        head = "| Extension | Category | Installs |\n|---|---|---:|\n"
        return head + "\n".join(
            f"| {r['name']} | {r['category']} | {int(r['installs']):,} |" for r in rs)

    return f"""# The {n} rows omitted from the published files

These extensions exist and were collected. Each one is omitted for the same reason: its
**publisher id has the shape of a secret**, and a dataset that ships it is a credential
dump whether or not the string is live. They are listed here in full so that nothing is
hidden by being removed, and `scripts/crawl.py` regenerates the complete set including
them — run `scripts/scrub.py` afterwards to reproduce exactly the files published here.

Combined installs across all {n}: {installs:,}. {n} of {crawl_total:,} collected rows is
{n / crawl_total * 100:.2f}% of the crawl, and it moves no headline figure in the README.

## {len(by_class['uuid'])} rows: publisher id is a bare UUID

GitHub's secret scanning matches a bare UUID as an **Open VSX access token**, and it is also
the shape this field takes when a publish token reaches the slot a namespace should occupy.
They were **not tested against Open VSX** — that would mean using somebody else's credential,
and the decision to omit them does not depend on the answer.

{table(by_class['uuid'])}

## {len(by_class['base32'])} rows: publisher id is a 52-character base32 string

GitHub's secret scanning misclassifies this as an Azure DevOps personal access token, which
blocks any push containing them. These are public identifiers, not credentials — the
unauthenticated Marketplace API returns them on request.

{table(by_class['base32'])}
"""


def main():
    rows = load()
    fields = list(rows[0])
    before = {"extensions": len(rows), "publishers": len({r["publisher"] for r in rows}),
              "installs": sum(int(r["installs"]) for r in rows)}

    dropped = [(r, c) for r in rows if (c := omission_class(r))]
    kept = [r for r in rows if not omission_class(r)]

    # Redact in place rather than drop: the extension is real and so is its install count.
    changed = 0
    for r in kept:
        if CREDENTIAL_CMD.search(str(r.get("publisher_display", ""))):
            r["publisher_display"] = REDACTION
            changed += 1
    # Count what the SHIPPED files carry, not what this run changed. The README quotes this
    # number, and on a second run nothing needs changing -- reporting the delta would
    # publish "0 redacted display names" over two rows that are redacted.
    redacted = sum(1 for r in kept if str(r.get("publisher_display", "")) == REDACTION)

    if not dropped:
        print("  --  nothing to drop; the published files are already scrubbed")
    else:
        counts = {c: sum(1 for _, k in dropped if k == c) for _, c in dropped}
        print(f"  --  dropping {len(dropped)} row(s) "
              f"({', '.join(f'{v} {k}' for k, v in sorted(counts.items()))}) — "
              f"{len(dropped) / len(rows) * 100:.3f}% of the published set, "
              f"{sum(int(r['installs']) for r, _ in dropped):,} installs, "
              f"{len({r['publisher'] for r, _ in dropped})} publishers")
    print(f"  --  {redacted} display name(s) redacted in the shipped files "
          f"({changed} changed by this run)")

    write(kept, fields)

    # Everything ever withheld, not just what this run withheld. The earlier 24 are gone
    # from the published files, so the document is their only record -- read it back.
    by_class = {"uuid": [r for r, c in dropped if c == "uuid"],
                "base32": [r for r, c in dropped if c == "base32"]}
    carried = previously_omitted()
    known = {r["name"] for v in by_class.values() for r in v}
    for cls, rs in carried.items():
        by_class[cls] += [r for r in rs if r["name"] not in known]
    n_omitted = sum(len(v) for v in by_class.values())
    crawl_total = len(kept) + n_omitted

    sys.path.insert(0, str(REPO / "scripts"))
    from summarize import summarize
    s = summarize(kept)
    s["omitted"] = {
        "rows": n_omitted,
        "uuid_publisher": len(by_class["uuid"]),
        "base32_publisher": len(by_class["base32"]),
        "installs": sum(int(r["installs"]) for v in by_class.values() for r in v),
        "uuid_installs": sum(int(r["installs"]) for r in by_class["uuid"]),
        "base32_installs": sum(int(r["installs"]) for r in by_class["base32"]),
        "crawl_total": crawl_total,
        "reason": "Publisher id has the shape of a secret (Open VSX token / Azure DevOps "
                  "PAT). Listed in full in data/omitted-rows.md.",
        "display_names_redacted": redacted,
    }
    (DATA / "summary.json").write_text(json.dumps(s, indent=1) + "\n", encoding="utf-8")

    # The omission has to be shown immaterial, not asserted to be. Reconcile against the
    # figures that were published before it, and name anything that moved.
    print(f"  --  extensions {before['extensions']:,} -> {s['extensions']:,}"
          f"   publishers {before['publishers']:,} -> {s['publishers']:,}"
          f"   installs {before['installs']:,} -> {s['installs_represented']:,}")
    if before["extensions"] - len(dropped) != s["extensions"]:
        sys.exit("REFUSING: kept + dropped does not reconcile to the published count.")

    (DATA / "omitted-rows.md").write_text(
        omitted_doc(by_class, crawl_total), encoding="utf-8")

    from build_readme import build, gate, no_offer
    gate(s)
    readme = build(s)
    no_offer(readme)
    (REPO / "README.md").write_text(readme, encoding="utf-8")
    print("  ok  README regenerated from the summary that describes the shipped files")

    scan([p for p in DATA.iterdir() if p.is_file()] + [REPO / "README.md"])


if __name__ == "__main__":
    main()
