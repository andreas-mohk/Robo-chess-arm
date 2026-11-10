"""Shoulder actuator (J2): NEMA 17 -> 20:1 two-disc cycloidal drive -> 6806 output bearing.

All dimensions in mm. Edit P below; run `python3 cad/shoulder_drive.py` to rebuild,
check for interference and export STEP + STL to cad/out/.

Axial stack, z = 0 at the motor face, output faces +z:
  motor plate | disc A | disc B | housing ring | output cap with 6806 | output clamp
"""
from dataclasses import dataclass, field
from math import atan2, cos, pi, sin
from pathlib import Path

import cadquery as cq


@dataclass
class Params:
    # --- reduction
    ratio: int = 20                 # = number of disc lobes; ring pins = ratio + 1
    pin_circle_r: float = 30.0      # ring pin pitch radius
    ring_pin_d: float = 5.0         # steel dowel
    ring_pin_len: float = 20.0      # standard 5 x 20 dowel
    ecc: float = 1.2                # eccentricity; keep below pin_circle_r / (ratio + 1)
    profile_clear: float = 0.15     # backlash allowance on the cycloid flank
    disc_t: float = 6.0             # each disc; two discs 180 deg apart
    disc_gap: float = 0.5
    # --- output pins (pick off disc rotation)
    out_pins: int = 6
    out_pin_d: float = 5.0
    out_pin_r: float = 19.0
    # --- cam bearings (one per disc)
    cam_brg_id: float = 15.0        # 6802: 15 x 24 x 5
    cam_brg_od: float = 24.0
    cam_brg_w: float = 5.0
    # --- output bearing
    out_brg_id: float = 30.0        # 6806: 30 x 42 x 7
    out_brg_od: float = 42.0
    out_brg_w: float = 7.0
    # --- motor (NEMA 17)
    nema_face: float = 42.3
    nema_hole_pitch: float = 31.0
    nema_boss_d: float = 22.0
    nema_boss_h: float = 2.0
    shaft_d: float = 5.0
    shaft_flat: float = 0.5         # D-flat depth
    # --- housing
    housing_od: float = 84.0
    plate_t: float = 6.0
    bolt_n: int = 6                 # M3 through-bolts holding the stack together
    bolt_r: float = 37.5
    bolt_d: float = 3.4
    flange_d: float = 50.0          # output flange disc carrying the pins
    flange_t: float = 5.0
    clamp_bolt_r: float = 11.0      # M3 screws clamping the 6806 inner race
    arm_bolt_r: float = 15.5        # M3 holes for the upper arm, in the clamp
    clamp_t: float = 5.0
    # --- print fits
    fit: float = 0.15               # radial clearance for printed holes on steel parts
    press: float = -0.05            # radial interference for bearing seats
    seg: int = 1200                 # points on the cycloid outline

    @property
    def n_ring_pins(self):
        return self.ratio + 1

    def check(self):
        assert self.ecc < self.pin_circle_r / self.n_ring_pins, "eccentricity too large: lobes undercut"
        root = self.pin_circle_r - self.ring_pin_d / 2 - self.ecc - self.profile_clear
        hole_outer = self.out_pin_r + self.out_pin_d / 2 + self.ecc + self.fit
        hole_inner = self.out_pin_r - self.out_pin_d / 2 - self.ecc - self.fit
        assert root - hole_outer >= 2.0, f"disc web outside pin holes only {root - hole_outer:.2f} mm"
        assert hole_inner - self.cam_brg_od / 2 >= 1.5, f"disc web at bore only {hole_inner - self.cam_brg_od / 2:.2f} mm"
        assert self.flange_d / 2 - hole_outer >= 2.0
        assert self.bolt_r - self.bolt_d / 2 - (self.pin_circle_r + self.ring_pin_d / 2) >= 2.0
        return self


P = Params().check()

# z positions
Z_PLATE = 0.0
Z_DISC_A = P.plate_t + P.disc_gap
Z_DISC_B = Z_DISC_A + P.disc_t + P.disc_gap
Z_RING_TOP = Z_DISC_B + P.disc_t + P.disc_gap
Z_FLANGE = Z_RING_TOP + 0.5
Z_BRG = Z_FLANGE + P.flange_t
Z_CAP_TOP = Z_BRG + P.out_brg_w
CAP_T = Z_CAP_TOP - Z_RING_TOP


def cycloid_points(p: Params):
    """Disc outline for N ring pins, centred on the disc axis (N-1 lobes)."""
    n, r, rr, e = p.n_ring_pins, p.pin_circle_r, p.ring_pin_d / 2 + p.profile_clear, p.ecc
    pts = []
    for i in range(p.seg):
        t = 2 * pi * i / p.seg
        psi = atan2(sin((1 - n) * t), r / (e * n) - cos((1 - n) * t))
        pts.append((r * cos(t) - rr * cos(t + psi) - e * cos(n * t),
                    -r * sin(t) + rr * sin(t + psi) + e * sin(n * t)))
    return pts


