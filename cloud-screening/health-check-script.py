from datetime import datetime, timezone
import os
import re
import sys
import matplotlib.pyplot as plt
import requests
import json
import pandas as pd
import openpyxl
from datetime import timedelta
from pptx import Presentation
from pptx.util import Inches
from openpyxl.utils.dataframe import dataframe_to_rows
import matplotlib.dates as mdates
from geopy.distance import geodesic

prs = Presentation()

json_file = input("Enter criteria json file name: ")
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
input_imei = ""
id = "username" 
pwd = "password" 
def prompt():
    """Prompt user for username, password, and file name for device id list."""
    id = input("Enter username: ")
    pwd = input("Enter password: ")
    input_imei = input("Enter file name of device id list: ")
    return id, pwd, input_imei


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
# id, pwd, input_imei = prompt()
id = "owen.tnt@tagntrac.com"
pwd = "Vx9%xCqf"
input_imei = "output.txt"

def login2(email, password):
    login_response = requests.post(f"{API_BASE}/login?clientId=Tbocs0cjhrac",
                             data = json.dumps({"emailId" : email, "userSecret" : password,"reqType": "cognitoAuth"}),
                             headers={"Content-Type" : "application/json", "Origin" : "DOC.API"})
    try:
        if login_response.json()["status"] == "SUCCESS":
            print("Login successful as ", email)
            return (login_response.json()["idToken"], login_response.json()['clientApiKey']['clientId'])
    except Exception as e:
        print(f"Exception: {str(e)}")
    print(f"Login failed: {login_response.text}")
    return (None, None)

idToken, xapikey2 = login2(id, pwd)
common_headers2 = {"Authorization" : idToken,
                  "Origin" : f"{API_BASE}",
                  "x-api-key" : xapikey2}

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

def generate_time_string(hours_ago):
    # Get the current time in UTC
    end_time = datetime.now(timezone.utc)
    # Calculate the start time by subtracting the given hours
    start_time = end_time - timedelta(hours=hours_ago)

    # Format both times to the ISO 8601 format with milliseconds
    start_str = start_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    end_str = end_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')

    # Construct the final string
    result_string = f"?start={start_str}&end={end_str}"
    return result_string

def get_device_data_v2(device_id, hours_ago):
    queryDates = generate_time_string(hours_ago)
    print(queryDates)
    response = requests.get(f"{API_BASE}/v2/device/{device_id}/data"+queryDates, headers=common_headers2)
    if response.json()['status'] == 'SUCCESS':
        data = response.json()['response']
        return data
    else: 
        print("Get Device data2 failed: "+device_id)
        return None

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

