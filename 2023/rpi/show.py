def generator():
    colors = [
        [
            (32, 0, 0),
            (0, 32, 0),
            (0, 0, 32),
        ][i%3]
        for i in range(3*80)
    ]
    while True:
        colors = colors[1:] + [colors[0]]
        yield ('rgb loop', colors, 0.1)