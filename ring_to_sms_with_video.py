#!/usr/bin/env python3
"""
Ring Event Monitor with SMS Notifications and Video Recording
Monitors Ring doorbell/camera events, sends SMS alerts, and downloads videos
"""

import os
import time
import json
from datetime import datetime
from pathlib import Path
from ring_doorbell import Ring, Auth
from oauthlib.oauth2 import MissingTokenError
from twilio.rest import Client
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

# Configuration
RING_USERNAME = os.getenv('RING_USERNAME')
RING_PASSWORD = os.getenv('RING_PASSWORD')
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_FROM_NUMBER = os.getenv('TWILIO_FROM_NUMBER')
TWILIO_TO_NUMBER = os.getenv('TWILIO_TO_NUMBER')
TOKEN_FILE = 'ring_token.cache'
CHECK_INTERVAL = 10  # seconds between checks
DOWNLOAD_VIDEOS = os.getenv('DOWNLOAD_VIDEOS', 'true').lower() == 'true'
VIDEOS_DIR = os.getenv('VIDEOS_DIR', './ring_videos')
MAX_STORAGE_GB = float(os.getenv('MAX_STORAGE_GB', '10'))  # Max storage in GB

class RingSMSNotifier:
    def __init__(self):
        self.ring = None
        self.twilio_client = None
        self.last_event_ids = {}
        self.videos_path = Path(VIDEOS_DIR)
        self.initialize()
    
    def initialize(self):
        """Initialize Ring and Twilio connections"""
        print(f"[{datetime.now()}] Initializing Ring SMS Notifier...")
        
        # Create videos directory if it doesn't exist
        if DOWNLOAD_VIDEOS:
            self.videos_path.mkdir(parents=True, exist_ok=True)
            print(f"✓ Videos directory created: {self.videos_path.absolute()}")
        
        # Initialize Twilio
        self.twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        print("✓ Twilio client initialized")
        
        # Initialize Ring authentication
        auth = Auth("MyRingSMSApp/1.0", None, token_updater=self.token_updated)
        
        try:
            # Try to load existing token
            auth.fetch_token(RING_USERNAME, RING_PASSWORD)
        except MissingTokenError:
            print("No cached token found, performing initial authentication...")
            auth.fetch_token(RING_USERNAME, RING_PASSWORD)
        
        self.ring = Ring(auth)
        self.ring.update_data()
        print("✓ Ring client initialized")
        
        # List devices
        devices = self.ring.devices()
        print(f"\nFound {len(devices.get('doorbots', []))} doorbell(s)")
        print(f"Found {len(devices.get('stickup_cams', []))} camera(s)")
        
        # Initialize last event tracking
        self._initialize_event_tracking()
    
    def token_updated(self, token):
        """Callback to save updated Ring token"""
        with open(TOKEN_FILE, 'w') as f:
            json.dump(token, f)
        print(f"[{datetime.now()}] Token updated and saved")
    
    def _initialize_event_tracking(self):
        """Get initial event IDs to avoid sending notifications for old events"""
        print("\nInitializing event tracking...")
        for doorbell in self.ring.doorbells:
            history = doorbell.history(limit=1)
            if history:
                self.last_event_ids[doorbell.id] = history[0]['id']
                print(f"  {doorbell.name}: Last event ID {history[0]['id']}")
        
        for camera in self.ring.stickup_cams:
            history = camera.history(limit=1)
            if history:
                self.last_event_ids[camera.id] = history[0]['id']
                print(f"  {camera.name}: Last event ID {history[0]['id']}")
    
    def get_storage_usage_gb(self):
        """Calculate total storage used by downloaded videos"""
        total_size = 0
        if self.videos_path.exists():
            for file in self.videos_path.rglob('*'):
                if file.is_file():
                    total_size += file.stat().st_size
        return total_size / (1024**3)  # Convert to GB
    
    def cleanup_old_videos(self):
        """Remove oldest videos if storage limit exceeded"""
        current_usage = self.get_storage_usage_gb()
        
        if current_usage > MAX_STORAGE_GB:
            print(f"[{datetime.now()}] Storage limit exceeded ({current_usage:.2f}GB / {MAX_STORAGE_GB}GB)")
            print("Cleaning up oldest videos...")
            
            # Get all video files sorted by modification time
            video_files = []
            for file in self.videos_path.rglob('*.mp4'):
                if file.is_file():
                    video_files.append((file, file.stat().st_mtime))
            
            video_files.sort(key=lambda x: x[1])  # Sort by oldest first
            
            # Delete oldest files until under limit
            while current_usage > MAX_STORAGE_GB * 0.9 and video_files:  # Keep 10% buffer
                oldest_file, _ = video_files.pop(0)
                file_size_gb = oldest_file.stat().st_size / (1024**3)
                oldest_file.unlink()
                current_usage -= file_size_gb
                print(f"  Deleted: {oldest_file.name} ({file_size_gb:.2f}GB)")
            
            print(f"✓ Cleanup complete. Current usage: {current_usage:.2f}GB")
    
    def download_video(self, device, event):
        """Download video for a specific event"""
        if not DOWNLOAD_VIDEOS:
            return None
        
        try:
            # Check storage before downloading
            self.cleanup_old_videos()
            
            # Get recording URL
            recording_url = event.get('recording', {}).get('status')
            
            if not recording_url or recording_url != 'ready':
                print(f"  Video not ready yet for event {event['id']}")
                return None
            
            # Ring API requires fetching the video URL
            video_url = device.recording_url(event['id'])
            
            if not video_url:
                print(f"  No video URL available for event {event['id']}")
                return None
            
            # Create filename with timestamp and device name
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            device_name = device.name.replace(' ', '_').replace('/', '_')
            event_kind = event.get('kind', 'unknown')
            filename = f"{timestamp}_{device_name}_{event_kind}_{event['id']}.mp4"
            filepath = self.videos_path / filename
            
            print(f"  Downloading video to {filename}...")
            
            # Download the video
            response = requests.get(video_url, stream=True)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            file_size_mb = filepath.stat().st_size / (1024**2)
            print(f"  ✓ Video saved ({file_size_mb:.2f}MB)")
            
            return str(filepath)
            
        except Exception as e:
            print(f"  Error downloading video: {e}")
            return None
    
    def send_sms(self, message):
        """Send SMS via Twilio"""
        try:
            msg = self.twilio_client.messages.create(
                body=message,
                from_=TWILIO_FROM_NUMBER,
                to=TWILIO_TO_NUMBER
            )
            print(f"[{datetime.now()}] SMS sent: {msg.sid}")
            return True
        except Exception as e:
            print(f"[{datetime.now()}] Error sending SMS: {e}")
            return False
    
    def check_for_events(self):
        """Check for new Ring events"""
        try:
            self.ring.update_data()
            
            # Check doorbells
            for doorbell in self.ring.doorbells:
                self._check_device_events(doorbell)
            
            # Check cameras
            for camera in self.ring.stickup_cams:
                self._check_device_events(camera)
                
        except Exception as e:
            print(f"[{datetime.now()}] Error checking events: {e}")
    
    def _check_device_events(self, device):
        """Check a specific device for new events"""
        history = device.history(limit=5)
        
        if not history:
            return
        
        latest_event_id = history[0]['id']
        last_seen_id = self.last_event_ids.get(device.id)
        
        # If this is a new event
        if last_seen_id != latest_event_id:
            # Process all new events (in case we missed multiple)
            for event in history:
                if event['id'] == last_seen_id:
                    break
                
                self._process_event(device, event)
            
            # Update last seen event
            self.last_event_ids[device.id] = latest_event_id
    
    def _process_event(self, device, event):
        """Process and send notification for an event"""
        kind = event.get('kind', 'unknown')
        created_at = event.get('created_at', 'unknown time')
        
        # Format the message based on event type
        if kind == 'ding':
            message = f"🔔 Ring Alert: Doorbell pressed at {device.name}"
        elif kind == 'motion':
            message = f"👁️ Ring Alert: Motion detected at {device.name}"
        elif kind == 'on_demand':
            message = f"📹 Ring Alert: Live view started at {device.name}"
        else:
            message = f"🔔 Ring Alert: {kind} event at {device.name}"
        
        message += f"\nTime: {created_at}"
        
        print(f"\n[{datetime.now()}] New event detected!")
        print(f"  Device: {device.name}")
        print(f"  Type: {kind}")
        print(f"  Time: {created_at}")
        
        # Download video if enabled
        video_path = None
        if DOWNLOAD_VIDEOS and kind in ['ding', 'motion']:
            # Wait a moment for Ring to finish processing the video
            print(f"  Waiting for video to be ready...")
            time.sleep(5)
            video_path = self.download_video(device, event)
            
            if video_path:
                message += f"\n📼 Video saved locally"
        
        self.send_sms(message)
    
    def get_stats(self):
        """Get statistics about stored videos"""
        if not self.videos_path.exists():
            return "No videos directory found"
        
        video_count = len(list(self.videos_path.rglob('*.mp4')))
        storage_gb = self.get_storage_usage_gb()
        
        return f"Videos: {video_count} | Storage: {storage_gb:.2f}GB / {MAX_STORAGE_GB}GB"
    
    def run(self):
        """Main monitoring loop"""
        print(f"\n{'='*50}")
        print("Ring SMS Notifier with Video Recording")
        print(f"Video downloads: {'ENABLED' if DOWNLOAD_VIDEOS else 'DISABLED'}")
        if DOWNLOAD_VIDEOS:
            print(f"Videos directory: {self.videos_path.absolute()}")
            print(f"Max storage: {MAX_STORAGE_GB}GB")
        print(f"Checking for events every {CHECK_INTERVAL} seconds")
        print(f"Notifications will be sent to: {TWILIO_TO_NUMBER}")
        print(f"Press Ctrl+C to stop")
        print(f"{'='*50}\n")
        
        # Send test message
        test_msg = "Ring SMS Notifier is now active and monitoring your devices!"
        if DOWNLOAD_VIDEOS:
            test_msg += f"\n📼 Video recording enabled"
        self.send_sms(test_msg)
        
        try:
            iteration = 0
            while True:
                self.check_for_events()
                
                # Print stats every 100 iterations (~17 minutes at 10s intervals)
                iteration += 1
                if iteration % 100 == 0 and DOWNLOAD_VIDEOS:
                    print(f"\n[{datetime.now()}] {self.get_stats()}\n")
                
                time.sleep(CHECK_INTERVAL)
        except KeyboardInterrupt:
            print(f"\n[{datetime.now()}] Shutting down Ring SMS Notifier...")
            final_msg = "Ring SMS Notifier has been stopped."
            if DOWNLOAD_VIDEOS:
                final_msg += f"\n{self.get_stats()}"
            self.send_sms(final_msg)

def main():
    # Validate environment variables
    required_vars = [
        'RING_USERNAME', 'RING_PASSWORD',
        'TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN',
        'TWILIO_FROM_NUMBER', 'TWILIO_TO_NUMBER'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("Error: Missing required environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease create a .env file with these variables.")
        return
    
    notifier = RingSMSNotifier()
    notifier.run()

if __name__ == '__main__':
    main()