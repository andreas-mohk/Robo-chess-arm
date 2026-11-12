"""Base (electronics box + J1 carrier + lower ball race) and turntable (upper race + tower mount).

Base parts are in the world frame. The turntable and everything on it are in the arm frame:
the J1 axis is at arm x = yaw_x, y = 0 (assembly rotates the arm frame about it).
"""
from math import cos, pi, radians, sin

import cadquery as cq

from common import box, hull_outline, polar
from config import CFG
from hardware import BUCK, BUTTON, COMPUTERS, DC_JACK_D, ESP32_BOARD, OLED
from joints import JointKit
from layout import D1, Z_BASE_TOP, Z_TT, Z_TT_TOP

C = CFG
W, Dp, H, WALL, TOP_T = C.base_w, C.base_d, C.base_h, C.base_wall, C.base_top_t
SHELF_T = 3.0
FLOOR_T = 3.0
BALL_DEPTH = 0.35 * C.ball_d          # groove depth in each race
YX = C.yaw_x

K1 = JointKit("J1", D1, C.joints["J1"].motor, TOP_T, C.joints["J1"].motor_r, C.joints["J1"].motor_angle,
              shelf_motor=True, shelf_t=SHELF_T)

# electronics layout (world X, Y of each board centre) -- move freely, the build checks for clashes
LAYOUT = {
    "computer": (-50.0, -46.0),
    "esp32_board": (39.0, -51.0),
    "buck": (55.0, 38.0),
}


def _at_base(w):
    return w.translate((0, 0, Z_BASE_TOP))


def _race_groove(z_face, up):
    """Torus-shaped groove of depth BALL_DEPTH around the yaw axis, cut into a face at z_face."""
    r_b = C.ball_d / 2 + 0.1
    zc = z_face - (r_b - BALL_DEPTH) if up else z_face + (r_b - BALL_DEPTH)
    return cq.Workplane("XY").add(cq.Solid.makeTorus(C.race_r, r_b, pnt=cq.Vector(0, 0, zc)))


def ball_z():
    return Z_BASE_TOP - BALL_DEPTH + C.ball_d / 2


def base_shell():
    s = cq.Workplane("XY").box(W, Dp, H).translate((0, 0, H / 2)).edges("|Z").fillet(8)
    s = s.cut(cq.Workplane("XY").box(W - 2 * WALL, Dp - 2 * WALL, H - TOP_T).translate((0, 0, (H - TOP_T) / 2)).edges("|Z").fillet(5))
    s = s.cut(_at_base(K1.carrier_cutter()))
    s = s.cut(_race_groove(Z_BASE_TOP, up=False))
    # cable passage under the turntable, on the side away from the J1 belt
    a = radians(C.joints["J1"].motor_angle + 180)
    s = s.cut(cq.Workplane("XY").workplane(offset=Z_BASE_TOP - TOP_T).center(55 * cos(a), 55 * sin(a))
              .slot2D(34, 12, C.joints["J1"].motor_angle + 90).extrude(TOP_T))
    # clearance pocket for the J1 motor shaft tip under the top plate
    mx, my = K1.mxy
    s = s.cut(cq.Workplane("XY").workplane(offset=Z_BASE_TOP - TOP_T).center(mx, my).circle(4.5).extrude(TOP_T - 1.5))
    # motor shelf posts (M3 into the top plate)
    for p in _shelf_posts():
        s = s.cut(cq.Workplane("XY").workplane(offset=Z_BASE_TOP - TOP_T).center(*p).circle(1.25).extrude(TOP_T - 1))
    # front panel: OLED window and buttons (front = +Y, faces the board and the player)
    o = OLED[C.oled]
    ox, oz = 52.0, H / 2 + 3
    s = s.cut(cq.Workplane("XZ").workplane(offset=-Dp / 2 - 1).center(ox, oz + o["window_dy"])
              .rect(o["window_w"], o["window_h"]).extrude(WALL + 2))
    s = s.cut(cq.Workplane("XZ").workplane(offset=-Dp / 2 - 1)
              .pushPoints([(ox - o["hole_pitch_x"] / 2, oz - o["hole_pitch_y"] / 2), (ox + o["hole_pitch_x"] / 2, oz - o["hole_pitch_y"] / 2),
                           (ox - o["hole_pitch_x"] / 2, oz + o["hole_pitch_y"] / 2), (ox + o["hole_pitch_x"] / 2, oz + o["hole_pitch_y"] / 2)])
              .circle(1.0).extrude(WALL + 2))
    bx = [-60.0 + 22 * i for i in range(C.buttons)]
    s = s.cut(cq.Workplane("XZ").workplane(offset=-Dp / 2 - 1).pushPoints([(x, H / 2) for x in bx])
              .circle(BUTTON["hole_d"] / 2).extrude(WALL + 2))
    # rear panel: DC jack, cable slot (webcam USB, Pi access)
    s = s.cut(cq.Workplane("XZ").workplane(offset=Dp / 2 - WALL - 1).center(70, H / 2 - 8).circle(DC_JACK_D / 2).extrude(WALL + 2))
    s = s.cut(cq.Workplane("XZ").workplane(offset=Dp / 2 - WALL - 1).center(-50, 14).rect(40, 14).extrude(WALL + 2))
    # side vents
    for x in (W / 2 - WALL - 1, -W / 2 - 1):
        s = s.cut(cq.Workplane("YZ").workplane(offset=x).pushPoints([(y, H / 2 - 4) for y in range(-50, 51, 12)])
                  .rect(5, 22).extrude(WALL + 2))
    # floor screw bosses in the corners
    corners = [(sx * (W / 2 - 10), sy * (Dp / 2 - 10)) for sx in (1, -1) for sy in (1, -1)]
    bosses = cq.Workplane("XY").workplane(offset=FLOOR_T).pushPoints(corners).circle(5).extrude(H - TOP_T - FLOOR_T)
    bosses = bosses.cut(cq.Workplane("XY").workplane(offset=FLOOR_T).pushPoints(corners).circle(1.25).extrude(20))
    return s.union(bosses)


