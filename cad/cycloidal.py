"""Parametric two-disc cycloidal drive, belt-driven, with an absolute angle sensor.

Used for J1-J4. Module frame: z axis = joint axis, z = 0 at the outer face of the
back cover, output faces +z. Everything behind the cover (pulley, magnet) is at z < 0.

Power path:  belt -> pulley -> hollow input shaft with two eccentrics -> two cycloid
discs rolling in N ring pins -> output pins -> output flange (in the output bearing)
-> clamp -> next link.
Sensor path: a thin rod printed on the output flange runs back through the hollow
input shaft; a diametric magnet on its tip faces an AS5600 behind the pulley, so the
sensor reads the OUTPUT angle directly.
"""
from dataclasses import dataclass, replace
from math import atan2, cos, pi, sin

import cadquery as cq

from hardware import AS5600, BEARINGS, GT2_PITCH, GT2_PLD, gt2_pitch_r


@dataclass(frozen=True)
class DriveParams:
    ratio: int = 20                  # disc lobes; ring pins = ratio + 1
    pin_circle_r: float = 30.0
    ring_pin_d: float = 5.0          # steel dowel
    ring_pin_len: float = 20.0
    ecc: float = 1.2                 # must stay below pin_circle_r / (ratio + 1)
    profile_clear: float = 0.15      # backlash allowance on the cycloid flank
    disc_t: float = 6.0
    disc_gap: float = 0.5
    out_pins: int = 6
    out_pin_d: float = 5.0
    out_pin_r: float = 19.0
    out_pin_len: float = 20.0
    cam_brg: str = "6802"            # on each eccentric
    journal_brg: str = "6801"        # input shaft support, one in the cover, one in the flange
    out_brg: str = "6806"            # output bearing
    housing_od: float = 84.0
    cover_t: float = 7.0
    bolt_n: int = 6                  # through-bolts, also mount the drive to its carrier
    bolt_r: float = 37.5
    bolt_d: float = 3.4
    flange_extra_t: float = 2.0      # flange thickness beyond the journal bearing
    clamp_t: float = 5.0
    clamp_bolt_n: int = 6            # screws through next link + clamp into the flange hub
    clamp_bolt_r: float = 11.0
    clamp_bolt_d: float = 3.4
    clamp_tap_d: float = 2.5
    rod_d: float = 4.0               # printed sensor rod, part of the output flange
    pulley_teeth: int = 40           # printed GT2 pulley on the input shaft
    belt_w: float = 6.0
    pulley_hub: float = 5.0          # hub length with radial M3 grub screw
    back_offset: float = 1.0         # outer face of cover -> pulley (add carrier plate thickness if the
                                     # pulley sits beyond the carrier)
    fit: float = 0.15                # radial clearance, printed hole on steel
    press: float = -0.05             # radial interference, bearing seats
    seg: int = 1200                  # points on the cycloid outline

    # ---------- derived
    @property
    def n_ring_pins(self):
        return self.ratio + 1

    @property
    def cam(self):
        return BEARINGS[self.cam_brg]

    @property
    def jb(self):
        return BEARINGS[self.journal_brg]

    @property
    def ob(self):
        return BEARINGS[self.out_brg]

    @property
    def flange_t(self):
        return self.jb.B + self.flange_extra_t

    @property
    def flange_d(self):
        return 2 * (self.out_pin_r + self.out_pin_d / 2 + 3.0)

    # z stations
    @property
    def z_disc_a(self):
        return self.cover_t + self.disc_gap

    @property
    def z_disc_b(self):
        return self.z_disc_a + self.disc_t + self.disc_gap

    @property
    def z_ring_top(self):
        return self.z_disc_b + self.disc_t + self.disc_gap

    @property
    def z_flange(self):
        return self.z_ring_top + 0.5

    @property
    def z_hub(self):
        return self.z_flange + self.flange_t

    @property
    def z_cap_top(self):
        return self.z_hub + self.ob.B

    @property
    def z_clamp(self):
        return self.z_cap_top + 0.2

    @property
    def height(self):
        """Back cover outer face to clamp outer face (where the next link sits)."""
        return self.z_clamp + self.clamp_t

    @property
    def hex_af(self):
        return round(self.jb.d * 0.866 - 0.2, 2)

    @property
    def pulley_w(self):
        return self.belt_w + 1 + 2 * 1.0 + self.pulley_hub

    @property
    def z_pulley(self):
        """Pulley occupies [z_pulley - pulley_w, z_pulley]; hub end is the far one."""
        return -self.back_offset

    @property
    def z_shaft_end(self):
        return self.z_pulley - self.pulley_w

    @property
    def z_magnet(self):
        """Outer face of the magnet."""
        return self.z_shaft_end - 0.8 - self.magnet_cap_h

    @property
    def magnet_cap_h(self):
        return AS5600["magnet_h"] + 1.0 + 3.0     # magnet pocket, web, rod socket

    @property
    def z_sensor_chip(self):
        return self.z_magnet - AS5600["air_gap"]

    @property
    def belt_plane(self):
        """z of the belt centre line."""
        return self.z_pulley - 1.0 - (self.belt_w + 1) / 2

    @property
    def pulley_r(self):
        return gt2_pitch_r(self.pulley_teeth)

    def check(self):
        msgs = []
        if self.ecc >= self.pin_circle_r / self.n_ring_pins:
            msgs.append("eccentricity too large: lobes undercut")
        root = self.pin_circle_r - self.ring_pin_d / 2 - self.ecc - self.profile_clear
        hole_r = (self.out_pin_d + 2 * self.ecc) / 2 + self.fit
        if root - (self.out_pin_r + hole_r) < 2.0:
            msgs.append(f"disc web outside pin holes {root - self.out_pin_r - hole_r:.2f} < 2 mm")
        if (self.out_pin_r - hole_r) - self.cam.D / 2 < 1.5:
            msgs.append(f"disc web at bore {(self.out_pin_r - hole_r) - self.cam.D / 2:.2f} < 1.5 mm")
        if self.bolt_r - self.bolt_d / 2 - (self.pin_circle_r + self.ring_pin_d / 2) < 2.0:
            msgs.append("through-bolts too close to ring pins")
        if self.housing_od / 2 - self.bolt_r - self.bolt_d / 2 < 2.0:
            msgs.append("through-bolts too close to housing edge")
        if self.cam.d / 2 < self.jb.d / 2 + self.ecc:
            msgs.append("eccentric lobe does not cover the journal")
        if self.cam.d / 2 - self.ecc - (self.rod_d / 2 + 0.5) < 2.0:
            msgs.append("input shaft wall at the eccentric < 2 mm")
        if (self.hex_af - (self.rod_d + 1)) / 2 < 1.6:
            msgs.append("input shaft wall at the pulley hex < 1.6 mm")
        if self.clamp_bolt_r + self.clamp_bolt_d / 2 > self.ob.d / 2 - 1.5:
            msgs.append("clamp screws too close to hub edge")
        pin_bottom = self.z_hub - self.out_pin_len
        if pin_bottom > self.z_disc_a + 1.0:
            msgs.append(f"output pins too short: end {pin_bottom - self.z_disc_a:.1f} mm above disc A's bottom")
        if pin_bottom < self.cover_t + 0.3:
            msgs.append("output pins too long: they touch the back cover")
        pin_span = self.ring_pin_len - 3 - (self.z_ring_top - self.cover_t)
        if pin_span < 1.5:
            msgs.append("ring pins too short to reach the cap")
        if msgs:
            raise ValueError("DriveParams: " + "; ".join(msgs))
        return self


