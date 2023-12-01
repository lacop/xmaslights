import serial
import sdnotify
import sys
import time

import show

# First and last 10 pixels of every 100 pixel strip are not used.
OFFSETS = [10, 110, 210]
PIXELS_PER_STRIP = 80

serial_port = serial.Serial('/dev/ttyACM1', timeout=0)

notify = sdnotify.SystemdNotifier()
notify.notify('READY=1')
notify.notify('STATUS=Initialized')

read_buffer = bytes()
def read_serial():
    global read_buffer
    if serial_port.in_waiting == 0:
        return
    read_buffer += serial_port.read(serial_port.in_waiting)
    while True:
        newline = read_buffer.find(b'\n')
        if newline == -1:
            break
        line = read_buffer[:newline]
        read_buffer = read_buffer[newline+1:]
        print('From serial:', line.decode('ascii'))
        # TODO parse line & update internal state

def write_colors(colors):
    # TODO fill blank pixels with white to warm up?
    buffer = [0 for _ in range(3*300)]
    for i in range(len(OFFSETS)):
        for j in range(PIXELS_PER_STRIP):
            buffer[3*(OFFSETS[i] + j) + 0] = colors[i*PIXELS_PER_STRIP + j][0]
            buffer[3*(OFFSETS[i] + j) + 1] = colors[i*PIXELS_PER_STRIP + j][1]
            buffer[3*(OFFSETS[i] + j) + 2] = colors[i*PIXELS_PER_STRIP + j][2]
    # TODO escaping
    serial_port.write(b'\xFA' + bytes(buffer) + b'\xFB')
    serial_port.flush()
    

# Main update loop.
last_state = None
for (state, colors, delay) in show.generator():
    # Update at least every 5 seconds, otherwise the watchdog will kill us.
    delay = min(delay, 5)
    notify.notify('WATCHDOG=1')
    
    if last_state != state:
        notify.notify('STATUS=' + state)
        last_state = state
    
    read_serial()

    write_colors(colors)
    time.sleep(delay)
