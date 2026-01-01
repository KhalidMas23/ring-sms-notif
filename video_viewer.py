#!/usr/bin/env python3
"""
Simple web interface to view Ring videos
Run this to browse videos from any device on your network
"""

from flask import Flask, render_template_string, send_file, abort
from pathlib import Path
import os
from datetime import datetime

VIDEOS_DIR = os.getenv('VIDEOS_DIR', './ring_videos')

app = Flask(__name__)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Ring Video Viewer</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .stats {
            background: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .video-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
        }
        .video-card {
            background: white;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }
        .video-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }
        video {
            width: 100%;
            border-radius: 4px;
            background: black;
        }
        .video-info {
            margin-top: 10px;
        }
        .video-title {
            font-weight: bold;
            color: #333;
            margin-bottom: 5px;
        }
        .video-meta {
            font-size: 0.9em;
            color: #666;
        }
        .download-btn {
            display: inline-block;
            margin-top: 10px;
            padding: 8px 16px;
            background: #007bff;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            font-size: 0.9em;
        }
        .download-btn:hover {
            background: #0056b3;
        }
        .no-videos {
            text-align: center;
            padding: 40px;
            color: #666;
        }
    </style>
</head>
<body>
    <h1>🔔 Ring Video Archive</h1>
    
    <div class="stats">
        <strong>Total Videos:</strong> {{ video_count }} |
        <strong>Total Size:</strong> {{ total_size_mb }} MB |
        <strong>Oldest:</strong> {{ oldest_date }} |
        <strong>Newest:</strong> {{ newest_date }}
    </div>
    
    {% if videos %}
    <div class="video-grid">
        {% for video in videos %}
        <div class="video-card">
            <video controls preload="metadata">
                <source src="/video/{{ video.filename }}" type="video/mp4">
                Your browser doesn't support video playback.
            </video>
            <div class="video-info">
                <div class="video-title">{{ video.device }}</div>
                <div class="video-meta">
                    {{ video.event_type }} | {{ video.date }}<br>
                    {{ video.time }} | {{ video.size_mb }} MB
                </div>
                <a href="/video/{{ video.filename }}" download class="download-btn">
                    Download
                </a>
            </div>
        </div>
        {% endfor %}
    </div>
    {% else %}
    <div class="no-videos">
        <h2>No videos found</h2>
        <p>Videos will appear here once Ring events are recorded.</p>
    </div>
    {% endif %}
</body>
</html>
'''

def parse_filename(filename):
    """Parse information from Ring video filename"""
    # Format: YYYYMMDD_HHMMSS_DeviceName_EventType_EventID.mp4
    parts = filename.replace('.mp4', '').split('_')
    
    if len(parts) >= 4:
        date_str = parts[0]
        time_str = parts[1]
        device = '_'.join(parts[2:-2]) if len(parts) > 4 else parts[2]
        event_type = parts[-2]
        
        # Format date and time nicely
        date = f"{date_str[4:6]}/{date_str[6:8]}/{date_str[0:4]}"
        time = f"{time_str[0:2]}:{time_str[2:4]}:{time_str[4:6]}"
        
        return {
            'device': device.replace('_', ' '),
            'event_type': event_type.capitalize(),
            'date': date,
            'time': time
        }
    
    return {
        'device': 'Unknown',
        'event_type': 'Unknown',
        'date': 'Unknown',
        'time': 'Unknown'
    }

@app.route('/')
def index():
    videos_path = Path(VIDEOS_DIR)
    
    if not videos_path.exists():
        videos_path.mkdir(parents=True, exist_ok=True)
    
    # Get all video files
    video_files = list(videos_path.glob('*.mp4'))
    video_files.sort(reverse=True)  # Newest first
    
    videos = []
    total_size = 0
    
    for video_file in video_files:
        info = parse_filename(video_file.name)
        size_mb = video_file.stat().st_size / (1024 * 1024)
        total_size += size_mb
        
        videos.append({
            'filename': video_file.name,
            'size_mb': f"{size_mb:.2f}",
            **info
        })
    
    # Get date range
    oldest_date = "N/A"
    newest_date = "N/A"
    if video_files:
        oldest_date = datetime.fromtimestamp(video_files[-1].stat().st_mtime).strftime('%m/%d/%Y')
        newest_date = datetime.fromtimestamp(video_files[0].stat().st_mtime).strftime('%m/%d/%Y')
    
    return render_template_string(
        HTML_TEMPLATE,
        videos=videos,
        video_count=len(videos),
        total_size_mb=f"{total_size:.2f}",
        oldest_date=oldest_date,
        newest_date=newest_date
    )

@app.route('/video/<filename>')
def serve_video(filename):
    """Serve video file"""
    videos_path = Path(VIDEOS_DIR)
    video_path = videos_path / filename
    
    # Security check - ensure file is in videos directory
    if not video_path.exists() or not video_path.is_relative_to(videos_path):
        abort(404)
    
    return send_file(video_path, mimetype='video/mp4')

if __name__ == '__main__':
    print(f"\n{'='*50}")
    print("Ring Video Viewer")
    print(f"Videos directory: {Path(VIDEOS_DIR).absolute()}")
    print(f"\nAccess the viewer at:")
    print(f"  http://localhost:5000")
    print(f"  http://[your-pi-ip]:5000")
    print(f"\nPress Ctrl+C to stop")
    print(f"{'='*50}\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False)