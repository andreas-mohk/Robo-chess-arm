# Chess Robot Arm

From-scratch articulated arm that plays chess against Ekke on a physical board.
Concept drawings: [`docs/diagrams.html`](docs/diagrams.html) (open in a browser; interactive reach/IK view).

## Fixed decisions
- **Arm:** base yaw (J1), shoulder (J2), elbow (J3), wrist pitch (J4), wrist roll (J5), two-finger gripper (J6). 6 motors, 6 × TMC2209.
- **Actuators:** steppers on every joint, self-built printed cycloidal reducers. No hobby servos.
- **Board:** 40 × 40 cm, 5 cm squares. Arm base 10 cm from the midpoint of one edge (arm plays Black, behind rank 8).
- **Vision:** fixed webcam, straight down from ~60 cm.
- **Compute:** Raspberry Pi 5 4 GB (vision, Stockfish, game logic, OLED menu) + ESP32 (real-time steps), UART/USB link.
- **CAD:** CadQuery, parameterised; export STLs at the end.
- **Budget:** ~€300 excluding webcam and chess set.

## Geometry (working assumptions)
| Item | Value |
|---|---|
| Upper arm / forearm | 28 / 28 cm (reach 56 cm) |
| Shoulder axis height | 18 cm |
| Wrist axis → fingertips | 15 cm (incl. roll joint) |
| Grip height / carry lift | 3 cm / +10 cm |
| Nearest square (d8/e8) | 12.7 cm, elbow folds to ~26° |
| Far corner (a1/h1) | 50.6 cm, 90 % extension (92 % at carry height) |
| Shoulder torque | ~7 Nm stretched incl. roll wrist → design for 10 Nm |

Joint ranges needed over all squares + capture tray (from diagrams.html):
J1 −54…+78°, J2 +25…+111°, J3 −154…−46°, J4 −78…−13°, J5 ±90°.

## Shoulder drive (J2), `cad/shoulder_drive.py`
NEMA 17 → twin eccentric cam → two 20-lobe cycloid discs (180° apart, for balance) in 21 ring pins → 6 output pins → output flange in a 6806 → clamp, upper arm bolts to the clamp.
Run `python3 cad/shoulder_drive.py`: checks disc/pin interference at 6 input angles, exports STEP + STL per part to `cad/out/` (not committed).
Key parameters: pin circle Ø60, pins Ø5, eccentricity 1.2, profile clearance 0.15, discs 2 × 6 mm, output pins on Ø38, housing Ø84, stack 37 mm.
Printed parts: motor_plate, housing_ring, cycloid_disc_a, cycloid_disc_b, cam, output_flange, output_cap, output_clamp.

Hardware per shoulder drive:
| Qty | Part |
|---|---|
| 21 | Ø5 × 20 dowel pins (ring) |
| 6 | Ø5 × 18 dowel pins (output) |
| 2 | 6802 bearing (15 × 24 × 5) |
| 1 | 6806 bearing (30 × 42 × 7) |
| 6 | M3 × 35 + nut (stack) |
| 4 | M3 × 8 (motor) |
| 4 | M3 × 10 (clamp) |
| 1 | NEMA 17 long-body, ~0.65 Nm, 5 mm D-shaft |

Not yet in the model: shaft support at the output end, mount to the base yoke, spring counterbalance anchor, AS5600 magnet pocket.

## Design decisions (rev B)
1. **Elbow fold (~26°):** offset elbow, with the forearm running beside the upper arm instead of in line with it, so the two can pass each other. Mount the elbow motor on the upper arm behind the shoulder axis, belted to the elbow reducer, where it also acts as a counterweight.
2. **Far-corner margin:** shoulder axis raised from 12 to 18 cm (the base gets taller; no torque cost). Keeps a1 at carry height at 92 % even with the longer roll wrist (15 cm). Fallback: forearm 30 cm.
3. **Shoulder torque:** long-body NEMA 17 (~0.65 Nm) plus a spring counterbalance at the shoulder; keep 20:1. Fallback: 30:1.
4. **Motor count:** resolved, 5th motor = wrist roll (NEMA 14 or pancake NEMA 17). Add a 6th TMC2209.
5. **Homing:** AS5600 magnetic encoder on each joint output, giving absolute position at power-up and step-loss detection. Gripper homes by closing to a switch.

## Log
- 2026-11-10: Project started. Concept diagrams (layout, IK side view, cycloid animation, system, turn sequence).
- 2026-11-10: Decided 5th motor = wrist roll. Adopted answers to questions 1–5 (rev B): offset elbow, elbow motor behind shoulder, shoulder at 18 cm, long-body shoulder motor + spring counterbalance, AS5600 per joint.
- 2026-11-10: First CadQuery model of the shoulder drive; no interference at 6 test angles.

## Next step
Test print of the shoulder drive (discs + ring + plate) to check fits and backlash, then add the AS5600 magnet pocket and the base-yoke mount.
