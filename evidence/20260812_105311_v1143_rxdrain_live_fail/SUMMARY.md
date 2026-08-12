# PX4 v1.14.3 receive-drain candidate A/B result

Collected: 2026-08-11 to 2026-08-12 (Asia/Taipei)

Final status: PX4-to-NX continuity PASS; live 2 Hz NX-to-PX4 freshness FAIL. The 20 Hz and
Offboard gates were not run.

## Firmware identity

QGC confirmed after flashing:

```text
PX4 version: 1.14.3
PX4 git-hash: 49049d855552c39879234bf4f19229baf0939a48
PX4 git-branch: p450-v1.14.3-xrce-fix
hardware: PX4_FMU_V6C
SYS_AUTOSTART: 4001
UXRCE_DDS_CFG: 102
SER_TEL2_BAUD: 460800
MAV_1_CONFIG: 0
```

Artifact:

```text
firmware/p450-pixhawk6c-v1.14.3-xrce-rx-drain-ping-fix-49049d8555.px4
SHA-256: ba1a57ad2b48fba9908d7caf34ad5f32d7aea8c0d7bdbe74016b2862aad8e1b5
```

The clean post-flash graph contained 13 `/fmu/in/*` and 10 `/fmu/out/*` topics, exactly one
`SensorCombined` publisher, and zero `OnboardComputerStatus` publishers before input testing.

## Read-only continuity

The 30-second post-flash smoke test passed:

```text
messages=2131
average_hz=71.018
max_gap_ms=34.492
gaps_over_100ms=0
result=PASS
```

The formal ten-minute no-input gate also passed:

```text
elapsed_s=600.014
messages=42594
average_hz=70.988
median_gap_ms=12.968
max_gap_ms=83.200
gaps_over_100ms=0
gaps_over_500ms=0
gaps_over_1s=0
result=PASS
```

- Agent PID remained 1693 and `NRestarts=0`.
- Input publisher count was zero before and after the interval.
- A corrected local-time journal query found no Agent service event during the interval.

## 2 Hz output-continuity gate

With one best-effort, volatile `/fmu/in/onboard_computer_status` publisher at 2 Hz, the concurrent
60-second PX4-to-NX output monitor passed:

```text
messages=4049
average_hz=67.472
max_gap_ms=77.056
gaps_over_100ms=0
result=PASS
```

Agent PID remained unchanged with zero restarts. This proves that 2 Hz input did not break output
continuity, but it does not prove PX4 input receipt.

## Invalid cross-reboot check excluded

One QGC check on 2026-08-12 at 10:49 reported `never published`, but the NX had rebooted at
10:41:12 and the prior publisher belonged to the previous boot. That result was explicitly excluded
from the A/B decision.

## Valid live 2 Hz freshness result

Within the same new boot, the NX started a new publisher with:

```text
topic: /fmu/in/onboard_computer_status
rate: 2 Hz
QoS: best effort, volatile, depth 1
marker: uptime=8121052, type=9
publisher count: 1
PX4 subscription count: 1
```

The publisher process was confirmed alive before the QGC query. It emitted at least 200 samples
before being deliberately stopped. During this active window QGC returned:

```text
uxrce_dds_client: Running, connected
transport: serial
Payload tx: 34503 B/s
Payload rx: 0 B/s
listener onboard_computer_status 5: never published
```

This is a valid FAIL for live NX-to-PX4 receipt on source `49049d8555`. Unlike the previous
ping-only result, no marker reached uORB during this observation window.

## Safe stop and recovery

The live publisher was stopped manually. Final state:

```text
OnboardComputerStatus publisher count: 0
PX4 subscription count: 1
Agent PID: 1687
Agent NRestarts: 0
Agent state: active
```

A 30-second read-only recovery monitor passed:

```text
messages=2136
average_hz=71.140
max_gap_ms=39.628
gaps_over_100ms=0
result=PASS
```

No 20 Hz input, Offboard heartbeat, mode command, setpoint, arming, actuator command, or motor test
was performed.

## Interpretation

The candidate replaces one `uxr_run_session_timeout(..., 0)` call with a loop that continues only
when `num_payload_received` increases. That counter changes only after a complete XRCE DATA payload
reaches the topic callback. It does not reveal raw UART bytes, partial serial frames, CRC failures,
or transport data that has not yet formed a DDS payload.

At 2 Hz there is little inbound backlog, so this payload-count loop can behave almost exactly like
the original single call. The candidate is therefore disproven as the P450 solution. The next useful
single-variable step is instrumentation that reports NuttX `FIONREAD` raw pending bytes, framing
progress, and complete payload totals before attempting another transport fix.
