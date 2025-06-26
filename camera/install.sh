#!/bin/bash

# Get the current directory where this script is located
CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Function to map keywords to filenames
get_filename() {
    case "$1" in
        "webcam")
            echo "webcam.py"
            ;;
        "ipcam")
            echo "ipcam.py"
            ;;
        "imagecam")
            echo "imagecam.py"
            ;;
        *)
            echo "$1"
            ;;
    esac
}

# Function to create/update service file
create_service() {
    local python_file="$1"
    
    # Check if file exists
    if [ ! -f "${CURRENT_DIR}/${python_file}" ]; then
        echo "Error: ${python_file} not found in ${CURRENT_DIR}"
        exit 1
    fi
    
    echo "Creating service for ${python_file}..."
    
    # Create the service file with the correct path
    cat << EOF | sudo tee /etc/systemd/system/camera.service
[Unit]
Description=start HTTP camera
After=network.target

[Service]
ExecStart=/usr/bin/python3 ${CURRENT_DIR}/${python_file}
WorkingDirectory=${CURRENT_DIR}
Restart=always
User=${USER}

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd and restart service
    sudo systemctl daemon-reload
    sudo systemctl enable camera.service
    sudo systemctl restart camera.service
    
    echo "Service updated to use ${python_file}"
}

# Function to do full installation
full_install() {
    local python_file="$1"
    
    echo "Running full installation..."
    
    # Update system packages
    sudo apt update
    sudo apt install libcamera-apps ffmpeg python3 -y
    
    # Create/update service
    create_service "$python_file"
    
    # Show status
    echo "Camera service installed and started!"
    echo "Current directory: ${CURRENT_DIR}"
    echo "Service status:"
    sudo systemctl status camera.service --no-pager
}

# Main script logic
case "$1" in
    "change")
        if [ -z "$2" ]; then
            echo "Usage: $0 change <filename>"
            echo "Example: $0 change webcam.py"
            exit 1
        fi
        python_file=$(get_filename "$2")
        create_service "$python_file"
        echo "Service status:"
        sudo systemctl status camera.service --no-pager
        ;;
    "")
        # No arguments - default to ipcam.py
        full_install "ipcam.py"
        ;;
    *)
        # Single keyword argument
        python_file=$(get_filename "$1")
        full_install "$python_file"
        ;;
esac

echo "Installation complete! If you changed the service file, please reboot with:"
echo "sudo reboot now"