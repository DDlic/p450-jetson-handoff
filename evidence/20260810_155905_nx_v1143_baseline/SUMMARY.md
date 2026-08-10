# Phase A NX read-only baseline summary

Collected: 2026-08-10 (Asia/Taipei)

Status: Phase A collection complete, with two documented metadata limitations: the extracted
ROS source snapshots have no `.git`, and the installed Agent binary rejects `--version`.

## Actual PX4 baseline

- Hardware: Pixhawk 6C (`PX4_FMU_V6C`, STM32H7 rev. V).
- PX4 version: 1.15.4.
- PX4 source: `996b1df7a10a35b3e3534df9c5629f3675c7cab0`.
- PX4 branch: `p450-v1.15.4-xrce-rx-drain`.
- Build: 2026-08-04 15:50:33, GCC 9.3.1.
- This is the first-generation v1.15.4 RX-drain diagnostic candidate, not the required final
  v1.14.3 baseline and not the untested v1.15.4 full-drain candidate.

## PX4 XRCE status and parameters

- Client: running and connected, serial transport.
- Payload TX: 64647 B/s.
- Payload RX: 0 B/s during the read-only condition.
- Timesync converged: false.
- Client cycle maximum: 1012003 us.
- Client cycle-interval maximum: 1012004 us.
- `UXRCE_DDS_CFG=102` (TELEM2).
- `UXRCE_DDS_SYNCT=0` (diagnostic setting, not a final-flight value).
- `SER_TEL2_BAUD=460800`.
- `MAV_1_CONFIG=0`.
- `UXRCE_DDS_PRT` returned no matching value in this firmware.

At 460800 baud with 8N1 framing, the raw serial ceiling is approximately 46080 bytes/s before
XRCE framing overhead. The client-reported 64647 B/s is an application payload counter rather
than a direct wire-throughput measurement, but it exceeds the physical raw-line ceiling and is
consistent with an unsustainable output demand or queued/backlogged traffic.

## NX, Agent, UART, and ROS workspace

- Agent service: active, PID 7017, `NRestarts=0`, `ExecMainStatus=0`.
- `/dev/ttyTHS1` had exactly one holder: MicroXRCEAgent PID 7017, fd 3.
- Service arguments: serial `/dev/ttyTHS1`, 460800 baud, verbosity 2, ROS domain 0.
- Current-boot evidence contains no UART baud, overrun, framing, or I/O error.
- Installed ROS workspace: `/home/p450/p450_ros2_ws`.
- CMake cache and extracted source directory names identify `px4_msgs-release-1.14` and
  `px4_ros_com-release-v1.14`.
- The source snapshots contain no `.git`, so exact commits and dirty status cannot be proven.
- Installed package versions: px4_msgs 2.0.1 and px4_ros_com 0.1.0.
- The installed Agent binary rejects `MicroXRCEAgent --version`; repository history identifies
  it as v2.4.2, but the binary did not independently print that version.
- DDS graph: 29 `/fmu/in/*` and 13 `/fmu/out/*` topics (42 total), consistent with the current
  v1.15 diagnostic firmware. `/fmu/out/sensor_combined` had one bare-DDS PX4 publisher using
  Best Effort and Transient Local QoS.

The current v1.15.4 firmware and release/1.14 ROS workspace are not an acceptable control-test
pair. `SensorCombined` remained decodable because that interface is compatible, but no active
`/fmu/in/*` test should be performed with this mismatch.

## 65-second read-only continuity

- Messages: 2647.
- Average: 40.721 Hz.
- Median gap: 1.131 ms.
- Maximum arrival gap: 1023.395 ms.
- Gaps over 100 ms: 23.
- Gaps over 500 ms: 23.
- Gaps over 1 second: 10.
- Result: FAIL against the project 100 ms gate.
- Agent before/after: PID 7017, `NRestarts=0`.
- Agent journal during the recent 90-second test window: no entries.

The ROS arrival maximum of 1023.395 ms and PX4 client-cycle maximum of 1012.003 ms independently
place the approximately one-second stall inside the active PX4 XRCE client loop. It occurred
without an Agent restart or session lifecycle event visible in the service journal.

## Vehicle and safety state

- `arming_state=1`, `armed_time=0`, `failsafe=false`, and `failure_detector_status=0`.
- `pre_flight_checks_pass=false`.
- `local_position_invalid=true`, `local_velocity_invalid=true`, and
  `global_position_invalid=true`.
- `offboard_control_signal_lost=true` and `manual_control_signal_lost=true`.
- Battery warning is zero and battery is not marked unhealthy.
- QGC USB is connected; GCS connection is not lost.

This state is not eligible for Offboard, arming, propeller, outdoor, or flight testing.

## Phase A conclusion and next gate

Phase A proves that the vehicle is currently running the failing v1.15.4 RX-drain diagnostic
candidate, not the project-mandated v1.14.3 final baseline. It also captures a deterministic
approximately one-second PX4 client-loop stall and an output payload demand above the 460800 8N1
raw-line ceiling.

Per `P450_PX4_V1143_FINAL_BASELINE_AND_NX_EVIDENCE_REQUEST_2026-08-10.md`, the next active step
requires a new owner authorization: restore the verified v1.14.3 session-ping firmware, use the
release/1.14 workspace, and begin with a 10-minute read-only continuity baseline. No firmware,
parameter, Agent, mode, or publisher change was made during this Phase A collection.