def base_floor():
    f = cq.Workplane("XY").box(W - 2 * WALL - 0.6, Dp - 2 * WALL - 0.6, FLOOR_T).translate((0, 0, FLOOR_T / 2)).edges("|Z").fillet(4.5)
    corners = [(sx * (W / 2 - 10), sy * (Dp / 2 - 10)) for sx in (1, -1) for sy in (1, -1)]
    f = f.cut(cq.Workplane("XY").pushPoints(corners).circle(1.7).extrude(FLOOR_T))
    # bolts into the shared baseplate (keeps the board registered to the arm)
    f = f.cut(cq.Workplane("XY").pushPoints([(sx * 70, sy * 25) for sx in (1, -1) for sy in (1, -1)]).circle(2.2).extrude(FLOOR_T))
    for key, spec, d in (("computer", COMPUTERS[C.computer], 2.2), ("esp32_board", ESP32_BOARD, 2.6), ("buck", BUCK, 2.6)):
        cx, cy = LAYOUT[key]
        hx, hy = spec["holes"][0] / 2, spec["holes"][1] / 2
        pts = [(cx + sx * hx, cy + sy * hy) for sx in (1, -1) for sy in (1, -1)]
        f = f.union(cq.Workplane("XY").workplane(offset=FLOOR_T).pushPoints(pts).circle(3).extrude(5)
                    .cut(cq.Workplane("XY").workplane(offset=FLOOR_T).pushPoints(pts).circle(d / 2).extrude(5)))
    return f


def _shelf_posts():
    a = radians(C.joints["J1"].motor_angle)
    mx, my = K1.mxy
    # two posts beside the motor, either side of the belt line, beyond the pulley
    return [(mx + 26 * cos(a + s * pi / 2) + 10 * cos(a), my + 26 * sin(a + s * pi / 2) + 10 * sin(a)) for s in (1, -1)]


def j1_motor_shelf():
    """Plate under the belt that holds the J1 motor face-up; hangs from the base top on two posts."""
    mx, my = K1.mxy
    z_face = Z_BASE_TOP + K1.motor_face_z
    posts = _shelf_posts()
    outline = hull_outline([(mx, my, 25)] + [(px, py, 5) for px, py in posts])
    sh = cq.Workplane("XY").workplane(offset=z_face).polyline(outline).close().extrude(SHELF_T)
    top = Z_BASE_TOP - TOP_T
    sh = sh.union(cq.Workplane("XY").workplane(offset=z_face).pushPoints(posts).circle(4.5).extrude(top - z_face))
    sh = sh.cut(cq.Workplane("XY").workplane(offset=z_face).pushPoints(posts).circle(1.7).extrude(top - z_face))
    from hardware import MOTORS
    m = MOTORS[C.joints["J1"].motor]
    h = m.hole_pitch / 2
    a = radians(C.joints["J1"].motor_angle)
    slot = lambda x, y, d: cq.Workplane("XY").workplane(offset=z_face).center(x, y).slot2D(6 + d, d, C.joints["J1"].motor_angle).extrude(SHELF_T)
    for x, y in [(h, h), (-h, h), (h, -h), (-h, -h)]:
        sh = sh.cut(slot(mx + x, my + y, 3.4))
    return sh.cut(slot(mx, my, m.boss_d + 1))


