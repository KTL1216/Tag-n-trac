import serial
import binascii

# Define the COM port and baud rate
COM_PORT = 'COM3'
BAUD_RATE = 115200

# Initialize the serial connection
ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=1)

# Function to read and print data from the sniffer
def read_sniffer_data():
    while True:
        try:
            # Read a line of data from the serial port
            data = ser.readline()
            if data:
                # Convert binary data to a hex string
                hex_data = binascii.hexlify(data).decode('utf-8')
                print(f"Captured Data: {hex_data}")
        except KeyboardInterrupt:
            print("Exiting...")
            break
        except Exception as e:
            print(f"Error: {e}")
            break

# Start capturing data
if __name__ == '__main__':
    print("Starting Bluetooth sniffer...")
    read_sniffer_data()

    # Close the serial connection when done
    ser.close()
    print("Bluetooth sniffer stopped.")