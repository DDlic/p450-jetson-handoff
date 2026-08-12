# 115200 baud A/B test

Purpose: distinguish a 460800-baud physical/clock-integrity problem from an XRCE framing/software problem.

Pre-change baseline:

- NX Agent: `/dev/ttyTHS1`, 460800 baud, 8N1, no hardware/software flow control.
- Agent service: `p450-micro-xrce-agent.service`, active with one UART holder and `NRestarts=0`.
- Pixhawk: `SER_TEL2_BAUD=460800`, diagnostic PX4 v1.14.3 build `f6beb984ca`.
- During the preceding 2 Hz marker, Pixhawk observed UART RX data but completed zero XRCE payload bytes.

Procedure:

1. Change the NX Agent service and Pixhawk `SER_TEL2_BAUD` together to 115200.
2. Reboot Pixhawk and verify the Agent reconnects.
3. Run one 2 Hz non-control `onboard_computer_status` marker.
4. Compare raw RX, framing state, complete payload count, and uORB listener output.

The repository service file is the authoritative NX-side configuration used for this A/B test.

NX-side setup observation:

- Restarting the Agent with `-b 115200` initially left the kernel-reported tty speed at 460800.
- With the Agent stopped, an explicit `stty` changed the tty to 115200; it remained 115200 after the Agent started.
- The service therefore includes an `ExecStartPre=/bin/stty ... 115200 ...` guard so the tested baud is explicit and survives service or host restarts.
