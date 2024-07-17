import serial
import time
import pyshark
from datetime import datetime
import os
import pandas as pd
import openpyxl
from openpyxl.utils.dataframe import dataframe_to_rows
import pyautogui

# Replace 'COM9' with the correct port number for your setup.
ser = serial.Serial('COM9', 9600)

def search_bt_traffic(capfile, address):
    # Specify the file to parse
    print("Parsing:", capfile)
    cap = pyshark.FileCapture(capfile, display_filter=f'btle.advertising_address == {address}')

    traffic_found = 0
    for packet in cap:
        traffic_found += 1
        print(packet)

    if traffic_found > 0:
        print(f"Unit {address}'s traffic is captured")
    else:
        print(f"There is no traffic for unit {address}")
    return traffic_found

def set_target(channel, target):
    # Target should be in quarter-microseconds (e.g., 1500us * 4 = 6000)
    target = target * 4
    command = bytearray([0x84, channel, target & 0x7F, (target >> 7) & 0x7F])
    ser.write(command)
    print(f'Sent command to channel {channel} with target {target / 4}us')

def run_maestro(reps):
    while True:
        try:
            for i in range(reps):
                set_target(0, 1500)  # Move to 1600us
                time.sleep(1)
                set_target(0, 2300)  # Move to 2000us
                time.sleep(1)
            time.sleep(1)
        finally:
            break

def wireshark_gui(test_run_i, timestamp):
    # Swap tab to Wireshark
    pyautogui.hotkey('alt', 'tab')
    pyautogui.sleep(12)

    # Press "Capture"
    pyautogui.hotkey('alt', 'c')
    pyautogui.sleep(1)

    # Stop capturing
    pyautogui.press('enter')
    pyautogui.sleep(1)
    pyautogui.press('enter')
    pyautogui.sleep(1)

    # Save capture file
    pyautogui.hotkey('ctrl', 'shift', 's')
    pyautogui.sleep(1)
    file_name = f"capture{test_run_i}at{timestamp}.pcapng"
    pyautogui.write(file_name)
    time.sleep(1)
    pyautogui.press('tab', presses=2)
    pyautogui.sleep(1)
    pyautogui.press('enter')
    pyautogui.sleep(1)

    # Start capturing again
    pyautogui.hotkey('alt', 'c')
    pyautogui.sleep(1)
    pyautogui.press('down')
    pyautogui.sleep(1)
    pyautogui.press('enter')
    pyautogui.sleep(1)

    # Swap tab to VSCode
    pyautogui.hotkey('alt', 'tab')

    return 'captures//' + file_name


def to_excel(data_list, sheet_name, timestamp, address):
    if not data_list:
        print(f"No data to write for {sheet_name}")
        return
    df = pd.DataFrame(data_list)
    df = df[list(data_list[0].keys())]
    address_clean = address.replace(':', '_')
    new_file_path = os.path.join(os.getcwd(), f'Bending Test for {address_clean} at {timestamp}.xlsx')
    if not os.path.isfile(new_file_path):
        df.to_excel(new_file_path, index=False, sheet_name=sheet_name)
    else:
        workbook = openpyxl.load_workbook(new_file_path)
        sheet = workbook.create_sheet(sheet_name)
        for row in dataframe_to_rows(df, header=True, index=False):
            sheet.append(row)
        workbook.save(new_file_path)
        workbook.close()
    print("Excel saved")

def run():
    reps = int(input("Enter the number of bending for one set: "))
    tests = int(input("Enter the number of tests wanted: "))
    address = input("Enter the advertising address for the tested unit: ")
    if address == "":
        address = "c0:04:03:4a:72:c4"

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    data_list = []

    for i in range(tests):
        run_maestro(reps)
        cap_file = wireshark_gui(i, timestamp)
        traffic_found = search_bt_traffic(cap_file, address)
        data = {
            "Address": address,
            "Test run": i,
            "Traffic found": traffic_found
        }
        data_list.append(data)

    ser.close()
    print('Serial connection closed')

    to_excel(data_list, "Bending Test", timestamp, address)

run()