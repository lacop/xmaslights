# Firmware for the RP2040 controller

Using Waveshare RP2040-LCD-0.96 board, but any RP2040 board should work.

`boot.py` sets up USB CDC channel for sending over the color data. `code.py` just listens on the serial port and updates the lights, sending back DHT22 readings and error messages. FPS is also `print()`-ed to the stdout which shows up on the LCD.

The single buffer pixel is used as an indicator light, should alternate colors on every successfully received frame.
