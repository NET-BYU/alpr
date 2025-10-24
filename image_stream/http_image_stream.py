#!/usr/bin/env python3
"""
HTTP Image Stream Server
Streams images from a folder as an HTTP camera feed with configurable timing and loop options.
"""

import os
import time
import argparse
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import BytesIO
import threading
from PIL import Image
import cv2
import numpy as np


class ImageStreamer:
    def __init__(self, image_folder, duration=2.0, loop=True, default_image='default.jpg'):
        """
        Initialize the image streamer.

        Args:
            image_folder: Path to folder containing images
            duration: Time to display each image in seconds
            loop: Whether to loop through images or stop at the end
            default_image: Path to default image to show when no images available
        """
        self.image_folder = Path(image_folder)
        self.duration = duration
        self.loop = loop
        self.default_image = Path(default_image)
        self.current_frame = None
        self.lock = threading.Lock()
        self.running = False
        self.target_size = (1920, 1080)  # 1080p resolution

    def get_image_files(self):
        """Get list of image files (jpg, jpeg, png) from the folder."""
        if not self.image_folder.exists():
            return []

        image_extensions = {'.jpg', '.jpeg', '.png'}
        image_files = []

        for ext in image_extensions:
            image_files.extend(self.image_folder.glob(f'*{ext}'))
            image_files.extend(self.image_folder.glob(f'*{ext.upper()}'))

        # Natural sort (handles numbers properly: 1, 2, 3, ... 10, 11 instead of 1, 10, 11, 2)
        import re

        def natural_sort_key(path):
            return [int(text) if text.isdigit() else text.lower()
                    for text in re.split('([0-9]+)', str(path.name))]

        return sorted(image_files, key=natural_sort_key)

    def load_and_resize_image(self, image_path):
        """Load an image and resize it to 1080p."""
        try:
            img = cv2.imread(str(image_path))
            if img is None:
                return None

            # Get original dimensions
            h, w = img.shape[:2]
            target_w, target_h = self.target_size

            # Calculate scaling to fit within 1080p while maintaining aspect ratio
            scale = min(target_w / w, target_h / h)
            new_w = int(w * scale)
            new_h = int(h * scale)

            # Resize image
            resized = cv2.resize(img, (new_w, new_h),
                                 interpolation=cv2.INTER_AREA)

            # Create black canvas at 1080p
            canvas = np.zeros((target_h, target_w, 3), dtype=np.uint8)

            # Center the resized image on the canvas
            y_offset = (target_h - new_h) // 2
            x_offset = (target_w - new_w) // 2
            canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized

            return canvas
        except Exception as e:
            print(f"Error loading image {image_path}: {e}")
            return None

    def get_default_frame(self):
        """Load the default image or create a black frame."""
        if self.default_image.exists():
            frame = self.load_and_resize_image(self.default_image)
            if frame is not None:
                return frame

        # Return black frame if default image not available
        return np.zeros((self.target_size[1], self.target_size[0], 3), dtype=np.uint8)

    def update_frames(self):
        """Background thread to cycle through images."""
        self.running = True

        while self.running:
            image_files = self.get_image_files()

            if not image_files:
                # No images, use default
                with self.lock:
                    self.current_frame = self.get_default_frame()
                time.sleep(self.duration)
                continue

            # Cycle through images
            for image_path in image_files:
                if not self.running:
                    break

                frame = self.load_and_resize_image(image_path)
                if frame is not None:
                    with self.lock:
                        self.current_frame = frame
                    print(f"Displaying: {image_path.name}")
                    time.sleep(self.duration)

            # After all images, either loop or show black/default
            if not self.loop:
                with self.lock:
                    self.current_frame = self.get_default_frame()
                print("Reached end of images. Showing default frame.")
                # Keep showing the default frame
                while self.running:
                    time.sleep(1)

    def get_current_frame(self):
        """Get the current frame as JPEG bytes."""
        with self.lock:
            if self.current_frame is None:
                self.current_frame = self.get_default_frame()

            # Encode frame as JPEG with lower quality for better streaming (50-60 is good for ALPR)
            ret, jpeg = cv2.imencode('.jpg', self.current_frame,
                                     [cv2.IMWRITE_JPEG_QUALITY, 55])
            if ret:
                return jpeg.tobytes()
            return None

    def start(self):
        """Start the frame update thread."""
        self.thread = threading.Thread(target=self.update_frames, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop the frame update thread."""
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join(timeout=2)


class StreamHandler(BaseHTTPRequestHandler):
    """HTTP request handler for streaming."""

    def log_message(self, format, *args):
        """Override to reduce console spam."""
        pass

    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>MJPEG Stream - OpenALPR Compatible</title>
                <style>
                    body {
                        margin: 0;
                        padding: 20px;
                        background-color: #000;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;
                        align-items: center;
                        min-height: 100vh;
                        color: #fff;
                        font-family: Arial, sans-serif;
                    }
                    h1 {
                        margin-bottom: 20px;
                    }
                    .info {
                        background-color: #222;
                        padding: 15px;
                        border-radius: 5px;
                        margin-bottom: 20px;
                        max-width: 600px;
                    }
                    img {
                        max-width: 100%;
                        height: auto;
                        border: 2px solid #333;
                        box-shadow: 0 0 10px rgba(255,255,255,0.1);
                    }
                </style>
            </head>
            <body>
                <h1>MJPEG Camera Stream</h1>
                <div class="info">
                    <strong>Stream URL for OpenALPR RekorScout:</strong><br>
                    <code>http://""" + self.headers.get('Host', 'localhost:8000') + """/video.mjpeg</code><br>
                    <br>
                    <strong>Alternative URLs:</strong><br>
                    <code>http://""" + self.headers.get('Host', 'localhost:8000') + """/stream</code><br>
                    <code>http://""" + self.headers.get('Host', 'localhost:8000') + """/mjpeg</code>
                </div>
                <img src="/video.mjpeg" />
            </body>
            </html>
            """
            self.wfile.write(html.encode())

        elif self.path in ['/stream', '/video.mjpeg', '/mjpeg', '/video.mjpg']:
            # MJPEG stream - compatible with OpenALPR RekorScout and other IP camera software
            self.send_response(200)
            self.send_header(
                'Content-Type', 'multipart/x-mixed-replace; boundary=--jpgboundary')
            self.send_header(
                'Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            self.send_header('Connection', 'close')
            self.end_headers()

            try:
                while True:
                    frame = self.server.streamer.get_current_frame()
                    if frame:
                        self.wfile.write(b'--jpgboundary\r\n')
                        self.wfile.write(b'Content-Type: image/jpeg\r\n')
                        self.wfile.write(
                            f'Content-Length: {len(frame)}\r\n'.encode())
                        self.wfile.write(b'\r\n')
                        self.wfile.write(frame)
                        self.wfile.write(b'\r\n')
                    # Update rate - adjust if needed for smoother or slower transitions
                    time.sleep(0.033)
            except (ConnectionResetError, BrokenPipeError):
                # Client disconnected
                pass
            except Exception as e:
                print(f"Stream error: {e}")

        else:
            self.send_error(404)


class StreamingServer(HTTPServer):
    """Custom HTTP server that holds a reference to the streamer."""

    def __init__(self, server_address, RequestHandlerClass, streamer):
        super().__init__(server_address, RequestHandlerClass)
        self.streamer = streamer


def main():
    parser = argparse.ArgumentParser(
        description='HTTP Image Stream Server - Stream images from a folder as an HTTP camera feed',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --duration 3.0 --loop
  %(prog)s --duration 5.0 --no-loop --port 8080
  %(prog)s --images ./my_images --duration 2.5
        """
    )

    parser.add_argument(
        '--images',
        type=str,
        default='images',
        help='Path to folder containing images (default: images)'
    )

    parser.add_argument(
        '--duration',
        type=float,
        default=2.0,
        help='Time to display each image in seconds (default: 2.0)'
    )

    parser.add_argument(
        '--loop',
        action='store_true',
        default=True,
        help='Loop through images continuously (default: True)'
    )

    parser.add_argument(
        '--no-loop',
        action='store_false',
        dest='loop',
        help='Stop at the end and show default image'
    )

    parser.add_argument(
        '--default',
        type=str,
        default='default.jpg',
        help='Path to default image to show when no images available (default: default.jpg)'
    )

    parser.add_argument(
        '--port',
        type=int,
        default=8000,
        help='HTTP server port (default: 8000)'
    )

    parser.add_argument(
        '--host',
        type=str,
        default='0.0.0.0',
        help='HTTP server host (default: 0.0.0.0)'
    )

    args = parser.parse_args()

    # Create image streamer
    print(f"Initializing image streamer...")
    print(f"  Images folder: {args.images}")
    print(f"  Duration: {args.duration}s per image")
    print(f"  Loop: {args.loop}")
    print(f"  Default image: {args.default}")
    print(f"  Output: 1920x1080 (1080p)")

    streamer = ImageStreamer(
        image_folder=args.images,
        duration=args.duration,
        loop=args.loop,
        default_image=args.default
    )

    # Start the frame update thread
    streamer.start()

    # Create and start HTTP server
    server = StreamingServer((args.host, args.port), StreamHandler, streamer)

    print(f"\nServer started at http://{args.host}:{args.port}")
    print(f"Open this URL in a browser to view the stream")
    print("Press Ctrl+C to stop the server\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        streamer.stop()
        server.shutdown()
        print("Server stopped.")


if __name__ == '__main__':
    main()
