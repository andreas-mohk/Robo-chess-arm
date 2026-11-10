"""Wrist bracket (on J4 output), J5 roll (direct drive), and the parallel gripper (J6).

Tool frame: origin on the J4 axis, x = arm lateral, z up, valid when the gripper hangs
vertically (sum of J2 + J3 + J4 = -90 deg). The roll axis is vertical at x = X_G, y = 0.
Gripper frame (inside the tool frame): origin on the roll axis at the gripper's top face,
jaws travel along u (= x when roll = 0), z down is negative.
"""
from math import acos, cos, pi, sin, tan

import cadquery as cq

from common import geared_motor_solid, hull_outline, motor_solid, polar
from config import CFG
from hardware import GEARED, MOTORS
from layout import D4, X_J4_OUT

C = CFG
RM = MOTORS[C.roll_motor]
GM = GEARED[C.gripper_motor]

BRACKET_T = 6.0
X_G = X_J4_OUT + BRACKET_T + 0.8 + RM.face / 2      # roll axis, clear of the J4 drive in x
SHELF_Z = 12.0                                        # shelf top below the J4 axis
SHELF_T = 5.0
HUB_GAP = 0.5
HUB_LEN = 22.0                                        # sets the gripper clear of the J4 drive
HUB_FLANGE_T = 4.0
HUB_FLANGE_D = 36.0
Z_GRIP_TOP = -(SHELF_Z + SHELF_T + HUB_GAP + HUB_LEN)  # gripper top face (tool frame)

# gripper internals (gripper frame, z measured downwards as negative)
G_TOP_T = 5.0
MOD = 1.0                    # gear module
PINION_T = 16
PINION_W = 6.0
ROD_D = 4.0                  # steel rods, the jaw carriages slide on them
ROD_V = 20.0
CARR_U = 14.0                # carriage length along u
CARR_H = 14.0
FINGER_T = 6.0
FINGER_W = 14.0
HALF_OPEN = C.jaw_open_max / 2
WALL_T = 5.0
PINION_R = PINION_T * MOD / 2

Z_MOTOR_PLATE = -(G_TOP_T + 1.0 + GM.can_h)          # top face of the motor plate (motor face sits here)
MOTOR_PLATE_T = 3.0
Z_PINION_TOP = Z_MOTOR_PLATE - MOTOR_PLATE_T - 0.5 - 1.0
Z_PINION_BOT = Z_PINION_TOP - PINION_W
Z_ROD = (Z_PINION_TOP + Z_PINION_BOT) / 2
Z_CARR_TOP = Z_ROD + CARR_H / 2
Z_CARR_BOT = Z_ROD - CARR_H / 2
U_WALL = HALF_OPEN + FINGER_T + CARR_U + 6.0          # inner face of the side walls
Z_TIP = Z_CARR_BOT - C.finger_len                      # fingertips, gripper frame
TOOL_LEN = -(Z_GRIP_TOP + Z_TIP)                       # J4 axis -> fingertips


def wrist_bracket():
    """Vertical plate on the J4 clamp + horizontal shelf carrying the roll motor."""
    x0 = X_J4_OUT
    plate = (cq.Workplane("YZ").workplane(offset=x0)
             .polyline(hull_outline([(0, 0, 16)], [(-23, -(SHELF_Z + SHELF_T), 23, -SHELF_Z)])).close()
             .extrude(BRACKET_T))
    plate = plate.cut(cq.Workplane("YZ").workplane(offset=x0).pushPoints(polar(D4.clamp_bolt_n, D4.clamp_bolt_r))
                      .circle(D4.clamp_bolt_d / 2).extrude(BRACKET_T))
    shelf = cq.Workplane("XY").workplane(offset=-(SHELF_Z + SHELF_T)).center((x0 + X_G + RM.face / 2 + 2) / 2, 0) \
        .rect(X_G + RM.face / 2 + 2 - x0, 46).extrude(SHELF_T)
    gusset = (cq.Workplane("XZ").workplane(offset=-3)
              .polyline([(x0 + BRACKET_T, -SHELF_Z), (x0 + BRACKET_T + 14, -SHELF_Z), (x0 + BRACKET_T, -SHELF_Z + 14)])
              .close().extrude(6))
    b = plate.union(shelf).union(gusset.translate((0, 0, 0)))
    h = RM.hole_pitch / 2
    b = b.cut(cq.Workplane("XY").workplane(offset=-(SHELF_Z + SHELF_T))
              .pushPoints([(X_G + h, h), (X_G - h, h), (X_G + h, -h), (X_G - h, -h)]).circle(1.7).extrude(SHELF_T))
    b = b.cut(cq.Workplane("XY").workplane(offset=-(SHELF_Z + SHELF_T)).center(X_G, 0)
              .circle(RM.boss_d / 2 + 0.5).extrude(SHELF_T))
    return b


