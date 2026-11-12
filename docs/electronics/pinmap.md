# Controller electronics: pin map

Generated from `electronics/netlist.py` (the schematic and perfboard layout use the same file).

## ESP32-DevKitC (38 pin)

| Header | Pin | Function / net | Notes |
|---|---|---|---|
| left | 3V3 | +3V3 |  |
| left | EN | - |  |
| left | IO36 | HOME_GRIP | input only, no internal pull-up |
| left | IO39 | STOP_IN | input only, no internal pull-up |
| left | IO34 | UARTA | input only |
| left | IO35 | UARTB | input only |
| left | IO32 | EN_ALL |  |
| left | IO33 | STEP6 |  |
| left | IO25 | STEP5 |  |
| left | IO26 | STEP4 |  |
| left | IO27 | STEP3 |  |
| left | IO14 | STEP2 |  |
| left | IO12 | - | left free: must be low at boot |
| left | GND | GND |  |
| left | IO13 | STEP1 |  |
| left | SD2 | - |  |
| left | SD3 | - |  |
| left | CMD | - |  |
| left | 5V | - | not used: the ESP32 is powered over USB from the Pi |
| right | GND | GND |  |
| right | IO23 | DIR6 |  |
| right | IO22 | SCL |  |
| right | TX0 | - | USB serial to the Pi |
| right | RX0 | - | USB serial to the Pi |
| right | IO21 | SDA |  |
| right | GND | GND |  |
| right | IO19 | DIR5 |  |
| right | IO18 | DIR4 |  |
| right | IO5 | UARTA_TX | strapping pin, idles high: safe as UART TX |
| right | IO17 | DIR3 |  |
| right | IO16 | DIR2 |  |
| right | IO4 | DIR1 |  |
| right | IO0 | - | left free: BOOT button |
| right | IO2 | - | left free: on-board LED, boot strap |
| right | IO15 | UARTB_TX | strapping pin, idles high: safe as UART TX |
| right | SD1 | - |  |
| right | SD0 | - |  |
| right | CLK | - |  |

## Stepper drivers (TMC2209, UART mode)

| Joint | Driver | STEP | DIR | UART bus | Address | MS1 | MS2 | Motor | Connector | Current (RMS) |
|---|---|---|---|---|---|---|---|---|---|---|
| J1 | U1 | IO13 | IO4 | A (IO5 via 1k / IO34) | 0 | GND | GND | 17HS08 base yaw | M1 | 0.7 A |
| J2 | U2 | IO14 | IO16 | A (IO5 via 1k / IO34) | 1 | 3V3 | GND | 17HS8401 shoulder | M2 | 1.2 A |
| J3 | U3 | IO27 | IO17 | A (IO5 via 1k / IO34) | 2 | GND | 3V3 | 17HS13 elbow | M3 | 0.9 A |
| J4 | U4 | IO26 | IO18 | A (IO5 via 1k / IO34) | 3 | 3V3 | 3V3 | 17HS13 wrist pitch | M4 | 0.9 A |
| J5 | U5 | IO25 | IO19 | B (IO15 via 1k / IO35) | 0 | GND | GND | 17HS08 wrist roll | M5 | 0.7 A |
| J6 | U6 | IO33 | IO23 | B (IO15 via 1k / IO35) | 1 | 3V3 | GND | 28BYJ-48 gripper (bipolar mod) | M6 | 0.15 A |

All drivers share EN (IO32, active low). Motor connector pins: 1-2 = coil A, 3-4 = coil B.
Find the coil pairs with a multimeter (a few ohms between the two wires of one coil).
28BYJ-48: cut the PCB trace to the red wire; blue/pink = one coil, yellow/orange = the other.

## Raspberry Pi 4 (40-pin header)

| Pin | Signal | Net | Goes to |
|---|---|---|---|
| 1 | 3V3 | +3V3_PI | OLED VCC |
| 3 | GPIO2 SDA1 | PI_SDA | OLED SDA |
| 5 | GPIO3 SCL1 | PI_SCL | OLED SCL |
| 9 | GND | GND | OLED GND, buttons |
| 11 | GPIO17 | BTN_UP | button UP (to GND) |
| 13 | GPIO27 | BTN_OK | button OK (to GND) |
| 14 | GND | GND | OLED GND, buttons |
| 15 | GPIO22 | BTN_DOWN | button DOWN (to GND) |

USB-C: 5 V from the buck converter (pigtail). USB-A: ESP32 (serial + its power), webcam.

## Sensor hub (TCA9548A, address 0x70)

| Channel | Connector | Sensor |
|---|---|---|
| SD0/SC0 | S1 | AS5600 J1 |
| SD1/SC1 | S2 | AS5600 J2 |
| SD2/SC2 | S3 | AS5600 J3 |
| SD3/SC3 | S4 | AS5600 J4 |

S5 = gripper home switch (HOME_GRIP, active low, 10k pull-up on the main board).
J_I2C (main board) <-> J_HUB (hub): 1 = +3V3, 2 = GND, 3 = SDA, 4 = SCL, 5 = HOME_GRIP.

## Power

- 24 V 5 A brick -> panel jack -> 5 A slow fuse -> rocker switch -> +24V.
- +24V feeds the six drivers (VM, 100 µF each at the driver) and the buck converter.
- Buck set to 5.1 V -> USB-C pigtail -> Pi. The Pi powers the ESP32 over USB; the ESP32's 3.3 V feeds driver logic, hub and sensors.
- One common ground for everything.

## Bring-up order (no motors connected until step 5)

1. Continuity check: +24V, +3V3 and GND not shorted to each other.
2. Power the brick with no modules plugged in; check +24V on the rail and set the buck to 5.1 V.
3. Plug in the ESP32 only (USB from a PC): flash, check STEP/DIR toggle on a meter or LED.
4. Plug in the drivers (orientation!), power 24 V: read each driver's version register over UART.
5. Only then connect one motor at a time, low current first. Never plug or unplug a motor with power on.


Netlist check: 49 parts, 67 nets, problems: none.
