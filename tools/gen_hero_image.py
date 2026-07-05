#!/usr/bin/env python3
"""gen_hero_image.py — generate a Sanctum-docs hero image via Google Imagen 4.

House style (see HERO_ROADMAP.md): black-and-white pencil sketch, hand-drawn,
wide format, white/off-white background, Tommy the Abyssinian cat observing,
one subtle localized color halo (teal or amber). Pass the full prompt in.

Usage:
  gen_hero_image.py --prompt "..." --out src/content/docs/operations/images/hero-x.png \
      [--aspect 16:9] [--model imagen-4.0-generate-001]

Key: $GEMINI_API_KEY, else ~/.sanctum/secrets/gemini-api-key.
Run with the cli-venv python that has google-genai:
  ~/.sanctum/cli-venv/bin/python tools/gen_hero_image.py ...
"""
import argparse
import os
import pathlib
import sys


def load_key() -> str:
    k = os.environ.get("GEMINI_API_KEY")
    if k:
        return k.strip()
    p = pathlib.Path.home() / ".sanctum" / "secrets" / "gemini-api-key"
    if p.exists():
        return p.read_text().strip()
    sys.exit("no GEMINI_API_KEY (env or ~/.sanctum/secrets/gemini-api-key)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--aspect", default="16:9")
    ap.add_argument("--model", default="imagen-4.0-generate-001")
    a = ap.parse_args()

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


if __name__ == "__main__":
    main()
