"""IKEA-style assembly guide, drawn from the CAD with hidden-line removal.

  python3 guide.py     -> out/guide/step_XX.svg, out/guide/chess_arm_assembly_guide.pdf, steps.json

Each step: new parts in black, exploded along their assembly direction with a dashed
motion arrow; parts already in place in grey; a hardware box with the screws drawn at
1:1 (hold a screw against the printed page to check it); a repeat badge when the step
is done several times.
"""
import json
import sys
from math import atan2, cos, hypot, pi, sin
from pathlib import Path

import cadquery as cq

import assembly as A
import base
import camera
import cycloidal as cy
import drafting as d
import kinematics as K
import links
import wrist
from config import CFG
from hardware import AS5600, BEARINGS, LM6UU
from layout import D1, D2, D3, D4

C = CFG
OUT = Path(__file__).parent / "out" / "guide"
PW, PH = 297.0, 210.0          # A4 landscape
GREY = "#9a9a9a"
ACCENT = "#0E6B66"


# ------------------------------------------------------------------ helpers
def _wp(*shapes):
    return cq.Workplane("XY").add([s for w in shapes for s in (w.vals() if isinstance(w, cq.Workplane) else [w])])


def ring(od, idd, h, z0=0.0, cx=0.0, cy_=0.0):
    return cq.Workplane("XY").workplane(offset=z0).center(cx, cy_).circle(od / 2).circle(idd / 2).extrude(h)


def drive_bearings(D):
    """Bearing stand-ins in the module frame: journal (cover), two cams, journal (flange), output."""
    jb, cb, ob = D.jb, D.cam, D.ob
    return {
        "brg_cover": ring(jb.D, jb.d, jb.B, D.cover_t - jb.B),
        "brg_cam_a": ring(cb.D, cb.d, cb.B, D.z_disc_a + 0.5, D.ecc, 0),
        "brg_cam_b": ring(cb.D, cb.d, cb.B, D.z_disc_b + 0.5, -D.ecc, 0),
        "brg_flange": ring(jb.D, jb.d, jb.B, D.z_flange),
        "brg_output": ring(ob.D, ob.d, ob.B, D.z_hub),
    }


def center(w):
    return cq.Compound.makeCompound(w.vals()).BoundingBox().center


# ------------------------------------------------------------------ hardware pictograms (1:1, mm)
def screw_icon(x, y, d_, L, label):
    """Socket head cap screw lying horizontally, head on the left; (x, y) = top-left of the head."""
    hd, hh = 1.6 * d_, d_
    o = [f'<rect x="{x:.2f}" y="{y:.2f}" width="{hh:.2f}" height="{hd:.2f}" rx="0.4" fill="#fff" stroke="#111" stroke-width="0.3"/>',
         f'<rect x="{x + hh:.2f}" y="{y + (hd - d_) / 2:.2f}" width="{L:.2f}" height="{d_:.2f}" fill="#fff" stroke="#111" stroke-width="0.3"/>']
    k = x + hh + 1.0
    while k < x + hh + L - 0.3:
        o.append(f'<line x1="{k:.2f}" y1="{y + (hd - d_) / 2:.2f}" x2="{k + 0.4:.2f}" y2="{y + (hd + d_) / 2:.2f}" stroke="#111" stroke-width="0.15"/>')
        k += 0.6 if d_ < 3 else 0.7
    o.append(d.text(x, y + hd + 3.6, label, size=2.6, anchor="start"))
    return "".join(o), hh + L, hd + 4.5


def nut_icon(x, y, d_, label):
    s = 1.8 * d_
    pts = [(x + s / 2 + s / 2 * cos(a * pi / 3), y + s / 2 + s / 2 * sin(a * pi / 3)) for a in range(6)]
    path = "M" + " L".join(f"{a:.2f} {b:.2f}" for a, b in pts) + " Z"
    return (f'<path d="{path}" fill="#fff" stroke="#111" stroke-width="0.3"/>'
            f'<circle cx="{x + s / 2:.2f}" cy="{y + s / 2:.2f}" r="{d_ / 2:.2f}" fill="none" stroke="#111" stroke-width="0.3"/>'
            + d.text(x, y + s + 3.6, label, size=2.6, anchor="start")), s, s + 4.5


def pin_icon(x, y, d_, L, label):
    return (f'<rect x="{x:.2f}" y="{y:.2f}" width="{L:.2f}" height="{d_:.2f}" rx="{d_ / 3:.2f}" fill="#ddd" stroke="#111" stroke-width="0.3"/>'
            + d.text(x, y + d_ + 3.6, label, size=2.6, anchor="start")), L, d_ + 4.5


