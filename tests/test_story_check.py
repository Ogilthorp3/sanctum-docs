"""Calibration contract for the docs gates.

story-check.py's thresholds are anchored to measured boundaries between pages
we hold up as models and pages the drift audit named. These tests pin those
anchors so an edit to the checker cannot silently move them — the near-miss
that motivated this file: a component-link change on 2026-07-31 briefly counted
Tommy's `.heic` asset link as lineage and erased his permanent warning, which
would have detached the whole calibration from its gold standard.

Run:  python3 -m pytest tests/ -q
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORY = ROOT / "scripts" / "story-check.py"
CONTRIB = ROOT / "scripts" / "contrib-check.py"
DOCS = "src/content/docs"


def run_story(*rels):
    return subprocess.run(
        [sys.executable, str(STORY), *[str(ROOT / DOCS / r) for r in rels]],
        capture_output=True, text=True, timeout=120,
    )


# ── the gold standard ────────────────────────────────────────────────────────

def test_tommy_passes_with_exactly_one_permanent_warning():
    """agents/tommy.mdx must pass with exactly one warning (book/no-lineage).
    A checker change that fails Tommy is a broken check, not a strict one; a
    change that CLEARS his warning has mistaken an asset link for lineage."""
    r = run_story("agents/tommy.mdx")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "book/no-lineage" in r.stdout
    assert re.search(r"0 error\(s\), 1 warning\(s\)", r.stdout), r.stdout


# ── deliberate exemptions ────────────────────────────────────────────────────

def test_portal_pages_are_exempt_from_lineage():
    """index-genre portals ARE the lineage hub — they link out via <Card>
    components. They must be clean, not warned."""
    r = run_story("index.mdx", "index-qc.mdx", "qc.mdx")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "book/no-lineage" not in r.stdout, r.stdout


def test_french_cast_is_visible():
    """The joual QC pages have real cast (a parent, a child, Tommy) addressed
    in French. The cast lexicon must see them — an English-only lexicon reads
    an inhabited page as empty."""
    r = run_story("parents-guide/qc/bedtime-now.mdx", "parents-guide/qc/block-now.mdx")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "cast/thin" not in r.stdout, r.stdout
    assert "cast/uninhabited" not in r.stdout, r.stdout


# ── contrib-check: the table-pipe build-crash class ──────────────────────────

def _load_contrib():
    import importlib.util
    spec = importlib.util.spec_from_file_location("contrib_check", CONTRIB)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_table_pipe_token_rule_fires_and_escape_passes():
    """`<|` inside a table cell crashed the 2026-07-30 deploy (dangling `<`
    after the pipe splits the cell). The escaped form must NOT fire."""
    cc = _load_contrib()
    bad = "| Symptom | Cause |\n|---|---|\n| loops | missing `<|im_start|>` prefix |\n"
    good = "| Symptom | Cause |\n|---|---|\n| loops | missing `<\\|im_start\\|>` prefix |\n"
    prose = "In prose, inline `<|im_start|>` is fine — no table cell to split.\n"

    for text, should_fire in ((bad, True), (good, False), (prose, False)):
        rep = cc.Report()
        cc.check_table_pipe_tokens(None, "fixture.mdx", text, 1, rep)
        fired = any("table-pipe-token" in e for e in rep.errors)
        assert fired == should_fire, f"{text!r} -> errors={rep.errors}"


def test_steps_item_counts_as_framing_for_a_code_block():
    """A numbered <Steps> item frames the block it introduces. Steps items
    parse as "bullet"; requiring prose flagged every Steps-based guide, which
    is the repo's own documented Page Structure (regression 2026-07-31)."""
    r = run_story("guides/parent-unlock.mdx")
    assert "config/unframed-block" not in r.stdout, r.stdout
    assert r.returncode == 0, r.stdout + r.stderr


def test_a_truly_unframed_block_still_errors():
    """The relaxation must not gut the rule: a bare code dump with no sentence
    anywhere near it still fails."""
    import tempfile, os
    body = (
        "---\ntitle: Fixture\ndescription: A fixture page for the unframed-block rule.\n---\n\n"
        "![alt](./images/nope.png)\n\n## Config\n\n"
        "```yaml\na: 1\nb: 2\nc: 3\nd: 4\ne: 5\nf: 6\n```\n\n"
        "## More\n\n```yaml\ng: 7\nh: 8\ni: 9\nj: 10\nk: 11\n```\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".mdx", delete=False,
                                    dir=str(ROOT / DOCS)) as fh:
        fh.write(body); tmp = fh.name
    try:
        r = subprocess.run([sys.executable, str(STORY), tmp],
                           capture_output=True, text=True, timeout=60)
        assert "config/unframed-block" in r.stdout, r.stdout
    finally:
        os.unlink(tmp)


