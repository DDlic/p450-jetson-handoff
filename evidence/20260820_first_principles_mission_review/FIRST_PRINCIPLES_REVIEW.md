# P450 delivery mission — first-principles review

Date: 2026-08-20

This review evaluates the current flight script without changing its flight-control behavior.

## Reviewed artifact

- Branch commit: `b7fea742f1726c7584db0cc6a558e58904f6f0d3`
- Script: `scripts/p450_delivery_poc_mission.py`
- SHA-256: `32c2360cc533507317ee036707916351a3dff783e0ab93354009e1f4bb33b53b`
- Intended sequence: hold, Offboard, Arm, climb, optional forward waypoint, PX4 Land, auto-disarm.

## Required invariants

An armed autonomous position mission is acceptable only while all of these remain true:

1. PX4 is actually using Offboard control during every Offboard-required phase.
2. The target is expressed in the current valid local-NED frame.
3. The 10 Hz Offboard heartbeat and setpoint stream remains timely.
4. PX4 active failsafes, estimator validity and battery state remain safe.
5. An operator RC mode takeover has priority and cannot be overwritten by a later autonomous command.
6. Heartbeat publication stops only after PX4 has actually entered a non-Offboard landing mode.

## Results

### R1 — FAIL: RC/manual takeover is not recognized

The script confirms `nav_state=OFFBOARD` only while requesting initial entry. During `REQUEST_ARM`, `TAKEOFF`, `HOLD_AFTER_TAKEOFF`, and `MOVE_FORWARD`, it does not require `VehicleStatus.nav_state == OFFBOARD` or `VehicleControlMode.flag_control_offboard_enabled == true`.

The adversarial reproduction changes PX4 to POSCTL while the mission state remains `HOLD_AFTER_TAKEOFF`. `safety_check()` returns no abort, and after two seconds `tick_state()` transitions to `REQUEST_LAND`. The script can therefore issue `VEHICLE_CMD_NAV_LAND` after an operator has deliberately taken over with the RC mode switch.

This violates invariants 1 and 5. It is also inconsistent with the 2026-08-12 field evidence, where Offboard loss fell back to Position and the operator used RC/Kill.

Required correction: if an armed mission leaves Offboard before the script requests Land, immediately relinquish ownership, stop all Offboard/setpoint/command publications, log manual takeover, and exit nonzero without sending Land or Disarm.

### R2 — FAIL: Land ACK is treated as landed-mode confirmation

In `REQUEST_LAND`, either `nav_state=AUTO_LAND` or an ACK result of ACCEPTED/IN_PROGRESS sets `land_mode_confirmed=true`. That flag suppresses the heartbeat immediately.

A command ACK establishes that Commander accepted or started processing the request; it does not prove the output navigation state has already become AUTO_LAND. The adversarial reproduction supplies an accepted ACK while `nav_state` is not AUTO_LAND and proves the script enters `WAIT_LANDED` and stops heartbeat publication.

This violates invariant 6. Required correction: record ACK separately, continue the hold heartbeat, and declare landing-mode confirmation only after `nav_state=AUTO_LAND` (and preferably `flag_control_offboard_enabled=false`).

### R3 — FAIL for the specified 0.5 m/1.0 m route: final-heading hard abort

The script accepts pending final heading on the ground and during `TAKEOFF`, then requires `heading_good_for_control=true` immediately in `HOLD_AFTER_TAKEOFF` and `MOVE_FORWARD`.

The 2026-08-20 manual-flight ULog shows that final alignment became true only after roughly 1.5 m of vertical motion and 11.79 seconds after takeoff detection. PX4 v1.14.3 magnetometer control waits for height-above-ground greater than 1.5 m before the applicable in-flight realignment. Both allowed routes top out at 0.5 m or 1.0 m, so the hard condition may be impossible by construction.

