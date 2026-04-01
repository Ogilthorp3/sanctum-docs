#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════╗
# ║  Sanctum Installer                                                  ║
# ║  https://sanctum.run                                                ║
# ║                                                                     ║
# ║  Usage:  curl -fsSL https://sanctum.run/install.sh | bash           ║
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

spinner() {
    local pid=$1 msg=$2
    local chars="⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    while kill -0 "$pid" 2>/dev/null; do
        for (( i=0; i<${#chars}; i++ )); do
            printf "\r${DIM}  ${chars:$i:1} %s${RESET}" "$msg"
            sleep 0.08
        done
    done
    printf "\r\033[K"
}

ask() {
    local prompt=$1 default=${2:-}
    if [ -n "$default" ]; then
        printf "${WHITE}  %s ${DIM}[%s]${RESET}: " "$prompt" "$default"
    else
        printf "${WHITE}  %s${RESET}: " "$prompt"
    fi
    read -r answer
    echo "${answer:-$default}"
}

confirm() {
    local prompt=$1
    printf "${WHITE}  %s ${DIM}[Y/n]${RESET}: " "$prompt"
    read -r answer
    [[ "${answer:-y}" =~ ^[Yy] ]]
}

# ── Preflight ────────────────────────────────────────────────────────────
clear
printf "\n"
printf "${AMBER}"
cat << 'LOGO'
    ◇
   ╱ ╲
  ╱   ╲       S A N C T U M
  ╲   ╱       Your home, intelligently managed.
   ╲ ╱
    ◇
LOGO
printf "${RESET}\n"
printf "${DIM}  Version 1.0  •  sanctum.run${RESET}\n\n"

# ── System Check ─────────────────────────────────────────────────────────
step "Checking your system"

# macOS version
MACOS_VERSION=$(sw_vers -productVersion 2>/dev/null || echo "0")
MACOS_MAJOR=$(echo "$MACOS_VERSION" | cut -d. -f1)
if [ "$MACOS_MAJOR" -ge 15 ] 2>/dev/null; then
    ok "macOS $MACOS_VERSION (Sequoia or later)"
else
    fail "macOS 15 (Sequoia) or later required — you have $MACOS_VERSION"
    exit 1
fi

# Apple Silicon
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
    CHIP=$(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo "Apple Silicon")
    ok "$CHIP"
else
    fail "Apple Silicon required — detected $ARCH"
    exit 1
fi

# RAM
RAM_GB=$(( $(sysctl -n hw.memsize 2>/dev/null || echo 0) / 1073741824 ))
if [ "$RAM_GB" -ge 16 ]; then
    ok "${RAM_GB} GB RAM"
else
    warn "${RAM_GB} GB RAM — 16 GB minimum recommended"
fi

# Disk space
DISK_FREE_GB=$(df -g "$HOME" | tail -1 | awk '{print $4}')
if [ "$DISK_FREE_GB" -ge 50 ]; then
    ok "${DISK_FREE_GB} GB free disk space"
else
    warn "Only ${DISK_FREE_GB} GB free — 50 GB recommended"
fi

# ── Dependencies ─────────────────────────────────────────────────────────
step "Checking dependencies"

MISSING=()

# Homebrew
if command -v brew &>/dev/null; then
    ok "Homebrew $(brew --version 2>/dev/null | head -1 | awk '{print $2}')"
else
    MISSING+=("homebrew")
    warn "Homebrew not found"
fi

# Git (comes with Xcode CLI tools)
if command -v git &>/dev/null; then
    ok "Git $(git --version | awk '{print $3}')"
else
    MISSING+=("git")
    warn "Git not found"
fi

# Python
if command -v python3 &>/dev/null; then
    PY_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
    if [ "$PY_MINOR" -ge 12 ] 2>/dev/null; then
        ok "Python $PY_VERSION"
    else
        MISSING+=("python")
        warn "Python 3.12+ required — you have $PY_VERSION"
    fi
else
    MISSING+=("python")
    warn "Python not found"
fi

# Node.js
if command -v node &>/dev/null; then
    NODE_VERSION=$(node --version 2>/dev/null)
    NODE_MAJOR=$(echo "$NODE_VERSION" | sed 's/v//' | cut -d. -f1)
    if [ "$NODE_MAJOR" -ge 22 ] 2>/dev/null; then
        ok "Node.js $NODE_VERSION"
    else
        MISSING+=("node")
        warn "Node.js 22+ required — you have $NODE_VERSION"
    fi
else
    MISSING+=("node")
    warn "Node.js not found"
fi

# Docker
if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
    ok "Docker $(docker --version 2>/dev/null | awk '{print $3}' | tr -d ',')"
else
    MISSING+=("docker")
    warn "Docker Desktop not found or not running"
fi

# Install missing dependencies
if [ ${#MISSING[@]} -gt 0 ]; then
    printf "\n"
    say "Missing: ${MISSING[*]}"
    if confirm "Install missing dependencies?"; then
        # Homebrew first
        if [[ " ${MISSING[*]} " =~ " homebrew " ]]; then
            step "Installing Homebrew"
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" &
            spinner $! "Installing Homebrew..."
            wait $!
            eval "$(/opt/homebrew/bin/brew shellenv)"
            ok "Homebrew installed"
        fi

        # Then brew packages
        BREW_PKGS=()
        [[ " ${MISSING[*]} " =~ " git " ]] && BREW_PKGS+=("git")
        [[ " ${MISSING[*]} " =~ " python " ]] && BREW_PKGS+=("python@3.12")
        [[ " ${MISSING[*]} " =~ " node " ]] && BREW_PKGS+=("node")

        if [ ${#BREW_PKGS[@]} -gt 0 ]; then
            step "Installing ${BREW_PKGS[*]}"
            brew install "${BREW_PKGS[@]}" &>/dev/null &
            spinner $! "Installing packages..."
            wait $!
            ok "Packages installed"
        fi

        # Docker Desktop
        if [[ " ${MISSING[*]} " =~ " docker " ]]; then
            step "Installing Docker Desktop"
            brew install --cask docker &>/dev/null &
            spinner $! "Installing Docker Desktop..."
            wait $!
            ok "Docker Desktop installed — please launch it from Applications"
        fi
    else
        fail "Cannot continue without required dependencies."
        detail "Install them manually and re-run the installer."
        exit 1
    fi
fi

# ── Configuration ────────────────────────────────────────────────────────
step "Setting up your Sanctum"

SANCTUM_HOME="$HOME/.sanctum"

# Home name
printf "\n"
say "Let's name your home."
detail "This is how Sanctum identifies your primary location."
detail "Use something short and meaningful — you'll see it everywhere."
printf "\n"

HOSTNAME_GUESS=$(scutil --get ComputerName 2>/dev/null | tr '[:upper:]' '[:lower:]' | tr ' ' '-' || echo "my-home")
HOME_NAME=$(ask "Home name" "$HOSTNAME_GUESS")
HOME_SLUG=$(echo "$HOME_NAME" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd 'a-z0-9-')

# LAN IP detection
LAN_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "192.168.1.10")
LAN_IP=$(ask "Mac Mini LAN IP" "$LAN_IP")

# Services selection
printf "\n"
say "Which features do you want?"
detail "You can change these later in ~/.sanctum/instance.yaml"
printf "\n"

ENABLE_HA=false
ENABLE_VOICE=false
ENABLE_AGENTS=true
ENABLE_DASHBOARD=true

confirm "Home Assistant (smart home automation)" && ENABLE_HA=true
confirm "Voice control (local text-to-speech)" && ENABLE_VOICE=true

printf "\n"

# ── Installation ─────────────────────────────────────────────────────────
step "Creating Sanctum"

# Directory structure
mkdir -p "$SANCTUM_HOME"/{templates/launchagents,tests,lib,scripts,litellm,memory}

ok "Created $SANCTUM_HOME"

# Generate instance.yaml
cat > "$SANCTUM_HOME/instance.yaml" << YAML
# ──────────────────────────────────────────────────────────────────────────
# Sanctum Instance Configuration
# Generated by the Sanctum installer on $(date +%Y-%m-%d)
# Documentation: https://sanctum.run/reference/instance-yaml/
# ──────────────────────────────────────────────────────────────────────────

instance:
  name: "${HOME_NAME}"
  slug: "${HOME_SLUG}"
  tier: "core"   # core | pro | family | estate

nodes:
  ${HOME_SLUG}:
    type: hub
    host: ${LAN_IP}
    services:
      gateway:
        enabled: true
        port: 18789
      dashboard:
        enabled: ${ENABLE_DASHBOARD}
        port: 3001
      homeassistant:
        enabled: ${ENABLE_HA}
        port: 8123
      voice:
        enabled: ${ENABLE_VOICE}
        port: 8020
      agents:
        enabled: ${ENABLE_AGENTS}
        port: 18091
      litellm:
        enabled: true
        port: 4000
        internal_port: 4001

vm:
  ip: 10.10.10.10
  bridge_ip: 10.10.10.1
  ssh_user: ubuntu

secrets:
  backend: keychain
  rotation_day: 1

models:
  local:
    provider: lmstudio
    port: 1234
  cloud:
    provider: openrouter
    pii_scrubbing: true

cloudflare:
  tunnel_name: "${HOME_SLUG}"
YAML

ok "Generated instance.yaml"

# Node identity
echo "$HOME_SLUG" > "$SANCTUM_HOME/.node_id"
ok "Set node identity: $HOME_SLUG"

# Clone core repos if git is available
if command -v git &>/dev/null; then
    if [ ! -d "$HOME/Projects/sanctum-docs" ]; then
        git clone -q https://github.com/Ogilthorp3/sanctum-docs.git "$HOME/Projects/sanctum-docs" 2>/dev/null &
        spinner $! "Cloning documentation..."
        wait $! && ok "Documentation cloned" || detail "Skipped (not available yet)"
    fi

    # Initialize the haus configuration repository
    if [ ! -d "$HOME/$HOME_SLUG" ]; then
        mkdir -p "$HOME/$HOME_SLUG"
        (cd "$HOME/$HOME_SLUG" && git init -q && git commit --allow-empty -q -m "chore: initial commit for $HOME_NAME configuration")
        ok "Initialized configuration repository at ~/$HOME_SLUG"
    else
        ok "Configuration repository ~/$HOME_SLUG already exists"
    fi
fi

# Presidio containers for PII scrubbing
if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
    step "Setting up privacy layer"

    if ! docker ps --format '{{.Names}}' | grep -q presidio-analyzer; then
        docker run -d --name presidio-analyzer --restart unless-stopped \
            -p 127.0.0.1:5002:3000 \
            mcr.microsoft.com/presidio-analyzer:latest &>/dev/null &
        spinner $! "Starting PII analyzer..."
        wait $! && ok "Presidio analyzer running (port 5002)" || warn "Failed to start analyzer"
    else
        ok "Presidio analyzer already running"
    fi

    if ! docker ps --format '{{.Names}}' | grep -q presidio-anonymizer; then
        docker run -d --name presidio-anonymizer --restart unless-stopped \
            -p 127.0.0.1:5001:3000 \
            mcr.microsoft.com/presidio-anonymizer:latest &>/dev/null &
        spinner $! "Starting PII anonymizer..."
        wait $! && ok "Presidio anonymizer running (port 5001)" || warn "Failed to start anonymizer"
    else
        ok "Presidio anonymizer already running"
    fi
fi

# ── Activation ───────────────────────────────────────────────────────────
step "Activating"

# Add shell library to zshrc if not already there
SHELL_SOURCE='source ~/.sanctum/lib/config.sh'
if [ -f "$SANCTUM_HOME/lib/config.sh" ]; then
    if ! grep -q 'sanctum/lib/config.sh' "$HOME/.zshrc" 2>/dev/null; then
        echo "" >> "$HOME/.zshrc"
        echo "# Sanctum shell library" >> "$HOME/.zshrc"
        echo "$SHELL_SOURCE" >> "$HOME/.zshrc"
        ok "Added shell library to ~/.zshrc"
    else
        ok "Shell library already in ~/.zshrc"
    fi
else
    detail "Shell library not found — will be available after full setup"
fi

# ── Done ─────────────────────────────────────────────────────────────────
printf "\n"
printf "${AMBER}"
cat << 'DONE'
    ◇
   ╱ ╲
  ╱   ╲       Installation complete.
  ╲   ╱
   ╲ ╱
    ◇
DONE
printf "${RESET}\n"

say "Your Sanctum is ready."
printf "\n"
detail "Config:      ~/.sanctum/instance.yaml"
detail "Node ID:     $HOME_SLUG"
detail "LAN IP:      $LAN_IP"
if [ "$ENABLE_HA" = true ]; then
    detail "Home Asst:   http://$LAN_IP:8123"
fi
detail "Dashboard:   http://$LAN_IP:3001"
detail "Docs:        https://sanctum.run"

printf "\n"
say "Next steps:"
detail "1. Open ~/.sanctum/instance.yaml to review your config"
detail "2. Run 'bash ~/.sanctum/generate-plists.sh' to create LaunchAgents"
detail "3. Visit https://sanctum.run/getting-started/first-run/"
printf "\n"

# Analytics opt-in (respect privacy)
if confirm "Send anonymous install analytics to help improve Sanctum?"; then
    curl -sf "https://sanctum.run/api/install?v=1.0&chip=$(uname -m)&ram=$RAM_GB&ha=$ENABLE_HA&voice=$ENABLE_VOICE" &>/dev/null || true
    detail "Thank you. No personal data is collected."
else
    detail "No data sent. Your privacy matters."
fi

printf "\n"
