import sys
import getpass
import os
import json
import requests
import time
import cv2

class Beacon:
    def __init__(self):
        self.beaconFolderLocation = self.get_beacon_folder_location()
        self.warehouseID = self.get_warehouse_id()

    def get_current_user(self):
        return getpass.getuser()

    def check_platform(self):
        if sys.platform.startswith('win'):
            return "Windows"
        elif sys.platform.startswith('linux'):
            return "Linux"
        else:
            return "Unknown"

    def get_beacon_folder_location(self):
        platform = self.check_platform()
        if platform == "Windows":
            return os.path.join("C:"+os.sep, "Users", self.get_current_user(), "ALPHA", "BEACON")
        elif platform == "Linux":
            return os.path.join(os.sep+"home", self.get_current_user(), "ALPHA", "BEACON")
        
    def get_warehouse_id(self):
        warehouseDetailsFile = os.path.join(self.beaconFolderLocation, "warehouse_details.json")
        if os.path.isfile(warehouseDetailsFile):
            with open(warehouseDetailsFile, 'r') as file:
                warehouseDetails = json.load(file)
                warehouseID = warehouseDetails.get('warehouseID', 0)
                return warehouseID
        else:
            print("warehouse details file not found")
 
    def transform_device_data(self, data):
        deviceData = {'deviceData':{}}
        for cameraData in data['deviceData']:
            if len(cameraData['device_mac']) == 0:
                deviceData['deviceData'][cameraData['_id']] = f"rtsp://admin:Assert@123@{cameraData['device_ip']}:554/Streaming/Channels/{cameraData['device_channel']}02"
            else:
                deviceData['deviceData'][cameraData['_id']] = f"rtsp://admin:Assert@123@{cameraData['device_ip']}:554/Streaming/Channels/{cameraData['device_mac']}02"
        print(deviceData)
        return deviceData

    
    def update_device_details(self):
        api_url = f"https://backend.app-assertai.com/api/v1/get-camera-by-wh?warehouseID={self.warehouseID}"
        device_details_file = os.path.join(self.beaconFolderLocation, "device_details.json")
        response = requests.get(api_url)
        if response.status_code == 200:
            new_device_data = response.json().get('data', {})
            final_device_data = self.transform_device_data(new_device_data)
            final_device_data['timestamp'] = int(time.time())
            with open(device_details_file, 'w') as file:
                json.dump(final_device_data, file, indent=4)
                print("Device details updated successfully.")
        else:
            print("Failed to fetch device details from API.")
        return response.text
    
    def check_and_update_device_details(self):
        device_details_file = os.path.join(self.beaconFolderLocation, "device_details.json")
        if os.path.isfile(device_details_file):
            with open(device_details_file, 'r') as file:
                device_details = json.load(file)
            timestamp = device_details.get('timestamp', 0)
            current_time = int(time.time())
            if current_time - timestamp > 86400:  # Check if more than 1 day has passed (86400 seconds)
                self.update_device_details()
            else:
                print("Device details were updated less than 1 day ago.")
        else:
            self.update_device_details()

    def check_cam_status(self, rtsp, timeout=5):
        startTime = int(time.time())
        cap = cv2.VideoCapture(rtsp)
        print(cap.isOpened(), rtsp)
        while True:
            if cap.isOpened():
                return True
            if time.time() - startTime > timeout or not cap.isOpened():
                return False
    
    def get_cam_status(self):
        print("Checking all the available cameras")
        device_details_file = os.path.join(self.beaconFolderLocation, "device_details.json")
        if not os.path.isfile(device_details_file):
            self.check_and_update_device_details()
        cameraSlot = {}
        with open(device_details_file, 'r') as file:
                device_details = json.load(file)
        currentTime = int(time.time())
        print(currentTime)
        for cameraData in device_details['deviceData']:
            if self.check_cam_status(device_details['deviceData'][cameraData]):
                print(cameraData)
                cameraSlot[cameraData] = [currentTime]
        
        return cameraSlot

    def get_device_status(self, startTime):
        current_time = int(time.time())
        return current_time - startTime > 6  # 600 seconds = 10 minutes
    
    def save_slots_to_delayed_file(self, timeSlots):
        delayedFile = os.path.join(self.beaconFolderLocation, "delayed.json")
        if os.path.isfile(delayedFile):
            print("Delayed file found")
        else:
            with open(delayedFile, "w") as json_file:
                json.dump({}, json_file)
        with open(delayedFile, 'r') as file:
                device_details = json.load(file)
        final_slots = {}
        if len(device_details) == 0:
            final_slots = timeSlots
        else:
            print(f"Found Previous slots in delayed file: {device_details}")
            for id in timeSlots:
                if id in device_details:
                    device_details[id].append(timeSlots[id][0]) 
                else:
                    device_details[id] = timeSlots[id]
            final_slots = device_details
        with open(delayedFile, "w") as json_file:
            print(f"Pushing final slot to delayed file {final_slots}")
            json.dump(final_slots, json_file)

    def push_slots_to_api(self, slots, live):
        url = "http://34.131.49.157:8000/process_data"
        payload = json.dumps({
        "TIME_SLOTS": slots,
        "LIVE": live,
        "WAREHOUSE_ID": self.warehouseID,
        "PROJECT_ID": "66065de7f49aa74f9a63dd39"
        })
        print(payload)
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json'
        }
        try:
            response = requests.request("POST", url, headers=headers, data=payload)
            if response.status_code == 200:
                print("API request successful")
                return True
            else:
                print(f"API request failed with status code: {response.status_code}")
                return False
        except Exception as e:
            print(f"Failed to make API request: {e}")
            return False
    
    def check_and_push_delayed_slots(self):
        delayedFile = os.path.join(self.beaconFolderLocation, "delayed.json")
        if not os.path.isfile(delayedFile):
            with open(delayedFile, "w") as json_file:
                json.dump({}, json_file)
        try:
            with open(delayedFile, 'r') as file:
                slots = json.load(file)
                if len(slots) > 0:
                    if self.push_slots_to_api(slots, live=False):
                        print("Clearing all the delayed slots and successful push")
                        with open(delayedFile, "w") as json_file:
                            json.dump({}, json_file)
                    else:
                        print("Unable to push delayed slots")
                else:
                    print("No delayed slots found")
        except json.JSONDecodeError as jde:
            print(f"Error decoding JSON from file '{delayedFile}': {jde}")

def main():
    beacon = Beacon()
    startTime = int(time.time())
    lastUpdateTime = int(time.time())
    timeSlots = {}
    while True:
        current_minute = time.localtime().tm_min

        if int(time.time()) - lastUpdateTime > 60*30: #60*60:
            beacon.check_and_update_device_details()
            lastUpdateTime = int(time.time())
        
        if current_minute % 2 == 0: # Every 5 mins
            beacon.check_and_push_delayed_slots() 

        if current_minute % 2 == 0: # Every 15 mins
            if beacon.get_device_status(startTime):
                timeSlots[beacon.warehouseID] = [int(time.time())]
                print(f" {beacon.warehouseID} device is online for more than 10 mins in last 15 mins")
            cameraSlots = beacon.get_cam_status()
            timeSlots.update(cameraSlots)
            if len(timeSlots) > 0:
                if beacon.push_slots_to_api(timeSlots, live=True):
                    print("Live Slots Pushed")
                else:
                    print(f"Unable to push live slots: {timeSlots}")
                    beacon.save_slots_to_delayed_file(timeSlots)
            else:
                 print("No slot found to push")
    
if __name__=="__main__":
    main()
