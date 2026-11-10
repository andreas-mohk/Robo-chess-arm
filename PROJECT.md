# Chess Robot Arm

From-scratch articulated arm that plays chess against Ekke on a physical board.

- **3D model:** [`docs/arm3d.html`](docs/arm3d.html) (pose joints, jump to squares, play a move)
- **CAD sources:** [`cad/`](cad/) (see [`cad/README.md`](cad/README.md) for how to change parameters)
- **Last build report:** [`docs/build_report.md`](docs/build_report.md) · **Bill of materials:** [`docs/bom.md`](docs/bom.md)
- Concept sheet (rev B, partly superseded): [`docs/diagrams.html`](docs/diagrams.html)

## Fixed decisions
- **Arm:** base yaw (J1), shoulder (J2), elbow (J3), wrist pitch (J4), wrist roll (J5), two-finger gripper (J6). 6 motors, 6 × TMC2209.
- **Actuators:** steppers everywhere, printed two-disc cycloidal reducers on J1–J4. No hobby servos.
- **Board:** 40 × 40 cm, 5 cm squares. Yaw axis 10 cm from the midpoint of one edge (arm plays Black, behind rank 8).
- **Vision:** fixed webcam, straight down from ~60 cm.
- **Compute:** Raspberry Pi 5 4 GB (vision, Stockfish, game logic, OLED menu) + ESP32 (step generation), UART/USB.
- **CAD:** CadQuery, fully parameterised (`cad/config.py`, `cad/hardware.py`); STLs exported by `cad/build.py`.
- **Budget:** ~€300 excluding webcam and chess set.

## Architecture (rev C)
Every joint J1–J4 uses the same module:
**motor → 20T/40T GT2 belt (2:1) → hollow input shaft with two eccentrics → two 20-lobe discs in 21 ring pins (20:1) → output flange in its output bearing → next link.**
A printed rod on the output flange runs back through the hollow input shaft and carries a magnet, so an **AS5600 behind the pulley reads the output angle directly** (absolute position at power-up, catches missed steps).

- The drive's back cover bolts straight onto a carrier plate; pulley, belt and sensor sit on the far side of the plate.
- **Motors are moved off the joints:** J2's motor sits on the tower, J3's motor rides on the upper arm behind the shoulder (as a counterweight), and J4's motor rides on the forearm behind the elbow. J1's motor hangs below the base top. The wrist only carries the roll motor and the gripper.
- **Links:** 15 × 15 × 1.5 aluminium tube with printed end fittings, so no part is longer than the print bed.
- **Offset elbow:** the forearm runs beside the upper arm, so the elbow can fold to 25° for the squares nearest the base.
- **Base:** printed box with the Pi, the ESP32 board and the buck converter inside. The OLED and 3 buttons face the board. A 6 mm ball race carries the turntable. Power comes from an external 24 V brick, so there is no mains wiring inside.
- **Wrist:** pancake NEMA 17 roll (direct drive) and a rack-and-pinion parallel gripper on 4 mm rods, driven by a 28BYJ-48. The jaws close along a board diagonal, where there is the most room between pieces.
- **J4 drive** is a smaller version (15:1, Ø68, 6804 output).

## Key numbers (from the last build)
| Item | Value |
|---|---|
| Upper arm / forearm | 28 / 28 cm |
| Shoulder axis height | 23 cm above the table |
| J4 axis → fingertips | 15.4 cm |
| Gripper offset from the yaw axis (sideways) | 5.5 cm (handled by the IK) |
| Reach | all 64 squares + capture tray, max 91 % extension, tightest elbow fold 25° |
| Joint ranges | J1 −67…+69°, J2 +22…+107°, J3 −155…−50°, J4 −73…+3°, J5 −68…+85° |
| Total ratio J1–J3 / J4 | 40:1 / 30:1 |
| Gravity torque ×1.3 vs capacity | J2 4.5 / 9.4 Nm (2.1×), J3 1.4 / 5.0 Nm (3.7×) |
| Link masses | upper 0.58 kg, forearm 0.47 kg, wrist + gripper 0.27 kg |
| Belts | J1 180, J2 232, J3 800, J4 800 mm closed GT2-6 |
| Printed parts | 59, all fit a 220 × 220 × 250 bed |
| Estimated cost | ≈ €302 (see bom.md) |

## Checks the build runs
Drive parameters (walls, undercut, pin lengths), cycloid meshing at 6 angles per drive, reach for every target, IK vs the assembled model, gravity torque per joint, print-bed fit, and a collision sweep: 13 poses including park, against the table, the board and worst-case tall pieces on neighbouring squares. The parts inside the base are checked too. Current status: **all clear**.

## Design decisions log
- **rev B:** wrist roll as 5th motor, offset elbow, elbow motor behind the shoulder, AS5600 per joint.
- **rev C (full CAD):**
  - Belt input on every drive. This makes the sensor-through-hollow-shaft possible and doubles the ratio, so standard motors are enough. No spring counterbalance and no long-body motor needed (J2 margin 2.1× with a 48 mm motor).
  - Shoulder raised to 23 cm. The J3 tail motor needs clearance over the turntable, and the board's thickness lifts the grip height anyway.
  - Tubes are 15 mm, not 20 mm, so the two links clear each other at the tight elbow fold.
  - Gripper hub lengthened so the gripper clears the J4 drive.
  - J3/J4 motor tails are 90 mm because they snap to a stocked 800 mm belt.

## Open items / to verify at the first test print
- Fits: `fit` (0.15) and `press` (−0.05) in `DriveParams`, printed pulley tooth shape, ring-pin pockets.
- AS5600 board size and hole pitch (assumed 23 × 23 mm, 17 mm) and magnet air gap (1.5 mm).
- Turntable ball race preload (no shim yet).
- Gripper homing switch position (not modelled), cable routing along the links (not modelled).
- Camera pole (not modelled).
- Firmware: ESP32 step generation, AS5600 via TCA9548A, Pi IK = `cad/kinematics.py`.

## Log
- 2026-11-10: Project started. Concept diagrams.
- 2026-11-10: Rev B decisions. First shoulder drive model.
- 2026-11-10: Rev C: complete parametric arm in CadQuery (base, turntable, tower, links, 4 drives, wrist, gripper), build checks, BOM, 3D viewer.

## Next step
First test print when back in the workshop: one J2 drive (back cover, housing ring, both discs, input shaft, pulley, output flange, cap, clamp). Check fits and backlash, then tune `fit` / `press`. Order hardware only after that (needs your OK).
