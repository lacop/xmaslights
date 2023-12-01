import sys
import time

l = 0
while True:
    pixels = bytes()
    for i in range(300):
        if (i+l) % 2 == 0:
            pixels += bytes([32, 0, 0])
        else:
            pixels += bytes([0, 32, 0])
    sys.stdout.buffer.write(b'\xFA' + pixels + b'\xFB')
    sys.stdout.flush()
    time.sleep(1)
    l = (l + 1) % 100
