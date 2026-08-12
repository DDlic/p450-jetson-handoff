# Minimal 115200 DDS post-flash test

Date: 2026-08-12 (Asia/Taipei)

## Verified identity and transport

- PX4 hash: `0438dbc6fd16fe4fb1df1adfda6ddf543373e47e`.
- PX4 branch: `p450-v1.14.3-xrce-minimal-115200`.
- Pixhawk `SER_TEL2_BAUD=115200`, saved.
- NX Agent and actual `/dev/ttyTHS1` termios: 115200 baud, 8N1.
- Minimal ROS graph exactly matched the intended retained topic set.
- PX4 received marker `uptime=8121150`, `type=5`.
- Complete RX payload bytes reached 6960, framing returned to state 0, and FIONREAD errors remained zero.

## Session reset observation

After the Pixhawk firmware flash/reboot, the long-running Agent retained stale DDS entities. The ROS CLI initially showed a cached graph, but a direct 30-second subscriber received zero messages. Stopping the ROS daemon exposed that the graph was actually absent.

A clean restart of `p450-micro-xrce-agent.service` immediately rebuilt the full minimal graph. Therefore, after a Pixhawk-only power cycle or firmware reboot, restart the Agent before accepting the ROS graph or running a test:

```bash
sudo systemctl restart p450-micro-xrce-agent.service
```

If the NX itself reboots, systemd starts a fresh Agent automatically.

## Valid 30-second local-position baseline

Measured after the clean Agent restart, with no input publisher active:

```text
elapsed_s=30.117 messages=622 average_hz=20.653
arrival median_ms=1.146 max_ms=366.477 over_100ms=92 over_500ms=0 over_1s=0
source median_ms=45.059 max_ms=99.168 over_100ms=0 over_500ms=0 over_1s=0
```

The PX4 source stream was continuous, but the 115200 serial output still arrived at the NX in bursts. This candidate is accepted only for propeller-off, disarmed outdoor GPS/EKF and Offboard-mode ground checks. It is not accepted for flight.

## Indoor estimator state

The indoor sample had valid vertical position but no valid horizontal/global position:

- `xy_valid=false`, `v_xy_valid=false`, `xy_global=false`.
- `z_valid=true`, `v_z_valid=true`.
- `heading_good_for_control=false`, `dead_reckoning=true`.
- `ref_lat`, `ref_lon`, and `ref_alt` were not initialized.

These are the exact conditions to recheck outdoors after GNSS quality has stabilized.
