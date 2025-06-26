# ALPR

To use this, you first have to have an active [OpenALPR](https://cloud.openalpr.com/) account. Once you have a subscription, you only need two things: an IP camera (a camera that broadcasts it's feed over IP) and a Windows machine on the same network.

**THIS BRANCH IS ONLY FOR SETTING UP IP CAMERAS** For the local-hosted server and OpenALPR instructions, go to the main branch.

## Setting up Cameras

Half of the project is getting a video source to stream as an RTSP or HTTP feed. Thus far, I have had better experiences with HTTP feeds.Currently, support exists for three types of cameras:
 - USB webcams
 - RPi cameras
 - a set of images in a folder

To get a camera running, clone this repo's `lite` branch onto a device (usually just a Raspberry Pi; Pi 5, 4 or even Z2W works depending on video requirements):

```sh
git clone --branch lite --depth=1 https://github.com/NET-BYU/alpr.git
```

then, just navigate to the `camera` directory and run the included `install.sh` script.

```sh
cd alpr/camera
chmod +x install.sh
./install.sh
```

`install.sh` can be run in three ways:
 - by itself (`install.sh`), which runs a full install and defaults setting up an Rpi camera
 - with one argument (`install.sh <type>`), which runs a full install where `<type>` is either `ipcam`, `webcam`, or `imagecam`.
   - `ipcam` is an Rpi camera
   - `webcam` is any* USB webcam
   - `imagecam` assumes there is a folder of images titled `img` in the camera directory
- with two arguments (`install.sh change <type>`), which rewrites the service file using the defined type, then asks you to reboot.

Once you run the install script, you end up with a service file named `camera.service` running `<type>.py` and streaming over HTTP on `0.0.0.0` (your local IP address). Anytime you turn on the Raspberry Pi, this service will start automatically. Test this by going to `http://<IP-ADDR>:8080`.

For `imagecam`, once it runs through all the images, it stops. You can restart the device or the service file to get it to start over.

You can configure the video streams by editing `<type>.py` and it's global variables:

```py
# Example: ipcam.py configuration         
WIDTH = 1920   
HEIGHT = 1080
FRAMERATE = 30
PORT = 8080
```

_Note: OpenALPR prefers a 1920x1080 stream, so going above that is not recommended according to them. Your max framerate is camera-dependant._
