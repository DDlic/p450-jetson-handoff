#!/usr/bin/env python3
"""Constrained P450 delivery PoC mission with fail-closed flight gates.

The active modes implement the repository delivery runbook:

    hold -> Offboard -> arm -> climb -> optional forward waypoint -> PX4 Land

No active mode is enabled by default.  Without an explicit mode this program
only prints the NED route that would be used.  It never force-disarms and it
hands landing to PX4 with VEHICLE_CMD_NAV_LAND.
"""

import argparse
import csv
import math
import os
import re
import time
from pathlib import Path

import rclpy
from px4_msgs.msg import (
    BatteryStatus,
    FailsafeFlags,
    OffboardControlMode,
    TrajectorySetpoint,
    VehicleCommand,
    VehicleCommandAck,
    VehicleControlMode,
    VehicleLandDetected,
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
ARMED = VehicleStatus.ARMING_STATE_ARMED
NAV_OFFBOARD = VehicleStatus.NAVIGATION_STATE_OFFBOARD
NAV_LAND = VehicleStatus.NAVIGATION_STATE_AUTO_LAND
AUTO_DISARM_LAND_REASON = VehicleStatus.ARM_DISARM_REASON_AUTO_DISARM_LAND

CMD_SET_MODE = VehicleCommand.VEHICLE_CMD_DO_SET_MODE
CMD_ARM_DISARM = VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM
CMD_LAND = VehicleCommand.VEHICLE_CMD_NAV_LAND
ACK_ACCEPTED = VehicleCommandAck.VEHICLE_CMD_RESULT_ACCEPTED
ACK_IN_PROGRESS = VehicleCommandAck.VEHICLE_CMD_RESULT_IN_PROGRESS

MAV_MODE_FLAG_CUSTOM_MODE_ENABLED = 1.0
PX4_CUSTOM_MAIN_MODE_OFFBOARD = 6.0

GROUND_CONFIRMATION = "PROPS_REMOVED_KILL_READY"
FLIGHT_CONFIRMATION = "PROPS_INSTALLED_AREA_CLEAR_KILL_READY"


def route_from_heading(x0, y0, z0, heading, height, forward):
    """Return takeoff and forward targets in PX4's local NED frame."""
    takeoff = (x0, y0, z0 - height)
    goal = (
        x0 + forward * math.cos(heading),
        y0 + forward * math.sin(heading),
        z0 - height,
    )
    return takeoff, goal


def finite(*values):
    return all(math.isfinite(value) for value in values)


class DeliveryMission(Node):
    HEARTBEAT_HZ = 10.0
    HEARTBEAT_PERIOD = 0.1
    PREROLL_SECONDS = 2.0
    COMMAND_RETRY_SECONDS = 0.5
    COMMAND_MAX_ATTEMPTS = 6
    STATUS_STALE_ABORT_SECONDS = 2.0
    POSITION_STALE_FREEZE_SECONDS = 1.0
    POSITION_STALE_ABORT_SECONDS = 2.0

    def __init__(self, args, log_dir):
        super().__init__("p450_delivery_poc_mission")
        self.args = args
        self.log_dir = log_dir
        self.started_ns = time.monotonic_ns()
        self.state = "PRECHECK"
        self.state_entered = time.monotonic()
        self.result = None
        self.abort_reason = None
        self.abort_land_deadline = None

        self.status = None
        self.control = None
        self.position = None
        self.land = None
        self.battery = None
        self.failsafe_flags = None
        self.received_at = {}
        self.last_ack = {}

        self.start = None
        self.takeoff = None
        self.goal = None
        self.target = None
        self.stable_since = None
        self.land_mode_confirmed = False

        self.command = None
        self.command_params = None
        self.command_attempts = 0
        self.next_command_send = 0.0
        self.command_deadline = 0.0

        self.publish_count = 0
        self.previous_publish_ns = None
        self.publish_gaps_ms = []
        self.next_publish = time.monotonic()

        subscription_qos = QoSProfile(
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
            VehicleStatus, "/fmu/out/vehicle_status", self._status_cb, subscription_qos
        )
        self.create_subscription(
            FailsafeFlags,
            "/fmu/out/failsafe_flags",
            self._failsafe_flags_cb,
            subscription_qos,
        )
        self.create_subscription(
            VehicleControlMode,
            "/fmu/out/vehicle_control_mode",
            self._control_cb,
            subscription_qos,
        )
        self.create_subscription(
            VehicleLocalPosition,
            "/fmu/out/vehicle_local_position",
            self._position_cb,
            subscription_qos,
        )
        self.create_subscription(
            VehicleLandDetected,
            "/fmu/out/vehicle_land_detected",
            self._land_cb,
            subscription_qos,
        )
        self.create_subscription(
            VehicleCommandAck,
            "/fmu/out/vehicle_command_ack",
            self._ack_cb,
            subscription_qos,
        )
        self.create_subscription(
            BatteryStatus,
            "/fmu/out/battery_status",
            self._battery_cb,
            subscription_qos,
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

        self.events_file = (log_dir / "MISSION_EVENTS.csv").open(
            "w", newline="", buffering=1
        )
        self.events = csv.writer(self.events_file, lineterminator="\n")
        self.events.writerow(
            ["monotonic_ns", "elapsed_ms", "state", "event", "detail"]
        )
        self.heartbeat_file = (log_dir / "HEARTBEAT.csv").open(
            "w", newline="", buffering=1
        )
        self.heartbeats = csv.writer(self.heartbeat_file, lineterminator="\n")
        self.heartbeats.writerow(
            [
                "sequence",
                "monotonic_ns",
                "elapsed_ms",
                "publish_gap_ms",
                "state",
                "offboard_subscriptions",
                "setpoint_subscriptions",
                "command_subscriptions",
                "arming_state",
                "nav_state",
                "failsafe",
                "x",
                "y",
                "z",
                "vx",
                "vy",
                "vz",
            ]
        )
        self.log_event("START", f"mode={args.mode} test_id={args.test_id}")

    def _stamp(self, name, message):
        setattr(self, name, message)
        self.received_at[name] = time.monotonic()

    def _status_cb(self, message):
        previous_arm = self.status.arming_state if self.status is not None else None
        previous_nav = self.status.nav_state if self.status is not None else None
        self._stamp("status", message)
        if message.arming_state != previous_arm:
            self.log_event("ARMING_STATE", str(message.arming_state))
        if message.nav_state != previous_nav:
            self.log_event("NAV_STATE", str(message.nav_state))

    def _failsafe_flags_cb(self, message):
        self._stamp("failsafe_flags", message)

    def _control_cb(self, message):
        self._stamp("control", message)

    def _position_cb(self, message):
        self._stamp("position", message)

    def _land_cb(self, message):
        previous = self.land.landed if self.land is not None else None
        self._stamp("land", message)
        if message.landed != previous:
            self.log_event(
                "LAND_STATE",
                f"landed={int(message.landed)} maybe={int(message.maybe_landed)} "
                f"ground={int(message.ground_contact)}",
            )

    def _battery_cb(self, message):
        self._stamp("battery", message)

    def _ack_cb(self, message):
        self.received_at["ack"] = time.monotonic()
        self.last_ack[message.command] = message.result
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
                self.state,
                event,
                detail,
            ]
        )
        print(f"MISSION {self.state} {event} {detail}".rstrip(), flush=True)

    def age(self, name):
        received = self.received_at.get(name)
        return math.inf if received is None else time.monotonic() - received

    def transition(self, state, detail=""):
        self.state = state
        self.state_entered = time.monotonic()
        self.stable_since = None
        self.clear_command()
        self.log_event("TRANSITION", detail)

    def clear_command(self):
        self.command = None
        self.command_params = None
        self.command_attempts = 0
        self.next_command_send = 0.0
        self.command_deadline = 0.0

    def begin_command(self, command, params, timeout):
        if self.command == command:
            return
        self.command = command
        self.command_params = params
        self.command_attempts = 0
        self.next_command_send = 0.0
        self.command_deadline = time.monotonic() + timeout
        self.last_ack.pop(command, None)
        self.log_event("COMMAND_BEGIN", f"command={command}")

    def send_command_if_due(self):
        if self.command is None:
            return
        now = time.monotonic()
        if now < self.next_command_send:
            return
        ack = self.last_ack.get(self.command)
        if ack in (ACK_ACCEPTED, ACK_IN_PROGRESS):
            return
        if self.command_attempts >= self.COMMAND_MAX_ATTEMPTS:
            return

        params = self.command_params
        message = VehicleCommand()
        message.timestamp = self.get_clock().now().nanoseconds // 1000
        message.param1 = float(params[0])
        message.param2 = float(params[1])
        message.param3 = float(params[2])
        message.param4 = float(params[3])
        message.param5 = float(params[4])
        message.param6 = float(params[5])
        message.param7 = float(params[6])
        message.command = self.command
        message.target_system = 1
        message.target_component = 1
        message.source_system = 1
        message.source_component = 1
        message.confirmation = self.command_attempts
        message.from_external = True
        self.command_pub.publish(message)
        self.command_attempts += 1
        self.next_command_send = now + self.COMMAND_RETRY_SECONDS
        self.log_event(
            "COMMAND_SEND",
            f"command={self.command} attempt={self.command_attempts}",
        )

    def endpoints_ready(self):
        return (
            self.offboard_pub.get_subscription_count() == 1
            and self.setpoint_pub.get_subscription_count() >= 1
            and self.command_pub.get_subscription_count() >= 1
        )

    def data_ready(self):
        return all(
            self.age(name) <= 1.0
            for name in ("status", "control", "position", "failsafe_flags")
        )

    def preflight_reasons(self):
        reasons = []
        if not self.data_ready():
            reasons.append("required PX4 telemetry is missing or stale")
            return reasons
        if self.status.arming_state != DISARMED or self.control.flag_armed:
            reasons.append("vehicle is not disarmed")
        if self.status.nav_state == NAV_OFFBOARD:
            reasons.append("vehicle is already in Offboard")
        if self.status.failsafe:
            reasons.append("PX4 failsafe is active")
        if not self.status.pre_flight_checks_pass:
            reasons.append("PX4 pre_flight_checks_pass is false")
        if self.land is not None and not self.land.landed:
            reasons.append("optional land detector does not report landed")
        flags = self.failsafe_flags
        for name in (
            "angular_velocity_invalid",
            "attitude_invalid",
            "local_altitude_invalid",
            "local_position_invalid",
            "local_velocity_invalid",
            "global_position_invalid",
            "home_position_invalid",
            "manual_control_signal_lost",
            "gcs_connection_lost",
            "battery_low_remaining_time",
            "battery_unhealthy",
            "primary_geofence_breached",
            "wind_limit_exceeded",
            "flight_time_limit_exceeded",
            "local_position_accuracy_low",
            "fd_critical_failure",
            "fd_esc_arming_failure",
            "fd_imbalanced_prop",
            "fd_motor_failure",
        ):
            if getattr(flags, name):
                reasons.append(f"failsafe flag {name}=true")
        if flags.battery_warning != 0:
            reasons.append(f"battery_warning={flags.battery_warning}")
        if not (
            self.position.xy_valid
            and self.position.z_valid
            and self.position.v_xy_valid
            and self.position.v_z_valid
            and self.position.xy_global
            and self.position.z_global
            and self.position.heading_good_for_control
            and not self.position.dead_reckoning
        ):
            reasons.append("local/global position or heading is not flight-valid")
        if not finite(
            self.position.x,
            self.position.y,
            self.position.z,
            self.position.vx,
            self.position.vy,
            self.position.vz,
            self.position.heading,
        ):
            reasons.append("position, velocity, or heading contains non-finite data")
        if self.battery is not None:
            if not self.battery.connected:
                reasons.append("optional BatteryStatus reports disconnected")
            if self.battery.warning != BatteryStatus.BATTERY_WARNING_NONE:
                reasons.append(f"battery warning={self.battery.warning}")
            if self.battery.faults != 0:
                reasons.append(f"battery faults={self.battery.faults}")
        if not self.endpoints_ready():
            reasons.append(
                "DDS endpoint mismatch "
                f"offboard={self.offboard_pub.get_subscription_count()} "
                f"setpoint={self.setpoint_pub.get_subscription_count()} "
                f"command={self.command_pub.get_subscription_count()}"
            )
        return reasons

    def capture_route(self):
        self.start = (
            float(self.position.x),
            float(self.position.y),
            float(self.position.z),
            float(self.position.heading),
        )
        self.takeoff, self.goal = route_from_heading(
            *self.start,
            self.args.takeoff_height,
            self.args.forward_distance,
        )
        self.target = self.start[:3]
        self.log_event(
            "ROUTE",
            f"start={self.start} takeoff={self.takeoff} goal={self.goal}",
        )

    def publish_control(self):
        if self.land_mode_confirmed or self.target is None:
            return
        now_ns = time.monotonic_ns()
        gap_ms = math.nan
        if self.previous_publish_ns is not None:
            gap_ms = (now_ns - self.previous_publish_ns) / 1_000_000.0
            self.publish_gaps_ms.append(gap_ms)
            if gap_ms > 250.0:
                self.abort(f"local heartbeat gap {gap_ms:.3f} ms exceeded 250 ms")
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
        setpoint.position = [self.target[0], self.target[1], self.target[2]]
        setpoint.velocity = [math.nan, math.nan, math.nan]
        setpoint.acceleration = [math.nan, math.nan, math.nan]
        setpoint.jerk = [math.nan, math.nan, math.nan]
        setpoint.yaw = self.start[3]
        setpoint.yawspeed = math.nan

        self.offboard_pub.publish(mode)
        self.setpoint_pub.publish(setpoint)
        self.publish_count += 1
        position = self.position
        self.heartbeats.writerow(
            [
                self.publish_count,
                now_ns,
                f"{(now_ns - self.started_ns) / 1_000_000.0:.3f}",
                "" if math.isnan(gap_ms) else f"{gap_ms:.3f}",
                self.state,
                self.offboard_pub.get_subscription_count(),
                self.setpoint_pub.get_subscription_count(),
                self.command_pub.get_subscription_count(),
                "" if self.status is None else self.status.arming_state,
                "" if self.status is None else self.status.nav_state,
                "" if self.status is None else int(self.status.failsafe),
                "" if position is None else f"{position.x:.4f}",
                "" if position is None else f"{position.y:.4f}",
                "" if position is None else f"{position.z:.4f}",
                "" if position is None else f"{position.vx:.4f}",
                "" if position is None else f"{position.vy:.4f}",
                "" if position is None else f"{position.vz:.4f}",
            ]
        )

    def reached(self, target, horizontal_tolerance, vertical_tolerance, velocity):
        horizontal_error = math.hypot(
            self.position.x - target[0], self.position.y - target[1]
        )
        vertical_error = abs(self.position.z - target[2])
        horizontal_speed = math.hypot(self.position.vx, self.position.vy)
        return (
            horizontal_error <= horizontal_tolerance
            and vertical_error <= vertical_tolerance
            and horizontal_speed <= velocity
            and abs(self.position.vz) <= velocity
        )

    def stable_for(self, condition, seconds):
        now = time.monotonic()
        if not condition:
            self.stable_since = None
            return False
        if self.stable_since is None:
            self.stable_since = now
        return now - self.stable_since >= seconds

    def abort(self, reason):
        if self.abort_reason is not None:
            return
        self.abort_reason = reason
        self.log_event("ABORT", reason)
        if self.status is not None and self.status.arming_state == ARMED:
            self.transition("REQUEST_LAND_ABORT", reason)
            self.abort_land_deadline = time.monotonic() + 12.0
        else:
            self.result = 10
            self.transition("FAILED", reason)

    def safety_check(self):
        if self.state in ("PRECHECK", "COMPLETE", "FAILED"):
            return
        if self.age("status") > self.STATUS_STALE_ABORT_SECONDS:
            self.abort("VehicleStatus stale for more than 2 s")
            return
        if self.age("failsafe_flags") > 2.0:
            self.abort("FailsafeFlags stale for more than 2 s")
            return
        flags = self.failsafe_flags
        for name in (
            "angular_velocity_invalid",
            "attitude_invalid",
            "local_altitude_invalid",
            "local_position_invalid",
            "local_velocity_invalid",
            "global_position_invalid",
            "home_position_invalid",
            "manual_control_signal_lost",
            "gcs_connection_lost",
            "battery_low_remaining_time",
            "battery_unhealthy",
            "primary_geofence_breached",
            "local_position_accuracy_low",
            "fd_critical_failure",
            "fd_esc_arming_failure",
            "fd_imbalanced_prop",
            "fd_motor_failure",
        ):
            if getattr(flags, name):
                self.abort(f"failsafe flag {name}=true")
                return
        if flags.battery_warning != 0:
            self.abort(f"battery_warning={flags.battery_warning}")
            return
        offboard_required_states = (
            "REQUEST_ARM",
            "GROUND_ARMED_HOLD",
            "TAKEOFF",
            "HOLD_AFTER_TAKEOFF",
            "MOVE_FORWARD",
        )
        if self.state in offboard_required_states and flags.offboard_control_signal_lost:
            self.abort("PX4 reports Offboard control signal lost")
            return
        if self.status.failsafe:
            self.abort("PX4 failsafe became active")
            return
        if self.status.failure_detector_status != 0:
            self.abort(
                f"failure_detector_status={self.status.failure_detector_status}"
            )
            return
        if self.status.gcs_connection_lost:
            self.abort("PX4 reports GCS connection lost")
            return
        if self.age("position") > self.POSITION_STALE_ABORT_SECONDS:
            self.abort("VehicleLocalPosition stale for more than 2 s")
            return
        if not (
            self.position.xy_valid
            and self.position.z_valid
            and self.position.v_xy_valid
            and self.position.v_z_valid
            and self.position.xy_global
            and self.position.z_global
            and self.position.heading_good_for_control
            and not self.position.dead_reckoning
        ):
            self.abort("position or heading validity was lost")
            return
        if self.land is not None and self.age("land") > 2.0:
            self.abort("optional VehicleLandDetected became stale")
            return
        if self.battery is not None and self.age("battery") > 2.0:
            self.abort("optional BatteryStatus became stale")
            return
        if not self.endpoints_ready():
            self.abort(
                "DDS endpoint mismatch during mission "
                f"offboard={self.offboard_pub.get_subscription_count()} "
                f"setpoint={self.setpoint_pub.get_subscription_count()} "
                f"command={self.command_pub.get_subscription_count()}"
            )
            return
        if self.battery is not None and (
            self.battery.warning >= BatteryStatus.BATTERY_WARNING_CRITICAL
            or self.battery.faults != 0
            or self.battery.is_powering_off
        ):
            self.abort(
                f"battery unsafe warning={self.battery.warning} "
                f"faults={self.battery.faults} powering_off={self.battery.is_powering_off}"
            )

    def tick_state(self):
        now = time.monotonic()
        elapsed = now - self.state_entered

        if self.state == "STREAM_PREROLL":
            if elapsed >= self.PREROLL_SECONDS:
                self.transition("REQUEST_OFFBOARD")

        elif self.state == "REQUEST_OFFBOARD":
            if self.status.nav_state == NAV_OFFBOARD:
                self.transition("REQUEST_ARM")
            else:
                self.begin_command(
                    CMD_SET_MODE,
                    (MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, PX4_CUSTOM_MAIN_MODE_OFFBOARD, 0, 0, 0, 0, 0),
                    5.0,
                )
                self.send_command_if_due()
                if now > self.command_deadline:
                    self.abort("Offboard request timeout")

        elif self.state == "REQUEST_ARM":
            if self.status.arming_state == ARMED and self.control.flag_armed:
                if self.args.mode == "ground-sequence":
                    self.transition("GROUND_ARMED_HOLD")
                else:
                    self.target = self.takeoff
                    self.transition("TAKEOFF")
            else:
                self.begin_command(CMD_ARM_DISARM, (1, 0, 0, 0, 0, 0, 0), 5.0)
                self.send_command_if_due()
                if now > self.command_deadline:
                    self.abort("normal Arm request timeout or rejection")

        elif self.state == "GROUND_ARMED_HOLD":
            if elapsed >= 3.0:
                self.transition("REQUEST_LAND")

        elif self.state == "TAKEOFF":
            if elapsed > 15.0:
                self.abort("takeoff timeout")
            elif self.stable_for(
                self.reached(self.takeoff, 0.20, 0.20, 0.20), 1.0
            ):
                self.transition("HOLD_AFTER_TAKEOFF")

        elif self.state == "HOLD_AFTER_TAKEOFF":
            if elapsed >= 2.0:
                if self.args.forward_distance > 0.0:
                    self.target = self.goal
                    self.transition("MOVE_FORWARD")
                else:
                    self.transition("REQUEST_LAND")

        elif self.state == "MOVE_FORWARD":
            if elapsed > 30.0:
                self.abort("forward waypoint timeout")
            elif self.stable_for(
                self.reached(self.goal, 0.30, 0.30, 0.30), 2.0
            ):
                self.transition("REQUEST_LAND")

        elif self.state in ("REQUEST_LAND", "REQUEST_LAND_ABORT"):
            if self.status.nav_state == NAV_LAND or self.last_ack.get(CMD_LAND) in (
                ACK_ACCEPTED,
                ACK_IN_PROGRESS,
            ):
                self.land_mode_confirmed = True
                if self.land is None:
                    self.log_event(
                        "LAND_FEEDBACK_FALLBACK",
                        "VehicleLandDetected is not bridged; require AUTO_DISARM_LAND reason",
                    )
                    self.transition("WAIT_AUTO_DISARM_FALLBACK")
                else:
                    self.transition("WAIT_LANDED")
            else:
                self.begin_command(CMD_LAND, (0, 0, 0, math.nan, math.nan, math.nan, math.nan), 8.0)
                self.send_command_if_due()
                deadline = (
                    self.abort_land_deadline
                    if self.state == "REQUEST_LAND_ABORT"
                    else self.command_deadline
                )
                if now > deadline:
                    self.log_event(
                        "LAND_NOT_CONFIRMED",
                        "operator must take over with RC mode switch or Kill",
                    )
                    self.result = 11
                    self.transition("FAILED", "Land command not confirmed")

        elif self.state == "WAIT_LANDED":
            if self.land.landed:
                self.transition("WAIT_AUTO_DISARM")
            elif elapsed > 30.0:
                reason = "PX4 Land did not report landed within 30 s"
                if self.abort_reason is None:
                    self.abort(reason)
                else:
                    self.log_event(
                        "LAND_TIMEOUT",
                        f"{reason}; operator must use RC mode switch or Kill",
                    )
                    self.result = 15
                    self.transition("FAILED", reason)

        elif self.state in ("WAIT_AUTO_DISARM", "WAIT_AUTO_DISARM_FALLBACK"):
            timeout = 45.0 if self.state == "WAIT_AUTO_DISARM_FALLBACK" else 15.0
            if self.status.arming_state == DISARMED and not self.control.flag_armed:
                if self.status.latest_disarming_reason != AUTO_DISARM_LAND_REASON:
                    self.log_event(
                        "UNEXPECTED_DISARM_REASON",
                        f"reason={self.status.latest_disarming_reason} expected={AUTO_DISARM_LAND_REASON}",
                    )
                    self.result = 16
                    self.transition("FAILED", "disarm was not PX4 auto-disarm-land")
                else:
                    self.result = 0 if self.abort_reason is None else 12
                    self.transition(
                        "COMPLETE" if self.abort_reason is None else "FAILED",
                        "PX4 AUTO_DISARM_LAND confirmed",
                    )
            elif elapsed > timeout:
                self.log_event(
                    "AUTO_DISARM_TIMEOUT",
                    "do not send normal/force disarm; operator must use approved recovery",
                )
                self.result = 13
                self.transition("FAILED", "auto-disarm timeout")

    def run_preflight(self):
        deadline = time.monotonic() + 20.0
        while time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
            if self.data_ready() and self.endpoints_ready():
                break
        reasons = self.preflight_reasons()
        if reasons:
            for reason in reasons:
                self.log_event("PREFLIGHT_REFUSED", reason)
            return 2
        self.capture_route()
        self.log_event(
            "PREFLIGHT_PASS",
            f"offboard_subscriptions={self.offboard_pub.get_subscription_count()} "
            f"setpoint_subscriptions={self.setpoint_pub.get_subscription_count()} "
            f"command_subscriptions={self.command_pub.get_subscription_count()}",
        )
        return 0

    def run(self):
        result = self.run_preflight()
        if result != 0 or self.args.mode == "preflight-only":
            return result
        self.transition("STREAM_PREROLL")
        try:
            while self.state not in ("COMPLETE", "FAILED"):
                rclpy.spin_once(self, timeout_sec=0.005)
                now = time.monotonic()
                self.safety_check()
                if self.age("position") <= self.POSITION_STALE_FREEZE_SECONDS:
                    self.tick_state()
                if now >= self.next_publish and not self.land_mode_confirmed:
                    self.publish_control()
                    self.next_publish += self.HEARTBEAT_PERIOD
                    if self.next_publish < now - self.HEARTBEAT_PERIOD:
                        self.next_publish = now + self.HEARTBEAT_PERIOD
        except KeyboardInterrupt:
            self.abort("operator interrupted mission")
            recovery_end = time.monotonic() + 12.0
            while (
                self.state not in ("COMPLETE", "FAILED")
                and time.monotonic() < recovery_end
            ):
                rclpy.spin_once(self, timeout_sec=0.02)
                self.tick_state()
                if time.monotonic() >= self.next_publish and not self.land_mode_confirmed:
                    self.publish_control()
                    self.next_publish += self.HEARTBEAT_PERIOD
        return self.result if self.result is not None else 14

    def close(self):
        if self.publish_gaps_ms:
            self.log_event(
                "HEARTBEAT_SUMMARY",
                f"publishes={self.publish_count} max_gap_ms={max(self.publish_gaps_ms):.3f} "
                f"over_150ms={sum(gap > 150.0 for gap in self.publish_gaps_ms)} "
                f"over_250ms={sum(gap > 250.0 for gap in self.publish_gaps_ms)} "
                f"over_500ms={sum(gap > 500.0 for gap in self.publish_gaps_ms)}",
            )
        self.events_file.flush()
        self.events_file.close()
        self.heartbeat_file.flush()
        self.heartbeat_file.close()


