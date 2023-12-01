# 2023 Setup

Archived setup used for the December 2023 season.

Check out the individual section READMEs:

| Section | Description |
| ------- | ----------- |
| [models](models/README.md) | 3D models for 3D printing |
| [mounting](mounting/README.md) | Mounting the lights on the fence |
| [wiring](wiring/README.md) | Wiring the electronics box |
| [pico](pico/README.md) | Raspberry Pi Pico light controller firmware |
| [rpi](rpi/README.md) | Raspberry Pi lights driver software |

## Ideas for improvement

- Get custom PCB made for the electronics box.
  - Include sockets for the Pico and the RPi (or other controllers).
  - Plug-in terminal blocks for the power and data lines.
- Better control software.
  - Pico could run two cores, one for serial->lights, one for the rest (watchdog, DHT readings etc).
  - More user-friendly interface for controlling the lights eg. web interface.
  - Better monitoring (graphana or MQTT).