Required correction: retain finite heading, valid local/global position, no dead reckoning, EKF/failsafe checks, and a bounded yaw policy; treat `heading_good_for_control` as a recorded diagnostic for this low-altitude PoC rather than an immediate hard abort. This loosens an existing flight gate and requires explicit owner approval.

### R4 — FAIL for intentional offline operation: raw GCS-history abort

The script checks both PX4's active `failsafe_flags.gcs_connection_lost` and raw `vehicle_status.gcs_connection_lost`. The manual GPS flight recorded raw GCS-lost true throughout while active GCS failsafe, vehicle failsafe, RC loss and RC failsafe all remained false.

For the defined offline mission, aborting on the raw status bit rejects a configuration that PX4 itself does not classify as an active GCS-loss failsafe. Required correction: keep the active failsafe flag and all RC/manual-control checks, but log the raw status as diagnostic only. This loosens an existing flight gate and requires explicit owner approval.

### R5 — FAIL: local-frame resets can invalidate captured targets

The route and fixed yaw are captured once during preflight. `VehicleLocalPosition` exposes XY, Z, velocity and heading reset counters/deltas, but the script neither logs nor reacts to them. An EKF origin/reset event can therefore change the meaning of the stored target while it remains numerically unchanged.

Required correction: snapshot all reset counters; log every change; abort to PX4 Land on a material XY/Z reset while the script still owns Offboard; and recompute the forward goal from the latest accepted position/heading after takeoff hold. Heading reset handling must avoid reintroducing R3's impossible low-altitude gate.

### R6 — PASS: heartbeat timing and stale-data guards are internally coherent

The script publishes at 10 Hz, performs a two-second pre-roll, prevents state advancement after a local gap greater than 250 ms, aborts stale status/position, and continues publishing during its abort-to-Land path. Existing Reliable soak evidence had no gap above 250 ms. This proves local scheduling behavior, not delivery at PX4 after the DDS Agent.

### R7 — PASS with residual risk: command scope and disarm policy

The active mission sends only Set Mode, normal Arm, and NAV_LAND. It does not send normal or force Disarm, and it requires PX4 auto-disarm after landing. Command ACKs are keyed by command ID and cleared at command start. Source/target identity is not validated in ACK callbacks, which is a lower-priority residual risk.

### R8 — FAIL storage containment: custom log root can escape the SD

Active modes verify that `/media/p450/P450_DATA` is mounted, but `--log-root` may point elsewhere. The validated `test_id` prevents path traversal, yet the parent itself is unrestricted. Required correction: resolve and require active-mode logs to remain below the mounted SD data volume.

## Test interpretation

All 26 existing unit tests pass, syntax compilation passes, and dry-run NED geometry is correct. These tests do not establish flight readiness: one test explicitly codifies the unsafe Land-ACK transition, and none exercises RC takeover or EKF reset counters. `ADVERSARIAL_RESULTS.txt` records the counterexamples.

## Verdict

The current V3 artifact is internally test-clean but is **not approved for propeller-on Offboard flight**. R1 and R2 are state-ownership defects independent of the heading issue. R3 and R4 explain why the two field flight attempts were refused. No new ULog is needed to prove these four defects.

The next safe engineering step is a reviewed V4 patch plus new unit tests. Changes to R3 and R4 must not be made without explicit owner approval because they relax existing abort conditions.

## Primary references

- PX4 v1.14 Offboard mode: https://docs.px4.io/v1.14/en/flight_modes/offboard
- PX4 v1.14 parameters (`COM_OF_LOSS_T`, `COM_OBL_RC_ACT`): https://docs.px4.io/v1.14/en/advanced_config/parameter_reference
- PX4 v1.14.3 NAV_LAND Commander path: https://github.com/PX4/PX4-Autopilot/blob/v1.14.3/src/modules/commander/Commander.cpp#L1017-L1028
- PX4 v1.14.3 in-flight magnetic alignment height check: https://github.com/PX4/PX4-Autopilot/blob/v1.14.3/src/modules/ekf2/EKF/mag_control.cpp#L234-L247
