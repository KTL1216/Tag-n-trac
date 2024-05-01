# coord finder
import pyautogui
import time

while True:
    x, y = pyautogui.position()
    print(f"Position: {x}, {y}")
    time.sleep(2)

#file button 20, 44
#export button 20, 290
#csv absolute 325, 290
#file path 423, 137
#save button 743 621

# import os

# # For Windows
# os.system('start DataExplorer.exe')

#program opner
# import subprocess
# import time

# def open_programs_from_file(file_path):
#     try:
#         with open(file_path, 'r') as file:
#             for line in file:
#                 # Trim newline and whitespace characters
#                 program_path = line.strip()
                
#                 # Open the program if the line is not empty
#                 if program_path:
#                     print(f"Opening: {program_path}")
#                     subprocess.Popen(program_path)
#                     print(f"Opened: {program_path}")
#                     time.sleep(1)
                    
#     except FileNotFoundError:
#         print(f"The file {file_path} was not found.")
#     except Exception as e:
#         print(f"An error occurred: {e}")

# if __name__ == "__main__":
#     file_path = 'programs.txt'
#     open_programs_from_file(file_path)

#argument test
# import sys
# print(int(sys.argv[1]))