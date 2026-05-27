#!/bin/bash
# ─────────────────────────────────────────────────────────────────
#  upload_to_server.sh
#  Copies your bot + saved session to your Oracle Cloud VM.
#  Run this from your Mac AFTER setting up the VM (see CLOUD_SETUP.md)
# ─────────────────────────────────────────────────────────────────

# ── Fill these in after creating your Oracle VM ──────────────────
SERVER_IP="YOUR_VM_IP_ADDRESS"        # e.g. 129.153.45.67
SSH_KEY="~/.ssh/oracle_key"           # path to your private key
REMOTE_USER="ubuntu"                  # Oracle Ubuntu VMs use 'ubuntu'
REMOTE_DIR="/home/ubuntu/peoplestrong-bot"
# ─────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Uploading PeopleStrong bot to Oracle Cloud VM"
echo "  Server : $SERVER_IP"
echo "  Local  : $SCRIPT_DIR"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check SSH key exists
if [ ! -f "${SSH_KEY/#\~/$HOME}" ]; then
    echo "❌ SSH key not found at $SSH_KEY"
    echo "   Update SSH_KEY in this script."
    exit 1
fi

# Check session profile exists
if [ ! -d "$SCRIPT_DIR/ps_profile" ]; then
    echo "❌ ps_profile/ not found."
    echo "   Run 'python3 timesheet_bot.py save_session' on your Mac first."
    exit 1
fi

# Create remote directory
echo "→ Creating remote directory..."
ssh -i "$SSH_KEY" "$REMOTE_USER@$SERVER_IP" "mkdir -p $REMOTE_DIR"

# Upload bot files
echo "→ Uploading bot files..."
scp -i "$SSH_KEY" \
    "$SCRIPT_DIR/timesheet_bot.py" \
    "$SCRIPT_DIR/config.py" \
    "$REMOTE_USER@$SERVER_IP:$REMOTE_DIR/"

# Upload saved session (the important bit)
echo "→ Uploading saved browser session (ps_profile/)..."
rsync -az --progress -e "ssh -i $SSH_KEY" \
    "$SCRIPT_DIR/ps_profile/" \
    "$REMOTE_USER@$SERVER_IP:$REMOTE_DIR/ps_profile/"

echo ""
echo "✅ Upload complete!"
echo ""
echo "Next: SSH into your server and run the installer:"
echo "  ssh -i $SSH_KEY $REMOTE_USER@$SERVER_IP"
echo "  cd $REMOTE_DIR && bash server_install.sh"
