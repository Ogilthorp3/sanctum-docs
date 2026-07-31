#!/usr/bin/env python3
"""story-check.py — the narrative gate for sanctum-docs.

`contrib-check.py` proves a page is correct. Nothing proved anyone would read
it, and over five months the site quietly became a filing cabinet with
excellent metadata. This is the missing half: shape, not accuracy.

It measures what arithmetic can see — how a page opens, whether it has a
spine, whether anybody is in the room, how it lands — and it is deliberately
silent about quality. A page can pass every check here and still be about
nothing. The checker says so out loud in `--explain`.

THE CALIBRATION CONTRACT. Every threshold in this file is anchored to a
measured boundary between pages we hold up as models and pages the drift audit
named. `agents/tommy.mdx` must pass with exactly one warning (`book/no-lineage`,
documented and permanent). A check that fails the gold standard is a broken
check, not a strict one — three otherwise-reasonable checks were rejected
outright for that reason and are named in `--explain` so nobody re-proposes
them. `tests/test_story_check.py` holds the fixture list.

Regex and arithmetic only. No model calls, ever.

Usage:
  story-check.py <paths...>          per-file; exit 1 on any error
  story-check.py --audit             whole corpus, errors demoted to warnings
  story-check.py --backlog --top 25  ranked rewrite queue
  story-check.py --explain <id>      the doctrine paragraph for one check
"""
from __future__ import annotations

import argparse
import json
import pathlib
import posixpath
import re
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ROOT / "src" / "content" / "docs"

# ── genre ────────────────────────────────────────────────────────────────────
# Reference material is allowed to be dry; index pages are allowed to be doors.
# Forcing either to tell a story is how you get whimsy tax on a lookup table.
REFERENCE_PATHS = {
    "architecture/port-summary.mdx", "architecture/services.mdx",
    "operations/feature-status-matrix.mdx", "operations/operational-history.mdx",
}


def genre_of(rel: str, fm: dict) -> str:
    g = (fm.get("genre") or "").strip().lower()
    if g in ("reference", "index"):
        return g
    if rel.startswith("reference/") or rel in REFERENCE_PATHS:
        return "reference"
    leaf = rel.rsplit("/", 1)[-1]
    if leaf.startswith("index") or leaf in ("qc.mdx", "404.mdx"):
        return "index"
    return "chapter"


# ── parser ───────────────────────────────────────────────────────────────────
# A BLOCK parser, not a line filter. contrib-check.py's check_length drops every
# line starting with "|" and counts heading text, JSX and link URLs as prose —
# which is why it reports the gold standard at 1253 words against a 1200 cap.
FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)
FENCE_RE = re.compile(r"^(```|~~~)")
IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)]*)\)")
INLINE_CODE_RE = re.compile(r"`[^`]*`")
LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")
JSX_RE = re.compile(r"</?[A-Z][A-Za-z0-9]*[^>]*/?>")
HTML_RE = re.compile(r"</?[a-z][a-z0-9]*[^>]*/?>")
ASIDE_OPEN_RE = re.compile(r"<Aside\b([^>]*)>")
ASIDE_TYPE_RE = re.compile(r'type=["\'](\w+)["\']')
ASIDE_TITLE_RE = re.compile(r'title=["\']([^"\']*)["\']')


class Block:
    __slots__ = ("kind", "text", "level", "aside", "line")

    def __init__(self, kind, text, level=0, aside=None, line=0):
        self.kind = kind      # prose|heading|code|table|bullet|image|jsx|rule|import
        self.text = text
        self.level = level    # heading level
        self.aside = aside    # enclosing Aside type, if any
        self.line = line


