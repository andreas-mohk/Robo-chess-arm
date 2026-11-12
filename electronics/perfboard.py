"""Perfboard layout for the main controller board (90 x 70 mm, 2.54 mm grid), drawn from netlist.py.

Top view (component side) with every wire drawn in colour, a mirrored solder-side view,
and a wiring list. The script checks that no hole is used twice and that every netlist
connection on this board has a wire (or a rail) between its pins.
"""
from collections import defaultdict
from math import hypot
from pathlib import Path

from netlist import DRIVERS, ESP_FUNC, ESP_LEFT, ESP_RIGHT, TMC_LEFT, TMC_RIGHT, build

OUT = Path(__file__).parent / "out"
COLS, ROWS = 34, 26
PITCH = 2.54
BOARD_W, BOARD_H = 90.0, 70.0
OX, OY = (BOARD_W - (COLS - 1) * PITCH) / 2, (BOARD_H - (ROWS - 1) * PITCH) / 2
ESP_COL_L, ESP_COL_R, ESP_ROW0 = 23, 33, 3      # check your DevKit: rows 10 holes (25.4 mm) apart
RAIL = {"+24V": 11, "GND": 12, "+3V3": 13}
RAIL_COLS = (0, 22)
NET_COLOR = {"+24V": "#d62728", "GND": "#222", "+3V3": "#ff9f1c", "EN_ALL": "#8c564b", "UARTA": "#2ca02c", "UARTB": "#17becf",
             "SDA": "#9467bd", "SCL": "#c084fc", "HOME_GRIP": "#e377c2", "STOP_IN": "#e377c2"}


def xy(c, r):
    return OX + c * PITCH, OY + r * PITCH


class Board:
    def __init__(self):
        self.pins = {}          # (ref, pin) -> (c, r)
        self.holes = {}         # (c, r) -> (ref, pin)
        self.bodies = []        # (ref, label, c0, r0, c1, r1, style)

    def place(self, ref, pin, c, r):
        if (c, r) in self.holes:
            raise ValueError(f"hole {c},{r} used by {self.holes[(c, r)]} and {(ref, pin)}")
        if not (0 <= c < COLS and 0 <= r < ROWS):
            raise ValueError(f"{ref}.{pin} at {c},{r} is off the board")
        self.pins[(ref, pin)] = (c, r)
        self.holes[(c, r)] = (ref, pin)

    def body(self, ref, label, c0, r0, c1, r1, style="module"):
        self.bodies.append((ref, label, c0, r0, c1, r1, style))


def layout():
    b = Board()
    # ESP32 on two 19-pin female headers
    for i, p in enumerate(ESP_LEFT):
        b.place("U_ESP", ("L", p), ESP_COL_L, ESP_ROW0 + i)
    for i, p in enumerate(ESP_RIGHT):
        b.place("U_ESP", ("R", p), ESP_COL_R, ESP_ROW0 + i)
    b.body("U_ESP", "ESP32-DevKitC (on sockets)", ESP_COL_L - 0.6, ESP_ROW0 - 2.2, ESP_COL_R + 0.6, ESP_ROW0 + 20.6)
    # drivers: top bank rotated 180 deg (VM at the bottom, near the rails), bottom bank upright
    for k, (j, ref, bus, addr, motor) in enumerate(DRIVERS):
        c = (k % 3) * 7
        if k < 3:
            r0 = 3
            for i, p in enumerate(reversed(TMC_RIGHT)):
                b.place(ref, ("P", p, i), c, r0 + i)
            for i, p in enumerate(reversed(TMC_LEFT)):
                b.place(ref, ("L", p), c + 5, r0 + i)
            b.body(ref, f"{ref} TMC2209 {j}", c - 0.5, r0 - 0.5, c + 5.5, r0 + 7.5)
            # motor connector at the top edge, above the power column
            for i in range(4):
                b.place(f"M{k + 1}", str(i + 1), c + i, 0)
            b.body(f"M{k + 1}", f"M{k + 1}", c - 0.6, -0.4, c + 3.6, 1.2, "jst")
        else:
            r0 = 14
            for i, p in enumerate(TMC_LEFT):
                b.place(ref, ("L", p), c, r0 + i)
            for i, p in enumerate(TMC_RIGHT):
                b.place(ref, ("P", p, i), c + 5, r0 + i)
            b.body(ref, f"{ref} TMC2209 {j}", c - 0.5, r0 - 0.5, c + 5.5, r0 + 7.5)
            for i in range(4):
                b.place(f"M{k + 1}", str(i + 1), c + 2 + i, 25)
            b.body(f"M{k + 1}", f"M{k + 1}", c + 1.4, 23.8, c + 5.6, 25.4, "jst")
        # bulk capacitor between the +24V and GND rails, laid flat
        cc = c + (1 if k < 3 else 4)
        b.place(f"C{k + 1}", "+", cc, RAIL["+24V"])
        b.place(f"C{k + 1}", "-", cc, RAIL["GND"])
    # 24 V input: 2-pin screw terminal, 5.08 mm
    b.place("J_24", "+", 20, 1)
    b.place("J_24", "-", 22, 1)
    b.body("J_24", "24V IN", 19.4, -0.2, 22.6, 2.2, "terminal")
    # resistors under the ESP32 module (it sits 8.5 mm up on sockets)
    for ref, (c, r) in (("R1", (25, 6)), ("R2", (25, 8)), ("R3", (25, 10)), ("R4", (25, 12))):
        b.place(ref, "1", c, r)
        b.place(ref, "2", c + 4, r)
        b.body(ref, ref, c + 0.8, r - 0.45, c + 3.2, r + 0.45, "resistor")
    # connectors on the bottom edge
    for i in range(5):
        b.place("J_I2C", str(i + 1), 20 + i, 25)
    b.body("J_I2C", "J_I2C hub", 19.4, 23.8, 24.6, 25.4, "jst")
    for i in range(2):
        b.place("J_STOP", str(i + 1), 31 + i, 25)
    b.body("J_STOP", "STOP", 30.4, 23.8, 32.6, 25.4, "jst")
    return b


