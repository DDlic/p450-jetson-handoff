#!/usr/bin/env python3
"""Offline tests for the P450 delivery mission safety envelope."""

import importlib.util
import math
from pathlib import Path
from types import SimpleNamespace
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


if __name__ == "__main__":
    unittest.main()
