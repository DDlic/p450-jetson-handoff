#!/usr/bin/env python3
"""Integrated 1440p display for Gazebo, ROS 2 transport, and PX4 state.

The displayed frame and the recorded frame are identical.  Gazebo's fixed
route camera occupies the left side; live ROS 2 topic health, PX4 state, and
the V4 mission state machine occupy the right side.
"""

from __future__ import annotations

import argparse
import csv
import math
import signal
import subprocess
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
import rclpy
from gz.msgs10.image_pb2 import Image as GzImage
from gz.transport13 import Node as GzNode
from px4_msgs.msg import (
    FailsafeFlags,
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


WIDTH = 2560
HEIGHT = 1440
CAMERA_TOPIC = "/p450_visual_camera"
DEFAULT_LOG_ROOT = Path("/media/p450/P450_DATA/builds/NX-user-storage/rosbags")

BG = (22, 27, 34)
PANEL = (31, 38, 48)
PANEL_ALT = (37, 45, 56)
LINE = (63, 75, 89)
TEXT = (232, 237, 242)
MUTED = (150, 162, 176)
GREEN = (112, 211, 143)
BLUE = (235, 167, 72)
ORANGE = (72, 170, 242)
RED = (104, 105, 239)
YELLOW = (80, 214, 232)


def enum_names(cls, prefix):
    return {
        value: name.removeprefix(prefix)
        for name, value in vars(cls).items()
        if name.startswith(prefix) and isinstance(value, int)
    }


ARMING_NAMES = enum_names(VehicleStatus, "ARMING_STATE_")
NAV_NAMES = enum_names(VehicleStatus, "NAVIGATION_STATE_")


MISSION_STEPS = (
    "PRECHECK",
    "OFFBOARD",
    "ARM",
    "TAKEOFF",
    "MOVE 5 M",
    "LAND",
    "COMPLETE",
)


def mission_step_index(state):
    if state == "COMPLETE":
        return 6
    if state == "FAILED":
        return -1
    if state in {"REQUEST_LAND", "REQUEST_LAND_ABORT", "WAIT_LANDED",
                 "WAIT_AUTO_DISARM", "WAIT_AUTO_DISARM_FALLBACK"}:
        return 5
    if state == "MOVE_FORWARD":
        return 4
    if state in {"TAKEOFF", "HOLD_AFTER_TAKEOFF"}:
        return 3
    if state in {"REQUEST_ARM", "GROUND_ARMED_HOLD"}:
        return 2
    if state in {"STREAM_PREROLL", "REQUEST_OFFBOARD"}:
        return 1
    return 0


@dataclass
class TopicHealth:
    label: str
    received: deque = field(default_factory=lambda: deque(maxlen=240))
    message: object | None = None

    def update(self, message):
        now = time.monotonic()
        self.message = message
        self.received.append(now)

    def age(self, now=None):
        if not self.received:
            return math.inf
        if now is None:
            now = time.monotonic()
        return now - self.received[-1]

    def rate(self):
        if len(self.received) < 2:
            return 0.0
        elapsed = self.received[-1] - self.received[0]
        return 0.0 if elapsed <= 0 else (len(self.received) - 1) / elapsed

    def max_gap_ms(self):
        if len(self.received) < 2:
            return 0.0
        values = list(self.received)
        return max(b - a for a, b in zip(values, values[1:])) * 1000.0


class MissionFollower:
    def __init__(self, path):
        self.path = path
        self.state = "WAITING"
        self.event = "NO LOG YET"
        self.detail = ""
        self.rows = []
        self.last_poll = 0.0

    def poll(self):
        now = time.monotonic()
        if now - self.last_poll < 0.08:
            return
        self.last_poll = now
        try:
            with self.path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
        except (OSError, csv.Error):
            return
        if not rows:
            return
        self.rows = rows[-5:]
        last = rows[-1]
        self.state = last.get("state") or "UNKNOWN"
        self.event = last.get("event") or ""
        self.detail = last.get("detail") or ""


class DashboardNode(Node):
    def __init__(self):
        super().__init__("p450_live_screen")
        qos = QoSProfile(
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=20,
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            durability=QoSDurabilityPolicy.VOLATILE,
        )
        self.health = {
            "status": TopicHealth("vehicle_status"),
            "position": TopicHealth("local_position"),
            "control": TopicHealth("control_mode"),
            "failsafe": TopicHealth("failsafe_flags"),
        }
        self.create_subscription(
            VehicleStatus,
            "/fmu/out/vehicle_status",
            lambda msg: self.health["status"].update(msg),
            qos,
        )
        self.create_subscription(
            VehicleLocalPosition,
            "/fmu/out/vehicle_local_position",
            lambda msg: self.health["position"].update(msg),
            qos,
        )
        self.create_subscription(
            VehicleControlMode,
            "/fmu/out/vehicle_control_mode",
            lambda msg: self.health["control"].update(msg),
            qos,
        )
        self.create_subscription(
            FailsafeFlags,
            "/fmu/out/failsafe_flags",
            lambda msg: self.health["failsafe"].update(msg),
            qos,
        )


class CameraReceiver:
    def __init__(self, topic):
        self.lock = threading.Lock()
        self.frame = None
        self.received = deque(maxlen=240)
        self.pixel_format = None
        self.node = GzNode()
        if not self.node.subscribe(GzImage, topic, self._callback):
            raise RuntimeError(f"Unable to subscribe to Gazebo camera topic {topic}")

    def _callback(self, message):
        width = int(message.width)
        height = int(message.height)
        step = int(message.step)
        raw = np.frombuffer(message.data, dtype=np.uint8)
        try:
            if message.pixel_format_type in (3, 8):
                rows = raw.reshape(height, step)
                image = rows[:, : width * 3].reshape(height, width, 3)
                if message.pixel_format_type == 3:
                    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                else:
                    image = image.copy()
            elif message.pixel_format_type in (4, 9):
                rows = raw.reshape(height, step)
                image = rows[:, : width * 4].reshape(height, width, 4)
                code = cv2.COLOR_RGBA2BGR if message.pixel_format_type == 4 else cv2.COLOR_BGRA2BGR
                image = cv2.cvtColor(image, code)
            elif message.pixel_format_type == 1:
                rows = raw.reshape(height, step)
                image = cv2.cvtColor(rows[:, :width], cv2.COLOR_GRAY2BGR)
            else:
                return
        except (ValueError, cv2.error):
            return
        with self.lock:
            self.frame = image
            self.pixel_format = int(message.pixel_format_type)
            self.received.append(time.monotonic())

    def latest(self):
        with self.lock:
            return self.frame

    def age(self):
        with self.lock:
            return math.inf if not self.received else time.monotonic() - self.received[-1]

    def rate(self):
        with self.lock:
            if len(self.received) < 2:
                return 0.0
            elapsed = self.received[-1] - self.received[0]
            return 0.0 if elapsed <= 0 else (len(self.received) - 1) / elapsed


def rect(image, x, y, w, h, color=PANEL, border=LINE):
    cv2.rectangle(image, (x, y), (x + w, y + h), color, -1, cv2.LINE_AA)
    cv2.rectangle(image, (x, y), (x + w, y + h), border, 2, cv2.LINE_AA)


def text(image, value, x, y, scale=0.65, color=TEXT, thickness=1):
    cv2.putText(
        image,
        str(value),
        (int(x), int(y)),
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        color,
        thickness,
        cv2.LINE_AA,
    )


def clipped(value, length):
    value = " ".join(str(value).split())
    # OpenCV's built-in Hershey fonts are ASCII-only.  Keep truncation
    # markers readable in the recorded dashboard instead of rendering a
    # Unicode ellipsis as question marks.
    return value if len(value) <= length else value[: length - 3] + "..."


def pill(image, label, x, y, color, width=None):
    if width is None:
        width = max(128, 16 * len(label) + 28)
    cv2.rectangle(image, (x, y), (x + width, y + 42), color, -1, cv2.LINE_AA)
    text(image, label, x + 14, y + 29, 0.62, BG, 2)
    return width


def draw_header(canvas, fps, camera):
    cv2.rectangle(canvas, (0, 0), (WIDTH, 88), (15, 20, 26), -1)
    text(canvas, "P450 SITL  /  LIVE INTEGRATED FLIGHT VIEW", 30, 56, 1.02, TEXT, 2)
    cam_rate = camera.rate()
    cam_age = camera.age() * 1000.0
    right = f"2560x1440  |  RECORD {fps:.0f} FPS  |  CAMERA {cam_rate:4.1f} Hz  {cam_age:4.0f} ms"
    (tw, _), _ = cv2.getTextSize(right, cv2.FONT_HERSHEY_SIMPLEX, 0.58, 1)
    text(canvas, right, WIDTH - tw - 28, 54, 0.58, MUTED, 1)


def draw_camera(canvas, camera):
    x, y, w, h = 28, 112, 1760, 990
    rect(canvas, x, y, w, h, (11, 15, 20))
    frame = camera.latest()
    if frame is None:
        text(canvas, "WAITING FOR /p450_visual_camera", x + 430, y + 500, 1.0, YELLOW, 2)
    else:
        shown = cv2.resize(frame, (w - 4, h - 4), interpolation=cv2.INTER_LINEAR)
        canvas[y + 2 : y + h - 2, x + 2 : x + w - 2] = shown
    cv2.rectangle(canvas, (x, y + h - 64), (x + w, y + h), (17, 22, 29), -1)
    text(canvas, "GAZEBO  /  ROUTE-WIDE  /  1 M TAKEOFF + 5 M FORWARD + LAND", x + 22, y + h - 23, 0.68, TEXT, 2)
    return x, y, w, h


def draw_event_stream(canvas, mission):
    x, y, w, h = 28, 1124, 1760, 278
    rect(canvas, x, y, w, h)
    text(canvas, "LIVE MISSION EVENT STREAM", x + 22, y + 38, 0.68, TEXT, 2)
    text(canvas, "ELAPSED", x + 24, y + 72, 0.46, MUTED, 1)
    text(canvas, "STATE", x + 170, y + 72, 0.46, MUTED, 1)
    text(canvas, "EVENT / DETAIL", x + 470, y + 72, 0.46, MUTED, 1)
    rows = mission.rows[-4:]
    if not rows:
        text(canvas, "Waiting for mission log...", x + 24, y + 122, 0.58, YELLOW, 1)
        return
    for index, row in enumerate(rows):
        row_y = y + 111 + index * 39
        try:
            elapsed = float(row.get("elapsed_ms") or 0.0) / 1000.0
            elapsed_label = f"{elapsed:7.2f} s"
        except ValueError:
            elapsed_label = "--"
        state = clipped(row.get("state") or "", 25)
        event = row.get("event") or ""
        detail = row.get("detail") or ""
        text(canvas, elapsed_label, x + 24, row_y, 0.50, MUTED, 1)
        text(canvas, state, x + 170, row_y, 0.50, ORANGE if index == len(rows) - 1 else TEXT, 1)
        text(canvas, clipped(f"{event}  {detail}", 98), x + 470, row_y, 0.48, TEXT, 1)


def draw_ros_panel(canvas, node):
    x, y, w, h = 1818, 112, 714, 438
    rect(canvas, x, y, w, h)
    text(canvas, "ROS 2 COMMUNICATION", x + 24, y + 42, 0.78, TEXT, 2)
    now = time.monotonic()
    live = all(item.age(now) < 1.0 for item in node.health.values())
    pill(canvas, "XRCE / DDS LIVE" if live else "WAITING FOR TOPICS", x + 24, y + 62, GREEN if live else YELLOW, 230)
    text(canvas, "TOPIC", x + 24, y + 132, 0.50, MUTED, 1)
    text(canvas, "RATE", x + 390, y + 132, 0.50, MUTED, 1)
    text(canvas, "AGE", x + 505, y + 132, 0.50, MUTED, 1)
    text(canvas, "MAX GAP", x + 594, y + 132, 0.50, MUTED, 1)
    for index, item in enumerate(node.health.values()):
        row_y = y + 172 + index * 59
        age = item.age(now)
        color = GREEN if age < 0.5 else YELLOW if age < 1.0 else RED
        cv2.circle(canvas, (x + 31, row_y - 6), 7, color, -1, cv2.LINE_AA)
        text(canvas, item.label, x + 50, row_y, 0.58, TEXT, 1)
        text(canvas, f"{item.rate():5.1f} Hz", x + 380, row_y, 0.55, TEXT, 1)
        age_label = "--" if not math.isfinite(age) else f"{age * 1000:4.0f} ms"
        text(canvas, age_label, x + 497, row_y, 0.55, color, 1)
        text(canvas, f"{item.max_gap_ms():4.0f} ms", x + 594, row_y, 0.52, MUTED, 1)


def draw_px4_panel(canvas, node):
    x, y, w, h = 1818, 574, 714, 402
    rect(canvas, x, y, w, h)
    text(canvas, "PX4 STATE MACHINE", x + 24, y + 42, 0.78, TEXT, 2)
    status = node.health["status"].message
    control = node.health["control"].message
    position = node.health["position"].message
    if status is None:
        text(canvas, "WAITING FOR vehicle_status", x + 24, y + 96, 0.70, YELLOW, 2)
        return
    armed = status.arming_state == VehicleStatus.ARMING_STATE_ARMED
    arm_name = ARMING_NAMES.get(status.arming_state, str(status.arming_state))
    nav_name = NAV_NAMES.get(status.nav_state, str(status.nav_state))
    failsafe = bool(status.failsafe)
    offboard = bool(control and control.flag_control_offboard_enabled)
    pill(canvas, arm_name, x + 24, y + 62, ORANGE if armed else BLUE, 196)
    pill(canvas, nav_name, x + 234, y + 62, GREEN if nav_name == "OFFBOARD" else BLUE, 218)
    pill(canvas, "FAILSAFE" if failsafe else "NO FAILSAFE", x + 466, y + 62, RED if failsafe else GREEN, 218)
    text(canvas, "OFFBOARD CONTROL", x + 24, y + 148, 0.56, MUTED, 1)
    text(canvas, "ENABLED" if offboard else "DISABLED", x + 286, y + 148, 0.66, GREEN if offboard else MUTED, 2)
    text(canvas, "GCS LINK", x + 24, y + 193, 0.56, MUTED, 1)
    gcs_ok = not bool(status.gcs_connection_lost)
    text(canvas, "CONNECTED" if gcs_ok else "LOST", x + 286, y + 193, 0.66, GREEN if gcs_ok else RED, 2)
    if position is not None:
        text(canvas, "LOCAL NED POSITION", x + 24, y + 250, 0.54, MUTED, 1)
        text(canvas, f"X {position.x:+7.2f} m", x + 24, y + 292, 0.66, TEXT, 1)
        text(canvas, f"Y {position.y:+7.2f} m", x + 235, y + 292, 0.66, TEXT, 1)
        text(canvas, f"Z {position.z:+7.2f} m", x + 446, y + 292, 0.66, TEXT, 1)
        speed = math.hypot(position.vx, position.vy)
        heading = math.degrees(position.heading)
        text(canvas, f"VXY {speed:5.2f} m/s", x + 24, y + 342, 0.62, TEXT, 1)
        text(canvas, f"VZ {position.vz:+5.2f} m/s", x + 250, y + 342, 0.62, TEXT, 1)
        text(canvas, f"HDG {heading:6.1f} deg", x + 458, y + 342, 0.62, TEXT, 1)


def draw_mission_panel(canvas, mission):
    x, y, w, h = 1818, 1000, 714, 402
    rect(canvas, x, y, w, h)
    text(canvas, "V4 MISSION STATE", x + 24, y + 42, 0.78, TEXT, 2)
    current = mission_step_index(mission.state)
    if mission.state == "FAILED":
        pill(canvas, "FAILED", x + 514, y + 18, RED, 174)
    elif mission.state == "COMPLETE":
        pill(canvas, "COMPLETE", x + 514, y + 18, GREEN, 174)
    base_y = y + 92
    for index, label in enumerate(MISSION_STEPS):
        cy = base_y + index * 39
        if index < current:
            color = GREEN
        elif index == current:
            color = ORANGE if mission.state != "FAILED" else RED
        else:
            color = LINE
        cv2.circle(canvas, (x + 44, cy), 10, color, -1, cv2.LINE_AA)
        if index < len(MISSION_STEPS) - 1:
            cv2.line(canvas, (x + 44, cy + 10), (x + 44, cy + 29), LINE, 3, cv2.LINE_AA)
        text(canvas, label, x + 72, cy + 7, 0.57, TEXT if index <= current else MUTED, 2 if index == current else 1)
    text(canvas, "RAW STATE", x + 286, y + 104, 0.50, MUTED, 1)
    text(canvas, clipped(mission.state, 25), x + 286, y + 138, 0.68, ORANGE, 2)
    text(canvas, "LAST EVENT", x + 286, y + 184, 0.50, MUTED, 1)
    text(canvas, clipped(mission.event, 31), x + 286, y + 218, 0.60, TEXT, 1)
    text(canvas, "DETAIL", x + 286, y + 264, 0.50, MUTED, 1)
    detail = clipped(mission.detail, 43)
    text(canvas, detail[:28], x + 286, y + 298, 0.50, MUTED, 1)
    text(canvas, detail[28:], x + 286, y + 328, 0.50, MUTED, 1)
    wall = time.strftime("%Y-%m-%d  %H:%M:%S")
    text(canvas, wall, x + 286, y + 374, 0.55, MUTED, 1)


class Recorder:
    def __init__(self, path, fps):
        self.path = path
        self.fps = fps
        self.process = None

    def start(self):
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        command = [
            "ffmpeg", "-y", "-v", "error",
            "-f", "rawvideo", "-pixel_format", "bgr24",
            "-video_size", f"{WIDTH}x{HEIGHT}", "-framerate", str(self.fps),
            "-i", "pipe:0", "-an", "-c:v", "libx264",
            "-preset", "ultrafast", "-tune", "zerolatency", "-crf", "18",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(self.path),
        ]
        # Keep terminal Ctrl-C on the dashboard process from aborting ffmpeg
        # before stdin is closed and the MP4 index is finalized.
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            start_new_session=True,
        )

    def write(self, frame):
        if self.process is None or self.process.stdin is None:
            return
        self.process.stdin.write(frame.tobytes())

    def stop(self):
        if self.process is None:
            return
        if self.process.stdin is not None:
            self.process.stdin.close()
        self.process.wait(timeout=30)
        if self.process.returncode:
            raise RuntimeError(f"ffmpeg recorder exited with {self.process.returncode}")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fps", type=int, choices=(60, 120), default=60)
    parser.add_argument("--record", type=Path)
    parser.add_argument("--test-id", required=True)
    parser.add_argument("--camera-topic", default=CAMERA_TOPIC)
    parser.add_argument("--windowed", action="store_true")
    parser.add_argument("--no-display", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    log_path = DEFAULT_LOG_ROOT / args.test_id / "MISSION_EVENTS.csv"
    mission = MissionFollower(log_path)
    camera = CameraReceiver(args.camera_topic)
    rclpy.init()
    node = DashboardNode()
    recorder = Recorder(args.record, args.fps)
    running = True

    def stop(_signum, _frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    if not args.no_display:
        cv2.namedWindow("P450 Integrated Flight View", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("P450 Integrated Flight View", WIDTH, HEIGHT)
        cv2.moveWindow("P450 Integrated Flight View", 0, 0)
        if not args.windowed:
            cv2.setWindowProperty(
                "P450 Integrated Flight View", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN
            )
    recorder.start()
    frame_count = 0
    late_frames = 0
    started = time.monotonic()
    next_frame = started
    try:
        while running:
            rclpy.spin_once(node, timeout_sec=0.0)
            mission.poll()
            canvas = np.full((HEIGHT, WIDTH, 3), BG, dtype=np.uint8)
            draw_header(canvas, args.fps, camera)
            draw_camera(canvas, camera)
            draw_event_stream(canvas, mission)
            draw_ros_panel(canvas, node)
            draw_px4_panel(canvas, node)
            draw_mission_panel(canvas, mission)
            recorder.write(canvas)
            if not args.no_display:
                cv2.imshow("P450 Integrated Flight View", canvas)
                if cv2.waitKey(1) & 0xFF in (27, ord("q")):
                    break
            frame_count += 1
            next_frame += 1.0 / args.fps
            delay = next_frame - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            else:
                late_frames += 1
                if delay < -0.5:
                    next_frame = time.monotonic()
    finally:
        elapsed = time.monotonic() - started
        recorder.stop()
        node.destroy_node()
        rclpy.shutdown()
        if not args.no_display:
            cv2.destroyAllWindows()
        print(
            f"P450_LIVE_SCREEN_STOP frames={frame_count} elapsed_s={elapsed:.3f} "
            f"effective_fps={frame_count / elapsed if elapsed else 0:.3f} "
            f"late_frames={late_frames} camera_hz={camera.rate():.3f} "
            f"mission_state={mission.state}",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