def parse(content: str):
    """Return (frontmatter dict, blocks, alt_texts, body_line_offset)."""
    fm, body, offset = {}, content, 1
    m = FM_RE.match(content)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line and not line.startswith(" "):
                k, _, v = line.partition(":")
                fm[k.strip()] = v.strip().strip("\"'")
        body = content[m.end():]
        offset = content[: m.end()].count("\n") + 1

    alts = [a for a, _ in IMG_RE.findall(body)]
    blocks, buf, in_fence, aside_stack = [], [], False, []
    lines = body.splitlines()

    def flush(ln):
        if not buf:
            return
        raw = "\n".join(buf).strip()
        buf.clear()
        if not raw:
            return
        aside = aside_stack[-1] if aside_stack else None
        if raw.lstrip().startswith("|"):
            blocks.append(Block("table", raw, aside=aside, line=ln))
        elif re.match(r"^\s*([-*+]|\d+\.)\s", raw):
            blocks.append(Block("bullet", raw, aside=aside, line=ln))
        elif IMG_RE.match(raw.strip()) and len(IMG_RE.sub("", raw).strip()) < 3:
            blocks.append(Block("image", raw, aside=aside, line=ln))
        elif raw.startswith("import "):
            blocks.append(Block("import", raw, aside=aside, line=ln))
        elif re.match(r"^\s*(---|\*\*\*|___)\s*$", raw):
            blocks.append(Block("rule", raw, aside=aside, line=ln))
        elif re.match(r"^\s*<[A-Za-z]", raw) and not re.search(r"[.!?]", JSX_RE.sub("", raw)):
            blocks.append(Block("jsx", raw, aside=aside, line=ln))
        else:
            blocks.append(Block("prose", raw, aside=aside, line=ln))

    for i, line in enumerate(lines, start=offset):
        if FENCE_RE.match(line.strip()):
            if in_fence:
                buf.append(line)
                raw = "\n".join(buf)
                buf.clear()
                in_fence = False
                blocks.append(Block("code", raw,
                                    aside=aside_stack[-1] if aside_stack else None, line=i))
            else:
                flush(i)
                in_fence = True
                buf.append(line)
            continue
        if in_fence:
            buf.append(line)
            continue

        if ASIDE_OPEN_RE.search(line):
            flush(i)
            attrs = ASIDE_OPEN_RE.search(line).group(1)
            t = ASIDE_TYPE_RE.search(attrs)
            title = ASIDE_TITLE_RE.search(attrs)
            aside_stack.append(t.group(1).lower() if t else "note")
            blocks.append(Block("jsx", line, aside=aside_stack[-1], line=i))
            if title:
                blocks[-1].text += f" ||title:{title.group(1)}"
            continue
        if "</Aside>" in line:
            flush(i)
            if aside_stack:
                aside_stack.pop()
            continue

        hm = re.match(r"^(#{1,6})\s+(.*)$", line)
        if hm:
            flush(i)
            blocks.append(Block("heading", hm.group(2).strip(), level=len(hm.group(1)),
                                aside=aside_stack[-1] if aside_stack else None, line=i))
            continue
        if not line.strip():
            flush(i)
            continue
        buf.append(line)
    flush(len(lines) + offset)
    return fm, blocks, alts, offset