def bearing_icon(x, y, name, label):
    b = BEARINGS[name]
    r = b.D / 2
    return (f'<circle cx="{x + r:.2f}" cy="{y + r:.2f}" r="{r:.2f}" fill="#fff" stroke="#111" stroke-width="0.3"/>'
            f'<circle cx="{x + r:.2f}" cy="{y + r:.2f}" r="{(b.D + b.d) / 4:.2f}" fill="none" stroke="#111" stroke-width="0.15" stroke-dasharray="0.8 0.5"/>'
            f'<circle cx="{x + r:.2f}" cy="{y + r:.2f}" r="{b.d / 2:.2f}" fill="#fff" stroke="#111" stroke-width="0.3"/>'
            + d.text(x, y + 2 * r + 3.6, label, size=2.6, anchor="start")), 2 * r, 2 * r + 4.5


def generic_icon(x, y, label, w=14, h=8):
    return (f'<rect x="{x:.2f}" y="{y:.2f}" width="{w}" height="{h}" rx="1" fill="#f3f3f3" stroke="#111" stroke-width="0.3"/>'
            + d.text(x + w / 2, y + h / 2 + 1, label.split()[0], size=2.4)
            + d.text(x, y + h + 3.6, label, size=2.6, anchor="start")), max(w, 2.2 * len(label)), h + 4.5


def hw_box(items, x0=PW - 12, y0=12, max_w=120):
    """items: [(count, kind, spec)] -> right-aligned box with 1:1 icons."""
    if not items:
        return ""
    icons = []
    for n, kind, spec in items:
        lab = f"{n}x  {spec}"
        if kind == "screw":
            dd, L = spec.replace("M", "").split(" x ")
            icons.append(lambda x, y, dd=float(dd), L=float(L), lab=lab: screw_icon(x, y, dd, L, lab))
        elif kind == "nut":
            dd = float(spec.replace("M", "").split()[0])
            icons.append(lambda x, y, dd=dd, lab=lab: nut_icon(x, y, dd, lab))
        elif kind == "pin":
            dd, L = spec.replace("Ø", "").split(" x ")
            icons.append(lambda x, y, dd=float(dd), L=float(L), lab=lab: pin_icon(x, y, dd, L, lab))
        elif kind == "bearing":
            icons.append(lambda x, y, s=spec, lab=lab: bearing_icon(x, y, s, lab))
        else:
            icons.append(lambda x, y, lab=lab: generic_icon(x, y, lab))
    # lay out in rows inside max_w
    placed, x, y, row_h, width = [], 0.0, 0.0, 0.0, 0.0
    for f in icons:
        svg, w, h = f(0, 0)
        w = max(w, 24)
        if x > 0 and x + w > max_w:
            x, y = 0.0, y + row_h + 2
            row_h = 0
        placed.append((f, x, y))
        x += w + 6
        width = max(width, x)
        row_h = max(row_h, h)
    bw, bh = width + 6, y + row_h + 8
    bx = x0 - bw
    out = [f'<rect x="{bx:.2f}" y="{y0:.2f}" width="{bw:.2f}" height="{bh:.2f}" rx="2.5" fill="#fff" stroke="#111" stroke-width="0.5"/>']
    for f, x, y in placed:
        svg, _, _ = f(bx + 4 + x, y0 + 5 + y)
        out.append(svg)
    return "".join(out)


