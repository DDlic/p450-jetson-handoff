#!/usr/bin/env python3
"""Read-only static IMU and attitude plausibility check for the P450."""

import argparse
import math
import statistics
import sys
import time

import rclpy
from px4_msgs.msg import SensorCombined, VehicleAttitude
from rclpy.node import Node
from rclpy.qos import (
    QoSDurabilityPolicy,
    QoSHistoryPolicy,
    QoSProfile,
    QoSReliabilityPolicy,
)


class StaticSensorCheck(Node):
    def __init__(self):
        super().__init__("p450_sensor_static_check")
        qos = QoSProfile(
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=5,
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            durability=QoSDurabilityPolicy.VOLATILE,
        )
        self.sensor_arrivals = []
        self.accel_norms = []
        self.gyro_norms = []
        self.accel_clipping_samples = 0
        self.attitude_arrivals = []
        self.quaternion_norms = []

        self.create_subscription(
            SensorCombined,
            "/fmu/out/sensor_combined",
            self._on_sensor,
            qos,
        )
        self.create_subscription(
            VehicleAttitude,
            "/fmu/out/vehicle_attitude",
            self._on_attitude,
            qos,
        )

    def _on_sensor(self, message):
        self.sensor_arrivals.append(time.monotonic())
        self.accel_norms.append(math.sqrt(sum(v * v for v in message.accelerometer_m_s2)))
        self.gyro_norms.append(math.sqrt(sum(v * v for v in message.gyro_rad)))
        if message.accelerometer_clipping != 0:
            self.accel_clipping_samples += 1

    def _on_attitude(self, message):
        self.attitude_arrivals.append(time.monotonic())
        self.quaternion_norms.append(math.sqrt(sum(v * v for v in message.q)))


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Subscribe to PX4 IMU and attitude data without publishing, then "
            "check static plausibility. Keep the vehicle stationary."
        )
    )
    parser.add_argument("--duration", type=float, default=60.0)
    return parser.parse_args()


def summarize(values):
    return {
        "mean": statistics.fmean(values),
        "std": statistics.pstdev(values),
        "min": min(values),
        "max": max(values),
    }


def main():
    args = parse_args()
    if args.duration <= 0:
        print("duration must be positive", file=sys.stderr)
        return 2

    rclpy.init()
    node = StaticSensorCheck()
    started = time.monotonic()
    try:
        while time.monotonic() - started < args.duration:
            rclpy.spin_once(node, timeout_sec=0.25)
    finally:
        elapsed = time.monotonic() - started
        node.destroy_node()
        rclpy.shutdown()

    if not node.accel_norms or not node.gyro_norms or not node.quaternion_norms:
        print("result=FAIL reason=missing_sensor_or_attitude_samples")
        return 2

    accel = summarize(node.accel_norms)
    gyro = summarize(node.gyro_norms)
    quaternion = summarize(node.quaternion_norms)
    quaternion_max_error = max(abs(value - 1.0) for value in node.quaternion_norms)

    print(f"elapsed_s={elapsed:.3f}")
    print(f"sensor_samples={len(node.sensor_arrivals)}")
    print(f"sensor_average_hz={len(node.sensor_arrivals) / elapsed:.3f}")
    print(f"attitude_samples={len(node.attitude_arrivals)}")
    print(f"attitude_average_hz={len(node.attitude_arrivals) / elapsed:.3f}")
    print(f"accel_norm_mean_m_s2={accel['mean']:.6f}")
    print(f"accel_norm_std_m_s2={accel['std']:.6f}")
    print(f"accel_norm_min_m_s2={accel['min']:.6f}")
    print(f"accel_norm_max_m_s2={accel['max']:.6f}")
    print(f"gyro_norm_mean_rad_s={gyro['mean']:.6f}")
    print(f"gyro_norm_std_rad_s={gyro['std']:.6f}")
    print(f"gyro_norm_max_rad_s={gyro['max']:.6f}")
    print(f"accelerometer_clipping_samples={node.accel_clipping_samples}")
    print(f"quaternion_norm_mean={quaternion['mean']:.9f}")
    print(f"quaternion_norm_max_error={quaternion_max_error:.9f}")
    print("gyro_clipping_field=IGNORED_known_px4_v1.14.3_uninitialized_field")

    failures = []
    if len(node.sensor_arrivals) / elapsed < 20.0:
        failures.append("sensor_rate_below_20hz")
    if not 7.5 <= accel["mean"] <= 12.0:
        failures.append("acceleration_magnitude_implausible")
    if gyro["mean"] >= 0.1:
        failures.append("vehicle_not_static_or_gyro_mean_high")
    if gyro["max"] >= 0.5:
        failures.append("vehicle_moved_or_gyro_peak_high")
    if node.accel_clipping_samples != 0:
        failures.append("accelerometer_clipping_detected")
    if quaternion_max_error >= 0.01:
        failures.append("attitude_quaternion_not_normalized")

    if failures:
        print(f"result=FAIL reasons={','.join(failures)}")
        return 2

    print("result=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