def time_delta(data, id):
    # if there is rsrp then it is an upload sample, if not it is a sensor sample
    upload_data = []
    sensor_data = []
    sensor_delta = []
    upload_delta = []
    for entry in data:
        if entry['rsrp'] is not None:
            upload_data.append(entry)
        else:
            sensor_data.append(entry)
    
    # Record the top three longest gap between sensor samples
    longest_sensor_gaps = []
    for i in range(1, len(sensor_data)):
        previous_ts_ms = int(sensor_data[i]['ts'])
        previous_ts_s = previous_ts_ms / 1000
        previous_time = datetime.fromtimestamp(previous_ts_s, timezone.utc)

        current_ts_ms = int(sensor_data[i-1]['ts'])
        currents_ts_s = current_ts_ms / 1000
        current_time = datetime.fromtimestamp(currents_ts_s, timezone.utc)

        # Calculate time difference
        time_difference = current_time - previous_time
        # Calculate hours, minutes, and seconds from time difference
        hours_formatted = time_difference.total_seconds() // 3600
        minutes = (time_difference.total_seconds() % 3600) // 60
        seconds = time_difference.total_seconds() % 60
        # Format the time difference
        formatted_time_difference = f"{int(hours_formatted)} hrs {int(minutes)} mins {int(seconds)} secs"
        if len(longest_sensor_gaps) < 3:
            longest_sensor_gaps.append([previous_ts_s, currents_ts_s, formatted_time_difference])
        else:
            min_index = 0
            for i in range(1, len(longest_sensor_gaps)):
                if longest_sensor_gaps[i][2] < longest_sensor_gaps[min_index][2]:
                    min_index = i
            if convert_to_seconds(longest_sensor_gaps[min_index][2]) < int(time_difference.total_seconds()):  
                longest_sensor_gaps[min_index] = [previous_ts_s, currents_ts_s, formatted_time_difference]

    # Record the top three longest gap between upload samples
    longest_upload_gaps = []
    for i in range(1, len(upload_data)):
        previous_ts_ms = int(upload_data[i]['ts'])
        previous_ts_s = previous_ts_ms / 1000
        previous_time = datetime.fromtimestamp(previous_ts_s, timezone.utc)

        current_ts_ms = int(upload_data[i-1]['ts'])
        currents_ts_s = current_ts_ms / 1000
        current_time = datetime.fromtimestamp(currents_ts_s, timezone.utc)

        # Calculate time difference
        time_difference = current_time - previous_time
        # Calculate hours, minutes, and seconds from time difference
        hours_formatted = time_difference.total_seconds() // 3600
        minutes = (time_difference.total_seconds() % 3600) // 60
        seconds = time_difference.total_seconds() % 60
        # Format the time difference
        formatted_time_difference = f"{int(hours_formatted)} hrs {int(minutes)} mins {int(seconds)} secs"
        if len(longest_upload_gaps) < 3:
            longest_upload_gaps.append([previous_ts_s, currents_ts_s, formatted_time_difference])
        else:
            min_index = 0
            for i in range(1, len(longest_upload_gaps)):
                if longest_upload_gaps[i][2] < longest_upload_gaps[min_index][2]:
                    min_index = i
            if convert_to_seconds(longest_upload_gaps[min_index][2]) < int(time_difference.total_seconds()):  
                longest_upload_gaps[min_index] = [previous_ts_s, currents_ts_s, formatted_time_difference]

    for item in longest_sensor_gaps:
        data_dict = {
            'IMEI': id,
            'Sensor Samples': len(sensor_data),
            "Previous Timestamp": str(item[0]),
            "Report TimeStamp": str(item[1]),
            "Time Delta": item[2]
        }
        sensor_delta.append(data_dict)

    for item in longest_upload_gaps:
        data_dict = {
            'IMEI': id,
            'Upload Samples': len(upload_data),
            "Previous Timestamp": str(item[0]),
            "Report TimeStamp": str(item[1]),
            "Time Delta": item[2]
        }
        upload_delta.append(data_dict)

    return sensor_delta, upload_delta

def count_decrement_num(data, id):
    # check how amny times the value of count went down compared to previous sample
    decrement_counts = 0
    answer = []

    previous_count = None
    for i in range(len(data)-1, -1, -1):
        current_count = data[i]['count']
        if current_count is not None:
            current_count = int(current_count)  # Convert to integer only if it's not None
            if previous_count is not None:
                if current_count < previous_count:
                    decrement_counts += 1
                    data_dict = {
                        "IMEI": id,
                        "Previous Timestamp": str(int(data[i]['ts'])/1000),
                        "Reported Timestamp": str(int(data[i-1]['ts'])/1000),
                        "Decrements in Count Value": decrement_counts
                    }
                    answer.append(data_dict)
            previous_count = current_count

    return answer

