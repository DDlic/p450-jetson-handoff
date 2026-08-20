# P450 mission V4 — first-principles fix result

Date: 2026-08-20

Owner authorization: `APPROVE_V4_FIRST_PRINCIPLES_FIX`

## Artifact

- Script: `scripts/p450_delivery_poc_mission.py`
- Artifact version logged at runtime: `V4`
- SHA-256: `4d42081c1c4e1355bb49b0dcb4c73df6a7816a9872258b1c8e1b35d73746a4ff`
- Allowed flight envelope remains takeoff height 0.1–1.0 m and forward distance 0–5.0 m.
- The script still never sends normal or force Disarm.

## Resolved first-principles findings

1. **Control ownership:** Armed Offboard-required states now require both `nav_state=OFFBOARD` and `flag_control_offboard_enabled=true`. If PX4/RC selects another mode, the script clears its command/target, stops every publication, sends no Land or Disarm, logs `CONTROL_RELINQUISHED`, and exits 20.
2. **Land confirmation:** Land ACK is recorded but does not stop the heartbeat. The hold stream continues until `nav_state=AUTO_LAND`; only then is `land_mode_confirmed=true`.
3. **Low-altitude heading:** `heading_good_for_control` is diagnostic for this ≤1 m PoC. Finite heading, valid local/global position and velocity, no dead reckoning, estimator flags and active failsafes remain hard gates.
4. **Offline GCS semantics:** Raw `vehicle_status.gcs_connection_lost` is logged as diagnostic. Active `failsafe_flags.gcs_connection_lost`, manual-control loss and vehicle failsafe remain hard gates.
5. **EKF resets:** XY/Z/velocity/heading reset counters are logged. Stored NED position/yaw targets are shifted by PX4 reset deltas. XY resets over 0.25 m or Z resets over 0.20 m request PX4 Land. The forward leg is rebuilt after takeoff hold from the latest position and finite heading.
6. **Storage:** Every active/preflight `--log-root` must resolve below the mounted `/media/p450/P450_DATA` volume.
7. **Evidence:** Heartbeat CSV now includes Offboard enabled, raw/active GCS state, heading diagnostic and reset counters.

PX4's own multicopter position controller uses the same positive-delta correction for position and yaw setpoints after EKF resets:

- https://github.com/PX4/PX4-Autopilot/blob/v1.14.3/src/modules/mc_pos_control/MulticopterPositionControl.cpp

## Verification

- Red phase: the new V4 tests produced 3 failures and 4 errors against V3, reproducing all approved defects.
- Green phase: 34/34 mission and soak tests passed.
- `py_compile`: passed for both scripts and both test files.
- `git diff --check`: passed.
- Dry run: passed with `publishes=0 commands=0` and correct NED geometry.
- No ROS node or MAVLink/vehicle command was started by the test suite.

The live Micro XRCE Agent service was active, but VehicleStatus produced no samples during a six-second read-only rate check. A live `--preflight-only` run was therefore intentionally not recorded; Gate P_D remains the first field action after PX4 telemetry resumes.

## Readiness boundary

V4 is approved as an offline-reviewed candidate, not as a completed flight result. The previous 300-second loaded soak is not repeated. Because flight-control code changed, one no-publish Gate P_D and one propeller-removed Gate G_D must pass before F1_D. F1_D remains the 0.5 m vertical gate; only its success permits F2_D at 1 m and 5 m forward.
