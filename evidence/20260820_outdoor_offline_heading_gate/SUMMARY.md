# 2026-08-20 outdoor offline soak, rejected flight attempts, and heading-gate correction

## Scope

This package preserves the complete NX/QGC evidence available for the 2026-08-20 outdoor attempt:

- 300-second disarmed mission-order soak under Moonlight 720p/30 load with external Internet unavailable and eth0/base-station LAN retained.
- Two requested flight modes that were rejected during PRECHECK before any control publication.
- QGC/PX4 baseline, XRCE receive statistics, Reliable trace, EKF follow-up, and the raw ULog from the later manual GPS-mode flight.
- The incorrect assumptions and process deviations discovered after the attempt.
- The corrected mission implementation, regression tests, and the superseding V3 offline card.

No actual flight occurred in either F1 or F2 script attempt. The operator subsequently performed a separate manual GPS-mode flight during the same field session and reported normal flight; that follow-up does not validate the Offboard mission.

The QGC text files preserve all posted commands, fields and values. Trailing spaces and extra blank lines at EOF were normalized for repository hygiene.

## Environment and baseline

- Branch before this evidence commit: `codex/delivery-poc-mission` at `b1bc2380d52c3c51aacdf4c744e86c9e85851d32`.
- NX eth0: `192.168.10.100/24`; base-station LAN remained available.
- External Internet probe failed as intended.
- Micro XRCE Agent remained active with `NRestarts=0`.
- Sunshine remained active and Moonlight was used as operational load.
- PX4 XRCE input was connected and Reliable.
- PX4 parameters remained `COM_OF_LOSS_T=1.0` and `COM_OBL_RC_ACT=0`; no PX4 parameter was changed.

## Gate S: 300-second disarmed loaded soak

TEST_ID: `P450_20260820_OUTDOOR_OFFLINE_DISARMED_SOAK_5M_A`

NX result:

- `SOAK COMPLETE PASS`, exit 0.
- 3042 publishes.
- Maximum local publish gap: 181.068 ms.
- Gaps >150/250/500/1000 ms: 8/0/0/0.
- Vehicle remained disarmed.
- Offboard mode was entered while disarmed.
- Virtual takeoff, hold and forward targets were streamed in mission order.
- PX4 Land mode was confirmed while still disarmed.

PX4 result:

- Offboard RX count: 3042, exactly matching NX publishes.
- Maximum RX gap: 742131 us.
- Gaps >150/250/500 ms: 640/139/7.
- Reliable trace froze on a 335873 us trigger.
- No observed gap reached the configured 1.0 second Offboard-loss timeout.
- Final commander state was STAB, Standby, no failsafe.

Verdict: PASS for the owner-authorized operational continuity gate. It is not a strict 250 ms Gate R PASS; the known PX4 receive-tail risk remains recorded.

## F1 and F2 attempts: no flight occurred

### F1

TEST_ID: `P450_20260820_OUTDOOR_FLIGHT_05M_B`

- Started at approximately 2026-08-20 14:01:36 +08:00.
- PRECHECK recorded arming state 1 and nav state 15.
- Rejected at 302.695 ms with `local/global position or heading is not flight-valid`.
- `HEARTBEAT.csv` contains only its header: publishes=0.
- No Offboard request, setpoint, Arm command, motor command or flight occurred.

A retry reused the same TEST_ID and was correctly rejected by `exist_ok=False` with `FileExistsError`. The original evidence directory was preserved.

### F2

TEST_ID: `P450_20260820_OUTDOOR_FLIGHT_1M_5M_B`

- Started at approximately 2026-08-20 14:02:36 +08:00.
- PRECHECK recorded arming state 1 and nav state 15.
- Rejected at 205.868 ms with the same validity message.
- `HEARTBEAT.csv` contains only its header: publishes=0.
- No Offboard request, setpoint, Arm command, motor command or flight occurred.

## Root cause

The installed PX4 v1.14.3 publishes:

```text
vehicle_local_position.heading_good_for_control = isYawFinalAlignComplete()
```

When magnetometer fusion is active, `isYawFinalAlignComplete()` requires initial yaw alignment plus in-flight magnetic alignment. Therefore this flag normally remains false on the ground and must not be used as a ground arming prerequisite.

Outdoor evidence before the attempts had valid XY/Z position and velocity, valid global origin and Home, finite heading, and no dead reckoning. The mission script nevertheless required `heading_good_for_control=true` during ground PRECHECK and runtime before liftoff, creating a circular deadlock.

The later EKF follow-up showed two healthy EKF instances, a healthy shared magnetometer, and no missed IMU/GPS/magnetometer messages. Its later `xy_valid=false` / `dead_reckoning=true` sample was captured after outdoor positioning was no longer available and is not the state at the rejected attempts.

## Operator follow-up after the rejected attempts

- Propellers were installed during both F1 and F2 command attempts. Both scripts stopped in PRECHECK with publishes=0, so neither script requested Offboard, Arm, motor output or flight.
- After F1/F2 were rejected, the operator manually armed and flew the aircraft in GPS mode. The operator reported normal flight.
- The RC, including mode switching and Kill, was reported normal.
- Moonlight remained connected throughout the 300-second soak, F1/F2 attempts and the later manual flight, with no observed connection instability.
- This follow-up supports basic airframe, RC/Kill, GPS-mode flight and loaded display-link operation. It does not prove corrected Offboard takeoff, final in-flight heading alignment, autonomous forward motion or autonomous landing.
- The PX4 ULog covering the manual flight has now been supplied and machine-verified. A QGC TLog remains optional.

