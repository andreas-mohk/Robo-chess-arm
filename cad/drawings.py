"""Technical drawing set (A3 sheets, SVG + one combined PDF) generated from the CAD.

  python3 drawings.py            -> out/drawings/*.svg and out/drawings/chess_arm_drawings.pdf

Sheets: 1 general arrangement, sub-assemblies (drives with section A-A, base, turret,
upper arm, forearm, wrist + gripper, camera pole) with balloons and parts lists, then one
sheet per unique printed part (identical parts are merged and their quantity counted).
"""
import json
import re
import sys
from math import atan2, cos, pi, sin
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
from common import sensor_bridge
from config import CFG
from layout import D1, D2, D3, D4

C = CFG
OUT = Path(__file__).parent / "out" / "drawings"
FULL_INFILL = ("disc", "pulley", "pinion", "jaw", "input_shaft", "clamp", "roll_hub")


# ------------------------------------------------------------------ part catalogue
def unique_printed_parts():
    """[(display name, workplane in a sensible frame, qty, used-in)] with identical parts merged."""
    raw = []
    for k in (base.K1, links.K2, links.K3, links.K4):
        parts = cy.build(k.D)
        for grp in ("static", "internal", "output"):
            for n, w in parts[grp].items():
                raw.append((f"{n}", w, k.name))
        raw.append(("sensor_bridge", sensor_bridge(k.D.z_sensor_chip, -k.t, k.span), k.name))
    for n, w in (("base_shell", base.base_shell()), ("base_floor", base.base_floor()),
                 ("j1_motor_shelf", base.j1_motor_shelf()), ("turntable", base.turntable()),
                 ("tower", links.tower()), ("upper_proximal", links.upper_proximal()),
                 ("upper_distal", links.upper_distal()), ("fore_proximal", links.fore_proximal()),
                 ("fore_distal", links.fore_distal()), ("wrist_bracket", wrist.wrist_bracket()),
                 ("roll_hub", wrist.roll_hub())):
        raw.append((n, w, "-"))
    gp, _ = wrist.build_gripper()
    for n, w in gp.items():
        raw.append((n, w, "gripper"))
    cp, _ = camera.camera_group()
    for n, w in cp.items():
        raw.append((n, w, "camera pole"))
    merged = {}
    for n, w, use in raw:
        o = d.orient_for_drawing(w)
        bb = cq.Compound.makeCompound(o.vals()).BoundingBox()
        vol = sum(s.Volume() for s in o.vals())
        key = (n, round(vol), round(bb.xlen, 1), round(bb.ylen, 1), round(bb.zlen, 1))
        if key in merged:
            merged[key][2] += 1
            merged[key][3].append(use)
        else:
            merged[key] = [n, o, 1, [use]]
    counts = {}
    for n, *_ in merged.values():
        counts[n] = counts.get(n, 0) + 1
    final = []
    for n, o, q, uses in merged.values():
        label = f"{n} ({', '.join(uses)})" if counts[n] > 1 or n == "sensor_bridge" else n
        final.append((label, o, q))
    return final


def _label(n):
    return n.replace("_", " ").upper()