def roll_motor():
    """Pancake motor, face down on the shelf, shaft down."""
    return motor_solid(C.roll_motor).rotate((0, 0, 0), (1, 0, 0), 180).translate((X_G, 0, -SHELF_Z))


def roll_hub():
    top = -(SHELF_Z + SHELF_T + HUB_GAP)
    h = cq.Workplane("XY").workplane(offset=top - HUB_LEN).center(X_G, 0).circle(7.5).extrude(HUB_LEN)
    h = h.union(cq.Workplane("XY").workplane(offset=top - HUB_LEN).center(X_G, 0)
                .circle(HUB_FLANGE_D / 2).extrude(HUB_FLANGE_T))
    shaft = (cq.Workplane("XY").workplane(offset=top - HUB_LEN + HUB_FLANGE_T).center(X_G, 0)
             .circle(RM.shaft_d / 2 + 0.1).extrude(HUB_LEN))
    h = h.cut(shaft)
    h = h.cut(cq.Workplane("YZ").workplane(offset=X_G).center(0, top - 5).circle(1.25).extrude(10))   # M3 grub
    h = h.cut(cq.Workplane("XY").workplane(offset=top - HUB_LEN).pushPoints(polar(3, 13, 0, X_G, 0))
              .circle(1.25).extrude(HUB_FLANGE_T))                                                    # M3 taps
    return h


# ------------------------------------------------------------------ gears
def involute_gear(teeth, module, width, bore_d=0.0, bore_flat=0.0, pressure=20.0):
    rp = teeth * module / 2
    rb = rp * cos(pressure * pi / 180)
    ra = rp + module
    rf = rp - 1.25 * module
    inv = lambda a: tan(a) - a
    a_p = acos(rb / rp)
    half_tooth = pi / (2 * teeth) + inv(a_p)
    pts = []
    n = 6
    for k in range(teeth):
        c = 2 * pi * k / teeth
        flank = []
        for i in range(n + 1):
            r = rb + (ra - rb) * i / n
            a = acos(rb / r)
            flank.append((r, inv(a)))
        right = [(r, c - half_tooth + t) for r, t in flank]
        left = [(r, c + half_tooth - t) for r, t in reversed(flank)]
        pts.append((max(rf, 0.1), c - pi / teeth))
        pts.append((min(rf, rb), c - half_tooth))
        pts += right + left
        pts.append((min(rf, rb), c + half_tooth))
    xy = [(r * cos(t), r * sin(t)) for r, t in pts]
    g = cq.Workplane("XY").polyline(xy).close().extrude(width)
    if bore_d:
        hole = cq.Workplane("XY").circle(bore_d / 2).extrude(width)
        if bore_flat:
            hole = hole.cut(cq.Workplane("XY").center(bore_d / 2 + bore_flat / 2 - (bore_d - bore_flat), 0)
                            .rect(bore_d, bore_d).extrude(width).translate((bore_d / 2, 0, 0)))
        g = g.cut(hole)
    return g


def rack(length, module, width, depth=5.0):
    """Teeth along +x, tips at y = module (pitch line y = 0), body towards -y."""
    p = pi * module
    body = cq.Workplane("XY").center(length / 2, -1.25 * module - depth / 2).rect(length, depth).extrude(width)
    teeth = None
    k = 0
    while k * p < length:
        x = k * p
        tw_tip = p / 2 - 2 * module * tan(20 * pi / 180)
        tw_root = p / 2 + 2 * 1.25 * module * tan(20 * pi / 180) - 0.2
        tooth = (cq.Workplane("XY").polyline([(x + p / 2 - tw_root / 2, -1.25 * module), (x + p / 2 + tw_root / 2, -1.25 * module),
                                              (x + p / 2 + tw_tip / 2, module), (x + p / 2 - tw_tip / 2, module)])
                 .close().extrude(width))
        teeth = tooth if teeth is None else teeth.union(tooth)
        k += 1
    return body.union(teeth).intersect(cq.Workplane("XY").center(length / 2, 0).rect(length, 30).extrude(width))