def polar(n, r, phase=0.0):
    return [(r * cos(phase + 2 * pi * k / n), r * sin(phase + 2 * pi * k / n)) for k in range(n)]


def bolt_holes(wp, depth):
    return wp.pushPoints(polar(P.bolt_n, P.bolt_r, pi / P.bolt_n)).hole(P.bolt_d, depth)


def ring_pin_pts():
    return polar(P.n_ring_pins, P.pin_circle_r)


def disc(hole_phase=0.0):
    """One cycloid disc, at its own origin (axis = z, bottom face z = 0).
    hole_phase (rad) turns the output-pin holes relative to the lobes."""
    d = cq.Workplane("XY").polyline(cycloid_points(P)).close().extrude(P.disc_t)
    d = d.faces(">Z").workplane().hole(P.cam_brg_od + 2 * P.press)
    hole = P.out_pin_d + 2 * P.ecc + 2 * P.fit
    return d.faces(">Z").workplane().pushPoints(polar(P.out_pins, P.out_pin_r, hole_phase)).hole(hole)


def motor_plate():
    pl = cq.Workplane("XY").circle(P.housing_od / 2).extrude(P.plate_t)
    pl = pl.faces("<Z").workplane().circle(P.nema_boss_d / 2 + P.fit).cutBlind(-(P.nema_boss_h + 0.3))
    pl = pl.faces(">Z").workplane().hole(P.cam_brg_od + 2)  # clearance for cam
    h = P.nema_hole_pitch / 2
    pl = (pl.faces(">Z").workplane().pushPoints([(h, h), (-h, h), (h, -h), (-h, -h)])
          .cboreHole(3.4, 6.0, 3.2))
    pl = pl.faces(">Z").workplane().pushPoints(ring_pin_pts()).hole(P.ring_pin_d + P.press * 2, 3.0)
    return bolt_holes(pl.faces(">Z").workplane(), P.plate_t)


def housing_ring():
    h = Z_RING_TOP - P.plate_t
    ring = (cq.Workplane("XY").circle(P.housing_od / 2).circle(P.pin_circle_r).extrude(h))
    pins = (cq.Workplane("XY").pushPoints(ring_pin_pts())
            .circle(P.ring_pin_d / 2 + P.press).extrude(h))
    ring = ring.cut(pins)
    ring = bolt_holes(ring.faces(">Z").workplane(), h)
    return ring.translate((0, 0, P.plate_t))


def output_cap():
    cap = cq.Workplane("XY").circle(P.housing_od / 2).extrude(CAP_T)
    # recess for the flange disc on the inside, bearing seat above it
    cap = cap.faces("<Z").workplane().hole(P.flange_d + 2 * 0.5, P.flange_t + 0.5)
    cap = cap.cut(cq.Workplane("XY").workplane(offset=P.flange_t + 0.5)
                  .circle(P.out_brg_od / 2 + P.press).extrude(P.out_brg_w))
    # ring pins: 3 mm in the motor plate, through the ring, rest (+0.3 slack) into the cap
    pocket = P.ring_pin_len - 3 - (Z_RING_TOP - P.plate_t) + 0.3
    cap = cap.cut(cq.Workplane("XY").pushPoints(ring_pin_pts()).circle(P.ring_pin_d / 2 + P.press).extrude(pocket))
    cap = bolt_holes(cap.faces(">Z").workplane(), CAP_T)
    return cap.translate((0, 0, Z_RING_TOP))


def output_flange():
    """Disc carrying the output pins, with a hub through the 6806 inner race."""
    f = cq.Workplane("XY").circle(P.flange_d / 2).extrude(P.flange_t)
    f = f.faces(">Z").workplane().circle(P.out_brg_id / 2 + P.press).extrude(P.out_brg_w)
    f = f.faces(">Z").workplane().hole(P.shaft_d + 3)  # motor shaft tip clearance
    f = (f.faces("<Z").workplane().pushPoints(polar(P.out_pins, P.out_pin_r))
         .hole(P.out_pin_d + 2 * P.press, P.flange_t))
    f = f.faces(">Z").workplane().pushPoints(polar(4, P.clamp_bolt_r, pi / 4)).hole(2.5, P.out_brg_w + 2)  # M3 tap
    return f.translate((0, 0, Z_FLANGE))


def output_clamp():
    """Clamps the 6806 inner race against the flange; the upper arm bolts to it."""
    od = P.out_brg_id + 4  # covers the inner race only
    c = cq.Workplane("XY").circle(od / 2).extrude(P.clamp_t)
    c = c.faces(">Z").workplane().pushPoints(polar(4, P.clamp_bolt_r, pi / 4)).cboreHole(3.4, 6.0, 2.0)
    c = c.faces(">Z").workplane().pushPoints(polar(4, P.arm_bolt_r)).hole(2.5, P.clamp_t)  # M3 tap
    return c.translate((0, 0, Z_CAP_TOP + 0.2))


