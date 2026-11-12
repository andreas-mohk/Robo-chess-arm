"""Single source of truth for the electronics: parts, pins and nets.

Schematic, perfboard layout and pin map are all drawn from this file, and check()
verifies that every net connects at least two pins and that no pin is used twice.
"""
from collections import defaultdict

# ESP32-DevKitC (38 pin, USB at the bottom). Top to bottom, as seen from the component side.
ESP_LEFT = ["3V3", "EN", "IO36", "IO39", "IO34", "IO35", "IO32", "IO33", "IO25", "IO26", "IO27", "IO14", "IO12", "GND",
            "IO13", "SD2", "SD3", "CMD", "5V"]
ESP_RIGHT = ["GND", "IO23", "IO22", "TX0", "RX0", "IO21", "GND", "IO19", "IO18", "IO5", "IO17", "IO16", "IO4", "IO0",
             "IO2", "IO15", "SD1", "SD0", "CLK"]

# what each ESP32 pin does (unlisted pins stay unconnected)
ESP_FUNC = {
    "IO13": "STEP1", "IO4": "DIR1",
    "IO14": "STEP2", "IO16": "DIR2",
    "IO27": "STEP3", "IO17": "DIR3",
    "IO26": "STEP4", "IO18": "DIR4",
    "IO25": "STEP5", "IO19": "DIR5",
    "IO33": "STEP6", "IO23": "DIR6",
    "IO32": "EN_ALL",
    "IO5": "UARTA_TX", "IO34": "UARTA",          # TX through R1 (1k) onto bus A, RX direct
    "IO15": "UARTB_TX", "IO35": "UARTB",
    "IO21": "SDA", "IO22": "SCL",
    "IO36": "HOME_GRIP",                           # input only, 10k pull-up on the board
    "IO39": "STOP_IN",                             # input only, 10k pull-up; optional stop button
    "3V3": "+3V3", "GND": "GND",
}
ESP_NOTES = {
    "IO5": "strapping pin, idles high: safe as UART TX", "IO15": "strapping pin, idles high: safe as UART TX",
    "IO34": "input only", "IO35": "input only", "IO36": "input only, no internal pull-up",
    "IO39": "input only, no internal pull-up", "IO12": "left free: must be low at boot",
    "IO2": "left free: on-board LED, boot strap", "IO0": "left free: BOOT button", "TX0": "USB serial to the Pi",
    "RX0": "USB serial to the Pi", "5V": "not used: the ESP32 is powered over USB from the Pi",
}

# joint -> (driver ref, UART bus, address 0-3, motor)
DRIVERS = [
    ("J1", "U1", "A", 0, "17HS08 base yaw"),
    ("J2", "U2", "A", 1, "17HS8401 shoulder"),
    ("J3", "U3", "A", 2, "17HS13 elbow"),
    ("J4", "U4", "A", 3, "17HS13 wrist pitch"),
    ("J5", "U5", "B", 0, "17HS08 wrist roll"),
    ("J6", "U6", "B", 1, "28BYJ-48 gripper (bipolar mod)"),
]
# TMC2209 StepStick, component side, pins top to bottom (check your module's silkscreen)
TMC_LEFT = ["EN", "MS1", "MS2", "PDN_UART", "NC", "CLK", "STEP", "DIR"]
TMC_RIGHT = ["VM", "GND", "B2", "B1", "A1", "A2", "VIO", "GND"]

PI_PINS = {  # Raspberry Pi 4 40-pin header pins used
    1: ("3V3", "+3V3_PI"), 3: ("GPIO2 SDA1", "PI_SDA"), 5: ("GPIO3 SCL1", "PI_SCL"), 9: ("GND", "GND"),
    11: ("GPIO17", "BTN_UP"), 13: ("GPIO27", "BTN_OK"), 15: ("GPIO22", "BTN_DOWN"), 14: ("GND", "GND"),
}


