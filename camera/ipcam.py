import subprocess
import threading                                           
import http.server
import socketserver 
import signal 
import sys                
import queue                

# Output Configuration         
WIDTH = 1920   
HEIGHT = 1080
FRAMERATE = 60
PORT = 8080

libcamera_cmd = [
    "libcamera-vid",
    "-t", "0",       
    "--width", str(WIDTH),     
    "--height", str(HEIGHT),           
    "--framerate", str(FRAMERATE),
    "--codec", "yuv420",
    "--inline",   
    "-o", "-"   
]      
                                               
ffmpeg_cmd = [                                             
    "ffmpeg",                                                                                  
    "-f", "rawvideo",                                      
    "-pixel_format", "yuv420p",      
    "-video_size", f"{WIDTH}x{HEIGHT}",                    
    "-framerate", str(FRAMERATE),
    "-i", "-",                                                                                                                                                                                
    "-f", "mjpeg",
    "-q:v", "5",
    "-"                                      
]                    
                                               
libcamera_proc = subprocess.Popen(libcamera_cmd, stdout=subprocess.PIPE)                                               
                                               
frame_queue = queue.Queue(maxsize=10)       
                                               
def ffmpeg_reader():                                                                           
    ffmpeg_proc = subprocess.Popen(ffmpeg_cmd, stdin=libcamera_proc.stdout, stdout=subprocess.PIPE, bufsize=0)                                                                                                                                
    buffer = b""                       
    while True:     
        chunk = ffmpeg_proc.stdout.read(4096)
        if not chunk:                                                                          
            break                                                                              
        buffer += chunk           
        while True:     
            start = buffer.find(b'\xff\xd8')
            end = buffer.find(b'\xff\xd9')
            if start != -1 and end != -1 and end > start:                                                              
                frame = buffer[start:end+2]                                                    
                buffer = buffer[end+2:]
                try:                                       
                    if frame_queue.full():                                                     
                        _ = frame_queue.get_nowait()                                                                   
                    frame_queue.put_nowait(frame)                                                                      
                except queue.Full: 
                    pass                                                                       
            else:             
                break
                                               
ffmpeg_thread = threading.Thread(target=ffmpeg_reader, daemon=True)                                                    
ffmpeg_thread.start()                                                                          
                                                                                               
class MJPEGHandler(http.server.BaseHTTPRequestHandler):                
    def do_GET(self):                 
        if self.path == '/':               
            self.send_response(200)                                                            
            self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=frame')                              
            self.end_headers()
            try:                
                while True:                                
                    frame = frame_queue.get()
                    self.wfile.write(b'--frame\r\n')                        
                    self.send_header('Content-Type', 'image/jpeg')                                                     
                    self.send_header('Content-Length', str(len(frame)))                                                
                    self.end_headers()                                                         
                    self.wfile.write(frame)
            except (BrokenPipeError, ConnectionResetError):                                                            
                pass                                       
        else:                                              
            self.send_error(404)                           

def start_server():                                        
    with socketserver.ThreadingTCPServer(("", PORT), MJPEGHandler) as httpd:                                           
        httpd.serve_forever()                              

server_thread = threading.Thread(target=start_server, daemon=True)                                                     
server_thread.start()                                      

def cleanup(signum, frame):                                
    libcamera_proc.terminate()                             
    libcamera_proc.wait()                                  
    sys.exit(0)                                            

signal.signal(signal.SIGINT, cleanup)                      
signal.signal(signal.SIGTERM, cleanup)                     

signal.pause()  