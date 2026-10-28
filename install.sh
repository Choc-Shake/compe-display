#!/usr/bin/env bash
# CompE Snack Bar display — installer for Ubuntu.
#   curl -fsSL https://raw.githubusercontent.com/Choc-Shake/compe-display/main/install.sh | bash
# Run it again any time to update. Your settings (config.toml, robot-key.json) are kept.
set -euo pipefail

REPO="${COMPE_REPO:-https://github.com/Choc-Shake/compe-display.git}"
DIR="$HOME/compe-display"
PORT=8787

say() { printf '\n\033[1;35m▶ %s\033[0m\n' "$*"; }

say "Installing system packages (you may be asked for your password)"
sudo apt-get update -qq
sudo apt-get install -y -qq git python3-venv curl
if ! command -v chromium >/dev/null && ! command -v chromium-browser >/dev/null; then
  sudo snap install chromium
fi
BROWSER="$(command -v chromium || command -v chromium-browser)"

say "Getting the display code"
if [ -d "$DIR/.git" ]; then
  git -C "$DIR" pull --ff-only
else
  git clone --depth 1 "$REPO" "$DIR"
fi
cd "$DIR"

say "Setting up Python"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt

if [ ! -f config.toml ]; then
  say "A few questions (press Enter to skip any — the display will show sample data for it)"
  # read from the terminal even when this script is piped from curl
  ask() { local v; read -r -p "$1: " v </dev/tty || true; printf '%s' "$v"; }
  SHEET_ID="$(ask "Google Sheet ID (from its URL)")"
  ICAL="$(ask "Google Calendar secret iCal address")"
  LINK="$(ask "Linktree URL [https://linktr.ee/compeclub]")"
  sed -e "s#^id = \"\"#id = \"$SHEET_ID\"#" \
      -e "s#^ical_url = \"\"#ical_url = \"$ICAL\"#" \
      -e "s#^linktree = .*#linktree = \"${LINK:-https://linktr.ee/compeclub}\"#" \
      config.example.toml > config.toml
fi

say "Starting the display server (runs automatically from now on)"
mkdir -p "$HOME/.config/systemd/user"
cat > "$HOME/.config/systemd/user/compe-display.service" <<EOF
[Unit]
Description=CompE Snack Bar display server
After=network-online.target

[Service]
WorkingDirectory=$DIR
ExecStart=$DIR/.venv/bin/uvicorn server.app:app --host 127.0.0.1 --port $PORT
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF
systemctl --user daemon-reload
systemctl --user enable --now compe-display.service
systemctl --user restart compe-display.service
sudo loginctl enable-linger "$USER"   # start the server at boot, even before login

say "Opening the display full-screen at login"
mkdir -p "$HOME/.config/autostart"
cat > "$HOME/.config/autostart/compe-display.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=CompE Display
Exec=sh -c 'sleep 8; $BROWSER --kiosk --noerrdialogs --disable-infobars --disable-session-crashed-bubble --check-for-update-interval=31536000 http://localhost:$PORT'
X-GNOME-Autostart-enabled=true
EOF

say "Keeping the screen on"
if command -v gsettings >/dev/null; then
  gsettings set org.gnome.desktop.session idle-delay 0 || true
  gsettings set org.gnome.desktop.screensaver lock-enabled false || true
  gsettings set org.gnome.desktop.screensaver idle-activation-enabled false || true
  gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'nothing' || true
fi

say "Done!"
cat <<EOF
  • Preview now:   open http://localhost:$PORT in a browser
  • Full screen:   log out and back in (or restart) — it opens by itself
  • Exit kiosk:    press Alt+F4
  • Turn screen:   Settings → Displays → Orientation → Portrait
  • Settings file: $DIR/config.toml   (restart: systemctl --user restart compe-display)
  • Snack sheet:   put the robot key at $DIR/robot-key.json — see SETUP.md
EOF
