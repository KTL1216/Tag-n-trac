#!/usr/bin/env python
# coding: utf-8

import os
import re
import pandas as pd
from openpyxl import load_workbook
import openpyxl
from openpyxl.utils.dataframe import dataframe_to_rows

# Initialize data dictionaries
data_dict = {}
data = []
logdir=os.getcwd()

# Create Error Folder if not exists
error_folder_path = os.path.join(logdir, "Error Folder")
if not os.path.exists(error_folder_path):
    os.makedirs(error_folder_path)

def time_format(string):
    ans = string.split("-")[0]+string.split("-")[1]+string.split("-")[2]
    return ans

for file in os.listdir(logdir+"\\ASSY-MMI\\"):
    # Get unit id
    unit_id = file.split('_')[0]
    time_stamp = int(time_format(file.split('_')[1])+time_format(file.split('_')[2]))
    file_path = "ASSY-MMI\\" + file
    f = open(file_path, 'r')
    try:
        lines = f.readlines()
        for line in lines:
            if re.search('Quick charge test with battery:', line):
                string=line.split(":")
                charge_current = string[1].split("\n")[0]
        
        # Check for duplicate IDs
        contained = False
        for unit in data:
            if unit["Unit ID"] == unit_id:
                contained = True
                if unit["Timestamp"] < time_stamp:
                    unit["Charge Current"] = charge_current
        if not contained:
            data_dict = {
                "Unit ID": unit_id,
                "Charge Current": charge_current,
                "Timestamp": time_stamp
            }
            data.append(data_dict)
    except Exception as e:
        f.close()
        # Move this file to directory "Error Folder"
        print(f"Error occurred on file: {file}. {str(e)}")
        error_file_path = os.path.join(error_folder_path, file)
        os.rename(file_path, error_file_path)
print(len(data))

# Create a dataframe
df = pd.DataFrame(data)
df = df[['Unit ID','Charge Current', 'Timestamp']]
# Save dataframe as excel
if os.path.isfile(logdir+'\\Summary.xlsx') == False:
    df.to_excel(logdir+"\\Summary.xlsx", index=False)
else:
    workbook = openpyxl.load_workbook(logdir+'\\Summary.xlsx')  # load workbook if already exists
    sheet = workbook['Sheet1']  # declare the active sheet 
    # append the dataframe results to the current excel file
    for row in dataframe_to_rows(df, header = False, index = False):
        sheet.append(row)
    workbook.save(logdir+'\\Summary.xlsx')  # save workbook
    workbook.close()  # close workbook

