from datetime import datetime, timezone
import os
import re
import sys
import json
#import matplotlib.pyplot as plt
import requests
import json
import pandas as pd
import openpyxl
from openpyxl.utils.dataframe import dataframe_to_rows


json_file = input("Enter criteria json file name (default criteria.json): ")
if json_file == "":
    json_file = "criteria.json"
# Open the JSON file
with open(json_file, 'r') as file:
    criteria = json.load(file)

# Base URL for the API
API_BASE = "https://api.tagntrac.io"

# Configuration dictionary with specific settings for different status codes
chk_cfg = {
    "0": 15, 
    "1": 60, 
    "35": "at%setacfg=radiom.config.preferred_rat_list,'CATM'", 
    "36": "  OK  "
}

# Parameter dictionary for configuration 0
cfg0_params = {
    "0": 15, 
    "1": 60, 
    "9": -124, 
    "21": 1
}

# Placeholder variables for user credentials and filename
fname = ""
id = "username" 
pwd = "password" 
def prompt():
    """Prompt user for username, password, and file name for device id list."""
    id = input("Enter username: ")
    pwd = input("Enter password: ")
    fname = input("Enter IMEI list file (default imei.txt): ")
    return id, pwd, fname


def login(email, password):
    """Attempt to log in a user with given email and password."""
    login_response = requests.post(f"{API_BASE}/login?clientId=Tbocs0cjhrac",
                             data = json.dumps({"emailId" : email, "userSecret" : password}),
                             headers={"Content-Type" : "application/json", "Origin" : "DOC.API"})
    try:
        if login_response.json()["status"] == "SUCCESS":
            print("Login successful as ", email)
            return (login_response.json()["token"], login_response.json()['clientApiKey']['clientId'])
    except Exception as e:
        print(f"Exception: {str(e)}")
    print(f"Login failed: {login_response.text}")
    return (None, None)

# Capture user input
id, pwd, fname = prompt()
if fname == "":
    fname = "imei.txt"

# Perform login and capture token and API key
token, xapikey = login(id, pwd)

# Common headers used in GET requests
common_headers = {
    "Authorization": token,
    "Origin": "https://app.tagntrac.io",
    "x-api-key": xapikey
}

# Common headers used in POST requests
common_headers_post = {
    "Authorization": token,
    "Origin": "https://app.tagntrac.io",
    "Content-Type": "application/json"
}

def get_device_shadow_reported(device_id):
    """Retrieve and parse device shadow state."""
    response = requests.get(f"{API_BASE}/device/{device_id}/shadow", headers=common_headers)
    shdw = response.json()
    reported = None
    if shdw['status'] == "SUCCESS":
        if 'reported' in shdw['shadow']['state']:
            reported = shdw['shadow']['state']['reported']
    return reported

def get_health_last_reported(device_id):
    """Retrieve and parse device health state."""
    response = requests.get(f"{API_BASE}/device/{device_id}/health", headers=common_headers)
    health = response.json()
    reported_time = None
    if health['status'] == "SUCCESS":
        reported_time = health['device']['health']['lastReportedAt']
        if reported_time is None:
            reported_time = "N/A"
    else:
        reported_time = "N/A"
    return reported_time

def sensor_interval_test(data_dict, criteria):
    if data_dict["Sensor Interval"] == "N/A":
        return False
    else:
        return criteria == data_dict["Sensor Interval"]

def upload_interval_test(data_dict, criteria):
    if data_dict["Upload Interval"] == "N/A":
        return False
    else:
        return criteria == data_dict["Upload Interval"]

def warehouse_interval_test(data_dict, criteria):
    if data_dict["Warehouse Interval"] == "N/A":
        return False
    else:
        return criteria == data_dict["Warehouse Interval"]

def min_vbat_test(data_dict, criteria):
    if data_dict["Min Vbat Mv"] == "N/A":
        return False
    else:
        return criteria == data_dict["Min Vbat Mv"]

def flight_mode_test(data_dict, criteria):
    if data_dict["Flight Mode Enable"] == "N/A":
        return False
    else:
        return criteria == data_dict["Flight Mode Enable"]

def handshake_test(data_dict, criteria):
    if data_dict["Upload Handshake"] == "N/A":
        return False
    else:
        return criteria == data_dict["Upload Handshake"]

def accelerometer_config_test(data_dict, criteria):
    if data_dict["Accelerometer Config"] == "N/A":
        return False
    else:
        return criteria == data_dict["Accelerometer Config"]

def accelerometer_threshold_test(data_dict, criteria):
    if data_dict["Accelerometer Threshold"] == "N/A":
        return False
    else:
        return criteria == data_dict["Accelerometer Threshold"]

