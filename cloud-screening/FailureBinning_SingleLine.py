import pandas as pd
import numpy as np
from openpyxl import Workbook

# read by default 1st sheet of an excel file
df1 = pd.read_csv('cct-hold-0729.txt', header = None)
#dupedf1=df1
#df2 = pd.read_csv('cct-inactive.csv', header = None)
#dupedf2=df2


while True:
    print("\n")
    print("*****************************")
    IMEI = input("Scan the IMEI barcode: ")
    print(f"Scanned unit {IMEI}")
    if IMEI == "exit" or IMEI == "Exit" or IMEI == "EXIT" :
        #with pd.ExcelWriter('Remaining.xlsx', engine='openpyxl', mode='a') as writer:  
        #    df1.to_excel(writer,sheet_name='FOTA')
        #    df2.to_excel(writer,sheet_name='Inactive')
        
        #df3 = pd.read_csv('FOTAScanned.csv', header = None)
        #df3=df3.drop(df3.columns[0], axis=1)
        #print (df3)
        #dfdelta=df1.compare(df3)
        #dfdelta.to_csv("FOTARemaining.csv",header=False)
        
        #df3 = pd.read_csv('FOTAScanned.csv', header = None)
        #df3=df3.drop(df3.columns[0], axis=1)
        #print (df3)
        #for x in range(len(df3)) :
        #    match = df1.loc[df1[0] == df3[x]]
        #    print (match)
        #    #match.to_csv("FOTARemaining.csv",mode='a',header=False)
            
        #with open("InactiveScanned.csv") as file:
        #    for imei in file:
        #        num=imei.strip()
        #        data1=np.append(data2,num)
        #for x in range(len(data2)) :
        #    match = df2.loc[df2[0] == int(data2[x])]
        #    match.to_csv("InactiveRemaining.csv",mode='a',header=False)
    
        #print("Creating remaining devices from input list.")
        #print("Progam Done")
        exit()
    if len(df1.loc[df1[0] == int(IMEI)]) == 1 :
        match = df1.loc[df1[0] == int(IMEI)]
        match.to_csv("FOTAScanned.csv",mode='a',header=False)
        #with pd.ExcelWriter('Scanned.xlsx', engine='openpyxl', mode='a',if_sheet_exists='overlay') as writer:  
        #    match.to_excel(writer,sheet_name='FOTA')
        #df1 = df1.drop(df1[df1[0] == int(IMEI)].index)
        print ("Fail: FOTA Match")
    #if len(df2.loc[df2[0] == int(IMEI)]) == 1 :
        #match = df2.loc[df2[0] == int(IMEI)]
        #match.to_csv("InactiveScanned.csv",mode='a',header=False)
        #with pd.ExcelWriter('Scanned.xlsx', engine='openpyxl', mode='a',if_sheet_exists='overlay') as writer:
        #    match.to_excel(writer,sheet_name='Inactive')
        #df2 = df2.drop(df2[df2[0] == int(IMEI)].index)
        #print ("Fail: Inactive Match")
    if  len(df1.loc[df1[0] == int(IMEI)]) != 1 :
        print ("Pass")
    print("*****************************")