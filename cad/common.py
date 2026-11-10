"""Shared geometry helpers: plate outlines, hardware stand-ins, belts, sensor bridge."""
from math import atan2, cos, hypot, pi, sin

import cadquery as cq

from hardware import AS5600, GEARED, GT2_BELT_T, MOTOR_PULLEY, MOTORS, gt2_pitch_r


def polar(n, r, phase=0.0, cx=0.0, cy=0.0):
    return [(cx + r * cos(phase + 2 * pi * k / n), cy + r * sin(phase + 2 * pi * k / n)) for k in range(n)]


def _hull(points):
    pts = sorted(set(points))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def hull_outline(circles=(), rects=(), n=48):
    """Convex outline around circles (cx, cy, r) and axis-aligned rects (x0, y0, x1, y1)."""
    pts = []
    for cx, cy, r in circles:
        pts += [(round(cx + r * cos(2 * pi * k / n), 4), round(cy + r * sin(2 * pi * k / n), 4)) for k in range(n)]
    for x0, y0, x1, y1 in rects:
        pts += [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    return _hull(pts)


def hull_plate(plane, offset, t, circles=(), rects=()):
    """Extrude a convex outline on `plane` ("YZ", "XY", ...) from `offset` by `t` along the plane normal."""
    return cq.Workplane(plane).workplane(offset=offset).polyline(hull_outline(circles, rects)).close().extrude(t)


def holes(plane, offset, t, pts, d):
    return cq.Workplane(plane).workplane(offset=offset).pushPoints(pts).circle(d / 2).extrude(t)


def vol(w):
    return sum(v.Volume() for v in w.vals()) if w.vals() else 0.0


# ------------------------------------------------------------------ hardware stand-ins
# Each built with its axis along +z, mounting face at z = 0, body towards -z, shaft towards +z.
def motor_solid(key):
    m = MOTORS[key]
    body = cq.Workplane("XY").rect(m.face, m.face).extrude(-m.length).edges("|Z").chamfer(3.5)
    body = body.union(cq.Workplane("XY").circle(m.boss_d / 2).extrude(m.boss_h))
    return body.union(cq.Workplane("XY").circle(m.shaft_d / 2).extrude(m.shaft_len))


def motor_holes(key, depth, offset=0.0, slot=0.0, slot_dir=(1, 0), clearance=0.4):
    """Cutter: 4 mounting holes + boss recess + shaft clearance, optionally slotted along slot_dir."""
    m = MOTORS[key]
    h = m.hole_pitch / 2
    pts = [(h, h), (-h, h), (h, -h), (-h, -h), (0, 0)]
    ds = [m.hole_d + clearance] * 4 + [m.boss_d + 1.0]
    cut = None
    for (x, y), d in zip(pts, ds):
        if slot:
            ang = atan2(slot_dir[1], slot_dir[0]) * 180 / pi
            c = (cq.Workplane("XY").workplane(offset=offset).center(x, y)
                 .slot2D(slot + d, d, ang).extrude(depth))
        else:
            c = cq.Workplane("XY").workplane(offset=offset).center(x, y).circle(d / 2).extrude(depth)
        cut = c if cut is None else cut.union(c)
    return cut


def geared_motor_solid(key):
    """28BYJ-48: mounting face (ears) at z = 0, can towards -z, shaft at origin towards +z."""
    g = GEARED[key]
    can = cq.Workplane("XY").center(0, -g.shaft_offset).circle(g.can_d / 2).extrude(-g.can_h)
    ears = (cq.Workplane("XY").center(0, -g.shaft_offset).rect(g.ear_pitch + 7, 7).extrude(-0.8))
    s = can.union(ears).union(cq.Workplane("XY").circle(g.boss_d / 2).extrude(g.boss_h))
    return s.union(cq.Workplane("XY").circle(g.shaft_d / 2).extrude(g.boss_h + g.shaft_len))


def motor_pulley_solid(z0):
    """Bought 20T pulley on a motor shaft; base at z0. Returns (solid, z of tooth centre)."""
    p = MOTOR_PULLEY
    hub = cq.Workplane("XY").workplane(offset=z0).circle(p["hub_d"] / 2).extrude(p["hub_len"])
    teeth_len = p["width"] - p["hub_len"]
    teeth = (cq.Workplane("XY").workplane(offset=z0 + p["hub_len"])
             .circle(p["flange_d"] / 2).extrude(teeth_len))
    return hub.union(teeth), z0 + p["hub_len"] + teeth_len / 2


def motor_pulley_base_for(belt_z):
    p = MOTOR_PULLEY
    return belt_z - p["hub_len"] - (p["width"] - p["hub_len"]) / 2


def belt_solid(c1, t1, c2, t2, z, width=6.0):
    """GT2 loop around two pulleys in the plane z = const. c1, c2 = (x, y) centres."""
    r1, r2 = gt2_pitch_r(t1), gt2_pitch_r(t2)
    outer = hull_outline([(c1[0], c1[1], r1 + GT2_BELT_T / 2), (c2[0], c2[1], r2 + GT2_BELT_T / 2)])
    inner = hull_outline([(c1[0], c1[1], r1 - GT2_BELT_T / 2), (c2[0], c2[1], r2 - GT2_BELT_T / 2)])
    o = cq.Workplane("XY").workplane(offset=z - width / 2).polyline(outer).close().extrude(width)
    i = cq.Workplane("XY").workplane(offset=z - width / 2).polyline(inner).close().extrude(width)
    return o.cut(i)


def box(cx, cy, cz, w, d, h):
    return cq.Workplane("XY").box(w, d, h).translate((cx, cy, cz))


# ------------------------------------------------------------------ AS5600 sensor
def as5600_board(chip_z):
    """Board with the chip face at chip_z, facing +z (towards the magnet). Axis = z."""
    a = AS5600
    back = chip_z - a["chip_from_back"]
    b = cq.Workplane("XY").workplane(offset=back).rect(a["board_w"], a["board_h"]).extrude(a["board_t"])
    return b.union(cq.Workplane("XY").workplane(offset=back + a["board_t"]).rect(5, 5).extrude(1.0))


def as5600_mount_holes(depth, offset):
    a = AS5600
    h = a["hole_pitch"] / 2
    return holes("XY", offset, depth, [(-h, 0), (h, 0)], 1.8)   # M2 self-tapping into plastic


def sensor_bridge(chip_z, base_z, span, t=4.0, post_d=9.0, bolt_d=3.4):
    """Bridge over a pulley carrying an AS5600 whose chip faces +z at chip_z (module frame:
    magnet above, carrier plate face at base_z above that). Posts at (0, +-span) reach up to base_z."""
    a = AS5600
    back = chip_z - a["chip_from_back"]
    z0 = back - t
    strip = cq.Workplane("XY").workplane(offset=z0).rect(14, 2 * span + post_d).extrude(t)
    strip = strip.union(cq.Workplane("XY").workplane(offset=z0).rect(a["board_w"] + 4, a["board_h"] + 4).extrude(t))
    posts = cq.Workplane("XY").workplane(offset=z0).pushPoints([(0, span), (0, -span)]).circle(post_d / 2).extrude(base_z - z0)
    b = strip.union(posts)
    b = b.cut(cq.Workplane("XY").workplane(offset=z0).pushPoints([(0, span), (0, -span)]).circle(bolt_d / 2).extrude(base_z - z0))
    return b.cut(as5600_mount_holes(t, z0))


# ------------------------------------------------------------------ placement
def place_axis_x(w, sign, origin, spin_deg=0.0):
    """Map a part built around +z (module frame) onto an axis along sign * x at `origin`.
    spin_deg turns the part about its own axis first. Module x -> link y; module y -> link sign*z."""
    w = w.rotate((0, 0, 0), (0, 0, 1), spin_deg) if spin_deg else w
    w = w.rotate((0, 0, 0), (1, 1, 1), 120)            # x->y, y->z, z->x
    if sign < 0:
        w = w.rotate((0, 0, 0), (0, 1, 0), 180)        # z->-x, y->-z
    return w.translate(origin)


def rot_x(w, deg, about=(0, 0, 0)):
    return w.rotate(about, (about[0] + 1, about[1], about[2]), deg) if deg else w


def rot_z(w, deg, about=(0, 0, 0)):
    return w.rotate(about, (about[0], about[1], about[2] + 1), deg) if deg else w