def firmware_version_test(data_dict, criteria):
    if data_dict["Firmware Version"] == "N/A":
        return False
    else:
        return data_dict["Firmware Version"] in criteria

def wifi_enable_test(data_dict, criteria):
    if data_dict["WiFi Enable"] == "N/A":
        return False
    else:
        return criteria == data_dict["WiFi Enable"]

def scan_suspend_test(data_dict, criteria):
    if data_dict["Scan Suspend"] == "N/A":
        return False
    else:
        return criteria == data_dict["Scan Suspend"]

def LTE_attach_timeout_test(data_dict, criteria):
    if data_dict["LTE Attach Timeout"] == "N/A":
        return False
    else:
        return criteria == data_dict["LTE Attach Timeout"]
    
def timeout_multiplier_test(data_dict, criteria):
    if data_dict["Time Passed Since Reported"] == "N/A":
        return False
    else:
        time_str = data_dict["Time Passed Since Reported"]

        # Split the string into components
        components = time_str.split()

        # Extract hours, minutes, and seconds
        hours = int(components[0]) if "hrs" in time_str else 0
        minutes = int(components[2]) if "mins" in time_str else 0
        seconds = int(components[4]) if "secs" in time_str else 0

        # Convert hours, minutes, and seconds to minutes
        total_minutes = hours * 60 + minutes + seconds / 60
        if criteria["Warehouse Interval"] and data_dict["Warehouse Interval"] !=  0:
            return total_minutes < criteria["Timeout Multiplier"] * data_dict["Warehouse Interval"]
        elif criteria["Upload Interval"] and data_dict["Upload Interval"] !=  0:
            return total_minutes < criteria["Timeout Multiplier"] * data_dict["Upload Interval"]
        else:
            return False

def run_test(data_dict, criteria):
    bool = True
    fail_list = []
    if criteria["Sensor Interval"] is not None:
        bool = bool and sensor_interval_test(data_dict, criteria["Sensor Interval"])
        if not sensor_interval_test(data_dict, criteria["Sensor Interval"]):
            fail_list.append("Sensor Interval")
    if criteria["Upload Interval"] is not None:
        bool = bool and upload_interval_test(data_dict, criteria["Upload Interval"])
        if not upload_interval_test(data_dict, criteria["Upload Interval"]):
            fail_list.append("Upload Interval")
    if criteria["Warehouse Interval"] is not None:
        bool = bool and warehouse_interval_test(data_dict, criteria["Warehouse Interval"])
        if not warehouse_interval_test(data_dict, criteria["Warehouse Interval"]):
            fail_list.append("Warehouse Interval")
    if criteria["Min Vbat Mv"] is not None:
        bool = bool and min_vbat_test(data_dict, criteria["Min Vbat Mv"])
        if not min_vbat_test(data_dict, criteria["Min Vbat Mv"]):
            fail_list.append("Min Vbat Mv")
    if criteria["Flight Mode Enable"] is not None:
        bool = bool and flight_mode_test(data_dict, criteria["Flight Mode Enable"])
        if not flight_mode_test(data_dict, criteria["Flight Mode Enable"]):
            fail_list.append("Flight Mode Enable")
    if criteria["Upload Handshake"] is not None:
        bool = bool and handshake_test(data_dict, criteria["Upload Handshake"])
        if not handshake_test(data_dict, criteria["Upload Handshake"]):
            fail_list.append("Upload Handshake")
    if criteria["Accelerometer Config"] is not None:
        bool = bool and accelerometer_config_test(data_dict, criteria["Accelerometer Config"])
        if not accelerometer_config_test(data_dict, criteria["Accelerometer Config"]):
            fail_list.append("Accelerometer Config")
    if criteria["Accelerometer Threshold"] is not None:
        bool = bool and accelerometer_threshold_test(data_dict, criteria["Accelerometer Threshold"])
        if not accelerometer_threshold_test(data_dict, criteria["Accelerometer Threshold"]):
            fail_list.append("Accelerometer Threshold")
    if criteria["Firmware Version"] is not None:
        bool = bool and firmware_version_test(data_dict, criteria["Firmware Version"])
        if not firmware_version_test(data_dict, criteria["Firmware Version"]):
            fail_list.append("Firmware Version")
    if criteria["WiFi Enable"] is not None:
        bool = bool and wifi_enable_test(data_dict, criteria["WiFi Enable"])
        if not wifi_enable_test(data_dict, criteria["WiFi Enable"]):
            fail_list.append("WiFi Enable")
    if criteria["Scan Suspend"] is not None:
        bool = bool and scan_suspend_test(data_dict, criteria["Scan Suspend"])
        if not scan_suspend_test(data_dict, criteria["Scan Suspend"]):
            fail_list.append("Scan Suspend")
    if criteria["LTE Attach Timeout"] is not None:
        bool = bool and LTE_attach_timeout_test(data_dict, criteria["LTE Attach Timeout"])
        if not LTE_attach_timeout_test(data_dict, criteria["LTE Attach Timeout"]):
            fail_list.append("LTE Attach Timeout")
    if criteria["Timeout Multiplier"] is not None:
        bool = bool and timeout_multiplier_test(data_dict, criteria)
        if not timeout_multiplier_test(data_dict, criteria):
            fail_list.append("Time Passed Since Reported")
    return bool, fail_list