# ------------------------------------------------------------------ part sheet
def part_sheet(no, total, name, w, qty):
    v = {k: d.project([w], k)[0] for k in ("front", "top", "right", "iso")}
    bb = cq.Compound.makeCompound(w.vals()).BoundingBox()
    X, Y, Z = bb.xlen, bb.ylen, bb.zlen
    gap = 22.0
    s, slab = d.pick_scale(X + Y + gap, Z + Y + gap, 255, 205)
    body = []
    fb = d.bounds(v["front"]["visible"] + v["front"]["hidden"])
    tb = d.bounds(v["top"]["visible"] + v["top"]["hidden"])
    rb = d.bounds(v["right"]["visible"] + v["right"]["hidden"])
    x_left = 32.0
    y_front_bottom = 245.0
    fy_top = y_front_bottom - (fb[3] - fb[1]) * s
    tx_front = lambda u, vv: (x_left + (u - fb[0]) * s, y_front_bottom - (vv - fb[1]) * s)
    top_bottom = fy_top - gap
    tx_top = lambda u, vv: (x_left + (u - tb[0]) * s, top_bottom - (vv - tb[1]) * s)
    x_right = x_left + (fb[2] - fb[0]) * s + gap
    tx_right = lambda u, vv: (x_right + (u - rb[0]) * s, y_front_bottom - (vv - rb[1]) * s)
    for key, tx, lab in (("front", tx_front, "FRONT"), ("top", tx_top, "TOP"), ("right", tx_right, "RIGHT")):
        body.append(d.polyline_svg(v[key]["hidden"], tx, width=d.THIN, dash="1.2 0.8", stroke="#333"))
        body.append(d.polyline_svg(v[key]["visible"], tx, width=d.MED))
    # dimensions
    a, b = tx_front(fb[0], fb[1]), tx_front(fb[2], fb[1])
    body.append(d.dim_linear(*a, *b, -7, f"{X:.1f}"))
    a, b = tx_front(fb[0], fb[1]), tx_front(fb[0], fb[3])
    body.append(d.dim_linear(*a, *b, 7, f"{Z:.1f}"))
    a, b = tx_top(tb[0], tb[1]), tx_top(tb[0], tb[3])
    body.append(d.dim_linear(*a, *b, 7, f"{Y:.1f}"))
    a, b = tx_right(rb[0], rb[1]), tx_right(rb[2], rb[1])
    body.append(d.dim_linear(*a, *b, -7, f"{Y:.1f}"))
    lx = x_left + (fb[2] - fb[0]) * s / 2
    body.append(d.text(lx, y_front_bottom + 16, "FRONT", size=3, weight="bold"))
    body.append(d.text(x_left + (tb[2] - tb[0]) * s / 2, top_bottom + 13, "TOP", size=3, weight="bold"))
    body.append(d.text(x_right + (rb[2] - rb[0]) * s / 2, y_front_bottom + 16, "RIGHT", size=3, weight="bold"))
    # iso, top right, own scale if needed
    ib = d.bounds(v["iso"]["visible"])
    iw, ih = ib[2] - ib[0], ib[3] - ib[1]
    si = min(s, 110 / max(iw, 1), 95 / max(ih, 1))
    cx0, cy0 = 350.0, 75.0
    tx_iso = lambda u, vv: (cx0 + (u - (ib[0] + ib[2]) / 2) * si, cy0 - (vv - (ib[1] + ib[3]) / 2) * si)
    body.append(d.polyline_svg(v["iso"]["visible"], tx_iso, width=d.MED))
    body.append(d.text(cx0, cy0 + ih * si / 2 + 8, "ISOMETRIC" + ("" if abs(si - s) < 1e-6 else " (NOT TO SCALE)"),
                       size=3, weight="bold"))
    # hole table
    holes = d.hole_table(w)
    if holes:
        rows = [[f"Ø{dd:g}", ax, str(n)] for dd, ax, n in holes[:14]]
        tb_svg, _ = d.table(290, 140, ["HOLE", "AXIS", "QTY"], rows, [22, 16, 14])
        body.append(tb_svg)
    infill = "100 %" if any(k in name for k in FULL_INFILL) else "40 %"
    notes = (f"PRINT: PETG, 0.2 mm layers, 4 perimeters, {infill} infill.",
             "HOLES ARE MODELLED AT PRINT SIZE (FIT ALLOWANCES INCLUDED); BEARING SEATS PRESS-FIT.",
             "UNTOLERANCED: ±0.2 mm. BREAK SHARP EDGES.")
    body.insert(0, d.frame(no, total, _label(name.split(" (")[0]), name if "(" in name else "Printed part",
                           f"P-{no:03d}", slab, material="PETG", qty=str(qty), notes=notes))
    return d.svg_doc("".join(body))


# ------------------------------------------------------------------ assembly helpers
def _assembly_views(parts, views, box, scale=None, hidden=False, styles=None):
    """Project named parts into several views laid out in `box` slots. Returns (svg, scale, transforms)."""
    names = list(parts)
    proj = {k: d.project([parts[n] for n in names], k, with_hidden=hidden) for k in views}
    bounds = {k: d.bounds([pl for r in proj[k] for pl in r["visible"]]) for k in views}
    if scale is None:
        s = min(min(box[k][2] / max(bounds[k][2] - bounds[k][0], 1), box[k][3] / max(bounds[k][3] - bounds[k][1], 1))
                for k in views)
        s, lab = next(((sc, l) for sc, l in d.STD_SCALES if sc <= s * 1.0001), d.STD_SCALES[-1])
    else:
        s, lab = scale
    svg, txs = [], {}
    for k in views:
        bx, by, bw, bh = box[k]
        b = bounds[k]
        cx, cyy = bx + bw / 2, by + bh / 2
        tx = (lambda b, cx, cyy: (lambda u, v: (cx + (u - (b[0] + b[2]) / 2) * s, cyy - (v - (b[1] + b[3]) / 2) * s)))(b, cx, cyy)
        txs[k] = (tx, b)
        for n, r in zip(names, proj[k]):
            st = (styles or {}).get(n, {})
            if hidden:
                svg.append(d.polyline_svg(r["hidden"], tx, width=d.THIN, dash="1.2 0.8", stroke="#555"))
            svg.append(d.polyline_svg(r["visible"], tx, width=st.get("w", d.MED), stroke=st.get("c", d.INK)))
    return "".join(svg), (s, lab), txs, proj, names