def cam():
    """Twin eccentric on the motor shaft; lobes 180 deg apart, one 6802 each."""
    lo, hi = Z_DISC_A, Z_DISC_B + P.disc_t
    a = (cq.Workplane("XY").workplane(offset=lo).center(P.ecc, 0)
         .circle(P.cam_brg_id / 2 + P.press).extrude(P.disc_t + P.disc_gap / 2))
    b = (cq.Workplane("XY").workplane(offset=lo + P.disc_t + P.disc_gap / 2).center(-P.ecc, 0)
         .circle(P.cam_brg_id / 2 + P.press).extrude(hi - lo - P.disc_t - P.disc_gap / 2))
    c = a.union(b)
    r = P.shaft_d / 2 + P.fit
    d_bore = (cq.Workplane("XY").workplane(offset=lo).circle(r).extrude(hi - lo)
              .cut(cq.Workplane("XY").workplane(offset=lo).center(r + (r - P.shaft_flat) , 0)
                   .rect(2 * r, 2 * r).extrude(hi - lo)))
    return c.cut(d_bore)


def build(input_angle=0.0):
    """Parts placed for input angle (rad). Disc B is opposite disc A."""
    rot = -input_angle / P.ratio * 180 / pi
    da = (disc().rotate((0, 0, 0), (0, 0, 1), rot)
          .translate((P.ecc * cos(input_angle), P.ecc * sin(input_angle), Z_DISC_A)))
    # disc B: lobes shifted half a lobe, holes shifted back so they line up with the output pins
    db = (disc(-pi / P.ratio).rotate((0, 0, 0), (0, 0, 1), rot + 180 / P.ratio)
          .translate((-P.ecc * cos(input_angle), -P.ecc * sin(input_angle), Z_DISC_B)))
    return {
        "motor_plate": motor_plate(),
        "housing_ring": housing_ring(),
        "cycloid_disc_a": da,
        "cycloid_disc_b": db,
        "cam": cam().rotate((0, 0, 0), (0, 0, 1), input_angle * 180 / pi),
        "output_flange": output_flange().rotate((0, 0, 0), (0, 0, 1), rot),
        "output_cap": output_cap(),
        "output_clamp": output_clamp().rotate((0, 0, 0), (0, 0, 1), rot),
    }


def steel_pins():
    """Ring pins and output pins as solids, for interference checks only."""
    rp = (cq.Workplane("XY").workplane(offset=P.plate_t - 3).pushPoints(ring_pin_pts())
          .circle(P.ring_pin_d / 2).extrude(Z_RING_TOP - P.plate_t + 6))
    op = (cq.Workplane("XY").workplane(offset=Z_DISC_A).pushPoints(polar(P.out_pins, P.out_pin_r))
          .circle(P.out_pin_d / 2).extrude(Z_FLANGE + P.flange_t - Z_DISC_A))
    return rp, op


if __name__ == "__main__":
    out = Path(__file__).parent / "out"
    out.mkdir(exist_ok=True)
    # interference: moving parts against each other and against steel pins at several angles
    rp, op = steel_pins()
    worst = 0.0
    for k in range(6):
        ang = 2 * pi * k / 6 + 0.13
        parts = build(ang)
        op_k = op.rotate((0, 0, 0), (0, 0, 1), -ang / P.ratio * 180 / pi)  # output pins turn with the output
        for name in ("cycloid_disc_a", "cycloid_disc_b"):
            for other, solid in (("ring pins", rp), ("output pins", op_k)):
                v = parts[name].intersect(solid).val().Volume() if parts[name].intersect(solid).vals() else 0.0
                worst = max(worst, v)
                if v > 1e-3:
                    print(f"  interference {name} / {other} at step {k}: {v:.3f} mm^3")
    print(f"worst disc interference: {worst:.4f} mm^3")
    parts = build()
    names = list(parts)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            inter = parts[a].intersect(parts[b])
            v = inter.val().Volume() if inter.vals() else 0.0
            if v > 1e-3:
                print(f"  overlap {a} / {b}: {v:.2f} mm^3")
    for name, wp in parts.items():
        cq.exporters.export(wp, str(out / f"{name}.step"))
        cq.exporters.export(wp, str(out / f"{name}.stl"), tolerance=0.02, angularTolerance=0.1)
    asm = cq.Assembly()
    for name, wp in parts.items():
        asm.add(wp, name=name)
    asm.export(str(out / "shoulder_drive_assembly.step"))
    print(f"stack height {Z_CAP_TOP + 0.2 + P.clamp_t:.1f} mm, OD {P.housing_od} mm; exported to {out}")
