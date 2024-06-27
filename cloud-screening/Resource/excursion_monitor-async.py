import aiohttp
import asyncio
import pandas as pd
from datetime import datetime, timezone, timedelta
import json
import os
import openpyxl
from openpyxl.utils.dataframe import dataframe_to_rows

API_BASE = "https://api.tagntrac.io"
id = "username"
pwd = "password"
fname = "imei.txt"

def prompt():
    """Prompt user for username, password, and file name for device id list."""
    id = input("Enter username: ")
    pwd = input("Enter password: ")
    fname = input("Enter IMEI list file (default imei.txt): ")
    return id, pwd, fname

async def login2(session, email, password):
    async with session.post(f"{API_BASE}/login?clientId=Tbocs0cjhrac",
                             data=json.dumps({"emailId": email, "userSecret": password, "reqType": "cognitoAuth"}),
                             headers={"Content-Type": "application/json", "Origin": "DOC.API"}) as response:
        resp_json = await response.json()
        if resp_json["status"] == "SUCCESS":
            print("Login successful as ", email)
            return resp_json["idToken"], resp_json['clientApiKey']['clientId']
        print(f"Login failed: {resp_json}")
        return None, None

async def get_device_shadow(session, device_id, common_headers2):
    async with session.get(f"{API_BASE}/device/{device_id}/shadow", headers=common_headers2) as response:
        shdw = await response.json()
        reported, desired = None, None
        if shdw['status'] == "SUCCESS":
            if 'reported' in shdw['shadow']['state']:
                reported = shdw['shadow']['state']['reported']
            if 'desired' in shdw['shadow']['state']:
                desired = shdw['shadow']['state']['desired']
        return reported, desired

def generate_time_string(hours_ago):
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=hours_ago)
    start_str = start_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    end_str = end_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    return f"?start={start_str}&end={end_str}"

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

def delta_greater_than(timestamp1, timestamp2, days):
    datetime1 = datetime.fromtimestamp(timestamp1, tz=timezone.utc)
    datetime2 = datetime.fromtimestamp(timestamp2, tz=timezone.utc)
    delta = abs(datetime2 - datetime1)
    return delta > timedelta(days=days), delta

def config_26(reported, desired, days, imei):
    if '26' in reported and reported['26'] != 0:
        if desired and '26' in desired:
            desired_match, unmatched_indices = compare_arrays(reported['26'], desired['26'], "desired")
        else:
            desired_match, unmatched_indices = "No 26 config in desired", "No 26 config in desired"
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
    else:
        data_dict = {
            "IMEI": imei,
            "Match Desired?": "No 26 config in reported",
            "Unmatched Indices": "No 26 config in reported",
            "Meet Criteria?": "No 26 config in reported",
            "Unmet Indices": "No 26 config in reported",
            "Time Delta Greater?": "No 26 config in reported",
            "Time Delta": "No 26 config in reported"
        }
    return data_dict

def config_27(reported, desired, imei):
    if '27' in reported and reported['27'] != 0:
        if desired and '27' in desired:
            desired_match = compare_dicts(reported['27'], desired['27'])
        else:
            desired_match = "No 27 config in desired"
        criteria_met = compare_dicts(reported['27'], criteria['27'])
        data_dict = {
            "IMEI": imei,
            "Match Desired?": desired_match,
            "Meet Criteria?": criteria_met
        }
    else:
        data_dict = {
            "IMEI": imei,
            "Match Desired?": "No 27 config in reported",
            "Meet Criteria?": "No 27 config in reported"
        }
    return data_dict

def config_33(reported, imei):
    if '33' in reported and reported['33'] != 0:
        monitor_state = reported['33'][0]
        criteria_met, unmet_indices = compare_arrays(reported['33'], criteria['33'], "criteria")
        if '26' in reported and reported['26'] != 0:
            start_time_match = reported['33'][1] == reported['26'][0]
        else:
            start_time_match = 'No 26 config in reported'
        data_dict = {
            "IMEI": imei,
            "Monitor State": monitor_state,
            "Meet Criteria?": criteria_met,
            "Criteria State": criteria['33'][0],
            "Start Time Match 26?": start_time_match
        }
    else:
        data_dict = {
            "IMEI": imei,
            "Monitor State": "No 33 config in reported",
            "Meet Criteria?": "No 33 config in reported",
            "Criteria State": "No 33 config in reported",
            "Start Time Match 26?": "No 33 config in reported"
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

async def run(fname):
    days_delta = input("Enter the delta for config 26 (default 40): ")
    if days_delta == "":
        days_delta = 40
    with open(fname, 'r') as file:
        device_list = file.read().splitlines()
    print("reading device list: ", len(device_list))

    data_list_26 = []
    data_list_27 = []
    data_list_33 = []
    async with aiohttp.ClientSession() as session:
        idToken, xapikey2 = await login2(session, id, pwd)
        if idToken is None or xapikey2 is None:
            print("Login failed. Exiting.")
            return
        common_headers2 = {"Authorization": idToken,
                           "Origin": f"{API_BASE}",
                           "x-api-key": xapikey2}
        tasks = []
        for i, dev in enumerate(device_list):
            tasks.append(asyncio.create_task(get_device_shadow(session, dev, common_headers2)))
        
        results = await asyncio.gather(*tasks)
        
        for i in range(len(device_list)):
            dev = device_list[i]
            reported, desired = results[i]
            data_list_26.append(config_26(reported, desired, days_delta, dev))
            data_list_27.append(config_27(reported, desired, dev))
            data_list_33.append(config_33(reported, dev))
            # try:
            #     dev = device_list[i]
            #     reported, desired = results[i]
            #     data_list_26.append(config_26(reported, desired, days_delta, dev))
            #     data_list_27.append(config_27(reported, desired, dev))
            #     data_list_33.append(config_33(reported, dev))
            # except Exception as e:
            #     print(f"Error occurred on {dev}: {e}")

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    to_excel(data_list_26, "26", timestamp)
    to_excel(data_list_27, "27", timestamp)
    to_excel(data_list_33, "33", timestamp)

if __name__ == "__main__":
    id, pwd, fname = prompt()
    if not fname:
        fname = "imei.txt"
    json_file = input("Enter criteria json file name (default criteria_excursion.json): ")
    if json_file == "":
        json_file = "criteria_excursion.json"
    # Open the JSON file
    with open(json_file, 'r') as file:
        criteria = json.load(file)
    asyncio.run(run(fname))