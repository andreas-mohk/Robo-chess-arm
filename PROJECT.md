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
| Shoulder axis height | 12 cm |
| Wrist axis → fingertips | 12 cm (assumed) |
| Grip height / carry lift | 3 cm / +10 cm |
| Nearest square (d8/e8) | 12.7 cm, elbow folds to ~27° |
| Far corner (a1/h1) | 50.6 cm, 91 % extension (93 % at carry height) |
| Shoulder torque | ~6 Nm stretched → design for 10 Nm |

Joint ranges needed over all squares + capture tray (from diagrams.html):
J1 −54…+78°, J2 +28…+117°, J3 −153…−42°, J4 −83…−27°.

## Shoulder drive (first-pass parameters)
NEMA 17 → eccentric cam → 20-lobe cycloid disc in 21 ring pins → 6 output pins → output flange on 6806 (30×42×7).
Pin circle Ø60, pins Ø5, eccentricity 1.2 mm, output holes Ø7.4 on Ø38. Needs ≈0.6 Nm at the motor for 10 Nm out.

## Proposed answers to open questions (not yet confirmed)
1. **Elbow fold (~27°):** offset elbow, with the forearm running beside the upper arm instead of in line with it, so the two can pass each other. Mount the elbow motor on the upper arm behind the shoulder axis, belted to the elbow reducer, where it also acts as a counterweight.
2. **Far-corner margin:** raise the shoulder axis from 12 to ~18 cm (the base gets taller; no torque cost). Keeps a1 at carry height at 92 % even with the longer roll wrist (15 cm). Fallback: forearm 30 cm.
3. **Shoulder torque:** long-body NEMA 17 (~0.65 Nm) plus a spring counterbalance at the shoulder; keep 20:1. Fallback: 30:1.
4. **Motor count:** resolved, 5th motor = wrist roll (NEMA 14 or pancake NEMA 17). Add a 6th TMC2209.
5. **Homing:** AS5600 magnetic encoder on each joint output, giving absolute position at power-up and step-loss detection. Gripper homes by closing to a switch.

## Log
- 2026-11-10: Project started. Concept diagrams (layout, IK side view, cycloid animation, system, turn sequence).
- 2026-11-10: Decided 5th motor = wrist roll. Proposed answers to open questions 1–5.

## Next step
Shoulder cycloidal drive in CadQuery (NEMA 17, 20:1, 6806 output bearing, all dimensions as parameters).
