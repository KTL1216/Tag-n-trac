import numpy as np
import pandas as pd
import os
from datetime import datetime
import subprocess
import sys
import pyautogui
import time
import math

x_stop, y_stop = 599, 763
x_mode, y_mode = 750, 470
x_charge, y_charge = 700, 476
x_discharge, y_discharge = 670, 560
x_cm_start, y_cm_start = 774, 778

def open_programs(file_path):
    try:
        with open(file_path, 'r') as file:
            for line in file:
                # Trim newline and whitespace characters
                program_path = line.strip()
                
                # Open the program if the line is not empty
                if program_path:
                    print(f"Opening: {program_path}")
                    subprocess.Popen(program_path)
                    print(f"Opened: {program_path}")
                    time.sleep(1)
                    
    except FileNotFoundError:
        print(f"The file {file_path} was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

def set_up(file_path):
    open_programs(file_path)

def exportDE(run_index):
    pyautogui.sleep(2)

    # Moving to the 'File' menu and clicking
    pyautogui.hotkey('alt', 'f')
    pyautogui.sleep(1)

    # Moving to the 'Export' submenu and clicking
    pyautogui.press('x')
    pyautogui.sleep(1)

    # Moving to the 'CSV Asbolute' submenu and clicking
    pyautogui.press('enter')
    pyautogui.sleep(1)

    # Write File Name
    pyautogui.write(f"nimh{run_index}.csv")
    time.sleep(1)

    # Moving to the 'File Path' submenu and clicking
    pyautogui.press('tab', presses=6)
    pyautogui.sleep(1)

    # Write File Path
    pyautogui.press('enter')
    pyautogui.write(os.getcwd() + "\\csv")
    time.sleep(1)
    
    # Simulate pressing the Enter key
    pyautogui.press('enter')
    time.sleep(1)

    # Moving to the 'Save' submenu and clicking
    pyautogui.press('tab', presses=9)
    pyautogui.sleep(1)
    pyautogui.press('enter')
    time.sleep(1)

def generate_csvs(run_index):
    # In DataExplorer
    pyautogui.sleep(2)
    open_programs("programs.txt")
    pyautogui.sleep(5)
    pyautogui.hotkey('alt', 'd')
    pyautogui.sleep(1)
    pyautogui.press('enter')
    pyautogui.sleep(2)

    # Swap to Charge Master
    pyautogui.hotkey('alt', 'tab')
    pyautogui.sleep(2)

    # In Charge Master
    # Select Mode
    pyautogui.moveTo(x_mode, y_mode, duration=1)
    pyautogui.click()
    if run_index % 2 == 1:
        pyautogui.moveTo(x_charge, y_charge, duration=1)
    else:
        pyautogui.moveTo(x_discharge, y_discharge, duration=1)
    pyautogui.click()
    pyautogui.sleep(2)
    # Click Start
    x_cm_start, y_cm_start = 774, 778
    pyautogui.moveTo(x_cm_start, y_cm_start, duration=1)
    pyautogui.click()
    pyautogui.sleep(4500 if run_index % 2 == 1 else 9000)

    # Stop Charge Master 
    pyautogui.moveTo(x_stop, y_stop, duration=1)
    pyautogui.click()

    # Swap to DataExplorer
    pyautogui.hotkey('alt', 'tab') 
    pyautogui.sleep(2)

    # Stop Gathering in DataExplorer
    pyautogui.hotkey('alt', 'd')
    pyautogui.press('enter')
    pyautogui.sleep(2)
    
    exportDE(run_index)
    pyautogui.sleep(2)

    pyautogui.hotkey('ctrl', 'w')
    pyautogui.press('enter')
    pyautogui.sleep(2)

def compile_csv_to_excel(folder_path, output_excel_path):
    # Initialize an empty DataFrame to hold data from all CSV files
    compiled_data = pd.DataFrame()
    run_index = 1

    # Loop through all files in the folder
    for filename in os.listdir(folder_path):
        if filename.endswith('.csv'):
            file_path = os.path.join(folder_path, filename)
            # Initially, we don't know where the header starts, so we need to find it first
            with open(file_path, 'r', encoding='latin1') as file:
                lines = file.readlines()
                header_line_index = None

                for i, line in enumerate(lines):
                    if line.startswith('Time'):
                        header_line_index = i
                        break
                
                # If header is found, read the file from that line
                if header_line_index is not None:
                    temp_df = pd.read_csv(file_path, sep=';', header=header_line_index, encoding='latin1')
                    columns_to_keep = ['Time [hh:mm:ss.SSS]', 'Voltage [V]', 'Current [A]', 'Capacity [mAh]']
                    # Remove useless data
                    temp_df = temp_df.loc[:, columns_to_keep]

                    # Add the Run column
                    temp_df['ID'] = [sys.argv[3]] * len(temp_df)

                    # Add the Run column
                    temp_df['Run'] = [math.ceil(run_index/2)] * len(temp_df)
                    
                    # Logic to alternate between 'Charge' and 'Discharge'
                    cycle_value = 'Charge' if run_index % 2 == 1 else 'Discharge'
                    temp_df['Cycle'] = [cycle_value] * len(temp_df)

                    #read temp
                    if sys.argv[2] == 'room':
                        temp_df['Temp'] = [25] * len(temp_df)
                    else: 
                        temp_df['Temp'] = [-20] * len(temp_df)
                    compiled_data = pd.concat([compiled_data, temp_df], ignore_index=True)
                    temp_df = None
                    run_index += 1

    # Write the compiled data to an Excel file
    compiled_data.to_excel(output_excel_path, index=False)

def run():
    # Check if any arguments were passed (excluding the script name itself)
    if len(sys.argv) > 3:
        # Usage
        #set_up('programs.txt')
        for i in range(0, int(sys.argv[1])):
            generate_csvs(i+1)
        current_dir = os.getcwd() + "\\csv"
        output_excel_path = os.getcwd() + '\\output_compiled_data.xlsx'
        compile_csv_to_excel(current_dir, output_excel_path)
    else:
        print("Not enough arguments were passed.")

run()
# current_dir = os.getcwd() + "\\csv"
# output_excel_path = os.getcwd() + '\\output_compiled_data.xlsx'
# compile_csv_to_excel(current_dir, output_excel_path)