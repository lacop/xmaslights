import board
import neopixel
import time
import usb_cdc

import fastdht

# Configuration.
PIXEL_COUNT = 300 # Without the first buffer/status pixel
PIXEL_PIN = board.GP0

FRAME_START = b'\xFA'
FRAME_END = b'\xFB'
FRAME_ESCAPE = b'\xFC'
PACKET_SIZE = 3 * PIXEL_COUNT

# Initialize.
print('START')
pixels = neopixel.NeoPixel(PIXEL_PIN, PIXEL_COUNT + 1, auto_write=False)
for i in range(PIXEL_COUNT + 1):
    pixels[i] = (0, 0, 0)
pixels[0] = (32, 0, 0)
pixels.show()

assert usb_cdc.data is not None
serial = usb_cdc.data
serial.timeout = 0.1
pixels[0] = (0, 32, 0)
pixels.show()

buffer = None
last_packet = time.monotonic_ns()
stats_time = time.monotonic_ns()
stats_counter = 0

status_color = 0

print('READY FOR DATA')
while True:
    if serial.in_waiting > 0:
        read = serial.read(serial.in_waiting)
        last_packet = time.monotonic_ns()
        escape = False
        for b in read:
            b = bytes([b])
            if escape:
                if b not in [FRAME_START, FRAME_END, FRAME_ESCAPE]:
                    print('ERROR: invalid escape byte', b)
                else:
                    buffer += b
                escape = False
            elif b == FRAME_START:
                print('FRAME START')
                if buffer is None:
                    buffer = bytes()
                else:
                    print('ERROR: invalid start byte', b)
                    buffer = bytes()
            elif b == FRAME_END:
                print('FRAME END', len(buffer))
                if len(buffer) == PACKET_SIZE:
                    for i in range(PIXEL_COUNT):
                        pixels[i+1] = (buffer[i*3], buffer[i*3+1], buffer[i*3+2])
                    pixels[0] = [
                        (0, 32, 0),
                        (0, 0, 32),
                    ][status_color]
                    status_color = (status_color + 1) % 2
                    pixels.show()
                    stats_time = time.monotonic_ns()
                    stats_counter += 1
                else:
                    print('ERROR: invalid packet size', len(buffer))
                buffer = None
            elif b == FRAME_ESCAPE:
                escape = True
            else:
                if buffer is not None:
                    buffer += b
    if stats_counter >= 10:
        now = time.monotonic_ns()
        print('FPS:', (now - stats_time)/1000/1000/stats_counter)
        stats_counter = 0
        stats_time = now
    if (time.monotonic_ns() - last_packet)/1000/1000/1000 > 5:
        for i in range(PIXEL_COUNT + 1):
            pixels[i] = (0, 0, 0)
        pixels[0] = (32, 0, 0)
        pixels.show()

# TODO read dht
# TODO report stats back up
# TODO watchdog?
# TODO show temp on lcd