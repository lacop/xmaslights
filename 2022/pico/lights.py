import board
from crc8 import crc8
import errno
import fastdht
import microcontroller
import neopixel
import socketpool
import struct
import time
import wifi

try:
    import config
    import secrets
except ImportError:
    print('Failed to open config.py or secrets.py')
    raise

print('STARTING')

print('Clearing out all LEDS, count:', config.LED_COUNT)
# +1 pixel always for the one acting as buffer / level shifter / status indicator
pixels = neopixel.NeoPixel(config.LED_PIN, config.LED_COUNT + 1, auto_write=False)
for i in range(config.LED_COUNT + 1):
    pixels[i] = 0
pixels.show()

print('Setting up...')
pixels[0] = (255, 165, 0)
pixels.show()

print('My mac:', ':'.join('{:02x}'.format(b) for b in wifi.radio.mac_address))
print('Attempting to connect to:', secrets.WIFI_SSID)

wifi.radio.connect(secrets.WIFI_SSID, secrets.WIFI_PASSWD)

print('Connected!')
print('My IP:', wifi.radio.ipv4_address)

pool = socketpool.SocketPool(wifi.radio)
sck = pool.socket(socketpool.SocketPool.AF_INET, socketpool.SocketPool.SOCK_DGRAM)
sck.bind((str(wifi.radio.ipv4_address), config.UDP_PORT))
sck.settimeout(5)
print('UDP listening on port', config.UDP_PORT)

# print('Setting up DHT')
# dht = adafruit_dht.DHT22(config.DHT_PIN)
# dht.measure()
dht = fastdht.FastDHT(config.DHT_PIN)

print('Entering listen loop...')
pixels[0] = (60, 0, 100)
pixels.show()

# Buffer size:
# - 4 byte magic 'LGHT'
# - 2 bytes for order
# - 2 bytes for length (entire packet)
# - 3x bytes for RGB values
# - 1 byte CRC8
MAX_PACKET_LEN = 4 + 2 + 2 + 3*config.LED_COUNT + 1
buffer = bytearray(MAX_PACKET_LEN + 16) # 16 = extra buffer

STATUS_COLORS = {
    # OK, receiving packets. Green variants.
    'ok': [(25, 75, 25), (5, 30, 5)],
    # Socket read timeout. Yellow variants.
    'timedout': [(50, 30, 10), (40, 20, 15)],
    # Socket read timeout and ping failed. Red variants.
    'timedoutfailedping': [(150, 20, 0), (150, 0, 20)],
    # Bad packets. Redish variants.
    'badpacket': [(95, 20, 10), (80, 10, 20)],
}
last_status_color = 0
def set_status_color(status):
    global last_status_color
    pixels[0] = STATUS_COLORS[status][last_status_color % len(STATUS_COLORS[status])]
    last_status_color += 1

# Last good packet.
last_received_order = 0
last_good_ns = 0

# Statistics.
stats_sent_ns = 0
# Contents:
# All values capped at 255 (avoid overflow), but should fit safely.
# All values reset when sent, except counter and dht_*.
# - 1 byte: Stats packet order, wraps around.
# - 1 byte: Times timed out.
# - 1 byte: Total packets received.
# - 1 byte: Missed packets.
# - 1 byte: Bad packets. Received - bad = displayed.
# - 1 byte: Max processing time since last report as ms.
# - 1 byte: DHT read errors count.
# - 1 byte: Seconds since last good DHT measurement.
# - 2 byte: Temperature * 10. Last good measurement.
# - 2 byte: Humidity * 10. Last good measurement.
# - 1 byte: CRC8
statsbuffer = bytearray(13)
stats_order = 0
stats_timeouts = 0
stats_packets_total = 0
stats_packets_missed = 0
stats_packets_bad = 0
stats_max_process_time_ns = 0

dht_read_errors = 0
dht_last_read_ns = 0
dht_last_good_read_ns = 0
dht_last_temp = 0
dht_last_humid = 0


