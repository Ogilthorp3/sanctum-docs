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
