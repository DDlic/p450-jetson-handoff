#!/usr/bin/env python3
"""Offline safety tests for the propeller-free disarmed command soak."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/p450_disarmed_command_soak.py"
SPEC = importlib.util.spec_from_file_location("p450_disarmed_command_soak", SCRIPT)
SOAK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SOAK)


def arguments(**overrides):
    values = {
        "test_id": "P450_DISARMED_SOAK_TEST",
        "duration": 900.0,
        "rate": 10.0,
        "virtual_height": 1.0,
        "virtual_forward": 5.0,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class CommandAllowlistTests(unittest.TestCase):
    def test_arm_disarm_is_hard_blocked(self):
        self.assertFalse(SOAK.command_is_allowed(SOAK.CMD_ARM_DISARM))
        self.assertNotIn(SOAK.CMD_ARM_DISARM, SOAK.SAFE_VEHICLE_COMMANDS)

    def test_delivery_non_arming_commands_are_allowed(self):
        self.assertTrue(SOAK.command_is_allowed(SOAK.CMD_SET_MODE))
        self.assertTrue(SOAK.command_is_allowed(SOAK.CMD_LAND))

    def test_nav_state_can_confirm_commands_without_ack_bridge(self):
        offboard = (1.0, 6.0, 0, 0, 0, 0, 0)
        self.assertTrue(
            SOAK.command_confirmed_by_nav(SOAK.CMD_SET_MODE, offboard, SOAK.NAV_OFFBOARD)
        )
        self.assertTrue(
            SOAK.command_confirmed_by_nav(SOAK.CMD_LAND, (0,) * 7, SOAK.NAV_LAND)
        )
        self.assertFalse(
            SOAK.command_confirmed_by_nav(SOAK.CMD_SET_MODE, offboard, SOAK.NAV_LAND)
        )


class ArgumentTests(unittest.TestCase):
    def test_default_15_minute_soak_is_valid(self):
        self.assertIsNone(SOAK.validate_args(arguments()))

    def test_five_minute_outdoor_soak_is_valid(self):
        self.assertIsNone(SOAK.validate_args(arguments(duration=300.0)))

    def test_duration_outside_5_to_20_minutes_is_refused(self):
        self.assertIn("300..1200", SOAK.validate_args(arguments(duration=299.0)))
        self.assertIn("300..1200", SOAK.validate_args(arguments(duration=1201.0)))

    def test_non_ten_hz_rate_is_refused(self):
        self.assertIn("10 Hz", SOAK.validate_args(arguments(rate=5.0)))


class VirtualRouteTests(unittest.TestCase):
    def test_virtual_phases_follow_takeoff_hold_forward_order(self):
        start = (10.0, 20.0, -0.5, 0.0)
        self.assertEqual(
            SOAK.virtual_target(start, 0.0, 100.0, 1.0, 5.0),
            ("VIRTUAL_TAKEOFF", (10.0, 20.0, -1.5)),
        )
        self.assertEqual(
            SOAK.virtual_target(start, 30.0, 100.0, 1.0, 5.0),
            ("HOLD_AFTER_TAKEOFF", (10.0, 20.0, -1.5)),
        )
        self.assertEqual(
            SOAK.virtual_target(start, 60.0, 100.0, 1.0, 5.0),
            ("VIRTUAL_FORWARD", (15.0, 20.0, -1.5)),
        )
        self.assertEqual(
            SOAK.virtual_target(start, 90.0, 100.0, 1.0, 5.0),
            ("VIRTUAL_FORWARD", (15.0, 20.0, -1.5)),
        )


if __name__ == "__main__":
    unittest.main()
