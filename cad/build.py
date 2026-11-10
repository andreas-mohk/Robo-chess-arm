"""Build the whole arm, check it, export it.

  python3 build.py            checks + STL/STEP per printed part + assembly STEP + GLB groups + report
  python3 build.py --quick    skip the collision sweep and the cycloid meshing check
  python3 build.py --no-export

Writes everything to cad/out/. Exit code 1 if a check fails.
"""
import json
import sys
from math import ceil, cos, pi, radians, sin
from pathlib import Path

import cadquery as cq

import assembly as A
import base
import bom as bom_mod
import camera
import kinematics as K
import links
import wrist
from config import CFG
from cycloidal import interference_report
from hardware import (AL_TUBE, AS5600, BEARINGS, COMPUTERS, LM6UU, WEBCAMS, DOWEL_PRICE, GEARED, MOTOR_PULLEY, MOTORS, STEEL_BALL_PRICE,
                      STEEL_DENSITY)
from layout import D1, D2, D3, D4, summary

C = CFG
OUT = Path(__file__).parent / "out"
G = 9.81
QUICK = "--quick" in sys.argv
EXPORT = "--no-export" not in sys.argv
problems, notes = [], []


def log(s=""):
    print(s)
    REPORT.append(s)


REPORT = []


# ------------------------------------------------------------------ collisions
def _bb(s):
    return s.BoundingBox()


def _overlap(b1, b2, tol=0.0):
    return (b1.xmin < b2.xmax - tol and b2.xmin < b1.xmax - tol and b1.ymin < b2.ymax - tol and
            b2.ymin < b1.ymax - tol and b1.zmin < b2.zmax - tol and b2.zmin < b1.zmax - tol)


def clashes(ga, gb, min_vol=1.0):
    """[(part_a, part_b, volume)] for solids that overlap by more than min_vol mm^3."""
    out = []
    sa = [(n, s, _bb(s)) for n, w in ga.items() for s in w.vals()]
    sb = [(n, s, _bb(s)) for n, w in gb.items() for s in w.vals()]
    for na, a, ba in sa:
        for nb, b, bb in sb:
            if not _overlap(ba, bb, 0.05):
                continue
            try:
                v = a.intersect(b).Volume()
            except Exception:
                v = -1
            if v > min_vol or v < 0:
                out.append((na, nb, round(v, 1)))
    return out


def pieces_near(name):
    """Target piece (pawn-sized) plus worst-case tall pieces on the 8 neighbouring squares."""
    if name == "tray":
        return {}
    f, r = K.FILES.index(name[0]), int(name[1])
    out = {}
    z0 = C.board_top_z
    for df in (-1, 0, 1):
        for dr in (-1, 0, 1):
            ff, rr = f + df, r + dr
            if not (0 <= ff < 8 and 1 <= rr <= 8):
                continue
            n = K.FILES[ff] + str(rr)
            x, y = K.square_xy(n)
            rad, h = (12.0, 50.0) if (df, dr) == (0, 0) else (17.0, 95.0)
            out[f"piece_{n}"] = cq.Workplane("XY").workplane(offset=z0).center(x, y).circle(rad).extrude(h)
    return out


def table_and_board():
    t = cq.Workplane("XY").box(2000, 2000, 10).translate((0, 0, -5))
    b = cq.Workplane("XY").box(8 * C.square, 8 * C.square, C.board_top_z).translate(
        (0, C.base_to_board + 4 * C.square, C.board_top_z / 2))
    return {"table": t, "board": b}


