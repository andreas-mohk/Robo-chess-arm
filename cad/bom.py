"""Sourcing bill of materials: every bought part, totalled across the whole arm.

Quantities and sizes come from the same parameters as the CAD, so the list follows any
change in config.py / hardware.py. Prices are rough 2026 estimates (EUR, typical online
marketplace, shipping excluded) for budgeting, not quotes.

  python3 bom.py        writes out/bom_sourcing.csv and out/bom_sourcing.md
"""
import csv
from collections import OrderedDict
from math import ceil
from pathlib import Path

import base
import camera
import links
import wrist
from config import CFG
from hardware import (AL_TUBE, AS5600, BEARINGS, COMPUTERS, GEARED, LM6UU, MICROSWITCH, MOTORS, OLED, WEBCAMS,
                      std_len)
from layout import D1, D2, D3, D4

C = CFG
OUT = Path(__file__).parent / "out"
KITS = (base.K1, links.K2, links.K3, links.K4)
DRIVES = (("J1", D1), ("J2", D2), ("J3", D3), ("J4", D4))
COLS = ["Category", "Part", "Specification", "Qty needed", "Buy", "Est. EUR", "Used for", "Search for", "Notes"]


class Bom:
    def __init__(self):
        self.rows = OrderedDict()

    def add(self, cat, part, spec, qty, used, buy=None, eur=0.0, search="", notes=""):
        """Lines with the same part + spec merge: quantities add, uses are listed."""
        key = (cat, part, spec)
        if key in self.rows:
            r = self.rows[key]
            r["qty"] += qty
            if used not in r["used"]:
                r["used"].append(used)
            r["eur_each"] = r["eur_each"] or eur
        else:
            self.rows[key] = {"cat": cat, "part": part, "spec": spec, "qty": qty, "used": [used], "buy": buy,
                              "eur_each": eur, "search": search, "notes": notes}

    def finalize(self, pack_rules):
        out = []
        for r in self.rows.values():
            rule = pack_rules.get((r["cat"], r["part"]))
            if rule:
                buy, eur = rule(r["qty"], r["spec"])
            else:
                buy = r["buy"] or str(r["qty"])
                eur = r["eur_each"] * (int(buy) if str(buy).isdigit() else r["qty"])
            out.append([r["cat"], r["part"], r["spec"], r["qty"], buy, round(eur, 2), "; ".join(r["used"]),
                        r["search"], r["notes"]])
        return out


def _packs(size, price_per_pack, spare=0.1):
    def rule(q, spec):
        n = ceil(q * (1 + spare) / size)
        return f"{n} x {size}-pack", n * price_per_pack
    return rule


