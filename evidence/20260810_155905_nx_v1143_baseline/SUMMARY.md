# Phase A NX read-only baseline summary

Collected: 2026-08-10 (Asia/Taipei)

Status: incomplete pending fresh QGC `ver all`, parameter, and listener outputs.

## Current evidence

- PX4 firmware version/source hash: not yet proven. The current DDS graph has 29 `/fmu/in/*`
  and 13 `/fmu/out/*` topics (42 total), which is consistent with the prior v1.15 diagnostic
  environment rather than the historical v1.14 graph, but only QGC `ver all` may decide this.
- Partial QGC status reports `Running, connected`, serial transport, payload TX 63978 B/s,
  payload RX 0 B/s, timesync not converged, cycle max 1012003 us, and cycle-interval max
  1012004 us.
- The installed ROS workspace is `/home/p450/p450_ros2_ws`. CMake cache and extracted source
  directory names identify `px4_msgs-release-1.14` and `px4_ros_com-release-v1.14`.
- These source snapshots do not contain `.git`, so exact branch commits and dirty status cannot
  be proven. Installed package versions are px4_msgs 2.0.1 and px4_ros_com 0.1.0.
- `MicroXRCEAgent --version` is unsupported by the installed binary, so the exact Agent version
  is not independently proven by that command. The repository history identifies it as v2.4.2.
- Agent service was active with PID 7017, `NRestarts=0`, and `ExecMainStatus=0`.
- `/dev/ttyTHS1` had exactly one holder: MicroXRCEAgent PID 7017, fd 3.
- Service arguments: serial `/dev/ttyTHS1`, 460800 baud, verbosity 2, ROS domain 0.
- `/fmu/out/sensor_combined` had one bare-DDS PX4 publisher using Best Effort and Transient Local
  QoS. No ROS subscriber was present at the snapshot instant.

## 65-second read-only continuity

- Messages: 2647
- Average: 40.721 Hz
- Median gap: 1.131 ms
- Maximum gap: 1023.395 ms
- Gaps over 100 ms: 23
- Gaps over 500 ms: 23
- Gaps over 1 second: 10
- Result: FAIL against the project 100 ms gate
- Agent before/after: PID 7017, `NRestarts=0`
- Agent journal during the recent 90-second window: no entries

This proves the approximately one-second data stalls occurred without a systemd Agent restart.
The partial PX4 status independently records a client cycle maximum of approximately 1.012 s.

## UART and Agent observations

- Current-boot kernel records normal Tegra UART/GPCDMA registration.
- No UART baud, overrun, framing, or I/O error was found in the filtered current-boot evidence.
- Earlier same-day Agent stop/start entries predate this Phase A collection and came from the
  prior diagnostic workflow. Phase A itself did not stop or restart the Agent.

## Missing evidence

- Fresh QGC `ver all`, needed for actual PX4 version, source hash, board, and build identity.
- Fresh values for `UXRCE_DDS_CFG`, `UXRCE_DDS_PRT`, `UXRCE_DDS_SYNCT`, `SER_TEL2_BAUD`,
  and `MAV_1_CONFIG`.
- Fresh QGC `listener vehicle_status 1` and `listener failsafe_flags 1` output.
- Exact Git commits for the extracted release/1.14 ROS source snapshots.
- Exact Agent binary version because this build rejects `--version`.

No firmware was flashed, no PX4 parameter or flight mode was changed, the Agent was not restarted,
and no `/fmu/in/*` topic was published during this Phase A collection.
