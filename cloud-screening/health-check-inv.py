from datetime import datetime, timezone
import os
import json
import requests
import pandas as pd
import concurrent.futures
import openpyxl
from openpyxl.utils.dataframe import dataframe_to_rows
from random import randint
from time import sleep
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Base URL for the API
API_BASE = "https://api.tagntrac.io"
orgID = "YjNKbllXNXBlbUYwYVc5dTNmNWEyNmUwLTNiYmItMTFlZS1hNzFjLTAxNWQxZjkxMWE2NA=="

# Set to None if want to ignore such config
criteria = {
    "Sensor Interval": None,
    "Upload Interval": None,
    "Warehouse Interval": None,
    "Min Vbat Mv": None,
    "Flight Mode Enable": None,
    "Upload Handshake": None,
    "Accelerometer Config": None,
    "Accelerometer Threshold": None,
    "Firmware Version": ["SSL3_00_L_1_12"],
    "WiFi Enable": None,
    "Scan Suspend": None,
    "LTE Attach Timeout": None,
    "Timeout Multiplier": None
}

def login(email, password):
    """Attempt to log in a user with given email and password."""
    login_response = requests.post(f"{API_BASE}/login?clientId=Tbocs0cjhrac",
                             data = json.dumps({"emailId" : email, "userSecret" : password}),
                             headers={"Content-Type" : "application/json", "Origin" : "DOC.API"})
    try:
        if login_response.json()["status"] == "SUCCESS":
            print("\nLogin successful!")
            return (login_response.json()["token"], login_response.json()['clientApiKey']['clientId'])
    except Exception as e:
        print(f"Exception: {str(e)}")
    print(f"\nLogin failed: {login_response.text}")
    return (None, None)

# Capture user input
id, pwd = "inventory@tagntrac.io", "T6wkccwd#1"

# Perform login and capture token and API key
token, xapikey = login(id, pwd)

# Common headers used in GET requests
common_headers = {
    "Authorization": token,
    "Origin": "https://app.tagntrac.io",
    "x-api-key": xapikey
}

def get_all_devices():
    """Retrieve all devices."""
    device_list = []
    response = requests.get(f"https://api.tagntrac.io/organization/{orgID}/devices", headers=common_headers)
    for dev in response.json()['devices']:
        if dev["deviceType"] == "CATM1_TAG":
            device_list.append(dev["id"])
    return device_list

def requests_retry_session(
    retries=10,
    backoff_factor=1,
    status_forcelist=(500, 502, 504),
    session=None,
):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def get_device_shadow_reported(device_id):
    """Retrieve and parse device shadow state."""
    try:
        response = requests_retry_session().get(f"{API_BASE}/device/{device_id}/shadow", headers=common_headers)
        response.raise_for_status()
        shdw = response.json()
        if shdw.get('status') == "SUCCESS":
            if 'reported' in shdw['shadow']['state']:
                return shdw['shadow']['state']['reported']
            else:
                return {"25": "Not Activated"}
    except requests.exceptions.HTTPError as errh:
        print(f"Http Error: {str(errh)}")
    except requests.exceptions.ConnectionError as errc:
        print(f"Error Connecting: {str(errc)}")
    except requests.exceptions.Timeout as errt:
        print(f"Timeout Error: {str(errt)}")
    except requests.exceptions.RequestException as err:
        print(f"Request Exception: {str(err)}")
    except ValueError:
        print(f"Error: Unable to parse JSON response: {response.text} --> {device_id}")
    except Exception as e:
        print(f"Exception: {str(e)}")
    return None


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
    if data_dict["Firmware Version"] == "N/A" or data_dict["Firmware Version"] == "Not Activated":
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
    shadow_reported = None
    count = 0
    while shadow_reported is None and count < 10:
        if count > 0:
            sleep(randint(1, 4*count))

        """Populate desired data for each device"""
        shadow_reported = get_device_shadow_reported(device_id)
        #tm = get_health_last_reported(device_id)
        tm = "N/A"
        count += 1
    if count > 9:
        print("Skipped device (couldn't read): ", device_id)
    
    current_utc_time = datetime.now(timezone.utc)
    
    if tm == "N/A":
        formatted_time_difference = "N/A"
    else:
        try:
            reported_time = datetime.strptime(tm, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
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
        "Last Reported Time (UTC)": tm,
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
    data_dict["Failed Category"] = ", ".join(data_dict["Failed Category"])  # Convert list to string

    short_dict = {
        "IMEI": data_dict["IMEI"],
        "Passed": "Firmware Version" not in data_dict["Failed Category"],
        "Firmware Version": data_dict["Firmware Version"]
    }
    return data_dict, short_dict

def to_excel(data_list, sheet_name, timestamp):
    if not data_list:
        print(f"No data to write for {sheet_name}")
        return
    df = pd.DataFrame(data_list)
    df = df[list(data_list[0].keys())]
    new_file_path = os.path.join(os.getcwd(), f'Health Check {timestamp}.xlsx')
    if not os.path.isfile(new_file_path):
        df.to_excel(new_file_path, index=False, sheet_name=sheet_name)
    else:
        workbook = openpyxl.load_workbook(new_file_path)
        sheet = workbook.create_sheet(sheet_name)
        for r in dataframe_to_rows(df, header=True, index=False):
            sheet.append(r)
        workbook.save(new_file_path)
        workbook.close()

def run(criteria):
    # Read device list from file specified by the user
    #device_list = get_all_devices()
    #print(f"Total %d devices in accout" % (len(device_list)))

    with open('imei.csv', 'r') as file:
        device_list = file.read().splitlines()
    print("reading device list: ", len(device_list))

    # An array tracking all the relevant data for all relevant devices
    data_list = []
    short_data_list = []
    count = 0
    # Using ThreadPoolExecutor for parallel processing
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(produce_data_dict, dev, criteria): dev for dev in device_list}
        for future in concurrent.futures.as_completed(futures):
            dev = futures[future]
            try:
                data_dict, short_dict = future.result()
                data_list.append(data_dict)
                short_data_list.append(short_dict)
                count += 1
                if count % 100 == 0:
                    print(f"Read {count} devices...")
            except Exception as e:
                print(dev + f": Exception 3: {str(e)}")

    print(f"Total {count} units, loading data into excel...")

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    to_excel(short_data_list, "Summary", timestamp)
    to_excel(data_list, "Detailed", timestamp)


run(criteria)
