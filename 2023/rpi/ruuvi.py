# Adapted / simplified from https://github.com/jannylund/ruuvi2mqtt

import json
import time

from concurrent.futures import ProcessPoolExecutor
from multiprocessing import Manager
from ruuvitag_sensor.ruuvi import RuuviTagSensor

import paho.mqtt.client as mqtt

import secrets

mqtt_client = mqtt.Client()
mqtt_client.username_pw_set(secrets.MQTT_USER, secrets.MQTT_PASSWORD)
mqtt_client.connect(secrets.MQTT_HOST, secrets.MQTT_PORT, 60)

mqtt_client.loop_start()

def ruuvi_process(queue):
    def handle_data(data):
        queue.put(data)        
    RuuviTagSensor.get_datas(handle_data)

manager = Manager()
queue = manager.Queue()

executor = ProcessPoolExecutor()
executor.submit(ruuvi_process, queue)

while True:
    while not queue.empty():
        mac, data = queue.get()
        mac = mac.replace(':', '')
        print(f'{mac}: {data}')
        mqtt_client.publish(f'ruuvi/{mac}', json.dumps(data))
    time.sleep(1)
