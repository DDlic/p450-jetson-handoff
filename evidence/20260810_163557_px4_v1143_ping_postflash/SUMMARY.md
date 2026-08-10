# PX4 v1.14.3 session-ping post-flash read-only baseline

Collected: 2026-08-10 (Asia/Taipei)

Status: firmware identity and ROS 2 receive-continuity gates PASS. The 2 Hz non-control input did
not degrade PX4-to-NX continuity, but two QGC checks reported `never published`; the 2 Hz
bidirectional gate is FAIL/pending root cause and 20 Hz remains blocked.

## Firmware and graph identity

- Intended artifact: `p450-pixhawk6c-v1.14.3-xrce-ping-fix-f9bc66c6f3.px4`.
- Repository artifact SHA-256 was rechecked before flashing:
  `cb14d73274014385e809645dd3525e1ce0e33cf5d648c7d23324c41b822bf0bd`.
- After flashing and clearing stale ROS CLI discovery state, the live DDS graph contained exactly
  13 `/fmu/in/*` and 10 `/fmu/out/*` topics, matching the PX4 v1.14 topic set.
- `/fmu/out/sensor_combined` had exactly one publisher.
- QGC `ver all` independently confirmed PX4 1.14.3, source
  `f9bc66c6f30d8ddcceaeba2545dc9f6d0e71faf1`, branch `p450-v1.14.3-xrce-fix`, and Pixhawk 6C.
- `SYS_AUTOSTART=4001`, `UXRCE_DDS_CFG=102`, `SER_TEL2_BAUD=460800`, and `MAV_1_CONFIG=0`.
- `UXRCE_DDS_PRT` and `UXRCE_DDS_SYNCT` returned no matching parameter in this v1.14.3 build.
- The PX4 XRCE client reported `Running, connected`, serial transport, TX 34904 B/s, and RX 0 B/s
  in the no-input snapshot.
- QGC confirmed `arming_state=1`, `armed_time=0`, `failsafe=false`, battery warning zero, and no
  critical failure flag. Preflight and position requirements remained invalid, so flight is blocked.

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

## 2 Hz non-control input gate

The NX published only `/fmu/in/onboard_computer_status` at 2 Hz for 63 seconds under an explicit
timeout while simultaneously monitoring `/fmu/out/sensor_combined` for 60 seconds:

```text
messages=4273
average_hz=71.214
max_gap_ms=37.397
gaps_over_100ms=0
result=PASS
```

- Agent remained PID 9922 with `NRestarts=0`.
- The publisher stopped automatically and publisher count returned to zero.
- No Agent journal event occurred.
- No control, mode, setpoint, thrust, torque, or actuator topic was published.

This proves that 2 Hz NX input did not degrade PX4-to-NX continuity. The first QGC listener check
afterward reported `onboard_computer_status: never published`, so it did not prove PX4 uORB receipt.

A follow-up definition and local DDS check found identical PX4/NX message SHA-256 values and no
source diff. An unbuffered local subscriber then received all three marker samples sent at 2 Hz with
`uptime=271828` and `type=4`. This proves the NX publisher and local serialization/DDS path. A second
QGC listener check still reported `never published`.

A controlled foreground Agent trace then sent six new markers with `uptime=424242` and `type=5`.
The Agent logged all six DataReader receipts at 240 bytes and all six corresponding serial writes at
252 bytes, with no input-path error or warning. The problem is therefore downstream of Agent DDS
receipt and its serial write call: physical UART TX/RX, PX4 XRCE receive/frame processing, or PX4
deserialization-to-uORB. The normal systemd Agent was automatically restored as PID 12167; a clean
13-in/10-out graph and 10-second read-only monitor passed after recovery.

## Remaining evidence gate

Run the QGC commands currently stored in `新增 文字文件.txt` after the foreground Agent trace. The
listener must show `uptime=424242` and `type=5` (with a PX4 receive timestamp) before this gate can
pass. If it still reports `never published`, all six Agent-received and Agent-written frames failed
to reach PX4 uORB; continue physical/PX4 receive-path diagnosis and do not proceed to 20 Hz or
Offboard.
