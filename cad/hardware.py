"""Catalog of bought parts: dimensions (mm), mass (kg), rough price (EUR).

If a part is unavailable, add the substitute here and point config.py at it.
Everything that depends on a part reads its size from this file.
Prices are rough 2026 figures for planning only.
"""
from dataclasses import dataclass
from math import asin, pi, sqrt


@dataclass(frozen=True)
class Motor:
    name: str
    face: float          # square flange size
    hole_pitch: float    # mounting hole spacing (square pattern)
    hole_d: float        # tap size of mounting holes (M3 -> 3)
    boss_d: float        # centring boss
    boss_h: float
    length: float        # body length behind the face
    shaft_d: float
    shaft_len: float     # from face (boss excluded)
    torque: float        # holding torque, Nm
    mass: float
    price: float


MOTORS = {
    "17HS4401": Motor("NEMA 17, 40 mm, 0.40 Nm", 42.3, 31.0, 3, 22.0, 2.0, 40, 5, 24, 0.40, 0.28, 9),
    "17HS8401": Motor("NEMA 17, 48 mm, 0.52 Nm", 42.3, 31.0, 3, 22.0, 2.0, 48, 5, 24, 0.52, 0.36, 11),
    "17HS24":   Motor("NEMA 17, 60 mm, 0.65 Nm", 42.3, 31.0, 3, 22.0, 2.0, 60, 5, 24, 0.65, 0.50, 15),
    "17HS13":   Motor("NEMA 17, 34 mm, 0.28 Nm", 42.3, 31.0, 3, 22.0, 2.0, 34, 5, 24, 0.28, 0.22, 9),
    "17HS08":   Motor("NEMA 17 pancake, 20 mm, 0.13 Nm", 42.3, 31.0, 3, 22.0, 2.0, 20, 5, 18, 0.13, 0.14, 9),
    "14HS13":   Motor("NEMA 14, 34 mm, 0.18 Nm", 35.2, 26.0, 3, 22.0, 2.0, 34, 5, 20, 0.18, 0.18, 10),
}


@dataclass(frozen=True)
class GearedMotor:
    """28BYJ-48 style: round can, two ears, shaft offset from can centre."""
    name: str
    can_d: float
    can_h: float
    ear_pitch: float     # distance between ear holes
    ear_hole_d: float
    shaft_offset: float  # shaft axis offset from can axis
    shaft_d: float
    shaft_flat: float    # across flats
    shaft_len: float
    boss_d: float
    boss_h: float
    torque: float
    mass: float
    price: float


GEARED = {
    # convert to bipolar (cut the middle trace) to run on a TMC2209
    "28BYJ-48": GearedMotor("28BYJ-48 geared stepper", 28.0, 19.0, 35.0, 4.2, 8.0, 5.0, 3.0, 10.0, 9.0, 1.5, 0.03, 0.04, 2),
}


@dataclass(frozen=True)
class Bearing:
    d: float
    D: float
    B: float
    mass: float
    price: float


BEARINGS = {
    "688":  Bearing(8, 16, 5, 0.004, 0.6),
    "608":  Bearing(8, 22, 7, 0.012, 0.5),
    "625":  Bearing(5, 16, 5, 0.005, 0.6),
    "6800": Bearing(10, 19, 5, 0.005, 0.8),
    "6801": Bearing(12, 21, 5, 0.006, 0.8),
    "6802": Bearing(15, 24, 5, 0.007, 1.0),
    "6803": Bearing(17, 26, 5, 0.008, 1.0),
    "6804": Bearing(20, 32, 7, 0.019, 1.5),
    "6805": Bearing(25, 37, 7, 0.023, 2.0),
    "6806": Bearing(30, 42, 7, 0.026, 2.5),
    "6807": Bearing(35, 47, 7, 0.030, 3.0),
    "6808": Bearing(40, 52, 7, 0.032, 3.5),
}

# --- GT2 belt
GT2_PITCH = 2.0
GT2_PLD = 0.254          # pitch line to tooth tip
GT2_BELT_T = 1.4         # belt thickness incl. teeth

# Closed-loop GT2 6 mm belt lengths commonly stocked. Edit to match your supplier;
# the assembly picks the closest one and slides the motor to suit.
GT2_LOOPS = [110, 122, 140, 158, 160, 180, 200, 202, 232, 240, 250, 280, 300, 320, 350, 400,
             450, 488, 500, 550, 600, 610, 650, 700, 710, 720, 750, 752, 760, 800, 852, 900, 1000]

# bought aluminium GT2 pulley for the motor shaft
MOTOR_PULLEY = dict(teeth=20, bore=5.0, hub_d=16.0, hub_len=7.0, flange_d=18.0, width=16.0, price=1.0, mass=0.008)


def gt2_pitch_r(teeth):
    return teeth * GT2_PITCH / (2 * pi)


def belt_length(c, t1, t2):
    """Closed belt length (pitch line) for two pulleys at centre distance c."""
    r1, r2 = gt2_pitch_r(t1), gt2_pitch_r(t2)
    dr = abs(r2 - r1)
    return 2 * sqrt(c * c - dr * dr) + pi * (r1 + r2) + 2 * dr * asin(dr / c)


