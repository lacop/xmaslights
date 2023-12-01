import board
import neopixel
import time
import usb_cdc

import fastdht

# Configuration.
PIXEL_COUNT = 300 # Without the first buffer/status pixel
PIXEL_PIN = board.GP0

DHT_PIN = board.GP15
DHT_INTERVAL_SECS = 5

FRAME_START = b'\xFA'
FRAME_END = b'\xFB'
FRAME_ESCAPE = b'\xFC'
PACKET_SIZE = 3 * PIXEL_COUNT

# Initialize.
print('INFO: START')
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

dht = fastdht.FastDHT(DHT_PIN)

buffer = None

last_packet = time.monotonic_ns()
need_clear = True

stats_time = time.monotonic_ns()
stats_counter = 0

status_color = 0

last_dht = 0

print('INFO: READY FOR DATA')
while True:
    read = serial.read(serial.in_waiting)
    if len(read) > 0:
        last_packet = time.monotonic_ns()
        need_clear = True
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
                if buffer is None:
                    buffer = bytes()
                else:
                    print('ERROR: invalid start byte', b)
                    buffer = bytes()
            elif b == FRAME_END:
                if buffer is None:
                    print('ERROR: invalid end byte', b)
                elif len(buffer) == PACKET_SIZE:
                    for i in range(PIXEL_COUNT):
                        pixels[i+1] = (buffer[i*3], buffer[i*3+1], buffer[i*3+2])
                    pixels[0] = [
                        (0, 32, 0),
                        (0, 0, 32),
                    ][status_color]
                    status_color = (status_color + 1) % 2
                    pixels.show()
                    stats_counter += 1
                else:
                    print('ERROR: invalid packet size', len(buffer))
                buffer = None
            elif b == FRAME_ESCAPE:
                escape = True
            else:
                if buffer is not None:
                    buffer += b
    now = time.monotonic_ns()
    if stats_counter >= 20:        
        elapsed = (now - stats_time) / 1000 / 1000 / 1000
        if elapsed > 0:
            print('FPS:', stats_counter / elapsed)
        stats_counter = 0
        stats_time = now
    if need_clear and (now - last_packet)//1000//1000//1000 > 5:
        for i in range(PIXEL_COUNT + 1):
            pixels[i] = (0, 0, 0)
        pixels[0] = (32, 0, 0)
        pixels.show()
        need_clear = False
    if (now - last_dht)//1000//1000//1000 > DHT_INTERVAL_SECS:
        reading = dht.read()
        if reading is None:
            print('DHT: error')
        else:
            temp, humid = reading
            print('DHT: temp={} humid={}'.format(temp, humid))
            last_dht = now

# TODO read dht
# TODO report stats back up
# TODO watchdog?
# TODO show temp on lcd