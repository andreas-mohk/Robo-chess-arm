"""Inverse kinematics for the arm as built (lateral offset included) and the standard poses.

Joint conventions
  J1 psi: base yaw, 0 = arm facing +Y. Positive turns towards -X (counter-clockwise from above).
  J2: upper arm elevation from horizontal.
  J3: forearm relative to the upper arm (negative = folding down).
  J4: tool relative to the forearm; J2 + J3 + J4 = -90 keeps the gripper vertical.
  J5: gripper roll about the vertical tool axis.
"""
from math import acos, atan2, cos, degrees, hypot, radians, sin, sqrt

from config import CFG
from wrist import TOOL_LEN, X_G

C = CFG
OFFSET = X_G - C.yaw_x          # gripper axis to yaw axis, sideways
FILES = "abcdefgh"


def square_xy(name):
    """World X, Y of a square centre. Arm plays Black from behind rank 8; h-file on the arm's left (-X)."""
    f, r = FILES.index(name[0]), int(name[1])
    return (3.5 - f) * C.square, C.base_to_board + (8 - r) * C.square + C.square / 2


def target_xy(name):
    return C.tray_xy if name == "tray" else square_xy(name)


def ik(X, Y, tip_z, roll_mode="diagonal"):
    rho = hypot(X, Y)
    if rho <= abs(OFFSET):
        return {"ok": False, "why": "inside the lateral offset circle"}
    r_in = sqrt(rho * rho - OFFSET * OFFSET)                # in-plane reach
    psi = atan2(Y, X) - atan2(r_in, OFFSET)                 # world = Rz(psi) * arm
    wz = tip_z + TOOL_LEN
    dz = wz - C.shoulder_z
    d = hypot(r_in, dz)
    if d > C.max_extension * (C.L1 + C.L2):
        return {"ok": False, "why": f"needs {100 * d / (C.L1 + C.L2):.0f}% extension", "ext": d / (C.L1 + C.L2)}
    a = atan2(dz, r_in) + acos((C.L1 ** 2 + d * d - C.L2 ** 2) / (2 * C.L1 * d))
    ex, ez = C.L1 * cos(a), C.shoulder_z + C.L1 * sin(a)
    fore = atan2(wz - ez, r_in - ex)
    j2, j3 = degrees(a), degrees(fore - a)
    j4 = -90.0 - j2 - j3
    j1 = degrees(psi)
    if roll_mode == "diagonal":           # jaws close along a board diagonal: most room between neighbours
        j5 = 45.0 - j1
    else:
        j5 = -j1
    j5 = (j5 + 90) % 180 - 90             # jaws are symmetric: keep roll within +-90
    return {"ok": True, "j": (j1, j2, j3, j4, j5), "ext": d / (C.L1 + C.L2),
            "fold": degrees(acos((C.L1 ** 2 + C.L2 ** 2 - d * d) / (2 * C.L1 * C.L2))), "r_in": r_in}


def grip_z():
    return C.board_top_z + C.grip_h


def pose(name, carry=False):
    X, Y = target_xy(name)
    z = grip_z() + (C.carry_lift if carry else 0.0)
    if name == "tray":
        z -= C.board_top_z                # tray sits on the table
    return ik(X, Y, z)


def _park():
    s = ik(*C.park_xyz, roll_mode="aligned")
    if not s["ok"]:
        raise ValueError(f"park position unreachable: {s['why']}")
    return tuple(round(v, 2) for v in s["j"])


PARK = _park()


def all_targets():
    names = [f + str(r) for f in FILES for r in range(1, 9)] + ["tray"]
    return [(n, carry) for n in names for carry in (False, True)]


def joint_ranges():
    lo, hi = [1e9] * 5, [-1e9] * 5
    worst = {"ext": 0, "fold": 999}
    bad = []
    for n, carry in all_targets():
        s = pose(n, carry)
        if not s["ok"]:
            bad.append((n, carry, s["why"]))
            continue
        for i, v in enumerate(s["j"]):
            lo[i], hi[i] = min(lo[i], v), max(hi[i], v)
        worst["ext"] = max(worst["ext"], s["ext"])
        worst["fold"] = min(worst["fold"], s["fold"])
    return lo, hi, worst, bad


if __name__ == "__main__":
    lo, hi, worst, bad = joint_ranges()
    print(f"tool length {TOOL_LEN:.1f}, lateral offset {OFFSET:.1f}")
    for i in range(5):
        print(f"  J{i + 1}: {lo[i]:+.0f} .. {hi[i]:+.0f}")
    print(f"  max extension {100 * worst['ext']:.0f}%, tightest elbow fold {worst['fold']:.0f} deg")
    print("  unreachable:", bad or "none")
