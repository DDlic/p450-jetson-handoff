#!/usr/bin/env python3
"""Disarmed-only PX4 Offboard mode ground probe.

Publishes a position-mode heartbeat and a hold-current-position setpoint. It
never publishes VehicleCommand and exits immediately if the vehicle is armed.
"""

import argparse
import csv
import math
import os
import sys
import time
from pathlib import Path

import rclpy
from px4_msgs.msg import OffboardControlMode, TrajectorySetpoint, VehicleControlMode, VehicleLocalPosition, VehicleStatus
from rclpy.node import Node
from rclpy.qos import QoSDurabilityPolicy, QoSHistoryPolicy, QoSProfile, QoSReliabilityPolicy


DISARMED = 1
NAV_OFFBOARD = 14


class GroundProbe(Node):
    def __init__(self, allow_armed=False, csv_path=None):
        super().__init__("p450_offboard_ground_probe")
        self.allow_armed = allow_armed
        self.started_ns = time.monotonic_ns()
        self.previous_publish_ns = None
        self.publish_count = 0
        self.publish_gaps_ms = []
        self.csv_file = None
        self.csv_writer = None
        if csv_path:
            path = Path(csv_path).expanduser().resolve()
            path.parent.mkdir(parents=True, exist_ok=True)
            self.csv_file = path.open("w", newline="", buffering=1)
            self.csv_writer = csv.writer(self.csv_file)
            self.csv_writer.writerow(
                [
                    "sequence",
                    "monotonic_ns",
                    "elapsed_ms",
                    "publish_gap_ms",
                    "ros_timestamp_us",
                    "offboard_subscription_count",
                    "setpoint_subscription_count",
                    "arming_state",
                    "nav_state",
                    "failsafe",
                ]
            )
            print(f"HEARTBEAT_CSV={path}", flush=True)
        qos = QoSProfile(
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            durability=QoSDurabilityPolicy.VOLATILE,
        )
        self.status = None
        self.control = None
        self.position = None
        self.hold = None
        self.last_nav = None
        self.create_subscription(VehicleStatus, "/fmu/out/vehicle_status", self.status_cb, qos)
        self.create_subscription(VehicleControlMode, "/fmu/out/vehicle_control_mode", self.control_cb, qos)
        self.create_subscription(VehicleLocalPosition, "/fmu/out/vehicle_local_position", self.position_cb, qos)
        self.offboard_pub = self.create_publisher(OffboardControlMode, "/fmu/in/offboard_control_mode", qos)
        self.setpoint_pub = self.create_publisher(TrajectorySetpoint, "/fmu/in/trajectory_setpoint", qos)

    def status_cb(self, message):
        self.status = message
        if message.nav_state != self.last_nav:
            print(
                f"NAV_STATE={message.nav_state} OFFBOARD={message.nav_state == NAV_OFFBOARD} "
                f"ARMING_STATE={message.arming_state} FAILSAFE={message.failsafe}",
                flush=True,
            )
            self.last_nav = message.nav_state
        if message.arming_state != DISARMED:
            print(
                f"ARMED_OBSERVED arming_state={message.arming_state} "
                f"nav_state={message.nav_state} failsafe={message.failsafe}",
                flush=True,
            )

    def control_cb(self, message):
        self.control = message

    def position_cb(self, message):
        self.position = message

    def ready(self):
        return (
            self.status is not None
            and self.control is not None
            and self.position is not None
            and self.status.arming_state == DISARMED
            and not self.control.flag_armed
            and self.position.xy_valid
            and self.position.z_valid
            and self.position.v_xy_valid
            and self.position.v_z_valid
            and self.position.xy_global
            and self.position.z_global
            and not self.position.dead_reckoning
        )

    def capture_hold(self):
        self.hold = (self.position.x, self.position.y, self.position.z, self.position.heading)
        print(
            "GROUND_PROBE_READY disarmed=true "
            f"hold=({self.hold[0]:.3f},{self.hold[1]:.3f},{self.hold[2]:.3f}) "
            f"yaw={self.hold[3]:.3f}",
            flush=True,
        )

    def publish(self):
        if not self.allow_armed and (self.status.arming_state != DISARMED or self.control.flag_armed):
            raise RuntimeError("vehicle became armed; probe stopped")
        monotonic_ns = time.monotonic_ns()
        gap_ms = math.nan
        if self.previous_publish_ns is not None:
            gap_ms = (monotonic_ns - self.previous_publish_ns) / 1_000_000.0
            self.publish_gaps_ms.append(gap_ms)
        self.previous_publish_ns = monotonic_ns

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
        setpoint.position = [self.hold[0], self.hold[1], self.hold[2]]
        setpoint.velocity = [math.nan, math.nan, math.nan]
        setpoint.acceleration = [math.nan, math.nan, math.nan]
        setpoint.jerk = [math.nan, math.nan, math.nan]
        setpoint.yaw = self.hold[3]
        setpoint.yawspeed = math.nan
        self.offboard_pub.publish(mode)
        self.setpoint_pub.publish(setpoint)
        self.publish_count += 1
        if self.csv_writer is not None:
            self.csv_writer.writerow(
                [
                    self.publish_count,
                    monotonic_ns,
                    f"{(monotonic_ns - self.started_ns) / 1_000_000.0:.3f}",
                    "" if math.isnan(gap_ms) else f"{gap_ms:.3f}",
                    timestamp,
                    self.offboard_pub.get_subscription_count(),
                    self.setpoint_pub.get_subscription_count(),
                    self.status.arming_state,
                    self.status.nav_state,
                    int(self.status.failsafe),
                ]
            )

    def report_publish_timing(self):
        if self.csv_file is not None:
            self.csv_file.flush()
            self.csv_file.close()
        if not self.publish_gaps_ms:
            print(f"HEARTBEAT_TIMING publishes={self.publish_count} gaps=0", flush=True)
            return
        gaps = self.publish_gaps_ms
        print(
            "HEARTBEAT_TIMING "
            f"publishes={self.publish_count} "
            f"max_gap_ms={max(gaps):.3f} "
            f"over_150ms={sum(gap > 150.0 for gap in gaps)} "
            f"over_250ms={sum(gap > 250.0 for gap in gaps)} "
            f"over_500ms={sum(gap > 500.0 for gap in gaps)}",
            flush=True,
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=float, default=120.0)
    parser.add_argument(
        "--allow-armed",
        action="store_true",
        help="continue heartbeat while observing a manual no-prop arming test",
    )
    parser.add_argument(
        "--csv",
        help="write every heartbeat publish time and DDS match count to this CSV",
    )
    args = parser.parse_args()
    rclpy.init()
    node = GroundProbe(allow_armed=args.allow_armed, csv_path=args.csv)
    deadline = time.monotonic() + 15.0
    while time.monotonic() < deadline and not node.ready():
        rclpy.spin_once(node, timeout_sec=0.1)
    if not node.ready():
        print("REFUSED: disarmed/global-position prerequisites not satisfied", flush=True)
        node.report_publish_timing()
        os._exit(2)
    node.capture_hold()
    end = time.monotonic() + args.duration
    next_send = time.monotonic()
    try:
        while time.monotonic() < end:
            rclpy.spin_once(node, timeout_sec=0.02)
            if time.monotonic() >= next_send:
                node.publish()
                next_send += 0.1
    except (KeyboardInterrupt, RuntimeError) as error:
        print(f"GROUND_PROBE_STOP: {error}", flush=True)
        node.report_publish_timing()
        os._exit(3 if isinstance(error, RuntimeError) else 0)
    if node.status is not None and node.status.arming_state != DISARMED:
        print("REFUSED_TO_EXIT_WHILE_ARMED", flush=True)
        while node.status is not None and node.status.arming_state != DISARMED:
            rclpy.spin_once(node, timeout_sec=0.02)
            node.publish()
    print("GROUND_PROBE_COMPLETE", flush=True)
    node.report_publish_timing()
    os._exit(0)


if __name__ == "__main__":
    main()
