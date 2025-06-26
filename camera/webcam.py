import subprocess
import threading
import http.server
import socketserver
import signal
import sys
import queue
import time
import logging

# Output Configuration - Reduced for better performance
WIDTH = 1280  # Reduced from 1920
HEIGHT = 720  # Reduced from 1080
FRAMERATE = 15  # Reduced from 30 for smoother performance
PORT = 8080
DEVICE = "/dev/video0"

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# USB webcam capture command - optimized
ffmpeg_capture_cmd = [
    "ffmpeg",
    "-f", "v4l2",
    "-video_size", f"{WIDTH}x{HEIGHT}",
    "-framerate", str(FRAMERATE),
    "-i", DEVICE,
    "-vcodec", "mjpeg",  # Use hardware MJPEG if available
    "-q:v", "8",  # Slightly lower quality for better performance
    "-f", "mjpeg",
    "-"
]

frame_queue = queue.Queue(maxsize=5)  # Reduced queue size
ffmpeg_process = None

def ffmpeg_reader():
    global ffmpeg_process
    try:
        ffmpeg_process = subprocess.Popen(
            ffmpeg_capture_cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            bufsize=10**5  # Larger buffer
        )
        
        buffer = bytearray()
        chunk_size = 8192  # Larger chunks
        
        while ffmpeg_process.poll() is None:
            try:
                chunk = ffmpeg_process.stdout.read(chunk_size)
                if not chunk:
                    time.sleep(0.001)  # Small delay to prevent busy waiting
                    continue
                    
                buffer.extend(chunk)
                
                # More efficient frame extraction
                while len(buffer) > 2:
                    # Find JPEG start
                    start_idx = -1
                    for i in range(len(buffer) - 1):
                        if buffer[i] == 0xFF and buffer[i + 1] == 0xD8:
                            start_idx = i
                            break
                    
                    if start_idx == -1:
                        buffer = buffer[-1:]  # Keep last byte in case it's 0xFF
                        break
                    
                    # Remove data before JPEG start
                    if start_idx > 0:
                        buffer = buffer[start_idx:]
                    
                    # Find JPEG end
                    end_idx = -1
                    for i in range(2, len(buffer) - 1):
                        if buffer[i] == 0xFF and buffer[i + 1] == 0xD9:
                            end_idx = i + 2
                            break
                    
                    if end_idx == -1:
                        break  # Wait for more data
                    
                    # Extract frame
                    frame = bytes(buffer[:end_idx])
                    buffer = buffer[end_idx:]
                    
                    # Add to queue (non-blocking)
                    try:
                        if frame_queue.full():
                            frame_queue.get_nowait()  # Drop oldest frame
                        frame_queue.put_nowait(frame)
                    except queue.Full:
                        pass
                        
            except Exception as e:
                logger.error(f"Error in frame processing: {e}")
                break
                
    except Exception as e:
        logger.error(f"FFmpeg process error: {e}")
    finally:
        if ffmpeg_process:
            ffmpeg_process.terminate()

class MJPEGHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Disable request logging for performance
        
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=frame')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            self.end_headers()
            
            try:
                while True:
                    try:
                        frame = frame_queue.get(timeout=1.0)
                        self.wfile.write(b'--frame\r\n')
                        self.send_header('Content-Type', 'image/jpeg')
                        self.send_header('Content-Length', str(len(frame)))
                        self.end_headers()
                        self.wfile.write(frame)
                        self.wfile.write(b'\r\n')
                    except queue.Empty:
                        continue
                        
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
        else:
            self.send_error(404)

def start_server():
    with socketserver.ThreadingTCPServer(("", PORT), MJPEGHandler) as httpd:
        httpd.allow_reuse_address = True
        logger.info(f"Server starting on port {PORT}")
        httpd.serve_forever()

def cleanup(signum, frame):
    global ffmpeg_process
    logger.info("Shutting down...")
    if ffmpeg_process:
        ffmpeg_process.terminate()
        ffmpeg_process.wait(timeout=5)
    sys.exit(0)

# Signal handlers
signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

# Start threads
ffmpeg_thread = threading.Thread(target=ffmpeg_reader, daemon=True)
server_thread = threading.Thread(target=start_server, daemon=True)

ffmpeg_thread.start()
server_thread.start()

try:
    signal.pause()
except KeyboardInterrupt:
    cleanup(None, None)