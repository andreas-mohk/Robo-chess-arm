"""Camera pole: foot on the baseplate, square aluminium pole, tee, horizontal boom, and a
tilting camera plate over the board centre. World frame.

The webcam hangs lens-down under a plate; a 1/4"-20 screw (cameras with a tripod thread)
or a strap through the slots (cameras without) holds it. The plate pivots on an M4 bolt
across the boom end, with an arc slot to level the camera +-8 deg.
"""
from math import atan2, cos, degrees, radians, sin, tan

import cadquery as cq

from config import CFG
from hardware import AL_TUBE, WEBCAMS

C = CFG
CAM = WEBCAMS[C.webcam]
TB = AL_TUBE[C.pole_tube]
TW = TB["w"]
WALL = 4.0
SOCK = 40.0
PX, PY = C.pole_xy
CX, CY = C.camera_xy
Z_LENS = C.board_top_z + C.camera_h
Z_CAM_TOP = Z_LENS + CAM["h"]
PLATE_T = 5.0
Z_PLATE = Z_CAM_TOP + 0.5                       # camera plate underside
HINGE_UP = 18.0                                 # pivot above the plate
Z_PIVOT = Z_PLATE + PLATE_T + HINGE_UP
Z_BOOM = Z_PIVOT + 26.0                         # boom centre line (tongue clears the boom socket)
FOOT = 110.0
FOOT_T = 6.0
Z_POLE_BOT = FOOT_T + 0.3
Z_POLE_TOP = Z_BOOM - TW / 2 - WALL - 0.5       # pole ends just under the tee's boom socket
BOOM_X0 = PX + (TW + 0.4) / 2 + 4.0 + 0.5       # boom starts just past the tee's pole socket
BOOM_X1 = CX - 8.0                              # and ends inside the mount
S = TW + 0.4                                    # socket cavity
LOCK_R = 12.0


def _socket_box(cx, cy, cz, lx, ly, lz):
    return cq.Workplane("XY").box(lx, ly, lz).translate((cx, cy, cz))


def camera_foot():
    f = cq.Workplane("XY").box(FOOT, FOOT, FOOT_T).translate((PX, PY, FOOT_T / 2)).edges("|Z").fillet(8)
    f = f.union(_socket_box(PX, PY, FOOT_T + SOCK / 2, S + 2 * WALL, S + 2 * WALL, SOCK))
    for ang in (0, 90, 180, 270):
        g = (cq.Workplane("XZ").workplane(offset=-2)
             .polyline([(S / 2 + WALL - 0.5, FOOT_T), (FOOT / 2 - 6, FOOT_T), (S / 2 + WALL - 0.5, FOOT_T + SOCK - 4)]).close()
             .extrude(4))
        f = f.union(g.rotate((0, 0, 0), (0, 0, 1), ang).translate((PX, PY, 0)))
    f = f.cut(_socket_box(PX, PY, FOOT_T + SOCK / 2 + 0.01, S, S, SOCK))
    f = f.cut(cq.Workplane("XY").pushPoints([(PX + sx * 42, PY + sy * 42) for sx in (1, -1) for sy in (1, -1)])
              .circle(2.2).extrude(FOOT_T))                                     # M4 into the baseplate
    f = f.cut(cq.Workplane("XZ").workplane(offset=-PY - 20).center(PX, FOOT_T + SOCK / 2).circle(2.1).extrude(40))  # M4 across
    return f


