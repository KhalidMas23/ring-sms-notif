# Video Recording Feature Guide

## Overview
The enhanced script (`ring_to_sms_with_video.py`) downloads and stores Ring videos locally on your Raspberry Pi in addition to sending SMS notifications.

## How It Works

1. **Event Detection**: When motion or doorbell press is detected
2. **Notification**: SMS sent immediately
3. **Video Download**: Script waits ~5 seconds for Ring to process the video, then downloads it
4. **Storage Management**: Automatically deletes oldest videos when storage limit is reached

## Video File Naming

Files are saved with this format:
```
YYYYMMDD_HHMMSS_DeviceName_EventType_EventID.mp4
```

Example:
```
20260115_143022_Front_Door_motion_1234567890.mp4
```

This makes it easy to:
- Sort chronologically
- Identify which device triggered
- Know what type of event occurred

## Storage Considerations

### Raspberry Pi Storage Options

**SD Card (typical):**
- 32GB card → Set `MAX_STORAGE_GB=10` (leaves room for OS and other files)
- 64GB card → Set `MAX_STORAGE_GB=25`
- 128GB card → Set `MAX_STORAGE_GB=60`

**USB Storage (recommended for video):**
You can attach a USB drive for much more storage:

```bash
# Find your USB drive
lsblk

# Mount it (example for /dev/sda1)
sudo mkdir -p /mnt/usb
sudo mount /dev/sda1 /mnt/usb

# Auto-mount on boot by editing /etc/fstab
# (See USB setup guide below)

# Update your .env file
VIDEOS_DIR=/mnt/usb/ring_videos
MAX_STORAGE_GB=100  # Or whatever your USB capacity allows
```

### Video File Sizes

Typical Ring video sizes:
- **Doorbell press**: 5-15 seconds → 1-3 MB
- **Motion event**: 10-60 seconds → 2-10 MB
- **Average**: ~5 MB per event

**Example calculations:**
- 1000 events × 5MB = 5GB
- With 10GB limit, you can store ~2000 events before auto-cleanup kicks in

### Auto-Cleanup Behavior

When storage reaches `MAX_STORAGE_GB`:
1. Script identifies oldest videos (by file modification date)
2. Deletes oldest videos until usage drops to 90% of limit
3. Continues monitoring and downloading new events
4. Logs which files were deleted

## Accessing Videos Remotely

### Option 1: VPN Access
Set up VPN to your home network (like WireGuard or Tailscale) and access Pi directly

### Option 2: Cloud Sync (Recommended)
Automatically upload videos to cloud storage:

**Using rclone to sync to Google Drive/Dropbox:**

```bash
# Install rclone
sudo apt install rclone

# Configure cloud storage
rclone config

# Create a cron job to sync every hour
crontab -e

# Add this line (adjust paths):
0 * * * * rclone sync /home/pi/ring-notifier/ring_videos remote:RingBackup
```

### Option 3: Simple File Server
Access via web browser on your local network:

```bash
# Install simple HTTP server
cd ~/ring-notifier/ring_videos
python3 -m http.server 8080

# Access from any device on your network:
# http://[Pi_IP_Address]:8080
```

## Viewing Videos

Videos are standard MP4 format and work with:
- VLC Media Player (recommended)
- Windows Media Player
- QuickTime (Mac)
- Any web browser
- Phone video players

## Comparison: Notification Only vs Video Recording

### Notification Only (`ring_to_sms.py`)
**Pros:**
- Minimal storage needed (just the script)
- Lower bandwidth usage
- Simpler setup
- Faster notifications

**Cons:**
- No video evidence
- Can't review what happened later
- Relies on Ring cloud storage (requires subscription for history)

### With Video Recording (`ring_to_sms_with_video.py`)
**Pros:**
- Complete video backup independent of Ring subscription
- Review events later
- Keep evidence of incidents
- No reliance on Ring cloud storage

**Cons:**
- Requires storage space (SD card or USB)
- Slight delay in notification (~5 seconds for video processing)
- Uses more bandwidth
- Needs storage management

## Recommended Setup

For a month-long deployment, I recommend:
1. **Small SD Card Setup**: Use notification-only version
2. **USB Drive Available**: Use video recording with 32GB+ USB drive
3. **Concerns about security/evidence**: Definitely use video recording

## Advanced: Accessing Videos While Traveling

### Setup SSH Access
```bash
# On Pi, enable SSH (should already be enabled)
sudo systemctl enable ssh
sudo systemctl start ssh

# From anywhere with your phone or laptop
ssh pi@your_home_ip_address

# Navigate to videos
cd ~/ring-notifier/ring_videos
ls -lh  # See all videos
```

### Port Forwarding (Be Careful!)
You can set up port forwarding on your router to access the Pi remotely, but:
- **Security risk** if not done properly
- Use key-based authentication, not passwords
- Consider using Tailscale or ZeroTier instead (much more secure)

### Tailscale (Recommended for Remote Access)
```bash
# Install Tailscale
curl -fsSL https://tailscale.com/install.sh | sh

# Authenticate
sudo tailscale up

# Access your Pi from anywhere using its Tailscale IP
# No port forwarding needed, encrypted connection
```

## Troubleshooting

**Videos not downloading:**
- Check that `DOWNLOAD_VIDEOS=true` in .env
- Some events (like live view) don't generate recordings
- Ring may take 10-30 seconds to process video - be patient
- Check Ring subscription status (some plans required for cloud recording)

**Storage filling up:**
- Increase `MAX_STORAGE_GB` if you have space
- Or decrease to force more aggressive cleanup
- Consider offloading to cloud storage with rclone

**Can't find videos:**
- Check `VIDEOS_DIR` setting in .env
- Verify directory exists: `ls -lh ~/ring-notifier/ring_videos`
- Check script logs for download errors

**Video playback issues:**
- Ring videos are H.264 MP4 - should work everywhere
- Try VLC if default player has issues
- Check file size isn't 0 bytes (corruption)