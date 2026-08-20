# NX mission Gate 1 software evidence (2026-08-20)

## Classification

- Host: P450 Jetson Xavier NX.
- Test type: offline Python unit tests plus CLI dry-run.
- SITL: no.
- Hardware publication: no.
- PX4 connection required: no.
- Propellers / arming / Offboard: none.
- Repository baseline before this evidence update:
  `38b3edea688f570f085e43d275e1ae12e4421857`.

The original 9 tests covered NED/heading conversion, CLI safety gates and selected
runtime failsafe declarations. The supplemental tests cover state timeout,
VehicleCommand ACK pairing, the accepted Land ACK branch, and fail-closed state
advancement after an artificial 300 ms heartbeat pause.

## Original claimed test set: 9/9 PASS

Command:

```bash
source /opt/ros/foxy/setup.bash
source /home/p450/p450_ros2_ws/install/setup.bash
python3 -m unittest -v tests/test_p450_delivery_poc_mission.py
```

Raw output before the supplemental tests:

```text
test_dry_run_defaults_are_allowed (tests.test_p450_delivery_poc_mission.ArgumentGateTests) ... ok
test_flight_requires_distinct_operator_confirmation (tests.test_p450_delivery_poc_mission.ArgumentGateTests) ... ok
test_forward_distance_above_delivery_scope_is_refused (tests.test_p450_delivery_poc_mission.ArgumentGateTests) ... ok
test_ground_sequence_requires_props_removed_confirmation (tests.test_p450_delivery_poc_mission.ArgumentGateTests) ... ok
test_height_above_delivery_scope_is_refused (tests.test_p450_delivery_poc_mission.ArgumentGateTests) ... ok
test_east_heading_moves_positive_y (tests.test_p450_delivery_poc_mission.RouteTests) ... ok
test_north_heading_moves_positive_x_and_climbs_negative_z (tests.test_p450_delivery_poc_mission.RouteTests) ... ok
test_runtime_checks_both_gcs_and_manual_control_loss (tests.test_p450_delivery_poc_mission.RuntimeSafetyCoverageTests) ... ok
test_runtime_checks_wind_and_flight_time_limits (tests.test_p450_delivery_poc_mission.RuntimeSafetyCoverageTests) ... ok

----------------------------------------------------------------------
Ran 9 tests in 0.030s

OK
```

Exit status: `0`.

## Supplemental Gate 1 test set: 13/13 PASS

Command: same as above.

Raw output:

```text
test_dry_run_defaults_are_allowed (tests.test_p450_delivery_poc_mission.ArgumentGateTests) ... ok
test_flight_requires_distinct_operator_confirmation (tests.test_p450_delivery_poc_mission.ArgumentGateTests) ... ok
test_forward_distance_above_delivery_scope_is_refused (tests.test_p450_delivery_poc_mission.ArgumentGateTests) ... ok
test_ground_sequence_requires_props_removed_confirmation (tests.test_p450_delivery_poc_mission.ArgumentGateTests) ... ok
test_height_above_delivery_scope_is_refused (tests.test_p450_delivery_poc_mission.ArgumentGateTests) ... ok
test_east_heading_moves_positive_y (tests.test_p450_delivery_poc_mission.RouteTests) ... ok
test_north_heading_moves_positive_x_and_climbs_negative_z (tests.test_p450_delivery_poc_mission.RouteTests) ... ok
test_ack_is_paired_by_vehicle_command (tests.test_p450_delivery_poc_mission.RuntimeSafetyCoverageTests) ... ok
test_heartbeat_pause_prevents_waypoint_state_advance (tests.test_p450_delivery_poc_mission.RuntimeSafetyCoverageTests) ... ok
test_land_ack_enters_wait_landed_branch (tests.test_p450_delivery_poc_mission.RuntimeSafetyCoverageTests) ... ok
test_runtime_checks_both_gcs_and_manual_control_loss (tests.test_p450_delivery_poc_mission.RuntimeSafetyCoverageTests) ... ok
test_runtime_checks_wind_and_flight_time_limits (tests.test_p450_delivery_poc_mission.RuntimeSafetyCoverageTests) ... ok
test_takeoff_state_timeout_aborts (tests.test_p450_delivery_poc_mission.RuntimeSafetyCoverageTests) ... ok

----------------------------------------------------------------------
Ran 13 tests in 0.006s

OK
```

Exit status: `0`.

## NED CLI dry-run: PASS

Command:

```bash
python3 scripts/p450_delivery_poc_mission.py --dry-run --x0 10 --y0 20 --z0 -0.4 --heading 1.5707963267948966 --takeoff-height 1.0 --forward-distance 5.0
```

Raw output:

```text
DRY_RUN_ONLY publishes=0 commands=0
NED_START x=10.000 y=20.000 z=-0.400 heading_rad=1.570796
NED_TAKEOFF x=10.000 y=20.000 z=-1.400
NED_GOAL x=10.000 y=25.000 z=-1.400
SEQUENCE preroll -> Offboard -> Arm -> takeoff -> waypoint -> PX4 Land -> auto-disarm
```

Exit status: `0`. The run emitted no ROS 2 publications or VehicleCommand.

## Remaining gates

This evidence does not replace the same-configuration hardware gates. Gate R,
no-publish Gate P and propeller-free Gate G must pass before Gate F1. The
operator card's Offboard-loss strategy fields must also be completed and
accepted before any propeller gate.
PATCH
