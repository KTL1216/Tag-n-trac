from datetime import datetime
import json
#import matplotlib.pyplot as plt
import requests
import sys

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
fname = ""
id = "username" 
pwd = "password" 

def prompt():
    """Prompt user for username, password, and file name for device id list."""
    id = input("Your username: ")
    pwd = input("Your password: ")
    fname = input("File name for the device id list: ")
    return id, pwd, fname

# Capture user input
id, pwd, fname = prompt()

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

def get_device(device_id):
    """Retrieve device information by device ID."""
    response = requests.get(f"{API_BASE}/device/{device_id}", headers=common_headers)
    return response.json()

def get_device_data(device_id):
    """Retrieve device data by device ID."""
    response = requests.get(f"{API_BASE}/device/{device_id}/data", headers=common_headers)
    if response.json()['status'] == 'SUCCESS':
        return response.json()['response']
    else: 
        return None

def get_device_shadow(device_id):
    """Retrieve and parse device shadow state."""
    response = requests.get(f"{API_BASE}/device/{device_id}/shadow", headers=common_headers)
    shdw = response.json()
    reported, desired = None, None
    if shdw['status'] == "SUCCESS":
        if 'reported' in shdw['shadow']['state']:
            reported = shdw['shadow']['state']['reported']
        if 'desired' in shdw['shadow']['state']:
            desired = shdw['shadow']['state']['desired']
    return reported, desired

def update_device_shadow(device_id, payload):
    """Update device shadow with new configuration."""
    response = requests.post(f"{API_BASE}/device/{device_id}/shadow",
                            payload, headers=common_headers_post)
    print(response.text)
    return response.json()

def parse_device_config(shdw):
    """Display device configuration if available."""
    if shdw['status'] == "SUCCESS":
        p = shdw['shadow']['state']['reported']
        print("config: ", p["0"], p["1"], p["25"])
    else:
        print("config: missing")

def parse_device_data(data):
    """Print the number of data points received."""
    print("num points: ", len(data))

def update_config(device_list, json_params):
    """Update configuration for each device in the list."""
    for dev in device_list:
        update_device_shadow(dev, json_params)

def print_device_config(device_list):
    """Print the configuration of each device in the list."""
    for dev in device_list:
        r, d = get_device_shadow(dev)
        if r is not None:
            try:
                print("%s\t%d\t%d\t%d\t%d\t%d\t%s\t%d\t%x" % (dev, r["0"], r["1"], r["11"], r['9'], r["30"], r["25"], r['34'], r['8']))
            except Exception as e:
                print(dev + f": Exception: {str(e)}")
                pass
        else:
            print("%s\tFail"%(dev))

def check_device_config(device_list, cfg):
    """Check each device configuration for discrepancies with a reference configuration."""
    for dev in device_list:
        r, d = get_device_shadow(dev)
        if r is not None:
            diff_keys = {k: (r[k], cfg[k]) for k in cfg if k in r and r[k] != cfg[k]}
            miss_keys = {k: (cfg[k]) for k in cfg if k not in r}
            print(dev)
            if len(diff_keys):
                print("\tDiffs: ", diff_keys)
            if len(miss_keys):
                print("\tMissing: ", miss_keys)
        else:
            print(dev, "\t", "No Shadow")

# Read device list from file specified by the user
with open(fname, 'r') as fname:
    device_list = fname.read().splitlines()

print("reading device list: ", len(device_list))

print_device_config(device_list)

#update_fota(device_list)
#update_config(device_list, json.dumps({"30": 0}))
# check_device_config(device_list, chk_cfg)
for dev in device_list:
    print(f"---\nReport for device {dev}")
    
    
    dev_data = get_device_data(dev)
    parse_device_data(dev_data)



'''
typedef enum {
  AWS_CONFIG_KEY_SENSOR_INTERVAL = 0,       // 0
  AWS_CONFIG_KEY_UPLOAD_INTERVAL,           // 1
  AWS_CONFIG_KEY_OPER_MODE,                 // 2
  AWS_CONFIG_KEY_INACTIVE_MODE,             // 3
  AWS_CONFIG_KEY_PoLTE,                     // 4
  AWS_CONFIG_KEY_PoLTE_AUTH,                // 5
  AWS_CONFIG_KEY_LOG_STORAGE,               // 6
  AWS_CONFIG_KEY_CRYO_SENSOR,               // 7
  AWS_CONFIG_KEY_SENSOR_MASK,               // 8
  AWS_CONFIG_KEY_RSRP,                      // 9
  AWS_CONFIG_KEY_POLL_PERIOD,               // 10
  AWS_CONFIG_KEY_WAREHOUSE_INTERVAL,        // 11
  AWS_CONFIG_KEY_LWM2M_INTERVAL,            // 12
  AWS_CONFIG_KEY_EXC_LIMIT_LOW,             // 13
  AWS_CONFIG_KEY_EXC_LIMIT_HIGH,            // 14
  AWS_CONFIG_KEY_EXC_SAMPLE_LIMIT_LOW,      // 15
  AWS_CONFIG_KEY_EXC_SAMPLE_LIMIT_HIGH,     // 16
  AWS_CONFIG_KEY_OOB_TIME_LIMIT,            // 17
  AWS_CONFIG_KEY_GPS,                       // 18
  AWS_CONFIG_KEY_GPS_ACQ_TIME,              // 19
  AWS_CONFIG_KEY_MIN_VBAT_MV,               // 20
  AWS_CONFIG_KEY_FLIGHT_DETECTION,          // 21
  AWS_CONFIG_KEY_UPLOAD_HANDSHAKE,          // 22
  AWS_CONFIG_KEY_ACCELEROMETER_CONFIG,      // 23
  AWS_CONFIG_KEY_ACCELEROMETER_THRESHOLD,   // 24
  AWS_CONFIG_KEY_FIRMWARE_VERSION,          // 25
  AWS_CONFIG_KEY_EXCMON_SESSION_PARAM,      // 26
  AWS_CONFIG_KEY_EXCMON_DEVICE,             // 27
  AWS_CONFIG_KEY_WIFI,                      // 28
  AWS_CONFIG_KEY_DFOTA_RESULT,              // 29
  AWS_CONFIG_KEY_SCAN_SUSPEND,              // 30
  AWS_CONFIG_KEY_RTD,                       // 31
  AWS_CONFIG_KEY_FLIGHTDETECTION_THRESHOLDS,// 32
  AWS_CONFIG_KEY_EXCMON_STATUS,             // 33
  AWS_CONFIG_KEY_LTE_ATTACH_TIMEOUT,        // 34
  AWS_CONFIG_KEY_AT_COMMAND_RECEIVE,        // 35
  AWS_CONFIG_KEY_AT_COMMAND_RETURN,         // 36
  AWS_CONFIG_KEY_OP_LIMITS,                 // 37
  AWS_CONFIG_KEY_SCAN_DURATION,             // 38
  AWS_CONFIG_KEY_AWS_KEY_INDEX,             // 39
//  AWS_CONFIG_KEY_EIS_MASK,
  AWS_CONFIG_KEY_MAX
} awsConfigKey_e;
'''
