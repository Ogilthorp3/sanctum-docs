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

WORK_DIR=""
cleanup() {
    if [ -n "${WORK_DIR:-}" ] && [ -d "$WORK_DIR" ]; then
        rm -rf "$WORK_DIR"
    fi
    WORK_DIR=""
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# ── Colors & Typography ──────────────────────────────────────────────────
BOLD=$'\033[1m'
DIM=$'\033[2m'
RESET=$'\033[0m'
AMBER=$'\033[38;5;214m'
GREEN=$'\033[38;5;77m'
RED=$'\033[38;5;203m'
WHITE=$'\033[97m'

# ── Helpers ──────────────────────────────────────────────────────────────
say()    { printf '%s%s%s%s\n' "$WHITE" "$BOLD" "$*" "$RESET"; }
detail() { printf '%s  %s%s\n' "$DIM" "$*" "$RESET"; }
ok()     { printf '%s  ✓%s %s\n' "$GREEN" "$RESET" "$*"; }
warn()   { printf '%s  !%s %s\n' "$AMBER" "$RESET" "$*"; }
fail()   { printf '%s  ✗%s %s\n' "$RED" "$RESET" "$*"; }
step()   { printf '\n%s◆%s %s%s%s\n' "$AMBER" "$RESET" "$BOLD" "$*" "$RESET"; }

# ── Zero-PII Aggregate Install Counter (opt-outable) ─────────────────────
# Sends ONLY an anonymous step name + macOS major version + CLI version to
# https://hive.sanctum.run/install-event (aggregate daily count — ZERO IP,
# ZERO machine ID, ZERO username, ZERO hostname). Skips automatically in CI
# or when SANCTUM_NO_TELEMETRY=1 / DO_NOT_TRACK=1 is set.
INSTALL_OS_MAJOR="macOS $(sw_vers -productVersion 2>/dev/null | cut -d. -f1 || echo unknown)"
report_install_step() {
    local step_name="$1"
    local cli_ver="${2:-unknown}"
    if [ "${SANCTUM_NO_TELEMETRY:-0}" = "1" ] || [ "${DO_NOT_TRACK:-0}" = "1" ] \
       || [ "${CI:-false}" = "true" ] || [ "${GITHUB_ACTIONS:-false}" = "true" ] \
       || [ "${SANCTUM_OWNER_TEST:-0}" = "1" ]; then
        return 0
    fi
    (
        curl -fsS --proto '=https' --tlsv1.2 --max-time 3 \
            -H 'Content-Type: application/json' \
            -d "{\"step\":\"${step_name}\",\"cli_version\":\"${cli_ver}\",\"os_major\":\"${INSTALL_OS_MAJOR}\"}" \
            https://hive.sanctum.run/install-event >/dev/null 2>&1 || true
    ) &
}

verify_node_codesign() {
    local node_path="$1"
    local sign_info
    [ -f "$node_path" ] && [ ! -L "$node_path" ] || return 1
    case "$node_path" in
        *$'\n'*) return 1 ;;
    esac
    codesign --verify --strict "$node_path" 2>/dev/null || return 1
    sign_info="$(codesign -dvv "$node_path" 2>&1)" || return 1
    case $'\n'"$sign_info"$'\n' in
        *$'\n'"TeamIdentifier=HX7739G8FX"$'\n'*) ;;
        *) return 1 ;;
    esac
    case $'\n'"$sign_info"$'\n' in
        *$'\n'"Authority=Developer ID Application: Node.js Foundation (HX7739G8FX)"$'\n'*) ;;
        *) return 1 ;;
    esac
    case $'\n'"$sign_info"$'\n' in
        *$'\n'"Signature=adhoc"$'\n'*|*$'\n'"TeamIdentifier=not set"$'\n'*) return 1 ;;
    esac
    return 0
}

# ── Preflight ────────────────────────────────────────────────────────────
if [ -t 1 ] && [ -n "${TERM:-}" ] && [ "${TERM:-}" != "dumb" ] && command -v clear >/dev/null 2>&1; then
    clear || true
fi
printf "\n"
printf '%s' "$AMBER"
cat << 'LOGO'
    ◇
   ╱ ╲
  ╱   ╲       S A N C T U M
  ╲   ╱       your haus, your hardware, your AI
   ╲ ╱
    ◇
LOGO
printf '%s\n' "$RESET"
printf '%s  sanctum.run installer  •  about a minute, no commitments%s\n\n' "$DIM" "$RESET"

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
detail "macOS 15 or later. The local brain needs 32 GB; the rest installs on less."
detail "Anonymous install counter active (zero PII; set SANCTUM_NO_TELEMETRY=1 to opt out)."
report_install_step "bootstrap_started"

# ── Homebrew ─────────────────────────────────────────────────────────────
step "Homebrew"

