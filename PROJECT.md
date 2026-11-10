# Chess Robot Arm

From-scratch articulated arm that plays chess against Ekke on a physical board.
Concept drawings: [`docs/diagrams.html`](docs/diagrams.html) (open in a browser; interactive reach/IK view).

## Fixed decisions
- **Arm:** base yaw (J1), shoulder (J2), elbow (J3), wrist pitch (J4), two-finger gripper (J5).
- **Actuators:** steppers on every joint, self-built printed cycloidal reducers. No hobby servos.
- **Board:** 40 × 40 cm, 5 cm squares. Arm base 10 cm from the midpoint of one edge (arm plays Black, behind rank 8).
- **Vision:** fixed webcam, straight down from ~60 cm.
- **Compute:** Raspberry Pi 5 4 GB (vision, Stockfish, game logic, OLED menu) + ESP32 (real-time steps), UART/USB link. 5 × TMC2209.
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

## Open questions
- Elbow must fold to ~27° for rank-8 squares without links colliding.
- Motor count: handover lists 5 NEMA 17 + gripper motor, but 4 arm joints. Spare or wrist roll?
- Homing: switch or hall sensor per joint (StallGuard unreliable behind reducers).
- Gripper length (shorter helps both reach extremes).
- Ratios for J1, J3, J4.

## Log
- 2026-11-10: Project started. Concept diagrams (layout, IK side view, cycloid animation, system, turn sequence).

## Next step
Shoulder cycloidal drive in CadQuery (NEMA 17, 20:1, 6806 output bearing, all dimensions as parameters).