# ------------------------------------------------------------------ step renderer
def render_step(no, total, title, parts, view="iso", explode=None, hardware=(), repeat=None, note="", box=None,
                arrows=True):
    """parts: [(name, workplane, role)] role: 'new' | 'old'. explode: {name: (dx, dy, dz)}."""
    explode = explode or {}
    names, shapes, roles = [], [], []
    for n, w, role in parts:
        v = explode.get(n)
        names.append(n)
        shapes.append(w.translate(v) if v else w)
        roles.append(role)
    proj = d.project(shapes, view, with_hidden=False)
    b = d.bounds([pl for r in proj for pl in r["visible"]])
    bx, by, bw, bh = box or (14, 30, PW - 28, PH - 52)
    s = min(bw / max(b[2] - b[0], 1), bh / max(b[3] - b[1], 1)) * 0.92
    cx, cyy = bx + bw / 2, by + bh / 2
    tx = lambda u, v: (cx + (u - (b[0] + b[2]) / 2) * s, cyy - (v - (b[1] + b[3]) / 2) * s)
    o = [f'<rect x="0" y="0" width="{PW}" height="{PH}" fill="#fff"/>']
    for r, role in zip(proj, roles):
        if role == "old":
            o.append(d.polyline_svg(r["visible"], tx, stroke=GREY, width=0.22))
    for r, role in zip(proj, roles):
        if role == "new":
            o.append(d.polyline_svg(r["visible"], tx, stroke="#111", width=0.42))
    if arrows:
        for n, w, role in parts:
            v = explode.get(n)
            if not v or role != "new":
                continue
            c0 = center(w)
            p_from = d.point_2d((c0.x + v[0], c0.y + v[1], c0.z + v[2]), view)
            p_to = d.point_2d((c0.x + v[0] * 0.12, c0.y + v[1] * 0.12, c0.z + v[2] * 0.12), view)
            (x1, y1), (x2, y2) = tx(*p_from), tx(*p_to)
            if hypot(x2 - x1, y2 - y1) < 4:
                continue
            o.append(d.line(x1, y1, x2, y2, w=0.35, dash="2 1.2"))
            o.append(d.arrow_head(x2, y2, atan2(y2 - y1, x2 - x1), size=3.0))
    # step number, title, note, hardware, repeat badge
    o.append(d.text(14, 24, str(no), size=16, anchor="start", weight="bold"))
    o.append(d.text(38, 17, title, size=5.0, anchor="start", weight="bold"))
    if note:
        for i, line_ in enumerate(note.split("\n")):
            o.append(d.text(38, 23.5 + 4.6 * i, line_, size=3.4, anchor="start", fill="#333"))
    o.append(hw_box(hardware))
    if repeat:
        o.append(f'<circle cx="{PW - 24}" cy="{PH - 22}" r="11" fill="{ACCENT}"/>'
                 + d.text(PW - 24, PH - 18.5, repeat, size=9, weight="bold", fill="#fff"))
    o.append(d.line(14, PH - 9, PW - 14, PH - 9, w=0.3, stroke="#bbb"))
    o.append(d.text(14, PH - 4.5, "CHESS ROBOT ARM · ASSEMBLY", size=2.6, anchor="start", fill="#777"))
    o.append(d.text(PW - 14, PH - 4.5, f"{no} / {total}", size=2.8, anchor="end", fill="#777"))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{PW}mm" height="{PH}mm" viewBox="0 0 {PW} {PH}">'
            + "".join(o) + "</svg>")


# ------------------------------------------------------------------ the steps
def drive_steps(D, label, repeat):
    p = cy.build(D)
    st, it, out = p["static"], p["internal"], p["output"]
    rp, op = cy.steel_pins(D)
    br = drive_bearings(D)
    up = (0, 0, 1)
    E = lambda k: (0, 0, k)
    ring_n, ring_d = D.n_ring_pins, D.ring_pin_d
    dowel = f"Ø{ring_d:g} x {D.ring_pin_len:g}"
    odowel = f"Ø{D.out_pin_d:g} x {D.out_pin_len:g}"
    steps = []
    steps.append((f"{label}: ring pins", f"Press the {ring_n} dowels into the housing ring.\nTap them flush with the ring's top face.",
                  [("housing_ring", st["housing_ring"], "old"), ("ring_pins", rp, "new")], "iso", {"ring_pins": E(40)},
                  [(ring_n, "pin", dowel)]))
    steps.append((f"{label}: output flange", "Press the output pins into the flange, then the small bearing\ninto the flange's centre seat (from the pin side).",
                  [("output_flange", out["output_flange"], "old"), ("output_pins", op, "new"), ("brg_flange", br["brg_flange"], "new")],
                  ((1, -1, -0.8), (1, 1, 0)), {"output_pins": E(-45), "brg_flange": E(-30)},
                  [(D.out_pins, "pin", odowel), (1, "bearing", D.journal_brg)]))
    steps.append((f"{label}: bearings in cover and cap", "Press one small bearing into the back cover and the big bearing\ninto the output cap. Push on the outer ring only.",
                  [("back_cover", st["back_cover"], "old"), ("brg_cover", br["brg_cover"], "new"),
                   ("output_cap", st["output_cap"].translate((0, 0, 30)), "old"), ("brg_output", br["brg_output"].translate((0, 0, 30)), "new")],
                  "iso", {"brg_cover": E(25), "brg_output": E(30)}, [(1, "bearing", D.journal_brg), (1, "bearing", D.out_brg)]))
    steps.append((f"{label}: input shaft", "Slide one bearing over each eccentric: the first from the pulley end,\nthe second from the other end.",
                  [("input_shaft", it["input_shaft"], "old"), ("brg_cam_a", br["brg_cam_a"], "new"), ("brg_cam_b", br["brg_cam_b"], "new")],
                  "iso", {"brg_cam_a": E(-35), "brg_cam_b": E(35)}, [(2, "bearing", D.cam_brg)]))
    steps.append((f"{label}: cover, shaft, ring", "Shaft into the cover bearing, then lower the ring with its pins\ninto the cover's pin holes.",
                  [("back_cover", _wp(st["back_cover"], br["brg_cover"]), "old"),
                   ("input_shaft", _wp(it["input_shaft"], br["brg_cam_a"], br["brg_cam_b"]), "new"),
                   ("housing_ring", _wp(st["housing_ring"], rp), "new")],
                  "iso", {"input_shaft": E(40), "housing_ring": E(85)}, []))
    steps.append((f"{label}: discs", "Drop in disc A, then disc B. Turn the shaft a little until each disc\nfalls flat between the pins.",
                  [("base", _wp(st["back_cover"], st["housing_ring"], rp, it["input_shaft"]), "old"),
                   ("cycloid_disc_a", it["cycloid_disc_a"], "new"), ("cycloid_disc_b", it["cycloid_disc_b"], "new")],
                  "iso", {"cycloid_disc_a": E(40), "cycloid_disc_b": E(75)}, []))
    steps.append((f"{label}: output flange and cap", "Feed the flange pins through both discs, onto the shaft's front journal.\nCap on top. Keep the stack together until it is bolted down.",
                  [("base", _wp(st["back_cover"], st["housing_ring"], rp, it["input_shaft"], it["cycloid_disc_a"], it["cycloid_disc_b"]), "old"),
                   ("output_flange", _wp(out["output_flange"], op, br["brg_flange"]), "new"),
                   ("output_cap", _wp(st["output_cap"], br["brg_output"]), "new")],
                  "iso", {"output_flange": E(45), "output_cap": E(90)}, []))
    return [s + (repeat,) for s in steps]


