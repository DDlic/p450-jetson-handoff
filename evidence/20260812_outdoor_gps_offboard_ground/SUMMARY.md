# Outdoor GPS/EKF and disarmed Offboard ground test

Date: 2026-08-12 (Asia/Taipei)

## Scope and safety

- Outdoor ground test only; no flight was attempted.
- Vehicle remained disarmed during the ROS 2 Offboard probe.
- The probe never published `VehicleCommand`, never requested arming, and stopped if an armed state was detected.
- The operator changed flight modes using the RC transmitter.

## GPS and estimator

- 3D GNSS fix (`fix_type=3`).
- Satellites used: 15.
- EPH approximately 0.89 m; EPV approximately 1.50 m.
- HDOP approximately 0.71; VDOP approximately 1.07.
- NED velocity valid; no jamming indication.
- Local position: XY/Z position and velocity valid, XY/Z global, not dead reckoning.
- PX4 preflight checks passed and the operator independently confirmed GPS-mode arming was permitted, then disarmed.
- GPS heading was NaN, as expected for the installed single-antenna GNSS. `heading_good_for_control` remained false in the observed local-position sample and requires follow-up before any flight qualification.

## Vehicle safety state before probe

- `arming_state=1`, `flag_armed=false`.
- `failsafe=false`.
- `power_input_valid=true`, `usb_connected=false`.
- `pre_flight_checks_pass=true`.

## Offboard ground probe

The script `scripts/p450_offboard_ground_probe.py` captured the current valid local position, then published at 10 Hz:

- `/fmu/in/offboard_control_mode` with position control selected.
- `/fmu/in/trajectory_setpoint` holding the captured current position and yaw.

It did not publish any mode-change or arm command.

Observed sequence:

```text
NAV_STATE=15 OFFBOARD=False ARMING_STATE=1 FAILSAFE=False
GROUND_PROBE_READY disarmed=true hold=(-5.792,-4.419,-6.455) yaw=-2.494
NAV_STATE=14 OFFBOARD=True ARMING_STATE=1 FAILSAFE=False
NAV_STATE=15 OFFBOARD=False ARMING_STATE=1 FAILSAFE=False
```

After the operator returned the RC switch to the original mode, the probe was stopped. Final ROS graph checks showed zero publishers on both Offboard input topics and the Pixhawk subscriptions remained present.

## Conclusion

PASS for outdoor, propeller-off/disarmed GPS/EKF validation and ROS 2 Offboard mode entry/exit. This does not qualify the vehicle for flight. Remaining blockers include the 115200 serial burst latency, `heading_good_for_control=false`, explicit Offboard-loss behavior under a controlled disarmed test, and all normal armed/propeller flight safety checks.
