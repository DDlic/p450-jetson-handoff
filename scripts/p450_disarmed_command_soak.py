#!/usr/bin/env python3
"""Propeller-free, disarmed PX4 command-path and telemetry soak.

This diagnostic follows the delivery mission in its original order, with only
the Arm/Disarm command omitted:

    hold/preroll -> Offboard -> [skip Arm] -> takeoff setpoint -> hold ->
    forward setpoint -> PX4 Land

It exercises Reliable OffboardControlMode and TrajectorySetpoint at 10 Hz,
VEHICLE_CMD_DO_SET_MODE for Offboard, VEHICLE_CMD_NAV_LAND, and the same PX4
telemetry/ACK paths used by the mission.

VEHICLE_CMD_COMPONENT_ARM_DISARM is not in the command allowlist and cannot be
published by this program.  Any observed armed state aborts the diagnostic.
"""

import argparse
import csv
import math
import re
import time
from pathlib import Path

import rclpy
from px4_msgs.msg import (
    FailsafeFlags,
    OffboardControlMode,
    TrajectorySetpoint,
    VehicleCommand,
    VehicleCommandAck,
    VehicleControlMode,
    VehicleLocalPosition,
    VehicleStatus,
)
from rclpy.node import Node
from rclpy.qos import (
    QoSDurabilityPolicy,
    QoSHistoryPolicy,
    QoSProfile,
    QoSReliabilityPolicy,
)


SD_MOUNT = Path("/media/p450/P450_DATA")
DEFAULT_LOG_ROOT = SD_MOUNT / "builds/NX-user-storage/rosbags"
TEST_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{5,95}$")

DISARMED = VehicleStatus.ARMING_STATE_STANDBY
NAV_LAND = VehicleStatus.NAVIGATION_STATE_AUTO_LAND
NAV_OFFBOARD = VehicleStatus.NAVIGATION_STATE_OFFBOARD
CMD_SET_MODE = VehicleCommand.VEHICLE_CMD_DO_SET_MODE
CMD_ARM_DISARM = VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM
CMD_LAND = VehicleCommand.VEHICLE_CMD_NAV_LAND

MAV_MODE_FLAG_CUSTOM_MODE_ENABLED = 1.0
PX4_CUSTOM_MAIN_MODE_OFFBOARD = 6.0

SAFE_VEHICLE_COMMANDS = frozenset((CMD_SET_MODE, CMD_LAND))


def finite(*values):
    return all(math.isfinite(value) for value in values)


def command_is_allowed(command):
    """Return whether this diagnostic may publish a VehicleCommand ID."""
    return command in SAFE_VEHICLE_COMMANDS and command != CMD_ARM_DISARM

def command_confirmed_by_nav(command, params, nav_state):
    """Use VehicleStatus when VehicleCommandAck is not bridged by PX4."""
    if command == CMD_SET_MODE and len(params) > 1:
        return params[1] == PX4_CUSTOM_MAIN_MODE_OFFBOARD and nav_state == NAV_OFFBOARD
    if command == CMD_LAND:
        return nav_state == NAV_LAND
    return False


def virtual_target(start, elapsed, duration, height, forward):
    """Return a changing virtual NED target without requiring vehicle motion."""
    x0, y0, z0, heading = start
    fraction = min(max(elapsed / duration, 0.0), 1.0)
    if fraction < 0.25:
        return "VIRTUAL_TAKEOFF", (x0, y0, z0 - height)
    if fraction < 0.35:
        return "HOLD_AFTER_TAKEOFF", (x0, y0, z0 - height)
    return (
        "VIRTUAL_FORWARD",
        (
            x0 + forward * math.cos(heading),
            y0 + forward * math.sin(heading),
            z0 - height,
        ),
    )


