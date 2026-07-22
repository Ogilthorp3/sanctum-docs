#!/usr/bin/env python3
"""gen_hero_image.py — the single canonical Sanctum-docs hero generator.

House style (see HERO_ROADMAP.md): black-and-white pencil sketch, hand-drawn,
wide format, white/off-white background, Tommy the Abyssinian cat observing,
one subtle localized color halo (teal or amber). Pass the full prompt in.

Tommy: pass --tommy to prepend the canonical breed descriptor (TOMMY below) so
his Abyssinian shape reaches CLIP's 77-token window instead of being truncated
out of it — the reason past heroes rendered a generic cat. See TOMMY's comment.

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

# ── Tommy, the haus's recurring Abyssinian guardian-spirit ───────────────────
# Two hard-won lessons are baked into this one string:
#
#   1. CLIP TRUNCATES AT 77 TOKENS. FLUX runs two text encoders — CLIP (hard
#      77-token cap) and T5 (512). CLIP is the one that pins recognizable
#      SUBJECT IDENTITY. In a long scene prompt, "Abyssinian" lands past token
#      77, CLIP never sees it, and you get a generic ghost cat (exactly the bug
#      reported 2026-07-14). So this descriptor is meant to be FRONT-LOADED via
#      --tommy, which prepends it — putting the breed inside CLIP's window.
#
#   2. THE HOUSE STYLE IS BLACK-AND-WHITE, which removes an Abyssinian's single
#      most recognizable trait: its warm ruddy TICKED COAT COLOR. So identity
#      here has to ride on SHAPE, not color — large pointed ears, a wedge face,
#      almond eyes, long slender legs, a lithe body, and the fine ticked coat
#      rendered as texture. Bare "Abyssinian cat" gives the model none of that.
TOMMY = ("Tommy, a lithe Abyssinian cat with large pointed ears, a wedge-shaped "
         "face, almond-shaped eyes, long slender legs and a fine ticked coat")


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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tommy", action="store_true",
                    help="prepend the canonical Tommy (Abyssinian) descriptor so his "
                         "breed shape lands inside CLIP's 77-token window. Write --prompt "
                         "with the medium/style first, then the scene; keep Tommy small "
                         "('in the corner, observing') so front-loading doesn't over-weight him.")
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

    # Front-load Tommy so his breed reaches CLIP (see TOMMY's comment). Prepend
    # rather than append: CLIP reads the first ~77 tokens, so the descriptor must
    # lead the prompt, not trail a long scene it never gets to.
    if a.tommy:
        a.prompt = f"{TOMMY}. {a.prompt}"

    if a.backend == "local":
        gen_local(a)
    else:
        gen_imagen(a)


if __name__ == "__main__":
    main()
