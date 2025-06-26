# ALPR Lite

This branch is just the camera module from the repository. This saves time and energy when cloning and installing.

## Setting up the Camera

This tutorial uses a Raspberry Pi 5 and a PiCam V3. You can probably use the included script to run almost any camera with a little tweaking, at least on the Raspberry Pi.

To get the camera running, clone this repo's `lite` branch onto a Raspberry Pi (you may need to run `sudo apt install git` first):

```sh
git clone --branch lite --depth=1 https://github.com/NET-BYU/alpr.git
```

then, just navigate to the `camera` directory and run the included `install.sh` script.

```sh
cd alpr/camera
chmod +x install.sh
./install.sh
```

Your Raspberry Pi now has a service file named `camera.service` running `ipcam.py` and streaming over HTTP on `0.0.0.0` (your local IP address). Anytime you turn on the Raspberry Pi, this service will start automatically. Test this by going to `http://<IP-ADDR>:8080`.

You can configure the video stream by editing `ipcam.py` and it's global variables:

```py
# Output Configuration         
WIDTH = 2560   
HEIGHT = 1440
FRAMERATE = 30
PORT = 8080
```