def successive_distance(data, id):
    top_3_distance = []
    answer = []

    for i in range(1, len(data)):
        previous_ts_ms = int(data[i]['ts'])
        previous_ts_s = previous_ts_ms / 1000
        previous_coord = (float(data[i]['lat']), float(data[i]['lng']))

        current_ts_ms = int(data[i-1]['ts'])
        currents_ts_s = current_ts_ms / 1000
        current_coord = (float(data[i-1]['lat']), float(data[i-1]['lng']))

        if len(top_3_distance) < 3:
            top_3_distance.append([previous_ts_s, currents_ts_s, geodesic(previous_coord, current_coord).miles])
        else:
            min_index = 0
            for i in range(1, len(top_3_distance)):
                if top_3_distance[i][2] < top_3_distance[min_index][2]:
                    min_index = i
            if top_3_distance[min_index][2] < geodesic(previous_coord, current_coord).miles:  
                top_3_distance[min_index] = [previous_ts_s, currents_ts_s, geodesic(previous_coord, current_coord).miles]
    
    for item in top_3_distance:
        data_dict = {
            "IMEI": id,
            "Previous Timestamp": str(item[0]),
            "Report TimeStamp": str(item[1]),
            "Distance Traveled (miles)": item[2]
        }
        answer.append(data_dict)

    return answer

def data_clean_up(data_entry, dev_id, hours_ago):
    timestamp_ms = int(data_entry['ts'])
    timestamp_s = timestamp_ms / 1000
    reported_time = datetime.fromtimestamp(timestamp_s, timezone.utc)

    # Calculate time difference
    current_utc_time = datetime.now(timezone.utc)
    time_difference = current_utc_time - reported_time

    if data_entry['vbat'] is not None:
        # Calculate hours, minutes, and seconds from time difference
        hours_formatted = time_difference.total_seconds() // 3600
        minutes = (time_difference.total_seconds() % 3600) // 60
        seconds = time_difference.total_seconds() % 60
        # Format the time difference
        formatted_time_difference = f"{int(hours_formatted)} hrs {int(minutes)} mins {int(seconds)} secs"
        data_dict = {
            'IMEI': dev_id,
            'Timestamp': reported_time.strftime('%Y-%m-%d %H:%M:%S'),
            'Time passed since Reported': formatted_time_difference,
            'vBat': int(data_entry['vbat']),
            f'Reported time since {hours_ago}hrs ago (hrs)': float(hours_ago)-time_difference.total_seconds() / 3600
        }
        return data_dict
    else:
        return None 

# Convert 'Time passed since Reported' into a total seconds for plotting
def convert_to_seconds(t):
    try:
        time_parts = {'hrs': 0, 'mins': 0, 'secs': 0}
        parts = t.split()
        for i in range(0, len(parts), 2):
            if parts[i + 1].startswith('hr'):
                time_parts['hrs'] = int(parts[i])
            elif parts[i + 1].startswith('min'):
                time_parts['mins'] = int(parts[i])
            elif parts[i + 1].startswith('sec'):
                time_parts['secs'] = int(parts[i])
        return time_parts['hrs'] * 3600 + time_parts['mins'] * 60 + time_parts['secs']
    except Exception as e:
        print(f"Error converting time: {t} - {e}")
        return 0  # return 0 if there's an error, or you could choose to handle it differently

def convert_to_hours(t):
    try:
        time_parts = {'hrs': 0, 'mins': 0, 'secs': 0}
        parts = t.split()
        for i in range(0, len(parts), 2):
            if parts[i + 1].startswith('hr'):
                time_parts['hrs'] = int(parts[i])
            elif parts[i + 1].startswith('min'):
                time_parts['mins'] = int(parts[i])
            elif parts[i + 1].startswith('sec'):
                time_parts['secs'] = int(parts[i])
        total_seconds = time_parts['hrs'] * 3600 + time_parts['mins'] * 60 + time_parts['secs']
        return total_seconds / 3600  # Convert seconds to hours
    except Exception as e:
        print(f"Error converting time: {t} - {e}")
        return 0  # return 0 if there's an error, or you could choose to handle it differently

