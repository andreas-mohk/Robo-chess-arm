# Chess arm CAD

Everything is generated from Python (CadQuery 2.x). Edit a number, rebuild, and every part,
check and export follows.

```
pip install cadquery
cd cad
python3 build.py            # checks + exports, about 6-8 min
python3 build.py --quick    # skip the collision sweep and gear meshing check, about 30 s
python3 build.py --no-export
```

Results land in `cad/out/` (not committed): `report.md`, `bom.md`, `stl/`, `step/`,
`chess_arm_assembly.step`, and `glb/` for the 3D viewer (`docs/arm3d.html`).
The build exits with code 1 if any check fails.

## Where to change things

| You want to change | Edit |
|---|---|
| Link lengths, shoulder height, board position, carry height, print bed size | `config.py` → `Config` |
| A motor (unavailable, too weak, different length) | `config.py` → `joints` (motor key), add new motors to `hardware.py` → `MOTORS` |
| Belt lengths your supplier stocks | `hardware.py` → `GT2_LOOPS` (motors slide to suit) |
| Bearings, AS5600 board size, OLED type, Pi/ESP32 board sizes | `hardware.py` |
| Cycloid ratio, pin sizes, eccentricity, print fits | `config.py` → `BIG` (J1-J3) and `SMALL` (J4) |
| Gripper opening, finger length | `config.py`, gripper internals at the top of `wrist.py` |
| Webcam model, camera height and position, pole position | `config.py` (`webcam`, `camera_h`, `camera_xy`, `pole_xy`), camera sizes in `hardware.py` → `WEBCAMS` |
| Raspberry Pi model | `config.py` → `computer` (`hardware.py` → `COMPUTERS`) |
| Where the arm waits | `config.py` → `park_xyz` |
| Electronics placement in the base | `base.py` → `LAYOUT` |

Fits: `fit` (clearance for printed holes on steel) and `press` (bearing seats) in `DriveParams`.
Tune them after the first test print; every drive picks them up.

## Files

| File | Contents |
|---|---|
| `config.py` | every design parameter |
| `hardware.py` | bought parts catalog, belt maths |
| `cycloidal.py` | generic two-disc cycloidal drive (hollow input, AS5600 rod), its own meshing check |
| `layout.py` | positions derived from the config |
| `joints.py` | joint kit: drive + motor + belt + sensor + the holes in its carrier |
| `base.py` | base box, J1, ball race, turntable, electronics placeholders |
| `links.py` | tower (J2), upper arm (J3 + its motor), forearm (J4 + its motor) |
| `wrist.py` | wrist bracket, J5 roll on a 6804, parallel gripper (J6): LM6UU jaws, rack and pinion, home switch |
| `camera.py` | camera pole, boom, tilting camera plate, field-of-view check |
| `kinematics.py` | inverse kinematics with the real lateral offset, standard poses |
| `assembly.py` | places all groups for given joint angles |
| `build.py` | checks, bill of materials, exports |

## What the build checks

1. Drive parameters: wall thicknesses, undercut, pin lengths (raises with a plain message).
2. Cycloid meshing: both discs against ring and output pins at 6 input angles.
3. Reach: every square and the capture tray, at grip and carry height, under 95% extension.
4. IK against the assembled model: the fingertip must land on the target.
5. Gravity torque per joint over every pose ×1.3, against motor × belt × cycloid × efficiency.
6. Every printed part fits the print bed.
7. Gripper internals: jaws, racks, frame and switch at 10 mm, half and full opening.
8. Camera field of view covers the board plus margin.
9. Collision sweep: 13 poses, all arm groups against each other, the camera pole, the table,
   the board and worst-case tall pieces on the neighbouring squares; the parked arm stays out
   of the camera's view; the parts inside the base don't overlap.
10. Cost estimate against the €300 budget.

## Conventions

World: origin on the table under the yaw axis, +Y towards the board, +Z up.
Arm lateral x: along J2-J4 axes, 0 at the face where the upper arm meets the J2 output.
Joint angles: see `kinematics.py`.