def turntable():
    """Disc on the J1 clamp with a skirt down to the ball race. Arm frame (J1 axis at x = yaw_x)."""
    r_in = C.race_r - 6
    t = cq.Workplane("XY").workplane(offset=Z_TT).circle(C.turntable_r).extrude(C.turntable_t)
    skirt_bot = Z_BASE_TOP + C.ball_d - 2 * BALL_DEPTH
    skirt = cq.Workplane("XY").workplane(offset=skirt_bot).circle(C.race_r + 6).circle(r_in).extrude(Z_TT - skirt_bot)
    t = t.union(skirt)
    t = t.cut(_race_groove(skirt_bot, up=True).translate((0, 0, 0)))
    pts = polar(D1.clamp_bolt_n, D1.clamp_bolt_r)
    t = t.cut(cq.Workplane("XY").workplane(offset=Z_TT).pushPoints(pts).circle(D1.clamp_bolt_d / 2).extrude(C.turntable_t))
    t = t.cut(cq.Workplane("XY").workplane(offset=Z_TT_TOP - 3.2).pushPoints(pts).circle(3.1).extrude(3.2))
    # cable hole lines up with the base slot at J1 = 0
    a = radians(C.joints["J1"].motor_angle + 180)
    t = t.cut(cq.Workplane("XY").workplane(offset=Z_TT).center(55 * cos(a), 55 * sin(a)).circle(9).extrude(C.turntable_t))
    t = t.translate((YX, 0, 0))
    # tower foot holes (M4), must match links.tower()
    from links import X_TOWER
    x0 = X_TOWER - C.tower_t
    fp = [(x0 - 20, -C.tower_w / 2 + 10), (x0 - 20, C.tower_w / 2 - 10), (x0 - 4, -C.tower_w / 2 + 10), (x0 - 4, C.tower_w / 2 - 10)]
    t = t.cut(cq.Workplane("XY").workplane(offset=Z_TT).pushPoints(fp).circle(2.2).extrude(C.turntable_t))
    return t


def balls():
    n = int(2 * pi * C.race_r / (C.ball_d + 1.0))
    return cq.Workplane("XY").add([cq.Solid.makeSphere(C.ball_d / 2, cq.Vector(x, y, ball_z()))
                                   for x, y in polar(n, C.race_r)]), n


def electronics():
    out = {}
    z0 = FLOOR_T + 5
    for key, spec in (("computer", COMPUTERS[C.computer]), ("esp32_board", ESP32_BOARD), ("buck", BUCK)):
        cx, cy = LAYOUT[key]
        out[key] = box(cx, cy, z0 + spec["h"] / 2, spec["w"], spec["d"], spec["h"])
    o = OLED[C.oled]
    out["oled"] = box(52.0, Dp / 2 - WALL - 3, H / 2 + 3, o["board_w"], 4, o["board_h"])
    return out


def base_group():
    """World frame: static base parts, J1 static drive parts, J1 motor/belt/sensor."""
    printed = {"base_shell": base_shell(), "base_floor": base_floor(), "j1_motor_shelf": j1_motor_shelf()}
    printed.update({k: _at_base(v) for k, v in K1.printed.items()})
    b, n = balls()
    hardware = {k: _at_base(v) for k, v in K1.all_hardware().items()}
    hardware["race_balls"] = b
    hardware.update(electronics())
    drive = {k: _at_base(v) for k, v in K1.static.items()}
    return printed, hardware, drive, n


def turntable_group():
    """Arm frame: turntable + J1 output parts."""
    printed = {"turntable": turntable()}
    drive = {k: v.translate((YX, 0, Z_BASE_TOP)) for k, v in K1.output.items()}
    return printed, {}, drive
