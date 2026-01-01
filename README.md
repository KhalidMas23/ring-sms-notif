# Ring to SMS Notifier with Video Recording

Monitor your Ring doorbell and cameras, receive SMS notifications, and automatically download videos to a Raspberry Pi.

## Features

- 📱 **SMS Notifications**: Instant alerts for doorbell presses and motion detection via Twilio
- 📹 **Video Recording**: Automatically downloads Ring videos to local storage
- 🌐 **Web Viewer**: Browse and watch recorded videos from any device on your network
- 🔄 **Auto-cleanup**: Manages storage by deleting oldest videos when full
- 🚀 **Auto-start**: Runs on boot with systemd service
- 💾 **Smart Caching**: Remembers Ring authentication to avoid constant 2FA

## Use Cases

- Traveling without app access
- Independent backup of Ring footage (no subscription needed)
- Privacy-focused local storage
- Areas with unreliable internet for Ring cloud
- Long-term archival of security footage

## Requirements

### Hardware
- Raspberry Pi (any model with network)
- SD card (32GB+ recommended) or USB drive for video storage
- Power supply
- Cooling fan (recommended for 24/7 operation)

### Accounts
- Ring account
- Twilio account (free trial includes $15 credit)

## Quick Start

### 1. Clone this repository
```bash
git clone https://github.com/yourusername/ring-notifier.git
cd ring-notifier
```

### 2. Install dependencies
```bash
pip3 install ring-doorbell python-dotenv twilio flask requests --break-system-packages
```

### 3. Configure credentials
```bash
cp .env.template .env
nano .env
```

Fill in your:
- Ring email and password
- Twilio credentials (Account SID, Auth Token, phone numbers)
- Video storage settings

**IMPORTANT**: Never commit your `.env` file! It's already in `.gitignore`.

### 4. Run the notifier
```bash
python3 ring_to_sms_with_video.py
```

You'll receive a test SMS and videos will be saved to `./ring_videos/`

### 5. Set up auto-start (optional)
See [SETUP.md](SETUP.md) for full systemd service configuration.

## Files

- `ring_to_sms_with_video.py` - Main script with video recording
- `ring_to_sms.py` - Notification-only version (lighter)
- `video_viewer.py` - Web interface for browsing videos
- `.env.template` - Configuration template (copy to `.env`)
- `SETUP.md` - Detailed setup instructions
- `VIDEO_GUIDE.md` - Advanced video storage and access guide

## Configuration

Edit `.env` to customize:

```bash
# Enable/disable video downloads
DOWNLOAD_VIDEOS=true

# Where to store videos
VIDEOS_DIR=./ring_videos

# Max storage before auto-cleanup (in GB)
MAX_STORAGE_GB=10

# How often to check for events (in script)
CHECK_INTERVAL=10  # seconds
```

## Accessing Videos

### Web Viewer (Recommended)
```bash
python3 video_viewer.py
# Open http://[Pi-IP]:5000 in browser
```

### Direct Access
```bash
cd ring_videos
ls -lh  # View all videos
```

### Remote Access
- SSH: `ssh pi@[Pi-IP]`
- SCP: Download videos to your computer
- Cloud sync: Use rclone to sync to Google Drive/Dropbox

## Storage Estimates

| Storage | Events (~5MB each) | Duration* |
|---------|-------------------|-----------|
| 5 GB    | ~1,000 events     | 1-2 weeks |
| 10 GB   | ~2,000 events     | 2-4 weeks |
| 25 GB   | ~5,000 events     | 2+ months |
| 50 GB   | ~10,000 events    | 4+ months |

*Duration varies based on activity level

## Costs

- **Twilio free trial**: $15 credit (~500-1000 SMS)
- **Twilio after trial**: ~$0.0075 per SMS
- **Raspberry Pi power**: ~$0.50/month electricity
- **Total for 1 month**: ~$1-5 depending on activity

## Security Notes

⚠️ **Important Security Practices:**

1. **Never commit `.env` file** - Contains sensitive credentials
2. **Use strong Ring password** - Consider changing after deployment
3. **Keep Pi behind firewall** - Don't expose SSH to internet without proper security
4. **Physical security** - Keep Pi in secure location
5. **For remote access** - Use VPN (Tailscale/WireGuard) instead of port forwarding

## Troubleshooting

**Authentication fails:**
- Approve the login on your Ring app (first time only)
- Check Ring credentials in `.env`
- Delete `ring_token.cache` and try again

**Videos not downloading:**
- Verify `DOWNLOAD_VIDEOS=true` in `.env`
- Check storage space: `df -h`
- Some events (live view) don't generate recordings
- Ring may take 10-30 seconds to process video

**SMS not sending:**
- Verify Twilio credentials
- Check trial account credit
- Ensure phone numbers include country code (+1 for US)
- Trial accounts can only send to verified numbers

See [SETUP.md](SETUP.md) for detailed troubleshooting.

## Contributing

Pull requests welcome! Please:
- Follow existing code style
- Test on Raspberry Pi before submitting
- Update documentation for new features
- Never commit credentials or tokens

## Disclaimer

This project uses the **unofficial** Ring API via the `ring-doorbell` library. Ring doesn't provide an official consumer API, so:
- The library could break if Ring changes their internal API
- Use at your own risk
- Not affiliated with or endorsed by Ring/Amazon

## License

MIT License - See LICENSE file

## Acknowledgments

- [ring-doorbell](https://github.com/tchellomello/python-ring-doorbell) - Unofficial Ring API library
- [Twilio](https://www.twilio.com/) - SMS notifications
- The Raspberry Pi community

## Support

- Open an issue for bugs or questions
- See [VIDEO_GUIDE.md](VIDEO_GUIDE.md) for advanced video features
- Check [SETUP.md](SETUP.md) for detailed setup instructions

---

**Made for**: People who need Ring notifications without the app, want local video backups, or value privacy through local storage.