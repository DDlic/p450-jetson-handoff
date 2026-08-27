# P450 NX kernel Phase 1 `88x2bu` A/B

- TEST_ID: `P450_20260819_1106_KERNEL_PHASE1_88X2BU_AB`
- Module unload timestamp: `2026-08-19 11:08:28 +08:00`
- `88x2bu` unload: SUCCESS; module absent and `wlan0` removed
- TP-Link USB Wi-Fi: `wlan0`, driver `rtl88x2bu`, module `88x2bu`
- Phone USB tether: `usb1`, driver `rndis_host`, NetworkManager state connected
- Phone IPv4: `10.136.236.205/24`, gateway/DNS `10.136.236.204`
- IPv4 default route: phone `usb1`, metric 100
- Wi-Fi IPv4 backup route: `wlan0`, metric 600
- Bound `usb1` gateway ping: 4/4, 0% loss
- Bound `usb1` internet ping: 4/4, 0% loss
- Bound `usb1` GitHub HTTPS: HTTP 200
- Bound `usb1` OpenAI HTTPS transport: connected successfully; HTTP 421 from API root is an application response, not a link failure
- `usb1` RX/TX errors: 0/0
- Current Codex established connections still use the Wi-Fi IPv6 address; unloading `88x2bu` will interrupt this session before it reconnects over phone IPv4

## Flight-system preflight

- Agent: active, PID 1670, NRestarts 0
- `/dev/ttyTHS1`: unchanged and owned by the Agent
- ROS/PX4 state: disarmed, non-Offboard, failsafe 0
- Reliable subscription count: 1
- No-publish preflight: PASS, publishes 0
- Recent kernel filter: no panic/Oops/key_garbage/hung-task event

## Gate

Before unloading `88x2bu`, the operator must explicitly confirm:

1. Propellers are removed.
2. The operator is physically at the NX console.
3. An unexpected NX reboot is acceptable and the operator will not rerun the unload.
4. The phone cable and USB tether will remain connected for the whole test.

If the NX reboots or hangs, do not repeat the test. Preserve `/sys/fs/pstore` immediately after reboot and mark Phase 1 FAIL.

## Immediate post-unload result

- NX did not reboot or hang.
- No kernel panic, Oops, `key_garbage`, or hung-task event was observed.
- Agent remained active with PID 1670 and `NRestarts=0`.
- `/dev/ttyTHS1` ownership remained with PID 1670.
- Phone tether remained the only route after Wi-Fi removal, but later experienced an independent RNDIS reset/re-enumeration.

## Phone RNDIS interruption

- `11:10:34`: `rndis_host` unregistered `usb1`; Tegra XUSB logged `Event TRB ... no TDs queued` and reset the phone USB device.
- The recreated interface failed its first 45-second DHCP attempt.
- `11:11:36`: the phone USB device fully disconnected.
- `11:11:42`: the phone re-enumerated in RNDIS mode; NetworkManager obtained a new MAC/IP and restored the default route.
- This occurred about two minutes after the `88x2bu` unload and involved the independent `rndis_host` device, so the evidence does not show that unloading `88x2bu` directly removed the phone interface.
- The phone is behind two USB hubs. Candidate causes are phone USB-mode switching, cable/hub/power instability, or RNDIS/Tegra-XUSB behavior; exact cause is unverified.
- After recovery: gateway ping 30/30, internet ping 12/12, GitHub HTTPS 200, RX/TX errors 0/0.

## Current phase

The required minimum two-hour software-only soak begins with `88x2bu` absent and the original Agent untouched. Agent stop/start is not authorized until the soak completes without a new kernel fault.

## First soak disposition

- Monitor start: `2026-08-19 11:19:30 +08:00`.
- NX entered deep suspend at `12:21:14` and resumed at `14:22:28`.
- Only about 61 minutes of continuous active samples were recorded before suspend.
- The monitor also lacked the Codex-specific `rg` path in its user-service environment; this produced journal warnings even though state rows continued.
- Result: `INCONCLUSIVE_SUSPEND`, not a two-hour PASS.
- During the observed active interval and after resume: no reboot, panic/Oops/key-GC event, Agent restart, or `88x2bu` reload was found.
- A new TEST_ID with an explicit sleep inhibitor and absolute `rg` path is required.
