# Main board wiring list

Hole coordinates are (column, row) from the top-left of the component side, 0-based.

| # | Net | From | To | Wire |
|---|---|---|---|---|
| 1 | +3V3 | U_ESP.3V3 (23,3) | +3V3 rail (22,13) | insulated |
| 2 | +3V3 | U1.VIO (0,4) | +3V3 rail (0,13) | insulated |
| 3 | +3V3 | U2.VIO (7,4) | +3V3 rail (7,13) | insulated |
| 4 | +3V3 | U2.MS1 (12,9) | +3V3 rail (12,13) | insulated |
| 5 | +3V3 | U3.VIO (14,4) | +3V3 rail (14,13) | insulated |
| 6 | +3V3 | U3.MS2 (19,8) | +3V3 rail (19,13) | insulated |
| 7 | +3V3 | U4.MS1 (0,15) | +3V3 rail (0,13) | insulated |
| 8 | +3V3 | U4.MS2 (0,16) | +3V3 rail (0,13) | insulated |
| 9 | +3V3 | U4.VIO (5,20) | +3V3 rail (5,13) | insulated |
| 10 | +3V3 | U5.VIO (12,20) | +3V3 rail (12,13) | insulated |
| 11 | +3V3 | U6.MS1 (14,15) | +3V3 rail (14,13) | insulated |
| 12 | +3V3 | U6.VIO (19,20) | +3V3 rail (19,13) | insulated |
| 13 | +3V3 | R3.2 (29,10) | +3V3 rail (22,13) | insulated |
| 14 | +3V3 | R4.2 (29,12) | +3V3 rail (22,13) | short bare link to rail |
| 15 | +3V3 | J_I2C.1 (20,25) | +3V3 rail (20,13) | insulated |
| 16 | HOME_GRIP | U_ESP.IO36 (23,5) | R3.1 (25,10) | insulated |
| 17 | HOME_GRIP | R3.1 (25,10) | J_I2C.5 (24,25) | insulated |
| 18 | STOP_IN | U_ESP.IO39 (23,6) | R4.1 (25,12) | insulated |
| 19 | STOP_IN | R4.1 (25,12) | J_STOP.1 (31,25) | insulated |
| 20 | UARTA | U_ESP.IO34 (23,7) | U3.PDN_UART (19,7) | insulated |
| 21 | UARTA | U3.PDN_UART (19,7) | U2.PDN_UART (12,7) | insulated |
| 22 | UARTA | U2.PDN_UART (12,7) | U1.PDN_UART (5,7) | insulated |
| 23 | UARTA | U1.PDN_UART (5,7) | U4.PDN_UART (0,17) | insulated |
| 24 | UARTA | U4.PDN_UART (0,17) | R1.2 (29,6) | insulated |
| 25 | UARTB | U_ESP.IO35 (23,8) | R2.2 (29,8) | insulated |
| 26 | UARTB | R2.2 (29,8) | U6.PDN_UART (14,17) | insulated |
| 27 | UARTB | U6.PDN_UART (14,17) | U5.PDN_UART (7,17) | insulated |
| 28 | EN_ALL | U_ESP.IO32 (23,9) | U3.EN (19,10) | insulated |
| 29 | EN_ALL | U3.EN (19,10) | U6.EN (14,14) | insulated |
| 30 | EN_ALL | U6.EN (14,14) | U2.EN (12,10) | insulated |
| 31 | EN_ALL | U2.EN (12,10) | U5.EN (7,14) | insulated |
| 32 | EN_ALL | U5.EN (7,14) | U1.EN (5,10) | insulated |
| 33 | EN_ALL | U1.EN (5,10) | U4.EN (0,14) | insulated |
| 34 | STEP6 | U_ESP.IO33 (23,10) | U6.STEP (14,20) | insulated |
| 35 | STEP5 | U_ESP.IO25 (23,11) | U5.STEP (7,20) | insulated |
| 36 | STEP4 | U_ESP.IO26 (23,12) | U4.STEP (0,20) | insulated |
| 37 | STEP3 | U_ESP.IO27 (23,13) | U3.STEP (19,4) | insulated |
| 38 | STEP2 | U_ESP.IO14 (23,14) | U2.STEP (12,4) | insulated |
| 39 | GND | U_ESP.GND (23,16) | GND rail (22,12) | insulated |
| 40 | GND | U_ESP.GND (33,9) | GND rail (22,12) | insulated |
| 41 | GND | U1.GND (0,3) | GND rail (0,12) | insulated |
| 42 | GND | U1.GND (0,9) | GND rail (0,12) | insulated |
| 43 | GND | U1.MS2 (5,8) | GND rail (5,12) | insulated |
| 44 | GND | U1.MS1 (5,9) | GND rail (5,12) | insulated |
| 45 | GND | U2.GND (7,3) | GND rail (7,12) | insulated |
| 46 | GND | U2.GND (7,9) | GND rail (7,12) | insulated |
| 47 | GND | U2.MS2 (12,8) | GND rail (12,12) | insulated |
| 48 | GND | U3.GND (14,3) | GND rail (14,12) | insulated |
| 49 | GND | U3.GND (14,9) | GND rail (14,12) | insulated |
| 50 | GND | U3.MS1 (19,9) | GND rail (19,12) | insulated |
| 51 | GND | U4.GND (5,15) | GND rail (5,12) | insulated |
| 52 | GND | U4.GND (5,21) | GND rail (5,12) | insulated |
| 53 | GND | U5.MS1 (7,15) | GND rail (7,12) | insulated |
| 54 | GND | U5.MS2 (7,16) | GND rail (7,12) | insulated |
| 55 | GND | U5.GND (12,15) | GND rail (12,12) | insulated |
| 56 | GND | U5.GND (12,21) | GND rail (12,12) | insulated |
| 57 | GND | U6.MS2 (14,16) | GND rail (14,12) | insulated |
| 58 | GND | U6.GND (19,15) | GND rail (19,12) | insulated |
| 59 | GND | U6.GND (19,21) | GND rail (19,12) | insulated |
| 60 | GND | J_24.- (22,1) | GND rail (22,12) | insulated |
| 61 | GND | J_I2C.2 (21,25) | GND rail (21,12) | insulated |
| 62 | GND | J_STOP.2 (32,25) | GND rail (22,12) | insulated |
| 63 | STEP1 | U_ESP.IO13 (23,17) | U1.STEP (5,4) | insulated |
| 64 | DIR6 | U_ESP.IO23 (33,4) | U6.DIR (14,21) | insulated |
| 65 | SCL | U_ESP.IO22 (33,5) | J_I2C.4 (23,25) | insulated |
| 66 | SDA | U_ESP.IO21 (33,8) | J_I2C.3 (22,25) | insulated |
| 67 | DIR5 | U_ESP.IO19 (33,10) | U5.DIR (7,21) | insulated |
| 68 | DIR4 | U_ESP.IO18 (33,11) | U4.DIR (0,21) | insulated |
| 69 | UARTA_TX | U_ESP.IO5 (33,12) | R1.1 (25,6) | insulated |
| 70 | DIR3 | U_ESP.IO17 (33,13) | U3.DIR (19,3) | insulated |
| 71 | DIR2 | U_ESP.IO16 (33,14) | U2.DIR (12,3) | insulated |
| 72 | DIR1 | U_ESP.IO4 (33,15) | U1.DIR (5,3) | insulated |
| 73 | UARTB_TX | U_ESP.IO15 (33,18) | R2.1 (25,8) | insulated |
| 74 | M1_A2 | U1.A2 (0,5) | M1.2 (1,0) | insulated |
| 75 | M1_A1 | M1.1 (0,0) | U1.A1 (0,6) | insulated |
| 76 | M1_B1 | U1.B1 (0,7) | M1.3 (2,0) | insulated |
| 77 | M1_B2 | U1.B2 (0,8) | M1.4 (3,0) | insulated |
| 78 | +24V | U1.VM (0,10) | +24V rail (0,11) | short bare link to rail |
| 79 | +24V | U2.VM (7,10) | +24V rail (7,11) | short bare link to rail |
| 80 | +24V | U3.VM (14,10) | +24V rail (14,11) | short bare link to rail |
| 81 | +24V | U4.VM (5,14) | +24V rail (5,11) | insulated |
| 82 | +24V | U5.VM (12,14) | +24V rail (12,11) | insulated |
| 83 | +24V | U6.VM (19,14) | +24V rail (19,11) | insulated |
| 84 | +24V | J_24.+ (20,1) | +24V rail (20,11) | insulated |
| 85 | M2_A2 | U2.A2 (7,5) | M2.2 (8,0) | insulated |
| 86 | M2_A1 | M2.1 (7,0) | U2.A1 (7,6) | insulated |
| 87 | M2_B1 | U2.B1 (7,7) | M2.3 (9,0) | insulated |
| 88 | M2_B2 | U2.B2 (7,8) | M2.4 (10,0) | insulated |
| 89 | M3_A2 | U3.A2 (14,5) | M3.2 (15,0) | insulated |
| 90 | M3_A1 | M3.1 (14,0) | U3.A1 (14,6) | insulated |
| 91 | M3_B1 | U3.B1 (14,7) | M3.3 (16,0) | insulated |
| 92 | M3_B2 | U3.B2 (14,8) | M3.4 (17,0) | insulated |
| 93 | M4_B2 | U4.B2 (5,16) | M4.4 (5,25) | insulated |
| 94 | M4_B1 | M4.3 (4,25) | U4.B1 (5,17) | insulated |
| 95 | M4_A1 | M4.1 (2,25) | U4.A1 (5,18) | insulated |
| 96 | M4_A2 | M4.2 (3,25) | U4.A2 (5,19) | insulated |
| 97 | M5_B2 | U5.B2 (12,16) | M5.4 (12,25) | insulated |
| 98 | M5_B1 | M5.3 (11,25) | U5.B1 (12,17) | insulated |
| 99 | M5_A1 | M5.1 (9,25) | U5.A1 (12,18) | insulated |
| 100 | M5_A2 | M5.2 (10,25) | U5.A2 (12,19) | insulated |
| 101 | M6_B2 | U6.B2 (19,16) | M6.4 (19,25) | insulated |
| 102 | M6_B1 | M6.3 (18,25) | U6.B1 (19,17) | insulated |
| 103 | M6_A1 | M6.1 (16,25) | U6.A1 (19,18) | insulated |
| 104 | M6_A2 | M6.2 (17,25) | U6.A2 (19,19) | insulated |
