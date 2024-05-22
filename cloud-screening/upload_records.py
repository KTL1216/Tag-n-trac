from datetime import datetime, timezone
import os
import re
import sys
import json
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

def total_distance_travel(coords):
    total_distance = 0.0
    # Iterate through the list of coordinates
    for i in range(1, len(coords)):
        # Calculate the distance between consecutive coordinates
        distance = geodesic(coords[i-1], coords[i]).miles
        total_distance += distance
    return total_distance

def calculate_expected_uploads(hours_ago, dev, criteria):
    mins_ago = int(hours_ago) * 60
    interval = -1
    if criteria["Warehouse Interval"] and criteria["Warehouse Interval"] !=  0:
        interval = criteria["Warehouse Interval"]
    elif criteria["Upload Interval"] and criteria["Upload Interval"] !=  0:
        interval = criteria["Upload Interval"]
    
    return mins_ago//interval
 
def get_coord_list(data):
    list = []
    for entry in data:
        list.append((float(entry['lat']), float(entry['lng'])))
    return list

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

fname_dev = "output.txt"

def run(fname):
    hours_ago = input("Enter the time period (how many hours ago from now): ")

    # Read device list from file specified by the user
    with open(fname, 'r') as file:
        device_list = file.read().splitlines()
    print("reading device list: ", len(device_list))

    json_file = input("Enter criteria json file name: ")
    # Open the JSON file
    with open(json_file, 'r') as file:
        criteria = json.load(file)

    # An array tracking all the relevant data for all relevant devices
    data_list = []
    for i, dev in enumerate(device_list):
        print(f"---\nReport for device {dev}")
        data = get_device_data_v2(dev, int(hours_ago))
        # for k, v in data[1].items():
        #     print(k, v)
        if data is not None:
            expected_uploads = calculate_expected_uploads(hours_ago, dev, criteria)
            coordinates = get_coord_list(data)
            data_dict = {
                "IMEI": dev,
                "Uploads Number": len(data),
                "Min Expected uploads": expected_uploads,
                "Total Distance Traveled (Miles)": total_distance_travel(coordinates)
            }
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