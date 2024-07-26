import pyvisa

try:
    # Create a resource manager
    rm = pyvisa.ResourceManager()

    # Replace with your device's resource string
    resource_string = 'GPIBO::9:INSTR'

    # Open a connection to the device
    instrument = rm.open_resource(resource_string)

    # Query the instrument's identity (IDN)
    idn_response = instrument.query('*IDN?')
    print('Instrument ID:', idn_response)

    # Example: Set channel and read data (replace with appropriate commands for your device)
    # Set the measurement configuration (example command, consult your device's manual)
    instrument.write('CONF:VOLT:DC AUTO')
    instrument.write('ROUT:CHAN:OPEN:ALL')  # Open all channels
    instrument.write('ROUT:CHAN:CLOS (@101)')  # Close channel 101

    # Read the data
    data = instrument.query('READ?')
    print('Measurement data:', data)

    # Close the connection
    instrument.close()
except pyvisa.VisaIOError as e:
    print(f'VISA I/O Error: {e}')
except Exception as e:
    print(f'Error: {e}')