def produce_data_dict(device_id, criteria):
    """Populate desired data for each device"""
    shadow_reported = get_device_shadow_reported(device_id)
    time = get_health_last_reported(device_id)
    # Get the current UTC time as a timezone-aware datetime object
    current_utc_time = datetime.now(timezone.utc)
    # Convert the time string to a timezone-aware datetime object
    if time == "N/A":
        formatted_time_difference = "N/A"
    else:
        reported_time = datetime.strptime(time, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
        # Calculate the time difference
        time_difference = current_utc_time - reported_time
        hours = time_difference.seconds // 3600
        minutes = (time_difference.seconds % 3600) // 60
        seconds = time_difference.seconds % 60
        # Format the time difference
        formatted_time_difference = f"{hours} hrs {minutes} mins {seconds} secs"

    # print(shadow_reported["42"].keys())
    data_dict = {
        "IMEI": device_id,
        "Last Reported Time (UTC)": time,
        "Current Time (UTC)": current_utc_time.replace(tzinfo=None).strftime('%Y-%m-%d %H:%M:%S'),
        "Time Passed Since Reported": formatted_time_difference,
        "Sensor Interval": shadow_reported["0"] if shadow_reported else "N/A",
        "Upload Interval": shadow_reported["1"] if shadow_reported else "N/A",
        "Warehouse Interval": shadow_reported["11"] if shadow_reported else "N/A",
        "Min Vbat Mv": shadow_reported["20"] if shadow_reported else "N/A",
        "Flight Mode Enable": shadow_reported["21"] if shadow_reported else "N/A",
        "Upload Handshake": shadow_reported["22"] if shadow_reported else "N/A",
        "Accelerometer Config": shadow_reported["23"] if shadow_reported else "N/A",
        "Accelerometer Threshold": shadow_reported["24"] if shadow_reported else "N/A",
        "Firmware Version": shadow_reported["25"] if shadow_reported else "N/A",
        "WiFi Enable": shadow_reported["28"] if shadow_reported else "N/A",
        "Scan Suspend": shadow_reported["30"] if shadow_reported else "N/A",
        "LTE Attach Timeout": shadow_reported["34"] if shadow_reported else "N/A",
        "Pass": True,
        "Failed Category": []
    }

    data_dict["Pass"], data_dict["Failed Category"] = run_test(data_dict, criteria)
    return data_dict

def run(fname, criteria):
    # Read device list from file specified by the user
    with open(fname, 'r') as file:
        device_list = file.read().splitlines()
    print("reading device list: ", len(device_list))

    # An array tracking all the relevant data for all relevant devices
    data_list = []

    for dev in device_list:
        try:
            data_dict = produce_data_dict(dev, criteria)
            data_list.append(data_dict)
        except Exception as e:
            print(dev + f": Exception: {str(e)}")
            pass

    # Create a dataframe
    df = pd.DataFrame(data_list)
    df = df[list(data_list[0].keys())]
    # Save dataframe as excel
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    new_file_path = os.path.join(os.getcwd(), f'Health Check {timestamp}.xlsx')
    df.to_excel(new_file_path, index=False, sheet_name="Health Check")

    # failed_list = []

    # with open(f'failed {timestamp}.txt', 'w') as outfile:
    #     for data_dict in data_list:
    #         if not data_dict["Pass"]:
    #             failed_list.append(str(data_dict["IMEI"]))
    #             failed_record = str(data_dict["IMEI"]) + "   " + str(data_dict["Last Reported Time (UTC)"])
    #             outfile.write(failed_record + '\n')

    # # Open the original file in read mode and a temporary file in write mode
    # with open(fname, 'r') as read_file, open('temp_file.txt', 'w') as temp_file:
    #     # Read through each line in the original file
    #     for line in read_file:
    #         # Check if the line's number (strip removes newline characters) is not in the numbers to remove
    #         if line.strip() not in failed_list:
    #             # Write this line to the temporary file
    #             temp_file.write(line)

    # # Remove the original file
    # os.remove(fname)

    # # Rename the temporary file to the original file name
    # os.rename('temp_file.txt', fname)
run(fname, criteria)