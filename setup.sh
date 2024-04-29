#!/bin/bash

# Define user's home directory
USER_HOME=/home/$(logname)

# Create folder ALPHA if it doesn't exist
ALPHA_DIR=$USER_HOME/ALPHA
if [ ! -d "$ALPHA_DIR" ]; then
    mkdir -p "$ALPHA_DIR"
fi

# Create folder beacon if it doesn't exist
BEACON_DIR=$ALPHA_DIR/beacon
if [ ! -d "$BEACON_DIR" ]; then
    mkdir -p "$BEACON_DIR"
fi

# Fetch the content from the URL and create the Python file
TOKEN=$1
DEVICE_ID=$2
curl -o $BEACON_DIR/main.py "https://beacon-backend.app-assertai.com/get_codes?token=$TOKEN&device_id=$DEVICE_ID"

# Create the service file for autostart
SERVICE_FILE=/etc/systemd/system/python_script.service
echo "
[Unit]
Description=Your Python Script
After=network.target

[Service]
User=$(logname)
WorkingDirectory=$BEACON_DIR
ExecStart=/usr/bin/python3 $BEACON_DIR/main.py
Restart=always

[Install]
WantedBy=multi-user.target
" > $SERVICE_FILE

# Set permissions for the Python file and service file
chmod +x $BEACON_DIR/main.py
chmod 644 $SERVICE_FILE

# Enable and start the service
systemctl daemon-reload
systemctl enable python_script.service
systemctl start python_script.service

echo "Setup completed successfully."
