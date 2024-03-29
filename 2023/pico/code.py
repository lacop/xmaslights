import board
import neopixel
import time
import usb_cdc

import fastdht

# Configuration.
PIXEL_COUNT = 300 # Without the first buffer/status pixel
PIXEL_PIN = board.GP0

DHT_PIN = board.GP15
DHT_INTERVAL_SECS = 30

FRAME_START = b'\xFA'
FRAME_END = b'\xFB'
FRAME_ESCAPE = b'\xFC'
PACKET_SIZE = 3 * PIXEL_COUNT

# Initialize.
print('SET UP SERIAL')
assert usb_cdc.data is not None
serial = usb_cdc.data
serial.timeout = 0.1

def log(msg):
    print(msg)
    serial.write((msg + '\n').encode('ascii'))

pixels = neopixel.NeoPixel(PIXEL_PIN, PIXEL_COUNT + 1, auto_write=False)
for i in range(PIXEL_COUNT + 1):
    pixels[i] = (0, 0, 0)
pixels[0] = (32, 0, 0)
pixels.show()

dht = fastdht.FastDHT(DHT_PIN)
last_dht_time = 0

buffer = None

last_packet_time = time.monotonic_ns()
need_clear = True

stats_time = time.monotonic_ns()
stats_counter = 0

status_color = 0

last_alive_time = time.monotonic_ns()
last_alive_state = 0

print('INFO: READY FOR DATA')
while True:
    read = serial.read(serial.in_waiting)
    if len(read) > 0:
        last_packet_time = time.monotonic_ns()
        need_clear = True
        escape = False
        for b in read:
            b = bytes([b])
            if escape:
                if b not in [FRAME_START, FRAME_END, FRAME_ESCAPE]:
                    log(f'ERROR: invalid escape byte {b}')
                else:
                    buffer += b
                escape = False
            elif b == FRAME_START:
                if buffer is None:
                    buffer = bytes()
                else:
                    log(f'ERROR: invalid start byte {b}')
                    buffer = bytes()
            elif b == FRAME_END:
                if buffer is None:
                    log(f'ERROR: invalid end byte {b}')
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
                    log('ERROR: invalid packet size {len(buffer)}')
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
            # Don't log.
            print('FPS:', stats_counter / elapsed)
            last_alive_time = now
        stats_counter = 0
        stats_time = now
    if need_clear and (now - last_packet_time)//1000//1000//1000 > 5:
        for i in range(PIXEL_COUNT + 1):
            pixels[i] = (0, 0, 0)
        pixels[0] = (32, 0, 0)
        pixels.show()
        need_clear = False
    if (now - last_dht_time)//1000//1000//1000 > DHT_INTERVAL_SECS:
        reading = dht.read()
        if reading is None:
            log('DHT: error')
            # Try again later...
            last_dht_time = now
        else:
            temp, humid = reading
            log(f'DHT: temp={temp} humid={humid}')
            last_dht_time = now
    if (now - last_alive_time)//1000//1000//1000 > 60:
        last_alive_time = now
        last_alive_state = (last_alive_state + 1) % 2
        # Just for display, don't log.
        print(f'INFO: Alive', last_alive_state)
# TODO watchdog?
