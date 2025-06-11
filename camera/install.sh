#!/bin/bash

# Get the current directory where this script is located
CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Update system packages
sudo apt update
sudo apt install libcamera-apps ffmpeg python3

# Create the service file with the correct path
cat << EOF | sudo tee /etc/systemd/system/camera.service
[Unit]
Description=start HTTP camera
After=network.target

[Service]
ExecStart=/usr/bin/python3 ${CURRENT_DIR}/ipcam.py
WorkingDirectory=${CURRENT_DIR}
Restart=always
User=\${USER}

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd, enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable camera.service
sudo systemctl start camera.service

# Show status
echo "Camera service installed and started!"
echo "Current directory: ${CURRENT_DIR}"
echo "Service status:"
sudo systemctl status camera.service --no-pager