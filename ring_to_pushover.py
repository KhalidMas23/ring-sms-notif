#!/usr/bin/env python3
"""
Ring Event Monitor with Pushover Notifications and Video Recording
Simple, reliable push notifications - perfect for hobbyists!
"""

import os
import time
import json
from datetime import datetime
from pathlib import Path
from ring_doorbell import Ring, Auth
from oauthlib.oauth2 import MissingTokenError
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

# Configuration
RING_USERNAME = os.getenv('RING_USERNAME')
RING_PASSWORD = os.getenv('RING_PASSWORD')
PUSHOVER_USER_KEY = os.getenv('PUSHOVER_USER_KEY')
PUSHOVER_API_TOKEN = os.getenv('PUSHOVER_API_TOKEN')
TOKEN_FILE = 'ring_token.cache'
CHECK_INTERVAL = 10  # seconds between checks
DOWNLOAD_VIDEOS = os.getenv('DOWNLOAD_VIDEOS', 'true').lower() == 'true'
VIDEOS_DIR = os.getenv('VIDEOS_DIR', './ring_videos')
MAX_STORAGE_GB = float(os.getenv('MAX_STORAGE_GB', '10'))

class RingPushoverNotifier:
    def __init__(self):
        self.ring = None
        self.last_event_ids = {}
        self.videos_path = Path(VIDEOS_DIR)
        self.was_connected = True  # Track connection state
        self.consecutive_errors = 0  # Track error count
        self.connection_lost_time = None  # Track when connection was lost
        self.initialize()
    
    def initialize(self):
        """Initialize Ring connection"""
        print(f"[{datetime.now()}] Initializing Ring Pushover Notifier...")
        
        # Create videos directory if it doesn't exist
        if DOWNLOAD_VIDEOS:
            self.videos_path.mkdir(parents=True, exist_ok=True)
            print(f"✓ Videos directory created: {self.videos_path.absolute()}")
        
        print("✓ Pushover configured")
        
        # Initialize Ring authentication with token cache
        token_cache = None
        if os.path.exists(TOKEN_FILE):
            try:
                with open(TOKEN_FILE, 'r') as f:
                    token_cache = json.load(f)
                print("✓ Found cached token, skipping authentication")
            except Exception as e:
                print(f"Warning: Could not load cached token: {e}")
        
        auth = Auth("MyRingPushoverApp/1.0", token_cache, token_updater=self.token_updated)
        
        # Only fetch token if we don't have a cached one
        if not token_cache:
            try:
                auth.fetch_token(RING_USERNAME, RING_PASSWORD)
            except Exception as e:
                print("\n" + "="*60)
                print("Ring requires 2-Factor Authentication")
                print("="*60)
                print("\nCheck your Ring app or email for a 2FA code.")
                print("If you received a code, enter it below.")
                print("If you need to approve in the app, do that now and press Enter.\n")
                
                two_fa_code = input("Enter 2FA code (or press Enter if approved in app): ").strip()
                
                if two_fa_code:
                    try:
                        auth.fetch_token(RING_USERNAME, RING_PASSWORD, two_fa_code)
                    except Exception as e2:
                        print(f"\n2FA failed: {e2}")
                        print("\nTroubleshooting:")
                        print("1. Check your Ring username/password in .env")
                        print("2. Make sure you're entering the correct 2FA code")
                        print("3. Try approving the login in your Ring app instead")
                        raise
                else:
                    # Try again after user approved in app
                    try:
                        auth.fetch_token(RING_USERNAME, RING_PASSWORD)
                    except Exception as e3:
                        print(f"\nStill failed: {e3}")
                        print("\nThe Ring library may have issues with 2FA on your account.")
                        print("Try this: Log into Ring in a browser, approve 'trust this device',")
                        print("then run this script again.")
                        raise
        
        self.ring = Ring(auth)
        self.ring.update_data()
        print("✓ Ring client initialized")
        
        # List devices
        devices = self.ring.devices()
        
        # Access devices correctly - RingDevices acts like a dict
        doorbell_count = len(devices['doorbots']) if 'doorbots' in devices else 0
        camera_count = len(devices['stickup_cams']) if 'stickup_cams' in devices else 0
        
        print(f"\nFound {doorbell_count} doorbell(s)")
        print(f"Found {camera_count} camera(s)")
        
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
        
        devices = self.ring.devices()
        
        # Access doorbells from devices dict
        if 'doorbots' in devices:
            for doorbell in devices['doorbots']:
                history = doorbell.history(limit=1)
                if history:
                    self.last_event_ids[doorbell.id] = history[0]['id']
                    print(f"  {doorbell.name}: Last event ID {history[0]['id']}")
        
        # Access cameras from devices dict
        if 'stickup_cams' in devices:
            for camera in devices['stickup_cams']:
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
            
            video_files = []
            for file in self.videos_path.rglob('*.mp4'):
                if file.is_file():
                    video_files.append((file, file.stat().st_mtime))
            
            video_files.sort(key=lambda x: x[1])  # Sort by oldest first
            
            while current_usage > MAX_STORAGE_GB * 0.9 and video_files:
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
            self.cleanup_old_videos()
            
            recording_url = event.get('recording', {}).get('status')
            
            if not recording_url or recording_url != 'ready':
                print(f"  Video not ready yet for event {event['id']}")
                return None
            
            video_url = device.recording_url(event['id'])
            
            if not video_url:
                print(f"  No video URL available for event {event['id']}")
                return None
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            device_name = device.name.replace(' ', '_').replace('/', '_')
            event_kind = event.get('kind', 'unknown')
            filename = f"{timestamp}_{device_name}_{event_kind}_{event['id']}.mp4"
            filepath = self.videos_path / filename
            
            print(f"  Downloading video to {filename}...")
            
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
    
    def extract_frame_from_video(self, video_path):
        """Extract first frame from video as JPEG"""
        try:
            import cv2
            
            cap = cv2.VideoCapture(video_path)
            ret, frame = cap.read()
            cap.release()
            
            if ret:
                # Save frame as JPEG
                frame_path = video_path.replace('.mp4', '_frame.jpg')
                cv2.imwrite(frame_path, frame)
                print(f"  ✓ Frame extracted: {os.path.basename(frame_path)}")
                return frame_path
            else:
                print(f"  ✗ Could not read video frame")
                return None
                
        except ImportError:
            print(f"  ℹ opencv-python not installed, skipping frame extraction")
            print(f"    Install with: pip install opencv-python")
            return None
        except Exception as e:
            print(f"  ✗ Frame extraction failed: {e}")
            return None
    
    def send_pushover(self, title, message, priority=0, image_path=None):
        """
        Send push notification via Pushover
        Priority: -2=lowest, -1=low, 0=normal, 1=high, 2=emergency
        image_path: Optional path to image file to attach
        """
        try:
            data = {
                "token": PUSHOVER_API_TOKEN,
                "user": PUSHOVER_USER_KEY,
                "title": title,
                "message": message,
                "priority": priority,
                "sound": "pushover"  # Can customize: pushover, bike, bugle, cashregister, etc.
            }
            
            files = {}
            if image_path and os.path.exists(image_path):
                # Attach image to notification
                files = {"attachment": ("image.jpg", open(image_path, "rb"), "image/jpeg")}
            
            response = requests.post(
                "https://api.pushover.net/1/messages.json",
                data=data,
                files=files
            )
            
            if response.status_code == 200:
                print(f"[{datetime.now()}] Pushover sent: {title}")
                return True
            else:
                print(f"[{datetime.now()}] Pushover error: {response.text}")
                return False
                
        except Exception as e:
            print(f"[{datetime.now()}] Error sending Pushover: {e}")
            return False
    
    def check_for_events(self):
        """Check for new Ring events"""
        try:
            self.ring.update_data()
            devices = self.ring.devices()
            
            # Check doorbells
            if 'doorbots' in devices:
                for doorbell in devices['doorbots']:
                    self._check_device_events(doorbell)
            
            # Check cameras
            if 'stickup_cams' in devices:
                for camera in devices['stickup_cams']:
                    self._check_device_events(camera)
            
            # Connection successful - check if we just recovered
            if not self.was_connected and self.connection_lost_time:
                recovery_time = datetime.now()
                disconnect_duration = recovery_time - self.connection_lost_time
                
                # Format duration nicely
                minutes = int(disconnect_duration.total_seconds() / 60)
                seconds = int(disconnect_duration.total_seconds() % 60)
                
                if minutes > 0:
                    duration_str = f"{minutes} minute{'s' if minutes != 1 else ''} and {seconds} second{'s' if seconds != 1 else ''}"
                else:
                    duration_str = f"{seconds} second{'s' if seconds != 1 else ''}"
                
                print(f"\n[{recovery_time}] Connection restored! (Was down for {duration_str})")
                
                self.send_pushover(
                    "Ring Connection Restored",
                    f"Connection restored at {recovery_time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    f"Lost connection at: {self.connection_lost_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"Downtime: {duration_str}\n\n"
                    f"Monitoring resumed. Any events during downtime were not recorded.",
                    priority=1  # High priority for reconnection alerts
                )
                self.was_connected = True
                self.connection_lost_time = None
            
            # Reset error counter on successful check
            self.consecutive_errors = 0
                
        except Exception as e:
            self.consecutive_errors += 1
            
            # Mark connection as lost after 3 consecutive errors (30 seconds)
            if self.was_connected and self.consecutive_errors >= 3:
                self.connection_lost_time = datetime.now()
                print(f"\n[{self.connection_lost_time}] Connection lost! Will notify when restored.")
                self.was_connected = False
            
            print(f"[{datetime.now()}] Error checking events ({self.consecutive_errors}): {e}")
    
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
        
        # Format notification based on event type
        if kind == 'ding':
            title = f"Doorbell: {device.name}"
            message = f"Doorbell pressed\nTime: {created_at}"
            priority = 1  # High priority for doorbell
        elif kind == 'motion':
            title = f"Motion: {device.name}"
            message = f"Motion detected\nTime: {created_at}"
            priority = 0  # Normal priority for motion
        elif kind == 'on_demand':
            title = f"Live View: {device.name}"
            message = f"Live view started\nTime: {created_at}"
            priority = 0
        else:
            title = f"Ring: {device.name}"
            message = f"{kind} event\nTime: {created_at}"
            priority = 0
        
        print(f"\n[{datetime.now()}] New event detected!")
        print(f"  Device: {device.name}")
        print(f"  Type: {kind}")
        print(f"  Time: {created_at}")
        
        # Try to capture snapshot
        snapshot_path = None
        try:
            # Get latest snapshot from Ring
            if hasattr(device, 'get_snapshot'):
                print(f"  Capturing snapshot...")
                snapshot_data = device.get_snapshot()
                
                if snapshot_data:
                    # Save snapshot temporarily
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    device_name = device.name.replace(' ', '_').replace('/', '_')
                    snapshot_filename = f"{timestamp}_{device_name}_snapshot.jpg"
                    snapshot_path = self.videos_path / snapshot_filename
                    
                    with open(snapshot_path, 'wb') as f:
                        f.write(snapshot_data)
                    
                    print(f"  ✓ Snapshot saved: {snapshot_filename}")
        except Exception as e:
            print(f"  Snapshot capture failed: {e}")
        
        # Download video if enabled
        video_path = None
        if DOWNLOAD_VIDEOS and kind in ['ding', 'motion']:
            print(f"  Waiting for video to be ready...")
            time.sleep(5)
            video_path = self.download_video(device, event)
            
            if video_path:
                message += f"\n\nVideo saved locally"
                
                # If no snapshot, try extracting frame from video
                if not snapshot_path:
                    print(f"  No snapshot available, extracting frame from video...")
                    snapshot_path = self.extract_frame_from_video(video_path)
        
        # Send notification with snapshot if available
        self.send_pushover(title, message, priority, image_path=str(snapshot_path) if snapshot_path else None)
        
        # Clean up snapshot after sending (optional - comment out if you want to keep them)
        # if snapshot_path and snapshot_path.exists():
        #     snapshot_path.unlink()
        #     print(f"  Snapshot sent and deleted")
    
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
        print("Ring Pushover Notifier with Video Recording")
        print(f"Video downloads: {'ENABLED' if DOWNLOAD_VIDEOS else 'DISABLED'}")
        if DOWNLOAD_VIDEOS:
            print(f"Videos directory: {self.videos_path.absolute()}")
            print(f"Max storage: {MAX_STORAGE_GB}GB")
        print(f"Checking for events every {CHECK_INTERVAL} seconds")
        print(f"Notifications via Pushover")
        print(f"Press Ctrl+C to stop")
        print(f"{'='*50}\n")
        
        # Send test notification
        test_title = "Ring Notifier Started"
        test_message = "Ring Pushover Notifier is now active and monitoring your devices!"
        if DOWNLOAD_VIDEOS:
            test_message += "\n\nVideo recording enabled"
        
        self.send_pushover(test_title, test_message, priority=0)
        
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
            print(f"\n[{datetime.now()}] Shutting down Ring Pushover Notifier...")
            final_title = "Ring Notifier Stopped"
            final_message = "Ring Pushover Notifier has been stopped."
            if DOWNLOAD_VIDEOS:
                final_message += f"\n\n{self.get_stats()}"
            self.send_pushover(final_title, final_message, priority=-1)

def main():
    # Validate environment variables
    required_vars = [
        'RING_USERNAME', 'RING_PASSWORD',
        'PUSHOVER_USER_KEY', 'PUSHOVER_API_TOKEN'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("Error: Missing required environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease create a .env file with these variables.")
        print("Get your Pushover credentials at: https://pushover.net")
        return
    
    notifier = RingPushoverNotifier()
    notifier.run()

if __name__ == '__main__':
    main()