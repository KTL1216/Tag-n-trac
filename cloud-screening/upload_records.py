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

## login
API_BASE = "https://api.tagntrac.io"

id = "owen.tnt@tagntrac.com"
pwd = "Vx9%xCqf"

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
    
    data_dict = {
        'IMEI': id,
        'Sensor Samples': len(sensor_data),
        'Upload Samples': len(upload_data),
        'Top 3 Sensor Gaps': longest_sensor_gaps,
        'Top 3 Upload Gaps': longest_upload_gaps,
    }

    return data_dict

def count_decrement_num(data, data_dict):
    # check how amny times the value of count went down compared to previous sample
    decrement_counts = 0
    ts_list = []

    previous_count = None
    for i in range(len(data)-1, -1, -1):
        current_count = data[i]['count']
        if current_count is not None:
            current_count = int(current_count)  # Convert to integer only if it's not None
            if previous_count is not None:
                if current_count < previous_count:
                    decrement_counts += 1
                    ts_list.append((int(data[i]['ts'])/1000, int(data[i-1]['ts'])/1000))
            previous_count = current_count

    data_dict['Count Value Decrements'] = decrement_counts
    data_dict['Count Decrements Timestamps'] = ts_list

    return data_dict

def successive_distance(data, data_dict):
    top_3_distance = []

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
    
    data_dict['Top 3 Successive Distance'] = top_3_distance

    return data_dict


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
fname_dev = "output.txt"

def run(fname):
    hours_ago = input("Enter the time period (how many hours ago from now): ")

    # Read device list from file specified by the user
    with open(fname, 'r') as file:
        device_list = file.read().splitlines()
    print("reading device list: ", len(device_list))

    # An array tracking all the relevant data for all relevant devices
    data_list = []
    for i, dev in enumerate(device_list):
        print(f"---\nReport for device {dev}")
        data = get_device_data_v2(dev, int(hours_ago))
        if data is not None:
            data_dict = time_delta(data, dev)
            data_dict = count_decrement_num(data, data_dict)
            data_dict = successive_distance(data, data_dict)
            data_list.append(data_dict)

    # Create a dataframe
    df = pd.DataFrame(data_list)
    df = df[list(data_list[0].keys())]
    # Save dataframe as excel
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    new_file_path = os.path.join(os.getcwd(), f'Upload Records Check {timestamp}.xlsx')
    df.to_excel(new_file_path, index=False, sheet_name="Upload Records Check")

    print(f"There are these many entries available: {len(data_list)}")
run(fname_dev)