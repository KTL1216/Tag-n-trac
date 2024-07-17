from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
import os
import requests
import json
import pandas as pd
import openpyxl
from openpyxl.utils.dataframe import dataframe_to_rows
from random import randint
from time import sleep
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

API_BASE = "https://api.tagntrac.io"
orgID = "YjNKbllXNXBlbUYwYVc5dTNmNWEyNmUwLTNiYmItMTFlZS1hNzFjLTAxNWQxZjkxMWE2NA=="

# Placeholder variables for user credentials and filename
id = "username" 
pwd = "password" 

criteria = {
    "26": [None, None, 1, None, 0, 28800, 11520, None, 10, 60 ],
    "27": None,
    "33": None
}

def login2(email, password):
    login_response = requests.post(f"{API_BASE}/login?clientId=Tbocs0cjhrac",
                                   data=json.dumps({"emailId": email, "userSecret": password, "reqType": "cognitoAuth"}),
                                   headers={"Content-Type": "application/json", "Origin": "DOC.API"})
    try:
        if login_response.json()["status"] == "SUCCESS":
            print("\nLogin successful")
            return login_response.json()["idToken"], login_response.json()['clientApiKey']['clientId']
    except Exception as e:
        print(f"Exception: {str(e)}")
    print(f"Login failed: {login_response.text}")
    return None, None

# Capture user input
id, pwd = "support.cct@tagntrac.com", "Lg2&V5cR"

idToken, xapikey2 = login2(id, pwd)
common_headers2 = {"Authorization": idToken,
                   "Origin": API_BASE,
                   "x-api-key": xapikey2}

# def get_all_devices():
#     """Retrieve all devices."""
#     device_list = []
#     response = requests.get(f"https://api.tagntrac.io/organization/{orgID}/devices", headers=common_headers2)
#     for dev in response.json()['devices']:
#         if dev["deviceType"] == "CATM1_TAG":
#             device_list.append(dev["id"])
#     return device_list

