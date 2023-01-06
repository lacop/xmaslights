# CircuitPython code for Raspberry Pico W

Code running on the RPi Pico W, listening for packets and driving the RGB LED strings.

Runs a basic loop listening for UDP packets with simple custom protocol. Displays the provided RGB values. Occasionally reads temperature/humidity data from DHT22 sensor and occasionally responds to the UDP sender with basic statistics.

# Notes and caveats:

Assumes there is one more pixel at the front of the chain which is used as status light. This is originally added to help with signal integrity (see the wiring readme) but is convenient for debugging too.

The DHT readings are not reliable, sometimes they seem to break after few days. My theory is that the 1wire timing via pulseio breaks when internal clock timer gets too big (float precision issues) though checking the code it seems integer timers are used. Who knows, maybe the sensor itself is crap.

The whole thing sometimes glitched and stopped responding. Unclear why, but adding watchdog might help. Unplugging and plugging it back in resolved the issue.

## Setup instructions:

- Setup CircuitPython on the Pico W.
- Copy `secrets.py.sample` to `secrets.py` and edit it.
- Edit `config.py` as necessary (pin numbers)
- Copy all the code from this directory to the pico.
- Verify via the REPL that this works.
- Copy `lights.py` as `code.py` to have it auto-start.

## Credits

CRC8 library is from https://pypi.org/project/crc8/

DHT library is based on https://github.com/adafruit/Adafruit_CircuitPython_DHT