## Manual GPS-mode flight ULog verification

Source: `log_98_2026-8-20-14-06-02.ulg` from `origin/main` commit `5870ddcfe6972b212dace9024c90ce020a8f5566`; SHA-256 `854e82464f004b555cd7056e395b84901258e2714c759f7d52952b9fcf780893`.

- 45.055-second PX4 log, no ULog dropouts, firmware `c7a3947840`.
- Armed by RC in nav state 2 (POSCTL/GPS position mode).
- Takeoff detected at approximately +5.15 s, landing at +42.06 s, automatic landing disarm at +44.06 s.
- No PX4 failsafe, RC loss/failsafe, failure-detector flag, dead reckoning, magnetic fault/disturbance or yaw rejection.
- Both EKF instances completed in-flight magnetic alignment around +15.75/+15.91 s.
- `heading_good_for_control` became true at +16.94 s, about 11.79 s after takeoff, and returned false after landing.
- The alignment occurred after approximately 1.5 m of local vertical change, matching PX4's 1.5 m magnetic-anomaly clearance logic.
- Raw `vehicle_status.gcs_connection_lost` remained true, but PX4 `failsafe=false` and `failsafe_flags.gcs_connection_lost=false` throughout; Moonlight and RC were operator-confirmed stable.

The complete interpretation and caveats are in `ULOG_ANALYSIS_20260820.md`.

Official source references:

- https://github.com/PX4/PX4-Autopilot/blob/v1.14.3/src/modules/ekf2/EKF2.cpp#L1358-L1360
- https://github.com/PX4/PX4-Autopilot/blob/v1.14.3/src/modules/ekf2/EKF/ekf.h#L316-L324

## V3 mission limitation discovered from the ULog

The first correction removed the invalid ground prerequisite but still requires the final-heading flag immediately after reaching the 0.5 m or 1.0 m takeoff target. The ULog and PX4 source show that this remains unsuitable:

- PX4 may wait until estimated HAGL exceeds 1.5 m before in-flight magnetic realignment.
- F1 and F2 are both intentionally below 1.5 m.
- V3 can therefore abort solely because a height-dependent diagnostic cannot become true at the commanded height.
- V3 also independently aborts on raw `vehicle_status.gcs_connection_lost` even when PX4's active GCS failsafe flag remains false in this offline field configuration.

V3 is suspended. The installed flight script has not been weakened or changed as part of this evidence update. A proposed V4 would treat the low-altitude final-heading flag as diagnostic, preserve finite heading and all estimator/failsafe checks, use the latest heading before forward travel, and rely on PX4's active GCS failsafe decision rather than raw link history. That safety-envelope change requires explicit owner approval.

Historical V3 verification remains preserved:

- Mission and soak tests: 26/26 PASS.
- `git diff --check`: PASS.
- V3 mission SHA-256: `32c2360cc533507317ee036707916351a3dff783e0ab93354009e1f4bb33b53b`.
- V3 mission test SHA-256: `a9d27e6e982a3985d49be47e28a426a9247b5a8bcbc72504998fb6bdfa4fee5a`.

## Errors and process deviations preserved

1. V2 displayed `sha256 <hash>` as a label, which could be mistaken for a shell command. V3 uses only the real command `sha256sum <file>`.
2. V2 and the mission implementation incorrectly treated an in-flight final-alignment flag as a ground prerequisite.
3. Gate P and propeller-free Gate G were skipped before requesting F1.
4. The failed F1 TEST_ID was reused once, producing the intended `FileExistsError`.
5. F2 was requested after F1 had failed. It was also rejected before publication.
6. The follow-up QGC command used `estimator_status_flag`; the actual topic name is `estimator_status_flags`.
7. Earlier guidance to wait on the ground for `heading_good_for_control=true` was incorrect for this PX4/magnetometer path.

## Evidence index

- `QGC_OUTDOOR_BASELINE_AND_SOAK_RAW.txt`: complete QGC baseline, soak RX status/trace and final commander state.
- `QGC_EKF_FOLLOWUP_RAW.txt`: complete EKF follow-up as posted.
- `nx/P450_20260820_OUTDOOR_OFFLINE_DISARMED_SOAK_5M_A/`: complete NX soak CSV files.
- `nx/P450_20260820_OUTDOOR_FLIGHT_05M_B/`: complete F1 PRECHECK evidence.
- `nx/P450_20260820_OUTDOOR_FLIGHT_1M_5M_B/`: complete F2 PRECHECK evidence.
- `HEADING_GATE_FIX.diff`: pre-commit implementation diff.
- `TEST_RESULTS.txt`: complete 26-test output.
- `MISSING_DATA.md`: data that only the operator/QGC laptop can still supply.
- `OPERATOR_FOLLOWUP_20260820.md`: operator-confirmed propeller, manual-flight, RC/Kill and Moonlight facts.
- `ULOG_ANALYSIS_20260820.md`: machine analysis, timing, safety state and V3 implications.
- `qgc/log_98_2026-8-20-14-06-02.ulg`: raw PX4 ULog of the later manual GPS-mode flight.
- `MANIFEST.sha256`: checksums for the evidence package.
