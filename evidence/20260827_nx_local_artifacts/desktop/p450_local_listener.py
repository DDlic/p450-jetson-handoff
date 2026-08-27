#!/usr/bin/env python3
"""Read-only local ROS 2 listener for PX4 uXRCE-DDS gap isolation tests."""

import argparse
import csv
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from statistics import median

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
from px4_msgs.msg import SensorCombined, VehicleStatus, FailsafeFlags


SERVICE = "p450-micro-xrce-agent.service"
WLAN = "/sys/class/net/wlan1/statistics/"


def read_int(path):
    try:
        with open(path, "r", encoding="ascii") as stream:
            return int(stream.read().strip())
    except (OSError, ValueError):
        return ""


def softnet_drops():
    total = 0
    try:
        with open("/proc/net/softnet_stat", "r", encoding="ascii") as stream:
            for line in stream:
                fields = line.split()
                if len(fields) > 2:
                    total += int(fields[1], 16)
    except (OSError, ValueError):
        return ""
    return total


def system_state():
    state = {"agent_pid": "", "agent_restarts": "", "agent_active": ""}
    try:
        result = subprocess.run(
            ["systemctl", "show", SERVICE, "-p", "MainPID", "-p", "NRestarts", "-p", "ActiveState"],
            text=True, capture_output=True, timeout=1, check=False,
        )
        for line in result.stdout.splitlines():
            key, _, value = line.partition("=")
            if key == "MainPID":
                state["agent_pid"] = value
            elif key == "NRestarts":
                state["agent_restarts"] = value
            elif key == "ActiveState":
                state["agent_active"] = value
    except (OSError, subprocess.SubprocessError):
        pass
    return state


class LocalListener(Node):
    def __init__(self, writer, started):
        super().__init__("p450_local_listener")
        self.writer = writer
        self.started = started
        self.last_arrival = None
        self.last_source = None
        self.arrival_gaps = []
        self.source_gaps = []
        self.count = 0
        self.last_status = {}
        # Query systemd once before measurement. Calling systemctl from every
        # callback can block the single-threaded ROS executor and create false
        # queue drops that look like PX4 timestamp gaps.
        self.agent_state = system_state()
        qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
        )
        self.create_subscription(SensorCombined, "/fmu/out/sensor_combined", self.sensor_cb, qos)
        self.create_subscription(VehicleStatus, "/fmu/out/vehicle_status", self.status_cb, qos)
        self.create_subscription(FailsafeFlags, "/fmu/out/failsafe_flags", self.failsafe_cb, qos)
        self.last_report = time.monotonic()
        self.get_logger().info("LISTENING: local-only, read-only, low-overhead; no /fmu/in topics are published")

    def common(self, kind, arrival_gap="", source_gap="", timestamp_us="", extra=None):
        now = time.monotonic()
        row = {
            "kind": kind,
            "wall_time": datetime.now().astimezone().isoformat(timespec="milliseconds"),
            "elapsed_s": f"{now - self.started:.3f}",
            "arrival_gap_ms": arrival_gap,
            "source_gap_ms": source_gap,
            "px4_timestamp_us": timestamp_us,
            "agent_pid": self.agent_state["agent_pid"],
            "agent_restarts": self.agent_state["agent_restarts"],
            "agent_active": self.agent_state["agent_active"],
            "load1": "",
            "wlan_rx_packets": "",
            "wlan_rx_dropped": "",
            "wlan_tx_packets": "",
            "wlan_tx_dropped": "",
            "softnet_dropped_total": "",
            "status": "",
            "failsafe": "",
        }
        if extra:
            row.update(extra)
        self.writer.writerow(row)
        return now

    def sensor_cb(self, msg):
        arrival = time.monotonic()
        arrival_gap = "" if self.last_arrival is None else (arrival - self.last_arrival) * 1000.0
        source = int(getattr(msg, "timestamp", 0))
        source_gap = "" if self.last_source is None else (source - self.last_source) / 1000.0
        self.last_arrival = arrival
        self.last_source = source
        if arrival_gap != "":
            self.arrival_gaps.append(arrival_gap)
        if source_gap != "":
            self.source_gaps.append(source_gap)
        self.count += 1
        self.common("sensor_combined", arrival_gap, source_gap, source)

    def status_cb(self, msg):
        self.last_status = {
            "arming_state": getattr(msg, "arming_state", ""),
            "nav_state": getattr(msg, "nav_state", ""),
            "failsafe": getattr(msg, "failsafe", ""),
        }
        self.common("vehicle_status", timestamp_us=getattr(msg, "timestamp", 0), extra={"status": str(self.last_status)})

    def failsafe_cb(self, msg):
        fields = [
            name for name in dir(msg)
            if not name.startswith("_") and name.endswith("lost") and isinstance(getattr(msg, name), bool)
        ]
        values = {name: getattr(msg, name) for name in fields}
        self.common("failsafe_flags", timestamp_us=getattr(msg, "timestamp", 0), extra={"failsafe": str(values)})

def main():
    parser = argparse.ArgumentParser(description="Local read-only PX4 ROS 2 gap listener")
    parser.add_argument("--duration", type=float, default=300.0, help="test duration in seconds (default: 300)")
    parser.add_argument("--output", default="", help="CSV output path")
    args = parser.parse_args()
    if os.environ.get("ROS_LOCALHOST_ONLY") != "1":
        print("ERROR: ROS_LOCALHOST_ONLY must be 1; refusing non-local test", file=sys.stderr)
        return 2

    output = args.output or f"/home/p450/Desktop/p450_local_listener_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    fields = [
        "kind", "wall_time", "elapsed_s", "arrival_gap_ms", "source_gap_ms", "px4_timestamp_us",
        "agent_pid", "agent_restarts", "agent_active", "load1", "wlan_rx_packets", "wlan_rx_dropped",
        "wlan_tx_packets", "wlan_tx_dropped", "softnet_dropped_total", "status", "failsafe",
    ]
    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
    with open(output, "w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        started = time.monotonic()
        rclpy.init()
        node = LocalListener(writer, started)
        end = started + max(1.0, args.duration)
        try:
            while rclpy.ok() and time.monotonic() < end:
                rclpy.spin_once(node, timeout_sec=0.25)
        except KeyboardInterrupt:
            print("\nStopped by user")
        finally:
            node.destroy_node()
            rclpy.shutdown()
        gaps = node.arrival_gaps
        source_gaps = node.source_gaps
        max_gap = max(gaps) if gaps else 0.0
        max_source = max(source_gaps) if source_gaps else 0.0
        print(f"CSV: {output}")
        print(f"SensorCombined: {node.count} messages; max arrival gap {max_gap:.1f} ms; max PX4 source gap {max_source:.1f} ms")
        print(f"Gaps >100/500/1000 ms: {sum(x > 100 for x in gaps)}/{sum(x > 500 for x in gaps)}/{sum(x > 1000 for x in gaps)}")
    return 0


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    sys.exit(main())
