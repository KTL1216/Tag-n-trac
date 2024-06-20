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

json_file = input("Enter criteria json file name (default criteria_excursion.json): ")
if json_file == "":
    json_file = "criteria_excursion.json"
# Open the JSON file
with open(json_file, 'r') as file:
    criteria = json.load(file)

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

def get_device_shadow(device_id):
    """Retrieve and parse device shadow state."""
    response = requests.get(f"{API_BASE}/device/{device_id}/shadow", headers=common_headers2)
    shdw = response.json()
    reported, desired = None, None
    if shdw['status'] == "SUCCESS":
        if 'reported' in shdw['shadow']['state']:
            reported = shdw['shadow']['state']['reported']
        if 'desired' in shdw['shadow']['state']:
            desired = shdw['shadow']['state']['desired']
    return reported, desired

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

def compare_arrays(arr1, arr2, type):
    # Check if the arrays are of the same length
    if len(arr1) != len(arr2):
        raise ValueError("Arrays must be of the same length")

    # Initialize the boolean result and the list of differing indices
    identical = True
    differing_indices = []

    # Iterate through both arrays and compare elements
    for i in range(len(arr1)):
        if arr1[i] != arr2[i]:
            if type != "criteria" or arr2[i] is not None:
                identical = False
                differing_indices.append(i)
    
    return identical, differing_indices if len(differing_indices) > 0 else "No Differing"

def compare_dicts(dict1, dict2):
    errors = []

    # Check if both dictionaries have the same keys
    if set(dict1.keys()) != set(dict2.keys()):
        return False, ["Different keys"]

    # Compare each key's corresponding value
    for key in dict1:
        if dict1[key] != dict2[key]:
            errors.append(str(key))
    
    return len(errors) == 0

def delta_greater_than(timestamp1, timestamp2, days):
    # Convert the Unix timestamps to datetime objects
    datetime1 = datetime.fromtimestamp(timestamp1, tz=timezone.utc)
    datetime2 = datetime.fromtimestamp(timestamp2, tz=timezone.utc)
    
    # Calculate the difference between the two dates
    delta = abs(datetime2 - datetime1)
    
    # Check if the difference is greater than 40 days
    return delta > timedelta(days=days), delta

def config_26(reported, desired, days, imei):
    desired_match, unmatched_indices = compare_arrays(reported['26'], desired['26'], "desired")
    criteria_met, unmet_indices = compare_arrays(reported['26'], criteria['26'], "criteria")
    delta_greater, time_delta = delta_greater_than(reported['26'][0], reported['26'][0], days)

    data_dict = {
        "IMEI": imei,
        "Match Desired?": desired_match,
        "Unmatched Indices": unmatched_indices,
        "Meet Criteria?": criteria_met,
        "Unmet Indices": unmet_indices,
        "Time Delta Greater?": delta_greater,
        "Time Delta": time_delta
    }
    return data_dict

def config_27(reported, desired, imei):
    desired_match = compare_dicts(reported['27'], desired['27'])
    criteria_met = compare_dicts(reported['27'], criteria['27'])

    data_dict = {
        "IMEI": imei,
        "Match Desired?": desired_match,
        "Meet Criteria?": criteria_met
    }
    return data_dict

def config_33(reported, imei):
    monitor_state = reported['33'][0]
    criteria_met, unmet_indices = compare_arrays(reported['33'], criteria['33'], "criteria")
    start_time_match = reported['33'][1] == reported['26'][0]

    data_dict = {
        "IMEI": imei,
        "Monitor State": monitor_state,
        "Meet Criteria?": criteria_met,
        "Criteria State": criteria['33'][0],
        "Start Time Match 26?": start_time_match
    }
    return data_dict

def to_excel(data_list, sheet_name, timestamp):
    if not data_list:  # Check if the data_list is empty
        print(f"No data to write for {sheet_name}")
        return
    
    df = pd.DataFrame(data_list)
    df = df[list(data_list[0].keys())]
    new_file_path = os.path.join(os.getcwd(), f'Excursion Monitor {timestamp}.xlsx')
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
    days_delta = input("Enter the delta for config 26 (default 40): ")
    if days_delta == "":
        days_delta = 40

    # Read device list from file specified by the user
    with open(fname, 'r') as file:
        device_list = file.read().splitlines()
    print("reading device list: ", len(device_list))

    # An array tracking all the relevant data for all relevant devices
    data_list_26 = []
    data_list_27 = []
    data_list_33 = []
    for i, dev in enumerate(device_list):
        try:
            print(f"---\nReport for device {dev}")
            reported, desired= get_device_shadow(dev)
            data_list_26.append(config_26(reported, desired, days_delta, dev))
            data_list_27.append(config_27(reported, desired, dev))
            data_list_33.append(config_33(reported, dev))
        except:
            print(f"Error occured on: {dev}")
    
    # store data in excel file
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    to_excel(data_list_26, "26", timestamp)
    to_excel(data_list_27, "27", timestamp)
    to_excel(data_list_33, "28", timestamp)
run(fname)