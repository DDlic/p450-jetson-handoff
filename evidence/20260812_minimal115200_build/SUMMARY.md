# PX4 v1.14.3 minimal 115200 DDS firmware build

Date: 2026-08-12 (Asia/Taipei)

## Identity

- Board: PX4 FMUv6C / board ID 56 / revision 0.
- Source branch: `p450-v1.14.3-xrce-minimal-115200`.
- Source commit: `0438dbc6fd`.
- Parent diagnostics: `f6beb984ca`.
- Earlier RX-drain fix: `49049d8555`.
- Earlier session ping fix: `f9bc66c6f3`.

## Artifact

- File: `firmware/p450-pixhawk6c-v1.14.3-xrce-minimal115200-0438dbc6fd.px4`
- Container size: 1,805,302 bytes.
- Image size: 1,934,852 bytes.
- SHA-256: `f9ebf0cceeffaf0487d6f4920d1ee29c2d23404f759c406523093e7ba37cd479`
- FLASH usage: 1,934,852 / 1,966,080 bytes, 98.41%.

## Preserved publications

- `/fmu/out/failsafe_flags`
- `/fmu/out/position_setpoint_triplet`
- `/fmu/out/timesync_status`
- `/fmu/out/vehicle_control_mode`
- `/fmu/out/vehicle_global_position`
- `/fmu/out/vehicle_gps_position`
- `/fmu/out/vehicle_local_position`
- `/fmu/out/vehicle_status`

## Removed high-bandwidth/nonessential publications

- `/fmu/out/collision_constraints`
- `/fmu/out/sensor_combined`
- `/fmu/out/vehicle_attitude`
- `/fmu/out/vehicle_odometry`
- `/fmu/out/vehicle_trajectory_waypoint_desired`

All original `/fmu/in/*` subscriptions remain present, including OffboardControlMode, TrajectorySetpoint, VehicleCommand, onboard-computer status, attitude/rate setpoints, external odometry, optical flow, obstacle distance, and telemetry status.

This is a bandwidth-isolation candidate. It must pass post-flash identity, 115200 bidirectional marker, local-position continuity, and Offboard precondition tests before any flight.