def collect():
    b = Bom()
    # ---------------- motors and motion
    for j, k in zip(("J1", "J2", "J3", "J4"), KITS):
        m = MOTORS[k.motor_key]
        b.add("Motors", f"Stepper {m.name}", f"{k.motor_key}, 5 mm D-shaft, 4-wire bipolar", 1, j, eur=m.price,
              search=f"{k.motor_key} stepper motor", notes="any bipolar NEMA 17 of the same length and torque")
    rm = MOTORS[C.roll_motor]
    b.add("Motors", f"Stepper {rm.name}", f"{C.roll_motor}, 5 mm D-shaft, 4-wire bipolar", 1, "J5 wrist roll", eur=rm.price,
          search=f"{C.roll_motor} pancake stepper")
    gm = GEARED[C.gripper_motor]
    b.add("Motors", gm.name, "5 V version", 1, "J6 gripper", eur=gm.price, search="28BYJ-48 5V",
          notes="cut the middle trace on the PCB to run it bipolar from a TMC2209; ULN2003 board not needed")
    for j, k in zip(("J1", "J2", "J3", "J4"), KITS):
        b.add("Motion", "GT2 closed-loop belt", f"6 mm wide, {k.loop} mm loop", 1, j, eur=1.5 if k.loop < 400 else 2.5,
              search=f"GT2 {k.loop} closed loop belt 6mm",
              notes="other lengths: add them to GT2_LOOPS in hardware.py and rebuild")
        b.add("Motion", "GT2 pulley 20T", "5 mm bore, 6 mm belt, with grub screws", 1, j, eur=1.0, search="GT2 20T pulley 5mm bore")
    for j, D in DRIVES:
        b.add("Motion", "Dowel pin (hardened)", f"Ø{D.ring_pin_d:g} x {D.ring_pin_len:g} mm", D.n_ring_pins, f"{j} ring pins")
        b.add("Motion", "Dowel pin (hardened)", f"Ø{D.out_pin_d:g} x {D.out_pin_len:g} mm", D.out_pins, f"{j} output pins")
        for name, n, use in ((D.cam_brg, 2, "eccentrics"), (D.journal_brg, 2, "input shaft"), (D.out_brg, 1, "output")):
            br = BEARINGS[name]
            b.add("Bearings", f"Bearing {name}", f"{br.d:g} x {br.D:g} x {br.B:g} mm, 2RS", n, f"{j} {use}", eur=br.price,
                  search=f"{name}-2RS bearing")
    rb = BEARINGS["6804"]
    b.add("Bearings", "Bearing 6804", f"{rb.d:g} x {rb.D:g} x {rb.B:g} mm, 2RS", 1, "J5 roll", eur=rb.price, search="6804-2RS bearing")
    b.add("Bearings", "Linear bushing LM6UU", f"{LM6UU['d']:g} x {LM6UU['D']:g} x {LM6UU['L']:g} mm", 4, "gripper jaws",
          eur=LM6UU["price"], search="LM6UU")
    b.add("Bearings", "Steel ball", f"Ø{C.ball_d:g} mm (bearing grade, or 6 mm airsoft BBs in a pinch)", base.balls()[1],
          "turntable race", search="6mm steel bearing balls")
    rod_len = 2 * (wrist.U_IN + wrist.WALL_T)
    b.add("Stock", "Smooth steel rod", f"Ø{wrist.ROD_D:g} mm, 2 x {rod_len:.0f} mm", 1, "gripper", buy="1 x 300 mm", eur=2.5,
          search="6mm linear shaft 300mm", notes="cut to length")
    t = AL_TUBE[C.tube]
    need = 2 * (C.L1 - 2 * links.TUBE_START)
    b.add("Stock", "Aluminium square tube", f"{C.tube} mm, 2 x {C.L1 - 2 * links.TUBE_START:.0f} mm", 1, "upper arm, forearm",
          buy="1 x 500 mm", eur=t["price_per_m"] * 0.5 + 1, search=f"aluminium square tube {C.tube}", notes=f"{need:.0f} mm needed")
    tp = AL_TUBE[C.pole_tube]
    pole, boom = camera.Z_POLE_TOP - camera.Z_POLE_BOT, camera.BOOM_X1 - camera.BOOM_X0
    b.add("Stock", "Aluminium square tube", f"{C.pole_tube} mm, {pole:.0f} + {boom:.0f} mm", 1, "camera pole + boom",
          buy="1 x 1000 mm", eur=tp["price_per_m"] + 1, search=f"aluminium square tube {C.pole_tube}",
          notes=f"{pole + boom:.0f} mm needed: measure before cutting")
    b.add("Stock", "Plywood baseplate", "about 700 x 650 x 12 mm", 1, "arm, board and camera pole on one plate",
          eur=12.0, notes="keeps the board registered to the arm; bolt the base and pole foot to it")

    # ---------------- sensors and electronics
    b.add("Electronics", "AS5600 magnetic encoder board", f"{AS5600['board_w']:g} x {AS5600['board_h']:g} mm, with "
          f"{AS5600['magnet_d']:g} x {AS5600['magnet_h']:g} mm diametric magnet", 4, "J1-J4 joint angle", eur=AS5600["price"],
          search="AS5600 magnetic encoder module",
          notes="check board size and hole pitch against hardware.py; the magnet must be DIAMETRICALLY magnetised")
    b.add("Electronics", "TCA9548A I2C multiplexer", "breakout board", 1, "4 x AS5600 share one address", eur=2.0, search="TCA9548A")
    cp = COMPUTERS[C.computer]
    b.add("Electronics", cp["name"], "", 1, "vision, Stockfish, game logic, OLED menu", eur=cp["price"])
    b.add("Electronics", "microSD card", "32 GB, A1 class", 1, "Pi OS Lite 64-bit", eur=6.0)
    b.add("Electronics", "Heatsink set for the Pi", "stick-on aluminium", 1, "Pi in a closed base", eur=2.0)
    b.add("Electronics", "ESP32 dev board", "ESP32-WROOM-32 DevKit (38-pin)", 1, "step generation", eur=6.0, search="ESP32 devkit v1")
    b.add("Electronics", "TMC2209 stepper driver", "StepStick format", 6, "J1-J5 + gripper", buy="7", eur=4.5,
          search="TMC2209 v1.3 stepstick", notes="one spare")
    b.add("Electronics", "Electrolytic capacitor", "100 µF 35 V", 6, "one per driver, across VM", buy="10", eur=0.1)
    b.add("Electronics", "Buck converter", "24 V in, 5 V 5 A out", 1, "powers the Pi", eur=6.0, search="24V to 5V 5A buck converter",
          notes="feed the Pi through its USB-C (short cable) or the 5 V GPIO pins")
    b.add("Electronics", "Power supply", "24 V 5 A (120 W) brick, 5.5 x 2.1 mm plug", 1, "everything", eur=20.0,
          notes="external brick: no mains wiring inside the printed base")
    b.add("Electronics", "Panel DC jack", "5.5 x 2.1 mm, panel mount", 1, "base rear", eur=0.8)
    b.add("Electronics", "Rocker switch", "KCD1, 6 A", 1, "main power", eur=0.5)
    b.add("Electronics", "Inline fuse holder + fuse", "5 x 20 mm, 5 A slow", 1, "24 V line", eur=1.5)
    o = OLED[C.oled]
    b.add("Electronics", "OLED display", {"SH1106_13": '1.3" SH1106', "SSD1306_096": '0.96" SSD1306'}.get(C.oled, C.oled) + " I2C, 4-pin", 1, "settings screen", eur=6.0,
          search="1.3 inch OLED SH1106 I2C", notes=f"window cut for {o['window_w']:g} x {o['window_h']:g} mm")
    b.add("Electronics", "Tactile switch + cap", "12 x 12 mm", C.buttons, "menu buttons", buy=str(C.buttons + 2), eur=0.3)
    b.add("Electronics", "Micro switch", f"SS-5GL style, {MICROSWITCH['w']:g} x {MICROSWITCH['d']:g} mm", 1, "gripper home",
          buy="2", eur=MICROSWITCH["price"])
    b.add("Electronics", "Perfboard", "90 x 70 mm, double-sided", 1, "ESP32 + driver carrier board", buy="2", eur=1.0)
    b.add("Electronics", "Female header strips", "2.54 mm, 40-pin", 1, "socketed drivers and ESP32", buy="6", eur=0.3)
    b.add("Electronics", "Stepper cable", "4-core, 22-24 AWG, flexible", 1, "motors in the arm", buy="6 m", eur=6.0)
    b.add("Electronics", "Signal cable", "4-core, 26-28 AWG, flexible", 1, "AS5600s, gripper switch", buy="6 m", eur=4.0)
    b.add("Electronics", "JST-XH connector kit", "2-5 pin, with crimps", 1, "motors and sensors", eur=6.0)
    b.add("Electronics", "Hook-up wire, heat shrink, cable ties", "", 1, "general", eur=5.0)

    # ---------------- fasteners
    nut = "M3 nut"
    for j, k in zip(("J1", "J2", "J3", "J4"), KITS):
        k.carrier_cutter()                       # sets k.bolt_len
        D = k.D
        b.add("Fasteners", "Socket head screw", f"M3 x {k.bolt_len}", D.bolt_n, f"{j} drive stack")
        b.add("Fasteners", "Hex nut", "M3", D.bolt_n, f"{j} drive stack")
        clamp = "M3 x 16" if D.clamp_bolt_d > 3 else "M2.5 x 16"
        b.add("Fasteners", "Socket head screw", clamp, D.clamp_bolt_n, f"{j} output clamp")
        post = -k.t - (D.z_sensor_chip - AS5600["chip_from_back"] - 4.0)
        b.add("Fasteners", "Socket head screw", f"M3 x {std_len(post + 4)}", 2, f"{j} sensor bridge")
        b.add("Fasteners", "Socket head screw", "M2 x 6", 2, f"{j} AS5600 board")
        b.add("Fasteners", "Grub screw", "M3 x 4", 1, f"{j} printed 40T pulley")
    for j, L in (("J1", "M3 x 8"), ("J2", "M3 x 10"), ("J3", "M3 x 10"), ("J4", "M3 x 10"), ("J5", "M3 x 10")):
        b.add("Fasteners", "Socket head screw", L, 4, f"{j} motor mount")
    b.add("Fasteners", "Socket head screw", "M3 x 12", 2, "J1 motor shelf posts")
    b.add("Fasteners", "Socket head screw", "M4 x 30", 8, "tube sockets (4 sockets x 2)")
    b.add("Fasteners", "Hex nut", "M4 nyloc", 8, "tube sockets")
    b.add("Fasteners", "Socket head screw", "M4 x 20", 4, "tower foot to turntable")
    b.add("Fasteners", "Hex nut", "M4 nyloc", 4, "tower foot")
    b.add("Fasteners", "Socket head screw", "M3 x 8", 4, "base floor to shell")
    b.add("Fasteners", "Socket head screw", "M4 x 25", 8, "base + pole foot to baseplate")
    b.add("Fasteners", "Washer", "M4", 8, "baseplate")
    b.add("Fasteners", "Hex nut", "M4 nyloc", 8, "baseplate")
    b.add("Fasteners", "Socket head screw", "M2.5 x 6", 4, "Pi")
    b.add("Fasteners", "Socket head screw", "M3 x 6", 8, "ESP32 board, buck converter")
    b.add("Fasteners", "Socket head screw", "M2 x 6", 4, "OLED")
    b.add("Fasteners", "Socket head screw", "M3 x 12", 3, "gripper to roll hub")
    b.add("Fasteners", "Socket head screw", "M3 x 8", 2, "28BYJ-48 ears")
    b.add("Fasteners", "Hex nut", "M3", 2, "28BYJ-48 ears")
    b.add("Fasteners", "Socket head screw", "M2 x 10", 2, "gripper home switch")
    b.add("Fasteners", "Socket head screw", "M4 x 35", 4, "camera pole: foot, tee x 2, boom end")
    b.add("Fasteners", "Socket head screw", "M4 x 40", 2, "camera plate pivot + tilt lock")
    b.add("Fasteners", "Hex nut", "M4 nyloc", 6, "camera pole")
    b.add("Fasteners", "Screw", "1/4\"-20 x 10 mm", 1, "webcam tripod thread", eur=0.5,
          notes="cameras without a thread: strap through the plate slots")
    # ---------------- printing
    b.add("Printing", "PETG filament", "1.75 mm", 1, "all printed parts", buy="2 kg", eur=36.0,
          notes="print the cycloid discs, pulleys and gripper racks at 100% infill")
    b.add("Printing", "TPU filament (optional)", "1.75 mm, 95A", 0, "finger pads", buy="optional", eur=0.0)
    return b


