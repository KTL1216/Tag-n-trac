from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
import os
import requests
import json
import pandas as pd
import openpyxl
from openpyxl.utils.dataframe import dataframe_to_rows

API_BASE = "https://api.tagntrac.io"

# Placeholder variables for user credentials and filename
id = "username" 
pwd = "password" 

def prompt():
    """Prompt user for username, password, and file name for device id list."""
    id = input("Enter username: ")
    pwd = input("Enter password: ")
    fname = input("Enter IMEI list file (default imei.txt): ")
    return id, pwd, fname

def login2(email, password):
    login_response = requests.post(f"{API_BASE}/login?clientId=Tbocs0cjhrac",
                                   data=json.dumps({"emailId": email, "userSecret": password, "reqType": "cognitoAuth"}),
                                   headers={"Content-Type": "application/json", "Origin": "DOC.API"})
    try:
        if login_response.json()["status"] == "SUCCESS":
            print("Login successful as ", email)
            return login_response.json()["idToken"], login_response.json()['clientApiKey']['clientId']
    except Exception as e:
        print(f"Exception: {str(e)}")
    print(f"Login failed: {login_response.text}")
    return None, None

# Capture user input
id, pwd, fname = prompt()
if fname == "":
    fname = "imei.txt"

idToken, xapikey2 = login2(id, pwd)
common_headers2 = {"Authorization": idToken,
                   "Origin": API_BASE,
                   "x-api-key": xapikey2}

json_file = input("Enter criteria json file name (default criteria_excursion.json): ")
if json_file == "":
    json_file = "criteria_excursion.json"
# Open the JSON file
with open(json_file, 'r') as file:
    criteria = json.load(file)

def generate_time_string(hours_ago):
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=hours_ago)
    start_str = start_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    end_str = end_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    result_string = f"?start={start_str}&end={end_str}"
    return result_string

def get_device_shadow(device_id):
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
    response = requests.get(f"{API_BASE}/v2/device/{device_id}/data" + queryDates, headers=common_headers2)
    if response.json()['status'] == 'SUCCESS':
        return response.json()['response']
    else:
        print("Get Device data2 failed: " + device_id)
        return None

def compare_arrays(arr1, arr2, type):
    if len(arr1) != len(arr2):
        return False, "Arrays are different in length"
    identical = True
    differing_indices = []
    for i in range(len(arr1)):
        if arr1[i] != arr2[i]:
            if type != "criteria" or arr2[i] is not None:
                identical = False
                differing_indices.append(i)
    return identical, differing_indices if len(differing_indices) > 0 else "No Differing"

def compare_dicts(dict1, dict2):
    errors = []
    if set(dict1.keys()) != set(dict2.keys()):
        return False
    for key in dict1:
        if dict1[key] != dict2[key]:
            errors.append(str(key))
    return len(errors) == 0

def is_valid_timestamp(timestamp):
    # Valid Unix timestamps should be within a reasonable range
    min_timestamp = 0
    # Dynamically calculate the maximum allowable timestamp as current time + a buffer (e.g., 10 years)
    max_timestamp = datetime.now(timezone.utc).timestamp() + (10 * 365 * 24 * 60 * 60)
    return min_timestamp <= timestamp <= max_timestamp

def delta_greater_than(timestamp1, timestamp2, days):
    if not is_valid_timestamp(timestamp1) or not is_valid_timestamp(timestamp2):
        return False, "Invalid Timestamp"
    datetime1 = datetime.fromtimestamp(timestamp1, tz=timezone.utc)
    datetime2 = datetime.fromtimestamp(timestamp2, tz=timezone.utc)
    delta = abs(datetime2 - datetime1)
    return delta > timedelta(days=days), delta


def config_26(reported, desired, days, imei):
    if '26' in reported and isinstance(reported['26'], list):
        if desired and '26' in desired:
            desired_match, unmatched_indices = compare_arrays(reported['26'], desired['26'], "desired")
        else:
            desired_match, unmatched_indices = "No 26 config in desired", "No 26 config in desired"
        criteria_met, unmet_indices = compare_arrays(reported['26'], criteria['26'], "criteria")
        delta_greater, time_delta = delta_greater_than(reported['26'][0], reported['26'][1], days)
        data_dict = {
            "IMEI": imei,
            "26 Match Desired?": desired_match,
            "26 Unmatched Indices": unmatched_indices,
            "26 Meet Criteria?": criteria_met,
            "26 Unmet Indices": unmet_indices,
            "26 Time Delta Greater?": delta_greater,
            "26 Time Delta": time_delta,
            "Passed": desired_match and criteria_met and not delta_greater
        }
    else:
        data_dict = {
            "IMEI": imei,
            "26 Match Desired?": "No 26 config in reported",
            "26 Unmatched Indices": "No 26 config in reported",
            "26 Meet Criteria?": "No 26 config in reported",
            "26 Unmet Indices": "No 26 config in reported",
            "26 Time Delta Greater?": "No 26 config in reported",
            "26 Time Delta": "No 26 config in reported",
            "Passed": False
        }
    return data_dict

