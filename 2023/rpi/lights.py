import json
import math
import multiprocessing
import re
import sdnotify
import serial
import sys
import threading
import time

import paho.mqtt.client as mqtt

import secrets
import show

# First and last 10 pixels of every 100 pixel strip are not used.
OFFSETS = [10, 110-1, 210]
PIXELS_PER_STRIP = 80
# Always on lights to burn some power in the PSU and keep the box warm.
# (Stupid thing is too efficient...)
HEAT_LIGHTS = [i + j for i in [0, 100, 200] for j in [0, 1, 2, 3, 4, 99, 98, 97, 96, 95]]
HEAT_INTENSITY = 64

serial_port = serial.Serial('/dev/ttyACM1', timeout=0)

notify = sdnotify.SystemdNotifier()
notify.notify('READY=1')
notify.notify('STATUS=Initialized')

mqtt_client = mqtt.Client()
mqtt_client.username_pw_set(secrets.MQTT_USER, secrets.MQTT_PASSWORD)
mqtt_client.connect(secrets.MQTT_HOST, secrets.MQTT_PORT, 60)
mqtt_client.loop_start()

# TODO connect to MQTT
def mqtt_send(topic, value):
    global mqtt_client
    print(f'MQTT: {topic}={value}')
    mqtt_client.publish(f'lights/{topic}', json.dumps(value))

dht_temp = None
dht_humid = None
def update_dht(temp, humid):
    global dht_temp, dht_humid
    dht_temp = temp
    dht_humid = humid
    mqtt_send('dht', {'temperature': temp, 'humidity': humid})

# Background processes for burning CPU to increase enclosure temperature.
def worker(queue):
    state = False
    while True:
        try:
            state = queue.get_nowait()
        except multiprocessing.queues.Empty:
            pass # Keep previous state
        if state:
            now = time.time()
            while time.time() < now + 1:
                for j in range(1000000):
                    math.sqrt(j)
        else:
            time.sleep(1)

WORKER_COUNT = 2
queues = [multiprocessing.Queue() for _ in range(WORKER_COUNT)]
workers = [multiprocessing.Process(target=worker, args=(queue,)) for queue in queues]
for worker in workers:
    worker.start()

worker_state = False
def set_worker_state(state):
    global worker_state
    if state == worker_state:
        return
    worker_state = state
    for queue in queues:
        queue.put(state)
    mqtt_send('cpu_burner', {'state': state})

def update_temp():
    # Read internal CPU temperature
    with open('/sys/class/thermal/thermal_zone0/temp') as f:
        try:
            internal_temp = int(f.read()) / 1000
        except:
            print('ERROR: failed to read internal temp')
            return
    mqtt_send('rpi_temp', {'temperature': internal_temp})

    # Update worker state based on internal temp and DHT temp.
    # Add some hysteresis to avoid frequent switching.
    if internal_temp > 55 or (dht_temp is not None and dht_temp > 15):
        set_worker_state(False)
    elif internal_temp < 40 or (dht_temp is not None and dht_temp < 10):
        set_worker_state(True)

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
                
        # DHT sensor data.
        matches = re.match(r'DHT: temp=(-?\d+) humid=(-?\d+)', line.decode('ascii'))
        if matches:
            temp = int(matches[1]) / 10
            humid = int(matches[2]) / 10
            update_dht(temp, humid)
        else:
            print('From serial:', line.decode('ascii'))
            # TODO handle other lines like errors

def write_colors(colors):
    buffer = [0 for _ in range(3*300)]
    for i in HEAT_LIGHTS:
        for j in range(3):
            buffer[3*i + j] = HEAT_INTENSITY
    for i in range(len(OFFSETS)):
        for j in range(PIXELS_PER_STRIP):
            buffer[3*(OFFSETS[i] + j) + 0] = colors[i*PIXELS_PER_STRIP + j][0]
            buffer[3*(OFFSETS[i] + j) + 1] = colors[i*PIXELS_PER_STRIP + j][1]
            buffer[3*(OFFSETS[i] + j) + 2] = colors[i*PIXELS_PER_STRIP + j][2]
    # TODO escaping
    serial_port.write(b'\xFA' + bytes(buffer) + b'\xFB')
    serial_port.flush()
    
# Background thread for reading serial data, MQTT reporting and
# temperature control.
def background():
    last_temp_update = time.time()
    while True:
        read_serial()
        if time.time() - last_temp_update > 60:
            update_temp()
            last_temp_update = time.time()
        time.sleep(1)
        # TODO report uptime (machine and process) to MQTT

threading.Thread(target=background, daemon=True).start()

# Main update loop for the lights and watchdog.
last_state = None
for (state, colors, delay) in show.generator():
    # Update at least every 5 seconds, otherwise the watchdog will kill us.
    delay = min(delay, 5)
    notify.notify('WATCHDOG=1')
    
    if last_state != state:
        notify.notify('STATUS=' + state)
        last_state = state
        mqtt_send('state', {'state': state})
    
    write_colors(colors)
    time.sleep(delay)