def centre_for_length(length, t1, t2):
    """Centre distance that makes a closed belt of `length` fit (bisection)."""
    lo, hi = abs(gt2_pitch_r(t2) - gt2_pitch_r(t1)) + 1, length
    for _ in range(80):
        mid = (lo + hi) / 2
        if belt_length(mid, t1, t2) < length:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def pick_belt(c_nominal, t1, t2, slack=(-3.0, 6.0)):
    """Smallest stocked loop whose centre distance lies within the motor slot around c_nominal.
    Returns (loop_length, centre_distance)."""
    for loop in GT2_LOOPS:
        c = centre_for_length(loop, t1, t2)
        if c_nominal + slack[0] <= c <= c_nominal + slack[1]:
            return loop, c
    # nothing fits: choose the loop just above and report its centre distance
    for loop in GT2_LOOPS:
        if belt_length(c_nominal, t1, t2) <= loop:
            return loop, centre_for_length(loop, t1, t2)
    raise ValueError("belt longer than any stocked loop")


# --- fasteners
SCREW_LENGTHS = [4, 6, 8, 10, 12, 16, 20, 25, 30, 35, 40, 45, 50]   # commonly stocked metric lengths
M3_NUT_H = 2.4


def stack_bolt(stack, carrier_t, nut_h=M3_NUT_H):
    """Longest standard bolt whose end lands inside the carrier with room for a nut.
    stack: head face to carrier face. Returns (length, nut pocket depth from the carrier's far face)."""
    for L in reversed(SCREW_LENGTHS):
        into = L - stack
        if nut_h + 0.6 <= into <= carrier_t:
            return L, carrier_t - (into - nut_h)
    raise ValueError(f"no standard bolt fits a {stack:.1f} mm stack on a {carrier_t} mm plate")


def std_len(minimum):
    return next(L for L in SCREW_LENGTHS if L >= minimum)


# --- sensors and electronics (verify against the boards you buy)
AS5600 = dict(board_w=23.0, board_h=23.0, board_t=1.6, chip_from_back=2.6, hole_pitch=17.0, hole_d=2.2,
              magnet_d=6.0, magnet_h=2.5, air_gap=1.5, price=2.5)
OLED = {
    "SSD1306_096": dict(board_w=27.3, board_h=27.8, window_w=25.0, window_h=14.0, window_dy=-1.0,
                        hole_pitch_x=23.0, hole_pitch_y=23.5, hole_d=2.2),
    "SH1106_13":   dict(board_w=35.4, board_h=33.5, window_w=30.0, window_h=15.0, window_dy=-1.5,
                        hole_pitch_x=30.4, hole_pitch_y=28.5, hole_d=2.2),
}
COMPUTERS = {   # same 85 x 56 footprint and 58 x 49 hole pattern; h includes a heatsink
    "PI4_1GB": dict(name="Raspberry Pi 4 Model B 1 GB", w=85.0, d=56.0, h=25.0, holes=(58.0, 49.0), hole_d=2.7, mass=0.046, price=35.0),
    "PI5_4GB": dict(name="Raspberry Pi 5 4 GB", w=85.0, d=56.0, h=30.0, holes=(58.0, 49.0), hole_d=2.7, mass=0.05, price=65.0),
}
ESP32_BOARD = dict(w=90.0, d=62.0, h=25.0, holes=(83.0, 55.0), hole_d=3.2)    # perfboard with ESP32 + 6 x TMC2209
BUCK = dict(w=60.0, d=35.0, h=20.0, holes=(52.0, 27.0), hole_d=3.2)            # 24 V -> 5 V 5 A for the Pi
DC_JACK_D = 8.0                                                                 # panel-mount 5.5/2.1 barrel jack
BUTTON = dict(body=12.0, cap_d=11.5, hole_d=12.4)                             # 12 x 12 tactile switch with cap

LM6UU = dict(d=6.0, D=12.0, L=19.0, price=0.6, mass=0.008)        # linear ball bushing for 6 mm rod
MICROSWITCH = dict(w=20.0, d=6.4, h=10.2, hole_pitch=9.5, hole_d=2.3, price=0.5)   # SS-5GL style
WEBCAMS = {   # body size with the lens facing down; check your camera and its field of view
    "C920": dict(w=95.0, d=29.0, h=25.0, hfov=70.4, vfov=43.3, tripod_thread=True),
    "C270": dict(w=73.0, d=32.0, h=22.0, hfov=55.0, vfov=42.0, tripod_thread=False),
}

# --- stock material
AL_TUBE = {  # square aluminium tube
    "15x15x1.5": dict(w=15.0, t=1.5, kg_per_m=0.22, price_per_m=5.0),
    "20x20x1.5": dict(w=20.0, t=1.5, kg_per_m=0.30, price_per_m=6.0),
    "25x25x1.5": dict(w=25.0, t=1.5, kg_per_m=0.38, price_per_m=7.0),
}
STEEL_DENSITY = 7.85e-6   # kg / mm^3
DOWEL_PRICE = {3: 0.06, 4: 0.07, 5: 0.08}      # per pin
STEEL_BALL_PRICE = 0.03                         # per 6 mm ball
