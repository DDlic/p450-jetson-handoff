# Ubuntu 22.04 / Humble / Gazebo desktop SITL evidence

Test family: `P450_20260825_DESKTOP_HUMBLE_SITL_HANDOFF`
Branch: `codex/ubuntu22-humble-sitl-20260825`
Baseline: `e6f783f7a0132656cbabf2a897b41a2bc705b3ad`

This is software-only evidence from PX4 v1.14.3 x500 SITL and Gazebo Garden. It does not
represent a P450 physics model, Jetson/Foxy/UART timing, or authorization for physical flight.

## Final matrix

| Case | TEST_ID | Expected exit | Result | Heartbeats | Max gap |
|---|---|---:|---:|---:|---:|
| SIM-P | `...SIM_P_R1` | 0 | PASS | 0 | n/a |
| SIM-G | `...SIM_G_R2` | 0 | PASS | 51 | 104.589 ms |
| SIM-F1 | `...SIM_F1` | 0 | PASS | 166 | 104.840 ms |
| SIM-F2 | `...SIM_F2` | 0 | PASS | 201 | 105.141 ms |
| Heartbeat pause | `...FI_HEARTBEAT_R1` | 12 | PASS | 118 | 636.361 ms injected |
| POSCTL takeover | `...FI_MODE_R1` | 20 | PASS | 117 | 105.118 ms |
| Agent 3 s pause | `...FI_AGENT_R2` | 20 | PASS | 164 | 105.296 ms local publish |

Every baseline active sample had `failsafe=0`, `active_gcs_lost=0`, and zero heartbeat gaps above
150 ms. SIM-F2 reached about 5.41 m maximum horizontal displacement and completed PX4 Land plus
auto-disarm-land. The initial Agent console has one `session established`, no
`session re-established`, and no close/delete before the failure-injection phase.

The Agent pause cases intentionally caused PX4 `Failsafe activated`, Offboard loss to POSCTL, and
session re-establishment. The final R2 retained the same Agent PID, mission exit 20 correctly
relinquished control, and the independent operator recovery confirmed Land/disarmed.

## Required compatibility fixes

The requested unmodified V4 claim is disproved by the preserved attempts:

- Original SIM-P: exit 2 because `Path.is_mount()` missed the required same-device bind mount.
- Original SIM-G: PX4 console reported `Disarmed by landing`, but v1.14.3 published reason 6 while
  the generated message constant expected 7; mission exit 16.

The tested mission hash after the two narrow fixes is
`825966c9e5f978c8cd6c9c39e2367d068187a3d77da10321b62da4b8f1d17f95`; the untouched baseline
hash remains `4d42081c1c4e1355bb49b0dcb4c73df6a7816a9872258b1c8e1b35d73746a4ff` in Git history.

## Retry ledger

No attempt was deleted:

- `SIM_P` records the original mount-detection refusal; `SIM_P_R1` is the pass.
- `SIM_G` records the v1.14 reason mismatch; `SIM_G_R1` records a stale Offboard reset refusal;
  `SIM_G_R2` is the pass.
- `FI_HEARTBEAT` injected before PX4 had confirmed takeoff and produced auto-disarm-preflight;
  `FI_HEARTBEAT_R1` injects after hold and is the pass.
- `FI_MODE` arrived after Land had begun; `FI_MODE_R1` injects in the hold window and is the pass.
- `FI_AGENT` used full Agent stop/restart and missed the mission's Land-confirm deadline, although
  PX4 ultimately AUTO_LANDed and disarmed. `FI_AGENT_R1` established that POSCTL takeover implies
  exit 20; `FI_AGENT_R2` repeats that expected path and is the pass.

## Layout

- `system/`: environment, unit tests, ROS topic inventory, Agent/PX4/operator and case consoles.
- `missions/`: every mission attempt's immutable `MISSION_EVENTS.csv` and `HEARTBEAT.csv`.
- `ulogs/`: ULogs for the three active baseline passes and three final failure-injection passes.
- `SHA256SUMS`: relative-path hashes for every raw artifact in this directory.

Verify from this directory with `sha256sum -c SHA256SUMS`.