def _balloons(proj_view, names, tx, numbers, center, radius_pad=14):
    """Place a balloon for each part around the view, leader to a visible point of that part."""
    items = []
    for n, r in zip(names, proj_view):
        if n not in numbers or not r["visible"]:
            continue
        pts = [tx(*p) for pl in r["visible"] for p in pl]
        mx = sum(p[0] for p in pts) / len(pts)
        my = sum(p[1] for p in pts) / len(pts)
        anchor = min(pts, key=lambda p: (p[0] - mx) ** 2 + (p[1] - my) ** 2)
        items.append((numbers[n], anchor))
    out = []
    if not items:
        return ""
    xs = [a[0] for _, a in items]
    ys = [a[1] for _, a in items]
    cx, cyy = center
    rx = (max(xs) - min(xs)) / 2 + radius_pad
    ry = (max(ys) - min(ys)) / 2 + radius_pad
    items.sort(key=lambda t: atan2(t[1][1] - cyy, t[1][0] - cx))
    used = []
    for num, (ax, ay) in items:
        ang = atan2(ay - cyy, ax - cx)
        bx, byy = cx + rx * cos(ang), cyy + ry * sin(ang)
        for ux, uy in used:
            if abs(ux - bx) < 9 and abs(uy - byy) < 9:
                byy += 9 if byy >= uy else -9
        used.append((bx, byy))
        out.append(d.balloon(bx, byy, ax, ay, str(num)))
    return "".join(out)


def _parts_list(rows, x=230, y=None, widths=None):
    widths = widths or [9, 48, 72, 11, 20]
    h = 4.6 * (len(rows) + 1)
    y = 251 - h - 3 if y is None else y
    svg, _ = d.table(x, y, ["ITEM", "PART", "DESCRIPTION", "QTY", "TYPE"], rows, widths, size=2.4, row_h=4.6)
    return svg


def _hw_desc(n):
    table = {"motor": "stepper motor (see BOM)", "motor_pulley": "GT2 20T pulley, 5 mm bore", "belt": "GT2 6 mm closed belt",
             "as5600": "AS5600 board + magnet", "tube": "aluminium square tube", "race_balls": "Ø6 steel balls",
             "roll_motor": "pancake stepper (J5)", "roll_bearing": "6804 bearing", "gripper_motor": "28BYJ-48",
             "gripper_rods": "Ø6 steel rod x2", "lm6uu": "LM6UU bushing x4", "home_switch": "micro switch",
             "webcam": "webcam", "pole_tube": "20x20 tube (pole)", "boom_tube": "20x20 tube (boom)",
             "computer": "Raspberry Pi 4", "esp32_board": "ESP32 + driver perfboard", "buck": "24 V -> 5 V buck",
             "oled": "OLED 1.3\""}
    for k, v in table.items():
        if n.endswith(k) or n == k:
            return v
    return ""


