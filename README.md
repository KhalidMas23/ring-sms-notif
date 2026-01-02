# Ring to Pushover Notifier with Video Recording

Monitor your Ring doorbell and cameras, receive instant push notifications with snapshots via Pushover, and automatically download videos to a Raspberry Pi.

Perfect for indoor room monitoring during travel when you can't use the Ring app.

## Features

- 📱 **Push Notifications**: Instant alerts via Pushover (no SMS fees, works on WiFi internationally)
- 📸 **Snapshots**: Includes image with each notification so you see what triggered the alert
- 📹 **Video Recording**: Automatically downloads Ring videos to local storage
- 🌐 **Web Viewer**: Browse and watch recorded videos from any device on your network
- 🔄 **Auto-cleanup**: Manages storage by deleting oldest videos when full
- 🚀 **Auto-start**: Runs on boot with systemd service
- 💾 **Smart Caching**: Remembers Ring authentication (no constant 2FA)
- 🎯 **Indoor Monitoring**: Perfect for monitoring rooms while traveling

## Use Cases

- Traveling internationally without Ring app access
- Indoor room monitoring (bedroom, nursery, etc.)
- Independent backup of Ring footage (no subscription needed)
- Privacy-focused local storage
- Areas with unreliable internet for Ring cloud

## Requirements

### Hardware
- Raspberry Pi (any model with network)
- SD card (32GB+ recommended) or USB drive for video storage
- Power supply
- Cooling fan (recommended for 24/7 operation)

### Accounts
- Ring account
- Pushover account ($5 one-time for app - unlimited notifications forever)

## Quick Start

### 1. Clone this repository
```bash
git clone https://github.com/yourusername/ring-notifier.git
cd ring-notifier
```

### 2. Install dependencies
```bash
pip install -r requirements.txt

# Or manually:
pip install ring-doorbell python-dotenv requests opencv-python-headless

# On Raspberry Pi, add --break-system-packages flag:
pip3 install -r requirements.txt --break-system-packages
```

### 3. Get Pushover Credentials

1. Buy Pushover app ($5 one-time): https://pushover.net
2. Log in to https://pushover.net
3. Copy your **User Key** from dashboard
4. Click **"Create an Application/API Token"**
   - Name: "Ring Notifier"
   - Click Create
5. Copy the **API Token**

### 4. Configure credentials
```bash
cp .env.pushover.template .env
nano .env
```

Fill in your:
- Ring email and password
- Pushover User Key and API Token
- Video storage settings

**IMPORTANT**: Never commit your `.env` file! It's already in `.gitignore`.

### 5. Run the notifier
```bash
python ring_to_pushover.py
```

First run will ask for Ring 2FA code. After that, token is cached - no more 2FA needed!

You'll receive a test Pushover notification and videos will be saved to `./ring_videos/`

### 6. Set up auto-start (optional)
See [SETUP.md](SETUP.md) for full systemd service configuration.

## Files

**Main Scripts:**
- `ring_to_pushover.py` - Main script with Pushover notifications and video recording
- `video_viewer.py` - Web interface for browsing videos
- `ring_debug.py` - Debug script to see your Ring devices

**Alternative Notification Methods:**
- `ring_to_email.py` - Email notifications (if you prefer email)
- `ring_to_whatsapp.py` - WhatsApp notifications via Twilio
- `ring_to_sms.py` - SMS notifications via Twilio (deprecated - use Pushover instead)

**Configuration:**
- `.env.pushover.template` - Pushover configuration template
- `requirements.txt` - Python dependencies

**Documentation:**
- `SETUP.md` - Detailed setup instructions
- `PUSHOVER_SETUP.md` - Pushover setup guide
- `VIDEO_GUIDE.md` - Advanced video storage and access guide
- `GMAIL_SETUP.md` - Gmail setup (if using email notifications)
- `WHATSAPP_SETUP.md` - WhatsApp setup (if using WhatsApp)

## Configuration

Edit `.env` to customize:

```bash
# Ring Account
RING_USERNAME=your_ring_email@example.com
RING_PASSWORD=your_ring_password

# Pushover (get from pushover.net)
PUSHOVER_USER_KEY=uxxxxxxxxxxxxxxxxxxxxx
PUSHOVER_API_TOKEN=axxxxxxxxxxxxxxxxxxxxx

# Video Settings
DOWNLOAD_VIDEOS=true              # Enable/disable video downloads
VIDEOS_DIR=./ring_videos          # Where to store videos
MAX_STORAGE_GB=10                 # Max storage before auto-cleanup
```

You can also edit the script to adjust:
- `CHECK_INTERVAL = 10` - How often to check for events (in seconds)
- Notification priorities for different event types
- Which events to record (doorbell, motion, etc.)

## Accessing Videos

### Web Viewer (Recommended)
```bash
python video_viewer.py
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

- **Pushover**: $5 one-time (unlimited notifications forever)
- **Raspberry Pi power**: ~$0.50/month electricity
- **Total for 1 month**: ~$0.50 (after initial $5 Pushover purchase)

Compare to Twilio SMS: ~$1-5/month depending on activity

## Why Pushover Over SMS?

✅ **$5 one-time** vs ongoing SMS costs  
✅ **No verification** - no business info needed  
✅ **Works internationally** on WiFi  
✅ **Rich notifications** - includes snapshots  
✅ **Made for hobbyists** - not a B2B service  
✅ **Instant delivery** - just as fast as SMS  

## Security Notes

⚠️ **Important Security Practices:**

1. **Never commit `.env` file** - Contains sensitive credentials
2. **Token caching** - `ring_token.cache` is auto-generated and shouldn't be shared
3. **Use strong Ring password** - Consider changing after deployment
4. **Keep Pi behind firewall** - Don't expose SSH to internet without proper security
5. **Physical security** - Keep Pi in secure location
6. **For remote access** - Use VPN (Tailscale/WireGuard) instead of port forwarding

## Troubleshooting

**Authentication fails:**
- First run requires Ring 2FA code
- After successful auth, token is cached in `ring_token.cache`
- Delete token file and re-run if authentication issues persist

**Videos not downloading:**
- Verify `DOWNLOAD_VIDEOS=true` in `.env`
- Check storage space: `df -h`
- Ring may take 10-30 seconds to process video after event

**Snapshots not appearing:**
- Install opencv: `pip install opencv-python-headless`
- Script extracts first frame from video as fallback
- Some Ring models may not support snapshot API

**Notifications not sending:**
- Verify Pushover credentials in `.env`
- Test by triggering motion detection manually
- Check console output for error messages

See [PUSHOVER_SETUP.md](PUSHOVER_SETUP.md) for detailed Pushover troubleshooting.

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
- [Pushover](https://pushover.net/) - Push notification service
- The Raspberry Pi community

## Support

- Open an issue for bugs or questions
- See [PUSHOVER_SETUP.md](PUSHOVER_SETUP.md) for Pushover setup help
- Check [VIDEO_GUIDE.md](VIDEO_GUIDE.md) for advanced video features
- See [SETUP.md](SETUP.md) for detailed setup instructions

---

**Made for**: People who need Ring notifications without the app, want local video backups for indoor monitoring, or value privacy through local storage during travel.