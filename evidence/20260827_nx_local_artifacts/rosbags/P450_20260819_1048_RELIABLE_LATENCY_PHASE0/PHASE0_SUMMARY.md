# P450 NX Reliable Latency Phase 0 baseline

- TEST_ID: `P450_20260819_1048_RELIABLE_LATENCY_PHASE0`
- NX timestamp: `2026-08-19T10:49:02+08:00`
- Repository HEAD: `0d57a9fb2af57cf80314b56ed6e1b71a56ad341a`
- Repository state: clean `main`, aligned with `origin/main`
- SD: `/dev/mmcblk1p1` mounted read-write at `/media/p450/P450_DATA`, 102 GB available
- Kernel: `5.10.216-tegra #1 SMP PREEMPT`
- Boot parameter: `cgroup.memory=nokmem` present
- Uptime at baseline: approximately 3 minutes

## Agent and UART

- Service: `p450-micro-xrce-agent.service`
- State: `active/running`
- MainPID: `1670`
- NRestarts: `0`
- Start: `2026-08-19 10:45:48 CST`
- Command: `/usr/local/bin/MicroXRCEAgent serial --dev /dev/ttyTHS1 -b 115200 -v 2`
- `/dev/ttyTHS1` owner: PID 1670, user `p450`, `MicroXRCEAgent`
- Agent binary SHA-256: `0feffc477e41c2ddd9a15d55fad0e55f27a78c02cb4b89a549851fa97f3017c6`
- Loaded Agent library: `/usr/local/lib/libmicroxrcedds_agent.so.2.4.2`
- Agent library SHA-256: `a22396c2047246176b105f568a5377c7ebf1aa6682e91743b27862da59f9bf41`

## Kernel and network

- Current-boot filtered kernel log contained normal ramoops/UART initialization only.
- No current-boot `panic`, `Oops`, `key_garbage`, or `hung task` was observed in the filtered output.
- `88x2bu` is loaded.
- Current default route uses Wi-Fi interface `wlan0`.
- `eth0` is down/unavailable, so the `88x2bu` runtime A/B must not start in this session.
- The operator ran the privileged pstore inventory twice; both commands returned no files.
- `/sys/fs/pstore` was empty at the Phase 0 check, so there was no new ramoops payload to preserve.

## ROS 2 graph and no-publish preflight

- `ROS_DOMAIN_ID=0`
- `ROS_LOCALHOST_ONLY=0`
- `RMW_IMPLEMENTATION=rmw_fastrtps_cpp`
- `/fmu/in/offboard_control_mode`: publisher count 0, subscription count 1
- Subscription reliability: Reliable
- Preflight state: disarmed, non-Offboard, failsafe 0
- Preflight result: `HEARTBEAT_PREFLIGHT_ONLY no_messages_published=true`
- Actual publishes: 0
- CSV contains the header only, as expected for a no-publish preflight.

Observed graph deviation: `/fmu/out/vehicle_global_position` was absent from the current topic list. This was recorded without restarting Agent or changing the graph.

## Decision

- NX Phase 0 local core checks: PASS.
- QGC/PX4 read-only identity/status output received and preserved.
- Full Phase 0 read-only baseline: COMPLETE / PASS.
- QGC read-only command request published to GitHub Issue #1:
  `https://github.com/DDlic/p450-jetson-handoff/issues/1#issuecomment-5336949744`
- QGC raw response:
  `https://github.com/DDlic/p450-jetson-handoff/issues/1#issuecomment-5336966102`
- Phase 1: BLOCKED for this session because the only active network path is through the loaded Wi-Fi module and no wired route is available.
- No Agent stop/start, module unload, parameter change, firmware flash, Offboard transition, arm command, heartbeat publication, setpoint publication, or flight action was performed.

## QGC/PX4 baseline result

- Hardware/firmware: PX4 FMUv6C, PX4 v1.14.3, Git `c7a39478405122a04ef9f10b69f873561751a126`.
- Commander: Standby, AUTO_LOITER, no failsafe.
- XRCE: Running/connected, serial, Reliable input stream, 3002 B/s output, no FIONREAD errors, framing idle/complete.
- Parameters: `COM_OF_LOSS_T=1.0`, `COM_OBL_RC_ACT=0`, `COM_DISARM_LAND=2.0`, `MPC_LAND_SPEED=0.7`.
- Vehicle: disarmed (`arming_state=1`), landed/at rest, but `pre_flight_checks_pass=False`.
- Local position: horizontal position/velocity invalid, no global reference, heading not good for control, `dead_reckoning=True`.
- Safety conclusion: this baseline does not authorize Offboard, arming, or flight.