def requests_retry_session(
    retries=3,
    backoff_factor=0.3,
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

def get_device_shadow(device_id):
    """Retrieve and parse device shadow state."""
    try:
        response = requests_retry_session().get(f"{API_BASE}/device/{device_id}/shadow", headers=common_headers2)
        response.raise_for_status()
        shdw = response.json()
        reported, desired = None, None
        if shdw.get('status') == "SUCCESS":
            if 'reported' in shdw['shadow']['state']:
                reported = shdw['shadow']['state']['reported']
            if 'desired' in shdw['shadow']['state']:
                desired = shdw['shadow']['state']['desired']
        return reported, desired
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
    return None, None

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
    if reported is None:
        data_dict = {
            "IMEI": imei,
            "Passed": False,
            "26 Match Desired?": "No reported data",
            "26 Unmatched Indices": "No reported data",
            "26 Meet Criteria?": "No reported data",
            "26 Unmet Indices": "No reported data",
            "26 Time Delta Greater?": "No reported data",
            "26 Time Delta": "No reported data",
            "26 Desired Abs Start Time": "No reported data"
        }
        return data_dict

    counter_id_26 = "No 26 config in desired"
    if '26' in reported and isinstance(reported['26'], list):
        if desired and '26' in desired:
            desired_match, unmatched_indices = compare_arrays(reported['26'], desired['26'], "desired")
            if len(desired['26']) > 7:  # Ensure there are at least 8 elements
                counter_id_26 = desired['26'][0]
            else:
                counter_id_26 = "Not enough elements in desired['26']"
        else:
            desired_match, unmatched_indices = "No 26 config in desired", "No 26 config in desired"
        criteria_met, unmet_indices = compare_arrays(reported['26'], criteria['26'], "criteria")
        delta_greater, time_delta = delta_greater_than(reported['26'][0], reported['26'][1], days)
        data_dict = {
            "IMEI": imei,
            "Passed": desired_match and criteria_met and not delta_greater,
            "26 Match Desired?": desired_match,
            "26 Unmatched Indices": unmatched_indices,
            "26 Meet Criteria?": criteria_met,
            "26 Unmet Indices": unmet_indices,
            "26 Time Delta Greater?": delta_greater,
            "26 Time Delta": time_delta,
            "26 Desired Abs Start Time": counter_id_26
        }
    else:
        data_dict = {
                "IMEI": imei,
                "Passed": False,
                "26 Match Desired?": "No 26 config in reported",
                "26 Unmatched Indices": "No 26 config in reported",
                "26 Meet Criteria?": "No 26 config in reported",
                "26 Unmet Indices": "No 26 config in reported",
                "26 Time Delta Greater?": "No 26 config in reported",
                "26 Time Delta": "No 26 config in reported",
                "26 Desired Abs Start Time": counter_id_26
            }
    return data_dict

def config_27(reported, desired, imei):
    if reported is None:
        data_dict = {
            "IMEI": imei,
            "27 Match Desired?": "No reported data",
            "27 Desired Counter id": "No reported data"
            #"Passed": False
        }
        return data_dict

    counter_id_27 = "No 27 config in desired"
    if '27' in reported and isinstance(reported['27'], dict):
        if desired and '27' in desired:
            desired_match = compare_dicts(reported['27'], desired['27'])
            if len(desired['27']['27.0']) > 7:  # Ensure there are at least 8 elements
                counter_id_27 = [value[7] for value in desired['27'].values()]
            else:
                counter_id_27 = "Not enough elements in desired['27']"
        else:
            desired_match = "No 27 config in desired"
        data_dict = {
            "IMEI": imei,
            "27 Match Desired?": desired_match,
            "27 Desired Counter id": counter_id_27
            #"Passed": desired_match
        }
    else:
        data_dict = {
            "IMEI": imei,
            "27 Match Desired?": "No 27 config in reported",
            "27 Desired Counter id": counter_id_27
            #"Passed": False
        }
    return data_dict

def config_33(reported, imei):
    if reported is None:
        data_dict = {
            "IMEI": imei,
            "33 Monitor State": "No reported data",
            "33 Start Time Match 26?": "No reported data",
            "33 Reported Abs Start Time": "No reported data"
            #"Passed": False
        }
        return data_dict
    if '33' in reported and reported['33'] != 0:
        monitor_state = reported['33'][0]
        if '26' in reported and isinstance(reported['26'], list):
            start_time_match = reported['33'][1] == reported['26'][0]
        else:
            start_time_match = 'No 26 config in reported'
        data_dict = {
            "IMEI": imei,
            "33 Monitor State": monitor_state,
            "33 Start Time Match 26?": start_time_match,
            "33 Reported Abs Start Time": reported['33'][1]
            #"Passed": start_time_match
        }
    else:
        data_dict = {
            "IMEI": imei,
            "33 Monitor State": "No 33 config in reported",
            "33 Start Time Match 26?": "No 33 config in reported",
            "33 Reported Abs Start Time": "No 33 config in reported"
            #"Passed": False
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
        
        combined_dict.update(config_26_data)
        combined_dict.update(config_27_data)
        combined_dict.update(config_33_data)
        
        return combined_dict
    except Exception as e:
        print(f"Error occurred on: {dev}, Exception: {e}")
        return None, None, None

def run():
    days_delta = 40
    #device_list = get_all_devices()
    fname = input("Enter IMEI list file (default imei.txt): ")
    if fname == '':
        fname = "imei.txt"
    with open(fname, 'r') as file:
        device_list = file.read().splitlines()
    print(f"Total %d devices in accout" % (len(device_list)))

    data_list = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(process_device, dev, days_delta) for dev in device_list]
        for future in as_completed(futures):
            try:
                data = future.result()
                if data:
                    data_list.append(data)
                    if len(data_list) % 100 == 0:
                        print(f"Read {len(data_list)} devices...")
            except Exception as e:
                print(f"Exception: {str(e)}")


    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    to_excel(data_list, "26, 27, 31", timestamp)

    # Count how many entries have Passed set to False
    print(f"Total {len(data_list)} units, loading data into excel...")
    failed_count = sum(1 for data in data_list if not data["Passed"])
    print(f"Number of devices that failed: {failed_count}")
run()