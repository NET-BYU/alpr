# MJPEG Image Stream Server

A Python-based MJPEG (Motion JPEG) HTTP server that streams images from a folder as a continuous video feed. Use this to simulate an IP camera for testing OpenALPR RekorScout with your own license plate images instead of a physical camera.

## What This Does

This image streamer acts as a **virtual IP camera** that feeds images to Rekor Scout for ALPR processing:

```
📁 Your Images → 📹 Image Streamer → 🤖 Rekor Scout → 🖥️ Local Dashboard
```

Perfect for:
- Testing ALPR setups without a physical camera
- Replaying captured license plate images
- Development and debugging
- Training and demonstrations

## Features

- 📹 **MJPEG Stream** - Standard Motion JPEG over HTTP format
- 🎥 **OpenALPR Compatible** - Works with RekorScout and other ALPR software
- 📺 **1080p Output** - Streams at 1920x1080 resolution
- ⏱️ **Configurable Timing** - Set display duration per image
- 🔄 **Loop Control** - Continuous loop or stop at end
- 🖼️ **Multi-Format Support** - Accepts PNG and JPG/JPEG files
- 🎯 **Smart Resizing** - Maintains aspect ratio with letterboxing
- 📊 **Natural Sorting** - Images sorted numerically (1, 2, 3...10)
- 🖤 **Fallback Image** - Default image when no content available

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs: `opencv-python`, `Pillow`, and `numpy`

### 2. Prepare Images

Create an `images` folder and add your images:

```bash
mkdir images
```

Add PNG or JPG images to this folder. Images will be streamed in natural numerical order.

**Optional:** Add a `default.jpg` file in the same directory as the script to serve as a fallback image when no images are available.

### 3. Download Sample Images (Optional)

Use the included sample downloader to quickly get test images:

```bash
# Download 10 sample images
python download_samples.py --download 10

# Download 50 images
python download_samples.py --download 50

# Clear all sample images
python download_samples.py --clear
```

## Usage

### Start the Stream Server

**Basic usage** (2 seconds per image, looping):
```bash
python http_image_stream.py
```

**Custom duration:**
```bash
python http_image_stream.py --duration 5.0
```

**No looping** (stops at end, shows default image):
```bash
python http_image_stream.py --duration 3.0 --no-loop
```

**Custom port:**
```bash
python http_image_stream.py --port 8080
```

**Custom images folder:**
```bash
python http_image_stream.py --images ./my_images --duration 2.5
```

### Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--images FOLDER` | Path to folder containing images | `images` |
| `--duration SECONDS` | Time to display each image | `2.0` |
| `--loop` | Loop through images continuously | Enabled |
| `--no-loop` | Stop at end and show default image | Disabled |
| `--default PATH` | Path to fallback image | `default.jpg` |
| `--port PORT` | HTTP server port | `8000` |
| `--host HOST` | HTTP server host | `0.0.0.0` |

## Accessing the Stream

### Web Browser

Open in any browser:
```
http://localhost:8000
```

Or from another device on your network:
```
http://<your-ip-address>:8000
```

## Connecting to OpenALPR RekorScout

Follow these steps to use the image streamer as a camera source for Rekor Scout ALPR processing:

### Step 1: Start the Image Stream Server

```bash
python http_image_stream.py --duration 3.0 --loop
```

The server will start on `http://localhost:8000`. Keep this terminal window open.

### Step 2: Add Camera in Rekor Scout

1. **Open Rekor Scout** on your Windows machine
2. **Click "Add Camera"** in the main interface
3. **Select camera type**: Choose `IP Camera (Manual)` from the dropdown
4. **Enter camera URL**: Use one of these URLs:
   - **Primary:** `http://localhost:8000/video.mjpeg`
   - **Alternative:** `http://localhost:8000/stream`
   - **Alternative:** `http://localhost:8000/mjpeg`

   > **Note:** Replace `localhost` with your computer's IP address if Rekor Scout is running on a different machine

5. **Click "Test"** to verify the stream is working
6. **Click "Save Camera"** and give it a name (e.g., "Image Stream Test")
7. **Start services** when prompted (click "Yes")

### Step 3: Configure Data Destination (Optional)

If you're using the local ALPR dashboard server, configure Rekor Scout to send detections there:

1. In Rekor Scout, go to **Configure → Data Destinations**
2. Select **"Other HTTP Server"**
3. Enter URL: `http://localhost:5000/alpr`
4. Click "Save"

Now your complete pipeline is:
```
📁 Images → 📹 Image Streamer → 🤖 Rekor Scout → 🖥️ Local Dashboard
```

See the main project [README](../README.md) for full instructions on setting up the local dashboard server.

### Stream Endpoints

| Endpoint | Description |
|----------|-------------|
| `/` | Web viewer with stream information |
| `/video.mjpeg` | MJPEG stream (recommended for ALPR) |
| `/stream` | MJPEG stream (alternative URL) |
| `/mjpeg` | MJPEG stream (alternative URL) |
| `/video.mjpg` | MJPEG stream (alternative URL) |

## Technical Details

### Image Processing

- Images are resized to fit within 1080p (1920x1080) while maintaining aspect ratio
- Smaller images are centered on a black background (letterboxing)
- Larger images are scaled down proportionally
- JPEG quality optimized at 55% for efficient streaming and ALPR compatibility

### Stream Format

- **Format:** MJPEG (Motion JPEG over HTTP)
- **Resolution:** 1920x1080 (1080p)
- **Update Rate:** ~30 FPS
- **Boundary:** `--jpgboundary`
- **MIME Type:** `multipart/x-mixed-replace`

### Supported Image Formats

- `.jpg` / `.jpeg` (case-insensitive)
- `.png` (case-insensitive)

### Fallback Behavior

The `default.jpg` is displayed when:
- No images exist in the images folder
- Using `--no-loop` and all images have been shown
- An error occurs loading an image

If `default.jpg` is not found, a black frame is displayed.

## Example Workflows

### Testing with Sample Images

```bash
# Download test images
python download_samples.py --download 20

# Start streaming with 3-second intervals
python http_image_stream.py --duration 3.0

# Access at http://localhost:8000
```

### Production Use with RekorScout

```bash
# Prepare your license plate images in the images folder
# Start the server
python http_image_stream.py --duration 2.0 --loop

# In RekorScout, add camera:
# URL: http://<server-ip>:8000/video.mjpeg
```

### One-Shot Playback

```bash
# Play through images once, then stop
python http_image_stream.py --duration 4.0 --no-loop
```

## Troubleshooting

**Stream not connecting to RekorScout:**
- Ensure the server is accessible from RekorScout's machine
- Try the different endpoint URLs (`/video.mjpeg`, `/stream`, `/mjpeg`)
- Check firewall settings on port 8000
- Verify the server is running with `--host 0.0.0.0` for network access

**Images not in correct order:**
- The server uses natural sorting - ensure filenames have consistent numbering
- Examples: `image_1.jpg`, `image_2.jpg`, `image_10.jpg` (not `image1.jpg`, `image02.jpg`)

**Stream quality issues:**
- JPEG quality is set to 55% for optimal ALPR performance and bandwidth
- Modify `IMWRITE_JPEG_QUALITY` in code if higher quality is needed

## Stopping the Server

Press `Ctrl+C` to gracefully stop the server.