# ------------------------------------------------------------------ helpers
def polar(n, r, phase=0.0):
    return [(r * cos(phase + 2 * pi * k / n), r * sin(phase + 2 * pi * k / n)) for k in range(n)]


def cycloid_points(p: DriveParams):
    n, r, rr, e = p.n_ring_pins, p.pin_circle_r, p.ring_pin_d / 2 + p.profile_clear, p.ecc
    pts = []
    for i in range(p.seg):
        t = 2 * pi * i / p.seg
        psi = atan2(sin((1 - n) * t), r / (e * n) - cos((1 - n) * t))
        pts.append((r * cos(t) - rr * cos(t + psi) - e * cos(n * t),
                    -r * sin(t) + rr * sin(t + psi) + e * sin(n * t)))
    return pts


def gt2_pulley(teeth, width, bore_hex_af=None, bore_d=None, flange=1.0, hub=0.0, hub_d=None):
    """Printed GT2 pulley, axis z, toothed section first, hub (if any) at the +z end.
    Tooth grooves are approximated by circles; good enough for a printed pulley."""
    pd = teeth * GT2_PITCH / pi
    od = pd - 2 * GT2_PLD
    p = cq.Workplane("XY").circle(od / 2).extrude(width)
    groove_r = 0.555
    centre = od / 2 - 0.75 + groove_r
    grooves = (cq.Workplane("XY").pushPoints(polar(teeth, centre))
               .circle(groove_r).extrude(width))
    p = p.cut(grooves)
    fl = cq.Workplane("XY").circle(od / 2 + 1.5).extrude(flange)
    p = p.union(fl.translate((0, 0, -flange))).union(fl.translate((0, 0, width)))
    p = p.translate((0, 0, flange))
    total = width + 2 * flange
    if hub:
        p = p.union(cq.Workplane("XY").workplane(offset=total).circle((hub_d or od * 0.6) / 2).extrude(hub))
        total += hub
    if bore_hex_af:
        p = p.cut(cq.Workplane("XY").polygon(6, bore_hex_af / cos(pi / 6) + 0.3).extrude(total))
    elif bore_d:
        p = p.cut(cq.Workplane("XY").circle(bore_d / 2).extrude(total))
    return p


