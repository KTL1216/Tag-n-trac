import numpy as np
import pandas as pd
import os
from datetime import datetime
import subprocess
import pyautogui
import time

# file button 20, 44
# export button 20, 290
# csv absolute 325, 290
# file path 423, 137
# save button 743 621
# x_file, y_file = 20, 44
# x_export, y_export = 20, 290
# x_csv, y_csv = 325, 290
# x_path, y_path = 423, 137
# x_save, y_save = 743, 621

# for i in range(0, 3):
#     # Open Data Explorer and move it to top right
#     pyautogui.sleep(10)

#     # Moving to the 'File' menu and clicking
#     pyautogui.hotkey('alt', 'f')
#     pyautogui.sleep(1)

#     # Moving to the 'Export' submenu and clicking
#     pyautogui.press('x')
#     pyautogui.sleep(1)

#     # Moving to the 'CSV Asbolute' submenu and clicking
#     pyautogui.press('enter')
#     pyautogui.sleep(1)

#     # Write File Name
#     pyautogui.write(f"nimh{i}.csv")
#     time.sleep(1)

#     # Moving to the 'File Path' submenu and clicking
#     pyautogui.press('tab', presses=6)
#     pyautogui.sleep(1)

#     # Write File Path
#     pyautogui.press('enter')
#     pyautogui.write('C:\\Users\\kenth\\OneDrive\\Desktop\\nimh_batttery_charge\\csv')
#     time.sleep(1)
    
#     # Simulate pressing the Enter key
#     pyautogui.press('enter')
#     time.sleep(1)

#     # Moving to the 'Save' submenu and clicking
#     pyautogui.press('tab', presses=9)
#     pyautogui.sleep(1)
#     pyautogui.press('enter')
#     time.sleep(1)


def compile_csv_to_excel(folder_path, output_excel_path):
    # Initialize an empty DataFrame to hold data from all CSV files
    compiled_data = pd.DataFrame()

    # Define the header titles to identify the header line
    header_titles = ['Time', 'Voltage', 'Current', 'Capacity']

    # Loop through all files in the folder
    for filename in os.listdir(folder_path):
        if filename.endswith('.csv'):
            file_path = os.path.join(folder_path, filename)
            # Initially, we don't know where the header starts, so we need to find it first
            with open(file_path, 'r') as file:
                lines = file.readlines()
                for i, line in enumerate(lines):
                    # Check if the line contains all header titles, indicating it's the header line
                    if all(title in line for title in header_titles):
                        # We've found the header, now let's read from this line onwards as the dataframe
                        temp_df = pd.read_csv(file_path, sep=';', header=i)
                        break

            # Append the data to the compiled DataFrame, ignoring if temp_df is not defined
            if 'temp_df' in locals():
                compiled_data = pd.concat([compiled_data, temp_df], ignore_index=True)
                del temp_df  # Clean up for the next file

    # Write the compiled data to an Excel file
    compiled_data.to_excel(output_excel_path, index=False)

# Example usage
current_dir = os.getcwd() + "\\csv"
output_excel_path = os.getcwd() + '\\output_compiled_data.xlsx'
compile_csv_to_excel(current_dir, output_excel_path)