def camera_tee():
    ob = S + 2 * WALL
    blk = _socket_box(PX, PY, Z_BOOM - SOCK / 2 + ob / 2, ob, ob, SOCK + ob)                 # vertical, around the pole top
    blk = blk.union(_socket_box(PX + ob / 2 + SOCK / 2 - 0.01, PY, Z_BOOM, SOCK + 0.02, ob, ob))  # horizontal arm
    brace = (cq.Workplane("XZ").workplane(offset=-PY - 3)
             .polyline([(PX + ob / 2, Z_BOOM - ob / 2), (PX + ob / 2 + SOCK, Z_BOOM - ob / 2), (PX + ob / 2, Z_BOOM - ob / 2 - SOCK)])
             .close().extrude(6))
    blk = blk.union(brace)
    blk = blk.cut(_socket_box(PX, PY, Z_BOOM - ob / 2 - SOCK / 2 + 0.01 + 0.0, S, S, SOCK).translate((0, 0, 0)))
    blk = blk.cut(_socket_box(PX + ob / 2 + SOCK / 2 + 0.5, PY, Z_BOOM, SOCK + 1, S, S))
    blk = blk.cut(cq.Workplane("XZ").workplane(offset=-PY - 20).pushPoints([(PX, Z_BOOM - ob / 2 - SOCK / 2)]).circle(2.1).extrude(40))
    blk = blk.cut(cq.Workplane("XY").workplane(offset=Z_BOOM - 20).center(PX + ob / 2 + SOCK / 2, PY).circle(2.1).extrude(40))
    return blk


def camera_mount():
    """Boom-end socket with two hinge ears hanging down; pivot axis along Y."""
    ob = S + 2 * WALL
    m = _socket_box(CX - SOCK / 2 + 6, CY, Z_BOOM, SOCK + 12, ob, ob)
    for y in (-(ob / 2) + 2.5, ob / 2 - 2.5):
        ear = (cq.Workplane("XZ").workplane(offset=-(CY + y) - 2.5).center(CX, (Z_PIVOT + Z_BOOM) / 2)
               .rect(22, Z_BOOM - Z_PIVOT + 12).extrude(5))
        m = m.union(ear)
    m = m.cut(_socket_box(CX - SOCK / 2 + 6 - 6.5, CY, Z_BOOM, SOCK + 1, S, S))
    m = m.cut(cq.Workplane("XZ").workplane(offset=-CY - 30).center(CX, Z_PIVOT).circle(2.2).extrude(60))          # pivot
    # arc slot for the M4 locking bolt, +-8 deg around the pivot at r = 12 below it
    pts = [(CX + LOCK_R * sin(radians(a)), Z_PIVOT - LOCK_R * cos(radians(a))) for a in range(-8, 9, 2)]
    m = m.cut(cq.Workplane("XZ").workplane(offset=-CY - 30).pushPoints(pts).circle(2.2).extrude(60))
    m = m.cut(cq.Workplane("XY").workplane(offset=Z_BOOM - 20).center(CX - 12, CY).circle(2.1).extrude(40))   # M4 into boom
    return m


def camera_plate():
    """Plate over the camera, tongue up between the ears with the pivot hole and a lock hole."""
    p = cq.Workplane("XY").workplane(offset=Z_PLATE).center(CX, CY).rect(CAM["w"] + 16, CAM["d"] + 16).extrude(PLATE_T)
    p = p.edges("|Z").fillet(4)
    ob = S + 2 * WALL
    tongue = (cq.Workplane("XZ").workplane(offset=-CY - (ob / 2 - 5.5)).center(CX, (Z_PLATE + Z_PIVOT + 8) / 2)
              .rect(20, Z_PIVOT + 8 - Z_PLATE).extrude(ob - 11))
    p = p.union(tongue)
    p = p.cut(cq.Workplane("XZ").workplane(offset=-CY - 30).pushPoints([(CX, Z_PIVOT), (CX, Z_PIVOT - LOCK_R)])
              .circle(2.2).extrude(60))
    p = p.cut(cq.Workplane("XY").workplane(offset=Z_PLATE).center(CX, CY).circle(3.3).extrude(PLATE_T))    # 1/4"-20
    slots = [(CX + sx * (CAM["w"] / 2 + 3), CY) for sx in (1, -1)]
    p = p.cut(cq.Workplane("XY").workplane(offset=Z_PLATE).pushPoints(slots).rect(4, CAM["d"] + 4).extrude(PLATE_T))  # strap
    p = p.cut(cq.Workplane("XY").workplane(offset=Z_PLATE).center(CX + 25, CY).rect(12, 8).extrude(PLATE_T))          # cable
    return p