# ------------------------------------------------------------------ parts (module frame)
def ring_pin_pts(p):
    return polar(p.n_ring_pins, p.pin_circle_r)


def bolt_pts(p):
    return polar(p.bolt_n, p.bolt_r, pi / p.bolt_n)


def back_cover(p: DriveParams):
    c = cq.Workplane("XY").circle(p.housing_od / 2).extrude(p.cover_t)
    c = c.cut(cq.Workplane("XY").circle(p.jb.d / 2 + 1.0).extrude(p.cover_t))
    c = c.cut(cq.Workplane("XY").workplane(offset=p.cover_t - p.jb.B).circle(p.jb.D / 2 + p.press).extrude(p.jb.B))
    c = c.cut(cq.Workplane("XY").workplane(offset=p.cover_t - 3).pushPoints(ring_pin_pts(p))
              .circle(p.ring_pin_d / 2 + p.press).extrude(3))
    c = c.cut(cq.Workplane("XY").pushPoints(bolt_pts(p)).circle(p.bolt_d / 2).extrude(p.cover_t))
    return c


def housing_ring(p: DriveParams):
    h = p.z_ring_top - p.cover_t
    r = cq.Workplane("XY").circle(p.housing_od / 2).circle(p.pin_circle_r).extrude(h)
    r = r.cut(cq.Workplane("XY").pushPoints(ring_pin_pts(p)).circle(p.ring_pin_d / 2 + p.press).extrude(h))
    r = r.cut(cq.Workplane("XY").pushPoints(bolt_pts(p)).circle(p.bolt_d / 2).extrude(h))
    return r.translate((0, 0, p.cover_t))


def output_cap(p: DriveParams):
    t = p.z_cap_top - p.z_ring_top
    c = cq.Workplane("XY").circle(p.housing_od / 2).extrude(t)
    recess = p.flange_t + 0.5
    c = c.cut(cq.Workplane("XY").circle(p.flange_d / 2 + 0.5).extrude(recess))
    c = c.cut(cq.Workplane("XY").workplane(offset=recess).circle(p.ob.D / 2 + p.press).extrude(t - recess))
    pocket = p.ring_pin_len - 3 - (p.z_ring_top - p.cover_t) + 0.3
    c = c.cut(cq.Workplane("XY").pushPoints(ring_pin_pts(p)).circle(p.ring_pin_d / 2 + p.press).extrude(pocket))
    c = c.cut(cq.Workplane("XY").pushPoints(bolt_pts(p)).circle(p.bolt_d / 2).extrude(t))
    return c.translate((0, 0, p.z_ring_top))


