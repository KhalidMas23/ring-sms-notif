#!/usr/bin/env python3
"""
Ring Event Monitor with SMS Notifications
Monitors Ring doorbell/camera events and sends SMS alerts via Twilio
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

class RingSMSNotifier:
    def __init__(self):
        self.ring = None
        self.twilio_client = None
        self.last_event_ids = {}
        self.initialize()
    
    def initialize(self):
        """Initialize Ring and Twilio connections"""
        print(f"[{datetime.now()}] Initializing Ring SMS Notifier...")
        
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
        
        self.send_sms(message)
    
    def run(self):
        """Main monitoring loop"""
        print(f"\n{'='*50}")
        print("Ring SMS Notifier is now running!")
        print(f"Checking for events every {CHECK_INTERVAL} seconds")
        print(f"Notifications will be sent to: {TWILIO_TO_NUMBER}")
        print(f"Press Ctrl+C to stop")
        print(f"{'='*50}\n")
        
        # Send test message
        self.send_sms("Ring SMS Notifier is now active and monitoring your devices!")
        
        try:
            while True:
                self.check_for_events()
                time.sleep(CHECK_INTERVAL)
        except KeyboardInterrupt:
            print(f"\n[{datetime.now()}] Shutting down Ring SMS Notifier...")
            self.send_sms("Ring SMS Notifier has been stopped.")

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