def clean_prose(text: str) -> str:
    """Strip everything that is not prose the reader reads."""
    t = INLINE_CODE_RE.sub(" ", text)
    t = IMG_RE.sub(" ", t)
    t = LINK_RE.sub(r"\1", t)          # link TEXT survives, target does not
    t = JSX_RE.sub(" ", t)
    t = HTML_RE.sub(" ", t)
    t = re.sub(r"[*_>#`]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


WORD_RE = re.compile(r"[0-9A-Za-zÀ-ÿ]")


def words(text: str) -> list[str]:
    return [w for w in clean_prose(text).split() if WORD_RE.search(w)]


SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'(\[*—-])")


def sentences(text: str) -> list[str]:
    out = []
    for chunk in SENT_SPLIT.split(clean_prose(text)):
        c = chunk.strip()
        if c and WORD_RE.search(c):
            out.append(c)
    return out


TRAILING_RE = re.compile(
    r"^(related|see also|next steps?|what'?s next|what is next|where to go next|"
    r"read next|further reading|references|sources|links|versioning|status|"
    r"annex.*|appendix.*)$", re.I)


def content_blocks(blocks):
    """Blocks that count as the story: no imports, no trailing matter."""
    out, dropping = [], False
    for b in blocks:
        if b.kind == "heading" and b.level <= 2:
            dropping = bool(TRAILING_RE.match(b.text.strip()))
        if dropping or b.kind == "import":
            continue
        out.append(b)
    return out


def prose_blocks(blocks):
    return [b for b in blocks if b.kind == "prose"]


# ── cast lexicon ─────────────────────────────────────────────────────────────
CAST_NAMES = ["tommy", "yoda", "windu", "qui-gon", "quigon", "cilghal", "mundi",
              "jocasta", "mothma", "ahsoka", "aemon", "r2d2", "castellan",
              "gollum", "abyssinian", "deadpool", "hermes", "albert", "maester"]
ROLES = ["operator", "engineer", "reader", "haushold", "hausehold", "family",
         "human", "someone", "nobody", "owner", "kid", "child", "person",
         "people", "council", "haus", "neo", "you", "i", "we", "me", "my", "our",
         # French inhabitant tokens — the QC/joual pages have real cast (a parent,
         # a child, Tommy) but the reader/parent is addressed in French. Only
         # French-ONLY words that never appear in English prose (no "on", "ton",
         # "ta", "parent") so English pages are unaffected.
         "tu", "toi", "vous", "tes", "nous", "enfant", "enfants",
         "maman", "papa", "famille"]
INHABITANTS = CAST_NAMES + ROLES
INHAB_RE = re.compile(r"\b(" + "|".join(re.escape(w) for w in INHABITANTS) + r")\b", re.I)
CAST_RE = re.compile(r"\b(" + "|".join(re.escape(w) for w in CAST_NAMES) + r")\b", re.I)


# ── report ───────────────────────────────────────────────────────────────────
class Report:
    def __init__(self):
        self.rows = []

    def add(self, rel, level, check, msg):
        self.rows.append({"file": rel, "level": level, "check": check, "msg": msg})

    def for_file(self, rel):
        return [r for r in self.rows if r["file"] == rel]


EXPLAIN = {
    "open/runaway": "The first sentence is the whole negotiation. Golden maximum is 26 words "
                    "(temple-of-the-kyber). Error above 30 — four words past the worst opener "
                    "we are proud of, and indefensible.",
    "rhythm/flat": "Four axes, aggregated: mean length, short-sentence share, coefficient of "
                   "variation, long-sentence share. All nineteen golden pages score 4 of 4. "
                   "Use CV, never raw SD — SD scales with the mean. HONEST CAVEAT: this is an "
                   "architecture-page detector. Field notes drift by losing their spine and "
                   "cast while the sentences stay fine; checks 11, 17 and 19 catch those.",
    "cast/thin": "A WARNING, never an error. Golden floor is 3.6 inhabitants per 1,000 words "
                 "(honest-green); the drifted set runs to 21.4. The distributions overlap "
                 "completely, so density cannot gate a build without failing pages we hold "
                 "up as models.",
    "cast/alt-text-cameo": "The character evicted into an HTML attribute — the cleanest "
                           "field-note detector here. Escalates to ERROR only when the page is "
                           "ALSO thin. The guard is load-bearing: a flat error fails pricing, "
                           "the-dragonpit and living-force, where the cat is a visual conceit "
                           "and the prose is richly inhabited by other voices.",
    "landing/on-a-warning": "note and tip are legal landings; caution and danger are to-do "
                            "items. Tommy's last words live in a note Aside — which is exactly "
                            "why the distinction exists.",
    "landing/no-callback": "NOT IMPLEMENTED, deliberately. Every proposed version fires on "
                           "tommy.mdx, because his opening's load-bearing token is 'cat' and "
                           "any sane token-length filter drops it. A warning that fires on the "
                           "gold standard trains everyone to ignore warnings. Callback quality "
                           "is a human's job.",
    "cast/reference-density": "DELIBERATELY ABSENT. Nothing here rewards more cast, more "
                              "franchises or more references. A checker that scores allusions "
                              "produces pages that sprinkle them.",
    "book/no-lineage": "After the 2026-07 sweep, ONLY Tommy trips this — his page is a "
                       "self-contained first-person monologue with no outbound links, and that "
                       "is correct and permanent. index-genre portals are exempt (they ARE the "
                       "lineage hub, linking out via <Card> components, which now count). It "
                       "names the amnesia; book/orphan-page does the enforcing.",
    "budget/chapter": "1600 words standard, 2000 hard ceiling — about seven minutes, which is a "
                      "chapter you finish in one sitting. This REPLACES the 1200-word Five-Minute "
                      "Rule, for a measured reason: the site's best pages already sit at 1155 "
                      "(tommy) and 1067 (the-dragon-earns-its-crown), so the old cap left the gold "
                      "standard 45 words of headroom. Then the Narrative Standard made a cold open "
                      "and a landing MANDATORY — roughly 150-250 words of story scaffolding that "
                      "did not exist before. Holding 1200 would have taken that budget straight out "
                      "of the technical content, which is the opposite of the intent. 1600 also "
                      "brings mothma (1508) inside the standard and leaves quigon (1840) as a "
                      "warning rather than a failure. The ceiling stays hard because the drift this "
                      "whole exercise exists to stop was partly accretion, and a generous cap with "
                      "no ceiling reopens that door. Annex prose is excluded from both numbers.",
}


# ── checks ───────────────────────────────────────────────────────────────────
META_OPEN_RE = re.compile(r"^\s*\*\*(date|status|author|owner|commit|pr|version|scope)\s*:?\*\*", re.I)
THIS_PAGE_RE = re.compile(r"^(this (page|document|note|field note|annex|section)|the following)\b", re.I)
DEFN_RE = re.compile(r"^(The |A |An )?([A-Z][\w'-]*(?:\s+[A-Z][\w'-]*){0,3})\s+"
                     r"(?:(is|are)\s+(a|an|the)\s|(provides|handles|manages|enables|allows|exists (for|to))\b)")
SPOILER_RE = re.compile(r"that (is|'s) the whole (note|story|page)|everything below is|"
                        r"the short version|\btl;?dr\b|in short,", re.I)
PARTICIPLES = ("minted|written|rebooted|verified|deployed|rotated|blocked|created|removed|"
               "added|updated|installed|configured|restarted|replaced|migrated|patched|"
               "signed|revoked|issued|generated|copied|moved|deleted|disabled|enabled|"
               "wired|shipped|landed|merged|renamed|restored|paused|resumed|killed|"
               "provisioned|synced|cached|purged|flushed|rebuilt|reset|tuned|capped|"
               "gated|routed|mounted|unmounted|archived|promoted|demoted")
PASSIVE_RE = re.compile(r"\b(was|were|has been|have been|had been)\s+(?:\w+ly\s+)?(" + PARTICIPLES + r")\b", re.I)
CHANGELOG_RE = re.compile(r"^(P\d+\s*[—–:-]|Phase \d+\s*[—–:-]|20\d\d-\d\d-\d\d\b|"
                          r"Update\s*[—–:-]|Changelog\b|v\d+\.\d+\s*[—–:-])", re.I)
DEFERRED_TITLE_RE = re.compile(r"current as of|superseded|stale|as of 20\d\d", re.I)
DEFERRED_BODY_RE = re.compile(r"mentally substitute|this page accumulated|"
                              r"read the .{1,45} section first|preserved because the (bugs|history)|"
                              r"the rest of the page is the path", re.I)
NAV_RE = re.compile(r"^(ready to|see |read |check |head |continue |for more|next,|"
                    r"start with|move on|to get started|browse )", re.I)


def check_page(path: pathlib.Path, rep: Report, sidebar_slugs: set, inbound: Counter):
    rel = str(path.relative_to(DOCS))
    content = path.read_text(encoding="utf-8")
    fm, blocks, alts, _ = parse(content)
    genre = genre_of(rel, fm)
    cb = content_blocks(blocks)
    pb = prose_blocks(cb)
    body_text = "\n".join(b.text for b in cb if b.kind in ("prose", "bullet"))
    table_text = "\n".join(b.text for b in cb if b.kind == "table")
    pwords = words(body_text)
    nwords = len(pwords)
    err = lambda c, m: rep.add(rel, "error", c, m)
    warn = lambda c, m: rep.add(rel, "warn", c, m)

    # ---- Family A: the cold open
    first_content = next((b for b in cb if b.kind in ("heading", "table", "code", "bullet", "prose")), None)
    if genre != "index" and first_content is not None and first_content.kind != "prose":
        err("open/heading-first", f"page opens on a {first_content.kind}, not prose — Act I is missing")

    if pb:
        first = pb[0].text
        if META_OPEN_RE.match(first.strip()):
            err("open/metadata-stanza", "opens on a metadata stanza — the page was filed, not written")
        fs = sentences(first)
        if fs:
            s0, n0 = fs[0], len(words(fs[0]))
            if genre != "reference":
                if n0 > 30:
                    err("open/runaway", f"first sentence is {n0} words — an inventory, not an opening (max 30)")
                elif n0 > 22:
                    warn("open/runaway", f"first sentence is {n0} words (golden max is 26)")
            if genre not in ("reference", "index"):
                if THIS_PAGE_RE.match(s0):
                    err("open/this-page", "opens by talking about the page instead of writing it")
                if DEFN_RE.match(s0):
                    warn("open/definitional", "opens on a definition — try opening on a problem")
                if PASSIVE_RE.search(s0) and " by " not in s0.lower() \
                        and not re.search(r"\b(i|we|you|my|our|your)\b", s0, re.I):
                    warn("open/agentless-passive", "opening is agentless passive — somebody did this; write that sentence")
        # opening beat + spoiler, over the first 110 / 200 prose words
        head110, head200, acc = [], [], 0
        for b in pb:
            for s in sentences(b.text):
                n = len(words(s))
                if acc < 110:
                    head110.append(n)
                if acc < 200:
                    head200.append(s)
                acc += n
            if acc >= 200:
                break
        if genre != "reference" and head110 and min(head110) > 12:
            warn("open/no-beat", f"no sentence under 13 words in the opening (shortest is {min(head110)})")
        if genre not in ("reference", "index") and SPOILER_RE.search(" ".join(head200)):
            warn("open/spoiler", "the opening spoils its own ending")

    # duplicate H1 — code fences already stripped by the block parser, which is
    # load-bearing: tommy.mdx has "# Tommy's patrols" inside a crontab fence.
    if any(b.kind == "heading" and b.level == 1 for b in blocks):
        err("open/duplicate-h1", "an H1 in the body duplicates the frontmatter title")

    # ---- Family B: rhythm
    if genre not in ("reference", "index"):
        lens = [len(words(s)) for b in pb for s in sentences(b.text)]
        lens = [n for n in lens if n > 0]
        if len(lens) >= 8:
            mean = sum(lens) / len(lens)
            var = sum((n - mean) ** 2 for n in lens) / len(lens)
            cv = (var ** 0.5) / mean if mean else 0
            short = sum(1 for n in lens if n <= 8) / len(lens)
            long = sum(1 for n in lens if n >= 30) / len(lens)
            passed = sum([mean <= 22.0, short >= 0.15, cv >= 0.50, long <= 0.22])
            detail = f"mean {mean:.2f} / CV {cv:.3f} / short {short:.3f} / long {long:.3f}"
            if passed <= 2:
                err("rhythm/flat", f"{passed} of 4 rhythm axes ({detail}) — the prose has calcified")
            elif passed == 3:
                warn("rhythm/flat", f"3 of 4 rhythm axes ({detail})")

    # ---- Family C: the build
    h2 = [b for b in cb if b.kind == "heading" and b.level == 2]
    if genre != "index" and nwords > 500 and len(h2) < 2:
        err("scene/no-spine", f"{nwords} prose words with {len(h2)} section heading(s) — no spine")

    # Splash and index pages have no scenes to be too long — they are doors,
    # not chapters, and their whole body is one continuous pitch.
    if genre not in ("reference", "index"):
        scene, scene_name = 0, "(opening)"
        for b in cb:
            if b.kind == "heading" and b.level == 2:
                if scene > 500:
                    err("scene/too-long", f"scene '{scene_name}' runs {scene} words (max 500)")
                elif scene > 420:
                    warn("scene/too-long", f"scene '{scene_name}' runs {scene} words")
                scene, scene_name = 0, b.text
            elif b.kind in ("prose", "bullet"):
                scene += len(words(b.text))
        if scene > 500:
            err("scene/too-long", f"scene '{scene_name}' runs {scene} words (max 500)")
        elif scene > 420:
            warn("scene/too-long", f"scene '{scene_name}' runs {scene} words")

    for i, b in enumerate(cb):
        if b.kind == "code" and len(b.text.splitlines()) >= 5:
            near = cb[max(0, i - 3): i] + cb[i + 1: i + 4]
            # A numbered <Steps> item IS framing — "2. **Enable** — Touch ID
            # only, or either method after a PIN:" explains the block that
            # follows it. Steps items parse as "bullet", so prose-only
            # matching flagged every Steps-based guide (the repo's own
            # documented Page Structure). Same 6-word floor either way: some
            # human sentence must sit next to the block. Widened 2026-07-31.
            if not any(x.kind in ("prose", "bullet") and len(words(x.text)) >= 6
                       for x in near):
                err("config/unframed-block", f"a {len(b.text.splitlines())}-line code block nobody framed")
                break

    for b in cb:
        if b.kind == "heading" and b.level in (2, 3) and CHANGELOG_RE.match(b.text.strip()):
            err("shape/changelog-heading", f"'{b.text.strip()[:40]}' is a sprint board in a page body")
            break
    if "Grade post-" in content:
        err("shape/changelog-heading", "'Grade post-' is a sprint board in a page body")

    for b in blocks:
        if b.kind == "jsx" and "||title:" in b.text and DEFERRED_TITLE_RE.search(b.text.split("||title:")[1]):
            err("shape/deferred-revision", "an Aside apologises for the page instead of revising it")
            break
    else:
        for b in blocks:
            if b.aside and b.kind == "prose" and DEFERRED_BODY_RE.search(b.text):
                err("shape/deferred-revision", "an Aside apologises for the page instead of revising it")
                break

    if genre != "reference" and table_text:
        cells = [c.strip() for row in table_text.splitlines() for c in row.split("|")]
        longest = max((len(words(c)) for c in cells), default=0)
        if longest > 90:
            warn("table/cell-essay", f"longest table cell is {longest} words — prose hiding in a grid")

    # ---- Family D: the cast
    inhab_text = body_text + "\n" + table_text
    inhab = len(INHAB_RE.findall(clean_prose(inhab_text)))
    thin = False
    if genre != "reference":
        if inhab == 0:
            err("cast/uninhabited", "nobody is in the room — no character, no operator, no reader")
        elif genre != "index":
            density = inhab * 1000.0 / max(nwords, 1)
            if density < 8.0:
                thin = True
                warn("cast/thin", f"{density:.1f} inhabitants per 1000 words")

        alt_cast = {m.lower() for a in alts for m in CAST_RE.findall(a)}
        prose_cast = {m.lower() for m in CAST_RE.findall(clean_prose(inhab_text))}
        orphans = alt_cast - prose_cast
        if orphans:
            who = ", ".join(sorted(orphans))
            if thin:
                err("cast/alt-text-cameo", f"{who} appears only in alt text on a thinly-inhabited page")
            else:
                warn("cast/alt-text-cameo", f"{who} appears only in alt text")

    # ---- Family E: the landing
    tail = [b for b in cb if b.kind in ("prose", "table", "code", "bullet")]
    if tail and genre != "reference":
        last = tail[-1]
        if last.kind in ("table", "code"):
            err("landing/on-table-or-code", f"the page ends on a {last.kind} — it stops, it does not land")
        elif last.aside in ("caution", "danger"):
            err("landing/on-a-warning", f"the page ends inside a {last.aside} Aside — that is a to-do, not a landing")
        elif last.kind == "bullet" and genre != "index":
            warn("landing/on-bullet", "the page ends on a bullet list")
        if last.kind == "prose" and genre != "index":
            ls = sentences(last.text)
            if ls and NAV_RE.match(ls[-1]):
                warn("landing/navigation", "the last line is navigation, not a landing")

    # ---- Family F: the book
    slug = rel[:-4] if rel.endswith(".mdx") else rel
    slug = re.sub(r"/index$", "", slug)
    if genre != "index" and rel != "404.mdx":
        if slug not in sidebar_slugs and inbound.get(slug, 0) == 0:
            err("book/orphan-page", "unreachable: no sidebar entry and no inbound link")
    # Portal/landing pages (genre "index") ARE the lineage hub — they link out
    # via <Card>/<LinkCard> components, not markdown links, so exempt them the
    # same way orphan-page and budget already do. Also count component links
    # (href=/link=) so any page that links via a Starlight component counts as
    # having lineage.
    has_md_link = LINK_RE.search(re.sub(IMG_RE.pattern, "", body_text))
    # A component link counts as lineage only if it points at an internal DOC
    # route — not an image/asset download. Mirror the markdown-link exclusions
    # (see load_inbound): skip http(s), and skip asset extensions (.heic/.png/…).
    comp_targets = re.findall(r'(?:href|link)\s*=\s*["\'](/[^"\']*)["\']', body_text)
    has_component_link = any(
        not re.search(r"\.(heic|png|jpe?g|svg|webp|gif|pdf|mp4|mov|zip)$", t, re.I)
        for t in comp_targets
    )
    if genre != "index" and not has_md_link and not has_component_link:
        warn("book/no-lineage", "no internal links — the page has no lineage")

    # ---- budget — see EXPLAIN["budget/chapter"] for why 1600, not 1200
    if genre not in ("reference", "index"):
        if nwords > 2000:
            err("budget/chapter", f"{nwords} prose words (hard ceiling 2000) — split it or annex it")
        elif nwords > 1600:
            warn("budget/chapter", f"{nwords} prose words (Chapter Rule is 1600)")
    return nwords


# ── corpus helpers ───────────────────────────────────────────────────────────
def load_sidebar() -> set:
    cfg = (ROOT / "astro.config.mjs").read_text(encoding="utf-8")
    return set(re.findall(r"slug:\s*['\"]([^'\"]+)['\"]", cfg))


def load_inbound() -> Counter:
    c = Counter()
    for p in DOCS.rglob("*.mdx"):
        body = p.read_text(encoding="utf-8")
        here = str(p.relative_to(DOCS))[:-4]
        for _, target in LINK_RE.findall(body):
            t = target.split("#")[0].strip()
            if not t or t.startswith(("http", "mailto:")) or t.endswith(".png"):
                continue
            t = re.sub(r"\.mdx$", "", t)
            if t.startswith("./") or t.startswith("../"):
                base = here.rsplit("/", 1)[0] if "/" in here else ""
                t = posixpath.normpath(posixpath.join(base, t))
            t = t.strip("/")
            c[t] += 1
            c[t.rsplit("/", 1)[-1]] += 1
    return c


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--audit", action="store_true", help="whole corpus; errors demoted to warnings")
    ap.add_argument("--backlog", action="store_true", help="ranked rewrite queue")
    ap.add_argument("--top", type=int, default=25)
    ap.add_argument("--explain", metavar="CHECK")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if a.explain:
        print(EXPLAIN.get(a.explain, f"no doctrine note for '{a.explain}'"))
        return 0

    targets = ([pathlib.Path(p).resolve() for p in a.paths] if a.paths
               else sorted(DOCS.rglob("*.mdx")))
    sidebar, inbound = load_sidebar(), load_inbound()
    rep, sizes = Report(), {}
    for p in targets:
        if not p.exists():
            print(f"missing: {p}", file=sys.stderr)
            continue
        try:
            sizes[str(p.relative_to(DOCS))] = check_page(p, rep, sidebar, inbound)
        except Exception as e:  # noqa: BLE001
            rep.add(str(p.relative_to(DOCS)), "error", "internal", f"{type(e).__name__}: {e}")

    if a.json:
        print(json.dumps(rep.rows, indent=2))
        return 0

    if a.backlog:
        score = Counter()
        for r in rep.rows:
            score[r["file"]] += 3 if r["level"] == "error" else 1
        print(f"{'score':>5}  {'errors':>6}  page")
        for f, s in score.most_common(a.top):
            e = sum(1 for r in rep.for_file(f) if r["level"] == "error")
            print(f"{s:>5}  {e:>6}  {f}")
        return 0

    errors = [r for r in rep.rows if r["level"] == "error"]
    warns = [r for r in rep.rows if r["level"] == "warn"]
    by_file = {}
    for r in rep.rows:
        by_file.setdefault(r["file"], []).append(r)
    for f in sorted(by_file):
        print(f"\n{f}")
        for r in sorted(by_file[f], key=lambda x: (x["level"] != "error", x["check"])):
            tag = "ERROR" if r["level"] == "error" else "warn "
            if a.audit and r["level"] == "error":
                tag = "warn "
            print(f"  {tag} {r['check']:<26} {r['msg']}")
    n = len(targets)
    print(f"\n{n} page(s) checked — {len(errors)} error(s), {len(warns)} warning(s)")
    if a.audit:
        print("(--audit: errors shown as warnings, exit 0)")
        return 0
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