def build():
    """Returns (parts, nets). parts: ref -> dict(value, pins: {pin: net}). nets: name -> [(ref, pin)]."""
    parts = {}

    def part(ref, value, pins, note=""):
        parts[ref] = {"value": value, "pins": dict(pins), "note": note}

    # power entry
    part("J_PWR", "DC jack 5.5/2.1, 24 V", {"+": "VIN_24", "-": "GND"})
    part("F1", "Fuse 5 A slow", {"1": "VIN_24", "2": "VIN_24F"})
    part("SW1", "Rocker switch", {"1": "VIN_24F", "2": "+24V"})
    part("U_BUCK", "Buck 24 V -> 5 V 5 A", {"IN+": "+24V", "IN-": "GND", "OUT+": "+5V_PI", "OUT-": "GND"})
    part("J_PIPWR", "USB-C pigtail to the Pi", {"VBUS": "+5V_PI", "GND": "GND"})
    part("J_24", "24 V in (perfboard pads)", {"+": "+24V", "-": "GND"})
    # ESP32
    esp = {}
    for p in ESP_LEFT + ESP_RIGHT:
        if p in ESP_FUNC:
            esp[p] = ESP_FUNC[p]
    esp["USB"] = "USB_ESP"
    parts["U_ESP"] = {"value": "ESP32-DevKitC 38-pin", "pins": esp, "note": ""}
    # UART resistors and pull-ups
    part("R1", "1 k", {"1": "UARTA_TX", "2": "UARTA"})
    part("R2", "1 k", {"1": "UARTB_TX", "2": "UARTB"})
    part("R3", "10 k", {"1": "HOME_GRIP", "2": "+3V3"})
    part("R4", "10 k", {"1": "STOP_IN", "2": "+3V3"})
    # drivers, capacitors, motor connectors
    for i, (j, ref, bus, addr, motor) in enumerate(DRIVERS, 1):
        ms1 = "+3V3" if addr & 1 else "GND"
        ms2 = "+3V3" if addr & 2 else "GND"
        part(ref, f"TMC2209 ({j}, bus {bus}, addr {addr})", {
            "EN": "EN_ALL", "MS1": ms1, "MS2": ms2, "PDN_UART": f"UART{bus}", "STEP": f"STEP{i}", "DIR": f"DIR{i}",
            "VM": "+24V", "GND": "GND", "VIO": "+3V3", "A1": f"M{i}_A1", "A2": f"M{i}_A2", "B1": f"M{i}_B1", "B2": f"M{i}_B2"})
        part(f"C{i}", "100 µF 35 V", {"+": "+24V", "-": "GND"})
        part(f"M{i}", f"JST-XH 4 -> {motor}", {"1": f"M{i}_A1", "2": f"M{i}_A2", "3": f"M{i}_B1", "4": f"M{i}_B2"})
    # sensor hub
    part("J_I2C", "Hub cable (JST-XH 5)", {"1": "+3V3", "2": "GND", "3": "SDA", "4": "SCL", "5": "HOME_GRIP"})
    part("J_HUB", "Hub cable (JST-XH 5)", {"1": "+3V3", "2": "GND", "3": "SDA", "4": "SCL", "5": "HOME_GRIP"})
    mux = {"VIN": "+3V3", "GND": "GND", "SDA": "SDA", "SCL": "SCL", "A0": "GND", "A1": "GND", "A2": "GND", "RST": "+3V3"}
    for ch in range(4):
        mux[f"SD{ch}"] = f"SDA{ch}"
        mux[f"SC{ch}"] = f"SCL{ch}"
    part("U_MUX", "TCA9548A breakout (0x70)", mux)
    for ch, j in enumerate(("J1", "J2", "J3", "J4")):
        part(f"S{ch + 1}", f"JST-XH 4 -> AS5600 {j}", {"1": "+3V3", "2": "GND", "3": f"SDA{ch}", "4": f"SCL{ch}"})
        part(f"ENC{ch + 1}", f"AS5600 board ({j})", {"VCC": "+3V3", "GND": "GND", "SDA": f"SDA{ch}", "SCL": f"SCL{ch}",
                                                     "DIR": "GND"}, note="set the board to 3.3 V")
    part("S5", "JST-XH 2 -> gripper home switch", {"1": "HOME_GRIP", "2": "GND"})
    part("SW_HOME", "Micro switch (NO)", {"COM": "GND", "NO": "HOME_GRIP"})
    part("SW_STOP", "Stop button (optional, NO)", {"1": "STOP_IN", "2": "GND"})
    # Pi side
    pi = {str(n): net for n, (_, net) in PI_PINS.items()}
    pi.update({"USB-C": "+5V_PI", "USB_A1": "USB_ESP", "USB_A2": "USB_CAM"})
    part("U_PI", "Raspberry Pi 4 Model B 1 GB", pi)
    part("U_OLED", '1.3" SH1106 OLED (I2C 0x3C)', {"VCC": "+3V3_PI", "GND": "GND", "SCL": "PI_SCL", "SDA": "PI_SDA"})
    for name, net in (("SW_UP", "BTN_UP"), ("SW_OK", "BTN_OK"), ("SW_DOWN", "BTN_DOWN")):
        part(name, "12 mm tactile", {"1": net, "2": "GND"})
    part("U_CAM", "Webcam (USB)", {"USB": "USB_CAM"})
    nets = defaultdict(list)
    for ref, p in parts.items():
        for pin, net in p["pins"].items():
            nets[net].append((ref, pin))
    return parts, dict(nets)


def check():
    parts, nets = build()
    problems = []
    for net, conns in nets.items():
        if len(conns) < 2:
            problems.append(f"net {net} has a single connection {conns}")
    used = defaultdict(list)
    for f, net in ESP_FUNC.items():
        if f not in ESP_LEFT + ESP_RIGHT:
            problems.append(f"ESP32 pin {f} does not exist")
    for ref, *_ in [(d[1],) for d in DRIVERS]:
        pass
    addrs = defaultdict(list)
    for j, ref, bus, addr, _ in DRIVERS:
        addrs[(bus, addr)].append(ref)
    for k, v in addrs.items():
        if len(v) > 1:
            problems.append(f"UART address clash {k}: {v}")
    return parts, nets, problems


if __name__ == "__main__":
    parts, nets, problems = check()
    print(f"{len(parts)} parts, {len(nets)} nets; problems: {problems or 'none'}")
