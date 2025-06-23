import os
import time
import threading
import http.server
import socketserver
import signal
import sys
import queue
from PIL import Image
import io

# Output Configuration
WIDTH = 1920
HEIGHT = 1080
PORT = 8080
IMAGE_FOLDER = "img/"
DISPLAY_TIME = 1  # seconds per image

frame_queue = queue.Queue(maxsize=10)
current_image_index = 0
image_files = []
streaming_active = True
server_instance = None
server_thread = None
cycler_thread = None

def load_image_files():
    """Load all image files from the specified folder"""
    global image_files
    
    if not os.path.exists(IMAGE_FOLDER):
        print(f"Error: Image folder '{IMAGE_FOLDER}' does not exist!")
        sys.exit(1)
    
    # Supported image formats
    supported_formats = ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp')
    
    image_files = []
    for filename in os.listdir(IMAGE_FOLDER):
        if filename.lower().endswith(supported_formats):
            image_files.append(os.path.join(IMAGE_FOLDER, filename))
    
    image_files.sort()  # Sort alphabetically
    
    if not image_files:
        print(f"Error: No supported image files found in '{IMAGE_FOLDER}'!")
        print(f"Supported formats: {supported_formats}")
        sys.exit(1)
    
    print(f"Found {len(image_files)} images to stream")
    return image_files

def resize_image_to_fit(image, target_width, target_height):
    """
    Resize image to fit within target dimensions while maintaining aspect ratio.
    Adds black padding if necessary.
    """
    original_width, original_height = image.size
    
    # Calculate scaling factor to fit within target dimensions
    scale_factor = min(target_width / original_width, target_height / original_height)
    
    # Only scale down if image is larger than target
    if scale_factor < 1:
        new_width = int(original_width * scale_factor)
        new_height = int(original_height * scale_factor)
        image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    else:
        new_width, new_height = original_width, original_height
    
    # Create a black background of target size
    background = Image.new('RGB', (target_width, target_height), (0, 0, 0))
    
    # Calculate position to center the image
    x_offset = (target_width - new_width) // 2
    y_offset = (target_height - new_height) // 2
    
    # Paste the resized image onto the black background
    background.paste(image, (x_offset, y_offset))
    
    return background

def image_to_jpeg_bytes(image, quality=85):
    """Convert PIL Image to JPEG bytes"""
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG', quality=quality)
    return buffer.getvalue()

def load_and_process_image(image_path):
    """Load an image file and process it for streaming"""
    try:
        with Image.open(image_path) as img:
            # Convert to RGB if necessary (handles PNG with transparency, etc.)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize to fit within target dimensions
            processed_img = resize_image_to_fit(img, WIDTH, HEIGHT)
            
            # Convert to JPEG bytes
            jpeg_bytes = image_to_jpeg_bytes(processed_img)
            
            return jpeg_bytes
    
    except Exception as e:
        print(f"Error processing image {image_path}: {e}")
        return None

def image_cycler():
    """Cycle through images and add them to the frame queue"""
    global current_image_index, streaming_active
    
    print(f"Starting image cycle - {len(image_files)} images, {DISPLAY_TIME}s each")
    
    while current_image_index < len(image_files) and streaming_active:
        image_path = image_files[current_image_index]
        print(f"Loading image {current_image_index + 1}/{len(image_files)}: {os.path.basename(image_path)}")
        
        # Load and process the image
        frame_data = load_and_process_image(image_path)
        
        if frame_data:
            # Add frame to queue for the duration of DISPLAY_TIME
            start_time = time.time()
            while time.time() - start_time < DISPLAY_TIME and streaming_active:
                try:
                    if frame_queue.full():
                        _ = frame_queue.get_nowait()
                    frame_queue.put_nowait(frame_data)
                except queue.Full:
                    pass
                time.sleep(0.1)  # Small delay to control frame rate
        
        current_image_index += 1
    
    print("Finished cycling through all images")
    streaming_active = False

class MJPEGHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass
    
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=frame')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            self.end_headers()
            
            try:
                while streaming_active:
                    try:
                        # Get frame with timeout
                        frame = frame_queue.get(timeout=1.0)
                        self.wfile.write(b'--frame\r\n')
                        self.send_header('Content-Type', 'image/jpeg')
                        self.send_header('Content-Length', str(len(frame)))
                        self.end_headers()
                        self.wfile.write(frame)
                        self.wfile.write(b'\r\n')
                    except queue.Empty:
                        # No frame available, continue
                        continue
                    except (BrokenPipeError, ConnectionResetError):
                        # Client disconnected
                        break
            except Exception as e:
                print(f"Stream error: {e}")
        
        elif self.path == '/status':
            # Status endpoint
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            status = {
                "active": streaming_active,
                "current_image": current_image_index,
                "total_images": len(image_files),
                "current_file": os.path.basename(image_files[current_image_index]) if current_image_index < len(image_files) else "finished"
            }
            self.wfile.write(str(status).encode())
        
        else:
            self.send_error(404)

def start_server():
    """Start the HTTP server"""
    global server_instance
    
    try:
        server_instance = socketserver.ThreadingTCPServer(("", PORT), MJPEGHandler)
        print(f"Server started on http://0.0.0.0:{PORT}")
        print(f"View stream at: http://localhost:{PORT}")
        print(f"View status at: http://localhost:{PORT}/status")
        server_instance.serve_forever()
    except OSError as e:
        print(f"Error starting server on port {PORT}: {e}")
        cleanup()

def cleanup(signum=None, frame=None):
    """Aggressively clean up and exit"""
    global streaming_active, server_instance, server_thread, cycler_thread
    
    print("\n=== SHUTTING DOWN ===")
    
    # 1. Stop streaming
    streaming_active = False
    print("✓ Stopped streaming")
    
    # 2. Shutdown HTTP server
    if server_instance:
        try:
            print("✓ Shutting down HTTP server...")
            server_instance.shutdown()
            server_instance.server_close()
        except Exception as e:
            print(f"Warning: Error shutting down server: {e}")
    
    # 3. Clear the frame queue
    try:
        while not frame_queue.empty():
            frame_queue.get_nowait()
        print("✓ Cleared frame queue")
    except:
        pass
    
    # 4. Wait for threads to finish (with timeout)
    if cycler_thread and cycler_thread.is_alive():
        print("✓ Waiting for image cycler thread...")
        cycler_thread.join(timeout=2.0)
        if cycler_thread.is_alive():
            print("Warning: Image cycler thread didn't stop cleanly")
    
    if server_thread and server_thread.is_alive():
        print("✓ Waiting for server thread...")
        server_thread.join(timeout=2.0)
        if server_thread.is_alive():
            print("Warning: Server thread didn't stop cleanly")
    
    print("✓ Cleanup complete")
    
    # 5. Force exit
    try:
        sys.exit(0)
    except SystemExit:
        pass
    
    # 6. Nuclear option - force kill the process
    print("Force terminating...")
    os._exit(0)

def main():
    global streaming_active, server_thread, cycler_thread
    
    print("Image Stream Server")
    print(f"Configuration: {WIDTH}x{HEIGHT}, {DISPLAY_TIME}s per image")
    print(f"Image folder: {IMAGE_FOLDER}")
    
    # Load image files
    load_image_files()
    
    # Set up signal handlers for clean shutdown
    signal.signal(signal.SIGINT, cleanup)   # Ctrl+C
    signal.signal(signal.SIGTERM, cleanup)  # Termination signal
    
    try:
        # Start server in background thread
        server_thread = threading.Thread(target=start_server, daemon=True)
        server_thread.start()
        
        # Give server a moment to start
        time.sleep(1)
        
        # Start image cycling in background thread
        cycler_thread = threading.Thread(target=image_cycler, daemon=True)
        cycler_thread.start()
        
        # Wait for cycling to complete
        try:
            cycler_thread.join()
            print("Image cycling completed. Server will continue running...")
            print("Press Ctrl+C to exit")
            
            # Keep server running even after images are done
            while streaming_active:
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            print("\nKeyboard interrupt received")
            cleanup()
            
    except Exception as e:
        print(f"Fatal error: {e}")
        cleanup()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nForced interrupt")
        cleanup()
    except Exception as e:
        print(f"Unhandled exception: {e}")
        cleanup()