def collision_sweep():
    poses = [("d8", False), ("d8", True), ("e8", False), ("a8", False), ("h8", False), ("a1", False), ("a1", True),
             ("h1", False), ("h1", True), ("e4", False), ("tray", False), ("tray", True)]
    names = ["base", "camera", "turret", "upper", "fore", "tool"]
    env = table_and_board()
    found = 0
    for name, carry in poses + [("park", None)]:
        if name == "park":
            j = K.PARK
        else:
            s = K.pose(name, carry)
            if not s["ok"]:
                continue
            j = s["j"]
        w = A.posed(j)
        hits = []
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                hits += [(a, b) + h for h in clashes(w[a], w[b])]
        for g in names[2:]:
            hits += [(g, "table/board") + h for h in clashes(w[g], env)]
        if name != "park" and not carry:
            for g in ("upper", "fore", "tool"):
                hits += [(g, "pieces") + h for h in clashes(w[g], pieces_near(name))]
        label = f"{name}{' carry' if carry else ''}"
        if hits:
            found += 1
            log(f"  CLASH at {label}: " + "; ".join(f"{h[2]} x {h[3]} ({h[4]} mm3)" for h in hits[:6]))
        else:
            log(f"  {label}: clear")
    # parked, the arm must stay out of the camera's view of the board
    w = A.posed(K.PARK)
    view = {"camera_view": camera.view_frustum()}
    seen = [h for g in ("turret", "upper", "fore", "tool") for h in clashes(w[g], view)]
    if seen:
        found += 1
        log("  IN VIEW when parked: " + ", ".join(sorted({h[0] for h in seen})))
    else:
        log("  parked arm is out of the camera's view of the board")
    # inside the base: electronics, J1 motor, shelf, sensor bridge, floor must not overlap
    bp, bh, bd = A.groups()["base"]
    inside = {k: v for k, v in {**bh, **bp}.items() if k in ("computer", "esp32_board", "buck", "oled", "J1_motor",
                                                           "j1_motor_shelf", "J1_sensor_bridge", "base_floor")}
    names_in = list(inside)
    hits = []
    for i, a in enumerate(names_in):
        for b in names_in[i + 1:]:
            if {a, b} in ({"J1_motor", "j1_motor_shelf"},):
                continue
            hits += clashes({a: inside[a]}, {b: inside[b]})
    if hits:
        found += 1
        log("  CLASH inside the base: " + "; ".join(f"{h[0]} x {h[1]} ({h[2]} mm3)" for h in hits))
    else:
        log("  inside the base: clear")
    if found:
        problems.append(f"collisions in {found} pose(s)")


# ------------------------------------------------------------------ masses and torques
def _printed_mass(w):
    return sum(s.Volume() for s in w.vals()) * C.print_density * C.infill_factor


def _hw_mass(name, w):
    n = name
    for j, jc in C.joints.items():
        if n == f"{j}_motor":
            return MOTORS[jc.motor].mass
        if n == f"{j}_motor_pulley":
            return MOTOR_PULLEY["mass"]
        if n == f"{j}_belt":
            return 0.007
        if n == f"{j}_as5600":
            return 0.003
    if n.endswith("_tube"):
        return AL_TUBE[C.tube]["kg_per_m"] * (C.L1 - 2 * links.TUBE_START) / 1000
    if n == "roll_motor":
        return MOTORS[C.roll_motor].mass
    if n == "gripper_motor":
        return GEARED[C.gripper_motor].mass
    if n == "lm6uu":
        return 4 * LM6UU["mass"]
    if n == "roll_bearing":
        return BEARINGS["6804"].mass
    if n == "home_switch":
        return 0.002
    if n in ("gripper_rods",):
        return sum(s.Volume() for s in w.vals()) * STEEL_DENSITY
    if n == "race_balls":
        return len(w.vals()) * 0.00088
    return {"computer": 0.05, "esp32_board": 0.10, "buck": 0.03, "oled": 0.01}.get(n, 0.0)


def _drive_steel(D):
    pins = (D.n_ring_pins * pi * (D.ring_pin_d / 2) ** 2 * D.ring_pin_len +
            D.out_pins * pi * (D.out_pin_d / 2) ** 2 * D.out_pin_len) * STEEL_DENSITY
    brg = 2 * BEARINGS[D.cam_brg].mass + 2 * BEARINGS[D.journal_brg].mass + BEARINGS[D.out_brg].mass
    return pins + brg


def group_mass_props(group):
    """(mass, centre of mass) of a group in its own frame. Drive steel is added at the drive centroid."""
    p, h, d = group
    items = []
    for w in p.values():
        items.append((_printed_mass(w), w.val().Center() if len(w.vals()) == 1 else cq.Compound.makeCompound(w.vals()).Center()))
    for n, w in h.items():
        items.append((_hw_mass(n, w), cq.Compound.makeCompound(w.vals()).Center()))
    for n, w in d.items():
        items.append((_printed_mass(w), cq.Compound.makeCompound(w.vals()).Center()))
    m = sum(i[0] for i in items)
    c = [sum(i[0] * getattr(i[1], ax) for i in items) / m for ax in "xyz"]
    return m, c


