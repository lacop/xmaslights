def rgbloop(speed, cycles, intensity):
    colors = [
        [
            (intensity, 0, 0),
            (0, intensity, 0),
            (0, 0, intensity),
        ][i%3]
        for i in range(3*80)
    ]
    for _ in range(cycles):
        yield (colors, speed)
        colors = colors[1:] + [colors[0]]

def chase(speed, cycles, color, length):
    colors = [
        color if i % 80 < length else (0, 0, 0)
        for i in range(3*80)
    ]
    for _ in range(cycles):
        yield (colors, speed)
        # TODO

SCENES = [
    ('rgbloop', lambda: rgbloop(speed=0.1, cycles=10, intensity=32)),
    ('chase', lambda: chase(speed=0.1, cycles=10, color=(32, 0, 0), length=10)),
]

def generator():
    scene = 0
    while True:
        name = SCENES[scene][0]
        generator = SCENES[scene][1]()
        for (colors, delay) in generator:
            yield (name, colors, delay)
        scene = (scene + 1) % len(SCENES)
        # TODO fade in/out?