import asyncio
import aiohttp
import json
import os
import pandas as pd
from datetime import datetime, timezone

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

async def login(session, email, password):
    """Attempt to log in a user with given email and password."""
    async with session.post(f"{API_BASE}/login?clientId=Tbocs0cjhrac",
                            json={"emailId": email, "userSecret": password},
                            headers={"Content-Type": "application/json", "Origin": "DOC.API"}) as response:
        login_response = await response.json()
        if login_response.get("status") == "SUCCESS":
            print("Login successful as ", email)
            return login_response["token"], login_response['clientApiKey']['clientId']
        print(f"Login failed: {login_response}")
        return None, None

async def get_device_shadow_reported(session, device_id, common_headers):
    """Retrieve and parse device shadow state."""
    async with session.get(f"{API_BASE}/device/{device_id}/shadow", headers=common_headers) as response:
        shdw = await response.json()
        reported = shdw['shadow']['state'].get('reported') if shdw['status'] == "SUCCESS" else None
    return reported

async def get_health_last_reported(session, device_id, common_headers):
    """Retrieve and parse device health state."""
    async with session.get(f"{API_BASE}/device/{device_id}/health", headers=common_headers) as response:
        health = await response.json()
        reported_time = health['device']['health'].get('lastReportedAt') if health['status'] == "SUCCESS" else "N/A"
    return reported_time or "N/A"

