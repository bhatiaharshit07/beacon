import logging
from logging.handlers import RotatingFileHandler
import requests
import json
import time
import hashlib
import uuid
import os

API_ENDPOINT = "https://beacon-backend.app-assertai.com"
# Get the current user's home directory
user_home = os.path.expanduser("~")
BEACON_DIR = os.path.join(user_home, "ALPHA", "BEACON")
DELAYED_FILE = os.path.join(BEACON_DIR, "delayed.json")
LOG_FILE = os.path.join(BEACON_DIR, "beacon.log")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
handler = RotatingFileHandler(LOG_FILE, maxBytes=3*1024*1024, backupCount=3)
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logging.getLogger('').addHandler(handler)

# Display message for user to note down hash for DB references
logging.info("Please note down the following hash for database references: ")

def hit_api(slots, live, mac_hash):
    payload = {"slots": slots, "live": live, "hash": mac_hash}
    try:
        response = requests.post(API_ENDPOINT, json=payload)
        if response.status_code == 200:
            logging.info("API request successful")
            return True
        else:
            logging.error(f"API request failed with status code: {response.status_code}")
            return False
    except Exception as e:
        logging.error(f"Failed to make API request: {e}")
        return False

def save_to_file(slots):
    existing_slots = load_from_file()
    existing_slots.extend(slots)
    with open(DELAYED_FILE, "w") as f:
        json.dump({"slots": existing_slots, "live": False}, f)
    logging.info(f"Slots saved to {DELAYED_FILE}")

def load_from_file():
    try:
        with open(DELAYED_FILE, "r") as f:
            data = json.load(f)
        return data.get("slots", [])
    except FileNotFoundError:
        return []

def device_status(start_time):
    current_time = int(time.time())
    return current_time - start_time > 60  # 600 seconds = 10 minutes

def hash_mac_address(mac_address):
    return hashlib.md5(mac_address.encode()).hexdigest()

def get_mac_address():
    mac = uuid.UUID(int=uuid.getnode()).hex[-12:]
    return ":".join([mac[e:e+2] for e in range(0, 11, 2)])

def main():
    start_time = int(time.time())  # Initialize start time
    
    mac_address = get_mac_address()  # Automatically read the MAC address
    mac_hash = hash_mac_address(mac_address)
    
    # Log the hashed MAC address
    logging.info(f"Hashed MAC Address: {mac_hash}")
    print(f"Hashed MAC Address: {mac_hash}")
    
    while True:
        current_minute = time.localtime().tm_min
        if current_minute % 2 == 0:
            # Check device uptime
            if device_status(start_time):  
                logging.info("Device is online for at least 10 mins in the last 15 mins")
                current_time = int(time.time())  # Current timestamp
                slots = [current_time]  # Example slot, replace with actual slot data
                if hit_api(slots, True, mac_hash):
                    logging.info("API request sent successfully")
                else:
                    logging.error("Failed to send API request. Saving slots to file...")
                    save_to_file(slots)
        else:
            recent_slots = load_from_file()
            if recent_slots:
                logging.info("Resending delayed slots")
                if hit_api(recent_slots, False, mac_hash):
                    logging.info("API request for delayed slots sent successfully. Clearing delayed file...")
                    open(DELAYED_FILE, 'w').close()  # Clear the delayed file
                else:
                    logging.error("Failed to resend delayed slots. Retrying in 1 minute...")
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    main()
