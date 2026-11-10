"""Tower (carries J2), upper arm (carries J3 + its motor), forearm (carries J4 + its motor).

Link frames: origin on the proximal joint axis, x = arm lateral, y along the link,
z completes the right-handed frame (up when the link is horizontal).
Tower frame = arm frame (z is height above the table).
Each link: a printed proximal fitting and distal fitting joined by an aluminium tube.
"""
from math import cos, radians, sin

import cadquery as cq

from common import hull_outline, place_axis_x, polar
from config import CFG
from joints import JointKit
from layout import D2, D3, D4, T, TUBE, X_F, X_J2_COVER, X_TOWER, X_U, Z_TT_TOP

C = CFG
TW = TUBE["w"]
SOCKET_LEN = 40.0
SOCKET_WALL = 4.0
TUBE_START = 45.0            # tube end distance from each joint axis


def _kits():
    k2 = JointKit("J2", D2, C.joints["J2"].motor, C.tower_t, C.joints["J2"].motor_r, C.joints["J2"].motor_angle)
    # J3 and J4 motors sit on the tail behind the previous joint: belt along the link, motor at phi = 180
    k3 = JointKit("J3", D3, C.joints["J3"].motor, T, C.tail3 + C.L1, 180.0)
    k4 = JointKit("J4", D4, C.joints["J4"].motor, T, C.tail4 + C.L2, 180.0)
    return k2, k3, k4


K2, K3, K4 = _kits()
TAIL3 = K3.c - C.L1          # actual, after snapping to a stocked belt
TAIL4 = K4.c - C.L2

# joint-frame -> link-frame placements
J2_AT_TOWER = dict(sign=+1, origin=(X_J2_COVER, 0.0, C.shoulder_z))
J2_AT_UPPER = dict(sign=+1, origin=(X_J2_COVER, 0.0, 0.0))
J3_AT_UPPER = dict(sign=-1, origin=(X_U, C.L1, 0.0))
J3_AT_FORE = dict(sign=-1, origin=(X_U, 0.0, 0.0))
J4_AT_FORE = dict(sign=+1, origin=(X_F, C.L2, 0.0))
J4_AT_TOOL = dict(sign=+1, origin=(X_F, 0.0, 0.0))


def put(w, sign, origin):
    return place_axis_x(w, sign, origin)


def put_all(d, at):
    return {k: put(v, at["sign"], at["origin"]) for k, v in d.items()}


def _socket(y0, x_lo, x_hi):
    """Tube socket: box around a TW tube running along +y from y0, with two M4 cross bolts."""
    w = TW + 2 * SOCKET_WALL
    s = cq.Workplane("XY").box(x_hi - x_lo, SOCKET_LEN, w).translate(((x_lo + x_hi) / 2, y0 + SOCKET_LEN / 2, 0))
    tube_x = (x_lo + SOCKET_WALL, x_hi) if x_lo < 0 and x_hi <= 0.01 else (x_lo, x_hi - SOCKET_WALL)
    return s, tube_x


def _tube_cavity(x0, x1, y0, y1):
    return cq.Workplane("XY").box(x1 - x0 + 0.3, y1 - y0, TW + 0.3).translate(((x0 + x1) / 2, (y0 + y1) / 2, 0))


def _cross_bolts(x_mid, ys):
    """M4 bolts across the socket and tube, along z."""
    return cq.Workplane("XY").workplane(offset=-TW).pushPoints([(x_mid, y) for y in ys]).circle(2.1).extrude(2 * TW)


