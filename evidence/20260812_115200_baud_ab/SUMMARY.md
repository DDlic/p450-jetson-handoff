# 115200 baud A/B result

Date: 2026-08-12 (Asia/Taipei)

## Result

The 115200-baud A/B proved that the NX-to-Pixhawk XRCE path can receive and decode valid frames at a lower UART rate.

- NX Agent and `/dev/ttyTHS1`: verified 115200 baud, 8N1.
- Pixhawk `SER_TEL2_BAUD`: verified 115200.
- Test input: `/fmu/in/onboard_computer_status` at 2 Hz, marker `uptime=8121200`, `type=7`.
- PX4 complete payload bytes received: 720.
- PX4 uORB listener received the exact marker.
- Framing returned to state 0; UART `FIONREAD` errors remained zero.

This differs decisively from 460800 baud, where raw UART RX bytes reached PX4 but complete payload bytes remained zero and the listener never published. The XRCE framing implementation and ROS topic mapping therefore work; the failure is strongly rate-dependent and is localized to the 460800 UART physical/timing path.

## 115200 output-capacity check

A 45-second read-only `/fmu/out/sensor_combined` continuity test produced:

```text
elapsed_s=45.005
messages=585
average_hz=12.998
median_gap_ms=1.186
max_gap_ms=379.877
gaps_over_100ms=132
gaps_over_500ms=0
gaps_over_1s=0
result=FAIL reason=max_gap_exceeded threshold_ms=100.000
```

PX4 reported approximately 9.6 KB/s TX, close to the 11.52 KB/s theoretical 115200/8N1 ceiling. Thus 115200 is a valid diagnostic and bidirectional proof, but the current full DDS publication set saturates it and is not yet acceptable as the final automatic-flight configuration.

## Power-cycle note

During the wider test window the Pixhawk was powered only by the laptop USB and could lose power when USB was unplugged. The accepted result was captured after one reboot, within one continuous powered interval: both status samples and the successful listener output belong to that same interval. Counters from before the power loss were not compared with counters after it.

## Next decision

Test 230400 baud as the intermediate rate. If it preserves valid NX-to-PX4 payload decoding but remains output-limited, build a minimal-flight DDS publication set by removing or throttling nonessential high-rate output topics while retaining Offboard command, setpoint, state, failsafe, and local-position paths.