def assembly_sheet(no, total, title, part_no, parts_printed, parts_hw, views, box, balloon_view, hidden=False,
                   extra=""):
    parts = {**parts_printed, **parts_hw}
    styles = {n: {"c": "#555", "w": d.THIN} for n in parts_hw}
    ortho = [v for v in views if v != "iso"]
    svg, (s, lab), txs, proj, names = _assembly_views(parts, ortho, {k: box[k] for k in ortho}, hidden=hidden, styles=styles)
    svg_i, _, txs_i, proj_i, _ = _assembly_views(parts, ["iso"], {"iso": box["iso"]}, styles=styles)
    svg += svg_i
    txs.update(txs_i)
    proj.update(proj_i)
    numbers, rows = {}, []
    for i, n in enumerate(list(parts_printed) + list(parts_hw), 1):
        numbers[n] = i
        kind = "printed" if n in parts_printed else "bought"
        desc = "printed PETG" if kind == "printed" else _hw_desc(n)
        rows.append([str(i), n.replace("_", " "), desc, "1", kind])
    bx = box[balloon_view]
    tx, _ = txs[balloon_view]
    pv = proj[balloon_view]
    body = [svg, _balloons(pv, names, tx, numbers, (bx[0] + bx[2] / 2, bx[1] + bx[3] / 2)), extra]
    for k in views:
        bx2 = box[k]
        body.append(d.text(bx2[0] + bx2[2] / 2, bx2[1] + bx2[3] + 4,
                           "ISOMETRIC (NOT TO SCALE)" if k == "iso" else k.upper(), size=3, weight="bold"))
    body.append(_parts_list(rows[:40], x=SHEET_PL_X, y=12.0))
    return d.svg_doc(d.frame(no, total, title, "Assembly", part_no, lab) + "".join(body))


SHEET_PL_X = 228.0


# ------------------------------------------------------------------ drive section sheet
def _hatch_defs():
    return ('<defs><pattern id="hatch" width="2.2" height="2.2" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
            '<line x1="0" y1="0" x2="0" y2="2.2" stroke="#111" stroke-width="0.25"/></pattern>'
            '<pattern id="hatch2" width="2.2" height="2.2" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)">'
            '<line x1="0" y1="0" x2="0" y2="2.2" stroke="#111" stroke-width="0.25"/></pattern></defs>')


