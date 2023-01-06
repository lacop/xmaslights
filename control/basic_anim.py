#!/usr/bin/python3

import crc8
from datetime import datetime
import ipaddress
from paho.mqtt import client as mqtt_client
import random
import socket
import struct
import time

TARGET = ('10.0.0.116', 3322)
LED_COUNT = 300

MQTT_TARGET = ('10.0.0.138', 1883)
MQTT_TOPIC_DHT = 'picowled/dht'
MQTT_TOPIC_MODE = 'picowled/mode'
MQTT_TOPIC_POWER = 'picowled/power'
MQTT_TOPIC_ALIVE = 'picowled/alive'
import secrets

mqtt = mqtt_client.Client('basic-mqtt-' + str(random.randint(1000, 2000)))
mqtt.username_pw_set(secrets.MQTT_USER, secrets.MQTT_PWD)
mqtt.connect(MQTT_TARGET[0], MQTT_TARGET[1])
mqtt.loop_start()

# 10 segments, 8 leds each = 80 total from start
STARTS = [11, 110, 208]

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(0)

packet_counter = 0
def make_packet(rgbs):
    global packet_counter
    packet_counter = (packet_counter + 1) % 65536

    assert(len(rgbs) % 3 == 0)
    packet_length = 4 + 2 + 2 + 1 + len(rgbs)

    packet = (
        bytearray(b'LGHT') +
        struct.pack('>H', packet_counter) +
        struct.pack('>H', packet_length) +
        bytearray(rgbs)
    )
    
    crc = crc8.crc8()
    crc.update(packet)
    packet += crc.digest()
    
    return packet


lastalive = ''
def setalive(alive):
    global lastalive
    if alive != lastalive:
        print('[ALIVE MQTT]')
        mqtt.publish(MQTT_TOPIC_ALIVE, f'{{"alive": "{alive}" }}')
    lastalive = alive

last_stats = 0
last_stats_time = 0
last_dht = (0, 0)
def print_stats(buf):
    global last_stats, last_stats_time, last_dht
    assert len(buf) == 13
    
    order = buf[0]
    # if (last_stats + 1) % 256 != order:
    #     print('MISSED SOME', last_stats, order)
    last_stats = order

    timedout = buf[1]
    total = buf[2]
    missed = buf[3]
    bad = buf[4]
    maxtime = buf[5]
    dhterrors = buf[6]
    dhtage = buf[7]
    
    temp = struct.unpack('<h', buf[8:10])[0] / 10.0
    humid = struct.unpack('<H', buf[10:12])[0] / 10.0

    crc = crc8.crc8()
    crc.update(buf[:12])
    if crc.digest()[0] != buf[12]:
        print('BAD CRC', crc.digest())
        return

    last_stats_time = time.time()

    print(f'#{order} timedout:{timedout} total:{total} missed:{missed} bad:{bad} ' +
          f'max:{maxtime}ms // DHT errors:{dhterrors} age:{dhtage}s T:{temp}C H:{humid}%')

    # Max value is 255...
    if dhtage > 200:
        print('STALE DHT')
        setalive('staledht')
        return # Don't publish
    
    setalive('alive')

    if last_dht != (temp, humid):
        print('  -> MQTT PUSH')
        last_dht = (temp, humid)
        mqtt.publish(MQTT_TOPIC_DHT, f'{{"temperature": {temp}, "humidity": {humid} }}')

# Rough estimate - product listing says ~50mA, other
# resources claim similar 12V pixels are ~30mA, let's
# try something inbetween.
MILLIAMP_PER_LED = 40
# 150W 12V PSU => 12.5A max, add some buffer room.
PSU_MAX_AMPS = 10
def power_estimate_amps(data):
    # Stupid linear model
    return sum(d/255.0 * (MILLIAMP_PER_LED / 3.0) for d in data) / 1000.0

last_sent_amps_time = 0
amps_avg = (0, 0)
def power_throttle(data):
    global last_sent_amps_time, amps_avg
    amps = power_estimate_amps(data)
    amps_avg = (amps_avg[0] + amps, amps_avg[1] + 1)
    if time.time() - last_sent_amps_time > 30 and amps_avg[1] > 0:
        avg = int((amps_avg[0] / amps_avg[1])*1000)
        #print('[MQTT amps]')
        mqtt.publish(MQTT_TOPIC_POWER, f'{{"avg": {avg} }}')
        last_sent_amps_time = time.time()
        amps_avg = (0, 0)
        
    
    # TODO Actually throttle?
    # if p > PSU_MAX_AMPS:
    #   ... compute ratio and multiply everything to clamp power


