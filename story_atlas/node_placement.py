"""Find free graph space without moving existing nodes or changing zoom."""
import math


def free_position(positions, xlim=(-1, 1), ylim=(-1, 1), size=(800, 500)):
    """Search screen-spaced rings, spilling outside a full viewport as necessary."""
    width, height = (max(1, value) for value in size)
    sx, sy = (xlim[1] - xlim[0]) / width, (ylim[1] - ylim[0]) / height
    cx, cy = sum(xlim) / 2, sum(ylim) / 2
    occupied = [((p[0] - cx) / sx, (p[1] - cy) / sy) for p in positions.values()]
    # Elliptical clearance also leaves room for the usual name/badge labels.
    for ring in range(len(occupied) + 2):
        count = max(1, ring * 8)
        for index in range(count):
            angle = index * math.tau / count
            x, y = ring * 135 * math.cos(angle), ring * 85 * math.sin(angle)
            if all(((x - ox) / 135) ** 2 + ((y - oy) / 85) ** 2 >= .99 for ox, oy in occupied):
                return [cx + x * sx, cy + y * sy]
    raise RuntimeError('No free graph position found')


def reveal_position(axes, point):
    """Pan only if the newly created node would otherwise be off screen."""
    for coordinate, getter, setter in ((point[0], axes.get_xlim, axes.set_xlim),
                                      (point[1], axes.get_ylim, axes.set_ylim)):
        low, high = getter()
        margin = (high - low) * .12
        shift = min(0, coordinate - low - margin) + max(0, coordinate - high + margin)
        if shift:
            setter(low + shift, high + shift)