def drive_sheet(no, total, label, D, part_no):
    parts = cy.build(D)
    flat = {n: w for g in parts.values() for n, w in g.items()}
    rp, op = cy.steel_pins(D)
    flat["ring_pins"], flat["output_pins"] = rp, op
    # section A-A: keep y >= 0, view from -y
    keep = cq.Workplane("XY").box(400, 200, 400).translate((0, 100, 0))
    halves = {}
    for n, w in flat.items():
        h = w.intersect(keep)
        if h.vals():
            halves[n] = h
    names = list(halves)
    sec = d.project([halves[n] for n in names], "front", with_hidden=False)
    b = d.bounds([pl for r in sec for pl in r["visible"]])
    s = 2.0 if D.housing_od < 90 and (b[3] - b[1]) * 2 < 200 else 1.5
    lab = {2.0: "2:1", 1.5: "3:2"}[s]
    cx, cyy = 120.0, 140.0
    tx = lambda u, v: (cx + (u - (b[0] + b[2]) / 2) * s, cyy - (v - (b[1] + b[3]) / 2) * s)
    body = [_hatch_defs()]
    # hatched cut faces
    for i, n in enumerate(names):
        for f in [ff for s_ in halves[n].vals() for ff in s_.Faces()]:
            if f.geomType() != "PLANE":
                continue
            c = f.Center()
            try:
                nrm = f.normalAt()
            except Exception:
                continue
            if abs(c.y) > 0.02 or abs(abs(nrm.y) - 1) > 1e-3:
                continue
            paths = []
            for wire in [f.outerWire()] + f.innerWires():
                pts = []
                for e in wire.Edges():
                    m = 2 if e.geomType() == "LINE" else 12
                    pts += [e.positionAt(k / (m - 1)) for k in range(m)]
                if pts:
                    paths.append("M" + " L".join(f"{tx(p.x, p.z)[0]:.2f} {tx(p.x, p.z)[1]:.2f}" for p in pts) + " Z")
            pat = "hatch" if i % 2 == 0 else "hatch2"
            if "pin" in n:
                body.append(f'<path d="{" ".join(paths)}" fill="#bbb" fill-rule="evenodd" stroke="none"/>')
            else:
                body.append(f'<path d="{" ".join(paths)}" fill="url(#{pat})" fill-rule="evenodd" stroke="none"/>')
    for n, r in zip(names, sec):
        body.append(d.polyline_svg(r["visible"], tx, width=d.MED))
    body.append(d.text(cx, 248, f"SECTION A-A ({lab})", size=3.6, weight="bold"))
    # axial view with section line
    ax = d.project([flat[n] for n in ("back_cover", "housing_ring", "cycloid_disc_a")], "top", with_hidden=False)
    bb2 = d.bounds([pl for r in ax for pl in r["visible"]])
    s2 = min(1.0, 80 / (bb2[2] - bb2[0]))
    cx2, cy2 = 330.0, 128.0
    tx2 = lambda u, v: (cx2 + (u - (bb2[0] + bb2[2]) / 2) * s2, cy2 - (v - (bb2[1] + bb2[3]) / 2) * s2)
    for r in ax:
        body.append(d.polyline_svg(r["visible"], tx2, width=d.THIN))
    r_ = (bb2[2] - bb2[0]) / 2 * s2 + 8
    body.append(d.line(cx2 - r_, cy2, cx2 + r_, cy2, w=0.5, dash="6 1.5 1 1.5"))
    for sgn in (-1, 1):
        body.append(d.text(cx2 + sgn * (r_ + 4), cy2 - 2, "A", size=4, weight="bold"))
        body.append(d.arrow_head(cx2 + sgn * r_, cy2 - 3.5, -pi / 2, size=2.6))
        body.append(d.line(cx2 + sgn * r_, cy2, cx2 + sgn * r_, cy2 - 3.5, w=0.5))
    body.append(d.text(cx2, cy2 + (bb2[3] - bb2[1]) * s2 / 2 + 8, "VIEW ON THE COVER (DISC SHOWN)", size=3, weight="bold"))
    # balloons on the section
    numbers = {n: i + 1 for i, n in enumerate(names)}
    body.append(_balloons(sec, names, tx, numbers, (cx, cyy), radius_pad=26))
    # key dimensions on the section
    body.append(d.dim_linear(*tx(-D.housing_od / 2, b[3]), *tx(D.housing_od / 2, b[3]), 8, f"Ø{D.housing_od:g}"))
    body.append(d.dim_linear(*tx(b[2], b[1]), *tx(b[2], b[3]), -24, f"{b[3] - b[1]:.1f}"))
    rows = []
    descr = {"back_cover": f"journal bearing {D.journal_brg}", "housing_ring": f"{D.n_ring_pins} ring pin pockets",
             "output_cap": f"output bearing {D.out_brg} seat", "cycloid_disc_a": f"{D.ratio} lobes, e = {D.ecc}",
             "cycloid_disc_b": "as A, 180° phase", "input_shaft": f"2 eccentrics + {D.cam_brg} x2",
             "input_pulley": f"GT2 {D.pulley_teeth}T", "output_flange": "pin carrier + sensor rod",
             "output_clamp": "clamps output bearing", "magnet_cap": "6 x 2.5 magnet",
             "ring_pins": f"Ø{D.ring_pin_d:g} x {D.ring_pin_len:g} dowel x{D.n_ring_pins}",
             "output_pins": f"Ø{D.out_pin_d:g} x {D.out_pin_len:g} dowel x{D.out_pins}"}
    for n in names:
        rows.append([str(numbers[n]), n.replace("_", " "), descr.get(n, ""), "1" if "pins" not in n else
                     str(D.n_ring_pins if n == "ring_pins" else D.out_pins), "bought" if "pins" in n else "printed"])
    body.append(_parts_list(rows, x=SHEET_PL_X, y=12.0))
    keyrows = [["Ratio", f"{D.ratio}:1 (x2 belt = {D.ratio * D.pulley_teeth // 20}:1)"], ["Pin circle", f"Ø{2 * D.pin_circle_r:g}"],
               ["Eccentricity", f"{D.ecc} mm"], ["Disc thickness", f"2 x {D.disc_t:g}"],
               ["Bearings", f"{D.cam_brg} x2, {D.journal_brg} x2, {D.out_brg}"], ["Stack bolts", f"{D.bolt_n} x M3 on Ø{2 * D.bolt_r:g}"]]
    kt, _ = d.table(SHEET_PL_X + 60, 190, ["KEY DATA", ""], keyrows, [40, 78], size=2.5)
    body.append(kt)
    return d.svg_doc(d.frame(no, total, f"CYCLOIDAL DRIVE {label}", "Assembly, section", part_no, lab,
                             qty="3" if D.ratio == 20 else "1") + "".join(body))


# ------------------------------------------------------------------ general arrangement
GA_POSE = (0.0, 90.0, -90.0, -90.0, 0.0)


