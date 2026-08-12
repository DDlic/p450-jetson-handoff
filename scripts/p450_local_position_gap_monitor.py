#!/usr/bin/env python3
"""Read-only arrival/source gap monitor for PX4 vehicle_local_position."""

import argparse
import statistics
import time

import rclpy
from px4_msgs.msg import VehicleLocalPosition
from rclpy.node import Node
from rclpy.qos import QoSDurabilityPolicy, QoSHistoryPolicy, QoSProfile, QoSReliabilityPolicy


class Monitor(Node):
    def __init__(self):
        super().__init__("p450_local_position_gap_monitor")
        self.arrivals = []
        self.timestamps = []
        qos = QoSProfile(
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            durability=QoSDurabilityPolicy.VOLATILE,
        )
        self.create_subscription(
            VehicleLocalPosition,
            "/fmu/out/vehicle_local_position",
            self.callback,
            qos,
        )

    def callback(self, message):
        self.arrivals.append(time.monotonic())
        self.timestamps.append(int(message.timestamp))


def summarize(values_ms):
    if not values_ms:
        return "no_gaps"
    return (
        f"median_ms={statistics.median(values_ms):.3f} "
        f"max_ms={max(values_ms):.3f} "
        f"over_100ms={sum(value > 100 for value in values_ms)} "
        f"over_500ms={sum(value > 500 for value in values_ms)} "
        f"over_1s={sum(value > 1000 for value in values_ms)}"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=float, default=30.0)
    args = parser.parse_args()
    rclpy.init()
    node = Monitor()
    started = time.monotonic()
    try:
        while time.monotonic() - started < args.duration:
            rclpy.spin_once(node, timeout_sec=0.25)
    finally:
        elapsed = time.monotonic() - started
        node.destroy_node()
        rclpy.shutdown()

    arrival_gaps = [
        (current - previous) * 1000.0
        for previous, current in zip(node.arrivals, node.arrivals[1:])
    ]
    source_gaps = [
        (current - previous) / 1000.0
        for previous, current in zip(node.timestamps, node.timestamps[1:])
        if current >= previous
    ]
    print(f"elapsed_s={elapsed:.3f} messages={len(node.arrivals)} average_hz={len(node.arrivals) / elapsed:.3f}")
    print(f"arrival {summarize(arrival_gaps)}")
    print(f"source {summarize(source_gaps)}")
    return 0 if arrival_gaps and max(arrival_gaps) <= 100.0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