def test_mascot_in_artwork_is_not_a_cameo_but_a_guest_is():
    """cast/alt-text-cameo must ignore the mascot and still catch a guest.

    The house art style puts the Abyssinian in 69 heroes. Firing on him told 54
    pages to bolt a Tommy sentence onto their last line — the check manufactured
    the sameness echo-audit measures. It must keep firing for a non-mascot name
    that appears in the art and nowhere in the prose (2026-07-31)."""
    import os, tempfile
    def check(alt, body_line):
        page = (f"---\ntitle: Fixture\ndescription: A fixture for the cameo rule.\n---\n\n"
                f"![{alt}](./images/x.png)\n\n"
                f"{body_line}\n\nSome operator prose so the page is inhabited, with we and you "
                f"and a reader in the room, and enough words that it is not thin at all.\n")
        with tempfile.NamedTemporaryFile("w", suffix=".mdx", delete=False,
                                        dir=str(ROOT / DOCS)) as fh:
            fh.write(page); tmp = fh.name
        try:
            r = subprocess.run([sys.executable, str(STORY), tmp],
                               capture_output=True, text=True, timeout=60)
            return r.stdout
        finally:
            os.unlink(tmp)

    mascot_only = check("Tommy the Abyssinian watches from the sill", "The haus checks itself.")
    assert "alt-text-cameo" not in mascot_only, mascot_only

    guest_only = check("Windu inspects the perimeter", "The haus checks itself.")
    assert "alt-text-cameo" in guest_only, guest_only


# ── the Cast Constitution ────────────────────────────────────────────────────

def test_cast_counts_match_their_sources():
    """CONTRIBUTING's Cast Constitution fixes four counts to two sources of
    truth. If a champion swap adds a routed seat, or a new agent gets a page,
    the doctrine must be updated in the same commit — not discovered later as
    prose that lies (audit 2026-07-31)."""
    import json
    roster = json.loads((ROOT / "src/data/council-roster.json").read_text())
    routed = len(roster["agents"])
    characters = len(list((ROOT / DOCS / "agents").glob("*.mdx")))

    contributing = (ROOT / "CONTRIBUTING.md").read_text()
    m = re.search(r"\*\*Routed seats\*\*\s*\|\s*(\d+)", contributing)
    assert m, "Cast Constitution table missing its Routed-seats row"
    assert int(m.group(1)) == routed, (
        f"CONTRIBUTING says {m.group(1)} routed seats; council-roster.json has {routed}")

    m = re.search(r"\*\*Named characters\*\*\s*\|\s*(\d+)", contributing)
    assert m, "Cast Constitution table missing its Named-characters row"
    assert int(m.group(1)) == characters, (
        f"CONTRIBUTING says {m.group(1)} named characters; agents/ has {characters} pages")


def test_evergreen_pages_do_not_state_bare_cast_counts():
    """Evergreen pages must name the SET a cast number counts ('five routed
    seats'), never a bare 'five agents'. Dated field notes are historical
    snapshots and exempt by the Constitution's rule 5."""
    bare = re.compile(
        r"\b(five|six|seven|eight|nine)\s+(agents|intelligences|seats|minds|robes)\b",
        re.I)
    qualified = re.compile(
        r"\b(routed|council|named|non-routed|reasoning|specialized)\b", re.I)
    # Lines that are self-defining in place: the reader cannot be confused, and
    # rewriting them would cost real craft. Each is exact-matched, so an edit to
    # the line re-arms the rule.
    ALLOW = {
        # The doctrine page's opener — and the roster table sits directly below it.
        "Seven minds share one table, and on most questions they disagree. That is the point.",
        # Enumerates its own arithmetic: 5 + 1 + 1 = 7.
        "Five Jedi, one Mac-side librarian, and one operations chancellor — **seven seats, and the table is full.** Each has a single domain. If a request spans two, route it. The full wiring — who calls whom, and how — lives in the [agents architecture](../architecture/agents/).",
    }
    offenders = []
    for p in sorted((ROOT / DOCS).rglob("*.mdx")):
        rel = str(p.relative_to(ROOT / DOCS))
        if re.match(r"operations/20\d\d-\d\d-\d\d", rel):
            continue                      # dated field note — historical
        for i, line in enumerate(p.read_text().splitlines(), 1):
            if line.strip() in ALLOW:
                continue
            for m in bare.finditer(line):
                window = line[max(0, m.start() - 60): m.end() + 40]
                if not qualified.search(window):
                    offenders.append(f"{rel}:{i}: {m.group(0)}")
    assert not offenders, "bare cast counts (name the set):\n  " + "\n  ".join(offenders)


# ── hero uniqueness gate ─────────────────────────────────────────────────────

def test_hero_dupe_check_exits_clean_on_current_corpus():
    """The perceptual-hash dedup must find 0 visually-identical hero clusters
    (and its exit code is what gates the deploy)."""
    import pytest
    pytest.importorskip("PIL")
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "hero-dupe-check.py"), str(ROOT), "10"],
        capture_output=True, text=True, timeout=300,
    )
    assert "VISUAL-DUPLICATE clusters: 0" in r.stdout, r.stdout
    assert r.returncode == 0, r.stdout
