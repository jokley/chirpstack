#!/bin/bash

set -e

PROJECT_DIR="/home/pi/Projects/chirpstack/reTerminal"
LXDE_AUTOSTART_DIR="/home/pi/.config/lxsession/LXDE-pi"
LXDE_AUTOSTART_FILE="$LXDE_AUTOSTART_DIR/autostart"
DESKTOP_FILE="/home/pi/Desktop/venti.desktop"
START_SCRIPT="$PROJECT_DIR/start.sh"
ICON_FILE="$PROJECT_DIR/venti.png"
XDG_AUTOSTART_DIR="/home/pi/.config/autostart"
XDG_DESKTOP_FILE="$XDG_AUTOSTART_DIR/start-my-app.desktop"

echo "==== STARTING INSTALLATION ===="

# Check necessary files exist
if [[ ! -f "$START_SCRIPT" ]]; then
    echo "❌ ERROR: $START_SCRIPT not found"
    exit 1
fi

if [[ ! -f "$ICON_FILE" ]]; then
    echo "❌ ERROR: $ICON_FILE not found"
    exit 1
fi

# Ensure the autostart directories exist
echo "📁 Creating autostart directories if needed..."
mkdir -p "$LXDE_AUTOSTART_DIR"
mkdir -p "$XDG_AUTOSTART_DIR"

# Write LXDE autostart file
echo "📝 Writing LXDE autostart file to $LXDE_AUTOSTART_FILE"
cat <<EOF > "$LXDE_AUTOSTART_FILE"
@lxpanel --profile LXDE-pi
@pcmanfm --desktop --profile LXDE-pi
@bash $START_SCRIPT &
EOF

# Write XDG autostart desktop entry
echo "📝 Writing XDG autostart desktop file to $XDG_DESKTOP_FILE"
cat <<EOF > "$XDG_DESKTOP_FILE"
[Desktop Entry]
Type=Application
Name=Start Venti
Exec=$START_SCRIPT
Icon=$ICON_FILE
X-GNOME-Autostart-enabled=true
EOF

chmod +x "$XDG_DESKTOP_FILE"

# Create Desktop shortcut
echo "🖥️ Creating desktop shortcut at $DESKTOP_FILE"
mkdir -p "/home/pi/Desktop"
cat <<EOF > "$DESKTOP_FILE"
[Desktop Entry]
Type=Link
Name=Heulüfter
Comment=Heulüfter Steuerung
Icon=$ICON_FILE
URL=http://172.16.238.19
EOF

chmod +x "$DESKTOP_FILE"

# Make start script executable
echo "🚀 Making start.sh executable"
chmod +x "$START_SCRIPT"

echo "✅ Setup complete. Please reboot the Raspberry Pi to apply changes."
