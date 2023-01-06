# Control software

This is just a very hacky python script with few hardcoded animations.

Run it on some proxmox VM or something (runscript to start on restart). Will switch between animations, warmup (few white leds to keep PSU active and heating up the enclosure) and off. Pushes metrics (temperature/humidity, mode etc) to MQTT.

The LED offsets are hardcoded, assuming 3 fence sections with 80 LEDs each. Might need adjusting depending on how the mounting goes.

Tons of room for improvement, the animations could be fancier. Could also integrate with ledfx (as listener to recalculate offsets and forward the packet, keeping the metrics) to have music sync etc.