def pack_rules():
    pins = lambda q, spec: (f"{ceil(q * 1.1 / 50) * 50} pcs", ceil(q * 1.1 / 50) * (2.5 if "Ø5" in spec else 2.0))
    screws = lambda q, spec: (f"{max(10, ceil(q * 1.2 / 10) * 10)} pcs",
                              max(10, ceil(q * 1.2 / 10) * 10) * (0.04 if spec.startswith(("M2", "M3")) else 0.07))
    nuts = lambda q, spec: (f"{max(10, ceil(q * 1.2 / 10) * 10)} pcs", max(10, ceil(q * 1.2 / 10) * 10) * 0.03)
    balls = lambda q, spec: ("100 pcs", 3.0)
    brg = lambda q, spec: (str(q + (1 if q >= 2 else 0)), 0.0)
    return {("Motion", "Dowel pin (hardened)"): pins,
            ("Fasteners", "Socket head screw"): screws, ("Fasteners", "Hex nut"): nuts, ("Fasteners", "Washer"): nuts,
            ("Fasteners", "Grub screw"): nuts, ("Bearings", "Steel ball"): balls}


def rows():
    b = collect()
    out = b.finalize(pack_rules())
    # bearings: buy one spare of each type used more than once, price per piece
    for r in out:
        if r[0] == "Bearings" and r[1].startswith("Bearing "):
            each = BEARINGS[r[1].split()[1]].price
            n = r[3] + (1 if r[3] >= 2 else 0)
            r[4], r[5] = str(n), round(n * each, 2)
        if r[0] == "Bearings" and r[1].startswith("Linear"):
            r[4], r[5] = "4", round(4 * LM6UU["price"], 2)
    order = ["Motors", "Motion", "Bearings", "Stock", "Electronics", "Fasteners", "Printing"]
    out.sort(key=lambda r: (order.index(r[0]), r[1], r[2]))
    return out


