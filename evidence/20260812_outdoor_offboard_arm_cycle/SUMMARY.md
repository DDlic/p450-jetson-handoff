# Outdoor no-prop ROS 2 Offboard arm-cycle result

Date: 2026-08-12 (Asia/Taipei)

## Safety scope

- Outdoor, vehicle confirmed propeller-free.
- Operator held RC throttle at minimum and retained the Kill Switch.
- A separate probe continuously published a hold-current-position Offboard heartbeat/setpoint.
- Arm and Disarm used normal `VEHICLE_CMD_COMPONENT_ARM_DISARM`; force arm was never used.

## Proven command path

The first short-lived command publisher attempted to send before its DDS endpoint had matched and did not arm. After the script explicitly waited for one Pixhawk `vehicle_command` subscription, the normal external Arm succeeded:

```text
COMMAND_ENDPOINT_MATCHED subscriptions=1
ARM_COMMAND normal=true force=false
ARM_CONFIRMED hold_seconds=3
```

QGC independently recorded:

```text
15:25:37.969 Armed by external command
15:25:39.887 Takeoff detected
```

This proves the ROS 2 `VehicleCommand` input path works.

## Why normal Disarm did not complete

The script repeatedly sent a normal Disarm after the three-second hold. QGC recorded many `Disarming denied, not landed` events. Therefore the Disarm commands reached PX4 but were rejected by commander because the land detector had transitioned to takeoff/not-landed, despite the propeller-free vehicle remaining physically on the ground.

Current indoor readback after the test showed `landed=true`, `ground_contact=true`, `at_rest=true`, and commander Standby. This current state does not alter the historical not-landed rejection during the armed Offboard interval.

## Critical Offboard loss

During the armed interval QGC repeatedly recorded:

```text
Failsafe activated, triggering fallback to position control
No offboard signal
```

ROS monitoring simultaneously observed repeated transitions between Offboard (`nav_state=14`, failsafe false) and Position (`nav_state=2`, failsafe true). The 10 Hz heartbeat was still active at the publisher. This is a transport delivery failure, not an intentionally stopped publisher.

The minimal firmware still reported approximately 10.1 KB/s PX4-to-NX payload at 115200 baud, close to the 11.52 KB/s theoretical 8N1 ceiling. The result is consistent with UART/XRCE congestion delaying inbound Offboard heartbeat beyond the PX4 timeout.

## Safe termination

The operator engaged Kill. QGC recorded `Disarmed by kill switch`, and later `Kill-switch disengaged`. All ROS 2 Offboard, TrajectorySetpoint, and VehicleCommand publishers were then stopped and verified at publisher count zero.

## Decision

- PASS: external ROS 2 Arm command delivery after DDS endpoint matching.
- PASS: PX4 commander receives normal Disarm commands.
- FAIL: normal Disarm during the probe because PX4 considered the vehicle not landed.
- FAIL: armed Offboard heartbeat continuity at 115200 with the current minimal publication set.
- Flight remains prohibited.

Next firmware must further reduce or throttle PX4-to-NX DDS publications before another no-prop arm test. A future test must also avoid allowing the land detector to enter takeoff, or must define the expected safe disarm/kill procedure in advance.
