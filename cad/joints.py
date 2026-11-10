"""One joint = drive + motor + belt + AS5600, plus the holes it needs in its carrier plate.

Everything is built in the joint frame (z = drive axis, output towards +z, z = 0 at the
carrier face the drive sits on, carrier plate at -t..0, belt and sensor beyond it).
Joint-frame angle phi points from the joint axis towards the motor (the belt direction).
The caller maps the kit into its link frame with common.place_axis_x (or a translation for J1).
"""
from math import cos, pi, radians, sin

import cadquery as cq

import cycloidal as cy
from common import as5600_board, belt_solid, motor_holes, motor_pulley_solid, motor_solid, polar, sensor_bridge
from hardware import MOTOR_PULLEY, MOTORS, pick_belt, stack_bolt
from layout import motor_pulley_base


class JointKit:
    def __init__(self, name, D, motor_key, carrier_t, c_nominal, phi_deg, motor_pulley=20,
                 shelf_motor=False, shelf_t=3.0, input_angle=0.0):
        self.name, self.D, self.motor_key, self.t = name, D, motor_key, carrier_t
        self.phi = phi_deg
        self.loop, self.c = pick_belt(c_nominal, motor_pulley, D.pulley_teeth)
        self.motor_pulley = motor_pulley
        self.shelf_motor, self.shelf_t = shelf_motor, shelf_t
        a = radians(phi_deg)
        self.mxy = (self.c * cos(a), self.c * sin(a))
        self.belt_z = D.belt_plane
        self.span = D.pulley_r + 1.5 + 9.0
        parts = cy.build(D, input_angle)
        spin = lambda w: w.rotate((0, 0, 0), (0, 0, 1), phi_deg)
        self.static = {f"{name}_{k}": spin(v) for k, v in {**parts["static"], **parts["internal"]}.items()}
        self.output = {f"{name}_{k}": spin(v) for k, v in parts["output"].items()}
        self._motor()
        self.printed = {f"{name}_sensor_bridge": spin(sensor_bridge(D.z_sensor_chip, -carrier_t, self.span))}
        self.hardware.update({f"{name}_belt": belt_solid((0, 0), D.pulley_teeth, self.mxy, motor_pulley, self.belt_z),
                              f"{name}_as5600": as5600_board(D.z_sensor_chip)})

    # motor: on the drive side of the carrier with its shaft through the plate, or (J1) on a
    # shelf beyond the belt with its shaft pointing back towards the carrier
    def _motor(self):
        mx, my = self.mxy
        m = MOTORS[self.motor_key]
        if not self.shelf_motor:
            face_z = 0.0
            belt_dist = face_z - self.belt_z
            base, _ = motor_pulley_base(self.motor_key, belt_dist)
            body = motor_solid(self.motor_key).rotate((0, 0, 0), (1, 0, 0), 180)          # shaft -> -z
            pul, _ = motor_pulley_solid(base)
            pul = pul.rotate((0, 0, 0), (1, 0, 0), 180)
            self.motor_face_z = face_z
        else:
            # face towards +z (the carrier), pulley teeth first above a shelf of thickness shelf_t
            teeth = MOTOR_PULLEY["width"] - MOTOR_PULLEY["hub_len"]
            base = self.shelf_t + 0.5
            face_z = self.belt_z - base - teeth / 2
            hub_mid = base + teeth + MOTOR_PULLEY["hub_len"] / 2
            if hub_mid > m.shaft_len - 1.5:
                raise ValueError(f"{self.name}: motor shaft too short for the shelf layout")
            body = motor_solid(self.motor_key)
            pul, _ = motor_pulley_solid(base)
            body, pul = body.translate((0, 0, face_z)), pul.translate((0, 0, face_z))
            self.motor_face_z = face_z
        self.hardware = {f"{self.name}_motor": body.translate((mx, my, 0)),
                         f"{self.name}_motor_pulley": pul.translate((mx, my, 0))}

    def carrier_cutter(self, depth_extra=0.0):
        """Holes in the carrier plate (z in [-t, 0]): shaft, through-bolts with nut pockets on the
        far face, sensor-bridge taps, and (unless shelf mounted) slotted motor holes."""
        D, t = self.D, self.t
        a = radians(self.phi)
        bolts = polar(D.bolt_n, D.bolt_r, a + pi / D.bolt_n)
        z0 = -t - depth_extra
        cut = cq.Workplane("XY").workplane(offset=z0).circle(D.hex_af / cos(pi / 6) / 2 + 1.0).extrude(t + depth_extra)
        cut = cut.union(cq.Workplane("XY").workplane(offset=z0).pushPoints(bolts).circle(D.bolt_d / 2).extrude(t + depth_extra))
        self.bolt_len, pocket = stack_bolt(D.z_cap_top, t)
        cut = cut.union(cq.Workplane("XY").workplane(offset=z0).pushPoints(bolts).polygon(6, 6.4).extrude(pocket + depth_extra))  # M3 nuts
        posts = [(self.span * cos(a + pi / 2), self.span * sin(a + pi / 2)),
                 (self.span * cos(a - pi / 2), self.span * sin(a - pi / 2))]
        cut = cut.union(cq.Workplane("XY").workplane(offset=z0).pushPoints(posts).circle(1.25).extrude(t + depth_extra))
        if not self.shelf_motor:
            mh = motor_holes(self.motor_key, t + depth_extra, z0, slot=6.0, slot_dir=(cos(a), sin(a)))
            cut = cut.union(mh.translate((self.mxy[0], self.mxy[1], 0)))
        return cut

    def all_hardware(self):
        return dict(self.hardware)

    def report(self):
        return f"{self.name}: GT2 loop {self.loop} mm, centre distance {self.c:.1f} mm, " \
               f"{self.motor_pulley}T -> {self.D.pulley_teeth}T, motor {self.motor_key}"
