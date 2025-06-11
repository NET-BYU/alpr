# ALPR

To use this, you first have to have an active [OpenALPR](https://cloud.openalpr.com/) account. Once you have a subscription, you only need two things: an IP camera (a camera that broadcasts it's feed over IP) and a Windows machine on the same network.

## Setting up the Camera

This tutorial uses a Raspberry Pi 5 and a PiCam V3. You can probably use the included script to run almost any camera with a little tweaking, at least on the Raspberry Pi.

To get the camera running, clone this repo's `lite` branch onto a Raspberry Pi:

```sh
git clone git@github.com:NET-BYU/alpr.git
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

## Setting up the Rekor Server (Windows)

Once you have at least one camera up and running, set up your Rekor Scout Agent on your Windows machine. Go to Rekor's page (or [this link](https://deb.openalpr.com/windows-agent/openalpr-agent-latest.exe)) and download the Rekor Agent. Run the installer. Along the way to opening the agent, it will ask you to sign in and verify your account. Once you have installed and signed it, it should land on this program:

[program](media/program_empty.png)

The program is very simple to run. First, add the camera you set up in the previous step. Click Add camera, select `IP Camera (Manual)` as the type, and then enter `http://<IP-ADDR>:<PORT>`, where `<IP-ADDR>` is the configured IP address of the camera, and `<PORT>` is the whatever port you setup (default is 8080)

[program](media/program_camsetup.png)

Then, click `test` to make sure your camera feed is working. You can skip the credentials it asks for (unless you have a custom camera setup).

[program](media/program_camtest.png)

In this example, I am actually setting it up to view our 3D Printer's HTTP camera. Once you can see the feed, click `Save Camera`, name the camera, and it will show up on your dashboard.

That's it! Any license plates it sees will automatically be uploaded to your server on OpenALPR's website. You can view the metrics there.

## Running your own local dashboard

This repository also contains an `alpr_integrated_server.py` which runs a local flask dashboard that mimics the OpenALPR dashboard, but runs locally without internet. To run it, first start the flask server, then point the Rekor Scout Agent to the server instead of the OpenALPR server.

To use the server, your Windows computer must have python installed (I used python 3.10, but any modern Python should work). Once you have that installed, run

```sh
python3.10 -m venv .venv
.\.venv\Scripts\activate
python3.10 -m pip install flask
```

to start the server, simply run

```sh
python3.10 .\alpr_integrated_server.py
```

You now have an openALPR mimic server that stores all its own local data. the server generates three different files:

- `alpr_raw_data.jsonl`: contains all the JSON reported by the server, including heartbeat messages.
- `alpr_parsed_data.jsonl`: contains just the useful license plate data. Configurable if you edit the integrated server script.
- `event.log`: a condensed event log of what the server reports.

It also stores all the images received in the `plates` folder. The server webpage looks like this:

[webpage](media/webpage.png)

_the error fetching data was because I wasn't running the server when I took the picture._

To connect Rekor Scout to your local webserver:

1. run your server.
2. Open Rekor Scount:

    ![program](media/program_empty.png)

3. Click on the top left, **Configure >> Data Destinations**:

    ![program](media/program_datadest.png)

4. Click on Other HTTP Server:

    ![program](media/program_datadest_popup.png)

5. Enter `http://localhost:5000/alpr` as the server URL:

    ![program](media/program_urldest_popup.png)

