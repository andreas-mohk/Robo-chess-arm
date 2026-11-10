"""Builds every group once in its own frame and places the groups for a set of joint angles."""
from math import cos, radians, sin

import cadquery as cq

import base
import links
import wrist
from config import CFG

C = CFG

# group -> (printed, hardware, drive) in the group's own frame
_CACHE = {}


def groups(roll_deg=0.0):
    if not _CACHE:
        bp, bh, bd, _ = base.base_group()
        tp, th, td = base.turntable_group()
        wp, whw, wd = links.tower_group()
        up, uh, ud = links.upper_group()
        fp, fh, fd = links.fore_group()
        _CACHE.update({
            "base": (bp, bh, bd),
            "turret": ({**tp, **wp}, {**th, **whw}, {**td, **wd}),
            "upper": (up, uh, ud),
            "fore": (fp, fh, fd),
        })
    tool_p, tool_h = wrist.build_wrist(roll_deg)
    return {**_CACHE, "tool": (tool_p, tool_h, links.j4_output_in_tool())}


def frames(j):
    """Placement functions (frame -> world) for joint angles j = (j1..j5) in degrees."""
    j1, j2, j3, j4, _ = j
    a2, a3 = radians(j2), radians(j2 + j3)
    elbow = (0.0, C.L1 * cos(a2), C.shoulder_z + C.L1 * sin(a2))
    wpt = (0.0, elbow[1] + C.L2 * cos(a3), elbow[2] + C.L2 * sin(a3))

    def arm_to_world(w):
        return w.translate((-C.yaw_x, 0, 0)).rotate((0, 0, 0), (0, 0, 1), j1)

    def rx(w, deg):
        return w.rotate((0, 0, 0), (1, 0, 0), deg)

    return {
        "base": lambda w: w,
        "turret": arm_to_world,
        "upper": lambda w: arm_to_world(rx(w, j2).translate((0, 0, C.shoulder_z))),
        "fore": lambda w: arm_to_world(rx(w, j2 + j3).translate(elbow)),
        "tool": lambda w: arm_to_world(rx(w, j2 + j3 + j4 + 90).translate(wpt)),
    }


def posed(j, include=("printed", "hardware", "drive")):
    """{group: {name: world solid}} for joint angles j."""
    g = groups(j[4])
    f = frames(j)
    out = {}
    for name, (p, h, d) in g.items():
        parts = {}
        for kind, dct in zip(("printed", "hardware", "drive"), (p, h, d)):
            if kind in include:
                parts.update({k: f[name](v) for k, v in dct.items()})
        out[name] = parts
    return out


def fingertip_world(j):
    """Centre between the fingertips, world frame (used to verify the IK)."""
    p = cq.Workplane("XY").sphere(0.5).translate((wrist.X_G, 0, wrist.Z_GRIP_TOP + wrist.Z_TIP))
    c = frames(j)["tool"](p).val().Center()
    return c.x, c.y, c.z
