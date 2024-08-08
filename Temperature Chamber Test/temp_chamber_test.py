import pyvisa
import time
from datetime import datetime

# Create a VISA resource manager
rm = pyvisa.ResourceManager()

# List available resources
resources = rm.list_resources()
print('Available resources:', resources)

def read_agilent(instrument):
    try:
        # Clear the instrument's buffer
        instrument.clear()

        # Configure the measurement for an RTD sensor in Celsius on channel 203
        instrument.write('CONF:TEMP RTD,85,(@203)')
        
        # Enable offset compensation
        instrument.write('FRES:OCOM ON,(@203)')

        # NPLC Adjustment
        instrument.write('SENS:VOLT:DC:NPLC 1,(@203)')
                
        # Set the RTD type to 4-wire
        instrument.write('SENS:TEMP:TRAN:FRTD:TYPE 85,(@203)')

        # Initiate the measurement
        instrument.write('INIT')

        # Fetch the measurement
        reading_str = instrument.query('FETCh?')
        reading = float(reading_str.strip())
        
        # Get the current timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Print the timestamp and reading
        print(f'[{timestamp}] Reading from channel 203: {reading}')
    
    except pyvisa.errors.VisaIOError as e:
        print(f"VISA IO Error: {e}")

def run(device_name, runs, gap):
    instrument = rm.open_resource(device_name, timeout=5000)  # Increase timeout if needed
    print(f"Connected to: {instrument.query('*IDN?')}")
    
    while runs > 0:
        read_agilent(instrument)
        time.sleep(gap)
        runs -= 1
    
    # Close the connection
    instrument.close()

# Example usage with a GPIB address
device_name = 'GPIB0::9::INSTR'
run(device_name, 10, 1)