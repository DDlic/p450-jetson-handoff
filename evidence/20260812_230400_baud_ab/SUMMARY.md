# 230400 baud quick A/B result

Date: 2026-08-12 (Asia/Taipei)

## RX marker result

- NX Agent and `/dev/ttyTHS1`: verified 230400 baud, 8N1.
- Pixhawk `SER_TEL2_BAUD`: verified 230400.
- Marker: `/fmu/in/onboard_computer_status`, 2 Hz, `uptime=8121230`, `type=6`.
- PX4 did receive the exact marker, but the listener sample was already 45.776581 seconds old.
- Complete payload bytes received: only 240.
- Framing was left in state 5 at 250/252 bytes after the check.
- UART `FIONREAD` errors: zero.

230400 therefore permits occasional valid input frames but is not a reliable RX transport for this hardware path.

## Output continuity

The concurrent 20-second read-only SensorCombined test produced:

```text
elapsed_s=20.003
messages=602
average_hz=30.095
median_gap_ms=33.871
max_gap_ms=1054.493
gaps_over_100ms=1
gaps_over_500ms=1
gaps_over_1s=1
result=FAIL reason=max_gap_exceeded threshold_ms=100.000
```

## Decision

Do not retain 230400 or return to 460800 for the automatic-flight baseline. Use the proven 115200 physical rate and reduce the PX4 DDS publication bandwidth to the minimum required for Offboard flight and safety monitoring.