def webcam():
    return cq.Workplane("XY").box(CAM["w"], CAM["d"], CAM["h"]).translate((CX, CY, Z_LENS + CAM["h"] / 2)).edges("|X").fillet(6)


def pole_tube():
    return (cq.Workplane("XY").box(TW, TW, Z_POLE_TOP - Z_POLE_BOT).translate((PX, PY, (Z_POLE_TOP + Z_POLE_BOT) / 2))
            .cut(cq.Workplane("XY").box(TW - 2 * TB["t"], TW - 2 * TB["t"], 2000).translate((PX, PY, 0))))


def boom_tube():
    return (cq.Workplane("XY").box(BOOM_X1 - BOOM_X0, TW, TW).translate(((BOOM_X0 + BOOM_X1) / 2, PY, Z_BOOM))
            .cut(cq.Workplane("XY").box(2000, TW - 2 * TB["t"], TW - 2 * TB["t"]).translate((0, PY, Z_BOOM))))


def view_frustum():
    """Pyramid from the lens to the board plus margin, for 'is the arm in the picture' checks."""
    m = C.view_margin
    x0, x1 = -4 * C.square - m, 4 * C.square + m
    y0, y1 = C.base_to_board - m, C.base_to_board + 8 * C.square + m
    z = C.board_top_z + 1.0
    apex = cq.Vector(CX, CY, Z_LENS - 1)
    base = cq.Wire.makePolygon([cq.Vector(x0, y0, z), cq.Vector(x1, y0, z), cq.Vector(x1, y1, z), cq.Vector(x0, y1, z)], close=True)
    tip = cq.Wire.makePolygon([apex + cq.Vector(-0.1, -0.1, 0), apex + cq.Vector(0.1, -0.1, 0), apex + cq.Vector(0.1, 0.1, 0),
                               apex + cq.Vector(-0.1, 0.1, 0)], close=True)
    return cq.Workplane("XY").add(cq.Solid.makeLoft([base, tip], True))


def fov_report():
    """Field of view the board needs vs what the camera has (either orientation)."""
    m = C.view_margin
    h = C.camera_h
    half_x = max(abs(-4 * C.square - m - CX), abs(4 * C.square + m - CX))
    half_y = max(abs(C.base_to_board - m - CY), abs(C.base_to_board + 8 * C.square + m - CY))
    need_x, need_y = 2 * degrees(atan2(half_x, h)), 2 * degrees(atan2(half_y, h))
    fits = (need_x <= CAM["hfov"] and need_y <= CAM["vfov"]) or (need_x <= CAM["vfov"] and need_y <= CAM["hfov"])
    cov = (2 * h * tan(radians(CAM["hfov"] / 2)), 2 * h * tan(radians(CAM["vfov"] / 2)))
    return fits, need_x, need_y, cov


def camera_group():
    printed = {"camera_foot": camera_foot(), "camera_tee": camera_tee(), "camera_mount": camera_mount(),
               "camera_plate": camera_plate()}
    hardware = {"pole_tube": pole_tube(), "boom_tube": boom_tube(), "webcam": webcam()}
    return printed, hardware


if __name__ == "__main__":
    fits, nx, ny, cov = fov_report()
    print(f"lens at z {Z_LENS:.0f}, boom at z {Z_BOOM:.0f}, pole {Z_POLE_TOP - Z_POLE_BOT:.0f} mm, boom {BOOM_X1 - BOOM_X0:.0f} mm")
    print(f"needs {nx:.1f} x {ny:.1f} deg, camera {CAM['hfov']} x {CAM['vfov']} deg -> {'fits' if fits else 'DOES NOT FIT'}; "
          f"covers {cov[0]:.0f} x {cov[1]:.0f} mm at the board")
    p, h = camera_group()
    names = list({**p, **h})
    allp = {**p, **h}
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            r = allp[a].intersect(allp[b])
            v = sum(s.Volume() for s in r.vals()) if r.vals() else 0
            if v > 0.5:
                print("  overlap", a, b, round(v, 1))
