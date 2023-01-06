import board
import ipaddress

# Network
UDP_PORT=3322
PING_IP = ipaddress.ip_address('10.0.0.1')

# LED strip
LED_COUNT=300
LED_PIN = board.GP2 # Pin 4

# DHT
DHT_PIN = board.GP27 # Pin 32
DHT_INTERVAL_SEC = 10

# Statistics
STATS_INTERVAL_SEC = 5