#!/bin/bash

# Automatically retrieve username
USER=$(whoami)

# Warehouse ID provided as a command-line argument
WAREHOUSE_ID="$1"

# Step 1: Ensure directory /home/{user}/ALPHA/BEACON exists, create if not
DIR="/home/$USER/ALPHA/BEACON"
if [ ! -d "$DIR" ]; then
    if sudo mkdir -p "$DIR" && sudo chown -R "$USER:$USER" "$DIR"; then
        echo "Directory created: $DIR"
    else
        echo "Error creating directory: $DIR"
        exit 1
    fi
fi

# Step 2: Create warehouse details JSON
if echo "{\"warehouseID\": \"$WAREHOUSE_ID\"}" | sudo tee "$DIR/warehouse_details.json" > /dev/null; then
    echo "Warehouse details JSON created: $DIR/warehouse_details.json"
else
    echo "Error creating warehouse details JSON"
    exit 1
fi

# Step 3: Retrieve Python script from API and save to main.py
MAIN_PY_URL="https://raw.githubusercontent.com/bhatiaharshit07/beacon/main/main.py"
if sudo curl -o "$DIR/main.py" "$MAIN_PY_URL" && sudo chmod 755 "$DIR/main.py" && sudo chown -R "$USER:$USER" "$DIR"; then
    echo "Python script downloaded and saved: $DIR/main.py"
else
    echo "Error downloading or saving Python script"
    exit 1
fi

# Step 4: Create service file for main.py
SERVICE_FILE="/etc/systemd/system/beacon.service"
SERVICE_CONTENT="[Unit]
Description=Beacon Service
After=network.target

[Service]
User=$USER
Group=$USER
Type=simple
ExecStart=/usr/bin/python3 $DIR/main.py
Restart=always

[Install]
WantedBy=multi-user.target"

if echo "$SERVICE_CONTENT" | sudo tee "$SERVICE_FILE" > /dev/null; then
    echo "Service file created: $SERVICE_FILE"
else
    echo "Error creating service file"
    exit 1
fi

# Step 5: Enable and start the service
if sudo systemctl daemon-reload && sudo systemctl enable beacon.service && sudo systemctl start beacon.service; then
    echo "Service enabled and started: beacon.service"
else
    echo "Error enabling or starting service"
    exit 1
fi

# Step 6: Update permissions
if sudo chmod -R 777 "$DIR"; then
    echo "Permissions updated to 777: $DIR"
else
    echo "Error updating permissions"
    exit 1
fi

# Validation
if [ -f "$DIR/main.py" ] && [ -f "$SERVICE_FILE" ]; then
    echo "Setup complete (1/2)."
else
    echo "Setup failed."
    rollback
fi

if [ -f "$DIR/device_details.json" ]; then
    echo "Device details setup complete (2/2)."
else
    echo "Device details not found"
    rollback
fi

echo "Setup completed successfully."
exit 0

# Rollback function
rollback() {
    echo "Rolling back changes..."

    # Stop and disable service
    sudo systemctl stop beacon.service
    sudo systemctl disable beacon.service

    # Remove service file
    sudo rm -f "$SERVICE_FILE"

    # Remove Python script
    sudo rm -f "$DIR/main.py"

    # Remove warehouse details JSON
    sudo rm -f "$DIR/warehouse_details.json"

    # Remove directory if empty
    if [ -z "$(ls -A "$DIR")" ]; then
        sudo rmdir "$DIR"
    fi

    echo "Rollback completed."
    exit 1
}
