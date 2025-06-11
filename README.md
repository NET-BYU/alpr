# ALPR

To use this, you first have to have an active [OpenALPR](https://cloud.openalpr.com/) account.

## Usage

Once you have subscribed to OA's Rekor Scout, follow their instructions to download the client on Windows.

To connect the webserver to Rekor Scout:

Open Rekor Scount:

![program](media/progam.png)

Click on the top left, **Configure >> Data Destinations**:

![program](media/data_dest.png)

Click on Other HTTP Server:

![program](media/server_dialogue.png)

Enter `http://localhost:5000/alpr` as the server URL:

![program](media/url_dest.png)

