#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════╗
# ║  Sanctum Installer                                                  ║
# ║  https://sanctum.run                                                ║
# ║                                                                     ║
# ║  Usage:  curl -fsSL https://sanctum.run/install.sh | bash           ║
# ║                                                                     ║
# ║  What this does: minimal bootstrap. Installs Homebrew if missing,   ║
# ║  installs sanctum-cli via the Ogilthorp3/sanctum tap, then hands    ║
# ║  off to `sanctum onboard --recipe family` for the actual config.    ║
# ╚══════════════════════════════════════════════════════════════════════╝
set -euo pipefail

# ── Colors & Typography ──────────────────────────────────────────────────
BOLD="\033[1m"
DIM="\033[2m"
RESET="\033[0m"
AMBER="\033[38;5;214m"
GREEN="\033[38;5;77m"
RED="\033[38;5;203m"
BLUE="\033[38;5;110m"
WHITE="\033[97m"

# ── Helpers ──────────────────────────────────────────────────────────────
say()    { printf "${WHITE}${BOLD}%s${RESET}\n" "$*"; }
detail() { printf "${DIM}  %s${RESET}\n" "$*"; }
ok()     { printf "${GREEN}  ✓${RESET} %s\n" "$*"; }
warn()   { printf "${AMBER}  !${RESET} %s\n" "$*"; }
fail()   { printf "${RED}  ✗${RESET} %s\n" "$*"; }
step()   { printf "\n${AMBER}◆${RESET} ${BOLD}%s${RESET}\n" "$*"; }

# ── Preflight ────────────────────────────────────────────────────────────
clear
printf "\n"
printf "${AMBER}"
cat << 'LOGO'
    ◇
   ╱ ╲
  ╱   ╲       S A N C T U M
  ╲   ╱       your haus, your hardware, your AI
   ╲ ╱
    ◇
LOGO
printf "${RESET}\n"
printf "${DIM}  sanctum.run installer  •  about a minute, no commitments${RESET}\n\n"

# Refuse to run on anything other than macOS Apple Silicon.
if [ "$(uname -s)" != "Darwin" ]; then
    fail "Sanctum is macOS-only today."
    detail "If you're on Linux/Windows, follow Sanctum on github.com/Ogilthorp3"
    detail "for the cross-platform port — not shipped yet."
    exit 1
fi
if [ "$(uname -m)" != "arm64" ]; then
    fail "Sanctum runs on Apple Silicon (M1/M2/M3/M4)."
    detail "Intel Macs are not supported. The cathedrals use MLX, which is"
    detail "Apple Silicon only."
    exit 1
fi
ok "macOS on Apple Silicon (uname=$(uname -m))"

# ── Homebrew ─────────────────────────────────────────────────────────────
step "Homebrew"

if command -v brew &>/dev/null; then
    ok "Homebrew already installed ($(brew --version 2>/dev/null | head -1))"
else
    say "Installing Homebrew — Apple will ask for your password once."
    detail "Homebrew is the macOS package manager. It installs into /opt/homebrew/"
    detail "and is what we use to ship sanctum-cli + its dependencies."
    printf "\n"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    eval "$(/opt/homebrew/bin/brew shellenv)"
    ok "Homebrew installed"
fi

# ── Command Line Tools (Apple) ───────────────────────────────────────────
step "Apple Command Line Tools"

if xcode-select -p &>/dev/null; then
    ok "Command Line Tools already present at $(xcode-select -p)"
else
    warn "Apple Command Line Tools missing."
    detail "Brew needs them to build a couple of Python wheels. Apple will"
    detail "open an installer dialog — accept it, wait for the install (~2 min),"
    detail "then re-run this installer."
    printf "\n"
    sudo xcode-select --install || true
    fail "Re-run: curl -fsSL https://sanctum.run/install.sh | bash"
    exit 1
fi

# ── sanctum-cli via the tap ──────────────────────────────────────────────
step "sanctum-cli"

if command -v sanctum &>/dev/null; then
    INSTALLED_VERSION=$(sanctum --version 2>/dev/null || echo "?")
    ok "sanctum-cli already installed ($INSTALLED_VERSION)"
    detail "Run 'sanctum update' to pull the latest."
