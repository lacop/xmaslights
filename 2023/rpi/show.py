from datetime import datetime, timedelta
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

def aligndebug():
    colors = [(255, 0, 0)] + [(0, 0, 0)]*78 + [(0, 0, 255)]
    colors = colors*3
    while True:
        yield (colors, 1)

def rain(speed, cycles, intmin, intmax, delaymin, delaymax):
    # (offset, direction)
    segments = [
        (80*section + 8*strip, -1 if strip % 2 == 0 else 1)
        for section in range(3)
        for strip in range(10)
    ]
    # (intensity, position)
    drops = [
        (random.randint(intmin, intmax), -random.randint(delaymin, delaymax))
        for _ in range(len(segments))
    ]
    min_intensity = 8
    for _ in range(cycles):
        colors = [(0, 0, 0)]*80*3
        for i in range(len(segments)):
            (offset, direction) = segments[i]
            (intensity, position) = drops[i]

            # Render drop + trail with /2 intensity for each step
            in_view = False
            for _ in range(10):
                if intensity >= min_intensity and position >= 0 and position < 8:
                    in_view = True
                    if direction == 1:
                        colors[offset + position] = (intensity, intensity, intensity)
                    else:
                        colors[offset + 8 - position] = (intensity, intensity, intensity)
                position -= 1
                intensity = intensity // 2

            drops[i] = (drops[i][0], drops[i][1] + 1)
            if not in_view and position >= 8:
                drops[i] = (random.randint(intmin, intmax), -random.randint(delaymin, delaymax))

        yield (colors, speed)

def rado(cycles, speed, intensity):
    rgb = [(intensity, 0, 0), (0, intensity, 0), (0, 0, intensity)]
    colors = [(0, 0, 0)]*40 + [(0, 0, intensity)]*40 + [rgb[i%3] for i in range(80)] + [(intensity, intensity, 0)]*20 + [(0, 0, 0)]*60
    for _ in range(cycles):
        yield (colors, speed)


# NEWYEAR_TRIGGER = datetime(2023, 12, 28, 16, 25, 0)
# NEWYEAR_COUNTDOWN = 30
# NEWYEAR_DURATION = 30

NEWYEAR_TRIGGER = datetime(2024, 1, 1, 0, 0, 0)
NEWYEAR_COUNTDOWN = 60*5
NEWYEAR_DURATION = 10*60

SCENES = [
    ('rain', lambda: rain(speed=0.10, cycles=300, intmin=32, intmax=196, delaymin=2, delaymax=8)),
    ('colorswap', lambda: randswap(speed=0.25, cycles=120, colors=[
        (64, 0, 0),
        (64, 0, 0),
        (0, 64, 0),
        (0, 64, 0),
        (64, 64, 16),
        (64, 32, 0),
        ], swapmin=3, swapmax=15)),
    ('whiteswap', lambda: randswap(speed=0.25, cycles=120, colors=[
        (32, 32, 32),
        (32, 32, 32),
        (32, 32, 32),
        (64, 64, 64),
        (64, 64, 64),
        (128, 128, 128),
        (128, 128, 128),
        (192, 192, 192)
        ], swapmin=10, swapmax=20)),
    # Unused.
    #('rado', lambda: rado(cycles=600, speed=0.1, intensity=128)),
    #('aligndebug', lambda: aligndebug()),
    #('rgbloop', lambda: rgbloop(speed=0.5, cycles=30, intensity=64)),    
    #('chase', lambda: chase(speed=0.1, cycles=10, color=(32, 0, 0), length=10)),
    #('chase', lambda: chase(speed=0.1, cycles=10, color=(0, 32, 0), length=10)),
    #('chase', lambda: chase(speed=0.1, cycles=10, color=(0, 0, 32), length=10)),
]

def newyear_active():
    now = datetime.now()
    return (
        now >= NEWYEAR_TRIGGER - timedelta(seconds=NEWYEAR_COUNTDOWN) and 
        now < NEWYEAR_TRIGGER + timedelta(seconds=NEWYEAR_DURATION)
    )
    
def newyear():
    # countdown
    while True:
        d = (datetime.now() - NEWYEAR_TRIGGER).total_seconds()
        if d >= 0: break            
        d = -d
        
        lights_on = int((3*80) * d/NEWYEAR_COUNTDOWN)
        margin_left = (3*80 - lights_on) // 2
        margin_right = 3*80 - lights_on - margin_left
        color = (192, 192, 192)
        # blink red on round seconds
        if d % 1 < 0.25:
            color = [
                (255, 64, 64),
                (64, 255, 64),
                (64, 64, 255)
                ][int(d) % 3]
        yield ([(0, 0, 0)]*margin_left + [color]*lights_on + [(0, 0, 0)]*margin_right, 0.2)
        
    # fireworks
    colors = [(0, 0, 0)]*80*3
    while True:
        if (datetime.now() - NEWYEAR_TRIGGER).total_seconds() > NEWYEAR_DURATION:
            break
        # fade existing at random rate
        blank = []
        for i in range(len(colors)):
            if colors[i] != (0, 0, 0):
                f = random.randint(4, 7)/10
                colors[i] = tuple(int(c*f) for c in colors[i])
            if min(colors[i]) < 8:
                colors[i] = (0, 0, 0)
                blank.append(i)
        # spawn a few random ones
        random.shuffle(blank)
        for i in range(min(len(blank), random.randint(1, 25))):
            COLS = [
                (255, 255, 255),
                (192, 192, 192),
                (128, 128, 128),
                (255, 0, 0),
                (0, 255, 0),
                (0, 0, 255),
                (255, 255, 0),
                (0, 255, 255),
                (255, 0, 255),
                (255, 128, 0),
                (255, 0, 128),
                (0, 255, 128),
                (0, 128, 255),
                (128, 255, 0),
                (128, 0, 255),
            ]
            colors[blank[i]] = random.choice(COLS)
        yield (colors, 0.1)

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
        if newyear_active():
            g = newyear()
            for (colors, delay) in g:
                yield ('newyear', colors, delay)
        
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
            if newyear_active():
                break # escape to outer loop
            yield (name, colors, delay)
        
        # TODO fade in/out?