# ------------------------------------------------------------------ gripper (gripper frame)
def gripper_frame():
    """Top plate, two side walls holding the rods, motor plate."""
    top = cq.Workplane("XY").workplane(offset=-G_TOP_T).rect(2 * (U_WALL + WALL_T), 2 * (ROD_V + 6)).extrude(G_TOP_T)
    top = top.cut(cq.Workplane("XY").workplane(offset=-G_TOP_T).pushPoints(polar(3, 13)).circle(1.7).extrude(G_TOP_T))
    walls = (cq.Workplane("XY").workplane(offset=Z_ROD - 7).pushPoints([(U_WALL + WALL_T / 2, 0), (-U_WALL - WALL_T / 2, 0)])
             .rect(WALL_T, 2 * (ROD_V + 6)).extrude(-G_TOP_T - (Z_ROD - 7)))
    f = top.union(walls)
    # motor plate between the walls, motor can above it
    mp = cq.Workplane("XY").workplane(offset=Z_MOTOR_PLATE - MOTOR_PLATE_T).rect(2 * U_WALL, 2 * (ROD_V - 4)).extrude(MOTOR_PLATE_T)
    mp = mp.cut(cq.Workplane("XY").workplane(offset=Z_MOTOR_PLATE - MOTOR_PLATE_T).circle(GM.boss_d / 2 + 0.5).extrude(MOTOR_PLATE_T))
    mp = mp.cut(cq.Workplane("XY").workplane(offset=Z_MOTOR_PLATE - MOTOR_PLATE_T)
                .pushPoints([(GM.ear_pitch / 2, GM.shaft_offset), (-GM.ear_pitch / 2, GM.shaft_offset)])
                .circle(1.5).extrude(MOTOR_PLATE_T))
    f = f.union(mp)
    f = f.cut(cq.Workplane("YZ").workplane(offset=-U_WALL - WALL_T).pushPoints([(ROD_V, Z_ROD), (-ROD_V, Z_ROD)])
              .circle(ROD_D / 2 - 0.05).extrude(2 * (U_WALL + WALL_T)))
    return f


def gripper_motor():
    return geared_motor_solid(C.gripper_motor).rotate((0, 0, 0), (1, 0, 0), 180).translate((0, 0, Z_MOTOR_PLATE))


def pinion():
    return involute_gear(PINION_T, MOD, PINION_W, bore_d=GM.shaft_d + 0.1, bore_flat=GM.shaft_flat).translate((0, 0, Z_PINION_BOT))


def carriage(side, opening):
    """side = +1 or -1. Carriage + finger + rack, positioned for the given finger gap."""
    s = side
    inner = opening / 2
    u0 = s * (inner + FINGER_T)                     # carriage inner face
    blk = cq.Workplane("XY").workplane(offset=Z_CARR_BOT).center(u0 + s * CARR_U / 2, 0) \
        .rect(CARR_U, 2 * (ROD_V + 5)).extrude(CARR_H)
    blk = blk.cut(cq.Workplane("YZ").workplane(offset=-U_WALL).pushPoints([(ROD_V, Z_ROD), (-ROD_V, Z_ROD)])
                  .circle(ROD_D / 2 + 0.2).extrude(2 * U_WALL))
    # rack arm: pitch line at v = s * PINION_R, teeth facing the pinion
    r_len = HALF_OPEN + 2 * PINION_R + 6
    rk = rack(r_len, MOD, PINION_W)
    if s > 0:
        rk = rk.rotate((0, 0, 0), (1, 0, 0), 180).translate((0, 0, PINION_W))   # teeth towards -v
        rk = rk.translate((u0 + 1 - r_len, PINION_R, Z_PINION_BOT))
    else:
        rk = rk.translate((u0 - 1, -PINION_R, Z_PINION_BOT))
    # finger hangs from the carriage, inner face at u = s * inner
    fz_top = Z_CARR_BOT
    finger = cq.Workplane("XY").workplane(offset=Z_TIP).center(s * (inner + FINGER_T / 2), 0) \
        .rect(FINGER_T, FINGER_W).extrude(fz_top - Z_TIP)
    finger = finger.cut(cq.Workplane("XZ").workplane(offset=-FINGER_W).center(s * inner, Z_TIP + 15)
                        .rect(2.0, 24).extrude(2 * FINGER_W))      # shallow groove on the inner face
    return blk.union(rk).union(finger)


def gripper_rods():
    return cq.Workplane("YZ").workplane(offset=-U_WALL - WALL_T).pushPoints([(ROD_V, Z_ROD), (-ROD_V, Z_ROD)]) \
        .circle(ROD_D / 2).extrude(2 * (U_WALL + WALL_T))


def build_gripper(opening=None):
    o = C.jaw_open_max * 0.7 if opening is None else opening
    printed = {"gripper_frame": gripper_frame(), "pinion": pinion(),
               "jaw_a": carriage(+1, o), "jaw_b": carriage(-1, o)}
    hardware = {"gripper_motor": gripper_motor(), "gripper_rods": gripper_rods()}
    return printed, hardware


def build_wrist(roll_deg=0.0, opening=None):
    """Printed parts and hardware in the tool frame."""
    gp, gh = build_gripper(opening)
    place = lambda w: w.rotate((0, 0, 0), (0, 0, 1), roll_deg).translate((X_G, 0, Z_GRIP_TOP))
    printed = {"wrist_bracket": wrist_bracket(), "roll_hub": roll_hub()}
    printed.update({k: place(v) for k, v in gp.items()})
    hardware = {"roll_motor": roll_motor()}
    hardware.update({k: place(v) for k, v in gh.items()})
    return printed, hardware


if __name__ == "__main__":
    print(f"X_G {X_G:.1f}, tool length {TOOL_LEN:.1f} (target {C.tool_len_target}), gripper width {2 * (U_WALL + WALL_T):.0f}")