# ------------------------------------------------------------------ tower (arm frame)
def tower():
    t = C.tower_t
    x0, x1 = X_TOWER - t, X_TOWER
    a = radians(C.joints["J2"].motor_angle)
    my, mz = K2.c * cos(a), C.shoulder_z + K2.c * sin(a)
    outline = hull_outline(
        [(0, C.shoulder_z, D2.housing_od / 2 + 3), (my, mz, 30)],
        [(-C.tower_w / 2, Z_TT_TOP, C.tower_w / 2, Z_TT_TOP + 12)])
    plate = cq.Workplane("YZ").workplane(offset=x0).polyline(outline).close().extrude(t)
    foot = cq.Workplane("XY").workplane(offset=Z_TT_TOP).center(x0 - 14, 0).rect(28 + t, C.tower_w).extrude(8)
    gussets = None
    for y in (-C.tower_w / 2 + 3, 0.0, C.tower_w / 2 - 3):
        g = (cq.Workplane("XZ").workplane(offset=-y - 3)
             .polyline([(x0 - 28, Z_TT_TOP + 8), (x0, Z_TT_TOP + 8), (x0, Z_TT_TOP + 60)]).close().extrude(6))
        gussets = g if gussets is None else gussets.union(g)
    tw = plate.union(foot).union(gussets)
    tw = tw.cut(put(K2.carrier_cutter(), **J2_AT_TOWER))
    # foot bolts to the turntable (M4), clear of the J1 clamp under it
    pts = [(x0 - 20, -C.tower_w / 2 + 10), (x0 - 20, C.tower_w / 2 - 10), (x0 - 4, -C.tower_w / 2 + 10), (x0 - 4, C.tower_w / 2 - 10)]
    tw = tw.cut(cq.Workplane("XY").workplane(offset=Z_TT_TOP).pushPoints(pts).circle(2.2).extrude(8))
    return tw


def tower_group():
    printed = {"tower": tower()}
    printed.update(put_all(K2.printed, J2_AT_TOWER))
    hardware = put_all(K2.all_hardware(), J2_AT_TOWER)
    drive = put_all(K2.static, J2_AT_TOWER)
    return printed, hardware, drive


# ------------------------------------------------------------------ upper arm (upper-arm frame)
def upper_proximal():
    plate_x = (X_U, X_U + T)
    m_half = 25.0
    outline = hull_outline([(0, 0, 24)], [(-TAIL3 - m_half, -m_half, -TAIL3 + m_half, m_half),
                                          (TUBE_START, -TW / 2 - SOCKET_WALL, TUBE_START + SOCKET_LEN, TW / 2 + SOCKET_WALL)])
    p = cq.Workplane("YZ").workplane(offset=plate_x[0]).polyline(outline).close().extrude(T)
    sock, _ = _socket(TUBE_START, -TW - SOCKET_WALL, X_U)
    p = p.union(sock).cut(_tube_cavity(-TW, X_U, TUBE_START - 1, TUBE_START + SOCKET_LEN + 1).translate((0, 0, 0)))
    p = p.cut(_cross_bolts(-TW / 2, [TUBE_START + 12, TUBE_START + SOCKET_LEN - 12]))
    # J2 clamp screws, heads sunk into the belt-side face
    pts = polar(D2.clamp_bolt_n, D2.clamp_bolt_r)
    p = p.cut(cq.Workplane("YZ").workplane(offset=plate_x[0]).pushPoints(pts).circle(D2.clamp_bolt_d / 2).extrude(T))
    p = p.cut(cq.Workplane("YZ").workplane(offset=plate_x[1] - 3.2).pushPoints(pts).circle(3.1).extrude(3.2))
    # J3 motor holes (the J3 kit's cutter also covers the motor on this tail)
    return p.cut(put(K3.carrier_cutter(), **J3_AT_UPPER))


def upper_distal():
    outline = hull_outline([(C.L1, 0, D3.housing_od / 2 + 3)],
                           [(C.L1 - TUBE_START - SOCKET_LEN, -TW / 2 - SOCKET_WALL, C.L1 - TUBE_START, TW / 2 + SOCKET_WALL)])
    p = cq.Workplane("YZ").workplane(offset=X_U).polyline(outline).close().extrude(T)
    sock, _ = _socket(C.L1 - TUBE_START - SOCKET_LEN, -TW - SOCKET_WALL, X_U)
    p = p.union(sock).cut(_tube_cavity(-TW, X_U, C.L1 - TUBE_START - SOCKET_LEN - 1, C.L1 - TUBE_START + 1))
    p = p.cut(_cross_bolts(-TW / 2, [C.L1 - TUBE_START - 12, C.L1 - TUBE_START - SOCKET_LEN + 12]))
    return p.cut(put(K3.carrier_cutter(), **J3_AT_UPPER))


def upper_tube():
    return cq.Workplane("XY").box(TW, C.L1 - 2 * TUBE_START, TW).translate((-TW / 2, C.L1 / 2, 0)) \
        .cut(cq.Workplane("XY").box(TW - 2 * TUBE["t"], C.L1, TW - 2 * TUBE["t"]).translate((-TW / 2, C.L1 / 2, 0)))


