# Lights control software

`lights.py` is the entrypoint which talks to the Pico over serial and handles systemd watchdog, light offsets, DHT22 readings etc.

`show.py` has the animations and schedule.

This is very basic but it works. More animations can be easily added and `scp`-ed over to the RPi.
