#!/usr/bin/env bash
# Smorfia (formerly GeppEmoji) - user-level installer, no root needed.
#
# Why: installs Smorfia for the current user only, in ~/.local/share/smorfia,
# with its own virtual environment (system GTK bindings visible) and a menu
# launcher. User data lives in ~/.config/Smorfia and is never overwritten;
# on first start the app copies your old ~/.config/GeppEmoji data, if any.
set -e

echo "=============================="
echo "  Smorfia - Installer"
echo "=============================="
echo

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ ! -f "smorfia.py" ]]; then
    echo "Error: smorfia.py not found in this folder."
    echo "Please run this installer from inside the Smorfia repository."
    exit 1
fi

APP_DIR="$HOME/.local/share/smorfia"
DESKTOP_FILE="$HOME/.local/share/applications/smorfia.desktop"

# --- System requirements -----------------------------------------------------
echo "Checking Python 3 ..."
if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: python3 not found. Please install Python 3.10+ and re-run."
    exit 1
fi

echo "Checking PyGObject / GTK 3 (system packages) ..."
if ! python3 -c "import gi; gi.require_version('Gtk', '3.0'); from gi.repository import Gtk" >/dev/null 2>&1; then
    echo "Error: Python GTK bindings not available."
    echo "On Debian / Ubuntu / Mint / LMDE install them with:"
    echo "  sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0"
    exit 1
fi

if ! command -v xdotool >/dev/null 2>&1; then
    echo "Warning: xdotool is not installed: auto-paste will not work."
    echo "  sudo apt install xdotool"
fi

# --- Copy the program --------------------------------------------------------
echo
echo "Install directory: $APP_DIR"
mkdir -p "$APP_DIR"
rsync -a \
  --exclude ".git" \
  --exclude "__pycache__" \
  --exclude ".venv" \
  --exclude "build_deb" \
  --exclude "assets" \
  --exclude "docs" \
  ./ "$APP_DIR/"
cd "$APP_DIR"

# --- Virtual environment (with system site-packages, for GTK) ----------------
echo
echo "Creating local virtual environment (.venv) ..."
rm -rf .venv
python3 -m venv .venv --system-site-packages

# --- Launcher ----------------------------------------------------------------
echo "Creating desktop launcher: $DESKTOP_FILE"
mkdir -p "$(dirname "$DESKTOP_FILE")"
cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=Smorfia
GenericName=Emoji Picker
Comment=Desktop emoji picker with search in your language (formerly GeppEmoji)
Exec=$APP_DIR/.venv/bin/python $APP_DIR/smorfia.py
Icon=$APP_DIR/smorfia.png
Terminal=false
Categories=Utility;GTK;
Keywords=emoji;picker;smiley;GeppEmoji;
StartupNotify=false
EOF
chmod +x "$DESKTOP_FILE"
command -v update-desktop-database >/dev/null 2>&1 && \
    update-desktop-database "$HOME/.local/share/applications" >/dev/null 2>&1 || true

# --- Old GeppEmoji install, if present --------------------------------------
if [[ -f "$HOME/.local/share/applications/geppemoji.desktop" ]]; then
    echo
    echo "Note: an old GeppEmoji launcher is still installed."
    echo "Your data will be copied automatically on the first start of Smorfia."
    echo "When you are happy with Smorfia you can remove the old version with:"
    echo "  rm ~/.local/share/applications/geppemoji.desktop"
    echo "  rm -r ~/.local/share/geppemoji"
fi

echo
echo "------------------------------"
echo "  Installation completed!"
echo "------------------------------"
echo "Look for 'Smorfia' in your application menu, or run:"
echo "  $APP_DIR/.venv/bin/python $APP_DIR/smorfia.py"
echo
echo "Tip: bind that command to a global keyboard shortcut. 😉"
