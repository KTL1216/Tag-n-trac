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

## login
API_BASE = "https://api.tagntrac.io"

# Placeholder variables for user credentials and filename
fname = ""
id = "username" 
pwd = "password" 
def prompt():
    """Prompt user for username, password, and file name for device id list."""
    id = input("Enter username: ")
    pwd = input("Enter password: ")
    fname = input("Enter IMEI list file (default imei.txt)")
    return id, pwd, fname

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

# Capture user input
id, pwd, fname = prompt()
if fname == "":
    fname = "imei.txt"

idToken, xapikey2 = login2(id, pwd)
common_headers2 = {"Authorization" : idToken,
                  "Origin" : f"{API_BASE}",
                  "x-api-key" : xapikey2}

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

def get_device_shadow_reported(device_id):
    """Retrieve and parse device shadow state."""
    response = requests.get(f"{API_BASE}/device/{device_id}/shadow", headers=common_headers2)
    shdw = response.json()
    reported = None
    if shdw['status'] == "SUCCESS":
        if 'reported' in shdw['shadow']['state']:
            reported = shdw['shadow']['state']['reported']
    return reported

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
            "Time Delta": item[2],
            "Sortable Mins Delta": float(convert_to_seconds(item[2]))/60.0
        }
        sensor_delta.append(data_dict)

    for item in longest_upload_gaps:
        data_dict = {
            'IMEI': id,
            'Upload Samples': len(upload_data),
            "Previous Timestamp": str(item[0]),
            "Report TimeStamp": str(item[1]),
            "Time Delta": item[2],
            "Sortable Mins Delta": float(convert_to_seconds(item[2]))/60.0
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
                        "Previous Count": previous_count,
                        "Reported Count": current_count
                    }
                    answer.append(data_dict)
            previous_count = current_count

    return answer

def successive_distance(data, id, speed_limit):
    distances = []
    answer = []

    for i in range(1, len(data)):
        previous_ts_ms = int(data[i]['ts'])
        previous_ts_s = previous_ts_ms / 1000
        previous_time = datetime.fromtimestamp(previous_ts_s, timezone.utc)
        previous_coord = (float(data[i]['lat']), float(data[i]['lng']))

        current_ts_ms = int(data[i-1]['ts'])
        currents_ts_s = current_ts_ms / 1000
        current_time = datetime.fromtimestamp(currents_ts_s, timezone.utc)
        current_coord = (float(data[i-1]['lat']), float(data[i-1]['lng']))

        time_difference = current_time - previous_time
        if time_difference.total_seconds() > 0:
            distances.append([previous_ts_s, currents_ts_s, float(geodesic(previous_coord, current_coord).miles),
                              float(geodesic(previous_coord, current_coord).miles) / (float(time_difference.total_seconds())/3600)])
        
    for item in distances:
        if item[3] >= 60:
            data_dict = {
                "IMEI": id,
                "Previous Timestamp": str(item[0]),
                "Report TimeStamp": str(item[1]),
                "Distance (Mi)": item[2],
                "Speed (Mph)": item[3]
            }
            answer.append(data_dict)

    return answer


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

def to_excel(data_list, sheet_name, timestamp):
    if not data_list:  # Check if the data_list is empty
        print(f"No data to write for {sheet_name}")
        return
    
    df = pd.DataFrame(data_list)
    df = df[list(data_list[0].keys())]
    new_file_path = os.path.join(os.getcwd(), f'Upload Records Check {timestamp}.xlsx')
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

def run(fname):
    hours_ago = input("Enter the time period in hours (default 72): ")
    if hours_ago == "":
        hours_ago = 72

    # Read device list from file specified by the user
    with open(fname, 'r') as file:
        device_list = file.read().splitlines()
    print("reading device list: ", len(device_list))

    speed_limit = input("Enter speed limit for successive reports (default 60mph): ")
    if speed_limit == "":
        speed_limit = 60

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
            distances_list += successive_distance(data, dev, speed_limit)
    
    # store data in excel file
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    to_excel(sensor_delta_list, "Sensor Samples", timestamp)
    to_excel(upload_delta_list, "Upload Samples", timestamp)
    to_excel(count_decrement_list, "Count Decrements", timestamp)
    to_excel(distances_list, "Distance", timestamp)
run(fname)