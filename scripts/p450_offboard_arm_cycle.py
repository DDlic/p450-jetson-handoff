#!/usr/bin/env python3
"""One normal arm/hold/disarm cycle for a confirmed propeller-free vehicle."""

import os
import time

import rclpy
from px4_msgs.msg import VehicleCommand, VehicleControlMode, VehicleStatus
from rclpy.node import Node
from rclpy.qos import QoSDurabilityPolicy, QoSHistoryPolicy, QoSProfile, QoSReliabilityPolicy


DISARMED = 1
ARMED = 2
NAV_OFFBOARD = 14
ARM_DISARM_COMMAND = 400


class ArmCycle(Node):
    def __init__(self):
        super().__init__("p450_offboard_arm_cycle")
        qos = QoSProfile(
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            durability=QoSDurabilityPolicy.VOLATILE,
        )
        self.status = None
        self.control = None
        self.create_subscription(VehicleStatus, "/fmu/out/vehicle_status", self.status_cb, qos)
        self.create_subscription(VehicleControlMode, "/fmu/out/vehicle_control_mode", self.control_cb, qos)
        self.command_pub = self.create_publisher(VehicleCommand, "/fmu/in/vehicle_command", qos)

    def status_cb(self, message):
        self.status = message

    def control_cb(self, message):
        self.control = message

    def spin_until(self, predicate, timeout):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.05)
            if predicate():
                return True
        return False

    def send_arm_action(self, arm):
        message = VehicleCommand()
        message.timestamp = self.get_clock().now().nanoseconds // 1000
        message.param1 = 1.0 if arm else 0.0
        message.param2 = 0.0  # Never force arm/disarm.
        message.command = ARM_DISARM_COMMAND
        message.target_system = 1
        message.target_component = 1
        message.source_system = 1
        message.source_component = 1
        message.confirmation = 0
        message.from_external = True
        self.command_pub.publish(message)


def main():
    rclpy.init()
    node = ArmCycle()
    if not node.spin_until(lambda: node.status is not None and node.control is not None, 10.0):
        print("REFUSED: no fresh vehicle status", flush=True)
        os._exit(2)
    if not (
        node.status.arming_state == DISARMED
        and not node.control.flag_armed
        and node.status.nav_state == NAV_OFFBOARD
        and node.control.flag_control_offboard_enabled
        and not node.status.failsafe
        and node.status.pre_flight_checks_pass
    ):
        print(
            "REFUSED: prerequisites "
            f"arming={node.status.arming_state} nav={node.status.nav_state} "
            f"offboard={node.control.flag_control_offboard_enabled} "
            f"failsafe={node.status.failsafe} preflight={node.status.pre_flight_checks_pass}",
            flush=True,
        )
        os._exit(3)

    matched = node.spin_until(lambda: node.command_pub.get_subscription_count() > 0, 8.0)
    if not matched:
        print("REFUSED: vehicle_command DDS subscription not matched", flush=True)
        os._exit(6)
    print(
        f"COMMAND_ENDPOINT_MATCHED subscriptions={node.command_pub.get_subscription_count()}",
        flush=True,
    )
    print("ARM_COMMAND normal=true force=false", flush=True)
    arm_deadline = time.monotonic() + 8.0
    armed = False
    while time.monotonic() < arm_deadline:
        node.send_arm_action(True)
        wait_end = time.monotonic() + 0.2
        while time.monotonic() < wait_end:
            rclpy.spin_once(node, timeout_sec=0.02)
            if node.status.arming_state == ARMED and node.control.flag_armed:
                armed = True
                break
        if armed:
            break
    if not armed:
        print(
            f"ARM_REJECTED_OR_TIMEOUT arming={node.status.arming_state} "
            f"failsafe={node.status.failsafe}",
            flush=True,
        )
        os._exit(4)

    print("ARM_CONFIRMED hold_seconds=3", flush=True)
    hold_end = time.monotonic() + 3.0
    while time.monotonic() < hold_end:
        rclpy.spin_once(node, timeout_sec=0.05)
        if node.status.failsafe:
            print("FAILSAFE_OBSERVED; DISARMING", flush=True)
            break

    print("DISARM_COMMAND normal=true force=false", flush=True)
    deadline = time.monotonic() + 8.0
    while time.monotonic() < deadline:
        node.send_arm_action(False)
        rclpy.spin_once(node, timeout_sec=0.1)
        if node.status.arming_state == DISARMED and not node.control.flag_armed:
            print(
                f"DISARM_CONFIRMED nav={node.status.nav_state} failsafe={node.status.failsafe}",
                flush=True,
            )
            os._exit(0)
    print(f"DISARM_NOT_CONFIRMED arming={node.status.arming_state}", flush=True)
    os._exit(5)


if __name__ == "__main__":
    main()
