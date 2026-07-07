#!/usr/bin/env python3
"""gen_hero_image.py — the single canonical Sanctum-docs hero generator.

House style (see HERO_ROADMAP.md): black-and-white pencil sketch, hand-drawn,
wide format, white/off-white background, Tommy the Abyssinian cat observing,
one subtle localized color halo (teal or amber). Pass the full prompt in.

Two backends, ONE entry point:
  --backend local  (default)  Flux.1-dev on-device via flux_backend.py — offline,
                              $0, no API key. Needs the torch/diffusers venv
                              (SANCTUM_FLUX_VENV, default ~/Projects/comfy-lab/.venv-flux)
                              and the locally-cached model.
  --backend imagen            Google Imagen 4 via google-genai — METERED (costs
                              money). Run with the cli-venv python that has
                              google-genai. Use only when you deliberately want it.

Usage:
  ~/Projects/comfy-lab/.venv-flux/bin/python tools/gen_hero_image.py \
      --prompt "..." --out src/content/docs/operations/images/hero-x.png
  # or explicitly paid:
  ~/.sanctum/cli-venv/bin/python tools/gen_hero_image.py --backend imagen --prompt "..." --out ...

The default is local so nobody accidentally spends on the API. If the local
env is missing we FAIL LOUDLY rather than silently falling back to the paid
path — that no-surprise-charge rule is the whole point of going local.
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
    print(f"OK {out} ({out.stat().st_size} bytes)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--aspect", default="16:9", choices=list(ASPECT_DIMS))
    ap.add_argument("--backend", default="local", choices=["local", "imagen"],
                    help="local=Flux on-device (free, default); imagen=Google (paid)")
    # local (Flux) knobs
    ap.add_argument("--steps", type=int, default=40, help="Flux inference steps (local)")
    ap.add_argument("--seed", type=int, default=42, help="Flux seed (local)")
    ap.add_argument("--dry-run", action="store_true", help="local: verify env, don't render")
    # imagen knob
    ap.add_argument("--model", default="imagen-4.0-generate-001", help="Imagen model (imagen)")
    a = ap.parse_args()

    if a.backend == "local":
        gen_local(a)
    else:
        gen_imagen(a)


if __name__ == "__main__":
    main()