def steps_all():
    g = A.groups(0.0)
    S = []
    S += drive_steps(D2, "Drive J1-J3", "x3")
    S += drive_steps(D4, "Drive J4", "x1")
    # ---------------- base
    bp, bh, bd = g["base"]
    shell = bp["base_shell"]
    floor = bp["base_floor"]
    elec = {k: bh[k] for k in ("computer", "esp32_board", "buck")}
    S.append(("Base: electronics on the floor", "Pi 4, the controller perfboard and the buck converter go on their standoffs.",
              [("base_floor", floor, "old")] + [(k, v, "new") for k, v in elec.items()], "iso",
              {k: (0, 0, 40) for k in elec}, [(4, "screw", "M2.5 x 6"), (8, "screw", "M3 x 6")], None))
    j1_static = _wp(*[v for k, v in bd.items()])
    S.append(("Base: J1 drive", "Drive on top of the base, bolts from the cap side,\nnuts in the pockets under the top plate.",
              [("base_shell", shell, "old"), ("j1", j1_static, "new")], "iso", {"j1": (0, 0, 60)},
              [(6, "screw", "M3 x 40"), (6, "nut", "M3 nut")], None))
    j1_pull = {k: bh[k] for k in ("J1_motor", "J1_motor_pulley", "J1_belt", "J1_as5600")}
    S.append(("Base: J1 belt and sensor (from below)",
              "Pulley onto the shaft hex (grub screw), magnet cap onto the rod, motor on its shelf,\nbelt on, shelf up onto its posts, sensor bridge last.",
              [("base_shell", shell, "old"), ("j1_motor_shelf", bp["j1_motor_shelf"], "new"),
               ("J1_sensor_bridge", bp["J1_sensor_bridge"], "new")] + [(k, v, "new") for k, v in j1_pull.items()],
              ((1, -1, -1), (1, 1, 0)), {"j1_motor_shelf": (0, 0, -35), "J1_motor": (0, 0, -35), "J1_motor_pulley": (0, 0, -35),
                                         "J1_belt": (0, 0, -20), "J1_sensor_bridge": (0, 0, -45), "J1_as5600": (0, 0, -45)},
              [(4, "screw", "M3 x 8"), (2, "screw", "M3 x 12"), (2, "screw", "M3 x 35"), (2, "screw", "M2 x 6"), (1, "screw", "M3 x 4")], None))
    S.append(("Base: close it", "OLED, 3 buttons, DC jack and switch into the shell. Wire up (see the\nelectronics sheets), then screw the floor on.",
              [("base_shell", shell, "old"), ("base_floor", _wp(floor, *elec.values()), "new")],
              ((1, -1, -0.6), (1, 1, 0)), {"base_floor": (0, 0, -70)}, [(4, "screw", "M3 x 8")], None))
    tp, th, td = g["turret"]
    tt = tp["turntable"].translate((-C.yaw_x, 0, 0))
    balls = bh["race_balls"]
    S.append(("Turntable", "Grease the race, lay in the 64 balls, set the turntable on the J1 clamp.\nScrews go through turntable and clamp into the drive's hub.",
              [("base", _wp(shell, j1_static), "old"), ("race_balls", balls, "new"), ("turntable", tt, "new")], "iso",
              {"race_balls": (0, 0, 25), "turntable": (0, 0, 70)}, [(64, "other", "Ø6 steel balls"), (6, "screw", "M3 x 16")], None))
    # ---------------- turret
    tower = tp["tower"]
    j2 = _wp(*[v for k, v in td.items() if k.startswith("J2_")])
    S.append(("Tower: J2 drive and motor", "Drive against the tower plate (6 bolts, nuts on the far side).\nMotor on the drive side, shaft through the slotted holes.",
              [("tower", tower, "old"), ("j2", j2, "new"), ("J2_motor", th["J2_motor"], "new")], "iso",
              {"j2": (60, 0, 0), "J2_motor": (75, 0, 0)}, [(6, "screw", "M3 x 40"), (6, "nut", "M3 nut"), (4, "screw", "M3 x 10")], None))
    S.append(("Tower: J2 belt and sensor", "On the back of the tower: pulley, magnet cap, belt, then the sensor bridge.\nSlide the motor to tension the belt, then tighten.",
              [("tower", _wp(tower, j2, th["J2_motor"]), "old"), ("J2_belt", th["J2_belt"], "new"),
               ("J2_motor_pulley", th["J2_motor_pulley"], "new"), ("J2_sensor_bridge", tp["J2_sensor_bridge"], "new"),
               ("J2_as5600", th["J2_as5600"], "new")],
              "iso_left", {"J2_belt": (-30, 0, 0), "J2_motor_pulley": (-30, 0, 0), "J2_sensor_bridge": (-60, 0, 0), "J2_as5600": (-60, 0, 0)},
              [(2, "screw", "M3 x 35"), (2, "screw", "M2 x 6"), (1, "screw", "M3 x 4")], None))
    turret_all = _wp(tower, j2, *th.values(), tp["J2_sensor_bridge"])
    S.append(("Tower onto the turntable", "Four M4 bolts through the tower foot and the turntable.",
              [("base", _wp(shell, tt, j1_static), "old"), ("tower", turret_all.translate((-C.yaw_x, 0, 0)), "new")], "iso",
              {"tower": (0, 0, 80)}, [(4, "screw", "M4 x 20"), (4, "nut", "M4 nyloc")], None))
    # ---------------- upper arm (bench)
    up, uh, ud = g["upper"]
    S.append(("Upper arm: tube and fittings", f"Cut the {C.tube} tube to {C.L1 - 2 * links.TUBE_START:.0f} mm. Push it into both fittings,\nthen bolt across each socket.",
              [("upper_tube", uh["upper_tube"], "old"), ("upper_proximal", up["upper_proximal"], "new"), ("upper_distal", up["upper_distal"], "new")],
              "iso", {"upper_proximal": (0, -60, 0), "upper_distal": (0, 60, 0)}, [(4, "screw", "M4 x 30"), (4, "nut", "M4 nyloc")], None))
    j3 = _wp(*[v for k, v in ud.items() if k.startswith("J3_")])
    S.append(("Upper arm: J3 drive and motor", "Drive under the elbow plate, motor under the tail plate.\nBelt side stays on top.",
              [("upper", _wp(up["upper_proximal"], up["upper_distal"], uh["upper_tube"]), "old"), ("j3", j3, "new"),
               ("J3_motor", uh["J3_motor"], "new")], "iso", {"j3": (-60, 0, 0), "J3_motor": (-60, 0, 0)},
              [(6, "screw", "M3 x 40"), (6, "nut", "M3 nut"), (4, "screw", "M3 x 10")], None))
    S.append(("Upper arm: J3 belt and sensor", "Pulleys, the long belt, magnet cap, sensor bridge.\nSlide the motor along its slots to tension the belt.",
              [("upper", _wp(up["upper_proximal"], up["upper_distal"], uh["upper_tube"], j3, uh["J3_motor"]), "old"),
               ("J3_belt", uh["J3_belt"], "new"), ("J3_motor_pulley", uh["J3_motor_pulley"], "new"),
               ("J3_sensor_bridge", up["J3_sensor_bridge"], "new"), ("J3_as5600", uh["J3_as5600"], "new")],
              "iso", {"J3_belt": (30, 0, 0), "J3_motor_pulley": (30, 0, 0), "J3_sensor_bridge": (60, 0, 0), "J3_as5600": (60, 0, 0)},
              [(2, "screw", "M3 x 35"), (2, "screw", "M2 x 6"), (1, "screw", "M3 x 4")], None))
    # ---------------- forearm (bench)
    fp, fh, fd = g["fore"]
    S.append(("Forearm: tube and fittings", f"Same as the upper arm: {C.L2 - 2 * links.TUBE_START:.0f} mm tube, 2 bolts per socket.",
              [("fore_tube", fh["fore_tube"], "old"), ("fore_proximal", fp["fore_proximal"], "new"), ("fore_distal", fp["fore_distal"], "new")],
              "iso", {"fore_proximal": (0, -60, 0), "fore_distal": (0, 60, 0)}, [(4, "screw", "M4 x 30"), (4, "nut", "M4 nyloc")], None))
    j4 = _wp(*[v for k, v in fd.items() if k.startswith("J4_")])
    S.append(("Forearm: J4 drive, motor, belt, sensor", "Small drive at the wrist end, motor on the tail.\nBelt, pulleys and sensor bridge on the other side of the plate.",
              [("fore", _wp(fp["fore_proximal"], fp["fore_distal"], fh["fore_tube"]), "old"), ("j4", j4, "new"),
               ("J4_motor", fh["J4_motor"], "new"), ("J4_belt", fh["J4_belt"], "new"), ("J4_sensor_bridge", fp["J4_sensor_bridge"], "new")],
              "iso", {"j4": (60, 0, 0), "J4_motor": (60, 0, 0), "J4_belt": (-30, 0, 0), "J4_sensor_bridge": (-60, 0, 0)},
              [(8, "screw", "M3 x 35"), (6, "nut", "M3 nut"), (4, "screw", "M3 x 10"), (2, "screw", "M2 x 6"), (1, "screw", "M3 x 4")], None))
    # ---------------- wrist and gripper (tool frame)
    brk = wrist.wrist_bracket()
    S.append(("Wrist: roll bearing, hub, roll motor", "Bearing into the shelf pocket from above, hub through it, then the pancake\nmotor on top: its D-shaft slides into the hub.",
              [("wrist_bracket", brk, "old"), ("roll_bearing", wrist.roll_bearing(), "new"), ("roll_hub", wrist.roll_hub(), "new"),
               ("roll_motor", wrist.roll_motor(), "new")], "iso",
              {"roll_bearing": (0, 0, 40), "roll_hub": (0, 0, 70), "roll_motor": (0, 0, 110)},
              [(1, "bearing", "6804"), (4, "screw", "M3 x 10")], None))
    gp, gh = wrist.build_gripper(30)
    S.append(("Gripper: jaws", "Press two LM6UU bushings into each jaw.",
              [("jaw_a", gp["jaw_a"], "old"), ("jaw_b", gp["jaw_b"], "old"), ("lm6uu", gh["lm6uu"], "new")],
              "iso", {"lm6uu": (0, 0, 30)}, [(4, "other", "LM6UU")], None))
    S.append(("Gripper: rods, motor, pinion", "Rods through the end wall and both jaws. Motor on the plate, pinion on its shaft\nwith both jaws at full open. Home switch on the end wall.",
              [("gripper_frame", gp["gripper_frame"], "old"), ("jaws", _wp(gp["jaw_a"], gp["jaw_b"], gh["lm6uu"]), "new"),
               ("gripper_rods", gh["gripper_rods"], "new"), ("gripper_motor", gh["gripper_motor"], "new"), ("pinion", gp["pinion"], "new"),
               ("home_switch", gh["home_switch"], "new")],
              "iso", {"jaws": (0, 0, -45), "gripper_rods": (90, 0, 0), "gripper_motor": (0, 0, 45), "pinion": (0, 0, -25),
                      "home_switch": (25, 0, 0)},
              [(2, "screw", "M3 x 8"), (2, "nut", "M3 nut"), (2, "screw", "M2 x 10")], None))
    wp_, wh_ = wrist.build_wrist(0, 30)
    grip_all = _wp(*[wp_[k] for k in ("gripper_frame", "pinion", "jaw_a", "jaw_b")], *[wh_[k] for k in ("gripper_motor", "gripper_rods", "lm6uu", "home_switch")])
    S.append(("Gripper onto the wrist", "Three screws through the hub flange into the gripper's top plate.",
              [("wrist", _wp(brk, wrist.roll_bearing(), wrist.roll_hub(), wrist.roll_motor()), "old"), ("gripper", grip_all, "new")],
              "iso", {"gripper": (0, 0, -50)}, [(3, "screw", "M3 x 12")], None))
    # ---------------- joining the arm (world, posed)
    pose = (0.0, 60.0, -100.0, -50.0, 0.0)
    w = A.posed(pose)
    f = A.frames(pose)
    base_old = _wp(*w["base"].values(), *w["turret"].values())
    S.append(("Upper arm onto J2", "Upper arm's round plate onto the J2 clamp: six screws through plate and clamp\ninto the J2 hub.",
              [("lower", base_old, "old"), ("upper", _wp(*w["upper"].values()), "new")], "iso",
              {"upper": (80, 0, 0)}, [(6, "screw", "M3 x 16")], None))
    S.append(("Forearm onto J3", "Forearm's round plate onto the J3 clamp, six screws.",
              [("lower", _wp(base_old, *w["upper"].values()), "old"), ("fore", _wp(*w["fore"].values()), "new")], "iso",
              {"fore": (-80, 0, 0)}, [(6, "screw", "M3 x 16")], None))
    S.append(("Wrist onto J4", "Wrist bracket onto the J4 clamp, four M2.5 screws into the J4 hub.",
              [("lower", _wp(base_old, *w["upper"].values(), *w["fore"].values()), "old"), ("tool", _wp(*w["tool"].values()), "new")], "iso",
              {"tool": (70, 0, 0)}, [(4, "screw", "M2.5 x 16")], None))
    # ---------------- camera pole and baseplate
    cp, ch, _ = g["camera"]
    S.append(("Camera pole", f"Cut the 20 mm tube to {camera.Z_POLE_TOP - camera.Z_POLE_BOT:.0f} (pole) and {camera.BOOM_X1 - camera.BOOM_X0:.0f} mm (boom).\nFoot, pole, tee, boom, mount, camera plate. Level the camera with the tilt bolt.",
              [("camera_foot", cp["camera_foot"], "old"), ("pole_tube", ch["pole_tube"], "new"), ("camera_tee", cp["camera_tee"], "new"),
               ("boom_tube", ch["boom_tube"], "new"), ("camera_mount", cp["camera_mount"], "new"),
               ("camera_plate", _wp(cp["camera_plate"], ch["webcam"]), "new")], "iso",
              {"pole_tube": (0, 0, 60), "camera_tee": (0, 0, 120), "boom_tube": (60, 0, 120), "camera_mount": (120, 0, 120),
               "camera_plate": (120, 0, 60)},
              [(4, "screw", "M4 x 35"), (2, "screw", "M4 x 40"), (6, "nut", "M4 nyloc"), (1, "other", "1/4-20 x 10")], None))
    board = cq.Workplane("XY").box(8 * C.square, 8 * C.square, C.board_top_z).translate((0, C.base_to_board + 4 * C.square, C.board_top_z / 2))
    plate = cq.Workplane("XY").box(700, 650, 12).translate((-20, 230, -6))
    S.append(("Baseplate", f"Arm base, chessboard and camera pole on one plywood plate. Board edge {C.base_to_board:g} mm from\nthe base axis, centred; pole at X {C.pole_xy[0]:g}, Y {C.pole_xy[1]:g}. Bolt base and pole foot down.",
              [("plate", plate, "old"), ("board", board, "new"), ("arm", _wp(*w["base"].values(), *w["turret"].values(), *w["upper"].values(),
                                                                             *w["fore"].values(), *w["tool"].values()), "new"),
               ("pole", _wp(*cp.values(), *ch.values()), "new")], "iso", {}, [(8, "screw", "M4 x 25"), (8, "nut", "M4 nyloc")], None))
    return S


