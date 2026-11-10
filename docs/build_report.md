# Chess arm build report

## Layout
  drive heights: {'J1': 40.2, 'J2': 40.2, 'J3': 40.2, 'J4': 36.7}
  x tower / upper arm / forearm / J4 out: (-40.2, 0.0, -40.2, -3.5)
  z base top / turntable top / shoulder: (60.0, 106.4, 230.0)
  tool length 169.5 mm (target 169.5), lateral offset 54.5 mm, J3 motor tail 89.9 mm, J4 motor tail 89.9 mm

## Belts
  J1: GT2 loop 180 mm, centre distance 59.7 mm, 20T -> 40T, motor 17HS08
  J2: GT2 loop 232 mm, centre distance 85.8 mm, 20T -> 40T, motor 17HS8401
  J3: GT2 loop 800 mm, centre distance 369.9 mm, 20T -> 40T, motor 17HS13
  J4: GT2 loop 800 mm, centre distance 369.9 mm, 20T -> 40T, motor 17HS13

## Reach
  J1: -67 .. +69 deg
  J2: +24 .. +111 deg
  J3: -156 .. -49 deg
  J4: -75 .. -4 deg
  J5: -68 .. +85 deg
  max extension 91%, tightest elbow fold 24 deg
  IK verified against the assembled model

## Cycloid meshing (6 input angles per drive)
  J1: worst disc/pin overlap 0.0000 mm3, part overlaps none
  J2: worst disc/pin overlap 0.0000 mm3, part overlaps none
  J3: worst disc/pin overlap 0.0000 mm3, part overlaps none
  J4: worst disc/pin overlap 0.0000 mm3, part overlaps none

## Gripper internals (jaws, racks, frame, switch over the opening range)
  clear at 10 mm, half and full opening

## Camera
  C920 at 600 mm needs 40.3 x 40.3 deg, has 70.4 x 43.3 deg: board fits (covers 847 x 476 mm at the board)

## Torque (gravity over every target pose, gripper vertical)
  link masses: upper 0.58 kg, forearm 0.47 kg, wrist+gripper 0.42 kg, payload 30 g
  joint   gravity(worst)  x1.3 accel   capacity   margin
  J2       4.13 Nm         5.37 Nm     9.36 Nm    1.7x
  J3       1.44 Nm         1.88 Nm     5.04 Nm    2.7x
  J4       0.00 Nm         0.00 Nm     3.78 Nm   1058.6x
  J1 capacity 2.34 Nm (no gravity load; enough for ~16 rad/s^2 on a ~0.15 kg m^2 arm)

## Print bed
  63 printed parts, all fit (220.0, 220.0, 250.0) mm

## Collision sweep (arm groups, table, board, neighbouring pieces)
  d8: clear
  d8 carry: clear
  e8: clear
  a8: clear
  h8: clear
  a1: clear
  a1 carry: clear
  h1: clear
  h1 carry: clear
  e4: clear
  tray: clear
  tray carry: clear
  park: clear
  parked arm is out of the camera's view of the board
  inside the base: clear

## Cost
  estimated total EUR 338 incl. spares and packs (budget EUR 300), see out/bom_sourcing.csv

## Export
  exported 63 printed parts (STL + STEP), assembly STEP, 7 GLB groups -> /home/user/Robo-chess-arm/cad/out

## Result
  problems: none
  notes: estimated cost EUR 338 is over the EUR 300 budget