def torque_check():
    g = A.groups(0.0)
    props = {k: group_mass_props(v) for k, v in g.items() if k in ("upper", "fore", "tool")}
    # drive steel: J3 static on upper, J4 static on fore, J2 output on upper (small), J4 output on tool
    m3s, m4s = _drive_steel(D3), _drive_steel(D4)
    for k, extra, at in (("upper", m3s, (0, C.L1, 0)), ("fore", m4s, (0, C.L2, 0))):
        m, c = props[k]
        props[k] = (m + extra, [(m * c[i] + extra * at[i]) / (m + extra) for i in range(3)])
    payload = 0.03
    log(f"  link masses: upper {props['upper'][0]:.2f} kg, forearm {props['fore'][0]:.2f} kg, "
        f"wrist+gripper {props['tool'][0]:.2f} kg, payload {payload * 1000:.0f} g")
    worst = {"J2": 0, "J3": 0, "J4": 0}
    targets = [(n, c) for n, c in K.all_targets()]
    for n, carry in targets:
        s = K.pose(n, carry)
        if not s["ok"]:
            continue
        j1, j2, j3, j4, _ = s["j"]
        a2, a3, a4 = radians(j2), radians(j2 + j3), radians(j2 + j3 + j4 + 90)

        def y_of(frame, p):          # horizontal in-plane distance from the shoulder, arm frame
            if frame == "upper":
                return p[1] * cos(a2) - p[2] * sin(a2)
            ey = C.L1 * cos(a2)
            if frame == "fore":
                return ey + p[1] * cos(a3) - p[2] * sin(a3)
            wy = ey + C.L2 * cos(a3)
            return wy + p[1] * cos(a4) - p[2] * sin(a4)
        ey, wy = C.L1 * cos(a2), C.L1 * cos(a2) + C.L2 * cos(a3)
        tip = y_of("tool", (0, 0, wrist.Z_GRIP_TOP + wrist.Z_TIP))
        loads = [(props[k][0], y_of(k, props[k][1])) for k in ("upper", "fore", "tool")] + [(payload, tip)]
        t2 = G * sum(m * y for m, y in loads) / 1000          # mm -> m
        t3 = G * sum(m * (y - ey) for m, y in loads[1:]) / 1000
        t4 = G * sum(m * (y - wy) for m, y in loads[2:]) / 1000
        for k, v in (("J2", t2), ("J3", t3), ("J4", t4)):
            worst[k] = max(worst[k], abs(v))
    log("  joint   gravity(worst)  x1.3 accel   capacity   margin")
    for k in ("J2", "J3", "J4"):
        jc = C.joints[k]
        cap = MOTORS[jc.motor].torque * jc.derate * jc.total_ratio * jc.efficiency
        need = worst[k] * 1.3
        margin = cap / need if need else float("inf")
        flag = "" if margin >= 1.5 else ("  <- low" if margin >= 1.0 else "  <- TOO WEAK")
        log(f"  {k}     {worst[k]:6.2f} Nm       {need:6.2f} Nm   {cap:6.2f} Nm   {margin:4.1f}x{flag}")
        if margin < 1.0:
            problems.append(f"{k} motor too weak ({margin:.2f}x)")
        elif margin < 1.5:
            notes.append(f"{k} torque margin only {margin:.2f}x")
    jc = C.joints["J1"]
    cap1 = MOTORS[jc.motor].torque * jc.derate * jc.total_ratio * jc.efficiency
    log(f"  J1 capacity {cap1:.2f} Nm (no gravity load; enough for ~{cap1 / 0.15:.0f} rad/s^2 on a ~0.15 kg m^2 arm)")


# ------------------------------------------------------------------ print bed
def all_printed():
    g = A.groups(0.0)
    out = {}
    for name, (p, h, d) in g.items():
        out.update(p)
        out.update(d)
    gp, _ = wrist.build_gripper()
    return out


