#!/usr/bin/env python3
"""gen_hero_image.py — the single canonical Sanctum-docs hero generator.

House style (see HERO_ROADMAP.md): black-and-white pencil sketch, hand-drawn,
wide format, white/off-white background, Tommy the Abyssinian cat observing,
one subtle localized color halo (teal or amber). Pass the full prompt in.

Three backends, ONE entry point:
  --backend local  (default)  Flux.1-dev on-device via flux_backend.py — offline,
                              $0, no API key. Needs the torch/diffusers venv
                              (SANCTUM_FLUX_VENV, default ~/Projects/comfy-lab/.venv-flux)
                              and the locally-cached model.
  --backend imagen            Google Imagen 4 via google-genai — METERED (costs
                              money). Run with the cli-venv python that has
                              google-genai. Use only when you deliberately want it.
  --backend gemini-browser    The Gemini web app driven by agent-browser on the
                              AI Ultra SUBSCRIPTION — no metered spend. Needs one
                              interactive Google login into a dedicated profile;
                              see gemini_browser_backend.py. Same ToS-grey class
                              as the :6543 code-assist OAuth proxy (owner-accepted
                              2026-06-13). Use when you want Imagen-grade output
                              without the Cloud bill.

Usage:
  ~/Projects/comfy-lab/.venv-flux/bin/python tools/gen_hero_image.py \
      --prompt "..." --out src/content/docs/operations/images/hero-x.png
  # or explicitly paid:
  ~/.sanctum/cli-venv/bin/python tools/gen_hero_image.py --backend imagen --prompt "..." --out ...

The default is local so nobody accidentally spends on the API. If the local
env is missing we FAIL LOUDLY rather than silently falling back to the paid
path — that no-surprise-charge rule is the whole point of going local.

KNOWN LIMIT OF THE LOCAL BACKEND — legible text and dense composition
(measured 2026-07-25). Flux renders the house style well but is weak at
multi-word signage and at compositions with many labelled elements or a
negation ("knobs REMOVED and set aside"). On the 2026-07-25 knobs hero it
produced invented words ("WIOUS", "WARLU"), garbled the plate to "AOIK-THEN",
drew three doorways instead of four, and left the knobs attached — inverting
the point of the illustration. 12 minutes of on-device compute, unusable frame.

IGNORE the CLIP warning you will see on every run:

    "The following part of your input was truncated because CLIP can only
     handle sequences up to 77 tokens: [...]"

It is benign and NOT the cause of a bad render. Flux has two text encoders:
CLIP supplies a pooled style embedding (77 tokens, always truncates on a long
prompt) while T5 carries the semantics — and flux_backend.py passes
max_sequence_length=512, so the full prompt does reach the model. Chasing that
warning as a truncation bug is a dead end; it was misdiagnosed as one here
before the T5 path was checked.

Practical rule: local is right for atmosphere and single-subject scenes. If the
hero needs LEGIBLE lettering or several precisely-labelled elements, use
--backend imagen and accept the metered cost.
"""
import argparse
import os
import pathlib
import subprocess
import sys

# aspect ratio -> (width, height), multiples of 16 for the diffusion backend
ASPECT_DIMS = {
    "16:9": (1344, 768),
    "1:1": (1024, 1024),
    "4:3": (1152, 896),
    "3:4": (896, 1152),
    "9:16": (768, 1344),
}
DEFAULT_FLUX_VENV = pathlib.Path.home() / "Projects" / "comfy-lab" / ".venv-flux"


def load_key() -> str:
    k = os.environ.get("GEMINI_API_KEY")
    if k:
        return k.strip()
    p = pathlib.Path.home() / ".sanctum" / "secrets" / "gemini-api-key"
    if p.exists():
        return p.read_text().strip()
    sys.exit("no GEMINI_API_KEY (env or ~/.sanctum/secrets/gemini-api-key)")


