"""Wrist bracket (on J4 output), J5 roll, and the parallel gripper (J6).

Tool frame: origin on the J4 axis, x = arm lateral, z up, valid when the gripper hangs
vertically (sum of J2 + J3 + J4 = -90 deg). The roll axis is vertical at x = X_G, y = 0.
Gripper frame (inside the tool frame): origin on the roll axis at the gripper's top face,
jaws travel along u (= x when roll = 0), z down is negative.

Roll: the pancake motor sits face-down on the bracket shelf. A 6804 bearing in the shelf
carries the gripper (weight and side loads); the motor shaft only drives the hub through
a D-bore, so the motor's own bearings see torque, not load.

Gripper: a closed box frame (top, two end walls holding 6 mm rods, two side walls, and a
motor plate across the middle). Each jaw carriage runs on two LM6UU bushings and carries a
tapered finger and a rack. The racks sit above the carriages so they pass over the other
jaw. A 28BYJ-48 turns a 16T pinion between the racks; a microswitch on the end wall homes
the jaws at full open.
"""
from math import acos, cos, pi, sin, tan

import cadquery as cq

from common import geared_motor_solid, hull_outline, motor_solid, polar
from config import CFG
from hardware import BEARINGS, GEARED, LM6UU, MICROSWITCH, MOTORS
from layout import D4, X_J4_OUT

C = CFG
RM = MOTORS[C.roll_motor]
GM = GEARED[C.gripper_motor]
RB = BEARINGS["6804"]                                 # roll bearing

# ---------------- wrist and roll (tool frame)
BRACKET_T = 6.0
X_G = X_J4_OUT + BRACKET_T + 0.8 + RM.face / 2      # roll axis, clear of the J4 drive in x
SHELF_Z = 12.0                                        # shelf top (= roll motor face) below the J4 axis
SHELF_T = 5.0
Z_FACE = -SHELF_Z
Z_SHOULDER_TOP = Z_FACE - RM.boss_h - 0.5            # hub shoulder, just under the motor boss
SHOULDER_T = 1.5
Z_BRG_TOP = Z_SHOULDER_TOP - SHOULDER_T
Z_BRG_BOT = Z_BRG_TOP - RB.B
LIP_T = 2.0
Z_BOSS_BOT = Z_BRG_BOT - LIP_T
BOSS_D = RB.D + 8.0
GRIP_TOP_DROP = 39.5                                  # gripper top below the J4 axis: clears the J4 drive
Z_GRIP_TOP = -GRIP_TOP_DROP
HUB_FLANGE_D = 40.0
HUB_FLANGE_T = 5.0
HUB_BOLT_R = 17.0

# ---------------- gripper (gripper frame)
G_TOP_T = 5.0
MOD = 1.0
PINION_T = 16
PINION_W = 6.5
PINION_R = PINION_T * MOD / 2
ROD_D = LM6UU["d"]
ROD_V = 24.0                    # rods at v = +-ROD_V
CARR_U = 24.0                   # carriage length along u (LM6UU is 19 long)
CARR_H = 18.0
CARR_V = ROD_V + LM6UU["D"] / 2 + 3.0
FINGER_ROOT = (10.0, 20.0)      # thickness along u, width along v
FINGER_TIP = (6.0, 14.0)
HALF_OPEN = C.jaw_open_max / 2
WALL_T = 5.0                    # end walls (hold the rods)
SIDE_T = 3.0
MOTOR_PLATE_T = 3.0

Z_MOTOR_PLATE = -(G_TOP_T + 1.0 + GM.can_h)          # motor face sits on top of this plate
Z_PINION_TOP = Z_MOTOR_PLATE - MOTOR_PLATE_T - 1.5
Z_PINION_BOT = Z_PINION_TOP - PINION_W
Z_CARR_TOP = Z_PINION_BOT - 1.0                       # racks run 1 mm above the carriages
Z_CARR_BOT = Z_CARR_TOP - CARR_H
Z_ROD = Z_CARR_TOP - CARR_H / 2
Z_FRAME_BOT = Z_ROD - ROD_D / 2 - 6.0
U_IN = HALF_OPEN + CARR_U + 3.0                       # inner face of the end walls
V_IN = CARR_V + 1.5                                   # inner face of the side walls
Z_TIP = Z_CARR_BOT - C.finger_len
TOOL_LEN = -(Z_GRIP_TOP + Z_TIP)                       # J4 axis -> fingertips
RACK_LEN = HALF_OPEN + CARR_U + PINION_R + 6.0