def disc(p: DriveParams, hole_phase=0.0):
    d = cq.Workplane("XY").polyline(cycloid_points(p)).close().extrude(p.disc_t)
    d = d.cut(cq.Workplane("XY").circle(p.cam.D / 2 + p.press).extrude(p.disc_t))
    hole = p.out_pin_d + 2 * p.ecc + 2 * p.fit
    return d.cut(cq.Workplane("XY").pushPoints(polar(p.out_pins, p.out_pin_r, hole_phase))
                 .circle(hole / 2).extrude(p.disc_t))


def output_flange(p: DriveParams):
    """Pin carrier + hub through the output bearing + printed sensor rod reaching back."""
    f = cq.Workplane("XY").circle(p.flange_d / 2).extrude(p.flange_t)
    f = f.union(cq.Workplane("XY").workplane(offset=p.flange_t).circle(p.ob.d / 2 + p.press).extrude(p.ob.B))
    f = f.cut(cq.Workplane("XY").circle(p.jb.D / 2 + p.press).extrude(p.jb.B))           # journal seat
    f = f.cut(cq.Workplane("XY").pushPoints(polar(p.out_pins, p.out_pin_r))
              .circle(p.out_pin_d / 2 + p.press).extrude(p.flange_t))
    tap = p.ob.B + p.flange_extra_t - 0.8
    f = f.cut(cq.Workplane("XY").workplane(offset=p.flange_t + p.ob.B - tap)
              .pushPoints(polar(p.clamp_bolt_n, p.clamp_bolt_r)).circle(p.clamp_tap_d / 2).extrude(tap))
    rod_len = p.jb.B - (p.z_shaft_end - 0.8 - 2.8)  # seat bottom -> into the magnet cap socket
    f = f.union(cq.Workplane("XY").workplane(offset=p.jb.B).circle(p.rod_d / 2).extrude(-rod_len))
    return f.translate((0, 0, p.z_flange))


def output_clamp(p: DriveParams):
    od = p.ob.d + 4
    c = cq.Workplane("XY").circle(od / 2).extrude(p.clamp_t)
    c = c.cut(cq.Workplane("XY").pushPoints(polar(p.clamp_bolt_n, p.clamp_bolt_r))
              .circle(p.clamp_bolt_d / 2).extrude(p.clamp_t))
    return c.translate((0, 0, p.z_clamp))


def input_shaft(p: DriveParams):
    jd, e = p.jb.d, p.ecc
    z0 = p.z_shaft_end
    s = cq.Workplane("XY").workplane(offset=z0).polygon(6, p.hex_af / cos(pi / 6)).extrude(-z0)       # hex
    s = s.union(cq.Workplane("XY").circle(jd / 2).extrude(p.cover_t + 0.2))                           # back journal
    za_end = p.z_disc_a + p.disc_t + p.disc_gap / 2
    s = s.union(cq.Workplane("XY").workplane(offset=p.cover_t + 0.2).center(e, 0)
                .circle(p.cam.d / 2 + p.press).extrude(za_end - p.cover_t - 0.2))                  # lobe A
    s = s.union(cq.Workplane("XY").workplane(offset=za_end).center(-e, 0)
                .circle(p.cam.d / 2 + p.press).extrude(p.z_ring_top - za_end))                     # lobe B
    s = s.union(cq.Workplane("XY").workplane(offset=p.z_ring_top)
                .circle(jd / 2).extrude(p.z_flange + p.jb.B - 0.3 - p.z_ring_top))                 # front journal
    return s.cut(cq.Workplane("XY").workplane(offset=z0).circle(p.rod_d / 2 + 0.5).extrude(200))


def input_pulley(p: DriveParams):
    pl = gt2_pulley(p.pulley_teeth, p.belt_w + 1, bore_hex_af=p.hex_af, hub=p.pulley_hub,
                    hub_d=p.hex_af + 8)
    # radial M3 grub hole in the hub
    pl = pl.cut(cq.Workplane("YZ").workplane(offset=0).center(0, p.belt_w + 3 + p.pulley_hub / 2)
                .circle(1.25).extrude(p.hex_af + 10))
    # hub end faces -z (away from the cover)
    return pl.mirror("XY").translate((0, 0, p.z_pulley))


