"""Pin map and wiring notes (Markdown), generated from netlist.py."""
from pathlib import Path

from netlist import DRIVERS, ESP_FUNC, ESP_LEFT, ESP_NOTES, ESP_RIGHT, PI_PINS, build, check

OUT = Path(__file__).parent / "out"
# suggested RMS current per joint (about 70 % of the motor's rating; adjust to your motors' data sheets)
CURRENT = {"J1": "0.7 A", "J2": "1.2 A", "J3": "0.9 A", "J4": "0.9 A", "J5": "0.7 A", "J6": "0.15 A"}


def write():
    parts, nets, problems = check()
    L = ["# Controller electronics: pin map\n",
         "Generated from `electronics/netlist.py` (the schematic and perfboard layout use the same file).\n",
         "## ESP32-DevKitC (38 pin)\n", "| Header | Pin | Function / net | Notes |", "|---|---|---|---|"]
    for side, pins in (("left", ESP_LEFT), ("right", ESP_RIGHT)):
        for p in pins:
            f = ESP_FUNC.get(p, "-")
            L.append(f"| {side} | {p} | {f} | {ESP_NOTES.get(p, '')} |")
    L += ["\n## Stepper drivers (TMC2209, UART mode)\n",
          "| Joint | Driver | STEP | DIR | UART bus | Address | MS1 | MS2 | Motor | Connector | Current (RMS) |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    rev = {v: k for k, v in ESP_FUNC.items()}
    for i, (j, ref, bus, addr, motor) in enumerate(DRIVERS, 1):
        L.append(f"| {j} | {ref} | {rev[f'STEP{i}']} | {rev[f'DIR{i}']} | {bus} ({rev[f'UART{bus}_TX']} via 1k / {rev[f'UART{bus}']}) | {addr} | "
                 f"{'3V3' if addr & 1 else 'GND'} | {'3V3' if addr & 2 else 'GND'} | {motor} | M{i} | {CURRENT[j]} |")
    L += ["", "All drivers share EN (IO32, active low). Motor connector pins: 1-2 = coil A, 3-4 = coil B.",
          "Find the coil pairs with a multimeter (a few ohms between the two wires of one coil).",
          "28BYJ-48: cut the PCB trace to the red wire; blue/pink = one coil, yellow/orange = the other.\n",
          "## Raspberry Pi 4 (40-pin header)\n", "| Pin | Signal | Net | Goes to |", "|---|---|---|---|"]
    dest = {"+3V3_PI": "OLED VCC", "PI_SDA": "OLED SDA", "PI_SCL": "OLED SCL", "GND": "OLED GND, buttons",
            "BTN_UP": "button UP (to GND)", "BTN_OK": "button OK (to GND)", "BTN_DOWN": "button DOWN (to GND)"}
    for n, (name, net) in sorted(PI_PINS.items()):
        L.append(f"| {n} | {name} | {net} | {dest.get(net, '')} |")
    L += ["", "USB-C: 5 V from the buck converter (pigtail). USB-A: ESP32 (serial + its power), webcam.\n",
          "## Sensor hub (TCA9548A, address 0x70)\n", "| Channel | Connector | Sensor |", "|---|---|---|"]
    for ch in range(4):
        L.append(f"| SD{ch}/SC{ch} | S{ch + 1} | AS5600 J{ch + 1} |")
    L += ["", "S5 = gripper home switch (HOME_GRIP, active low, 10k pull-up on the main board).",
          "J_I2C (main board) <-> J_HUB (hub): 1 = +3V3, 2 = GND, 3 = SDA, 4 = SCL, 5 = HOME_GRIP.\n",
          "## Power\n",
          "- 24 V 5 A brick -> panel jack -> 5 A slow fuse -> rocker switch -> +24V.",
          "- +24V feeds the six drivers (VM, 100 µF each at the driver) and the buck converter.",
          "- Buck set to 5.1 V -> USB-C pigtail -> Pi. The Pi powers the ESP32 over USB; the ESP32's 3.3 V feeds driver logic, hub and sensors.",
          "- One common ground for everything.\n",
          "## Bring-up order (no motors connected until step 5)\n",
          "1. Continuity check: +24V, +3V3 and GND not shorted to each other.",
          "2. Power the brick with no modules plugged in; check +24V on the rail and set the buck to 5.1 V.",
          "3. Plug in the ESP32 only (USB from a PC): flash, check STEP/DIR toggle on a meter or LED.",
          "4. Plug in the drivers (orientation!), power 24 V: read each driver's version register over UART.",
          "5. Only then connect one motor at a time, low current first. Never plug or unplug a motor with power on.\n"]
    L += [f"\nNetlist check: {len(parts)} parts, {len(nets)} nets, problems: {problems or 'none'}."]
    OUT.mkdir(exist_ok=True)
    (OUT / "pinmap.md").write_text("\n".join(L) + "\n")
    print("pinmap written")


if __name__ == "__main__":
    write()
