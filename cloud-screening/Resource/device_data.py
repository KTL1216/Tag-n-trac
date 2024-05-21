import pandas as pd
import numpy as np
import os
from pathlib import Path
from datetime import datetime
import json
import requests

## login
API_BASE = "https://api.tagntrac.io"


id = "owen.tnt@tagntrac.com"
pwd = "Vx9%xCqf"


def login(email, password):
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

token, xapikey = login(id, pwd)
common_headers = {"Authorization" : token,
                  "Origin" : f"{API_BASE}",
                  "x-api-key" : xapikey}

idToken, xapikey2 = login2(id, pwd)
common_headers2 = {"Authorization" : idToken,
                  "Origin" : f"{API_BASE}",
                  "x-api-key" : xapikey2}

queryDates = ""
## to specify data range
#queryDates = "?start=2024-03-15T10:00:00.000Z&end=2024-03-17T10:00:00.000Z"

def get_device_data_v2(device_id):
    response = requests.get(f"{API_BASE}/v2/device/{device_id}/data"+queryDates,
                            headers=common_headers2)
    if response.json()['status'] == 'SUCCESS':
        return response.json()['response']
    else: 
        print("Get Device data2 failed: "+device_id)
        return None

    
#device_list = ['868617060222892']
fname_dev = "tmp.csv"


with open(fname_dev, 'r') as fname:
    device_list = fname.read().splitlines()
print("Number of devices: ", len(device_list))

for dev in device_list[:]:
    print(f"---\nReport for device {dev}")
    #dev_shdw = get_device_shadow(dev)
    #parse_device_config(dev_shdw)
    data = get_device_data_v2(dev)
    #parse_device_data(dev_data)
    df = pd.DataFrame(data)


    df['ts'] = df['ts'].astype(int).floordiv(1000)
    df['time'] = pd.to_datetime(df['ts'], unit='s')

    df_cell = df[df['rsrp'].notnull()].drop(columns=['accX', 'evnts', 'vbat', 'accY', 'accZ', 'prs', 'h', 'tm', 'prb'])
    df_s = df[['ts', 'lat', 'lng', 'tm', 'prs', 'vbat', 'evnts', 'accX', 'accY', 'accZ']]
    df_s = df_s.sort_values(by=['ts'], ascending=True, ignore_index=True)
    print("\t Samples: %d Uploads %d" % (len(df_s), len(df_cell)))

df