def wrist_bracket():
    """Vertical plate on the J4 clamp + horizontal shelf with the roll motor and the 6804 boss."""
    x0 = X_J4_OUT
    plate = (cq.Workplane("YZ").workplane(offset=x0)
             .polyline(hull_outline([(0, 0, 16)], [(-23, -(SHELF_Z + SHELF_T), 23, -SHELF_Z)])).close()
             .extrude(BRACKET_T))
    plate = plate.cut(cq.Workplane("YZ").workplane(offset=x0).pushPoints(polar(D4.clamp_bolt_n, D4.clamp_bolt_r))
                      .circle(D4.clamp_bolt_d / 2).extrude(BRACKET_T))
    x1 = X_G + RM.face / 2 + 2
    shelf = cq.Workplane("XY").workplane(offset=-(SHELF_Z + SHELF_T)).center((x0 + x1) / 2, 0) \
        .rect(x1 - x0, 46).extrude(SHELF_T)
    boss = cq.Workplane("XY").workplane(offset=Z_BOSS_BOT).center(X_G, 0).circle(BOSS_D / 2) \
        .extrude(-(SHELF_Z + SHELF_T) - Z_BOSS_BOT)
    gussets = None
    for y in (-20.0, 17.0):
        g = (cq.Workplane("XZ").workplane(offset=-y - 3)
             .polyline([(x0 + BRACKET_T, -SHELF_Z), (x0 + BRACKET_T + 16, -SHELF_Z), (x0 + BRACKET_T, -SHELF_Z + 14)])
             .close().extrude(3))
        gussets = g if gussets is None else gussets.union(g)
    b = plate.union(shelf).union(boss).union(gussets)
    h = RM.hole_pitch / 2
    b = b.cut(cq.Workplane("XY").workplane(offset=-(SHELF_Z + SHELF_T))
              .pushPoints([(X_G + h, h), (X_G - h, h), (X_G + h, -h), (X_G - h, -h)]).circle(1.7).extrude(SHELF_T))
    # bearing pocket from the top (bearing drops in before the motor goes on), lip at the bottom
    b = b.cut(cq.Workplane("XY").workplane(offset=Z_BRG_BOT).center(X_G, 0).circle(RB.D / 2 - 0.05).extrude(Z_FACE - Z_BRG_BOT))
    b = b.cut(cq.Workplane("XY").workplane(offset=Z_BOSS_BOT).center(X_G, 0).circle(RB.d / 2 + 3.0).extrude(LIP_T))
    return b


def roll_motor():
    """Pancake motor, face down on the shelf, shaft down."""
    return motor_solid(C.roll_motor).rotate((0, 0, 0), (1, 0, 0), 180).translate((X_G, 0, Z_FACE))


def roll_bearing():
    return cq.Workplane("XY").workplane(offset=Z_BRG_BOT).center(X_G, 0).circle(RB.D / 2).circle(RB.d / 2).extrude(RB.B)


