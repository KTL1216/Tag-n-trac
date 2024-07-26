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

    data_list = []
    traffic_found = 0
    for packet in cap:
        traffic_found += 1
        voltage_hex = str(packet.btle.btcommon_eir_ad_entry_data.split(':')[11])+str(packet.btle.btcommon_eir_ad_entry_data.split(':')[12])
        data_dict = {
            'Address': address,
            'Test Temp[C]': 25,
            'Packet Seq Number': int(packet.nordic_ble.packet_counter),
            'Payload [Byte]': int(packet.captured_length),
            'Channel': int(packet.nordic_ble.channel),
            'RSSI [dBm]': int(packet.nordic_ble.rssi),
            'Adv Address': str(packet.btle.advertising_address),
            'Temp [Hex]': '',
            'Temp [Decimal]': '',
            'Tamper Event': '',
            'Voltage Payload': int(voltage_hex, 16)
        }
        if packet.captured_length == '56':
            list=[packet.btle.btcommon_eir_ad_entry_data[9:11],packet.btle.btcommon_eir_ad_entry_data[12:14]]
            s=""
            s=s.join(list)
            data_dict['Temp [Hex]'] = s
            
            #print(int(s,16))
            if int(s,16) < 32767:   #16 bit max positive value
                data_dict['Temp [Decimal]'] = 0.003906*int(s,16)     
            else:
                data_dict['Temp [Decimal]'] = 0.003906*(int(s,16)-4096)
            data_dict['Tamper Event'] = int(packet.btle.btcommon_eir_ad_entry_data[6:8])
        data_list.append(data_dict)
        # print(packet)

    if traffic_found > 0:
        print(f"Unit {address}'s traffic is captured")
    else:
        print(f"There is no traffic for unit {address}")
    return traffic_found, data_list

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
    pyautogui.sleep(30)

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


def to_excel(data_list, sheet_name, timestamp, is_summary):
    if not data_list:
        print(f"No data to write for {sheet_name}")
        return
    df = pd.DataFrame(data_list)
    df = df[list(data_list[0].keys())]
    if not is_summary:
        sheet_name = sheet_name.replace(':', '_')
    new_file_path = os.path.join(os.getcwd(), f'Bending Test at {timestamp}.xlsx')
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
        address = "C0:04:03:4A:6F:D7"

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    summary_list = []
    lists_of_data = {}

    for i in range(tests):
        if address not in lists_of_data:
            lists_of_data[address] = []
        run_maestro(reps)
        cap_file = wireshark_gui(i, timestamp)
        traffic_found, data_list = search_bt_traffic(cap_file, address)
        summary = {
            "Address": address,
            "Test run": i,
            "Traffic found": traffic_found
        }
        summary_list.append(summary)
        lists_of_data[address] += data_list

    ser.close()
    print('Serial connection closed')

    to_excel(summary_list, "Bending Test", timestamp, True)
    for key in lists_of_data.keys():
        to_excel(lists_of_data[key], key, timestamp, False)

run()