def bed_check(parts):
    bed = sorted(C.bed)
    too_big = []
    for n, w in parts.items():
        bb = cq.Compound.makeCompound(w.vals()).BoundingBox()
        dims = sorted([bb.xlen, bb.ylen, bb.zlen])
        if any(d > b for d, b in zip(dims, bed)):
            too_big.append((n, [round(x) for x in dims]))
    if too_big:
        problems.append("parts larger than the print bed: " + ", ".join(f"{n} {d}" for n, d in too_big))
    log(f"  {len(parts)} printed parts, all fit {C.bed} mm" if not too_big else f"  too big: {too_big}")


# ------------------------------------------------------------------ BOM
# ------------------------------------------------------------------ exports
COLORS = {"printed": (0.07, 0.45, 0.42), "drive": (0.80, 0.55, 0.15), "hardware": (0.35, 0.37, 0.40)}


def export_glb(name, parts_by_kind):
    asm = cq.Assembly(name=name)
    for kind, dct in parts_by_kind.items():
        col = cq.Color(*COLORS[kind])
        for n, w in dct.items():
            shapes = [s for s in w.vals() if isinstance(s, (cq.Solid, cq.Compound, cq.Shell))]
            if shapes:
                asm.add(cq.Compound.makeCompound(shapes), name=n, color=col)
    asm.export(str(OUT / "glb" / f"{name}.glb"), tolerance=0.3, angularTolerance=0.5)


def export_viewer():
    """GLB per group in its own frame + poses, for docs/arm3d.html. Also writes base64 copies (.b64.txt),
    because the artifact host does not serve .glb files."""
    import base64
    (OUT / "glb").mkdir(parents=True, exist_ok=True)
    g = A.groups(0.0)
    for gname in ("base", "camera", "turret", "upper", "fore"):
        p, h, d = g[gname]
        export_glb(gname, {"printed": p, "hardware": h, "drive": d})
    tool_fixed = {"wrist_bracket": wrist.wrist_bracket()}
    export_glb("tool", {"printed": tool_fixed, "hardware": {"roll_motor": wrist.roll_motor(), "roll_bearing": wrist.roll_bearing()},
                        "drive": links.j4_output_in_tool()})
    gp, gh = wrist.build_gripper()
    hub = wrist.roll_hub().translate((-wrist.X_G, 0, -wrist.Z_GRIP_TOP))
    export_glb("gripper", {"printed": {**gp, "roll_hub": hub}, "hardware": gh})
    # poses for the viewer
    poses = {}
    for n, carry in K.all_targets():
        s = K.pose(n, carry)
        if s["ok"]:
            poses[n + ("+" if carry else "")] = [round(v, 2) for v in s["j"]]
    poses["park"] = list(K.PARK)
    geom = {"yaw_x": C.yaw_x, "shoulder_z": C.shoulder_z, "L1": C.L1, "L2": C.L2,
            "x_g": wrist.X_G, "z_grip_top": wrist.Z_GRIP_TOP, "square": C.square,
            "base_to_board": C.base_to_board, "board_top_z": C.board_top_z}
    (OUT / "glb" / "poses.json").write_text(json.dumps({"geom": geom, "poses": poses}))
    for f in (OUT / "glb").glob("*.glb"):
        (OUT / "glb" / (f.stem + ".b64.txt")).write_text(base64.b64encode(f.read_bytes()).decode())


def exports():
    (OUT / "stl").mkdir(parents=True, exist_ok=True)
    (OUT / "step").mkdir(parents=True, exist_ok=True)
    (OUT / "glb").mkdir(parents=True, exist_ok=True)
    parts = all_printed()
    gp, _ = wrist.build_gripper()
    parts.update({k: v for k, v in gp.items()})          # gripper parts in their own frame
    for n, w in parts.items():
        cq.exporters.export(w, str(OUT / "stl" / f"{n}.stl"), tolerance=0.02, angularTolerance=0.1)
        cq.exporters.export(w, str(OUT / "step" / f"{n}.step"))
    # assembly at a reference pose
    s = K.pose("e4", True)
    posed = A.posed(s["j"])
    asm = cq.Assembly(name="chess_arm_e4")
    for gname, dct in posed.items():
        for n, w in dct.items():
            asm.add(cq.Compound.makeCompound(w.vals()), name=n)
    asm.export(str(OUT / "chess_arm_assembly.step"))
    export_viewer()
    log(f"  exported {len(parts)} printed parts (STL + STEP), assembly STEP, 7 GLB groups -> {OUT}")


