#!/usr/bin/env python3
"""Offline tests for the P450 delivery mission safety envelope."""

import importlib.util
import math
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import time
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/p450_delivery_poc_mission.py"
SPEC = importlib.util.spec_from_file_location("p450_delivery_poc_mission", SCRIPT)
MISSION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MISSION)


def arguments(**overrides):
    values = {
        "mode": "dry-run",
        "test_id": None,
        "allow_armed": False,
        "operator_confirmation": "",
        "takeoff_height": 0.5,
        "forward_distance": 0.0,
        "x0": 0.0,
        "y0": 0.0,
        "z0": 0.0,
        "heading": 0.0,
        "log_root": str(MISSION.DEFAULT_LOG_ROOT),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def valid_position(**overrides):
    values = {
        "xy_valid": True,
        "z_valid": True,
        "v_xy_valid": True,
        "v_z_valid": True,
        "xy_global": True,
        "z_global": True,
        "heading_good_for_control": False,
        "dead_reckoning": False,
        "x": 1.0,
        "y": 2.0,
        "z": -0.2,
        "vx": 0.0,
        "vy": 0.0,
        "vz": 0.0,
        "heading": 0.9,
        "delta_xy": [0.0, 0.0],
        "xy_reset_counter": 0,
        "delta_z": 0.0,
        "z_reset_counter": 0,
        "delta_vxy": [0.0, 0.0],
        "vxy_reset_counter": 0,
        "delta_vz": 0.0,
        "vz_reset_counter": 0,
        "delta_heading": 0.0,
        "heading_reset_counter": 0,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class RouteTests(unittest.TestCase):
    def test_north_heading_moves_positive_x_and_climbs_negative_z(self):
        takeoff, goal = MISSION.route_from_heading(10.0, 20.0, -0.4, 0.0, 1.0, 5.0)
        self.assertEqual(takeoff, (10.0, 20.0, -1.4))
        self.assertAlmostEqual(goal[0], 15.0)
        self.assertAlmostEqual(goal[1], 20.0)
        self.assertAlmostEqual(goal[2], -1.4)

    def test_east_heading_moves_positive_y(self):
        _, goal = MISSION.route_from_heading(10.0, 20.0, -0.4, math.pi / 2, 1.0, 5.0)
        self.assertAlmostEqual(goal[0], 10.0)
        self.assertAlmostEqual(goal[1], 25.0)


class ArgumentGateTests(unittest.TestCase):
    def test_same_device_bind_mount_is_detected_from_mountinfo(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "bind target"
            target.mkdir()
            escaped_target = str(target.resolve()).replace(" ", r"\040")
            mountinfo = root / "mountinfo"
            mountinfo.write_text(
                f"36 25 259:5 /source {escaped_target} rw,relatime "
                "- ext4 /dev/nvme0n1p5 rw\n",
                encoding="utf-8",
            )

            self.assertTrue(MISSION.path_is_mounted(target, mountinfo))

    def test_dry_run_defaults_are_allowed(self):
        self.assertIsNone(MISSION.validate_args(arguments()))

    def test_height_above_delivery_scope_is_refused(self):
        error = MISSION.validate_args(arguments(takeoff_height=1.01))
        self.assertIn("0.1..1.0", error)

    def test_forward_distance_above_delivery_scope_is_refused(self):
        error = MISSION.validate_args(arguments(forward_distance=5.01))
        self.assertIn("0..5", error)

    def test_ground_sequence_requires_props_removed_confirmation(self):
        with patch.object(MISSION, "path_is_mounted", return_value=True):
            error = MISSION.validate_args(
                arguments(mode="ground-sequence", test_id="P450_GROUND_TEST")
            )
        self.assertIn(MISSION.GROUND_CONFIRMATION, error)

    def test_flight_requires_distinct_operator_confirmation(self):
        with patch.object(MISSION, "path_is_mounted", return_value=True):
            error = MISSION.validate_args(
                arguments(mode="flight", test_id="P450_FLIGHT_TEST", allow_armed=True)
            )
        self.assertIn(MISSION.FLIGHT_CONFIRMATION, error)

    def test_active_log_root_must_resolve_below_sd_mount(self):
        with patch.object(MISSION, "path_is_mounted", return_value=True):
            error = MISSION.validate_args(
                arguments(
                    mode="preflight-only",
                    test_id="P450_PREFLIGHT_TEST",
                    log_root="/home/p450/flight-logs",
                )
            )
        self.assertIn("below the mounted SD", error)


class RuntimeSafetyCoverageTests(unittest.TestCase):
    def test_ground_navigation_accepts_finite_yaw_before_final_inflight_alignment(self):
        self.assertTrue(MISSION.position_is_navigation_valid(valid_position()))

    def test_navigation_still_rejects_dead_reckoning_or_nonfinite_yaw(self):
        self.assertFalse(
            MISSION.position_is_navigation_valid(valid_position(dead_reckoning=True))
        )
        self.assertFalse(
            MISSION.position_is_navigation_valid(valid_position(heading=math.nan))
        )

    def test_preflight_does_not_deadlock_on_px4_inflight_heading_flag(self):
        flags = SimpleNamespace(
            **{name: False for name in MISSION.FAILSAFE_FLAG_NAMES},
            battery_warning=0,
        )
        mission = SimpleNamespace(
            data_ready=lambda: True,
            status=SimpleNamespace(
                arming_state=MISSION.DISARMED,
                nav_state=15,
                failsafe=False,
                pre_flight_checks_pass=True,
            ),
            control=SimpleNamespace(flag_armed=False),
            land=SimpleNamespace(landed=True),
            failsafe_flags=flags,
            position=valid_position(heading_good_for_control=False),
            battery=None,
            endpoints_ready=lambda: True,
        )

        self.assertEqual(MISSION.DeliveryMission.preflight_reasons(mission), [])

    def test_runtime_treats_pending_final_heading_as_low_altitude_diagnostic(self):
        def run_safety(state, raw_gcs_lost=False, active_gcs_lost=False):
            aborts = []
            relinquished = []
            flags = SimpleNamespace(
                **{name: False for name in MISSION.FAILSAFE_FLAG_NAMES},
                battery_warning=0,
                offboard_control_signal_lost=False,
            )
            flags.gcs_connection_lost = active_gcs_lost
            mission = SimpleNamespace(
                state=state,
                args=SimpleNamespace(mode="flight"),
                age=lambda _name: 0.0,
                STATUS_STALE_ABORT_SECONDS=2.0,
                POSITION_STALE_ABORT_SECONDS=2.0,
                failsafe_flags=flags,
                status=SimpleNamespace(
                    arming_state=MISSION.ARMED,
                    nav_state=MISSION.NAV_OFFBOARD,
                    failsafe=False,
                    failure_detector_status=0,
                    gcs_connection_lost=raw_gcs_lost,
                ),
                control=SimpleNamespace(flag_control_offboard_enabled=True),
                position=valid_position(heading_good_for_control=False),
                position_reset_abort_reason=None,
                land=None,
                battery=None,
                endpoints_ready=lambda: True,
                abort=aborts.append,
                relinquish_control=relinquished.append,
            )
            MISSION.DeliveryMission.safety_check(mission)
            return aborts, relinquished

        self.assertEqual(run_safety("TAKEOFF"), ([], []))
        self.assertEqual(run_safety("HOLD_AFTER_TAKEOFF"), ([], []))
        self.assertEqual(run_safety("MOVE_FORWARD"), ([], []))
        self.assertEqual(run_safety("MOVE_FORWARD", raw_gcs_lost=True), ([], []))
        aborts, relinquished = run_safety(
            "MOVE_FORWARD", active_gcs_lost=True
        )
        self.assertEqual(aborts, ["failsafe flag gcs_connection_lost=true"])
        self.assertEqual(relinquished, [])

    def test_posctl_takeover_is_detected_before_later_land_request(self):
        relinquished = []
        flags = SimpleNamespace(
            **{name: False for name in MISSION.FAILSAFE_FLAG_NAMES},
            battery_warning=0,
            offboard_control_signal_lost=False,
        )
        mission = SimpleNamespace(
            state="HOLD_AFTER_TAKEOFF",
            args=SimpleNamespace(mode="flight"),
            age=lambda _name: 0.0,
            STATUS_STALE_ABORT_SECONDS=2.0,
            POSITION_STALE_ABORT_SECONDS=2.0,
            failsafe_flags=flags,
            status=SimpleNamespace(
                arming_state=MISSION.ARMED,
                nav_state=2,
                failsafe=False,
                failure_detector_status=0,
                gcs_connection_lost=False,
            ),
            control=SimpleNamespace(flag_control_offboard_enabled=False),
            position=valid_position(heading_good_for_control=False),
            position_reset_abort_reason=None,
            land=None,
            battery=None,
            endpoints_ready=lambda: True,
            abort=lambda reason: self.fail(f"unexpected Land abort: {reason}"),
            relinquish_control=relinquished.append,
        )

        MISSION.DeliveryMission.safety_check(mission)

        self.assertEqual(len(relinquished), 1)
        self.assertIn("left Offboard", relinquished[0])

    def test_relinquish_stops_targets_and_commands_without_requesting_land(self):
        events = []
        transitions = []
        cleared = []
        mission = SimpleNamespace(
            control_relinquished=False,
            abort_reason=None,
            target=(1.0, 2.0, -1.0),
            result=None,
            clear_command=lambda: cleared.append(True),
            log_event=lambda event, detail="": events.append((event, detail)),
            transition=lambda state, detail="": transitions.append((state, detail)),
        )

        MISSION.DeliveryMission.relinquish_control(mission, "operator selected POSCTL")

        self.assertTrue(mission.control_relinquished)
        self.assertIsNone(mission.target)
        self.assertEqual(mission.result, MISSION.RESULT_CONTROL_RELINQUISHED)
        self.assertEqual(cleared, [True])
        self.assertEqual(transitions, [("FAILED", "operator selected POSCTL")])
        self.assertEqual(events[0][0], "CONTROL_RELINQUISHED")

    def test_offboard_control_flag_loss_relinquishes_even_before_nav_update(self):
        relinquished = []
        flags = SimpleNamespace(
            **{name: False for name in MISSION.FAILSAFE_FLAG_NAMES},
            battery_warning=0,
            offboard_control_signal_lost=False,
        )
        mission = SimpleNamespace(
            state="TAKEOFF",
            args=SimpleNamespace(mode="flight"),
            age=lambda _name: 0.0,
            STATUS_STALE_ABORT_SECONDS=2.0,
            POSITION_STALE_ABORT_SECONDS=2.0,
            failsafe_flags=flags,
            status=SimpleNamespace(
                arming_state=MISSION.ARMED,
                nav_state=MISSION.NAV_OFFBOARD,
                failsafe=False,
                failure_detector_status=0,
                gcs_connection_lost=False,
            ),
            control=SimpleNamespace(flag_control_offboard_enabled=False),
            position=valid_position(),
            position_reset_abort_reason=None,
            land=None,
            battery=None,
            endpoints_ready=lambda: True,
            abort=lambda reason: self.fail(f"unexpected Land abort: {reason}"),
            relinquish_control=relinquished.append,
        )

        MISSION.DeliveryMission.safety_check(mission)

        self.assertEqual(
            relinquished,
            ["PX4 control mode no longer reports Offboard enabled"],
        )

    def test_relinquished_publisher_returns_without_ros_publication(self):
        mission = SimpleNamespace(
            control_relinquished=True,
            land_mode_confirmed=False,
            target=(1.0, 2.0, -1.0),
        )

        self.assertIsNone(MISSION.DeliveryMission.publish_control(mission))

    def test_runtime_checks_wind_and_flight_time_limits(self):
        self.assertIn("wind_limit_exceeded", MISSION.FAILSAFE_FLAG_NAMES)
        self.assertIn("flight_time_limit_exceeded", MISSION.FAILSAFE_FLAG_NAMES)

    def test_runtime_checks_both_gcs_and_manual_control_loss(self):
        self.assertIn("gcs_connection_lost", MISSION.FAILSAFE_FLAG_NAMES)
        self.assertIn("manual_control_signal_lost", MISSION.FAILSAFE_FLAG_NAMES)

    def test_preflight_only_returns_before_any_active_transition(self):
        events = []
        mission = SimpleNamespace(
            args=SimpleNamespace(mode="preflight-only"),
            run_preflight=lambda: 0,
            log_event=lambda event, detail="": events.append((event, detail)),
            transition=lambda *_args: self.fail("active transition must not run"),
        )

        result = MISSION.DeliveryMission.run(mission)

        self.assertEqual(result, 0)
        self.assertEqual(events, [("PREFLIGHT_ONLY", "publishes=0 commands=0")])

    def test_takeoff_state_timeout_aborts(self):
        reasons = []
        mission = SimpleNamespace(
            state="TAKEOFF",
            state_entered=time.monotonic() - 16.0,
            abort=reasons.append,
        )

        MISSION.DeliveryMission.tick_state(mission)

        self.assertEqual(reasons, ["takeoff timeout"])

    def test_ack_is_paired_by_vehicle_command(self):
        mission = SimpleNamespace(
            received_at={},
            last_ack={},
            log_event=lambda *_args: None,
        )
        ack = SimpleNamespace(
            command=MISSION.CMD_ARM_DISARM,
            result=MISSION.ACK_ACCEPTED,
            result_param1=0,
            result_param2=0,
        )

        MISSION.DeliveryMission._ack_cb(mission, ack)

        self.assertEqual(
            mission.last_ack[MISSION.CMD_ARM_DISARM], MISSION.ACK_ACCEPTED
        )
        self.assertNotIn(MISSION.CMD_LAND, mission.last_ack)

    def test_land_ack_does_not_stop_heartbeat_before_auto_land_nav_state(self):
        transitions = []
        mission = SimpleNamespace(
            state="REQUEST_LAND",
            state_entered=time.monotonic(),
            status=SimpleNamespace(nav_state=MISSION.NAV_OFFBOARD),
            last_ack={MISSION.CMD_LAND: MISSION.ACK_ACCEPTED},
            land=SimpleNamespace(landed=False),
            land_mode_confirmed=False,
            command_deadline=time.monotonic() + 5.0,
            abort_land_deadline=None,
            begin_command=lambda *_args: None,
            send_command_if_due=lambda: None,
            log_event=lambda *_args: None,
            transition=lambda state, detail="": transitions.append((state, detail)),
        )

        MISSION.DeliveryMission.tick_state(mission)

        self.assertFalse(mission.land_mode_confirmed)
        self.assertEqual(transitions, [])

    def test_auto_land_nav_state_stops_heartbeat_and_enters_wait_landed(self):
        transitions = []
        mission = SimpleNamespace(
            state="REQUEST_LAND",
            state_entered=time.monotonic(),
            status=SimpleNamespace(nav_state=MISSION.NAV_LAND),
            last_ack={},
            land=SimpleNamespace(landed=False),
            land_mode_confirmed=False,
            log_event=lambda *_args: None,
            transition=lambda state, detail="": transitions.append((state, detail)),
        )

        MISSION.DeliveryMission.tick_state(mission)

        self.assertTrue(mission.land_mode_confirmed)
        self.assertEqual(transitions, [("WAIT_LANDED", "")])

    def test_px4_v114_auto_disarm_land_reason_completes_fallback(self):
        transitions = []
        events = []
        mission = SimpleNamespace(
            state="WAIT_AUTO_DISARM_FALLBACK",
            state_entered=time.monotonic(),
            status=SimpleNamespace(
                arming_state=MISSION.DISARMED,
                latest_disarming_reason=6,
            ),
            control=SimpleNamespace(flag_armed=False),
            abort_reason=None,
            result=None,
            log_event=lambda event, detail="": events.append((event, detail)),
            transition=lambda state, detail="": transitions.append((state, detail)),
        )

        MISSION.DeliveryMission.tick_state(mission)

        self.assertEqual(MISSION.PX4_V114_AUTO_DISARM_LAND_REASON, 6)
        self.assertEqual(mission.result, 0)
        self.assertEqual(
            transitions,
            [("COMPLETE", "PX4 AUTO_DISARM_LAND confirmed")],
        )
        self.assertEqual(events, [])

    def test_px4_v114_auto_disarm_preflight_reason_is_rejected(self):
        transitions = []
        events = []
        mission = SimpleNamespace(
            state="WAIT_AUTO_DISARM_FALLBACK",
            state_entered=time.monotonic(),
            status=SimpleNamespace(
                arming_state=MISSION.DISARMED,
                latest_disarming_reason=7,
            ),
            control=SimpleNamespace(flag_armed=False),
            abort_reason=None,
            result=None,
            log_event=lambda event, detail="": events.append((event, detail)),
            transition=lambda state, detail="": transitions.append((state, detail)),
        )

        MISSION.DeliveryMission.tick_state(mission)

        self.assertEqual(mission.result, 16)
        self.assertEqual(
            transitions,
            [("FAILED", "disarm was not PX4 auto-disarm-land")],
        )
        self.assertEqual(
            events,
            [("UNEXPECTED_DISARM_REASON", "reason=7 expected=6")],
        )

    def test_forward_goal_is_refreshed_from_latest_hold_position_and_heading(self):
        events = []
        mission = SimpleNamespace(
            args=SimpleNamespace(forward_distance=5.0),
            position=valid_position(x=4.0, y=6.0, z=-1.1, heading=math.pi / 2),
            takeoff=(1.0, 2.0, -1.0),
            goal=(99.0, 99.0, -1.0),
            target=None,
            yaw_target=0.0,
            log_event=lambda event, detail="": events.append((event, detail)),
        )

        MISSION.DeliveryMission.refresh_forward_goal(mission)

        self.assertAlmostEqual(mission.goal[0], 4.0)
        self.assertAlmostEqual(mission.goal[1], 11.0)
        self.assertAlmostEqual(mission.goal[2], -1.0)
        self.assertEqual(mission.target, mission.goal)
        self.assertAlmostEqual(mission.yaw_target, math.pi / 2)
        self.assertEqual(events[0][0], "ROUTE_REFRESH")

    def test_local_position_reset_shifts_targets_and_material_reset_requests_land(self):
        events = []
        mission = SimpleNamespace(
            reset_counters={"xy": 0, "z": 0, "vxy": 0, "vz": 0, "heading": 0},
            start=(1.0, 2.0, -0.2, 0.3),
            takeoff=(1.0, 2.0, -1.2),
            goal=(6.0, 2.0, -1.2),
            target=(1.0, 2.0, -1.2),
            yaw_target=0.3,
            position_reset_abort_reason=None,
            XY_RESET_ABORT_METERS=0.25,
            Z_RESET_ABORT_METERS=0.20,
            log_event=lambda event, detail="": events.append((event, detail)),
        )
        mission.shift_stored_route = lambda dx=0.0, dy=0.0, dz=0.0: (
            MISSION.DeliveryMission.shift_stored_route(mission, dx, dy, dz)
        )
        reset = valid_position(
            xy_reset_counter=1,
            delta_xy=[0.30, -0.10],
            z_reset_counter=1,
            delta_z=0.05,
            heading_reset_counter=1,
            delta_heading=0.02,
        )

        MISSION.DeliveryMission.handle_position_resets(mission, reset)

        self.assertEqual(mission.target, (1.3, 1.9, -1.15))
        self.assertAlmostEqual(mission.yaw_target, 0.32)
        self.assertIn("XY reset", mission.position_reset_abort_reason)
        self.assertTrue(any(event == "EKF_XY_RESET" for event, _ in events))
        self.assertTrue(any(event == "EKF_Z_RESET" for event, _ in events))
        self.assertTrue(any(event == "EKF_HEADING_RESET" for event, _ in events))

    def test_heartbeat_pause_prevents_waypoint_state_advance(self):
        aborts = []
        advances = []
        mission = SimpleNamespace(
            previous_publish_ns=time.monotonic_ns() - 300_000_000,
            land_mode_confirmed=False,
            abort_reason=None,
            abort=aborts.append,
            age=lambda _name: 0.0,
            POSITION_STALE_FREEZE_SECONDS=1.0,
            tick_state=lambda: advances.append("advanced"),
        )
        mission.abort_if_heartbeat_overdue = lambda: (
            MISSION.DeliveryMission.abort_if_heartbeat_overdue(mission)
        )

        result = MISSION.DeliveryMission.advance_state_if_safe(mission)

        self.assertFalse(result)
        self.assertEqual(advances, [])
        self.assertEqual(len(aborts), 1)
        self.assertIn("heartbeat gap", aborts[0])


if __name__ == "__main__":
    unittest.main()
