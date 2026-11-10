"""All design parameters for the chess arm, in one place.

Units: mm, degrees, kg, Nm. Change a value, run `python3 build.py`, and every part,
check and export follows. Bought-part sizes live in hardware.py.

Frames used everywhere
  World: origin on the table under the base-yaw axis, +Y towards the board, +Z up.
  Arm (lateral) x: along the J2-J4 axes. x = 0 is the face where the upper arm
  bolts onto the J2 output clamp; +x points away from the tower.
"""
from dataclasses import dataclass, field

from cycloidal import DriveParams


@dataclass(frozen=True)
class JointCfg:
    drive: DriveParams | None
    motor: str                      # key in hardware.MOTORS
    motor_pulley: int = 20          # bought GT2 pulley on the motor
    motor_r: float = 0.0            # motor axis distance from the joint axis (belt centre distance, nominal)
    motor_angle: float = 0.0        # where the motor sits around the joint, see each link file
    derate: float = 0.6             # torque at working speed / holding torque
    efficiency: float = 0.75        # belt + cycloidal

    @property
    def belt_ratio(self):
        return self.drive.pulley_teeth / self.motor_pulley if self.drive else 1.0

    @property
    def total_ratio(self):
        return self.belt_ratio * (self.drive.ratio if self.drive else 1)


BIG = DriveParams()                                     # J1, J2, J3: 20:1, 84 mm, 6806 output
SMALL = DriveParams(                                    # J4 wrist pitch: 15:1, 68 mm, 6804 output
    ratio=15, pin_circle_r=24.0, ring_pin_d=3.0, ring_pin_len=16.0, ecc=0.8, disc_t=5.0,
    out_pin_d=3.0, out_pin_r=15.5, out_pin_len=18.0, cam_brg="6801", journal_brg="6800", out_brg="6804",
    housing_od=68.0, cover_t=6.0, bolt_r=30.0, bolt_d=3.4, clamp_bolt_n=4, clamp_bolt_r=7.0,
    clamp_bolt_d=2.9, clamp_tap_d=2.1, rod_d=3.0, pulley_teeth=40, flange_extra_t=1.5)


@dataclass(frozen=True)
class Config:
    # ---------------- board and game
    square: float = 50.0
    base_to_board: float = 100.0      # yaw axis to the near board edge
    board_top_z: float = 15.0         # board surface above the table (board thickness)
    grip_h: float = 30.0              # fingertip height above the board when gripping
    carry_lift: float = 100.0         # extra height while carrying (clears a 95 mm king)
    tray_xy: tuple = (280.0, 60.0)    # capture tray centre, world X, Y
    tray_size: tuple = (80.0, 100.0)

    # ---------------- arm geometry
    shoulder_z: float = 230.0         # J2 axis above the table
    L1: float = 280.0                 # J2 -> J3
    L2: float = 280.0                 # J3 -> J4
    yaw_x: float = -30.0              # yaw axis position in the arm's lateral x
    max_extension: float = 0.95       # IK refuses poses beyond this fraction of L1 + L2

    # ---------------- links
    plate_t: float = 6.0              # printed link plates
    tube: str = "15x15x1.5"           # aluminium square tube for both links (2 x tube width < J3 drive height)
    tail3: float = 75.0               # J3 motor behind the shoulder (>= drive radius + motor half-diagonal)
    tail4: float = 75.0               # J4 motor behind the elbow
    j2_gap_extra: float = 1.0         # extra room between tower and J2 drive

    # ---------------- base and turntable
    base_w: float = 200.0             # X
    base_d: float = 180.0             # Y, keep base_d / 2 < base_to_board
    base_h: float = 60.0              # table to top of base
    base_wall: float = 3.0
    base_top_t: float = 8.0
    turntable_r: float = 84.0
    turntable_t: float = 6.0
    race_r: float = 72.0              # ball race radius
    ball_d: float = 6.0               # 6 mm steel balls
    tower_t: float = 6.0
    tower_w: float = 96.0             # tower plate width (along Y)
    oled: str = "SH1106_13"
    buttons: int = 3

    # ---------------- wrist and gripper
    roll_motor: str = "17HS08"
    gripper_motor: str = "28BYJ-48"
    jaw_open_max: float = 42.0        # finger gap fully open
    finger_len: float = 75.0          # fingertips -> carriage; keeps the gripper body above a 95 mm king
    tool_len_target: float = 154.0    # J4 axis -> fingertips; build warns if the design differs by > 5 mm

    # ---------------- printing and materials
    bed: tuple = (220.0, 220.0, 250.0)
    print_density: float = 1.27e-6    # PETG, kg / mm^3
    infill_factor: float = 0.45       # printed mass / solid mass (walls + infill)

    joints: dict = field(default_factory=lambda: {
        # J1 motor_angle: degrees from +X in the base (world). J2 motor_angle: degrees in the tower plane
        # from forward (+Y) towards up (+Z). J3/J4 motors always sit on the tail of the previous link.
        "J1": JointCfg(BIG, "17HS08", motor_r=55.0, motor_angle=60.0),     # pancake: hangs below the belt inside the base
        "J2": JointCfg(BIG, "17HS8401", motor_r=80.0, motor_angle=150.0),
        "J3": JointCfg(BIG, "17HS13"),     # motor on the upper-arm tail; belt length from tail3 + L1
        "J4": JointCfg(SMALL, "17HS13"),   # motor on the forearm tail; belt length from tail4 + L2
        "J5": JointCfg(None, "17HS08", derate=0.6, efficiency=0.95),   # roll, direct drive
    })

    def drive(self, j):
        return self.joints[j].drive


CFG = Config()