BREW_BIN=""
if command -v brew >/dev/null 2>&1; then
    BREW_BIN="$(command -v brew)"
elif [ -x /opt/homebrew/bin/brew ]; then
    BREW_BIN="/opt/homebrew/bin/brew"
elif [ -x /usr/local/bin/brew ]; then
    BREW_BIN="/usr/local/bin/brew"
fi

if [ -n "$BREW_BIN" ]; then
    eval "$("$BREW_BIN" shellenv)"
    BREW_VER="$("$BREW_BIN" --version 2>/dev/null || true)"
    BREW_VER="${BREW_VER%%$'\n'*}"
    ok "Homebrew already installed (${BREW_VER:-unknown})"
    report_install_step "brew_ready"
else
    say "Installing Homebrew — Apple will ask for your password once."
    detail "Homebrew is the macOS package manager. It installs into /opt/homebrew/"
    detail "and is what we use to ship sanctum-cli + its dependencies."
    printf "\n"
    BREW_INSTALL_SCRIPT="$(curl -fsSL --proto '=https' --proto-redir '=https' --tlsv1.2 --max-time 180 https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    /bin/bash -c "$BREW_INSTALL_SCRIPT"
    if [ -x /opt/homebrew/bin/brew ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [ -x /usr/local/bin/brew ]; then
        eval "$(/usr/local/bin/brew shellenv)"
    else
        fail "Homebrew installation finished but brew binary was not found."
        report_install_step "cli_failed"
        exit 1
    fi
    ok "Homebrew installed"
    report_install_step "brew_ready"
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
    report_install_step "clt_missing"
    xcode-select --install || true
    fail "Re-run: curl -fsSL --proto '=https' --proto-redir '=https' --tlsv1.2 https://sanctum.run/install.sh | bash"
    exit 1
fi

# ── sanctum-cli via the tap ──────────────────────────────────────────────
step "sanctum-cli"

SANCTUM_VER_CLEAN="unknown"
if command -v sanctum &>/dev/null; then
    INSTALLED_VERSION=$(sanctum --version 2>/dev/null || echo "?")
    ok "sanctum-cli already installed ($INSTALLED_VERSION)"
    say "Checking for latest sanctum-cli via Homebrew…"
    brew update >/dev/null 2>&1 || true
    brew upgrade ogilthorp3/sanctum/sanctum-cli >/dev/null 2>&1 || true
    UPDATED_VERSION=$(sanctum --version 2>/dev/null || echo "$INSTALLED_VERSION")
    SANCTUM_VER_CLEAN="${UPDATED_VERSION#sanctum }"
    ok "sanctum-cli current ($UPDATED_VERSION)"
    report_install_step "cli_installed" "$SANCTUM_VER_CLEAN"
else
    say "Installing sanctum-cli from the Ogilthorp3/sanctum tap."
    detail "Tap repo:    https://github.com/Ogilthorp3/homebrew-sanctum"
    detail "Source:      https://github.com/Ogilthorp3/sanctum-cli"
    detail "License:     FSL-1.1-Apache-2.0 (source-available)"
    printf "\n"
    if ! brew install ogilthorp3/sanctum/sanctum-cli; then
        report_install_step "cli_failed"
        fail "Homebrew install of sanctum-cli failed. Please share the error at https://github.com/Ogilthorp3/sanctum-cli/issues"
        exit 1
    fi
    INSTALLED_VERSION="$(sanctum --version 2>/dev/null || echo '')"
    if [ -z "$INSTALLED_VERSION" ]; then
        report_install_step "cli_failed"
        fail "sanctum binary did not respond after install."
        exit 1
    fi
    SANCTUM_VER_CLEAN="${INSTALLED_VERSION#sanctum }"
    ok "sanctum-cli installed ($INSTALLED_VERSION)"
    report_install_step "cli_installed" "$SANCTUM_VER_CLEAN"
fi

# ── Node.js Foundation .pkg (TCC stability — optional but recommended) ───
step "Node.js Foundation .pkg"

if [ -f /usr/local/bin/node ]; then
    if verify_node_codesign /usr/local/bin/node; then
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
    WORK_DIR="$(mktemp -d)"
    PKG_URL="https://nodejs.org/dist/v26.0.0/node-v26.0.0.pkg"
    SHASUMS_URL="${PKG_URL%/*}/SHASUMS256.txt"
    PKG_FILE="${PKG_URL##*/}"
    SHASUMS_PATH="$WORK_DIR/SHASUMS256.txt"
    PKG_PATH="$WORK_DIR/$PKG_FILE"

    say "Downloading $PKG_URL"
    curl -fsSL --proto '=https' --proto-redir '=https' --tlsv1.2 --max-time 60 -o "$SHASUMS_PATH" "$SHASUMS_URL"
    curl -fsSL --proto '=https' --proto-redir '=https' --tlsv1.2 --max-time 180 -o "$PKG_PATH" "$PKG_URL"

    EXPECTED_SHA="$(awk -v fn="$PKG_FILE" '{ gsub(/\r$/, "") } $2 == fn { fn_count++; if (NF == 2 && $1 ~ /^[0-9a-f]{64}$/) { sha=$1; valid_count++ } } END { if (fn_count != 1 || valid_count != 1) exit 1; print sha }' "$SHASUMS_PATH" || true)"
    if [ -z "$EXPECTED_SHA" ]; then
        fail "Could not locate valid SHA-256 for $PKG_FILE in SHASUMS256.txt"
        exit 1
    fi
    ACTUAL_SHA="$(shasum -a 256 "$PKG_PATH")"
    ACTUAL_SHA="${ACTUAL_SHA%% *}"
    if [ "$ACTUAL_SHA" != "$EXPECTED_SHA" ]; then
        fail "SHA-256 mismatch for $PKG_FILE (expected $EXPECTED_SHA, got $ACTUAL_SHA)"
        exit 1
    fi
    ok "Verified SHA-256 for $PKG_FILE"

    PKG_SIG_OUT=""
    if ! PKG_SIG_OUT="$(pkgutil --check-signature "$PKG_PATH" 2>&1)"; then
        fail "Installer signature verification failed for $PKG_FILE"
        exit 1
    fi
    pkg_has_status=0
    pkg_has_cert=0
    while IFS= read -r pkg_line; do
        pkg_line="${pkg_line#"${pkg_line%%[![:space:]]*}"}"
        pkg_line="${pkg_line%"${pkg_line##*[![:space:]]}"}"
        case "$pkg_line" in
            "Status: signed by a developer certificate issued by Apple for distribution")
                pkg_has_status=1
                ;;
            "1. Developer ID Installer: Node.js Foundation (HX7739G8FX)")
                pkg_has_cert=1
                ;;
        esac
    done <<EOF