def pin_net(parts, ref, pin):
    """Net of a placed pin, using the netlist."""
    if ref == "U_ESP":
        side, name = pin
        return ESP_FUNC.get(name)
    if ref.startswith("U") and ref[1:].isdigit():
        name = pin[1]
        return parts[ref]["pins"].get(name)
    if ref == "J_STOP":
        return {"1": "STOP_IN", "2": "GND"}[pin]
    p = parts.get(ref, {}).get("pins", {})
    return p.get(pin)


def connections(b, parts):
    """Group placed pins by net, then join each group into a chain of wires.
    Rail nets (+24V, GND, +3V3) connect each pin to the nearest point of its rail."""
    groups = defaultdict(list)
    for (ref, pin), (c, r) in b.pins.items():
        net = pin_net(parts, ref, pin)
        if net and net not in ("NC",):
            groups[net].append(((ref, pin), (c, r)))
    wires = []
    for net, items in groups.items():
        if net in RAIL:
            rr = RAIL[net]
            for (ref, pin), (c, r) in items:
                if r == rr:
                    continue
                cc = min(max(c, RAIL_COLS[0]), RAIL_COLS[1])
                wires.append((net, (c, r), (cc, rr), f"{ref}.{_pn(pin)}", f"{net} rail"))
            continue
        if len(items) < 2:
            continue
        # chain: nearest-neighbour order starting from the ESP32 pin if present
        items = sorted(items, key=lambda t: (t[0][0] != "U_ESP", t[1]))
        chain = [items.pop(0)]
        while items:
            last = chain[-1][1]
            k = min(range(len(items)), key=lambda i: hypot(items[i][1][0] - last[0], items[i][1][1] - last[1]))
            chain.append(items.pop(k))
        for a, bb in zip(chain, chain[1:]):
            wires.append((net, a[1], bb[1], f"{a[0][0]}.{_pn(a[0][1])}", f"{bb[0][0]}.{_pn(bb[0][1])}"))
    return wires, groups


def _pn(pin):
    if isinstance(pin, tuple):
        return pin[1]
    return pin


def check(b, parts, wires):
    """Every connection the netlist makes between parts on this board must be wired."""
    on_board = {ref for ref, _ in b.pins}
    problems = []
    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            x = parent[x]
        return x

    for net, a, c, *_ in wires:
        parent[find(a)] = find(c)
    for net, r in RAIL.items():
        for col in range(RAIL_COLS[0], RAIL_COLS[1]):
            parent[find((col, r))] = find((col + 1, r))
    by_net = defaultdict(set)
    for (ref, pin), pos in b.pins.items():
        net = pin_net(parts, ref, pin)
        if net and net != "NC":
            by_net[net].add(find(pos))
    for net, roots in by_net.items():
        if len(roots) > 1:
            problems.append(f"net {net} is split into {len(roots)} islands")
    return problems