async def produce_data_dict(session, device_id, criteria, common_headers):
    """Populate desired data for each device"""
    shadow_reported = await get_device_shadow_reported(session, device_id, common_headers)
    time = await get_health_last_reported(session, device_id, common_headers)
    current_utc_time = datetime.now(timezone.utc)

    if time == "N/A":
        formatted_time_difference = "N/A"
    else:
        try:
            reported_time = datetime.strptime(time, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
            time_difference = current_utc_time - reported_time
            total_seconds = time_difference.total_seconds()
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            seconds = int(total_seconds % 60)
            formatted_time_difference = f"{hours} hrs {minutes} mins {seconds} secs"
        except ValueError:
            formatted_time_difference = "Invalid date format"

    data_dict = {
        "IMEI": device_id,
        "Last Reported Time (UTC)": time,
        "Current Time (UTC)": current_utc_time.replace(tzinfo=None).strftime('%Y-%m-%d %H:%M:%S'),
        "Time Passed Since Reported": formatted_time_difference,
        "Sensor Interval": shadow_reported["0"] if shadow_reported and "0" in shadow_reported else "N/A",
        "Upload Interval": shadow_reported["1"] if shadow_reported and "1" in shadow_reported else "N/A",
        "Warehouse Interval": shadow_reported["11"] if shadow_reported and "11" in shadow_reported else "N/A",
        "Min Vbat Mv": shadow_reported["20"] if shadow_reported and "20" in shadow_reported else "N/A",
        "Flight Mode Enable": shadow_reported["21"] if shadow_reported and "21" in shadow_reported else "N/A",
        "Upload Handshake": shadow_reported["22"] if shadow_reported and "22" in shadow_reported else "N/A",
        "Accelerometer Config": shadow_reported["23"] if shadow_reported and "23" in shadow_reported else "N/A",
        "Accelerometer Threshold": shadow_reported["24"] if shadow_reported and "24" in shadow_reported else "N/A",
        "Firmware Version": shadow_reported["25"] if shadow_reported and "25" in shadow_reported else "N/A",
        "WiFi Enable": shadow_reported["28"] if shadow_reported and "28" in shadow_reported else "N/A",
        "Scan Suspend": shadow_reported["30"] if shadow_reported and "30" in shadow_reported else "N/A",
        "LTE Attach Timeout": shadow_reported["34"] if shadow_reported and "34" in shadow_reported else "N/A",
        "Pass": True,
        "Failed Category": []
    }

    data_dict["Pass"], data_dict["Failed Category"] = run_test(data_dict, criteria)
    return data_dict
    # try:
    #     shadow_reported = await get_device_shadow_reported(session, device_id, common_headers)
    #     time = await get_health_last_reported(session, device_id, common_headers)
    #     current_utc_time = datetime.now(timezone.utc)

    #     if time == "N/A":
    #         formatted_time_difference = "N/A"
    #     else:
    #         try:
    #             reported_time = datetime.strptime(time, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
    #             time_difference = current_utc_time - reported_time
    #             total_seconds = time_difference.total_seconds()
    #             hours = int(total_seconds // 3600)
    #             minutes = int((total_seconds % 3600) // 60)
    #             seconds = int(total_seconds % 60)
    #             formatted_time_difference = f"{hours} hrs {minutes} mins {seconds} secs"
    #         except ValueError:
    #             formatted_time_difference = "Invalid date format"

    #     data_dict = {
    #         "IMEI": device_id,
    #         "Last Reported Time (UTC)": time,
    #         "Current Time (UTC)": current_utc_time.replace(tzinfo=None).strftime('%Y-%m-%d %H:%M:%S'),
    #         "Time Passed Since Reported": formatted_time_difference,
    #         "Sensor Interval": shadow_reported["0"] if shadow_reported else "N/A",
    #         "Upload Interval": shadow_reported["1"] if shadow_reported else "N/A",
    #         "Warehouse Interval": shadow_reported["11"] if shadow_reported else "N/A",
    #         "Min Vbat Mv": shadow_reported["20"] if shadow_reported else "N/A",
    #         "Flight Mode Enable": shadow_reported["21"] if shadow_reported else "N/A",
    #         "Upload Handshake": shadow_reported["22"] if shadow_reported else "N/A",
    #         "Accelerometer Config": shadow_reported["23"] if shadow_reported else "N/A",
    #         "Accelerometer Threshold": shadow_reported["24"] if shadow_reported else "N/A",
    #         "Firmware Version": shadow_reported["25"] if shadow_reported else "N/A",
    #         "WiFi Enable": shadow_reported["28"] if shadow_reported else "N/A",
    #         "Scan Suspend": shadow_reported["30"] if shadow_reported else "N/A",
    #         "LTE Attach Timeout": shadow_reported["34"] if shadow_reported else "N/A",
    #         "Pass": True,
    #         "Failed Category": []
    #     }

    #     data_dict["Pass"], data_dict["Failed Category"] = run_test(data_dict, criteria)
    #     return data_dict
    # except Exception as e:
    #     print(f"Error processing device {device_id}: {e}")
    #     return None

async def run_async():
    id, pwd, fname = prompt()
    if fname == "":
        fname = "imei.txt"

    json_file = input("Enter criteria json file name (default criteria.json): ")
    if json_file == "":
        json_file = "criteria.json"
    # Open the JSON file
    with open(json_file, 'r') as file:
        criteria = json.load(file)

    async with aiohttp.ClientSession() as session:
        token, xapikey = await login(session, id, pwd)

        if not token or not xapikey:
            return

        common_headers = {
            "Authorization": token,
            "Origin": "https://app.tagntrac.io",
            "x-api-key": xapikey
        }

        with open(fname, 'r') as file:
            device_list = file.read().splitlines()
        print("reading device list: ", len(device_list))

        tasks = [produce_data_dict(session, dev, criteria, common_headers) for dev in device_list]
        data_list = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out None results and log exceptions
        valid_data_list = []
        for data in data_list:
            if isinstance(data, dict):
                valid_data_list.append(data)
            elif isinstance(data, Exception):
                print(f"Task resulted in an exception: {data}")

        df = pd.DataFrame(valid_data_list)
        if not df.empty:
            df = df[list(valid_data_list[0].keys())]
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            new_file_path = os.path.join(os.getcwd(), f'Health Check {timestamp}.xlsx')
            df.to_excel(new_file_path, index=False, sheet_name="Health Check")
        else:
            print("No valid data to write to Excel")

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

        components = time_str.split()
        hours = int(components[0]) if "hrs" in time_str else 0
        minutes = int(components[2]) if "mins" in time_str else 0
        seconds = int(components[4]) if "secs" in time_str else 0
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

if __name__ == "__main__":
    asyncio.run(run_async())