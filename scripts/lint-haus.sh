#!/usr/bin/env bash
# lint-haus.sh — Find stray "home" and "house" that should be "haus"
#
# Usage:
#   ./scripts/lint-haus.sh              # Lint all docs
#   ./scripts/lint-haus.sh path/to.mdx  # Lint specific file
#
# Exits 0 if clean, 1 if violations found.
# Does NOT auto-fix — just reports. Humans decide context.

set -euo pipefail

DOCS_DIR="src/content/docs"
TARGET="${1:-$DOCS_DIR}"

RED='\033[0;31m'
YELLOW='\033[0;33m'
GREEN='\033[0;32m'
NC='\033[0m'

# ── Allowlist patterns (grep -P negative lookahead/lookbehind) ──────────
# These are contexts where "home" or "house" should stay as-is.
ALLOW_PATTERNS=(
  # Product names
  'Home Assistant'
  'HomeKit'
  'Apple Home'
  'Home Companion'
  'home-assistant'
  'Health Auto Export'
  # File paths and config keys
  '/home/'
  'sanctum_home'
  'DOCKER_HOST'
  # Skill and directory names (established)
  'house-pulse'
  # Standard English category terms
  'home office'
  'home router'
  'home server'
  'Home energy'
  # Code/config contexts
  'home_assistant'
  'ghcr.io/home'
  # General tech domain terms (not Sanctum-specific)
  'Home networking'
  'Home automation (HA)'
  'home directory'
  'MBP home'
  # Idiomatic / generic analogies (intentional "house")
  'a house that lost power'
  'house calls'
  'house is on fire'
  'burning your house down'
  'Home automation .HA.'
)

# Build a combined grep pattern to filter out allowed lines
FILTER=""
for pat in "${ALLOW_PATTERNS[@]}"; do
  if [ -z "$FILTER" ]; then
    FILTER="$pat"
  else
    FILTER="$FILTER|$pat"
  fi
done

violations=0
checked=0

while IFS= read -r file; do
  checked=$((checked + 1))

  # Find lines with "home" or "house" (case-insensitive, word boundary)
  matches=$(grep -Pin '\b(home|house)\b' "$file" 2>/dev/null || true)

  if [ -z "$matches" ]; then
    continue
  fi

  # Filter out allowed patterns
  flagged=$(echo "$matches" | grep -Piv "$FILTER" || true)

  if [ -n "$flagged" ]; then
    echo -e "${RED}$file${NC}"
    echo "$flagged" | while IFS= read -r line; do
      echo -e "  ${YELLOW}$line${NC}"
    done
    echo ""
    violations=$((violations + $(echo "$flagged" | wc -l)))
  fi
done < <(find "$TARGET" -name '*.mdx' -o -name '*.md' | sort)

echo "───────────────────────────────────"
echo -e "Files checked: ${checked}"
if [ "$violations" -gt 0 ]; then
  echo -e "Violations:    ${RED}${violations}${NC}"
  echo ""
  echo "Review each hit — some may be intentional (idioms, generic analogies)."
  echo "If it refers to THIS dwelling running Sanctum, change to 'haus'."
  echo "See CONTRIBUTING.md § The Haus Rule for the full policy."
  exit 1
else
  echo -e "Violations:    ${GREEN}0${NC} — all clear."
  exit 0
fi
