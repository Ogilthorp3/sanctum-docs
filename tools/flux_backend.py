#!/usr/bin/env python3
"""flux_backend.py — LOCAL backend for gen_hero_image.py (offline, $0, no API).

This is NOT a second generator. It is the local rendering half of the single
canonical hero generator (gen_hero_image.py); that script shells out to this
file using the torch/diffusers venv. Keeping them side-by-side keeps one
entry point (gen_hero_image.py) while isolating the heavy ML deps.

Renders with Flux.1-dev on Apple MPS from the locally-cached model — no
GEMINI_API_KEY, no Google Cloud billing. Must be run with a python that has
torch + diffusers (the .venv-flux built for this), e.g.:

  ~/Projects/comfy-lab/.venv-flux/bin/python flux_backend.py \
      --prompt "..." --out hero.png --width 1344 --height 768 --steps 40

gen_hero_image.py invokes this automatically for `--backend local`.
"""
import argparse
import os
import sys


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--width", type=int, default=1344)
    ap.add_argument("--height", type=int, default=768)
    ap.add_argument("--steps", type=int, default=40)
    ap.add_argument("--guidance", type=float, default=3.5)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--model", default="black-forest-labs/FLUX.1-dev")
    ap.add_argument("--dry-run", action="store_true",
                    help="verify env + model cache without rendering")
    a = ap.parse_args()

    os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
    os.environ.setdefault("HF_HUB_OFFLINE", "1")  # local-only: never hit HF network

    try:
        import torch
        from diffusers import FluxPipeline
    except Exception as e:  # noqa: BLE001
        sys.exit(f"flux_backend: torch/diffusers not importable ({e}). "
                 f"Run me with the .venv-flux python.")

    if a.dry_run:
        dev = "mps" if torch.backends.mps.is_available() else "cpu"
        print(f"flux_backend dry-run OK: torch={torch.__version__} device={dev} "
              f"model={a.model} {a.width}x{a.height} steps={a.steps}")
        return

    pipe = FluxPipeline.from_pretrained(a.model, torch_dtype=torch.bfloat16)
    if torch.backends.mps.is_available():
        pipe = pipe.to("mps")
    else:
        pipe.enable_model_cpu_offload()

    img = pipe(
        a.prompt,
        width=a.width,
        height=a.height,
        num_inference_steps=a.steps,
        guidance_scale=a.guidance,
        max_sequence_length=512,
        generator=torch.Generator("cpu").manual_seed(a.seed),
    ).images[0]

    import pathlib
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out))
    print(f"OK {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
