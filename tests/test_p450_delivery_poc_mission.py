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