def roll_hub():
    """Shoulder on the bearing's inner race, sleeve through it, flange that carries the gripper.
    Driven by the motor shaft through a D-bore; hangs on the bearing, not on the motor."""
    z_sleeve_bot = Z_BOSS_BOT - 0.5
    h = cq.Workplane("XY").workplane(offset=Z_BRG_TOP).center(X_G, 0).circle(RB.d / 2 + 2.5).extrude(SHOULDER_T)
    h = h.union(cq.Workplane("XY").workplane(offset=z_sleeve_bot).center(X_G, 0).circle(RB.d / 2 - 0.02)
                .extrude(Z_BRG_TOP - z_sleeve_bot))
    h = h.union(cq.Workplane("XY").workplane(offset=Z_GRIP_TOP).center(X_G, 0).circle(15).extrude(z_sleeve_bot - Z_GRIP_TOP))
    h = h.union(cq.Workplane("XY").workplane(offset=Z_GRIP_TOP).center(X_G, 0).circle(HUB_FLANGE_D / 2).extrude(HUB_FLANGE_T))
    shaft_end = Z_FACE - RM.boss_h - RM.shaft_len
    bore = cq.Workplane("XY").workplane(offset=shaft_end - 1).center(X_G, 0).circle(RM.shaft_d / 2 + 0.05) \
        .extrude(Z_SHOULDER_TOP - shaft_end + 1)
    flat = cq.Workplane("XY").workplane(offset=shaft_end - 1).center(X_G + RM.shaft_d / 2 - 0.5 + 5, 0) \
        .rect(10, 10).extrude(Z_SHOULDER_TOP - shaft_end + 1)
    h = h.cut(bore.cut(flat))
    return h.cut(cq.Workplane("XY").workplane(offset=Z_GRIP_TOP).pushPoints(polar(3, HUB_BOLT_R, 0, X_G, 0))
                 .circle(1.7).extrude(HUB_FLANGE_T))


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
    """Closed box: top plate, end walls with the rods, side walls, motor plate across the middle."""
    ou, ov = U_IN + WALL_T, V_IN + SIDE_T
    f = cq.Workplane("XY").workplane(offset=Z_FRAME_BOT).rect(2 * ou, 2 * ov).extrude(-Z_FRAME_BOT)
    f = f.edges("|Z").fillet(3)
    f = f.cut(cq.Workplane("XY").workplane(offset=Z_FRAME_BOT).rect(2 * U_IN, 2 * V_IN).extrude(-Z_FRAME_BOT - G_TOP_T))
    mp = cq.Workplane("XY").workplane(offset=Z_MOTOR_PLATE - MOTOR_PLATE_T).rect(2 * U_IN, 2 * V_IN).extrude(MOTOR_PLATE_T)
    mp = mp.cut(cq.Workplane("XY").workplane(offset=Z_MOTOR_PLATE - MOTOR_PLATE_T).circle(GM.boss_d / 2 + 0.5).extrude(MOTOR_PLATE_T))
    mp = mp.cut(cq.Workplane("XY").workplane(offset=Z_MOTOR_PLATE - MOTOR_PLATE_T)
                .pushPoints([(GM.ear_pitch / 2, GM.shaft_offset), (-GM.ear_pitch / 2, GM.shaft_offset)])
                .circle(1.5).extrude(MOTOR_PLATE_T))
    f = f.union(mp)
    # rods in the end walls
    f = f.cut(cq.Workplane("YZ").workplane(offset=-ou).pushPoints([(ROD_V, Z_ROD), (-ROD_V, Z_ROD)])
              .circle(ROD_D / 2 - 0.05).extrude(2 * ou))
    # hub bolts, cable slot for the gripper motor
    f = f.cut(cq.Workplane("XY").workplane(offset=-G_TOP_T).pushPoints(polar(3, HUB_BOLT_R)).circle(1.25).extrude(G_TOP_T))
    f = f.cut(cq.Workplane("XY").workplane(offset=-G_TOP_T).center(-30, 22).rect(14, 6).extrude(G_TOP_T))
    # home switch outside the +u end wall, its lever reaches the jaw through a slot
    m = MICROSWITCH
    f = f.cut(cq.Workplane("XY").workplane(offset=Z_ROD - 3).center(U_IN + WALL_T / 2, -14).rect(WALL_T + 1, 4).extrude(6))
    f = f.cut(cq.Workplane("YZ").workplane(offset=U_IN).pushPoints([(-14 - m["hole_pitch"] / 2, Z_ROD + 1), (-14 + m["hole_pitch"] / 2, Z_ROD + 1)])
              .circle(1.0).extrude(WALL_T))
    return f


def home_switch():
    m = MICROSWITCH
    return cq.Workplane("XY").box(m["d"], m["w"], m["h"]).translate((U_IN + WALL_T + m["d"] / 2, -14, Z_ROD + 1))


def gripper_motor():
    return geared_motor_solid(C.gripper_motor).rotate((0, 0, 0), (1, 0, 0), 180).translate((0, 0, Z_MOTOR_PLATE))


def pinion():
    return involute_gear(PINION_T, MOD, PINION_W, bore_d=GM.shaft_d + 0.1, bore_flat=GM.shaft_flat).translate((0, 0, Z_PINION_BOT))


def _finger(s, inner):
    """Tapered finger, inner face vertical at u = s * inner, root under the carriage."""
    (tr, wr), (tt, wt) = FINGER_ROOT, FINGER_TIP
    root = cq.Wire.makePolygon([cq.Vector(s * inner, -wr / 2, Z_CARR_BOT + 0.01), cq.Vector(s * (inner + tr), -wr / 2, Z_CARR_BOT + 0.01),
                                cq.Vector(s * (inner + tr), wr / 2, Z_CARR_BOT + 0.01), cq.Vector(s * inner, wr / 2, Z_CARR_BOT + 0.01)], close=True)
    tip = cq.Wire.makePolygon([cq.Vector(s * inner, -wt / 2, Z_TIP), cq.Vector(s * (inner + tt), -wt / 2, Z_TIP),
                               cq.Vector(s * (inner + tt), wt / 2, Z_TIP), cq.Vector(s * inner, wt / 2, Z_TIP)], close=True)
    f = cq.Workplane("XY").add(cq.Solid.makeLoft([root, tip], True))
    # vertical V-groove on the inner face near the tip, centres round pieces
    g = cq.Workplane("XY").workplane(offset=Z_TIP).polyline(
        [(s * (inner - 0.1), -2.5), (s * (inner + 2.0), 0), (s * (inner - 0.1), 2.5)]).close().extrude(30)
    return f.cut(g)