def total(rs):
    return sum(r[5] for r in rs)


def write(rs, folder=OUT):
    folder.mkdir(exist_ok=True)
    with open(folder / "bom_sourcing.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLS)
        w.writerows(rs)
        w.writerow(["", "TOTAL (estimate)", "", "", "", round(total(rs), 2), "", "", ""])
    lines = [f"# Chess arm: bill of materials\n",
             "Generated by `cad/bom.py` from the CAD parameters. Prices are rough estimates (EUR, online marketplace, "
             "shipping excluded). Webcam and chess set not included.\n"]
    cat = None
    for r in rs:
        if r[0] != cat:
            cat = r[0]
            lines += [f"\n## {cat}\n", "| Part | Spec | Need | Buy | Est. € | Used for | Notes |", "|---|---|---|---|---|---|---|"]
        notes = " ".join(x for x in (f"Search: *{r[7]}*." if r[7] else "", r[8]) if x)
        lines.append(f"| {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]:.2f} | {r[6]} | {notes} |")
    lines.append(f"\n**Estimated total: €{total(rs):.0f}** (budget €300)\n")
    (folder / "bom_sourcing.md").write_text("\n".join(lines))


if __name__ == "__main__":
    rs = rows()
    write(rs)
    print(f"{len(rs)} lines, estimated total EUR {total(rs):.0f} -> {OUT / 'bom_sourcing.csv'}")
