# ☁️ Running PeopleStrong Bot 24/7 on Oracle Cloud (Free)

Oracle Cloud's Always-Free tier gives you a real Ubuntu server that runs
forever at zero cost — no credit card tricks, no expiry.

---

## What you'll need
- An Oracle Cloud account (free): https://cloud.oracle.com
- ~30 minutes
- Your bot working locally with a saved session (`ps_profile/` folder exists)

---

## Part 1 — Create your free Oracle VM (one time, ~15 mins)

### Step 1 — Sign up
Go to https://cloud.oracle.com and create a free account.
Use a real phone number — Oracle sends a verification SMS.

### Step 2 — Create a VM instance
1. In the Oracle Console, click **"Create a VM instance"**
2. Set these options:
   - **Name**: `peoplestrong-bot`
   - **Image**: `Canonical Ubuntu 22.04` (click "Change Image" if needed)
   - **Shape**: `VM.Standard.A1.Flex` — select this, set **1 OCPU, 6 GB RAM** (Always Free)
3. Under **"Add SSH keys"**:
   - Select **"Generate a key pair for me"**
   - Click **Download private key** → save as `oracle_key` in your `~/.ssh/` folder
   - Also download the public key
4. Click **Create**
5. Wait ~2 minutes for the VM to show **RUNNING**
6. Copy the **Public IP address** shown on the instance page

### Step 3 — Fix SSH key permissions (Mac)
```bash
chmod 600 ~/.ssh/oracle_key
```

### Step 4 — Open port / firewall (important!)
Oracle blocks all traffic by default. You only need SSH (already open).
No extra ports needed for this bot.

### Step 5 — Test SSH connection
```bash
ssh -i ~/.ssh/oracle_key ubuntu@YOUR_VM_IP
```
You should see a Linux prompt. Type `exit` to disconnect.

---

## Part 2 — Upload your bot (5 mins)

### Step 1 — Make sure your session is saved on Mac first
```bash
# On your Mac, in the bot folder:
python3 timesheet_bot.py save_session
# Log in + MFA → press Enter → ps_profile/ folder is created
```

### Step 2 — Edit upload_to_server.sh
Open `upload_to_server.sh` and fill in:
```bash
SERVER_IP="129.153.45.67"      # ← your actual VM IP
SSH_KEY="~/.ssh/oracle_key"    # ← your key path
```

### Step 3 — Run the upload
```bash
bash upload_to_server.sh
```
This uploads `timesheet_bot.py`, `config.py`, and your entire `ps_profile/` folder.

---

## Part 3 — Install & schedule on the VM (5 mins)

### Step 1 — SSH into your VM
```bash
ssh -i ~/.ssh/oracle_key ubuntu@YOUR_VM_IP
```

### Step 2 — Run the installer
```bash
cd ~/peoplestrong-bot
bash server_install.sh
```
This installs Python, Playwright, Chromium, and sets up cron automatically.

### Step 3 — Test it
```bash
python3 timesheet_bot.py punch_in
```

### Step 4 — Watch the logs
```bash
tail -f /tmp/peoplestrong_bot.log
```

---

## Part 4 — Ongoing maintenance

### Check if it's running
```bash
ssh -i ~/.ssh/oracle_key ubuntu@YOUR_VM_IP
tail -50 /tmp/peoplestrong_bot.log
```

### If session expires (weeks/months later)
Re-do session save on your Mac, then re-upload:
```bash
# On Mac:
python3 timesheet_bot.py save_session
bash upload_to_server.sh

# On server:
ssh -i ~/.ssh/oracle_key ubuntu@YOUR_VM_IP
# Session is automatically replaced — no reinstall needed
```

### Update punch times
Edit `config.py` locally, re-upload, re-run `server_install.sh`.

---

## ⚠️ Important notes

**Timezone**: Oracle VMs default to UTC. Bengaluru is UTC+5:30.
Your cron times must be in UTC. The installer handles this automatically
by reading your config times and converting — but double-check!

For example, if you want 9:00 AM IST punch-in:
- IST 9:00 AM = UTC 3:30 AM
- Set in config.py: `PUNCH_IN_TIME = "09:00"` (IST)
- The installer sets cron to `30 3 * * 1-5` automatically

**The VM runs 24/7** — your laptop can be off, asleep, or abroad.
The bot punches in and out on its own every weekday.
