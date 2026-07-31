#!/usr/bin/env python3
"""echo-audit.py — corpus-level sameness advisory for sanctum-docs.

story-check proves each page has a hook, a spine, cast, a landing. Nothing
proves the pages aren't all pulling the SAME hook and the SAME landing — and
after the 2026-07 narrative sweep they measurably were: 23% of the corpus
landed on Tommy and 14% opened on a clock time. A surprise used 69 times is a
stamp. This audit names the echoes so the weekly health issue surfaces them;
it never fails a page, because sameness is a property of the book, not of any
single chapter.

Budgets are editorial taste, written down (measured 2026-07-31, after the
sweep). Exceeding one is a nudge to vary the next pages you touch — or to run
a de-tic pass — not a build failure.

Regex and arithmetic only. Always exits 0. Output lines are prefixed `note:`
so health-audit.yml's FAIL/warn counters ignore them.

Usage:
  echo-audit.py            # audit the corpus, print the report
"""
import glob
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "src", "content", "docs")

# device -> (budget as fraction of corpus, detector)
OPENING_DEVICES = {
    "clock-time cold open": (0.08, re.compile(
        r"\b\d{1,2}[:h]\d{2}\b|\b\d{1,2}\s?(AM|A\.M\.)\b")),
}
LANDING_CAST_BUDGET = 0.10          # any single character closing >10% of the book
# A BOLTED cameo is the precise defect: a landing that names a character who
# appears nowhere else on the page. The 2026-07 sweep created 54 of them by
# satisfying cast/alt-text-cameo the cheapest way available — one closing line.
# An earned cameo (the character is present earlier) is fine at any volume.
BOLTED_BUDGET = 0.05
# Tic budget is per 100 pages, not absolute. An absolute 12 was miscalibrated
# for a 300-page book: a phrase used once on 26 different pages is house voice,
# not a tic — a reader meets it every tenth page. A tic is felt when it clusters.
TIC_PER_100 = 5.0
TICS = [
    "on purpose.",
    "the whole point",
    "which is how you know",
    "That was always the point",
    "You do not get to",
    "does exactly one thing",
]
LANDING_CAST = ["tommy", "yoda", "windu", "qui-gon", "cilghal", "mundi",
                "jocasta", "mothma", "ahsoka"]


def body_of(path):
    s = open(path, encoding="utf-8").read()
    s = re.sub(r"^---.*?---", "", s, flags=re.S)
    s = re.sub(r"^import .*$", "", s, flags=re.M)
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", s)
    return s.strip()


def main():
    pages = sorted(glob.glob(os.path.join(DOCS, "**", "*.mdx"), recursive=True))
    n = len(pages)
    if not n:
        print("note: no pages found")
        return 0

    open_hits = {k: [] for k in OPENING_DEVICES}
    land_hits = Counter()
    bolted_hits = Counter()
    bolted_pages = []
    tic_hits = Counter()

    for p in pages:
        b = body_of(p)
        rel = os.path.relpath(p, DOCS)
        first = b[:400]
        last, rest = b[-500:].lower(), b[:-500].lower()
        for name, (_, rx) in OPENING_DEVICES.items():
            if rx.search(first):
                open_hits[name].append(rel)
        for who in LANDING_CAST:
            rx = re.compile(r"\b" + re.escape(who) + r"\b")
            if rx.search(last):
                land_hits[who] += 1
                if not rx.search(rest):
                    bolted_hits[who] += 1
                    bolted_pages.append((who, rel))
        low = b.lower()
        for t in TICS:
            tic_hits[t] += low.count(t.lower())

    print(f"note: echo audit — {n} pages (advisory; budgets are taste, not law)")
    over = 0
    for name, (budget, _) in OPENING_DEVICES.items():
        got = len(open_hits[name])
        pct = got / n
        flag = "OVER" if pct > budget else "ok"
        if pct > budget:
            over += 1
        print(f"note:   opening «{name}»: {got}/{n} ({pct:.0%}) — budget {budget:.0%} [{flag}]")
    for who, got in land_hits.most_common():
        pct = got / n
        if pct > LANDING_CAST_BUDGET:
            over += 1
            print(f"note:   landing on «{who}»: {got}/{n} ({pct:.0%}) — budget {LANDING_CAST_BUDGET:.0%} [OVER]")
    for who, got in bolted_hits.most_common():
        pct = got / n
        flag = "OVER" if pct > BOLTED_BUDGET else "ok"
        if pct > BOLTED_BUDGET:
            over += 1
        print(f"note:   BOLTED cameo «{who}» (named only in the closing beat): "
              f"{got}/{n} ({pct:.0%}) — budget {BOLTED_BUDGET:.0%} [{flag}]")
        if flag == "OVER":
            for w, rel in [x for x in bolted_pages if x[0] == who][:8]:
                print(f"note:       {rel}")
    for t, got in tic_hits.most_common():
        per100 = got * 100.0 / n
        if per100 > TIC_PER_100:
            over += 1
            print(f"note:   tic «{t}»: {got}× = {per100:.1f} per 100 pages — "
                  f"budget {TIC_PER_100} [OVER]")
    if over:
        print(f"note: {over} echo(es) over budget — vary the device on the next pages "
              f"you touch, or schedule a de-tic pass. A beat repeated this often "
              f"stops being a beat.")
    else:
        print("note: no echoes over budget — the book still varies its music")
    return 0


if __name__ == "__main__":
    sys.exit(main())
