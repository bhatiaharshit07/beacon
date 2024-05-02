#!/bin/bash

# Automatically retrieve username
USER=$(whoami)

# Warehouse ID provided as a command-line argument
WAREHOUSE_ID="$1"

# Step 1: Ensure directory /home/{user}/ALPHA/BEACON exists, create if not
DIR="/home/$USER/ALPHA/BEACON"
if [ ! -d "$DIR" ]; then
    sudo mkdir -p "$DIR"
    sudo chown -R "$USER:$USER" "$DIR"
fi

# Step 2: Save warehouse ID to JSON file
echo "{\"warehouseID\": \"$WAREHOUSE_ID\"}" | sudo tee "$DIR/warehouse_details.json" > /dev/null

# Step 3: Retrieve Python script from API and save to main.py
MAIN_PY_URL="https://raw.githubusercontent.com/bhatiaharshit07/beacon/main/main.py"
sudo curl -o "$DIR/main.py" "$MAIN_PY_URL"

# Step 4: Create service file for main.py
SERVICE_FILE="/etc/systemd/system/beacon.service"
echo "[Unit]
Description=Beacon Service
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 $DIR/main.py
Restart=always

[Install]
WantedBy=multi-user.target" | sudo tee "$SERVICE_FILE" > /dev/null

# Step 5: Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable beacon.service
sudo systemctl start beacon.service

# Step 6: Validation
if [ -f "$DIR/warehouse_details.json" ] && [ -f "$DIR/main.py" ] && [ -f "$SERVICE_FILE" ]; then
    echo "Setup complete."
else
    echo "Setup failed."
fi