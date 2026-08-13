"""Backend-selection guards for tools/gen_hero_image.py.

Both bugs these cover cost real money in production, on 2026-08-11 and 2026-08-12:

  1. `--backend auto` delegated to the render host without checking whether it WAS the
     render host, so on that box it ssh'd itself, failed, and fell through to the metered
     API. Two heroes were billed that way.
  2. `gen_imagen()` ignored `--dry-run` entirely — every other backend honoured it. The
     first dry-run after `auto` started routing to Imagen bought a real 737 KB image.

Deliberately hermetic: no network, no ssh, no API key. Anything that needs the render host
or the live API belongs in a manual check, not here.
"""
import os
import pathlib
import subprocess
import sys
import types

import pytest

TOOLS = pathlib.Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

import gen_hero_image as g  # noqa: E402


def test_internet_probe_is_false_when_host_unreachable():
    """The probe decides Imagen-vs-Flux. A closed port must read as offline."""
    assert g._internet_up(host="127.0.0.1", port=9, timeout=1.0) is False


def test_internet_probe_targets_the_api_host_not_a_generic_ping():
    """A captive portal passes 'can I reach 1.1.1.1' and then fails the real call."""
    assert "googleapis.com" in g._internet_up.__defaults__[0] if g._internet_up.__defaults__[0] else True
    src = (TOOLS / "gen_hero_image.py").read_text()
    assert "generativelanguage.googleapis.com" in src


def test_gen_imagen_dry_run_never_spends(tmp_path, capsys):
    """The guard must short-circuit BEFORE importing google-genai or calling the API.

    Asserting it returns cleanly under an interpreter that has no google-genai is the
    strongest available proof that no API call happens: if it fell through, the import
    itself would sys.exit.
    """
    out = tmp_path / "hero.png"
    a = types.SimpleNamespace(dry_run=True, model="gemini-3-pro-image", out=str(out),
                              prompt="x", aspect="16:9", steps=40, seed=1)
    g.gen_imagen(a)                      # must return, not SystemExit
    assert not out.exists(), "dry-run wrote a file — that means it called the paid API"


def test_dry_run_via_cli_writes_nothing(tmp_path):
    """End-to-end on the real argv path, with the metered backend forced."""
    out = tmp_path / "hero.png"
    r = subprocess.run(
        [sys.executable, str(TOOLS / "gen_hero_image.py"), "--backend", "imagen",
         "--dry-run", "--prompt", "x", "--out", str(out)],
        capture_output=True, text=True, timeout=120,
    )
    assert r.returncode == 0, (r.stdout + r.stderr)[:400]
    assert not out.exists(), "dry-run wrote a file"
    assert "dry-run" in (r.stdout + r.stderr).lower()


def test_render_host_aliases_cover_both_names():
    """The box answers to 'mbp' (ssh target) and 'berts' (hostname -s).

    Comparing them as plain strings is what made the render host refuse to render on
    itself while `auto` ssh'd a name that did not resolve.
    """
    aliases = {a.lower() for a in g.RENDER_HOST_ALIASES if a}
    assert "mbp" in aliases and "berts" in aliases


def test_remote_backend_is_free_or_nothing():
    """`remote` must never reach the paid path — that is its entire contract."""
    src = (TOOLS / "gen_hero_image.py").read_text()
    # The online shortcut has to be scoped to auto; if it ever loses that guard,
    # --backend remote starts billing.
    assert 'a.backend == "auto" and not offline' in src
