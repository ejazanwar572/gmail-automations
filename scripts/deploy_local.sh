#!/bin/bash

# Exit on error
set -e

PROJECT_DIR="/Users/ejazanwar/Documents/Gmail Automations"
LOGS_DIR="/Users/ejazanwar/.gemini/antigravity/logs"
PLIST_FILE="/Users/ejazanwar/Library/LaunchAgents/com.ejaz.expense_tracker.plist"
PYTHON_BIN="/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3"
SCRIPT_PATH="$PROJECT_DIR/local_expense_tracker.py"

echo "=== Local Expense Tracker Daemon Deployment ==="

# 1. Create logs directory
echo "[1/4] Creating logs directory..."
mkdir -p "$LOGS_DIR"

# 2. Write launchd plist file
echo "[2/4] Generating launchd configuration..."
cat <<EOF > "$PLIST_FILE"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ejaz.expense_tracker</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_BIN</string>
        <string>$SCRIPT_PATH</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>
    <key>StartInterval</key>
    <integer>3600</integer>
    <key>StandardOutPath</key>
    <string>$LOGS_DIR/tracker.log</string>
    <key>StandardErrorPath</key>
    <string>$LOGS_DIR/tracker_error.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/Users/ejazanwar/.pyenv/shims:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
EOF

# Ensure correct permissions
chmod 644 "$PLIST_FILE"

# 3. Validate plist syntax
echo "[3/4] Validating configuration syntax..."
plutil -lint "$PLIST_FILE"

# 4. Load daemon into launchctl
echo "[4/4] Activating background daemon..."
# Unload first if already loaded to avoid duplicate load errors
launchctl unload "$PLIST_FILE" 2>/dev/null || true
launchctl load "$PLIST_FILE"

echo "============================================="
echo "Deployment successful!"
echo "The tracker will run automatically in the background every hour."
echo "Logs are available at: $LOGS_DIR/tracker.log"
echo "To manually trigger a run right now, execute:"
echo "  launchctl start com.ejaz.expense_tracker"
echo "To stop the daemon, run:"
echo "  launchctl unload \"$PLIST_FILE\""
echo "============================================="
