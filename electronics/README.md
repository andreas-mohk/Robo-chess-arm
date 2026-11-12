# Controller electronics

Everything here is generated from `netlist.py` (parts, pins, nets, ESP32 pin assignment).

```
cd electronics
python3 netlist.py      # consistency check: every net has 2+ pins, no UART address clash
python3 schematic.py    # out/schematic_1.svg, out/schematic_2.svg (KiCad style)
python3 perfboard.py    # out/perfboard_top.svg, out/perfboard_bottom.svg, out/perfboard_wiring.md
python3 pinmap.py       # out/pinmap.md
```

- **Main board** (90 × 70 mm perfboard in the base): ESP32-DevKitC on sockets, 6 × TMC2209 on sockets,
  6 bulk capacitors, motor connectors, UART resistors, pull-ups, hub and stop connectors.
- **Sensor hub** (small perfboard near the cable passage): TCA9548A breakout, 4 AS5600 connectors, gripper switch.
- **Raspberry Pi 4**: OLED + 3 buttons on its GPIO, ESP32 and webcam on USB, powered from the buck converter.

To change a pin, edit `ESP_FUNC` in `netlist.py` and re-run the scripts. Then check the
DevKit's header spacing (`ESP_COL_L/R` in `perfboard.py`) and the driver pin order against your modules.
