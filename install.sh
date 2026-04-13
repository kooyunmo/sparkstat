#!/bin/sh
set -e

if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[0;33m'
    NC='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    NC=''
fi

log_err() { printf "${RED}Error: %s${NC}\n" "$1"; }
log_warn() { printf "${YELLOW}Warning: %s${NC}\n" "$1"; }
log_ok() { printf "${GREEN}%s${NC}\n" "$1"; }

PY_BIN=""
for cmd in python3 python; do
    if command -v "$cmd" >/dev/null 2>&1; then
        VER=$( "$cmd" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "0.0" )
        if [ "$(printf "%.1f" "$VER" | cut -d. -f1)" -ge 3 ] && [ "$(printf "%.1f" "$VER" | cut -d. -f2)" -ge 9 ]; then
            PY_BIN="$cmd"
            break
        fi
    fi
done

if [ -z "$PY_BIN" ]; then
    log_err "Python 3.9+ is required. Please install Python 3.9 or newer."
    exit 1
fi

INSTALLED=0
for pip_cmd in pip3 pip; do
    if command -v "$pip_cmd" >/dev/null 2>&1; then
        if "$pip_cmd" install --user sparkstat >/dev/null 2>&1; then
            INSTALLED=1
            break
        fi
    fi
done

if [ "$INSTALLED" -eq 0 ]; then
    if "$PY_BIN" -m pip install --user sparkstat >/dev/null 2>&1; then
        INSTALLED=1
    fi
fi

if [ "$INSTALLED" -eq 0 ]; then
    log_warn "Pip installation failed. Falling back to direct script download."
    BIN_DIR="$HOME/.local/bin"
    mkdir -p "$BIN_DIR"
    URL="https://raw.githubusercontent.com/kooyunmo/sparkstat/main/src/sparkstat/cli.py"
    if curl -fsSL "$URL" -o "$BIN_DIR/sparkstat" >/dev/null 2>&1; then
        chmod +x "$BIN_DIR/sparkstat"
        log_warn "Installed as standalone script. Auto-updates are not supported."
    else
        log_err "Failed to download sparkstat from GitHub."
        exit 1
    fi
fi

export PATH="$HOME/.local/bin:$PATH"

if command -v sparkstat >/dev/null 2>&1; then
    VERSION=$(sparkstat -v 2>&1)
    log_ok "sparkstat installed successfully: $VERSION"
else
    log_err "Installation appeared to succeed, but 'sparkstat' command not found."
    exit 1
fi
