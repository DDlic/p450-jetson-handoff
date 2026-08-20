# Remaining operator/QGC data

The following have been supplied and resolved:

- Propeller state during F1/F2.
- Separate manual arm and normal GPS-mode flight.
- RC mode switching and Kill status.
- Moonlight continuity.
- PX4 ULog for the manual flight: `qgc/log_98_2026-8-20-14-06-02.ulg`, SHA-256 `854e82464f004b555cd7056e395b84901258e2714c759f7d52952b9fcf780893`.

No additional historical ULog is required for the present root-cause decision. If later timeout statistics or cross-day estimator comparisons are needed, request only logs from identified flight days rather than the full archive.

## Optional remaining files

1. The QGC `.tlog` for approximately 2026-08-20 13:50-14:30 Asia/Taipei, if recording was enabled.
2. Any QGC screenshots or video showing the heading indicator versus the vehicle's physical direction outdoors.

## Optional field metadata

- Test location description.
- Approximate wind/weather.
- Battery identifier.
- Whether the aircraft was physically restrained during the two rejected command attempts.

Do not manufacture missing values. Add later evidence under this directory with source, timestamp and SHA-256.
