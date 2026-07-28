#!/usr/bin/env python3
"""Read-only PX4 ROS 2 link continuity monitor for the P450."""

import argparse
import statistics
import sys
import time

import rclpy
from px4_msgs.msg import SensorCombined
from rclpy.node import Node
from rclpy.qos import (
    QoSDurabilityPolicy,
    QoSHistoryPolicy,
    QoSProfile,
    QoSReliabilityPolicy,
)


class SensorGapMonitor(Node):
    def __init__(self):
        super().__init__("p450_sensor_gap_monitor")
        self.arrivals = []
        qos = QoSProfile(
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=5,
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            durability=QoSDurabilityPolicy.VOLATILE,
        )
        self.subscription = self.create_subscription(
            SensorCombined,
            "/fmu/out/sensor_combined",
            self._on_sensor,
            qos,
        )

    def _on_sensor(self, _message):
        self.arrivals.append(time.monotonic())


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Subscribe to /fmu/out/sensor_combined without publishing anything "
            "and report inter-message gaps."
        )
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=65.0,
        help="monitoring duration in seconds (default: 65)",
    )
    parser.add_argument(
        "--max-gap-ms",
        type=float,
        default=100.0,
        help="largest allowed inter-message gap for PASS (default: 100)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if args.duration <= 0 or args.max_gap_ms <= 0:
        print("duration and max-gap-ms must be positive", file=sys.stderr)
        return 2

    rclpy.init()
    node = SensorGapMonitor()
    started = time.monotonic()

    try:
        while time.monotonic() - started < args.duration:
            rclpy.spin_once(node, timeout_sec=0.25)
    finally:
        elapsed = time.monotonic() - started
        arrivals = node.arrivals
        node.destroy_node()
        rclpy.shutdown()

    gaps = [
        current - previous
        for previous, current in zip(arrivals, arrivals[1:])
    ]

    print(f"elapsed_s={elapsed:.3f}")
    print(f"messages={len(arrivals)}")
    print(f"average_hz={len(arrivals) / elapsed:.3f}")

    if not gaps:
        print("result=FAIL reason=no_continuous_sensor_data")
        return 2

    median_gap_ms = statistics.median(gaps) * 1000.0
    max_gap_ms = max(gaps) * 1000.0
    print(f"median_gap_ms={median_gap_ms:.3f}")
    print(f"max_gap_ms={max_gap_ms:.3f}")
    print(f"gaps_over_100ms={sum(gap > 0.1 for gap in gaps)}")
    print(f"gaps_over_500ms={sum(gap > 0.5 for gap in gaps)}")
    print(f"gaps_over_1s={sum(gap > 1.0 for gap in gaps)}")

    if max_gap_ms > args.max_gap_ms:
        print(
            "result=FAIL "
            f"reason=max_gap_exceeded threshold_ms={args.max_gap_ms:.3f}"
        )
        return 2

    print(f"result=PASS threshold_ms={args.max_gap_ms:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