# ------------------------------------------------------------------ drawing
def draw(b, wires, mirror=False, title=""):
    s = 4.0                      # px per mm in the SVG user space (we keep mm and scale with viewBox)
    pad = 12
    W, H = BOARD_W + 2 * pad + 44, BOARD_H + 2 * pad + 6
    def X(x):
        return pad + (BOARD_W - x if mirror else x)
    def Y(y):
        return pad + 6 + y
    o = [f'<rect x="0" y="0" width="{W}" height="{H}" fill="#fbfaf6"/>',
         f'<text x="{pad}" y="7" font-family="DejaVu Sans, sans-serif" font-size="3.2" font-weight="bold">{title}</text>',
         f'<rect x="{X(0) if not mirror else X(BOARD_W)}" y="{Y(0)}" width="{BOARD_W}" height="{BOARD_H}" rx="1.5" fill="#d9b779" stroke="#8a6d3b" stroke-width="0.4"/>']
    for c in range(COLS):
        for r in range(ROWS):
            x, y = xy(c, r)
            o.append(f'<circle cx="{X(x):.2f}" cy="{Y(y):.2f}" r="0.55" fill="#c9a35d" stroke="#a88545" stroke-width="0.15"/>')
    # rails (bare tinned wire on the solder side)
    for net, r in RAIL.items():
        x0, y0 = xy(RAIL_COLS[0], r)
        x1, _ = xy(RAIL_COLS[1], r)
        o.append(f'<line x1="{X(x0):.2f}" y1="{Y(y0):.2f}" x2="{X(x1):.2f}" y2="{Y(y0):.2f}" stroke="{NET_COLOR[net]}" stroke-width="0.9" stroke-linecap="round" opacity="0.85"/>')
        lx = X(0) - 1.0 if not mirror else X(0) + 1.0
        o.append(f'<text x="{lx:.2f}" y="{Y(y0) + 0.6:.2f}" font-family="DejaVu Sans" font-size="1.6" text-anchor="{"end" if not mirror else "start"}" fill="{NET_COLOR[net]}" font-weight="bold">{net}</text>')
    # bodies (component side only)
    if not mirror:
        for ref, label, c0, r0, c1, r1, style in b.bodies:
            x0, y0 = xy(c0, r0)
            x1, y1 = xy(c1, r1)
            fill = {"module": "#2f6f6a", "jst": "#f2f2f2", "terminal": "#2b6cb0", "resistor": "#d8c7a1"}[style]
            op = "0.22" if style == "module" else "0.9"
            o.append(f'<rect x="{X(x0):.2f}" y="{Y(y0):.2f}" width="{x1 - x0:.2f}" height="{y1 - y0:.2f}" rx="0.6" fill="{fill}" fill-opacity="{op}" stroke="#333" stroke-width="0.2"/>')
            if style == "module" and ref != "U_ESP":
                cx_, cy_ = X((x0 + x1) / 2), Y((y0 + y1) / 2)
                o.append(f'<text x="{cx_:.2f}" y="{cy_:.2f}" font-family="DejaVu Sans" font-size="1.7" text-anchor="middle" '
                         f'fill="#111" font-weight="bold" transform="rotate(-90 {cx_:.2f} {cy_:.2f})">{label}</text>')
            elif style == "module":
                o.append(f'<text x="{X((x0 + x1) / 2):.2f}" y="{Y(y1) - 1.2:.2f}" font-family="DejaVu Sans" font-size="1.7" '
                         f'text-anchor="middle" fill="#111" font-weight="bold">{label}</text>')
            else:
                o.append(f'<text x="{X((x0 + x1) / 2):.2f}" y="{Y((y0 + y1) / 2) + 0.45:.2f}" font-family="DejaVu Sans" '
                         f'font-size="1.2" text-anchor="middle" fill="#111">{label}</text>')
    # wires
    for net, a, c, la, lc in wires:
        (x0, y0), (x1, y1) = xy(*a), xy(*c)
        col = NET_COLOR.get(net, NET_COLOR.get(net.rstrip("0123456789"), "#1f77b4"))
        if net.startswith(("STEP", "DIR")):
            col = "#1f77b4" if net.startswith("STEP") else "#4a90d9"
        if net.startswith("M"):
            col = "#b5651d"
        mx = (x0 + x1) / 2
        bend = 0.18 * hypot(x1 - x0, y1 - y0)
        path = f"M{X(x0):.2f} {Y(y0):.2f} Q{X(mx):.2f} {Y(min(y0, y1) - bend * 0.2):.2f} {X(x1):.2f} {Y(y1):.2f}"
        o.append(f'<path d="{path}" fill="none" stroke="{col}" stroke-width="0.45" stroke-linecap="round" opacity="0.9"/>')
    # pads with pins
    for (ref, pin), (c, r) in b.pins.items():
        x, y = xy(c, r)
        o.append(f'<circle cx="{X(x):.2f}" cy="{Y(y):.2f}" r="0.75" fill="#e7c25c" stroke="#7a5c12" stroke-width="0.2"/>')
    # pin names for drivers and ESP32 (small)
    for (ref, pin), (c, r) in b.pins.items():
        x, y = xy(c, r)
        name = _pn(pin)
        if ref == "U_ESP":
            dx = -1.1 if pin[0] == "L" else 1.1
            if mirror:
                dx = -dx
            o.append(f'<text x="{X(x) + dx:.2f}" y="{Y(y) + 0.45:.2f}" font-family="DejaVu Sans Mono" font-size="0.95" text-anchor="{"end" if dx < 0 else "start"}" fill="#333">{name}</text>')
        elif ref.startswith("U") and ref[1:].isdigit():
            o.append(f'<text x="{X(x):.2f}" y="{Y(y) - 0.95:.2f}" font-family="DejaVu Sans Mono" font-size="0.8" text-anchor="middle" fill="#333">{name}</text>')
    legend = [("+24V", "#d62728"), ("GND", "#222"), ("+3V3", "#ff9f1c"), ("STEPn", "#1f77b4"), ("DIRn", "#4a90d9"),
              ("EN_ALL", "#8c564b"), ("UART bus A", "#2ca02c"), ("UART bus B", "#17becf"), ("SDA / SCL", "#9467bd"),
              ("HOME / STOP", "#e377c2"), ("motor coils", "#b5651d")]
    lx0 = pad + BOARD_W + 6
    o.append(f'<text x="{lx0}" y="{Y(2):.2f}" font-family="DejaVu Sans" font-size="2" font-weight="bold">Wire colours</text>')
    for i, (n, col) in enumerate(legend):
        yy = Y(6 + i * 4.2)
        o.append(f'<line x1="{lx0}" y1="{yy:.2f}" x2="{lx0 + 6}" y2="{yy:.2f}" stroke="{col}" stroke-width="0.9"/>'
                 f'<text x="{lx0 + 8}" y="{yy + 0.7:.2f}" font-family="DejaVu Sans" font-size="1.8">{n}</text>')
    o.append(f'<text x="{lx0}" y="{Y(55):.2f}" font-family="DejaVu Sans" font-size="1.6" fill="#444">JST-XH is 2.5 mm pitch:</text>')
    o.append(f'<text x="{lx0}" y="{Y(57.5):.2f}" font-family="DejaVu Sans" font-size="1.6" fill="#444">fits 2.54 mm holes (4-5 pins).</text>')
    o.append(f'<text x="{lx0}" y="{Y(61):.2f}" font-family="DejaVu Sans" font-size="1.6" fill="#444">Lay C1-C6 flat under the</text>')
    o.append(f'<text x="{lx0}" y="{Y(63.5):.2f}" font-family="DejaVu Sans" font-size="1.6" fill="#444">driver overhang.</text>')
    o.append(f'<text x="{pad}" y="{H - 2:.1f}" font-family="DejaVu Sans" font-size="1.9" fill="#444">'
             f'{COLS} x {ROWS} holes at 2.54 mm. Thick lines = bare rails on the solder side; thin lines = insulated wire. '
             f'{"Solder side (mirrored)." if mirror else "Component side."}</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W * s:.0f}" height="{H * s:.0f}" viewBox="0 0 {W:.1f} {H:.1f}">'
            + "".join(o) + "</svg>")


