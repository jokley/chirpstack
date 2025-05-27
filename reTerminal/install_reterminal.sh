#!/bin/bash

# Set working directory
PROJECT_DIR="/home/pi/Projects/chirpstack/reTerminal"

# Ensure the project directory exists
mkdir -p "$PROJECT_DIR"

# 1. Setup autostart
echo "Setting up autostart..."
AUTOSTART_FILE="/home/pi/.config/lxsession/LXDE-pi/autostart"
mkdir -p "$(dirname "$AUTOSTART_FILE")"

# Write or overwrite the autostart file
cat <<EOF > "$AUTOSTART_FILE"
@lxpanel --profile LXDE-pi
@pcmanfm --desktop --profile LXDE-pi
xscreensaver -no-splash
@bash $PROJECT_DIR/start.sh &
EOF

# 2. Add desktop shortcut
echo "Creating desktop shortcut..."
DESKTOP_FILE="/home/pi/Desktop/venti.desktop"
mkdir -p "/home/pi/Desktop"

cat <<EOF > "$DESKTOP_FILE"
[Desktop Entry]
Type=Link
Name=Heulüfter
Comment=Heulüfter Steuerung
Icon=$PROJECT_DIR/venti.png
URL=http://172.16.238.19
EOF

chmod +x "$DESKTOP_FILE"

# 3. Ensure start.sh is executable
echo "Making start.sh executable..."
chmod +x "$PROJECT_DIR/start.sh"

echo "Setup complete. Reboot to apply changes."
