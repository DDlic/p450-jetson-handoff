# Missing operator/QGC data

The current package is sufficient to prove that the mission scripts never published or armed during F1/F2. The following data would make the engineering record complete and should be supplied if available.

## Required answers from the operator

1. During the F1 and F2 command attempts, were propellers installed or removed?
2. Did any manual PX4 Arm/Disarm occur during this boot outside the NX scripts? The later `vehicle_status` showed `latest_arming_reason=1` and `latest_disarming_reason=6`, while both NX flight attempts published zero commands.
3. Was the RC mode switch operational and was the Kill switch function checked that day?
4. Confirm whether Moonlight remained connected at 720p/30 for the entire 300-second soak.

## Requested files from the QGC laptop

1. The PX4 `.ulg` file covering approximately 2026-08-20 13:50-14:30 Asia/Taipei. This is the most important missing artifact because it can show yaw/magnetometer control flags over time.
2. The QGC `.tlog` for the same connection, if recording was enabled.
3. Any QGC screenshots or video showing the heading indicator versus the vehicle's physical direction outdoors.

## Optional field metadata

- Test location description.
- Approximate wind/weather.
- Battery identifier and voltage at the start of the attempts.
- Whether the vehicle was restrained during the command attempts.

Do not manufacture missing values. Add later evidence under this directory with source, timestamp and SHA-256.