class DisarmedCommandSoak(Node):
    TELEMETRY_STALE_SECONDS = 2.0
    COMMAND_RETRY_SECONDS = 0.5
    COMMAND_MAX_ATTEMPTS = 6
    LOCAL_DISCONNECT_GAP_MS = 1000.0

    def __init__(self, args, log_dir):
        super().__init__("p450_disarmed_command_soak")
        self.args = args
        self.log_dir = log_dir
        self.started_ns = time.monotonic_ns()
        self.status = None
        self.control = None
        self.failsafe_flags = None
        self.position = None
        self.received_at = {}
        self.pending_command = None
        self.pending_ack = None
        self.publish_count = 0
        self.previous_publish_ns = None
        self.publish_gaps_ms = []
        self.next_publish = time.monotonic()
        self.start = None
        self.phase = "PRECHECK"
        self.require_offboard = False

        telemetry_qos = QoSProfile(
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            durability=QoSDurabilityPolicy.VOLATILE,
        )
        reliable_qos = QoSProfile(
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.VOLATILE,
        )
        command_qos = QoSProfile(
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            durability=QoSDurabilityPolicy.VOLATILE,
        )

        self.create_subscription(
            VehicleStatus, "/fmu/out/vehicle_status", self._status_cb, telemetry_qos
        )
        self.create_subscription(
            VehicleControlMode,
            "/fmu/out/vehicle_control_mode",
            self._control_cb,
            telemetry_qos,
        )
        self.create_subscription(
            FailsafeFlags,
            "/fmu/out/failsafe_flags",
            self._failsafe_cb,
            telemetry_qos,
        )
        self.create_subscription(
            VehicleLocalPosition,
            "/fmu/out/vehicle_local_position",
            self._position_cb,
            telemetry_qos,
        )
        self.create_subscription(
            VehicleCommandAck,
            "/fmu/out/vehicle_command_ack",
            self._ack_cb,
            telemetry_qos,
        )

        self.offboard_pub = self.create_publisher(
            OffboardControlMode, "/fmu/in/offboard_control_mode", reliable_qos
        )
        self.setpoint_pub = self.create_publisher(
            TrajectorySetpoint, "/fmu/in/trajectory_setpoint", command_qos
        )
        self.command_pub = self.create_publisher(
            VehicleCommand, "/fmu/in/vehicle_command", command_qos
        )

        self.events_file = (log_dir / "SOAK_EVENTS.csv").open(
            "w", newline="", buffering=1
        )
        self.events = csv.writer(self.events_file, lineterminator="\n")
        self.events.writerow(
            ["monotonic_ns", "elapsed_ms", "phase", "event", "detail"]
        )
        self.samples_file = (log_dir / "SOAK_SAMPLES.csv").open(
            "w", newline="", buffering=1
        )
        self.samples = csv.writer(self.samples_file, lineterminator="\n")
        self.samples.writerow(
            [
                "sequence",
                "monotonic_ns",
                "elapsed_ms",
                "publish_gap_ms",
                "phase",
                "offboard_subscriptions",
                "setpoint_subscriptions",
                "command_subscriptions",
                "arming_state",
                "nav_state",
                "failsafe",
                "target_x",
                "target_y",
                "target_z",
                "actual_x",
                "actual_y",
                "actual_z",
            ]
        )
        self.log_event(
            "START",
            f"test_id={args.test_id} duration={args.duration} rate={args.rate}",
        )

    def _stamp(self, name, message):
        setattr(self, name, message)
        self.received_at[name] = time.monotonic()

    def _status_cb(self, message):
        self._stamp("status", message)

    def _control_cb(self, message):
        self._stamp("control", message)

    def _failsafe_cb(self, message):
        self._stamp("failsafe_flags", message)

    def _position_cb(self, message):
        self._stamp("position", message)

    def _ack_cb(self, message):
        if message.command == self.pending_command:
            self.pending_ack = int(message.result)
        self.log_event(
            "COMMAND_ACK",
            f"command={message.command} result={message.result} "
            f"param1={message.result_param1} param2={message.result_param2}",
        )

    def log_event(self, event, detail=""):
        now_ns = time.monotonic_ns()
        self.events.writerow(
            [
                now_ns,
                f"{(now_ns - self.started_ns) / 1_000_000.0:.3f}",
                self.phase,
                event,
                detail,
            ]
        )
        print(f"SOAK {self.phase} {event} {detail}".rstrip(), flush=True)

    def age(self, name):
        received = self.received_at.get(name)
        return math.inf if received is None else time.monotonic() - received

    def endpoints_ready(self):
        return (
            self.offboard_pub.get_subscription_count() == 1
            and self.setpoint_pub.get_subscription_count() >= 1
            and self.command_pub.get_subscription_count() >= 1
        )

    def check_safety(self):
        for name in ("status", "control", "failsafe_flags", "position"):
            if self.age(name) > self.TELEMETRY_STALE_SECONDS:
                return f"{name} telemetry stale for more than 2 s"
        if self.status.arming_state != DISARMED or self.control.flag_armed:
            return (
                "armed state observed; script never sends Arm/Disarm "
                f"arming_state={self.status.arming_state} flag_armed={int(self.control.flag_armed)}"
            )
        if self.status.failsafe:
            return "PX4 failsafe became active"
        if self.require_offboard and self.status.nav_state != NAV_OFFBOARD:
            return f"PX4 left Offboard unexpectedly nav_state={self.status.nav_state}"
        if self.status.failure_detector_status != 0:
            return f"failure_detector_status={self.status.failure_detector_status}"
        if not self.endpoints_ready():
            return (
                "DDS endpoint mismatch "
                f"offboard={self.offboard_pub.get_subscription_count()} "
                f"setpoint={self.setpoint_pub.get_subscription_count()} "
                f"command={self.command_pub.get_subscription_count()}"
            )
        return None

    def wait_ready(self):
        deadline = time.monotonic() + 20.0
        while time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
            if all(
                self.age(name) <= 1.0
                for name in ("status", "control", "failsafe_flags", "position")
            ) and self.endpoints_ready():
                break
        reason = self.check_safety()
        if reason:
            self.log_event("PREFLIGHT_REFUSED", reason)
            return False
        if not finite(
            self.position.x,
            self.position.y,
            self.position.z,
            self.position.heading,
        ):
            self.log_event("PREFLIGHT_REFUSED", "local position contains non-finite data")
            return False
        self.start = (
            float(self.position.x),
            float(self.position.y),
            float(self.position.z),
            float(self.position.heading),
        )
        self.log_event(
            "PREFLIGHT_PASS",
            f"start={self.start} heading_good={int(self.position.heading_good_for_control)} "
            f"xy_valid={int(self.position.xy_valid)} z_valid={int(self.position.z_valid)}",
        )
        return True

    def publish_control(self, target):
        now_ns = time.monotonic_ns()
        gap_ms = math.nan
        if self.previous_publish_ns is not None:
            gap_ms = (now_ns - self.previous_publish_ns) / 1_000_000.0
            self.publish_gaps_ms.append(gap_ms)
            if gap_ms > self.LOCAL_DISCONNECT_GAP_MS:
                raise RuntimeError(
                    f"local publish gap {gap_ms:.3f} ms exceeded "
                    f"{self.LOCAL_DISCONNECT_GAP_MS:.0f} ms continuity limit"
                )
        self.previous_publish_ns = now_ns

        timestamp = self.get_clock().now().nanoseconds // 1000
        mode = OffboardControlMode()
        mode.timestamp = timestamp
        mode.position = True
        mode.velocity = False
        mode.acceleration = False
        mode.attitude = False
        mode.body_rate = False
        mode.actuator = False

        setpoint = TrajectorySetpoint()
        setpoint.timestamp = timestamp
        setpoint.position = [target[0], target[1], target[2]]
        setpoint.velocity = [math.nan, math.nan, math.nan]
        setpoint.acceleration = [math.nan, math.nan, math.nan]
        setpoint.jerk = [math.nan, math.nan, math.nan]
        setpoint.yaw = self.start[3]
        setpoint.yawspeed = math.nan

        self.offboard_pub.publish(mode)
        self.setpoint_pub.publish(setpoint)
        self.publish_count += 1
        self.samples.writerow(
            [
                self.publish_count,
                now_ns,
                f"{(now_ns - self.started_ns) / 1_000_000.0:.3f}",
                "" if math.isnan(gap_ms) else f"{gap_ms:.3f}",
                self.phase,
                self.offboard_pub.get_subscription_count(),
                self.setpoint_pub.get_subscription_count(),
                self.command_pub.get_subscription_count(),
                self.status.arming_state,
                self.status.nav_state,
                int(self.status.failsafe),
                f"{target[0]:.4f}",
                f"{target[1]:.4f}",
                f"{target[2]:.4f}",
                f"{self.position.x:.4f}",
                f"{self.position.y:.4f}",
                f"{self.position.z:.4f}",
            ]
        )

    def spin_and_publish(self, target):
        rclpy.spin_once(self, timeout_sec=0.005)
        reason = self.check_safety()
        if reason:
            raise RuntimeError(reason)
        now = time.monotonic()
        if now >= self.next_publish:
            self.publish_control(target)
            self.next_publish += 1.0 / self.args.rate
            if self.next_publish < now - 1.0 / self.args.rate:
                self.next_publish = now + 1.0 / self.args.rate

    def send_vehicle_command(self, command, params, confirmation):
        if not command_is_allowed(command):
            raise RuntimeError(f"VehicleCommand {command} is not in disarmed allowlist")
        message = VehicleCommand()
        message.timestamp = self.get_clock().now().nanoseconds // 1000
        message.param1 = float(params[0])
        message.param2 = float(params[1])
        message.param3 = float(params[2])
        message.param4 = float(params[3])
        message.param5 = float(params[4])
        message.param6 = float(params[5])
        message.param7 = float(params[6])
        message.command = command
        message.target_system = 1
        message.target_component = 1
        message.source_system = 1
        message.source_component = 1
        message.confirmation = confirmation
        message.from_external = True
        self.command_pub.publish(message)
        self.log_event(
            "COMMAND_SEND", f"command={command} confirmation={confirmation}"
        )

    def exchange_command(self, label, command, params, target):
        self.phase = label
        self.pending_command = command
        self.pending_ack = None
        next_send = 0.0
        attempts = 0
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            self.spin_and_publish(target)
            if command_confirmed_by_nav(command, params, self.status.nav_state):
                self.log_event(
                    "COMMAND_STATE_CONFIRMED",
                    f"command={command} nav_state={self.status.nav_state}",
                )
                self.pending_command = None
                return VehicleCommandAck.VEHICLE_CMD_RESULT_ACCEPTED
            if self.pending_ack is not None:
                result = self.pending_ack
                self.log_event(
                    "COMMAND_ROUNDTRIP", f"command={command} ack_result={result}"
                )
                self.pending_command = None
                return result
            now = time.monotonic()
            if now >= next_send and attempts < self.COMMAND_MAX_ATTEMPTS:
                self.send_vehicle_command(command, params, attempts)
                attempts += 1
                next_send = now + self.COMMAND_RETRY_SECONDS
        self.log_event("COMMAND_UNCONFIRMED", f"command={command} attempts={attempts} ack={self.pending_ack}")
        self.pending_command = None
        return None

    def run(self):
        if not self.wait_ready():
            return 2
        if self.args.preflight_only:
            self.phase = "COMPLETE"
            self.log_event("PREFLIGHT_ONLY_PASS", "publishes=0 commands=0")
            return 0
        target = self.start[:3]
        self.phase = "PREROLL"
        preroll_end = time.monotonic() + 2.0
        try:
            while time.monotonic() < preroll_end:
                self.spin_and_publish(target)

            offboard_ack = self.exchange_command(
                "REQUEST_OFFBOARD_DISARMED",
                CMD_SET_MODE,
                (
                    MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
                    PX4_CUSTOM_MAIN_MODE_OFFBOARD,
                    0,
                    0,
                    0,
                    0,
                    0,
                ),
                target,
            )
            if offboard_ack not in (
                VehicleCommandAck.VEHICLE_CMD_RESULT_ACCEPTED,
                VehicleCommandAck.VEHICLE_CMD_RESULT_IN_PROGRESS,
            ):
                raise RuntimeError(
                    f"Offboard command was not accepted ack_result={offboard_ack}"
                )
            offboard_deadline = time.monotonic() + 3.0
            while (
                self.status.nav_state != NAV_OFFBOARD
                and time.monotonic() < offboard_deadline
            ):
                self.spin_and_publish(target)
            if self.status.nav_state != NAV_OFFBOARD:
                raise RuntimeError(
                    f"PX4 did not enter Offboard nav_state={self.status.nav_state}"
                )
            self.require_offboard = True
            self.log_event("OFFBOARD_CONFIRMED", "vehicle remains disarmed")

            soak_started = time.monotonic()
            soak_end = soak_started + self.args.duration
            last_phase = None
            while time.monotonic() < soak_end:
                elapsed = time.monotonic() - soak_started
                phase, target = virtual_target(
                    self.start,
                    elapsed,
                    self.args.duration,
                    self.args.virtual_height,
                    self.args.virtual_forward,
                )
                if phase != last_phase:
                    self.phase = phase
                    self.log_event("PHASE_TARGET", f"target={target}")
                    last_phase = phase
                self.spin_and_publish(target)

            self.require_offboard = False
            land_ack = self.exchange_command(
                "REQUEST_LAND_DISARMED",
                CMD_LAND,
                (0, 0, 0, math.nan, math.nan, math.nan, math.nan),
                target,
            )
            if land_ack not in (
                VehicleCommandAck.VEHICLE_CMD_RESULT_ACCEPTED,
                VehicleCommandAck.VEHICLE_CMD_RESULT_IN_PROGRESS,
            ):
                raise RuntimeError(
                    f"PX4 Land command was not accepted ack_result={land_ack}"
                )
        except (KeyboardInterrupt, RuntimeError) as error:
            self.phase = "FAILED"
            self.log_event("ABORT", str(error))
            return 10

        self.phase = "COMPLETE"
        self.log_event(
            "PASS",
            "mission-order soak complete; Offboard held while disarmed; PX4 Land ACK accepted",
        )
        return 0

    def close(self):
        gaps = self.publish_gaps_ms
        self.log_event(
            "SUMMARY",
            f"publishes={self.publish_count} "
            f"max_gap_ms={(max(gaps) if gaps else 0.0):.3f} "
            f"over_150ms={sum(g > 150.0 for g in gaps)} "
            f"over_250ms={sum(g > 250.0 for g in gaps)} "
            f"over_500ms={sum(g > 500.0 for g in gaps)} "
            f"over_1000ms={sum(g > 1000.0 for g in gaps)}",
        )
        self.events_file.flush()
        self.events_file.close()
        self.samples_file.flush()
        self.samples_file.close()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-id", required=True)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--duration", type=float, default=900.0)
    parser.add_argument("--rate", type=float, default=10.0)
    parser.add_argument("--virtual-height", type=float, default=1.0)
    parser.add_argument("--virtual-forward", type=float, default=5.0)
    parser.add_argument("--log-root", default=str(DEFAULT_LOG_ROOT))
    return parser.parse_args()