def cover(total):
    pose = (0.0, 75.0, -120.0, -45.0, 0.0)
    w = A.posed(pose)
    parts = [(g, _wp(*dct.values()), "new") for g, dct in w.items()]
    svg = render_step(0, total, "", parts, "iso", box=(110, 14, 175, 170), arrows=False)
    head = svg[:svg.index(">") + 1]
    body = svg[svg.index(">") + 1:-6]
    body = body.replace('<text x="14" y="24" font-family', '<text visibility="hidden" x="14" y="24" font-family', 1)
    extra = (d.text(14, 26, "CHESS ROBOT ARM", size=12, anchor="start", weight="bold")
             + d.text(14, 35, "Assembly instructions", size=6, anchor="start")
             + d.text(14, PH - 26, f"{total} steps. Read the whole step before you start it.", size=3.6, anchor="start")
             + d.text(14, PH - 21, "Drawings are generated from the CAD: what you see is what you print.", size=3.2, anchor="start", fill="#555")
             + d.text(14, PH - 16, "Parts in black are new in a step; grey parts are already in place.", size=3.2, anchor="start", fill="#555"))
    return head + body + extra + "</svg>"


def inventory(S):
    """Before-you-start page: tools and every piece of hardware at 1:1 with total counts."""
    from collections import OrderedDict
    tot = OrderedDict()
    for (title, note, parts, view, explode, hw, rep) in S:
        mult = int(rep[1:]) if rep else 1
        for n, kind, spec in hw:
            tot[(kind, spec)] = tot.get((kind, spec), 0) + n * mult
    o = [f'<rect x="0" y="0" width="{PW}" height="{PH}" fill="#fff"/>',
         d.text(14, 22, "Before you start", size=8, anchor="start", weight="bold")]
    tools = ["Hex keys 1.5, 2, 2.5, 3 mm", "Small hammer or a vice (pins, bearings)", "Superglue (magnets)",
             "Bearing grease (ball race)", "Hacksaw + file (aluminium tube)", "Soldering iron, wire stripper",
             "Multimeter", "Pliers, side cutters"]
    o.append(d.text(14, 34, "TOOLS", size=4, anchor="start", weight="bold"))
    for i, t_ in enumerate(tools):
        o.append(f'<rect x="14" y="{38 + i * 7.5:.1f}" width="4" height="4" fill="none" stroke="#111" stroke-width="0.35"/>'
                 + d.text(21, 41.5 + i * 7.5, t_, size=3.4, anchor="start"))
    o.append(d.text(14, 110, "PRINT FIRST", size=4, anchor="start", weight="bold"))
    for i, t_ in enumerate(["All parts: PETG, 0.2 mm, 4 walls.", "Discs, pulleys, shafts, clamps, jaws, pinion: 100 % infill.",
                            "Everything else: 40 % infill.", "See the drawing set for every part."]):
        o.append(d.text(14, 117 + i * 6, t_, size=3.2, anchor="start"))
    o.append(d.text(110, 34, "HARDWARE (all steps, actual size)", size=4, anchor="start", weight="bold"))
    items = [(n, kind, spec) for (kind, spec), n in tot.items()]
    items.sort(key=lambda t: (t[1] != "screw", t[1], t[2]))

    def icon(kind, spec, lab, x, y):
        if kind == "screw":
            dd, L = spec.replace("M", "").split(" x ")
            return screw_icon(x, y, float(dd), float(L), lab)
        if kind == "nut":
            return nut_icon(x, y, float(spec.replace("M", "").split()[0]), lab)
        if kind == "pin":
            dd, L = spec.replace("Ø", "").split(" x ")
            return pin_icon(x, y, float(dd), float(L), lab)
        if kind == "bearing":
            return bearing_icon(x, y, spec, lab)
        return generic_icon(x, y, lab)

    x0, x, y, row_h = 110.0, 110.0, 40.0, 0.0
    for n, kind, spec in items:
        lab = f"{n}x {spec}"
        _, w_, h_ = icon(kind, spec, lab, 0, 0)
        w_ = max(w_, 2.0 * len(lab), 26)
        if x + w_ > PW - 14:
            x, y, row_h = x0, y + row_h + 3, 0.0
        svg, _, _ = icon(kind, spec, lab, x, y)
        o.append(svg)
        x += w_ + 6
        row_h = max(row_h, h_)
    o.append(d.text(14, PH - 14, "Check: print this page at 100 % and a screw should cover its drawing exactly.", size=3.0,
                    anchor="start", fill="#555"))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{PW}mm" height="{PH}mm" viewBox="0 0 {PW} {PH}">'
            + "".join(o) + "</svg>")