def magnet_cap(p: DriveParams):
    mh, md = AS5600["magnet_h"], AS5600["magnet_d"]
    h = p.magnet_cap_h
    c = cq.Workplane("XY").circle(md / 2 + 1.2).extrude(h)
    c = c.cut(cq.Workplane("XY").circle(md / 2 + 0.05).extrude(mh))                       # magnet, open at -z
    c = c.cut(cq.Workplane("XY").workplane(offset=h - 3).circle(p.rod_d / 2 + 0.05).extrude(3))  # rod socket
    return c.translate((0, 0, p.z_magnet))


def build(p: DriveParams, input_angle=0.0):
    """Returns parts grouped by what they move with.
    'static': fixed to the carrier.  'output': turns with the output.  'internal': discs and shaft."""
    out_rot = -input_angle / p.ratio * 180 / pi
    ca, sa = cos(input_angle), sin(input_angle)
    da = (disc(p).rotate((0, 0, 0), (0, 0, 1), out_rot).translate((p.ecc * ca, p.ecc * sa, p.z_disc_a)))
    db = (disc(p, -pi / p.ratio).rotate((0, 0, 0), (0, 0, 1), out_rot + 180 / p.ratio)
          .translate((-p.ecc * ca, -p.ecc * sa, p.z_disc_b)))
    rotz = lambda w, a: w.rotate((0, 0, 0), (0, 0, 1), a)
    return {
        "static": {"back_cover": back_cover(p), "housing_ring": housing_ring(p), "output_cap": output_cap(p)},
        "output": {"output_flange": rotz(output_flange(p), out_rot), "output_clamp": rotz(output_clamp(p), out_rot),
                   "magnet_cap": magnet_cap(p)},
        "internal": {"cycloid_disc_a": da, "cycloid_disc_b": db,
                     "input_shaft": rotz(input_shaft(p), input_angle * 180 / pi),
                     "input_pulley": rotz(input_pulley(p), input_angle * 180 / pi)},
    }


def steel_pins(p: DriveParams, output_rot_deg=0.0):
    rp = (cq.Workplane("XY").workplane(offset=p.cover_t - 3).pushPoints(ring_pin_pts(p))
          .circle(p.ring_pin_d / 2).extrude(p.ring_pin_len))
    op = (cq.Workplane("XY").workplane(offset=p.z_flange + p.flange_t - p.out_pin_len)
          .pushPoints(polar(p.out_pins, p.out_pin_r)).circle(p.out_pin_d / 2).extrude(p.out_pin_len))
    return rp, op.rotate((0, 0, 0), (0, 0, 1), output_rot_deg)


def _vol(w):
    return sum(v.Volume() for v in w.vals()) if w.vals() else 0.0


def interference_report(p: DriveParams, steps=6):
    """Largest overlap (mm^3) between discs and steel pins, and between any two parts, over `steps` input angles."""
    worst, pairs = 0.0, []
    for k in range(steps):
        ang = 2 * pi * k / steps + 0.13
        parts = build(p, ang)
        rp, op = steel_pins(p, -ang / p.ratio * 180 / pi)
        for name in ("cycloid_disc_a", "cycloid_disc_b"):
            for solid in (rp, op):
                worst = max(worst, _vol(parts["internal"][name].intersect(solid)))
    flat = {n: w for g in build(p).values() for n, w in g.items()}
    names = list(flat)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            v = _vol(flat[a].intersect(flat[b]))
            if v > 1e-3:
                pairs.append((a, b, v))
    return worst, pairs


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from config import CFG
    for j in ("J1", "J2", "J3", "J4"):
        p = CFG.drive(j).check()
        w, pairs = interference_report(p)
        print(f"{j}: ratio {p.ratio}:1, OD {p.housing_od}, height {p.height:.1f}, worst disc/pin overlap {w:.4f} mm^3,"
              f" part overlaps {pairs or 'none'}")
