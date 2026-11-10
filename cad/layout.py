"""Numbers derived from config.py that several parts share (positions, drive variants).

Every joint uses the same arrangement: the drive's back cover bolts straight onto a
carrier plate; the input shaft passes through the plate; pulley, belt and AS5600 sit
on the far side of the plate; the motor sits on the drive side of the plate with its
shaft pushed through into the belt plane (J1: motor hangs below the belt on a shelf).
"""
from dataclasses import replace

from config import CFG
from hardware import AL_TUBE, MOTOR_PULLEY, MOTORS

C = CFG
T = C.plate_t
TUBE = AL_TUBE[C.tube]

# drives with the pulley placed beyond each carrier plate
D1 = replace(C.drive("J1"), back_offset=C.base_top_t + 1.0).check()
D2 = replace(C.drive("J2"), back_offset=C.tower_t + 1.0).check()
D3 = replace(C.drive("J3"), back_offset=T + 1.0).check()
D4 = replace(C.drive("J4"), back_offset=T + 1.0).check()

# ---------------- lateral (arm x) stations
X_U = 0.0                        # upper-arm plate, drive-side face (J2 clamp face)
X_J2_COVER = X_U - D2.height     # J2 back cover / tower plate +x face
X_TOWER = X_J2_COVER             # tower plate occupies [X_TOWER - tower_t, X_TOWER]
X_F = X_U - D3.height            # forearm plate +x face (J3 clamp face); plate is [X_F - T, X_F]
X_J4_OUT = X_F + D4.height       # J4 clamp face, wrist bracket starts here

# ---------------- heights (world z)
Z_BASE_TOP = C.base_h
Z_J1_OUT = Z_BASE_TOP + D1.height            # J1 clamp face
Z_TT = Z_J1_OUT + 0.2                        # turntable underside
Z_TT_TOP = Z_TT + C.turntable_t


def motor_pulley_base(motor_key, belt_dist):
    """Where the bought pulley sits on a motor shaft so its teeth are on the belt plane.
    belt_dist: belt centre plane measured from the motor face along the shaft.
    Returns (base distance from the face, hub_towards_motor)."""
    p = MOTOR_PULLEY
    shaft = MOTORS[motor_key].shaft_len
    teeth = p["width"] - p["hub_len"]
    options = ((belt_dist - p["hub_len"] - teeth / 2, True),   # hub towards the motor
               (belt_dist - teeth / 2, False))                  # hub away from the motor
    for base, hub_first in options:
        hub_mid = base + p["hub_len"] / 2 if hub_first else base + teeth + p["hub_len"] / 2
        if base >= 2.5 and hub_mid <= shaft - 2:     # grub screw must bite on the shaft
            return base, hub_first
    raise ValueError(f"{motor_key}: pulley cannot reach a belt {belt_dist:.1f} mm from the motor face")


def summary():
    return {
        "drive heights": {j: round(d.height, 1) for j, d in zip(("J1", "J2", "J3", "J4"), (D1, D2, D3, D4))},
        "x tower / upper arm / forearm / J4 out": (round(X_TOWER, 1), X_U, round(X_F, 1), round(X_J4_OUT, 1)),
        "z base top / turntable top / shoulder": (Z_BASE_TOP, round(Z_TT_TOP, 1), C.shoulder_z),
    }