def ga_sheet(no, total):
    w = A.posed(GA_POSE, include=("printed", "hardware", "drive"))
    parts = {}
    for g, dct in w.items():
        comp = cq.Workplane("XY").add([s for v in dct.values() for s in v.vals()])
        parts[g] = comp
    board = cq.Workplane("XY").box(8 * C.square, 8 * C.square, C.board_top_z).translate(
        (0, C.base_to_board + 4 * C.square, C.board_top_z / 2))
    parts["board"] = board
    box = {"right": (22, 30, 150, 200), "front": (178, 30, 108, 200)}
    svg, (s, lab), txs, proj, names = _assembly_views(parts, list(box), box, scale=(0.2, "1:5"))
    ibox = {"iso": (292, 22, 116, 108)}
    svg_i, _, txs_i, proj_i, _ = _assembly_views(parts, ["iso"], ibox)
    svg += svg_i
    txs.update(txs_i)
    proj.update(proj_i)
    box.update(ibox)
    body = [svg]
    tx, b = txs["right"]
    # dimensions in the side view (view x = world Y, view y = world Z)
    sh = C.shoulder_z
    ey = C.L1 * 0  # elbow straight above the shoulder
    def P(y, z):
        return tx(y, z)
    body.append(d.dim_linear(*P(-120, 0), *P(-120, sh), 8, f"{sh:g}"))
    body.append(d.dim_linear(*P(-120, sh), *P(-120, sh + C.L1), 8, f"{C.L1:g}"))
    body.append(d.dim_linear(*P(0, sh + C.L1 + 60), *P(C.L2, sh + C.L1 + 60), -6, f"{C.L2:g}"))
    wz = sh + C.L1
    body.append(d.dim_linear(*P(C.L2 + 70, wz), *P(C.L2 + 70, wz - wrist.TOOL_LEN), -8, f"{wrist.TOOL_LEN:.1f}"))
    body.append(d.dim_linear(*P(0, 0), *P(C.base_to_board, 0), -14, f"{C.base_to_board:g}"))
    body.append(d.dim_linear(*P(C.base_to_board, 0), *P(C.base_to_board + 8 * C.square, 0), -14, f"{8 * C.square:g}"))
    body.append(d.dim_linear(*P(C.base_to_board + 8 * C.square + 25, C.board_top_z),
                             *P(C.base_to_board + 8 * C.square + 25, C.board_top_z + C.camera_h), -6, f"{C.camera_h:g} (LENS)"))
    body.append(d.text(22 + 75, 238, "J2 SHOULDER, J3 ELBOW, J4 WRIST PITCH (RED); J1 YAW ABOUT THE BASE AXIS, J5 ROLL ABOUT THE GRIPPER AXIS",
                       size=2.3))
    for name, (yy, zz) in (("J2", (0, sh)), ("J3", (0, sh + C.L1)), ("J4", (C.L2, sh + C.L1))):
        x_, y_ = P(yy, zz)
        body.append(f'<circle cx="{x_:.2f}" cy="{y_:.2f}" r="1.6" fill="none" stroke="#c00" stroke-width="0.35"/>')
        body.append(d.text(x_ + 4, y_ - 3, name, size=3, anchor="start", fill="#c00", weight="bold"))
    for k, title in (("right", "SIDE VIEW (FROM +X)"), ("front", "FRONT (FROM -Y)"), ("iso", "ISOMETRIC (NOT TO SCALE)")):
        bx = box[k]
        body.append(d.text(bx[0] + bx[2] / 2, bx[1] + bx[3] + 5, title, size=3, weight="bold"))
    # balloons on iso for sub-assemblies
    numbers = {"base": 1, "turret": 2, "upper": 3, "fore": 4, "tool": 5, "camera": 6, "board": 7}
    txi, _ = txs["iso"]
    bxi = box["iso"]
    body.append(_balloons(proj["iso"], names, txi, numbers, (bxi[0] + bxi[2] / 2, bxi[1] + bxi[3] / 2), radius_pad=10))
    rows = [["1", "base", "electronics box, J1 drive, ball race", "1", "sheet 4"],
            ["2", "turret", "turntable, tower, J2 drive + motor", "1", "sheet 5"],
            ["3", "upper arm", "tube, fittings, J3 drive + motor", "1", "sheet 6"],
            ["4", "forearm", "tube, fittings, J4 drive + motor", "1", "sheet 7"],
            ["5", "wrist + gripper", "J5 roll, parallel gripper", "1", "sheet 8"],
            ["6", "camera pole", "pole, boom, webcam plate", "1", "sheet 9"],
            ["7", "chessboard", "40 x 40, not supplied", "1", "-"]]
    body.append(_parts_list(rows, x=292, y=145, widths=[9, 24, 59, 9, 15]))
    notes = ("POSE SHOWN: J1 0°, J2 90°, J3 -90°, J4 -90° (UPPER ARM VERTICAL, FOREARM LEVEL).",)
    return d.svg_doc(d.frame(no, total, "CHESS ARM - GENERAL ARRANGEMENT", "Whole build", "GA-001", lab, notes=notes)
                     + "".join(body))