# ------------------------------------------------------------------ main
def main():
    OUT.mkdir(exist_ok=True)
    log("# Chess arm build report\n")
    log("## Layout")
    for k, v in summary().items():
        log(f"  {k}: {v}")
    log(f"  tool length {wrist.TOOL_LEN:.1f} mm (target {C.tool_len_target}), lateral offset {K.OFFSET:.1f} mm, "
        f"J3 motor tail {links.TAIL3:.1f} mm, J4 motor tail {links.TAIL4:.1f} mm")
    if abs(wrist.TOOL_LEN - C.tool_len_target) > 5:
        notes.append(f"tool length {wrist.TOOL_LEN:.0f} differs from target {C.tool_len_target:.0f}")
    log("\n## Belts")
    for k in (base.K1, links.K2, links.K3, links.K4):
        log("  " + k.report())
    log("\n## Reach")
    lo, hi, worst, bad = K.joint_ranges()
    for i in range(5):
        log(f"  J{i + 1}: {lo[i]:+.0f} .. {hi[i]:+.0f} deg")
    log(f"  max extension {100 * worst['ext']:.0f}%, tightest elbow fold {worst['fold']:.0f} deg")
    if bad:
        problems.append(f"unreachable targets: {bad}")
    for n in ("a1", "h8", "tray"):
        s = K.pose(n, True)
        tip = A.fingertip_world(s["j"])
        X, Y = K.target_xy(n)
        err = abs(tip[0] - X) + abs(tip[1] - Y)
        if err > 0.1:
            problems.append(f"IK and assembly disagree at {n} by {err:.2f} mm")
    log("  IK verified against the assembled model")
    if not QUICK:
        log("\n## Cycloid meshing (6 input angles per drive)")
        for j, D in (("J1", D1), ("J2", D2), ("J3", D3), ("J4", D4)):
            w, pairs = interference_report(D)
            log(f"  {j}: worst disc/pin overlap {w:.4f} mm3, part overlaps {pairs or 'none'}")
            if w > 0.05 or pairs:
                problems.append(f"{j} drive interference")
    if not QUICK:
        log("\n## Gripper internals (jaws, racks, frame, switch over the opening range)")
        ic = wrist.internal_clashes()
        if ic:
            problems.append("gripper internal clashes")
            log("  CLASH: " + "; ".join(f"opening {o:g}: {a} x {b} ({v} mm3)" for o, a, b, v in ic))
        else:
            log("  clear at 10 mm, half and full opening")
    log("\n## Camera")
    fits, nx, ny, cov = camera.fov_report()
    log(f"  {C.webcam} at {C.camera_h:.0f} mm needs {nx:.1f} x {ny:.1f} deg, has {WEBCAMS[C.webcam]['hfov']} x "
        f"{WEBCAMS[C.webcam]['vfov']} deg: {'board fits' if fits else 'BOARD DOES NOT FIT'} "
        f"(covers {cov[0]:.0f} x {cov[1]:.0f} mm at the board)")
    if not fits:
        problems.append("camera field of view too small for the board; raise camera_h")
    log("\n## Torque (gravity over every target pose, gripper vertical)")
    torque_check()
    log("\n## Print bed")
    bed_check(all_printed())
    if not QUICK:
        log("\n## Collision sweep (arm groups, table, board, neighbouring pieces)")
        collision_sweep()
    rows = bom_mod.rows()
    total = bom_mod.total(rows)
    log(f"\n## Cost\n  estimated total EUR {total:.0f} incl. spares and packs (budget EUR 300), see out/bom_sourcing.csv")
    if total > 300:
        notes.append(f"estimated cost EUR {total:.0f} is over the EUR 300 budget")
    if EXPORT:
        log("\n## Export")
        bom_mod.write(rows)
        exports()
    log("\n## Result")
    log("  problems: " + ("; ".join(problems) if problems else "none"))
    log("  notes: " + ("; ".join(notes) if notes else "none"))
    (OUT / "report.md").write_text("\n".join(REPORT) + "\n")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