else
    say "Installing sanctum-cli from the Ogilthorp3/sanctum tap."
    detail "Tap repo:    https://github.com/Ogilthorp3/homebrew-sanctum"
    detail "Source:      https://github.com/Ogilthorp3/sanctum-cli"
    detail "License:     FSL-1.1-Apache-2.0 (source-available)"
    printf "\n"
    brew install ogilthorp3/sanctum/sanctum-cli
    ok "sanctum-cli installed"
fi

# ── Node.js Foundation .pkg (TCC stability — optional but recommended) ───
step "Node.js Foundation .pkg"

if [ -f /usr/local/bin/node ]; then
    if codesign -dvv /usr/local/bin/node 2>&1 | grep -q HX7739G8FX; then
        ok "/usr/local/bin/node is the Node.js Foundation .pkg install"
        detail "Team ID HX7739G8FX — the TCC-stable identity for the haus services."
    else
        warn "/usr/local/bin/node exists but isn't signed by Node.js Foundation."
        detail "This is fine for the brew install, but sanctum services routed"
        detail "through node will hit periodic TCC prompts on brew upgrades."
        detail "See: https://sanctum.run/architecture/tcc-identity-anchors/"
    fi
else
    say "Installing Node.js Foundation .pkg (for TCC stability)."
    detail "Why: sanctum services that touch protected resources (iMessage,"
    detail "Calendar, etc) need a stable signed node binary. brew node's path"
    detail "churns on every upgrade, retriggering permission prompts. The"
    detail ".pkg install puts node at a fixed path with a stable Team ID."
    printf "\n"
    TMPDIR=$(mktemp -d)
    PKG_URL="https://nodejs.org/dist/v26.0.0/node-v26.0.0.pkg"
    say "Downloading $PKG_URL"
    curl -sL -o "$TMPDIR/node.pkg" "$PKG_URL"
    say "Opening the Apple Installer — accept the prompts."
    open -W "$TMPDIR/node.pkg"
    rm -rf "$TMPDIR"
    if [ -f /usr/local/bin/node ]; then
        ok "Node.js Foundation .pkg installed"
    else
        warn ".pkg install was cancelled or failed — continuing without it"
        detail "You can re-run this installer later, or run only the .pkg leg manually."
    fi
fi

# ── Hand-off ─────────────────────────────────────────────────────────────
step "Onboarding"

say "Bootstrap complete. The rest of setup is interactive."
detail "Next command runs sanctum-cli's family-recipe onboarding wizard:"
detail "  • estimate the backup scope (~5 GB after dedup)"
detail "  • walk through Cloudflare R2 cloud-bucket setup (free tier)"
detail "  • run a dry-run + first real backup"
detail "  • restore a known file as a canary to prove the round-trip"
printf "\n"

read -r -p "$(printf "${WHITE}  Run ${BOLD}sanctum onboard --recipe family${RESET}${WHITE} now? ${DIM}[Y/n]${RESET}: ")" answer
if [[ "${answer:-y}" =~ ^[Yy] ]]; then
    exec sanctum onboard --recipe family
fi

# ── Manual hand-off ──────────────────────────────────────────────────────
printf "\n"
printf "${AMBER}"
cat << 'DONE'
    ◇
   ╱ ╲
  ╱   ╲       Bootstrap complete.
  ╲   ╱
   ╲ ╱
    ◇
DONE
printf "${RESET}\n"

say "You're ready. When you have a moment, run:"
printf "\n"
detail "  ${BOLD}sanctum onboard --recipe family${RESET}    ${DIM}— first-run wizard${RESET}"
detail "  ${BOLD}sanctum self-test${RESET}                   ${DIM}— verify everything's healthy${RESET}"
detail "  ${BOLD}sanctum status${RESET}                      ${DIM}— one-line snapshot${RESET}"
detail "  ${BOLD}sanctum doctor${RESET}                      ${DIM}— deep diagnostic${RESET}"
printf "\n"
detail "Quick start:  https://sanctum.run/getting-started/quick-start/"
detail "Architecture: https://sanctum.run/architecture/"
detail "Source:       https://github.com/Ogilthorp3/sanctum-cli"
printf "\n"