def create_plot_and_slide(grouped, timestamp, prs, count):
    # Create a figure and an axes.
    fig, ax = plt.subplots()

    for name, group in grouped:
        ax.plot(group['Hours Since Reported'], group['vBat'], label=name)

    # Setting the x-axis to show more recent times on the right
    ax.invert_xaxis()

    # Label the axes
    ax.set_xlabel('Time Passed (hours ago)')
    ax.set_ylabel('Battery Voltage (vBat)')

    # Title and legend
    ax.set_title('Battery Voltage Over Time')
    ax.legend(title='IMEI')

    # Show a grid
    ax.grid(True)

    # Save the plot as an image
    image_dir = os.path.join(os.getcwd(), "images")
    if not os.path.exists(image_dir):
        os.makedirs(image_dir)
    image_path = os.path.join(image_dir, f'vBat_Time_{timestamp}_{count}.png')
    plt.savefig(image_path)
    plt.close(fig)

    # Add a new slide for the plot
    slide_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(slide_layout)
    left = Inches(1)
    top = Inches(0.1)
    slide.shapes.add_picture(image_path, left, top, width=Inches(10), height=Inches(8))

def to_excel(data_list, sheet_name, excel_name):
    df = pd.DataFrame(data_list)
    df = df[list(data_list[0].keys())]
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    new_file_path = os.path.join(os.getcwd(), excel_name)
    if os.path.isfile(new_file_path) == False:
        df.to_excel(new_file_path, index=False, sheet_name=sheet_name)
    else:
        workbook = openpyxl.load_workbook(new_file_path)  # load workbook if already exists
        sheet = workbook.create_sheet(sheet_name)
        # append the dataframe results to the current excel file
        for row in dataframe_to_rows(df, header = True, index = False):
            sheet.append(row)
        workbook.save(new_file_path)  # save workbook
        workbook.close()  # close workbook

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
    excel_name = f'Health Check {timestamp}.xlsx'
    new_file_path = os.path.join(os.getcwd(), excel_name)
    df.to_excel(new_file_path, index=False, sheet_name="Last Reported")

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
    hours_ago = input("Enter the time period (how many hours ago from now): ")

    # An array tracking all the relevant data for all relevant devices
    sensor_delta_list = []
    upload_delta_list = []
    count_decrement_list = []
    distances_list = []
    for i, dev in enumerate(device_list):
        print(f"---\nReport for device {dev}")
        data = get_device_data_v2(dev, int(hours_ago))
        if data is not None:
            sensor_delta_temp, upload_delta_temp = time_delta(data,dev)
            sensor_delta_list += sensor_delta_temp
            upload_delta_list += upload_delta_temp
            count_decrement_list += count_decrement_num(data, dev)
            distances_list += successive_distance(data, dev)
    
    # store data in excel file
    to_excel(sensor_delta_list, "Sensor Samples", excel_name)
    to_excel(upload_delta_list, "Upload Samples", excel_name)
    to_excel(count_decrement_list, "Count Decrements", excel_name)
    to_excel(distances_list, "Distance", excel_name)

    # An array tracking all the relevant data for all relevant devices
    vbat_data_list = []
    group_list = []
    entry_list = []
    slide_count = 0
    for i, dev in enumerate(device_list):
        data = get_device_data_v2(dev, int(hours_ago))
        if data is not None:
            for entry in data:
                if 1==1:# and entry['vbat'] is not None:
                    entry_list.append(entry['ts'])
                data_dict = data_clean_up(entry, dev, hours_ago)
                try:
                    data_dict = data_clean_up(entry, dev, hours_ago)
                    if data_dict is not None:
                        group_list.append(data_dict)
                        vbat_data_list.append(data_dict)
                except:
                    print(f"Device {dev} shows error")
        # Check if we need to create a new slide
        if (i + 1) % 5 == 0 or i + 1 == len(group_list):  # After every 5 devices or the last device
            df = pd.DataFrame(group_list)
            df['Hours Since Reported'] = df['Time passed since Reported'].apply(convert_to_hours)
            grouped = df.groupby('IMEI')
            create_plot_and_slide(grouped, datetime.now().strftime("%Y%m%d%H%M%S"), prs, slide_count)
            slide_count += 1
            group_list = []  # Reset for the next batch

    print(f"There are these many entries available: {len(entry_list)}")
    
    to_excel(vbat_data_list, "vBat", excel_name)

    # Save the presentation
    prs.save(os.path.join(os.getcwd(), f'Presentation_{timestamp}.pptx'))
run(input_imei, criteria)