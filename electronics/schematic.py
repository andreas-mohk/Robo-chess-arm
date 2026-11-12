"""KiCad-style schematic (2 x A3 SVG) drawn from netlist.py.

Connections are made by net labels (same name = same net), as in KiCad; short green wires
are drawn where parts sit next to each other. Every label on these sheets comes from the
netlist, so the drawing and the pin map cannot disagree.
"""
from pathlib import Path

from netlist import (DRIVERS, ESP_FUNC, ESP_LEFT, ESP_NOTES, ESP_RIGHT, PI_PINS, TMC_LEFT, TMC_RIGHT, build,
                     check)

OUT = Path(__file__).parent / "out"
W, H = 420.0, 297.0
BG, BODY, FILL, PIN, PINNAME, REF, WIRE, LABEL, POWER = ("#F5F4EF", "#840000", "#FFFFC2", "#840000", "#008484",
                                                        "#006464", "#008400", "#5B2A86", "#840000")
FONT = "DejaVu Sans Mono, Liberation Mono, monospace"
P = 3.81          # pin pitch
STUB = 3.81       # pin length
POWER_NETS = {"+24V", "+3V3", "+5V_PI", "+3V3_PI", "GND", "VIN_24", "VIN_24F"}


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def t(x, y, s, size=1.9, color="#000", anchor="start", weight="normal", rot=0):
    r = f' transform="rotate({rot} {x:.2f} {y:.2f})"' if rot else ""
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-family="{FONT}" font-size="{size}" fill="{color}" '
            f'text-anchor="{anchor}" font-weight="{weight}"{r}>{esc(s)}</text>')


def ln(x1, y1, x2, y2, c=WIRE, w=0.25):
    return f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{c}" stroke-width="{w}" stroke-linecap="round"/>'


def dot(x, y):
    return f'<circle cx="{x:.2f}" cy="{y:.2f}" r="0.55" fill="{WIRE}"/>'


def net_label(x, y, net, side):
    """Label attached at (x, y); side = -1 draws it to the left, +1 to the right."""
    if net in POWER_NETS:
        col = POWER
        if net == "GND":
            gx = x + side * 3.0
            return (ln(x, y, gx, y) + ln(gx, y - 1.6, gx, y + 1.6, POWER, 0.3) + ln(gx + side * 0.7, y - 1.0, gx + side * 0.7, y + 1.0, POWER, 0.3)
                    + ln(gx + side * 1.4, y - 0.4, gx + side * 1.4, y + 0.4, POWER, 0.3)
                    + t(gx + side * 2.4, y + 0.7, "GND", 1.7, col, "start" if side > 0 else "end"))
        gx = x + side * 3.0
        return (ln(x, y, gx, y) + ln(gx, y - 1.5, gx, y + 1.5, POWER, 0.35)
                + t(gx + side * 1.0, y + 0.7, net, 1.8, col, "start" if side > 0 else "end", "bold"))
    wlen = 1.25 * len(net) + 3.2
    x0 = x + side * 1.2
    x1 = x0 + side * wlen
    pts = [(x, y), (x0, y - 1.3), (x1, y - 1.3), (x1, y + 1.3), (x0, y + 1.3)]
    path = "M" + " L".join(f"{a:.2f} {b:.2f}" for a, b in pts) + " Z"
    return (f'<path d="{path}" fill="#fff" stroke="{LABEL}" stroke-width="0.25"/>'
            + t((x0 + x1) / 2, y + 0.65, net, 1.7, LABEL, "middle"))


def symbol(x, y, w, left, right, ref, value, labels=True, pin_numbers=None):
    """Rectangle symbol with pins on both sides. left/right: [(pin name, net or None)].
    Returns (svg, {pin name or (side, i): (x, y) of the pin's outer end})."""
    n = max(len(left), len(right))
    h = (n + 1) * P
    out = [f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" fill="{FILL}" stroke="{BODY}" stroke-width="0.35"/>',
           t(x, y - 3.2, ref, 2.1, REF, weight="bold"), t(x, y - 1.0, value, 1.8, REF)]
    ends = {}
    for side, pins in ((-1, left), (1, right)):
        for i, (name, net) in enumerate(pins):
            py = y + (i + 1) * P
            px = x if side < 0 else x + w
            ex = px + side * STUB
            out.append(ln(px, py, ex, py, PIN, 0.3))
            out.append(t(px - side * 1.0, py + 0.65, name, 1.65, PINNAME, "start" if side < 0 else "end"))
            ends[(side, i)] = (ex, py)
            ends.setdefault(name, (ex, py))
            if labels and net:
                out.append(net_label(ex, py, net, side))
    return "".join(out), ends


