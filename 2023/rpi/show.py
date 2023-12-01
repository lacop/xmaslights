from datetime import datetime
import random

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

def randswap(speed, cycles, colors, swapmin, swapmax):
    colors = [random.choice(colors) for _ in range(3*80)]
    for _ in range(cycles):
        yield (colors, speed)
        for _ in range(random.randint(swapmin, swapmax)):
            i = random.randint(0, len(colors)-1)
            j = random.randint(0, len(colors)-1)
            colors[i], colors[j] = colors[j], colors[i]

SCENES = [
    ('rgbloop', lambda: rgbloop(speed=0.1, cycles=10, intensity=32)),
    ('randswp', lambda: randswap(speed=0.1, cycles=10, colors=[
        (64, 0, 0),
        (0, 64, 0),
        (0, 0, 64),
        (64, 32, 0),
        ], swapmin=3, swapmax=10)),
    #('chase', lambda: chase(speed=0.1, cycles=10, color=(32, 0, 0), length=10)),
    #('chase', lambda: chase(speed=0.1, cycles=10, color=(0, 32, 0), length=10)),
    #('chase', lambda: chase(speed=0.1, cycles=10, color=(0, 0, 32), length=10)),
]

def active():
    # TODO figure out timing
    now = datetime.now()
    if now.hour >= 16:
        return True
    return False

def generator():
    scene = 0
    scene_queue = []
    while True:
        if not active():
            yield ('off', [(0, 0, 0) for _ in range(3*80)], 1)
            continue

        if len(scene_queue) == 0:
            scene_queue = list(range(len(SCENES)))
            random.shuffle(scene_queue)
            # Make it seem more random by making sure next scene is always different.
            if scene_queue[0] == scene:
                scene_queue[0], scene_queue[-1] = scene_queue[-1], scene_queue[0]
        scene = scene_queue.pop(0)

        # Yield frames from the scene generator until it finishes.
        name = SCENES[scene][0]
        generator = SCENES[scene][1]()
        for (colors, delay) in generator:
            yield (name, colors, delay)
        
        # TODO fade in/out?