def validate_args(args):
    if not args.test_id or not TEST_ID_RE.fullmatch(args.test_id):
        return "a safe --test-id is required"
    if not finite(
        args.duration,
        args.rate,
        args.virtual_height,
        args.virtual_forward,
    ):
        return "all numeric arguments must be finite"
    if not 300.0 <= args.duration <= 1200.0:
        return "duration must be within 300..1200 seconds"
    if args.rate != 10.0:
        return "this diagnostic requires exactly 10 Hz"
    if not 0.1 <= args.virtual_height <= 1.0:
        return "virtual height must be within 0.1..1.0 m"
    if not 0.0 <= args.virtual_forward <= 5.0:
        return "virtual forward distance must be within 0..5 m"
    if not SD_MOUNT.is_mount():
        return f"SD data volume is not mounted at {SD_MOUNT}"
    if CMD_ARM_DISARM in SAFE_VEHICLE_COMMANDS:
        return "internal safety invariant violated: Arm/Disarm is allowlisted"
    return None


def main():
    args = parse_args()
    error = validate_args(args)
    if error:
        print(f"REFUSED: {error}", flush=True)
        return 2
    log_dir = Path(args.log_root).expanduser().resolve() / args.test_id
    log_dir.mkdir(parents=True, exist_ok=False)
    print(f"SOAK_LOG_DIR={log_dir}", flush=True)
    print(
        f"SOAK_COMMAND_ALLOWLIST={sorted(SAFE_VEHICLE_COMMANDS)} "
        f"ARM_DISARM_COMMAND={CMD_ARM_DISARM} blocked=true",
        flush=True,
    )
    rclpy.init()
    node = DisarmedCommandSoak(args, log_dir)
    try:
        return node.run()
    finally:
        node.close()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