def section(x, y, w, h, title):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none" stroke="#9a9a9a" stroke-width="0.3" stroke-dasharray="2 1.2"/>'
            + t(x + 2, y + 4.5, title, 2.6, "#444", weight="bold"))


def frame(sheet, total, title):
    m = 8
    out = [f'<rect x="0" y="0" width="{W}" height="{H}" fill="{BG}"/>',
           f'<rect x="{m}" y="{m}" width="{W - 2 * m}" height="{H - 2 * m}" fill="none" stroke="{BODY}" stroke-width="0.4"/>']
    for i in range(8):
        out.append(t(m + (i + .5) * (W - 2 * m) / 8, m - 1.5, i + 1, 2.2, BODY, "middle"))
    for j in range(6):
        out.append(t(m - 3.2, m + (j + .5) * (H - 2 * m) / 6, "ABCDEF"[j], 2.2, BODY))
    bx, by, bw, bh = W - m - 130, H - m - 28, 130, 28
    out.append(f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" fill="{BG}" stroke="{BODY}" stroke-width="0.4"/>')
    out.append(ln(bx, by + 9, bx + bw, by + 9, BODY, 0.3) + ln(bx, by + 19, bx + bw, by + 19, BODY, 0.3))
    out.append(t(bx + 2, by + 6.5, title, 3.4, "#000", weight="bold"))
    out.append(t(bx + 2, by + 14.5, "Chess Robot Arm - controller electronics", 2.3))
    out.append(t(bx + 2, by + 25, f"Sheet {sheet}/{total}   Rev D   generated from electronics/netlist.py", 2.0))
    return "".join(out)


def svg(body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}">{body}</svg>')


# ------------------------------------------------------------------ sheet 1
def sheet1(parts):
    o = [frame(1, 2, "Power, controller, stepper drivers")]
    # power
    o.append(section(14, 16, 150, 82, "POWER"))
    y = 34
    xs = [24, 52, 80, 108]
    o.append(f'<rect x="{xs[0] - 6}" y="{y - 6}" width="10" height="12" fill="{FILL}" stroke="{BODY}" stroke-width="0.35"/>')
    o.append(t(xs[0] - 6, y - 8, "J_PWR", 2.1, REF, weight="bold") + t(xs[0] - 6, y + 9.5, "DC jack 24 V", 1.8, REF))
    o.append(t(xs[0] - 5, y - 1.5, "+", 2, BODY) + t(xs[0] - 5, y + 4, "-", 2, BODY))
    o.append(ln(xs[0] + 4, y - 3, xs[1] - 4, y - 3))
    o.append(f'<rect x="{xs[1] - 4}" y="{y - 4.5}" width="8" height="3" fill="{FILL}" stroke="{BODY}" stroke-width="0.35"/>')
    o.append(t(xs[1] - 4, y - 6, "F1 5 A slow", 1.8, REF, weight="bold"))
    o.append(ln(xs[1] + 4, y - 3, xs[2] - 4, y - 3))
    o.append(f'<path d="M{xs[2] - 4} {y - 3} L{xs[2] + 3} {y - 6}" stroke="{BODY}" stroke-width="0.4"/>'
             + f'<circle cx="{xs[2] - 4}" cy="{y - 3}" r="0.6" fill="none" stroke="{BODY}" stroke-width="0.3"/>'
             + f'<circle cx="{xs[2] + 4}" cy="{y - 3}" r="0.6" fill="none" stroke="{BODY}" stroke-width="0.3"/>')
    o.append(t(xs[2] - 4, y - 7.5, "SW1 power", 1.8, REF, weight="bold"))
    o.append(ln(xs[2] + 4.6, y - 3, xs[3], y - 3) + dot(xs[3], y - 3) + net_label(xs[3], y - 3, "+24V", 1))
    o.append(ln(xs[0] + 4, y + 3, xs[3], y + 3) + net_label(xs[3], y + 3, "GND", 1))
    o.append(t(24, 50, "24 V 5 A external brick. No mains inside the base.", 1.8, "#444"))
    s, e = symbol(40, 62, 28, [("IN+", "+24V"), ("IN-", "GND")], [("OUT+", "+5V_PI"), ("OUT-", "GND")],
                  "U_BUCK", "Buck 24 V -> 5 V 5 A")
    o.append(s)
    s, e = symbol(108, 62, 26, [("VBUS", "+5V_PI"), ("GND", "GND")], [], "J_PIPWR", "USB-C pigtail -> Pi 4")
    o.append(s)
    o.append(t(24, 86, "Set the buck to 5.10 V before connecting the Pi.", 1.8, "#444"))
    o.append(t(24, 90, "Drivers and buck share one GND with the ESP32 and the Pi.", 1.8, "#444"))
    # controller
    o.append(section(14, 102, 150, 166, "CONTROLLER - ESP32-DevKitC (38 pin, USB from the Pi)"))
    left = [(p, ESP_FUNC.get(p)) for p in ESP_LEFT]
    right = [(p, ESP_FUNC.get(p)) for p in ESP_RIGHT]
    s, e = symbol(62, 118, 34, left, right, "U_ESP", "ESP32-DevKitC-32 (38 pin)")
    o.append(s)
    o.append(t(79, 118 + 20 * P + 2.5, "USB: data + 5 V from the Pi (USB_ESP)", 1.7, REF, "middle"))
    # resistors
    rx, ry = 20, 210
    for i, (ref, val, a, b) in enumerate((("R1", "1k", "UARTA_TX", "UARTA"), ("R2", "1k", "UARTB_TX", "UARTB"),
                                          ("R3", "10k", "HOME_GRIP", "+3V3"), ("R4", "10k", "STOP_IN", "+3V3"))):
        yy = ry + i * 13
        o.append(f'<rect x="{rx + 22}" y="{yy - 1.4}" width="8" height="2.8" fill="{FILL}" stroke="{BODY}" stroke-width="0.35"/>')
        o.append(t(rx + 22, yy - 2.4, f"{ref} {val}", 1.8, REF, weight="bold"))
        o.append(ln(rx + 19, yy, rx + 22, yy, PIN, 0.3) + ln(rx + 30, yy, rx + 33, yy, PIN, 0.3))
        o.append(net_label(rx + 19, yy, a, -1) if False else net_label(rx + 19, yy, a, -1))
        o.append(net_label(rx + 33, yy, b, 1))
    s, e = symbol(118, 228, 16, [(str(i), parts["J_I2C"]["pins"][str(i)]) for i in range(1, 6)], [], "J_I2C",
                  "JST-XH 5 -> sensor hub")
    o.append(s)
    o.append(t(rx + 52, ry - 4, "Single-wire UART: TX through 1k,", 1.7, "#444"))
    o.append(t(rx + 52, ry - 0.5, "RX straight on the bus (TMC2209 PDN_UART).", 1.7, "#444"))
    o.append(t(rx + 52, ry + 3, "GPIO34-39 have no pull-ups: R3, R4.", 1.7, "#444"))
    o.append(t(rx + 52, ry + 6.5, "Bus A: J1-J4 (addr 0-3). Bus B: J5, J6.", 1.7, "#444"))
    # drivers
    o.append(section(168, 16, 238, 252, "STEPPER DRIVERS - 6 x TMC2209 StepStick (UART mode)"))
    for k, (j, ref, bus, addr, motor) in enumerate(DRIVERS):
        col, row = k % 3, k // 3
        bx, by = 172 + col * 79, 30 + row * 118
        pins = parts[ref]["pins"]
        lp = [(n, pins.get(n)) for n in TMC_LEFT]
        rp = [(n, pins.get(n) if n not in ("A1", "A2", "B1", "B2") else None) for n in TMC_RIGHT]
        s, e = symbol(bx + 20, by + 8, 24, lp, rp, ref, f"TMC2209  {j}", labels=True)
        o.append(s)
        o.append(t(bx + 2, by + 49, f"{j}: bus {bus}, address {addr} (MS1={'1' if addr & 1 else '0'}, MS2={'1' if addr & 2 else '0'})",
                   1.7, "#444"))
        o.append(t(bx + 2, by + 52.5, f"motor: {motor}", 1.7, "#444"))
        # motor connector
        mx, my = bx + 62, by + 14
        conn_y = [my + i * P for i in range(4)]
        o.append(f'<rect x="{mx}" y="{my - 2.5}" width="7" height="{4 * P + 1.2}" fill="{FILL}" stroke="{BODY}" stroke-width="0.35"/>')
        o.append(t(mx, my - 4, f"M{k + 1}", 2.0, REF, weight="bold") + t(mx - 3, my + 4 * P + 2.5, "JST-XH 4", 1.6, REF))
        for i, (nm, ci) in enumerate((("A1", 0), ("A2", 1), ("B1", 2), ("B2", 3))):
            idx = TMC_RIGHT.index(nm)
            ex, ey = e[(1, idx)]
            cy_ = conn_y[ci]
            lane = ex + 2.0 + 1.6 * ci
            o.append(ln(ex, ey, lane, ey) + ln(lane, ey, lane, cy_) + ln(lane, cy_, mx, cy_))
            o.append(t(mx + 1.0, cy_ + 0.6, str(ci + 1), 1.6, PINNAME))
        o.append(t(mx + 8, my + 1.5, "coil A", 1.6, "#444") + t(mx + 8, my + 2 * P + 1.5, "coil B", 1.6, "#444"))
        # bulk capacitor
        cx, cy0 = bx + 6, by + 62
        o.append(ln(cx, cy0, cx, cy0 + 4) + ln(cx - 3, cy0 + 4, cx + 3, cy0 + 4, BODY, 0.45)
                 + f'<path d="M{cx - 3} {cy0 + 6} Q{cx} {cy0 + 4.8} {cx + 3} {cy0 + 6}" fill="none" stroke="{BODY}" stroke-width="0.45"/>'
                 + ln(cx, cy0 + 5.5, cx, cy0 + 9))
        o.append(net_label(cx, cy0, "+24V", 1) + net_label(cx, cy0 + 9, "GND", 1))
        o.append(t(cx + 5, cy0 + 5.6, f"C{k + 1} 100µF 35V (at VM)", 1.7, REF))
    return svg("".join(o))


# ------------------------------------------------------------------ sheet 2
def sheet2(parts):
    o = [frame(2, 2, "Sensor hub, Raspberry Pi, user interface")]
    o.append(section(14, 16, 250, 252, "SENSOR HUB - small perfboard near the cable passage"))
    s, e = symbol(22, 36, 16, [], [(str(i), parts["J_HUB"]["pins"][str(i)]) for i in range(1, 6)], "J_HUB",
                  "JST-XH 5 (cable from main board J_I2C)")
    o.append(s)
    mux = parts["U_MUX"]["pins"]
    left = [(n, mux[n]) for n in ("VIN", "GND", "SDA", "SCL", "RST", "A0", "A1", "A2")]
    right = [(f"{a}{ch}", mux[f"{a}{ch}"]) for ch in range(4) for a in ("SD", "SC")]
    s, e = symbol(98, 36, 30, left, right, "U_MUX", "TCA9548A breakout")
    o.append(s)
    o.append(t(98, 36 + 9 * P + 3, "SD4..SD7 / SC4..SC7 not used. Address 0x70.", 1.7, "#444"))
    for ch in range(4):
        y0 = 36 + ch * 30
        s, e = symbol(170, y0, 14, [(str(i), parts[f"S{ch + 1}"]["pins"][str(i)]) for i in range(1, 5)], [],
                      f"S{ch + 1}", f"JST-XH 4 -> J{ch + 1}")
        o.append(s)
        enc = parts[f"ENC{ch + 1}"]["pins"]
        s, e2 = symbol(215, y0, 18, [(n, enc[n]) for n in ("VCC", "GND", "SDA", "SCL", "DIR")], [],
                       f"ENC{ch + 1}", f"AS5600 J{ch + 1} (3.3 V)")
        o.append(s)
    y5 = 165
    s, e = symbol(170, y5, 14, [("1", "HOME_GRIP"), ("2", "GND")], [], "S5", "JST-XH 2 -> gripper")
    o.append(s)
    s, e = symbol(215, y5, 18, [("NO", "HOME_GRIP"), ("COM", "GND")], [], "SW_HOME", "micro switch")
    o.append(s)
    s, e = symbol(215, 190, 18, [("1", "STOP_IN"), ("2", "GND")], [], "SW_STOP", "stop button (optional)")
    o.append(s)
    notes = ["AS5600 boards: solder the 3.3 V option, tie DIR to GND, magnet 1-2 mm from the chip.",
             "I2C runs at 100 kHz; up to ~1 m of cable per sensor is fine.",
             "Most AS5600 / TCA9548A breakouts already carry 4.7k-10k pull-ups.",
             "STOP_IN reaches the main board over a separate 2-wire cable (optional)."]
    for i, n in enumerate(notes):
        o.append(t(22, 220 + i * 4.5, n, 1.8, "#444"))
    # Pi + UI
    o.append(section(268, 16, 138, 226, "RASPBERRY PI 4 + USER INTERFACE"))
    pi = sorted(PI_PINS.items())
    left = [(f"{n} {name}", net) for n, (name, net) in pi if n % 2 == 1]
    right = [(f"{name} {n}", net) for n, (name, net) in pi if n % 2 == 0]
    s, e = symbol(312, 36, 40, left, right + [("USB-C", "+5V_PI"), ("USB-A", "USB_ESP"), ("USB-A", "USB_CAM")],
                  "U_PI", "Raspberry Pi 4 Model B 1 GB")
    o.append(s)
    s, e = symbol(312, 90, 30, [(n, parts["U_OLED"]["pins"][n]) for n in ("VCC", "GND", "SCL", "SDA")], [],
                  "U_OLED", '1.3" SH1106 I2C (0x3C)')
    o.append(s)
    for i, (ref, net) in enumerate((("SW_UP", "BTN_UP"), ("SW_OK", "BTN_OK"), ("SW_DOWN", "BTN_DOWN"))):
        y = 130 + i * 14
        o.append(net_label(300, y, net, -1) + ln(300, y, 312, y) + ln(312, y, 314, y - 1.8, BODY, 0.4)
                 + f'<circle cx="{312}" cy="{y}" r="0.5" fill="none" stroke="{BODY}" stroke-width="0.3"/>'
                 + f'<circle cx="{316}" cy="{y}" r="0.5" fill="none" stroke="{BODY}" stroke-width="0.3"/>'
                 + ln(316.5, y, 320, y) + net_label(320, y, "GND", 1) + t(306, y - 3, f"{ref} 12 mm", 1.8, REF, weight="bold"))
    s, e = symbol(340, 176, 24, [("USB", "USB_CAM")], [], "U_CAM", "Webcam")
    o.append(s)
    s, e = symbol(340, 196, 24, [("USB", "USB_ESP")], [], "U_ESP", "ESP32 micro-USB (sheet 1)")
    o.append(s)
    for i, n in enumerate(["Buttons use the Pi's internal pull-ups.", "OLED shares the Pi's I2C bus 1 (not the ESP32's).",
                           "USB_ESP: serial link Pi <-> ESP32 + its 5 V supply."]):
        o.append(t(274, 220 + i * 4.5, n, 1.8, "#444"))
    return svg("".join(o))


def write():
    parts, nets, problems = check()
    if problems:
        raise SystemExit(problems)
    OUT.mkdir(exist_ok=True)
    (OUT / "schematic_1.svg").write_text(sheet1(parts))
    (OUT / "schematic_2.svg").write_text(sheet2(parts))
    print("schematic written")


if __name__ == "__main__":
    write()