$PKG_SIG_OUT
EOF
    if [ "$pkg_has_status" -ne 1 ] || [ "$pkg_has_cert" -ne 1 ]; then
        fail "Installer signature for $PKG_FILE does not match Node.js Foundation (HX7739G8FX)"
        exit 1
    fi
    ok "Verified Apple Developer ID Installer signature (HX7739G8FX)"

    say "Opening the Apple Installer — accept the prompts."
    open -W "$PKG_PATH" || true
    cleanup
    if [ -f /usr/local/bin/node ]; then
        if verify_node_codesign /usr/local/bin/node; then
            ok "Node.js Foundation .pkg installed"
        else
            warn "/usr/local/bin/node exists after .pkg step, but signature verification (HX7739G8FX) failed"
            detail "See: https://sanctum.run/architecture/tcc-identity-anchors/"
        fi
    else
        warn ".pkg install was cancelled or failed — continuing without it"
        detail "You can re-run this installer later, or run only the .pkg leg manually."
    fi
fi

# ── Hand-off ─────────────────────────────────────────────────────────────
report_install_step "bootstrap_completed" "$SANCTUM_VER_CLEAN"
step "Full Rust Sanctum Engine, Yoda on Signal & Onboarding"

say "Bootstrap complete. Turn this Mac into a full Sanctum hub:"
detail "  1. sanctum haus install   — 32 signed sanctum-rs Rust services (sanctum-mlx, proxyd,"
detail "                              Presidio, Memory Vault, Castellan, Force Flow, Watchdog,"
detail "                              Msg-Bus, Chitti, Thalamus, Triage, Pressure Valve, Chi),"
detail "                              per-machine mTLS PKI, Dragon 27B + Coder 9B (64 GB+)"
detail "  2. sanctum yoda setup     — Yoda on Signal wired to Rust proxyd :4040 → sanctum-mlx"
detail "  3. sanctum onboard        — Cloudflare R2 encrypted backups + canary + optional AI keys"
detail "  4. sanctum hive join      — Claim your zero-PII Sovereign Seal (Seed #1 / Founding Circle)"
printf "\n"