def parse_args():
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--preflight-only", action="store_true")
    modes.add_argument("--ground-sequence", action="store_true")
    modes.add_argument("--flight", action="store_true")
    parser.add_argument("--test-id")
    parser.add_argument("--allow-armed", action="store_true")
    parser.add_argument("--operator-confirmation", default="")
    parser.add_argument("--takeoff-height", type=float, default=0.5)
    parser.add_argument("--forward-distance", type=float, default=0.0)
    parser.add_argument("--x0", type=float, default=0.0)
    parser.add_argument("--y0", type=float, default=0.0)
    parser.add_argument("--z0", type=float, default=0.0)
    parser.add_argument("--heading", type=float, default=0.0)
    parser.add_argument("--log-root", default=str(DEFAULT_LOG_ROOT))
    args = parser.parse_args()

    if args.preflight_only:
        args.mode = "preflight-only"
    elif args.ground_sequence:
        args.mode = "ground-sequence"
    elif args.flight:
        args.mode = "flight"
    else:
        args.mode = "dry-run"
    return args


def validate_args(args):
    if not finite(
        args.takeoff_height,
        args.forward_distance,
        args.x0,
        args.y0,
        args.z0,
        args.heading,
    ):
        return "all numeric arguments must be finite"
    if not 0.1 <= args.takeoff_height <= 1.0:
        return "takeoff height must be within 0.1..1.0 m"
    if not 0.0 <= args.forward_distance <= 5.0:
        return "forward distance must be within 0..5 m"
    if args.mode == "ground-sequence" and args.forward_distance != 0.0:
        return "ground sequence refuses a forward waypoint"
    if args.mode != "dry-run":
        if not args.test_id or not TEST_ID_RE.fullmatch(args.test_id):
            return "active/preflight modes require a safe --test-id"
        if not SD_MOUNT.is_mount():
            return f"SD data volume is not mounted at {SD_MOUNT}"
    if args.mode == "ground-sequence":
        if not args.allow_armed or args.operator_confirmation != GROUND_CONFIRMATION:
            return (
                "ground sequence requires --allow-armed and "
                f"--operator-confirmation {GROUND_CONFIRMATION}"
            )
    if args.mode == "flight":
        if not args.allow_armed or args.operator_confirmation != FLIGHT_CONFIRMATION:
            return (
                "flight requires --allow-armed and "
                f"--operator-confirmation {FLIGHT_CONFIRMATION}"
            )
    return None


