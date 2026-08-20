# Missing operator/QGC data

The operator has now confirmed:

- Propellers were installed during F1 and F2. Both NX scripts published zero commands and never armed.
- After the rejected script attempts, a separate manual arm and GPS-mode flight was normal.
- RC mode switching and Kill were normal.
- Moonlight remained connected during the 300-second soak, F1/F2 and the manual flight, with no observed instability.

These answers explain the later arm/disarm history and establish an operator-observed manual flight, but they do not replace the corrected Offboard gates.

## Requested files from the QGC laptop

1. The PX4 `.ulg` file covering approximately 2026-08-20 13:50-14:30 Asia/Taipei, including the manual GPS-mode flight. This is the most important missing artifact because it can independently verify flight state, estimator status, RC input, mode transitions, failsafes and yaw/magnetometer control flags.
2. The QGC `.tlog` for the same connection, if recording was enabled.
3. Any QGC screenshots or video showing the heading indicator versus the vehicle's physical direction outdoors.

## Optional field metadata

- Test location description.
- Approximate wind/weather.
- Battery identifier and voltage at the start of the attempts.
- Whether the aircraft was physically restrained during the two rejected command attempts.

Do not manufacture missing values. Add later evidence under this directory with source, timestamp and SHA-256.