HIVE_PROMPT="$(printf '%s  0/3 Join the zero-PII Sanctum Hive & claim your Sovereign Seal (%ssanctum hive join%s)? %s[Y/n]%s: ' "$WHITE" "$BOLD" "${RESET}${WHITE}" "$DIM" "$RESET")"
HAUS_PROMPT="$(printf '%s  1/3 Install the full Rust Sanctum engine (%ssanctum haus install%s) now? %s[Y/n]%s: ' "$WHITE" "$BOLD" "${RESET}${WHITE}" "$DIM" "$RESET")"
YODA_PROMPT="$(printf '%s  2/3 Set up Yoda on Signal (%ssanctum yoda setup%s) now? %s[Y/n]%s: ' "$WHITE" "$BOLD" "${RESET}${WHITE}" "$DIM" "$RESET")"
ONBOARD_PROMPT="$(printf '%s  3/3 Run %ssanctum onboard --recipe family%s now? %s[Y/n]%s: ' "$WHITE" "$BOLD" "${RESET}${WHITE}" "$DIM" "$RESET")"
if [ -t 0 ]; then
    read -r -p "$HIVE_PROMPT" hive_ans || hive_ans="n"
    if [[ "${hive_ans:-y}" =~ ^[Yy] ]]; then
        sanctum hive join || true
    fi
    read -r -p "$HAUS_PROMPT" haus_ans || haus_ans="n"
    if [[ "${haus_ans:-y}" =~ ^[Yy] ]]; then
        if sanctum haus install; then
            report_install_step "haus_completed" "$SANCTUM_VER_CLEAN"
        fi
    fi
    read -r -p "$YODA_PROMPT" yoda_ans || yoda_ans="n"
    if [[ "${yoda_ans:-y}" =~ ^[Yy] ]]; then
        if sanctum yoda setup; then
            report_install_step "yoda_completed" "$SANCTUM_VER_CLEAN"
        fi
    fi
    read -r -p "$ONBOARD_PROMPT" answer || answer="n"
    if [[ "${answer:-y}" =~ ^[Yy] ]]; then
        cleanup
        exec sanctum onboard --recipe family
    fi
elif (: < /dev/tty) 2>/dev/null; then
    read -r -p "$HIVE_PROMPT" hive_ans < /dev/tty || hive_ans="n"
    if [[ "${hive_ans:-y}" =~ ^[Yy] ]]; then
        sanctum hive join < /dev/tty || true
    fi
    read -r -p "$HAUS_PROMPT" haus_ans < /dev/tty || haus_ans="n"
    if [[ "${haus_ans:-y}" =~ ^[Yy] ]]; then
        if sanctum haus install < /dev/tty; then
            report_install_step "haus_completed" "$SANCTUM_VER_CLEAN"
        fi
    fi
    read -r -p "$YODA_PROMPT" yoda_ans < /dev/tty || yoda_ans="n"
    if [[ "${yoda_ans:-y}" =~ ^[Yy] ]]; then
        if sanctum yoda setup < /dev/tty; then
            report_install_step "yoda_completed" "$SANCTUM_VER_CLEAN"
        fi
    fi
    read -r -p "$ONBOARD_PROMPT" answer < /dev/tty || answer="n"
    if [[ "${answer:-y}" =~ ^[Yy] ]]; then
        cleanup
        exec sanctum onboard --recipe family < /dev/tty
    fi
else
    detail "Non-interactive shell detected (no TTY) — skipping interactive prompts."
fi

# ── Manual hand-off ──────────────────────────────────────────────────────
printf "\n"
printf '%s' "$AMBER"
cat << 'DONE'
    ◇
   ╱ ╲
  ╱   ╲       Bootstrap complete.
  ╲   ╱
   ╲ ╱
    ◇
DONE
printf '%s\n' "$RESET"

say "You're ready. When you have a moment, run:"
printf "\n"
detail "  ${BOLD}sanctum haus install${RESET}               ${DIM}— full Rust engine (32 signed sanctum-rs binaries + Dragon)${RESET}"
detail "  ${BOLD}sanctum haus seats${RESET}                 ${DIM}— wire \$0 flat-rate Claude / Grok / Gemini sub proxies${RESET}"
detail "  ${BOLD}sanctum ui${RESET}                         ${DIM}— local zero-cloud web dashboard (127.0.0.1:1119)${RESET}"
detail "  ${BOLD}sanctum onboard --recipe family${RESET}    ${DIM}— first-run wizard (backups + AI keys)${RESET}"
detail "  ${BOLD}sanctum yoda setup${RESET}                 ${DIM}— Yoda on Signal (wired to Rust proxyd :4040 → sanctum-mlx)${RESET}"
detail "  ${BOLD}sanctum council${RESET}                    ${DIM}— open the Jedi Council chamber${RESET}"
detail "  ${BOLD}sanctum update${RESET}                     ${DIM}— one-command update (CLI + Rust suite + Dragon + Yoda)${RESET}"
detail "  ${BOLD}sanctum bug-report${RESET}                 ${DIM}— redacted diagnostic report → pre-filled GitHub issue${RESET}"
printf "\n"
detail "Quick start:  https://sanctum.run/getting-started/quick-start/"
detail "Architecture: https://sanctum.run/architecture/overview/"
detail "Source:       https://github.com/Ogilthorp3/sanctum-cli"
printf "\n"
