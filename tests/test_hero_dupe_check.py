"""Guards for tools/hero-dupe-check.py, the deploy's hero uniqueness gate.

The gate hashes every page's hero. Until 2026-11-08 any exception while hashing
printed "skip" and moved on, so a Pillow release that drops a call the gate
makes would not break the gate. It would turn it silently green: zero heroes
hashed, zero duplicates reported, deploy allowed. Pillow 13 already warns that
Image.getdata goes away in Pillow 14, and deploy.yml installs Pillow unpinned.

Each test runs the gate with DeprecationWarning promoted to an error, so the
next deprecation fails here first instead of being skipped in production.
Deliberately hermetic: a throwaway repo of tiny generated images, no network.
"""
import pathlib
import subprocess
import sys

import pytest

Image = pytest.importorskip("PIL.Image")

GATE = pathlib.Path(__file__).resolve().parents[1] / "tools" / "hero-dupe-check.py"


def _gradient(width, height, horizontal=True, lift=0):
    img = Image.new("L", (width, height))
    span = (width if horizontal else height) - 1
    img.putdata([
        min(255, lift + (255 * (x if horizontal else y)) // span)
        for y in range(height) for x in range(width)
    ])
    return img.convert("RGB")


def _checker(width, height, cell=8):
    img = Image.new("L", (width, height))
    img.putdata([
        255 if ((x // cell) + (y // cell)) % 2 else 0
        for y in range(height) for x in range(width)
    ])
    return img.convert("RGB")


def _page(repo, name, image=None, raw=None):
    docs = repo / "src" / "content" / "docs"
    (docs / "images").mkdir(parents=True, exist_ok=True)
    (docs / f"{name}.mdx").write_text(
        f"---\ntitle: {name}\n---\n\n![A test hero for {name}.](./images/hero-{name}.png)\n"
    )
    hero = docs / "images" / f"hero-{name}.png"
    if raw is not None:
        hero.write_bytes(raw)
    else:
        image.save(hero)


def _gate(repo):
    return subprocess.run(
        [sys.executable, "-W", "error::DeprecationWarning", str(GATE), str(repo), "10"],
        capture_output=True, text=True, timeout=60,
    )


def test_distinct_heroes_are_all_hashed_and_pass(tmp_path):
    _page(tmp_path, "across", _gradient(64, 36, horizontal=True))
    _page(tmp_path, "down", _gradient(64, 36, horizontal=False))
    _page(tmp_path, "board", _checker(64, 36))
    run = _gate(tmp_path)
    assert "skip" not in run.stdout, run.stdout + run.stderr
    assert "scanned 3 hero images" in run.stdout, run.stdout + run.stderr
    assert "VISUAL-DUPLICATE clusters: 0" in run.stdout, run.stdout
    assert run.returncode == 0, run.stdout + run.stderr


def test_positive_control_a_near_copy_fails_the_gate(tmp_path):
    """Different bytes and size, same picture: the gate must still count to one."""
    _page(tmp_path, "across", _gradient(64, 36, horizontal=True))
    _page(tmp_path, "across-again", _gradient(80, 45, horizontal=True, lift=3))
    _page(tmp_path, "down", _gradient(64, 36, horizontal=False))
    run = _gate(tmp_path)
    assert "skip" not in run.stdout, run.stdout + run.stderr
    assert "scanned 3 hero images" in run.stdout, run.stdout + run.stderr
    assert "cluster of 2" in run.stdout, run.stdout
    assert run.returncode == 1, run.stdout + run.stderr


def test_a_hero_the_gate_cannot_read_fails_the_gate(tmp_path):
    """An unhashable hero is unverified art, not a pass."""
    _page(tmp_path, "across", _gradient(64, 36, horizontal=True))
    _page(tmp_path, "broken", raw=b"this is not a png")
    run = _gate(tmp_path)
    assert "broken.mdx" in run.stdout, run.stdout + run.stderr
    assert run.returncode == 2, run.stdout + run.stderr
