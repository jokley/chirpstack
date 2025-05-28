#!/bin/bash

set -e

PROJECT_DIR="/home/pi/Projects/chirpstack/reTerminal"
AUTOSTART_DIR="/home/pi/.config/lxsession/LXDE-pi"
AUTOSTART_FILE="$AUTOSTART_DIR/autostart"
DESKTOP_FILE="/home/pi/Desktop/venti.desktop"
START_SCRIPT="$PROJECT_DIR/start.sh"
ICON_FILE="$PROJECT_DIR/venti.png"

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

# Ensure the autostart directory exists
echo "📁 Creating autostart directory if needed..."
mkdir -p "$AUTOSTART_DIR"

# Write autostart file
echo "📝 Writing autostart file to $AUTOSTART_FILE"
cat <<EOF > "$AUTOSTART_FILE"
@lxpanel --profile LXDE-pi
@pcmanfm --desktop --profile LXDE-pi
xscreensaver -no-splash
@bash $START_SCRIPT &
EOF

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