def send(data):
    global last_stats_time
    power_throttle(data)
    packet = make_packet(data)
    sock.sendto(packet, TARGET)
    try:
        buf, sender = sock.recvfrom(1024)
        if len(buf) > 0:
            print_stats(buf)
    except:
        if time.time() - last_stats_time > 30:
            setalive('dead')

# while True:
#     data = [0] * (3 * LED_COUNT)
#     send(data)
#     time.sleep(1)

def dotswap(frames):
    data = [0] * (3 * LED_COUNT)
    for start in STARTS:
        for led in range(80):
            rgb = [
                (192, 0, 0),
                (0, 192, 0),
                (0, 0, 192),
                (128, 64, 0)
            ][random.randint(0, 3)]
            data[start*3 + led*3] = rgb[0]
            data[start*3 + led*3 + 1] = rgb[1]
            data[start*3 + led*3 + 2] = rgb[2]
    for _ in range(frames):        
        swaps = random.randint(3, 10)
        for _ in range(swaps):
            si, li = STARTS[random.randint(0, 2)], random.randint(0, 79)
            sj, lj = STARTS[random.randint(0, 2)], random.randint(0, 79)
            for i in range(3):
                data[si*3 + li*3 + i], data[sj*3 + lj*3 + i] = data[sj*3 + lj*3 + i], data[si*3 + li*3 + i]
        send(data)
        time.sleep(0.5)

def rgbcycle(frames):
    x = 0
    for _ in range(frames):
        data = [0] * (3 * LED_COUNT)
        x = (x + 1) % 3
        
        for start in STARTS:
            for seg in range(10):
                for led in range(8):
                    data[start*3 + 8*seg*3+led*3+((seg+x)%3)] = 100
        send(data)
        time.sleep(0.5)

def redgreenbar(frames):
    x = 0
    for _ in range(frames):
        data = [0] * (3 * LED_COUNT)
        x = (x + 1) % 8
        
        for start in STARTS:
            for seg in range(10):
                for led in range(8):
                    q = seg-4 if seg >= 5 else 5-seg
                    g = 100 if q < x else 0
                    r = 100 if q == x else 0
                    data[start*3 + 8*seg*3+led*3] = g
                    data[start*3 + 8*seg*3+led*3+1] = r
        send(data)
        time.sleep(0.5)

# def fastline(frames, speed=0.1):
#     global sock
#     x = 0
#     for _ in range(frames):
#         data = [0] * (3 * LED_COUNT)
#         x = (x + 1) % 30
#         start = STARTS[x // 10]
#         seg = x-(x//10)*10
#         for led in range(8):
#             data[start*3 + 8*seg*3+led*3] = 50
#             data[start*3 + 8*seg*3+led*3+1] = 50
#             data[start*3 + 8*seg*3+led*3+2] = 50
#         send(data)
#         time.sleep(speed)

def warmup(pwr):
    data = [0] * (3 * LED_COUNT)
    for led in [0, 1, 2, 97, 98, 99, 100, 101, 102, 197, 198, 199, 200, 201, 202, 297, 298, 299]:
        data[led*3] = pwr
        data[led*3+1] = pwr
        data[led*3+2] = pwr
    for _ in range(60):
        send(data)
        time.sleep(1)

def blank():
    data = [0] * (3 * LED_COUNT)
    for _ in range(60):
        send(data)
        time.sleep(1)

lastmode = ''
lastmode_sent = 0
def setmode(mode):
    global lastmode, lastmode_sent
    if mode != lastmode or time.time() - lastmode_sent > 60:
        #print('[MODE MQTT]')
        mqtt.publish(MQTT_TOPIC_MODE, f'{{"mode": "{mode}" }}')
        lastmode_sent = time.time()
    lastmode = mode


while True:
    hour = datetime.now().hour
    minute = datetime.now().minute
    if (hour >= 15 and hour < 22) or (hour == 14 and minute >= 30):
        setmode('animate')
        dotswap(2*30)
        rgbcycle(20*2)
        redgreenbar(24*1)
    elif hour >= 22 or hour < 7:
        setmode('warmup120')
        warmup(120)
    elif hour >= 7 and hour < 12:
        setmode('warmup60')
        warmup(60)
    else:
        setmode('blank')
        blank()
    #fastline(60, speed=0.5)
    #fastline(60, speed=0.25)
    #fastline(30, speed=0.1)
    #fastline(60, speed=0.05)
    #fastline(60, speed=0.02)
