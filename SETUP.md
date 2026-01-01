# Ring to SMS Notifier - Setup Guide

## Overview
This script monitors your Ring doorbell/cameras and sends SMS alerts when events occur (doorbell presses, motion detection, etc.)

## Prerequisites
- Raspberry Pi with Raspbian/Raspberry Pi OS
- Internet connection
- Ring account
- Twilio account (for SMS)

## Step 1: Get Twilio Credentials

1. Go to https://www.twilio.com and sign up for a free trial account
2. You'll get $15 in free credit (plenty for a month of notifications)
3. From the Twilio Console (https://console.twilio.com):
   - Note your **Account SID** and **Auth Token**
   - Get a Twilio phone number (free with trial)
4. Verify your personal phone number in Twilio (required for trial accounts)

**Cost estimate:** With the free trial, you get about 500-1000 SMS messages. After that, SMS costs ~$0.0075 per message.

## Step 1b: Choose Your Version

**Notification Only** (`ring_to_sms.py`):
- Just SMS notifications
- Minimal storage needed
- Simpler setup

**With Video Recording** (`ring_to_sms_with_video.py`):
- SMS notifications + video downloads
- Requires storage space (recommended: 32GB+ USB drive)
- Full backup of events

For this guide, we'll use the **video recording version**. If you only want notifications, use `ring_to_sms.py` instead.

## Step 2: Install on Raspberry Pi

```bash
# Update system
sudo apt update
sudo apt upgrade -y

# Install Python dependencies
pip3 install ring-doorbell python-dotenv twilio flask requests --break-system-packages

# Create project directory
mkdir ~/ring-notifier
cd ~/ring-notifier

# Copy the script files here:
# - ring_to_sms_with_video.py (or ring_to_sms.py for notifications only)
# - video_viewer.py (optional - for web interface)
# - .env.template
```

## Step 3: Configure Environment Variables

```bash
# Copy template and edit
cp .env.template .env
nano .env
```

Fill in your credentials:
- Ring email and password
- Twilio Account SID and Auth Token
- Twilio phone number (from their console)
- Your personal phone number (must include country code, e.g., +1 for US)

Save with `Ctrl+X`, then `Y`, then `Enter`

## Step 4: Test the Script

```bash
# Make script executable
chmod +x ring_to_sms_with_video.py

# Run it
python3 ring_to_sms_with_video.py
```

You should receive a test SMS saying the notifier is active!

**First Run Note:** Ring uses 2FA, so you may need to:
1. Approve the login on your phone when first running the script
2. The script will cache the token for future use

**Video Download Note:** Videos are saved to `./ring_videos` by default. Test by triggering your doorbell or walking in front of a camera.

## Step 5: Set Up Auto-Start (runs on boot)

Create a systemd service so it starts automatically:

```bash
sudo nano /etc/systemd/system/ring-notifier.service
```

Paste this content (replace `your_username` with your Pi username, usually `pi`):

```ini
[Unit]
Description=Ring SMS Notifier with Video Recording
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/home/your_username/ring-notifier
ExecStart=/usr/bin/python3 /home/your_username/ring-notifier/ring_to_sms_with_video.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable ring-notifier.service

# Start the service now
sudo systemctl start ring-notifier.service

# Check status
sudo systemctl status ring-notifier.service
```

## Managing the Service

```bash
# Check if running
sudo systemctl status ring-notifier.service

# View logs
sudo journalctl -u ring-notifier.service -f

# Stop the service
sudo systemctl stop ring-notifier.service

# Restart the service
sudo systemctl restart ring-notifier.service

# Disable auto-start
sudo systemctl disable ring-notifier.service
```

## Step 6: Access Videos (Optional)

### Option A: Web Viewer (Recommended)
Run the included web viewer to browse videos from any device:

```bash
cd ~/ring-notifier
python3 video_viewer.py
```

Then open in your browser:
- From Pi: `http://localhost:5000`
- From phone/laptop on same network: `http://[Pi-IP]:5000`

To find your Pi's IP: `hostname -I`

**Auto-start the video viewer** (optional):
```bash
sudo nano /etc/systemd/system/ring-viewer.service
```

Paste:
```ini
[Unit]
Description=Ring Video Viewer
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/ring-notifier
ExecStart=/usr/bin/python3 /home/pi/ring-notifier/video_viewer.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable it:
```bash
sudo systemctl enable ring-viewer.service
sudo systemctl start ring-viewer.service
```

### Option B: Direct File Access
```bash
# View videos directly
cd ~/ring-notifier/ring_videos
ls -lh

# Copy to USB drive
cp *.mp4 /media/usb/
```

### Option C: SSH Access
```bash
# From your phone/laptop
ssh pi@[Pi-IP]
cd ~/ring-notifier/ring_videos
ls -lh
```

## Customization

Edit `ring_to_sms_with_video.py` to customize:
- `CHECK_INTERVAL = 10` - How often to check for events (in seconds)
- Message formats in the `_process_event()` method
- Which events to notify about (motion, doorbell, etc.)

Edit `.env` to configure:
- `DOWNLOAD_VIDEOS=true` - Enable/disable video downloads
- `VIDEOS_DIR=./ring_videos` - Where to store videos
- `MAX_STORAGE_GB=10` - Maximum storage before auto-cleanup

## Troubleshooting

**Ring authentication fails:**
- Make sure you've approved the login on your Ring app
- Try running the script manually first: `python3 ring_to_sms.py`
- Check your Ring credentials in `.env`

**SMS not sending:**
- Verify Twilio credentials in `.env`
- Check your Twilio trial account has credit
- Make sure phone numbers include country code (+1 for US)
- Trial accounts can only send to verified numbers

**Service won't start:**
- Check logs: `sudo journalctl -u ring-notifier.service -n 50`
- Verify file paths in service file match your setup
- Make sure script is executable: `chmod +x ring_to_sms.py`

**Pi overheating:**
- With a cooling fan, this shouldn't be an issue
- Monitor temperature: `vcgencmd measure_temp`
- Normal operating temp is 40-60°C

## Power Considerations

The Pi will consume about 2-5 watts depending on model. Over a month:
- Power consumption: ~3.6 kWh
- Cost: ~$0.50 (at $0.14/kWh)

Make sure you have a good quality power supply (official Raspberry Pi adapter recommended).

## Security Notes

- The `.env` file contains sensitive credentials - don't share it
- Keep your Raspberry Pi behind your firewall
- Consider changing your Ring password after your trip if the Pi is left unsupervised
- The script stores Ring tokens locally - keep the Pi physically secure