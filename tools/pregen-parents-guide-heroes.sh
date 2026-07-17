#!/bin/bash
# Pre-generate all Parents' Guide hero images (sequential — one Flux job at a time on MPS).
# Run from sanctum-docs repo root. Skips images that already exist (idempotent).
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
GEN="python3 tools/gen_hero_image.py --aspect 16:9"
IMG="src/content/docs/parents-guide/images"
mkdir -p "$IMG"
STYLE="pencil sketch, dark background, single accent halo, moody, minimal, no text"

declare -a JOBS=(
  "hero-index|$STYLE, teal halo, a calm parent's hand resting on a single glowing pause button on a bedside table, children's drawings on the wall"
  "hero-block-now|$STYLE, amber halo, a hand flipping one large vintage light switch to off, small screens dimming in the background"
  "hero-more-time|$STYLE, teal halo, an hourglass being gently topped up with glowing sand by a parent's hand"
  "hero-bedtime-now|$STYLE, teal halo, a haus at night with every window going dark one by one, moon above"
  "hero-homework-mode|$STYLE, amber halo, an open notebook and pencil in a pool of lamplight, game controller resting asleep in shadow"
  "hero-budgets|$STYLE, teal halo, an old brass balance scale weighing minutes as small glowing coins"
  "hero-schedules-and-holidays|$STYLE, amber halo, a wall calendar with moons and suns marked in a child's hand, one week circled"
  "hero-troubleshooting|$STYLE, teal halo, a flashlight beam inspecting a tidy junction box, everything labeled and calm"
  "hero-mirrors-apple-ios|$STYLE, teal halo, a small handheld slate mirror reflecting a moonlit bedtime clock"
  "hero-mirrors-meta-quest|$STYLE, amber halo, a VR headset resting on a nightstand under a dimmed lamp, straps neatly folded"
  "hero-mirrors-nintendo-switch|$STYLE, teal halo, a handheld game console docked and sleeping, tiny moon icon on its dark screen"
  "hero-mirrors-steam|$STYLE, amber halo, a desktop gaming keyboard with keys going dark row by row like city lights at night"
  "hero-mirrors-xbox-playstation|$STYLE, teal halo, two game controllers side by side on a charging dock in a dark living room"
  "hero-qc-index|$STYLE, amber halo, a warm kitchen table at night with a single phone face-down and a cup of tea, fleur-de-lis on the mug"
  "hero-qc-block-now|$STYLE, teal halo, mittened hand pulling one big lever on a snowy porch breaker panel, warm window light behind"
  "hero-qc-bedtime-now|$STYLE, amber halo, a wooden staircase at night, nightlight glow, small socks on the steps"
)

FAILED=0
for job in "${JOBS[@]}"; do
  name="${job%%|*}"; prompt="${job#*|}"
  out="$IMG/${name}.png"
  if [[ -s "$out" ]]; then echo "SKIP $name (exists)"; continue; fi
  echo "=== $(date +%H:%M:%S) generating $name"
  if ! $GEN --out "$out" --prompt "$prompt" >/dev/null 2>&1; then
    echo "FAIL $name"; FAILED=$((FAILED+1))
  else
    echo "OK   $name"
  fi
done
echo "DONE failed=$FAILED total=${#JOBS[@]}"
exit $FAILED