def upper_group():
    printed = {"upper_proximal": upper_proximal(), "upper_distal": upper_distal()}
    printed.update(put_all(K3.printed, J3_AT_UPPER))
    hardware = {"upper_tube": upper_tube()}
    hardware.update(put_all(K3.all_hardware(), J3_AT_UPPER))
    drive = put_all(K3.static, J3_AT_UPPER)
    drive.update(put_all(K2.output, J2_AT_UPPER))
    return printed, hardware, drive


# ------------------------------------------------------------------ forearm (forearm frame)
def fore_proximal():
    x0 = X_F - T
    m_half = 25.0
    outline = hull_outline([(0, 0, 24)], [(-TAIL4 - m_half, -m_half, -TAIL4 + m_half, m_half),
                                          (TUBE_START, -TW / 2 - SOCKET_WALL, TUBE_START + SOCKET_LEN, TW / 2 + SOCKET_WALL)])
    p = cq.Workplane("YZ").workplane(offset=x0).polyline(outline).close().extrude(T)
    sock, _ = _socket(TUBE_START, X_F, X_F + TW + SOCKET_WALL)
    p = p.union(sock).cut(_tube_cavity(X_F, X_F + TW, TUBE_START - 1, TUBE_START + SOCKET_LEN + 1))
    p = p.cut(_cross_bolts(X_F + TW / 2, [TUBE_START + 12, TUBE_START + SOCKET_LEN - 12]))
    pts = polar(D3.clamp_bolt_n, D3.clamp_bolt_r)
    p = p.cut(cq.Workplane("YZ").workplane(offset=x0).pushPoints(pts).circle(D3.clamp_bolt_d / 2).extrude(T))
    p = p.cut(cq.Workplane("YZ").workplane(offset=x0).pushPoints(pts).circle(3.1).extrude(3.2))
    return p.cut(put(K4.carrier_cutter(), **J4_AT_FORE))


def fore_distal():
    x0 = X_F - T
    outline = hull_outline([(C.L2, 0, D4.housing_od / 2 + 3)],
                           [(C.L2 - TUBE_START - SOCKET_LEN, -TW / 2 - SOCKET_WALL, C.L2 - TUBE_START, TW / 2 + SOCKET_WALL)])
    p = cq.Workplane("YZ").workplane(offset=x0).polyline(outline).close().extrude(T)
    sock, _ = _socket(C.L2 - TUBE_START - SOCKET_LEN, X_F, X_F + TW + SOCKET_WALL)
    p = p.union(sock).cut(_tube_cavity(X_F, X_F + TW, C.L2 - TUBE_START - SOCKET_LEN - 1, C.L2 - TUBE_START + 1))
    p = p.cut(_cross_bolts(X_F + TW / 2, [C.L2 - TUBE_START - 12, C.L2 - TUBE_START - SOCKET_LEN + 12]))
    return p.cut(put(K4.carrier_cutter(), **J4_AT_FORE))


def fore_tube():
    return cq.Workplane("XY").box(TW, C.L2 - 2 * TUBE_START, TW).translate((X_F + TW / 2, C.L2 / 2, 0)) \
        .cut(cq.Workplane("XY").box(TW - 2 * TUBE["t"], C.L2, TW - 2 * TUBE["t"]).translate((X_F + TW / 2, C.L2 / 2, 0)))


def fore_group():
    printed = {"fore_proximal": fore_proximal(), "fore_distal": fore_distal()}
    printed.update(put_all(K4.printed, J4_AT_FORE))
    hardware = {"fore_tube": fore_tube()}
    hardware.update(put_all(K4.all_hardware(), J4_AT_FORE))
    drive = put_all(K4.static, J4_AT_FORE)
    drive.update(put_all(K3.output, J3_AT_FORE))
    return printed, hardware, drive


def j4_output_in_tool():
    return put_all(K4.output, J4_AT_TOOL)


if __name__ == "__main__":
    for k in (K2, K3, K4):
        print(k.report())
    print(f"tails: J3 motor {TAIL3:.1f} mm behind the shoulder, J4 motor {TAIL4:.1f} mm behind the elbow")
