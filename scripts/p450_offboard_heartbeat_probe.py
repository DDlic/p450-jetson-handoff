#!/usr/bin/env python3
"""Disarmed-only OffboardControlMode transport timing probe.

This node publishes only the PX4 ROS 2 Offboard proof-of-life message. It does
not publish a setpoint or VehicleCommand, and aborts if the vehicle arms or
enters/intends to enter Offboard mode.
"""

import argparse
import csv
import math
import os
import time
from pathlib import Path

import rclpy
from px4_msgs.msg import OffboardControlMode, VehicleControlMode, VehicleStatus
from rclpy.node import Node
from rclpy.qos import QoSDurabilityPolicy, QoSHistoryPolicy, QoSProfile, QoSReliabilityPolicy


DISARMED = 1
NAV_OFFBOARD = 14


class HeartbeatProbe(Node):
    def __init__(self, csv_path, reliability):
        super().__init__("p450_offboard_heartbeat_probe")
        subscription_qos = QoSProfile(
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            durability=QoSDurabilityPolicy.VOLATILE,
        )
        publisher_qos = QoSProfile(
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=(
                QoSReliabilityPolicy.RELIABLE
                if reliability == "reliable"
                else QoSReliabilityPolicy.BEST_EFFORT
            ),
            durability=QoSDurabilityPolicy.VOLATILE,
        )
        self.reliability = reliability
        self.status = None
        self.control = None
        self.started_ns = time.monotonic_ns()
        self.previous_publish_ns = None
        self.publish_count = 0
        self.gaps_ms = []
        self.create_subscription(
            VehicleStatus, "/fmu/out/vehicle_status", self._status, subscription_qos
        )
        self.create_subscription(
            VehicleControlMode,
            "/fmu/out/vehicle_control_mode",
            self._control,
            subscription_qos,
        )
        self.publisher = self.create_publisher(
            OffboardControlMode, "/fmu/in/offboard_control_mode", publisher_qos
        )

        path = Path(csv_path).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        self.csv_file = path.open("w", newline="", buffering=1)
        self.csv_writer = csv.writer(self.csv_file, lineterminator="\n")
        self.csv_writer.writerow(
            [
                "sequence",
                "monotonic_ns",
                "elapsed_ms",
                "publish_gap_ms",
                "ros_timestamp_us",
                "reliability",
                "subscription_count",
                "arming_state",
                "nav_state",
                "nav_state_user_intention",
                "failsafe",
            ]
        )
        print(f"HEARTBEAT_CSV={path}", flush=True)

    def _status(self, message):
        self.status = message

    def _control(self, message):
        self.control = message

    def safe(self):
        return (
            self.status is not None
            and self.control is not None
            and self.status.arming_state == DISARMED
            and not self.control.flag_armed
            and self.status.nav_state != NAV_OFFBOARD
            and self.status.nav_state_user_intention != NAV_OFFBOARD
        )

    def publish_heartbeat(self):
        if not self.safe():
            raise RuntimeError(
                "unsafe state: armed or Offboard selected; heartbeat probe stopped"
            )

        monotonic_ns = time.monotonic_ns()
        gap_ms = math.nan
        if self.previous_publish_ns is not None:
            gap_ms = (monotonic_ns - self.previous_publish_ns) / 1_000_000.0
            self.gaps_ms.append(gap_ms)
        self.previous_publish_ns = monotonic_ns

        timestamp_us = self.get_clock().now().nanoseconds // 1000
        message = OffboardControlMode()
        message.timestamp = timestamp_us
        message.position = True
        message.velocity = False
        message.acceleration = False
        message.attitude = False
        message.body_rate = False
        message.actuator = False
        self.publisher.publish(message)
        self.publish_count += 1
        self.csv_writer.writerow(
            [
                self.publish_count,
                monotonic_ns,
                f"{(monotonic_ns - self.started_ns) / 1_000_000.0:.3f}",
                "" if math.isnan(gap_ms) else f"{gap_ms:.3f}",
                timestamp_us,
                self.reliability,
                self.publisher.get_subscription_count(),
                self.status.arming_state,
                self.status.nav_state,
                self.status.nav_state_user_intention,
                int(self.status.failsafe),
            ]
        )

    def report(self):
        self.csv_file.flush()
        self.csv_file.close()
        if not self.gaps_ms:
            print(f"HEARTBEAT_TIMING publishes={self.publish_count} gaps=0", flush=True)
            return
        print(
            "HEARTBEAT_TIMING "
            f"publishes={self.publish_count} "
            f"max_gap_ms={max(self.gaps_ms):.3f} "
            f"over_150ms={sum(gap > 150.0 for gap in self.gaps_ms)} "
            f"over_250ms={sum(gap > 250.0 for gap in self.gaps_ms)} "
            f"over_500ms={sum(gap > 500.0 for gap in self.gaps_ms)}",
            flush=True,
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--rate", type=float, default=10.0)
    parser.add_argument(
        "--reliability",
        choices=("best_effort", "reliable"),
        default="best_effort",
    )
    parser.add_argument("--csv", required=True)
    args = parser.parse_args()
    if args.duration <= 0 or args.rate < 2.0 or args.rate > 20.0:
        print("REFUSED: duration must be positive and rate must be 2..20 Hz", flush=True)
        return 2

    rclpy.init()
    node = HeartbeatProbe(args.csv, args.reliability)
    ready_deadline = time.monotonic() + 15.0
    while time.monotonic() < ready_deadline and not node.safe():
        rclpy.spin_once(node, timeout_sec=0.1)
    if not node.safe():
        print("REFUSED: fresh disarmed non-Offboard status unavailable", flush=True)
        node.report()
        return 3

    match_deadline = time.monotonic() + 8.0
    while time.monotonic() < match_deadline and node.publisher.get_subscription_count() < 1:
        rclpy.spin_once(node, timeout_sec=0.1)
    if node.publisher.get_subscription_count() < 1:
        print("REFUSED: PX4 OffboardControlMode DDS subscription not matched", flush=True)
        node.report()
        return 4

    print(
        "HEARTBEAT_PROBE_READY disarmed=true offboard=false "
        f"subscriptions={node.publisher.get_subscription_count()} "
        f"rate_hz={args.rate:.3f} reliability={args.reliability}",
        flush=True,
    )
    period = 1.0 / args.rate
    next_send = time.monotonic()
    end = next_send + args.duration
    result = 0
    try:
        while time.monotonic() < end:
            rclpy.spin_once(node, timeout_sec=min(0.02, period / 4.0))
            now = time.monotonic()
            if now >= next_send:
                node.publish_heartbeat()
                next_send += period
    except (KeyboardInterrupt, RuntimeError) as error:
        print(f"HEARTBEAT_PROBE_STOP: {error}", flush=True)
        result = 5 if isinstance(error, RuntimeError) else 130
    finally:
        node.report()
        node.destroy_node()
        rclpy.shutdown()
    return result


if __name__ == "__main__":
    raise SystemExit(main())