def fill_and_reset_stats():
    global statsbuffer, stats_order, stats_timeouts
    global stats_packets_total, stats_packets_missed, stats_packets_bad
    global stats_max_process_time_ns
    global dht_read_errors, dht_last_good_read_ns
    global dht_last_temp, dht_last_humid
    
    # Populate packet
    statsbuffer[0] = stats_order
    statsbuffer[1] = min(255, stats_timeouts)
    statsbuffer[2] = min(255, stats_packets_total)
    statsbuffer[3] = min(255, stats_packets_missed)
    statsbuffer[4] = min(255, stats_packets_bad)
    statsbuffer[5] = min(255, stats_max_process_time_ns//1000//1000)
    statsbuffer[6] = min(255, dht_read_errors)
    statsbuffer[7] = min(255, (time.monotonic_ns()-dht_last_good_read_ns)//1000//1000//1000)
    statsbuffer[8:10] = struct.pack('<h', dht_last_temp)
    statsbuffer[10:12] = struct.pack('<H', dht_last_humid)
    
    crc = crc8()
    crc.update(statsbuffer[:12])
    statsbuffer[12] = crc.digest()[0]

    # Adjust counter
    stats_order = (stats_order + 1) % 256
    # Reset everything else
    stats_timeouts = 0
    stats_packets_total = 0
    stats_packets_missed = 0
    stats_packets_bad = 0
    stats_max_process_time_ns = 0
    dht_read_errors = 0


def badpacket():
    global last_good_ns
    set_status_color('badpacket')
    # Clear out everything else if we keep getting bad data.
    if time.monotonic_ns() - last_good_ns > 5*1000*1000*1000:
        for i in range(config.LED_COUNT):
            pixels[i+1] = 0
    pixels.show()

failed_pings = 0

# TODO start watchdog & increment in each loop (even error)
# print('STARTING WATCHDOG NOW')
# Maximum supported by RPi Pico should be 8 seconds or so
# microcontroller.watchdog.timeout = 6 

while True:
    # Maybe read DHT values if enough time passed.
    dht_read_time = time.monotonic_ns()
    if dht_read_time - dht_last_read_ns > config.DHT_INTERVAL_SEC*1000*1000*1000:
        dht_last_read_ns = dht_read_time
        m = dht.read()
        if m:
            #print('DHT good')
            dht_last_good_read_ns = dht_read_time
            dht_last_temp, dht_last_humid = m
        else:
            dht_read_errors += 1
            #print('DHT bad')

    # Wait for network packet, with timeout.
    try:
        size, sender = sck.recvfrom_into(buffer)
    except OSError as error:
        if error.errno == errno.ETIMEDOUT:
            stats_timeouts += 1
            
            pingok = wifi.radio.ping(config.PING_IP) is not None
            if pingok:
                set_status_color('timedout')
                failed_pings = 0
            else:
                set_status_color('timedoutfailedping')
                failed_pings += 1
                print('PING FAILED, now at ', failed_pings)
                if failed_pings > 5:
                    print('!!!REBOOT!!!')
                    microcontroller.reset()

            # Clear to avoid getting stuck in display mode when network or sender is down.
            for i in range(config.LED_COUNT):
                pixels[i+1] = 0
            pixels.show()
            continue
        else:
            raise error
    stats_packets_total += 1
    failed_pings = 0
    
    # Verify the packet
    process_start = time.monotonic_ns()
    #print('Got', size, 'from', sender)
    
    if size > MAX_PACKET_LEN or size < 9 or buffer[:4] != b'LGHT':
        #print('BAD PACKET')
        badpacket()
        stats_packets_bad += 1
        continue
    
    order = struct.unpack('>H', buffer[4:6])[0]
    length = struct.unpack('>H', buffer[6:8])[0]
    packet_crc = buffer[size - 1]
    
    packet_lights = length - 9
    if length != size or packet_lights % 3 != 0:
        #print('BAD SIZE')
        badpacket()
        stats_packets_bad += 1
        continue
    packet_lights = packet_lights // 3
    
    computed_crc = crc8()
    computed_crc.update(buffer[:size - 1])
    if computed_crc.digest() != bytes([packet_crc]):
        #print('BAD CRC')
        badpacket()
        continue

    # TODO need modular math here
    if last_received_order + 1 < order:
        #print('MISSED PACKETS', order-last_received_order-1)
        stats_packets_missed += 1 # TODO increment by the real amount
        # No "continue", this is fine, just display it.
        pass
    last_received_order = order
    
    verify_end = time.monotonic_ns()
    last_good_ns = verify_end

    # Write out to pixels, toggle status
    for i in range(config.LED_COUNT):
        if i < packet_lights:
            pixels[i+1] = (buffer[8 + 3*i], buffer[8 + 3*i + 1], buffer[8 + 3*i + 2])
        else:
            pixels[i+1] = 0
    set_status_color('ok')
    # TODO power estimate and brightness control?
    # maybe better done on server side but we can at least sanity check and refuse...
    #pixels.brightness = (1.0 if order%2 == 0 else 0.5)
    pixels.show()

    process_end = time.monotonic_ns()
    stats_max_process_time_ns = max(stats_max_process_time_ns, process_end-process_start)

    if process_end - stats_sent_ns > config.STATS_INTERVAL_SEC*1000*1000*1000:
        stats_sent_ns = process_end
        fill_and_reset_stats()
        sck.sendto(statsbuffer, sender)
        #print('reply', (time.monotonic_ns()-process_end)/1000/1000)

    #TODO wrap these prints in some DEBUG_ON or whatever
    #print('Verify', (verify_end-process_start)/1000/1000, 'ms')
    #print('Write', (process_end-verify_end)/1000/1000, 'ms')