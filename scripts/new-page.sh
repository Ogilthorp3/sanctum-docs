#!/bin/bash
# new-page.sh — stamp out a CONTRIBUTING-compliant MDX skeleton.
#
# Usage:
#   scripts/new-page.sh <category/slug>                 # defaults title
#   scripts/new-page.sh <category/slug> "Page Title"    # explicit title

set -euo pipefail

if [ $# -lt 1 ] || [ $# -gt 2 ]; then
  cat >&2 <<'USAGE'
usage: scripts/new-page.sh <category/slug> [title]
USAGE
  exit 2
fi

SLUG="$1"
TITLE="${2:-${SLUG##*/}}"
TITLE_CAPS="$(echo "$TITLE" | sed 's/-/ /g; s/\b\(.\)/\u\1/g')"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCS_DIR="$ROOT/src/content/docs"
PAGE_PATH="$DOCS_DIR/$SLUG.mdx"
CATEGORY="${SLUG%/*}"
IMG_DIR="$DOCS_DIR/$CATEGORY/images"
SLUG_LEAF="${SLUG##*/}"
HERO_REL="./images/hero-$SLUG_LEAF.png"

if [ -e "$PAGE_PATH" ]; then
  echo "error: $PAGE_PATH already exists" >&2
  exit 1
fi

mkdir -p "$(dirname "$PAGE_PATH")" "$IMG_DIR"

cat > "$PAGE_PATH" <<MDX
---
title: $TITLE_CAPS
description: One sentence on what this page documents.
---

import { Aside, Steps, Tabs, TabItem } from '@astrojs/starlight/components';

![$TITLE_CAPS — REPLACE with descriptive alt, personality, pencil sketch, dark bg, teal/amber accent.]($HERO_REL)

Opening paragraph. Hook the reader. Lead with the technical fact, follow with the human observation.

## How It Works

Real content here. Real ports, real paths, real commands.

<Aside type="tip">
Asides earn their place with personality.
</Aside>
MDX

echo "created: $PAGE_PATH"
echo "next: generate hero + validate with scripts/contrib-check.py $SLUG.mdx"