def carriage(side, opening):
    """side = +1 or -1. Carriage (two LM6UU) + finger + rack, positioned for a given finger gap."""
    s = side
    inner = opening / 2
    u_lo, u_hi = sorted((s * inner, s * (inner + CARR_U)))
    blk = cq.Workplane("XY").workplane(offset=Z_CARR_BOT).center((u_lo + u_hi) / 2, 0).rect(CARR_U, 2 * CARR_V).extrude(CARR_H)
    blk = blk.edges("|X").fillet(2)
    blk = blk.cut(cq.Workplane("YZ").workplane(offset=u_lo - 1).pushPoints([(ROD_V, Z_ROD), (-ROD_V, Z_ROD)])
                  .circle(LM6UU["D"] / 2 - 0.05).extrude(CARR_U + 2))                       # bushing pockets
    # rack: pitch line at v = s * PINION_R, teeth towards the pinion, running above the carriages
    far = s * (inner + CARR_U - 2)
    rk = rack(RACK_LEN, MOD, PINION_W)
    if s > 0:
        rk = rk.rotate((0, 0, 0), (1, 0, 0), 180).translate((far - RACK_LEN, PINION_R, Z_PINION_TOP))
    else:
        rk = rk.translate((far, -PINION_R, Z_PINION_BOT))
    riser = cq.Workplane("XY").workplane(offset=Z_CARR_TOP - 0.01).center((u_lo + u_hi) / 2, s * (PINION_R + 4.5)) \
        .rect(CARR_U - 4, 9).extrude(1.02)
    return blk.union(riser).union(rk).union(_finger(s, inner))


def bushings(opening):
    out = None
    for s in (1, -1):
        inner = opening / 2
        u0 = min(s * inner, s * (inner + CARR_U)) + (CARR_U - LM6UU["L"]) / 2
        b = (cq.Workplane("YZ").workplane(offset=u0).pushPoints([(ROD_V, Z_ROD), (-ROD_V, Z_ROD)])
             .circle(LM6UU["D"] / 2).circle(LM6UU["d"] / 2 + 0.3).extrude(LM6UU["L"]))
        out = b if out is None else out.union(b)
    return out


def gripper_rods():
    ou = U_IN + WALL_T
    return cq.Workplane("YZ").workplane(offset=-ou).pushPoints([(ROD_V, Z_ROD), (-ROD_V, Z_ROD)]).circle(ROD_D / 2).extrude(2 * ou)


def build_gripper(opening=None):
    o = C.jaw_open_max * 0.7 if opening is None else opening
    printed = {"gripper_frame": gripper_frame(), "pinion": pinion(), "jaw_a": carriage(+1, o), "jaw_b": carriage(-1, o)}
    hardware = {"gripper_motor": gripper_motor(), "gripper_rods": gripper_rods(), "lm6uu": bushings(o),
                "home_switch": home_switch()}
    return printed, hardware


def build_wrist(roll_deg=0.0, opening=None):
    """Printed parts and hardware in the tool frame."""
    gp, gh = build_gripper(opening)
    place = lambda w: w.rotate((0, 0, 0), (0, 0, 1), roll_deg).translate((X_G, 0, Z_GRIP_TOP))
    printed = {"wrist_bracket": wrist_bracket(), "roll_hub": roll_hub().translate((-X_G, 0, 0)).rotate((0, 0, 0), (0, 0, 1), roll_deg).translate((X_G, 0, 0))}
    printed.update({k: place(v) for k, v in gp.items()})
    hardware = {"roll_motor": roll_motor(), "roll_bearing": roll_bearing()}
    hardware.update({k: place(v) for k, v in gh.items()})
    return printed, hardware


def internal_clashes(openings=(10.0, 0.5 * C.jaw_open_max, C.jaw_open_max)):
    """Overlaps inside the gripper over its opening range. Rack/pinion mesh and bushing seats are expected
    contacts and are skipped."""
    expected = {frozenset(p) for p in (("jaw_a", "pinion"), ("jaw_b", "pinion"), ("jaw_a", "lm6uu"), ("jaw_b", "lm6uu"),
                                       ("gripper_frame", "gripper_rods"), ("lm6uu", "gripper_rods"),
                                       ("pinion", "gripper_motor"))}
    out = []
    for o in openings:
        p, h = build_gripper(o)
        allp = {**p, **h}
        names = list(allp)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                if frozenset((a, b)) in expected:
                    continue
                v = sum(s.Volume() for s in allp[a].intersect(allp[b]).vals()) if allp[a].intersect(allp[b]).vals() else 0.0
                if v > 0.5:
                    out.append((o, a, b, round(v, 1)))
    return out


if __name__ == "__main__":
    print(f"X_G {X_G:.1f}, tool length {TOOL_LEN:.1f} (target {C.tool_len_target}), "
          f"gripper {2 * (U_IN + WALL_T):.0f} x {2 * (V_IN + SIDE_T):.0f} x {-Z_FRAME_BOT:.0f} mm")
    print("internal clashes:", internal_clashes() or "none")
