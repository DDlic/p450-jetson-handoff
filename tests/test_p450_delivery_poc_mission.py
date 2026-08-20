#!/usr/bin/env python3
"""Offline tests for the P450 delivery mission safety envelope."""

import importlib.util
import math
from pathlib import Path
from types import SimpleNamespace
import time
import unittest


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
    def test_dry_run_defaults_are_allowed(self):
        self.assertIsNone(MISSION.validate_args(arguments()))

    def test_height_above_delivery_scope_is_refused(self):
        error = MISSION.validate_args(arguments(takeoff_height=1.01))
        self.assertIn("0.1..1.0", error)

    def test_forward_distance_above_delivery_scope_is_refused(self):
        error = MISSION.validate_args(arguments(forward_distance=5.01))
        self.assertIn("0..5", error)

    def test_ground_sequence_requires_props_removed_confirmation(self):
        error = MISSION.validate_args(
            arguments(mode="ground-sequence", test_id="P450_GROUND_TEST")
        )
        self.assertIn(MISSION.GROUND_CONFIRMATION, error)

    def test_flight_requires_distinct_operator_confirmation(self):
        error = MISSION.validate_args(
            arguments(mode="flight", test_id="P450_FLIGHT_TEST", allow_armed=True)
        )
        self.assertIn(MISSION.FLIGHT_CONFIRMATION, error)


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

    def test_final_heading_is_not_required_until_after_flight_takeoff(self):
        self.assertFalse(
            MISSION.final_heading_required("ground-sequence", "GROUND_ARMED_HOLD")
        )
        self.assertFalse(MISSION.final_heading_required("flight", "TAKEOFF"))
        self.assertTrue(
            MISSION.final_heading_required("flight", "HOLD_AFTER_TAKEOFF")
        )
        self.assertTrue(MISSION.final_heading_required("flight", "MOVE_FORWARD"))

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

    def test_runtime_allows_pending_final_heading_during_takeoff_only(self):
        def run_safety(state):
            aborts = []
            flags = SimpleNamespace(
                **{name: False for name in MISSION.FAILSAFE_FLAG_NAMES},
                battery_warning=0,
                offboard_control_signal_lost=False,
            )
            mission = SimpleNamespace(
                state=state,
                args=SimpleNamespace(mode="flight"),
                age=lambda _name: 0.0,
                STATUS_STALE_ABORT_SECONDS=2.0,
                POSITION_STALE_ABORT_SECONDS=2.0,
                failsafe_flags=flags,
                status=SimpleNamespace(
                    failsafe=False,
                    failure_detector_status=0,
                    gcs_connection_lost=False,
                ),
                position=valid_position(heading_good_for_control=False),
                land=None,
                battery=None,
                endpoints_ready=lambda: True,
                abort=aborts.append,
            )
            MISSION.DeliveryMission.safety_check(mission)
            return aborts

        self.assertEqual(run_safety("TAKEOFF"), [])
        self.assertEqual(
            run_safety("HOLD_AFTER_TAKEOFF"),
            ["final in-flight heading alignment did not complete"],
        )

    def test_runtime_checks_wind_and_flight_time_limits(self):
        self.assertIn("wind_limit_exceeded", MISSION.FAILSAFE_FLAG_NAMES)
        self.assertIn("flight_time_limit_exceeded", MISSION.FAILSAFE_FLAG_NAMES)

    def test_runtime_checks_both_gcs_and_manual_control_loss(self):
        self.assertIn("gcs_connection_lost", MISSION.FAILSAFE_FLAG_NAMES)
        self.assertIn("manual_control_signal_lost", MISSION.FAILSAFE_FLAG_NAMES)

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

    def test_land_ack_enters_wait_landed_branch(self):
        transitions = []
        mission = SimpleNamespace(
            state="REQUEST_LAND",
            state_entered=time.monotonic(),
            status=SimpleNamespace(nav_state=-1),
            last_ack={MISSION.CMD_LAND: MISSION.ACK_ACCEPTED},
            land=SimpleNamespace(landed=False),
            land_mode_confirmed=False,
            transition=lambda state, detail="": transitions.append((state, detail)),
        )

        MISSION.DeliveryMission.tick_state(mission)

        self.assertTrue(mission.land_mode_confirmed)
        self.assertEqual(transitions, [("WAIT_LANDED", "")])

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