def config_27(reported, desired, imei):
    if '27' in reported and isinstance(reported['27'], dict):
        if desired and '27' in desired:
            desired_match = compare_dicts(reported['27'], desired['27'])
        else:
            desired_match = "No 27 config in desired"
        criteria_met = compare_dicts(reported['27'], criteria['27'])
        data_dict = {
            "IMEI": imei,
            "27 Match Desired?": desired_match,
            "27 Meet Criteria?": criteria_met,
            "Passed": desired_match and criteria_met
        }
    else:
        data_dict = {
            "IMEI": imei,
            "27 Match Desired?": "No 27 config in reported",
            "27 Meet Criteria?": "No 27 config in reported",
            "Passed": False
        }
    return data_dict

def config_33(reported, imei):
    if '33' in reported and reported['33'] != 0:
        monitor_state = reported['33'][0]
        criteria_met, unmet_indices = compare_arrays(reported['33'], criteria['33'], "criteria")
        if '26' in reported and isinstance(reported['26'], list):
            start_time_match = reported['33'][1] == reported['26'][0]
        else:
            start_time_match = 'No 26 config in reported'
        data_dict = {
            "IMEI": imei,
            "33 Monitor State": monitor_state,
            "33 Meet Criteria?": criteria_met,
            "33 Criteria State": criteria['33'][0],
            "33 Start Time Match 26?": start_time_match,
            "Passed": criteria_met and start_time_match
        }
    else:
        data_dict = {
            "IMEI": imei,
            "33 Monitor State": "No 33 config in reported",
            "33 Meet Criteria?": "No 33 config in reported",
            "33 Criteria State": "No 33 config in reported",
            "33 Start Time Match 26?": "No 33 config in reported",
            "Passed": False
        }
    return data_dict

def to_excel(data_list, sheet_name, timestamp):
    if not data_list:
        print(f"No data to write for {sheet_name}")
        return
    df = pd.DataFrame(data_list)
    df = df[list(data_list[0].keys())]
    new_file_path = os.path.join(os.getcwd(), f'Excursion Monitor {timestamp}.xlsx')
    if not os.path.isfile(new_file_path):
        df.to_excel(new_file_path, index=False, sheet_name=sheet_name)
    else:
        workbook = openpyxl.load_workbook(new_file_path)
        sheet = workbook.create_sheet(sheet_name)
        for row in dataframe_to_rows(df, header=True, index=False):
            sheet.append(row)
        workbook.save(new_file_path)
        workbook.close()

def process_device(dev, days_delta):
    try:
        reported, desired = get_device_shadow(dev)
        combined_dict = {}
        
        config_26_data = config_26(reported, desired, days_delta, dev)
        config_27_data = config_27(reported, desired, dev)
        config_33_data = config_33(reported, dev)

        passed = config_26_data["Passed"] and config_27_data["Passed"] and config_33_data["Passed"]
        
        combined_dict.update(config_26_data)
        combined_dict.update(config_27_data)
        combined_dict.update(config_33_data)

        combined_dict.pop("Passed")
        combined_dict["Passed"] = passed
        
        return combined_dict
    except Exception as e:
        print(f"Error occurred on: {dev}, Exception: {e}")
        return None, None, None

def run(fname):
    days_delta = input("Enter the delta for config 26 (default 40): ")
    if days_delta == "":
        days_delta = 40
    else:
        days_delta = int(days_delta)

    with open(fname, 'r') as file:
        device_list = file.read().splitlines()
    print("Reading device list: ", len(device_list))

    data_list = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(process_device, dev, days_delta) for dev in device_list]
        for future in as_completed(futures):
            data = future.result()
            if data:
                data_list.append(data)

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    to_excel(data_list, "26, 27, 31", timestamp)

    # Count how many entries have Passed set to False
    failed_count = sum(1 for data in data_list if not data["Passed"])
    print(f"Number of devices that failed: {failed_count}")
run(fname)