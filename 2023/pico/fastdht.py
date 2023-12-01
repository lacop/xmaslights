# Simplified from adafruit_dht
# https://github.com/adafruit/Adafruit_CircuitPython_DHT
# MIT license
#
# Main change is to reduce the wait time to make reads finish in around 20ms or less.
# 
# TODO make a PIO based version that ignores length and checks hi/low after edge transition
# maybe that can be entirely background based and not block main event loop?

from pulseio import PulseIn
import array
import time

def _parse_byte(pulses, start):
        val = 0
        high = False
        for i in range(16):
            if high:
                bit = 1 if pulses[start + i] > 51 else 0
                val = (val << 1) | bit
            high = not high
        return val

class FastDHT:
    def __init__(self, pin):
        self.pin = pin
        self.last_read = None
        self.pulse = PulseIn(self.pin, maxlen=81, idle_state=True)
        self.pulse.pause()
    
    
    def read(self):
        # Throttle reads, return None rather than stale value.
        now = time.monotonic_ns()
        if self.last_read and (now - self.last_read) < 2*1000*1000:
            return None
        self.last_read = now
        
        # Send trigger sequence
        self.pulse.clear()
        self.pulse.resume(1000)

        # Wait for response. Should take 81 pulses, each one up
        # to 48-55 + 68-75 = max 130us in length for a total of
        # 10.5ms max (actually less unless the entire response is
        # "1" bits, but this is safe upper bound).
        deadline = time.monotonic_ns() + (10.5 + 1)*1000*1000
        while len(self.pulse) < 81 and time.monotonic_ns() < deadline:
            time.sleep(0.001)
        
        if len(self.pulse) < 81:
            return None

        # Checksum        
        b = [_parse_byte(self.pulse, i) for i in [0, 16, 32, 48, 64]]
        if sum(b[:4]) & 0xFF != b[4]:
            return None

        humid = ((b[0] << 8) | b[1])
        temp = (((b[2] & 0x7F) << 8) | b[3])
        if b[2] & 0x80:
            temp = -temp
        
        return (temp, humid)