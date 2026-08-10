# PX4 v1.14.3 session-ping post-flash read-only baseline

Collected: 2026-08-10 (Asia/Taipei)

Status: ROS 2 receive-continuity gate PASS. Exact PX4 source hash and post-flash parameter values
remain pending until the owner pushes the requested QGC MAVLink Console output.

## Firmware and graph identity

- Intended artifact: `p450-pixhawk6c-v1.14.3-xrce-ping-fix-f9bc66c6f3.px4`.
- Repository artifact SHA-256 was rechecked before flashing:
  `cb14d73274014385e809645dd3525e1ce0e33cf5d648c7d23324c41b822bf0bd`.
- After flashing and clearing stale ROS CLI discovery state, the live DDS graph contained exactly
  13 `/fmu/in/*` and 10 `/fmu/out/*` topics, matching the PX4 v1.14 topic set.
- `/fmu/out/sensor_combined` had exactly one publisher.
- `ver all` is still required to independently prove source hash `f9bc66c6f3...`; the graph alone
  cannot distinguish stock v1.14.3 from the session-ping build.

## Clean test starting point

The Agent stayed alive across the firmware flash, so the first ROS CLI query retained old v1.15
entities and reported multiple publishers. One intentional Agent service restart and one ROS 2 CLI
daemon cache clear were performed before the formal test. This established:

- Agent PID 9922, `NRestarts=0`, `ExecMainStatus=0`.
- Exactly one Agent process and one `/dev/ttyTHS1` holder.
- Serial transport `/dev/ttyTHS1` at 460800 baud.
- A clean 13-in/10-out graph with one SensorCombined publisher.

The intentional pre-test restart is not counted as a continuity failure. The acceptance interval
began only after PID 9922 and the clean graph were established.

## Formal 10-minute read-only result

```text
elapsed_s=600.005
messages=42718
average_hz=71.196
median_gap_ms=12.841
max_gap_ms=38.913
gaps_over_100ms=0
gaps_over_500ms=0
gaps_over_1s=0
result=PASS threshold_ms=100.000
```

- Agent remained PID 9922 for the full interval.
- `NRestarts` remained zero and `ExecMainStatus` remained zero.
- The service journal contained no lifecycle or error entries during the test window.
- No `/fmu/in/*` topic was published, and no PX4 parameter, mode, arming, or control action occurred.

This reproduces the previously verified v1.14.3 session-ping receive-continuity behavior and removes
the approximately one-second gap seen with the v1.15.4 diagnostic firmware.

## Remaining evidence gate

The owner still needs to run the commands currently stored in `新增 文字文件.txt`, append the
complete QGC output, and push it. Before any 2 Hz input test, verify:

- PX4 version and exact source hash from `ver all`.
- `SYS_AUTOSTART`.
- `UXRCE_DDS_CFG`, `UXRCE_DDS_SYNCT`, and `SER_TEL2_BAUD`.
- `MAV_1_CONFIG` and XRCE client connection state.
- Disarmed vehicle and failsafe status.

Only after that read-only evidence is accepted should the project proceed to the authorized test
sequence: 2 Hz non-control input, then 20 Hz non-control pressure, then disarmed zero-thrust
Offboard heartbeat freshness.