def print_dry_run(args):
    takeoff, goal = route_from_heading(
        args.x0,
        args.y0,
        args.z0,
        args.heading,
        args.takeoff_height,
        args.forward_distance,
    )
    print("DRY_RUN_ONLY publishes=0 commands=0")
    print(
        f"NED_START x={args.x0:.3f} y={args.y0:.3f} z={args.z0:.3f} "
        f"heading_rad={args.heading:.6f}"
    )
    print(f"NED_TAKEOFF x={takeoff[0]:.3f} y={takeoff[1]:.3f} z={takeoff[2]:.3f}")
    print(f"NED_GOAL x={goal[0]:.3f} y={goal[1]:.3f} z={goal[2]:.3f}")
    print("SEQUENCE preroll -> Offboard -> Arm -> takeoff -> waypoint -> PX4 Land -> auto-disarm")
    return 0


def main():
    args = parse_args()
    error = validate_args(args)
    if error:
        print(f"REFUSED: {error}", flush=True)
        return 2
    if args.mode == "dry-run":
        return print_dry_run(args)

    log_dir = Path(args.log_root).expanduser().resolve() / args.test_id
    log_dir.mkdir(parents=True, exist_ok=False)
    print(f"MISSION_LOG_DIR={log_dir}", flush=True)
    rclpy.init()
    node = DeliveryMission(args, log_dir)
    try:
        return node.run()
    finally:
        node.close()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
