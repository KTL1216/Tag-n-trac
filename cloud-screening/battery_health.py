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


def get_device_data_v2(device_id, hours_ago):
    queryDates = generate_time_string(hours_ago)
    print(queryDates)
    response = requests.get(f"{API_BASE}/v2/device/{device_id}/data"+queryDates,
                            headers=common_headers2)
    if response.json()['status'] == 'SUCCESS':
        data = response.json()['response']
        return data
    else: 
        print("Get Device data2 failed: "+device_id)
        return None

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


fname_dev = "output.txt"


def run(fname):
    hours_ago = input("Enter the time period (how many hours ago from now): ")

    # Read device list from file specified by the user
    with open(fname, 'r') as file:
        device_list = file.read().splitlines()
    print("reading device list: ", len(device_list))

    # An array tracking all the relevant data for all relevant devices
    data_list = []
    group_list = []
    entry_list = []
    slide_count = 0
    for i, dev in enumerate(device_list):
        print(f"---\nReport for device {dev}")
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
                        data_list.append(data_dict)
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
    
    # Create a dataframe
    df = pd.DataFrame(data_list)
    df = df[list(data_list[0].keys())]
    # Save dataframe as excel
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    new_file_path = os.path.join(os.getcwd(), f'Battery Health {timestamp}.xlsx')
    df.to_excel(new_file_path, index=False, sheet_name="vBat Check")

    # Convert 'Time passed since Reported' into hours for plotting
    df['Hours Since Reported'] = df['Time passed since Reported'].apply(convert_to_hours)

    # Save the presentation
    prs.save(os.path.join(os.getcwd(), f'Presentation_{timestamp}.pptx'))
run(fname_dev)