def make_pdf():
    import subprocess
    files = [str(OUT / "step_00a_cover.svg"), str(OUT / "step_00b_inventory.svg")] + sorted(
        str(p) for p in OUT.glob("step_[0-9][0-9].svg"))
    tool = Path(__file__).resolve().parent.parent / "tools" / "svg2pdf.js"
    subprocess.run(["node", str(tool), str(OUT / "chess_arm_assembly_guide.pdf"), "297", "210", *files], check=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    only = int(sys.argv[1]) if len(sys.argv) > 1 else None
    if only == 0:
        only = 0
    S = steps_all()
    total = len(S)
    meta = []
    for i, (title, note, parts, view, explode, hw, rep) in enumerate(S, 1):
        meta.append({"no": i, "title": title, "note": note, "hardware": hw, "repeat": rep})
        if only is not None and i != only:
            continue
        (OUT / f"step_{i:02d}.svg").write_text(render_step(i, total, title, parts, view, explode, hw, rep, note))
        print("step", i, title)
    (OUT / "steps.json").write_text(json.dumps(meta, indent=1))
    if only is None or only == 0:
        (OUT / "step_00b_inventory.svg").write_text(inventory(S))
        (OUT / "step_00a_cover.svg").write_text(cover(total))
        print("cover + inventory")
    if only is None:
        make_pdf()


if __name__ == "__main__":
    main()
