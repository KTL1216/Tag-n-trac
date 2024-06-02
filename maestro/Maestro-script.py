import serial
import time
import pyshark

# Replace 'COM9' with the correct port number for your setup.
ser = serial.Serial('COM9', 9600)

def set_target(channel, target):
    # Target should be in quarter-microseconds (e.g., 1500us * 4 = 6000)
    target = target * 4
    command = bytearray([0x84, channel, target & 0x7F, (target >> 7) & 0x7F])
    ser.write(command)
    print(f'Sent command to channel {channel} with target {target / 4}us')

def wire_shark_test():
    pass

def run(reps):
    while True:
        try:
            for i in range(reps):
                set_target(0, 1500)  # Move to 1600us
                time.sleep(1)
                set_target(0, 2300)  # Move to 2000us
                time.sleep(1)
            wire_shark_test()
            time.sleep(1)
        finally:
            break
    ser.close()
    print('Serial connection closed')