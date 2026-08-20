# PX4 ULog analysis — manual GPS-mode flight after rejected F1/F2

## Provenance

- Original repository location: `log_98_2026-8-20-14-06-02.ulg` on `origin/main` commit `5870ddcfe6972b212dace9024c90ce020a8f5566`.
- Evidence copy: `qgc/log_98_2026-8-20-14-06-02.ulg`.
- File size: 1,879,659 bytes.
- SHA-256: `854e82464f004b555cd7056e395b84901258e2714c759f7d52952b9fcf780893`.
- Parser: pyulog 1.2.3.
- PX4 software: `c7a39478405122a04ef9f10b69f873561751a126`, branch `p450-xrce-rx-trace`.
- Log duration: 45.055 seconds.
- ULog dropouts: 0.

## Manual-flight sequence verified

- Logger message: `Armed by RC`.
- Vehicle remained in PX4 nav state 2, POSCTL/GPS position mode.
- Takeoff was detected approximately 5.15 seconds after log start.
- Landing was detected approximately 42.06 seconds after log start.
- Automatic landing disarm occurred at approximately 44.06 seconds with disarming reason 6.
- The log contains actuator motor/output data throughout the flight interval.
- F1/F2 script logs separately prove that those attempts published zero commands; this ULog is the later independent RC flight, not an Offboard mission.

## Safety and estimator result

- No PX4 failsafe became active.
- No failure-detector flag or motor-failure mask became active.
- RC loss=false and RC failsafe=false for all samples.
- RC lost-frame counter delta: 0 over 2,225 received-frame increments.
- Local XY/Z position and velocity remained valid and globally referenced.
- `dead_reckoning=false` for all 452 local-position samples.
- Both EKF instances retained GPS, tilt and yaw alignment.
- No magnetometer fault, magnetic-field disturbance, bad-heading fault, yaw rejection or inertial dead reckoning was recorded.
- ULog battery warning remained 0. The logged current channel is not used here to estimate propulsion load.

## Final-heading timing

- `heading_good_for_control` was false on the ground and during the initial climb.
- EKF instance 0 set `mag_aligned_in_flight=true` at approximately +15.754 s.
- EKF instance 1 set it at approximately +15.907 s.
- The selected local-position output set `heading_good_for_control=true` at approximately +16.935 s, about 11.79 seconds after takeoff detection.
- A heading-reset counter increment occurred at +15.936 s with `delta_heading=-0.009847 rad`, approximately -0.56 degrees.
- The flag returned false after landing, matching PX4's on-ground reset behavior.
- Local vertical position had changed by approximately 1.5 m when magnetic in-flight alignment occurred.

PX4 v1.14.3 source explains the height dependence: when range-finder support is compiled, the magnetic realignment request waits until estimated height above ground exceeds 1.5 m. F1 targets 0.5 m and F2 targets 1.0 m, so V3's post-takeoff hard requirement can remain impossible at both commanded heights.

Official source:

- https://github.com/PX4/PX4-Autopilot/blob/v1.14.3/src/modules/ekf2/EKF/mag_control.cpp#L234-L247
- https://github.com/PX4/PX4-Autopilot/blob/v1.14.3/src/modules/ekf2/EKF/mag_control.cpp#L302-L310
- https://github.com/PX4/PX4-Autopilot/blob/v1.14.3/src/modules/ekf2/EKF2.cpp#L1358-L1360
- https://github.com/PX4/PX4-Autopilot/blob/v1.14.3/src/modules/ekf2/EKF/ekf.h#L316-L324

## GCS status distinction

`vehicle_status.gcs_connection_lost` was true throughout this log, while:

- vehicle failsafe remained false;
- `failsafe_flags.gcs_connection_lost` remained false;
- all boolean active-failsafe fields remained false;
- RC remained healthy;
- the operator reported the Moonlight display link remained connected.

Moonlight connectivity is an NX/base-station LAN fact and is not the same signal as the PX4 MAVLink GCS-heartbeat status. The current mission has an extra raw `vehicle_status.gcs_connection_lost` runtime abort in addition to PX4's active failsafe flag; in this field configuration that extra abort would stop the mission even though PX4 did not invoke a GCS-loss failsafe.

## Operational conclusion

- The manual GPS-mode flight is machine-verified as normal for the recorded 45-second sequence.
- It validates the original diagnosis that final heading alignment is an in-flight, height-dependent diagnostic on this platform.
- V3 must not be used for F1/F2 as written.
- Changing the flight script to remove either hard abort changes the safety envelope and requires explicit owner approval.
- Until a reviewed V4 artifact exists, no propeller-on Offboard flight command is approved.
