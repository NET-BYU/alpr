#!/bin/bash

# Get the current directory where this script is located
CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

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
        echo -e "${RED}Error: ${python_file} not found in ${CURRENT_DIR}${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Creating service for ${python_file}...${NC}"
    
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
    
    echo -e "${GREEN}Service updated to use ${python_file}${NC}"
}

# Function to do full installation
full_install() {
    local python_file="$1"
    
    echo -e "${GREEN}Running full installation...${NC}"
    
    # Update system packages
    echo -e "${GREEN}Updating system packages...${NC}"
    sudo apt update
    echo -e "${GREEN}Installing required packages...${NC}"
    sudo apt install libcamera-apps ffmpeg python3 -y
    
    # Create/update service
    create_service "$python_file"
    
    # Show status
    echo -e "${GREEN}Camera service installed and started!${NC}"
    echo -e "${GREEN}Current directory: ${CURRENT_DIR}${NC}"
    echo -e "${GREEN}Service status:${NC}"
    sudo systemctl status camera.service --no-pager
}

# Main script logic
case "$1" in
    "change")
        if [ -z "$2" ]; then
            echo -e "${RED}Usage: $0 change <filename>${NC}"
            echo -e "${RED}Example: $0 change webcam.py${NC}"
            exit 1
        fi
        python_file=$(get_filename "$2")
        create_service "$python_file"
        echo -e "${GREEN}Service status:${NC}"
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

echo -e "${RED}Installation complete! If you changed the service file, please reboot with:${NC}"
echo -e "${RED}sudo reboot now${NC}"