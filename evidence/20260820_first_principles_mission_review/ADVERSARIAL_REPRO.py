#!/usr/bin/env python3
"""Reproduce current V3 state-machine counterexamples without ROS publication."""

import importlib.util
import time
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/p450_delivery_poc_mission.py"
SPEC = importlib.util.spec_from_file_location("p450_delivery_poc_mission", SCRIPT)
MISSION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MISSION)


def position(**overrides):
    fields = dict(
        xy_valid=True,
        z_valid=True,
        v_xy_valid=True,
        v_z_valid=True,
        xy_global=True,
        z_global=True,
        dead_reckoning=False,
        x=0.0,
        y=0.0,
        z=-1.0,
        vx=0.0,
        vy=0.0,
        vz=0.0,
        heading=0.0,
        heading_good_for_control=True,
    )
    fields.update(overrides)
    return SimpleNamespace(**fields)


def flags(**overrides):
    fields = {name: False for name in MISSION.FAILSAFE_FLAG_NAMES}
    fields.update(battery_warning=0, offboard_control_signal_lost=False)
    fields.update(overrides)
    return SimpleNamespace(**fields)


def safety_result(*, state="HOLD_AFTER_TAKEOFF", nav_state=MISSION.NAV_OFFBOARD,
                  heading_good=True, raw_gcs_lost=False, active_gcs_lost=False):
    aborts = []
    mission = SimpleNamespace(
        state=state,
        args=SimpleNamespace(mode="flight"),
        age=lambda _name: 0.0,
        STATUS_STALE_ABORT_SECONDS=2.0,
        POSITION_STALE_ABORT_SECONDS=2.0,
        failsafe_flags=flags(gcs_connection_lost=active_gcs_lost),
        status=SimpleNamespace(
            nav_state=nav_state,
            failsafe=False,
            failure_detector_status=0,
            gcs_connection_lost=raw_gcs_lost,
        ),
        control=SimpleNamespace(flag_control_offboard_enabled=nav_state == MISSION.NAV_OFFBOARD),
        position=position(heading_good_for_control=heading_good),
        land=None,
        battery=None,
        endpoints_ready=lambda: True,
        abort=aborts.append,
    )
    MISSION.DeliveryMission.safety_check(mission)
    return aborts


def main():
    cases = [
        ("baseline_offboard", safety_result()),
        ("low_alt_heading_pending_hold", safety_result(heading_good=False)),
        ("raw_gcs_lost_no_active_failsafe", safety_result(raw_gcs_lost=True)),
        ("active_gcs_failsafe", safety_result(active_gcs_lost=True)),
        ("rc_takeover_posctl", safety_result(nav_state=2)),
    ]
    for name, result in cases:
        print(f"{name}: {result}")

    transitions = []
    takeover = SimpleNamespace(
        state="HOLD_AFTER_TAKEOFF",
        state_entered=time.monotonic() - 3.0,
        args=SimpleNamespace(forward_distance=0.0),
        transition=lambda state, detail="": transitions.append((state, detail)),
    )
    MISSION.DeliveryMission.tick_state(takeover)
    print(f"rc_takeover_then_state_machine_transition: {transitions}")

    transitions = []
    landing = SimpleNamespace(
        state="REQUEST_LAND",
        state_entered=time.monotonic(),
        status=SimpleNamespace(nav_state=-1),
        last_ack={MISSION.CMD_LAND: MISSION.ACK_ACCEPTED},
        land=SimpleNamespace(landed=False),
        land_mode_confirmed=False,
        transition=lambda state, detail="": transitions.append((state, detail)),
    )
    MISSION.DeliveryMission.tick_state(landing)
    print(
        "land_ack_before_nav_land: "
        f"land_mode_confirmed={landing.land_mode_confirmed} transitions={transitions}"
    )


if __name__ == "__main__":
    main()
