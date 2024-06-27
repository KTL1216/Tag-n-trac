import serial
import time
import pyshark

def capture_ble_traffic(pcap_file, source_address):
    # Setting up the display filter for BLE device address in the "Source" field
    display_filter = f'btcommon.eir_ad.entry.device_name == "{source_address}"'  # Correct display filter for BLE address
    
    # Load the capture file with the specified display filter
    capture = pyshark.FileCapture(pcap_file, display_filter=display_filter)
    
    # Enable debug mode
    capture.set_debug()
    
    try:
        found_packet = False
        for packet in capture:
            print(packet)
            found_packet = True
        if not found_packet:
            print(f"No packets found with the address {source_address}")
    except Exception as e:
        print(f"Error during packet capture: {e}")
    finally:
        capture.close()

# Example usage
capture_ble_traffic('capture1.pcapng', 'c0:04:03:45:09:0b')


# # Replace 'COM9' with the correct port number for your setup.
# ser = serial.Serial('COM9', 9600)

# def set_target(channel, target):
#     # Target should be in quarter-microseconds (e.g., 1500us * 4 = 6000)
#     target = target * 4
#     command = bytearray([0x84, channel, target & 0x7F, (target >> 7) & 0x7F])
#     ser.write(command)
#     print(f'Sent command to channel {channel} with target {target / 4}us')

# def wire_shark_test():
#     pass

# def run(reps):
#     while True:
#         try:
#             for i in range(reps):
#                 set_target(0, 1500)  # Move to 1600us
#                 time.sleep(1)
#                 set_target(0, 2300)  # Move to 2000us
#                 time.sleep(1)
#             wire_shark_test()
#             time.sleep(1)
#         finally:
#             break
#     ser.close()
#     print('Serial connection closed')

# run(10)