def wiring_list(wires):
    rows = ["| # | Net | From | To | Wire |", "|---|---|---|---|---|"]
    for i, (net, a, c, la, lc) in enumerate(wires, 1):
        kind = "short bare link to rail" if lc.endswith("rail") and abs(a[1] - c[1]) <= 1 else "insulated"
        rows.append(f"| {i} | {net} | {la} ({a[0]},{a[1]}) | {lc} ({c[0]},{c[1]}) | {kind} |")
    return "\n".join(rows)


def write():
    parts, nets = build()
    b = layout()
    wires, groups = connections(b, parts)
    problems = check(b, parts, wires)
    OUT.mkdir(exist_ok=True)
    (OUT / "perfboard_top.svg").write_text(draw(b, wires, False, "MAIN BOARD - component side (top view)"))
    (OUT / "perfboard_bottom.svg").write_text(draw(b, wires, True, "MAIN BOARD - solder side (mirrored, for soldering)"))
    (OUT / "perfboard_wiring.md").write_text("# Main board wiring list\n\nHole coordinates are (column, row) from the top-left "
                                             "of the component side, 0-based.\n\n" + wiring_list(wires) + "\n")
    print(f"{len(b.pins)} pins placed, {len(wires)} wires; problems: {problems or 'none'}")
    return problems


if __name__ == "__main__":
    raise SystemExit(1 if write() else 0)
