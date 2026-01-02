#!/usr/bin/env python3
"""
Ring Device Debug Script - See what devices are available
"""

import os
from dotenv import load_dotenv
from ring_doorbell import Ring, Auth

load_dotenv()

RING_USERNAME = os.getenv('RING_USERNAME')
RING_PASSWORD = os.getenv('RING_PASSWORD')

print("Authenticating with Ring...")
auth = Auth("RingDebug/1.0", None)

try:
    auth.fetch_token(RING_USERNAME, RING_PASSWORD)
except:
    code = input("Enter 2FA code: ")
    auth.fetch_token(RING_USERNAME, RING_PASSWORD, code)

ring = Ring(auth)
ring.update_data()

print("\n" + "="*60)
print("Ring Account Debug Info")
print("="*60)

# Check what attributes Ring object has
print("\nRing object attributes:")
for attr in dir(ring):
    if not attr.startswith('_'):
        print(f"  - {attr}")

# Try to get devices
print("\n" + "="*60)
print("Attempting to access devices...")
print("="*60)

try:
    devices = ring.devices()
    print(f"\ndevices() returned type: {type(devices)}")
    print(f"devices() value: {devices}")
except Exception as e:
    print(f"Error calling devices(): {e}")

# Try different device attributes
print("\n" + "="*60)
print("Checking for device attributes...")
print("="*60)

device_attrs = ['doorbots', 'stickup_cams', 'chimes', 'other', 'devices', 'all_devices']

for attr in device_attrs:
    try:
        value = getattr(ring, attr, None)
        if value is not None:
            print(f"\n✓ ring.{attr}:")
            print(f"  Type: {type(value)}")
            if hasattr(value, '__len__'):
                print(f"  Count: {len(value)}")
                if len(value) > 0:
                    print(f"  First item: {value[0]}")
                    print(f"  First item type: {type(value[0])}")
                    if hasattr(value[0], 'name'):
                        print(f"  First item name: {value[0].name}")
            else:
                print(f"  Value: {value}")
        else:
            print(f"✗ ring.{attr} is None or doesn't exist")
    except Exception as e:
        print(f"✗ Error accessing ring.{attr}: {e}")

print("\n" + "="*60)
print("Debug complete!")
print("="*60)