# ------------------------------------------------------------------ build all
def sub_sheets():
    """(title, part no, printed dict, hardware dict, views, boxes, balloon view)"""
    g = A.groups(0.0)
    bp, bh, bd = g["base"]
    tp, th, td = g["turret"]
    up, uh, ud = g["upper"]
    fp, fh, fd = g["fore"]
    wp, wh = wrist.build_wrist(0.0)
    cp, ch, _ = g["camera"]
    std = {"top": (15, 20, 105, 112), "left": (122, 20, 105, 112), "front": (15, 145, 105, 96), "right": (122, 145, 105, 96),
           "iso": (235, 138, 170, 104)}
    wide = {"top": (15, 25, 210, 100), "front": (15, 150, 210, 88), "iso": (235, 138, 170, 104)}
    tall = {"right": (15, 25, 100, 215), "front": (120, 25, 100, 215), "iso": (235, 138, 170, 104)}
    keep_drive = lambda dd: {k: v for k, v in dd.items() if k.endswith(("back_cover", "housing_ring", "output_cap",
                                                                      "output_clamp", "input_pulley"))}
    return [
        ("BASE", "SA-001", {**bp, **keep_drive(bd)}, bh, list(std), std, "iso"),
        ("TURRET (TURNTABLE, TOWER, J2)", "SA-002", {**tp, **keep_drive(td)}, th, list(std), std, "iso"),
        ("UPPER ARM", "SA-003", {**up, **keep_drive(ud)}, uh, list(wide), wide, "top"),
        ("FOREARM", "SA-004", {**fp, **keep_drive(fd)}, fh, list(wide), wide, "top"),
        ("WRIST + GRIPPER", "SA-005", wp, wh, list(std), std, "iso"),
        ("CAMERA POLE", "SA-006", cp, ch, list(tall), tall, "iso"),
    ]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    only = sys.argv[1] if len(sys.argv) > 1 else None
    parts = unique_printed_parts()
    subs = sub_sheets()
    total = 1 + 2 + len(subs) + len(parts)
    sheets = []
    n = 1
    sheets.append(("01_general_arrangement", lambda n=n: ga_sheet(n, total)))
    n += 1
    sheets.append(("02_drive_20to1", lambda n=n: drive_sheet(n, total, "J1-J3 (20:1)", D2, "SA-010")))
    n += 1
    sheets.append(("03_drive_15to1", lambda n=n: drive_sheet(n, total, "J4 (15:1)", D4, "SA-011")))
    n += 1
    for title, pno, pr, hw, views, box, bv in subs:
        sheets.append((f"{n:02d}_{pno}", (lambda n=n, title=title, pno=pno, pr=pr, hw=hw, views=views, box=box, bv=bv:
                                          assembly_sheet(n, total, title, pno, pr, hw, views, box, bv))))
        n += 1
    index = []
    for name, w, q in parts:
        safe = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")
        sheets.append((f"{n:02d}_P{n:03d}_{safe}", (lambda n=n, name=name, w=w, q=q: part_sheet(n, total, name, w, q))))
        index.append((n, name, q))
        n += 1
    for fname, fn in sheets:
        if only and only not in fname:
            continue
        (OUT / f"{fname}.svg").write_text(fn())
        print("wrote", fname)
    (OUT / "index.json").write_text(json.dumps({"sheets": [f for f, _ in sheets], "parts": index}))


def make_pdf():
    import subprocess
    files = sorted(str(p) for p in OUT.glob("*.svg"))
    tool = Path(__file__).resolve().parent.parent / "tools" / "svg2pdf.js"
    subprocess.run(["node", str(tool), str(OUT / "chess_arm_drawings.pdf"), "420", "297", *files], check=True)


if __name__ == "__main__":
    main()
    if len(sys.argv) == 1:
        make_pdf()