def gen_local(a) -> None:
    """Render with the local Flux backend. Fail loudly if the env is absent."""
    venv = pathlib.Path(os.environ.get("SANCTUM_FLUX_VENV", str(DEFAULT_FLUX_VENV)))
    py = venv / "bin" / "python"
    backend = pathlib.Path(__file__).with_name("flux_backend.py")
    if not py.exists():
        sys.exit(
            f"--backend local: flux venv not found at {py}\n"
            f"  Build it, or set SANCTUM_FLUX_VENV, or run with --backend imagen "
            f"(paid) if you deliberately want Google."
        )
    if not backend.exists():
        sys.exit(f"--backend local: flux_backend.py missing next to {__file__}")
    w, h = ASPECT_DIMS.get(a.aspect, ASPECT_DIMS["16:9"])
    cmd = [
        str(py), str(backend), "--prompt", a.prompt, "--out", a.out,
        "--width", str(w), "--height", str(h),
        "--steps", str(a.steps), "--seed", str(a.seed),
    ]
    if a.dry_run:
        cmd.append("--dry-run")
    # let stdout/stderr stream through so progress + the final "OK ..." show
    raise SystemExit(subprocess.call(cmd))


def gen_imagen(a) -> None:
    """Render with Google Imagen 4 — METERED. Deliberate opt-in only."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=load_key())
    resp = client.models.generate_images(
        model=a.model,
        prompt=a.prompt,
        config=types.GenerateImagesConfig(number_of_images=1, aspect_ratio=a.aspect),
    )
    imgs = getattr(resp, "generated_images", None) or []
    if not imgs:
        sys.exit("no image returned (safety filter or quota?)")
    image = imgs[0].image
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    data = getattr(image, "image_bytes", None)
    if data:
        out.write_bytes(data)
    else:
        image.save(str(out))
    # Metered call ($0.02-0.06/image) — ledger it in the haus spend meter, fail-open.
    meter = pathlib.Path.home() / "Projects/Claude_Code/tools/gcp_spend.py"
    if meter.exists():
        try:
            subprocess.run([sys.executable, str(meter), "record", "--service", "imagen",
                            "--model", a.model, "--note", "gen_hero_image"],
                           capture_output=True, timeout=15)
        except Exception:
            pass
    print(f"OK {out} ({out.stat().st_size} bytes)")


def gen_gemini_browser(a) -> None:
    """Drive the Gemini web app on the AI Ultra subscription (no metered spend).

    Delegates to gemini_browser_backend.py, which owns the agent-browser session
    and fails loudly (with the accessibility snapshot) if the UI moved or the
    profile is signed out.
    """
    backend = pathlib.Path(__file__).with_name("gemini_browser_backend.py")
    if not backend.exists():
        sys.exit(f"--backend gemini-browser: {backend.name} missing next to {__file__}")
    cmd = [sys.executable, str(backend), "--prompt", a.prompt, "--out", a.out]
    r = subprocess.run(cmd)
    if r.returncode != 0:
        sys.exit(r.returncode)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--aspect", default="16:9", choices=list(ASPECT_DIMS))
    ap.add_argument("--backend", default="local",
                    choices=["local", "imagen", "gemini-browser"],
                    help="local=Flux on-device (free, default); "
                         "gemini-browser=Gemini web app on the AI Ultra sub (free, needs login); "
                         "imagen=Google API (PAID)")
    # local (Flux) knobs
    ap.add_argument("--steps", type=int, default=40, help="Flux inference steps (local)")
    ap.add_argument("--seed", type=int, default=42, help="Flux seed (local)")
    ap.add_argument("--dry-run", action="store_true", help="local: verify env, don't render")
    # imagen knob
    ap.add_argument("--model", default="imagen-4.0-generate-001", help="Imagen model (imagen)")
    a = ap.parse_args()

    if a.backend == "local":
        gen_local(a)
    elif a.backend == "gemini-browser":
        gen_gemini_browser(a)
    else:
        gen_imagen(a)


if __name__ == "__main__":
    main()
