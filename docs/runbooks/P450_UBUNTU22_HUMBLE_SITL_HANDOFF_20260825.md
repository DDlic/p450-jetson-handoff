# P450 Ubuntu 22.04 / Humble / Gazebo SITL handoff

Date: 2026-08-25 (Asia/Taipei)
Test family: `P450_20260825_DESKTOP_HUMBLE_SITL_HANDOFF`
Scope: software-only PX4 x500 SITL; no Pixhawk, Jetson, P450, battery, or propellers.

This runbook reproduces the desktop result recorded in
[`evidence/20260825_desktop_humble_sitl`](../../evidence/20260825_desktop_humble_sitl/README.md).
It does not clear the NX UART freshness, repeated kernel panic, RC-loss, or physical-flight gates.

## Verified result

| Gate | Result | Key observation |
|---|---:|---|
| Unit tests | PASS | 28/28 |
| SIM-P | PASS | exit 0; preflight only; 0 publishes, 0 commands |
| SIM-G | PASS | exit 0; Offboard/Arm/Land ownership; PX4 auto-disarm-land |
| SIM-F1 | PASS | exit 0; 0.5 m vertical flight; max local heartbeat gap 104.840 ms |
| SIM-F2 | PASS | exit 0; 1 m climb and 5 m forward waypoint; max gap 105.141 ms |
| Heartbeat pause | PASS | 600 ms pause detected; abort Land; expected exit 12 |
| POSCTL takeover | PASS | no further mission control publication; expected exit 20; operator Land recovery |
| Agent pause | PASS | 3 s stall; PX4 exits Offboard first; expected exit 20; operator Land recovery |

SIM-F2 recorded 201 heartbeats, no active failsafe samples, no gap above 150 ms, and about
5.41 m maximum horizontal displacement from the first recorded setpoint sample. The baseline
Agent process recorded one session establishment and no reconnect or close before failure injection.

## Fixed versions

- Ubuntu 22.04 x86_64, native ROS 2 Humble.
- PX4 `v1.14.3`, commit `1dacb4cdef2d7145754fc788fa8dc482eed74b40`.
- `px4_msgs` `release/1.14`, commit `ffb6e80e1c17e5714395611a020c282a87af8fa4`.
- Micro XRCE-DDS Agent `v2.4.2`, commit `57d086216d01ec43121845d385894a25987f8a2c`.
- Fast DDS `v2.12.2`, commit `092848725b8425e4f05a8ccf7b3b8d513fabf733`.
- Gazebo Garden `gz-sim 7.9.0`, `gz-transport 12.2.2`.
- `ROS_DOMAIN_ID=0`, `ROS_LOCALHOST_ONLY=0`, Agent UDP4 port 8888.

Do not substitute PX4 main, `px4_msgs/main`, Gazebo Harmonic, or an unpinned Fast DDS branch.

## Compatibility findings

The original V4 artifact at `e6f783f7` is preserved by Git, but it cannot pass this pinned desktop
matrix unchanged:

1. `Path.is_mount()` does not recognize a same-filesystem bind mount. The mission now reads
   `/proc/self/mountinfo`, still fails closed when the target is absent, and has a regression test.
2. PX4 v1.14.3 Commander stores `events::arm_disarm_reason_t::auto_disarm_land=6` in
   `VehicleStatus`, while the generated release/1.14 message constant says 7 because that message
   still includes an unused safety-button entry. The mission accepts only the pinned firmware's
   exact value 6. The original behavior was observed as PX4 console `Disarmed by landing`, ROS
   reason 6, and mission exit 16.
3. Agent v2.4.2's superbuild references the deleted Fast DDS branch `2.12.x`. Apply
   [`micro-xrce-agent-v2.4.2-fastdds-v2.12.2.patch`](../../patches/micro-xrce-agent-v2.4.2-fastdds-v2.12.2.patch)
   to use the final 2.12 release tag.
4. A stock x500 SITL has no GCS/joystick source. Keep the mission's GCS/manual-control gates and
   run [`p450_sitl_operator_link.py`](../../scripts/p450_sitl_operator_link.py), which is restricted
   to localhost and sends only GCS heartbeat plus neutral joystick input.

## Host preparation

Install ROS 2 Humble from the official ROS repository, then install the build dependencies:

```bash
sudo apt update
sudo apt install -y \
  astyle bc build-essential cmake cppcheck file gdb git lcov libasio-dev \
  libeigen3-dev libfuse2 libopencv-dev libtinyxml2-dev libxml2-dev \
  libxml2-utils make ninja-build pkg-config protobuf-compiler \
  python3-dev python3-pip python3-setuptools python3-venv python3-wheel \
  rsync shellcheck unzip zip gz-garden
```

Use a dedicated work root and exact commits:

```bash
export P450_SITL_ROOT=/absolute/path/to/p450-sitl-work
export P450_REPO=/absolute/path/to/p450-jetson-handoff

git clone --branch v1.14.3 --recurse-submodules --shallow-submodules \
  https://github.com/PX4/PX4-Autopilot.git "$P450_SITL_ROOT/PX4-Autopilot"
git -C "$P450_SITL_ROOT/PX4-Autopilot" checkout 1dacb4cdef2d7145754fc788fa8dc482eed74b40
git -C "$P450_SITL_ROOT/PX4-Autopilot/platforms/nuttx/NuttX/nuttx" fetch --depth=1 \
  origin refs/tags/nuttx-11.0.0:refs/tags/nuttx-11.0.0

git clone --branch release/1.14 https://github.com/PX4/px4_msgs.git \
  "$P450_SITL_ROOT/px4_msgs"
git -C "$P450_SITL_ROOT/px4_msgs" checkout ffb6e80e1c17e5714395611a020c282a87af8fa4

git clone --branch v2.4.2 https://github.com/eProsima/Micro-XRCE-DDS-Agent.git \
  "$P450_SITL_ROOT/Micro-XRCE-DDS-Agent"
git -C "$P450_SITL_ROOT/Micro-XRCE-DDS-Agent" checkout 57d086216d01ec43121845d385894a25987f8a2c
git -C "$P450_SITL_ROOT/Micro-XRCE-DDS-Agent" apply \
  "$P450_REPO/patches/micro-xrce-agent-v2.4.2-fastdds-v2.12.2.patch"
```

PX4 v1.14 has a legacy requirement that modern pip rejects. Pin pip 24 and empy 3.3.4:

```bash
python3 -m venv --system-site-packages "$P450_SITL_ROOT/sim-venv"
"$P450_SITL_ROOT/sim-venv/bin/python" -m pip install 'pip==24.0' 'empy==3.3.4'
"$P450_SITL_ROOT/sim-venv/bin/python" -m pip install \
  -r "$P450_SITL_ROOT/PX4-Autopilot/Tools/setup/requirements.txt"
```

## Build

```bash
cmake -S "$P450_SITL_ROOT/Micro-XRCE-DDS-Agent" \
  -B "$P450_SITL_ROOT/agent-build" -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="$P450_SITL_ROOT/agent-install"
cmake --build "$P450_SITL_ROOT/agent-build" --parallel
cmake --install "$P450_SITL_ROOT/agent-build"

mkdir -p "$P450_SITL_ROOT/ros_ws/src"
ln -s "$P450_SITL_ROOT/px4_msgs" "$P450_SITL_ROOT/ros_ws/src/px4_msgs"
cd "$P450_SITL_ROOT/ros_ws"
source /opt/ros/humble/setup.bash
colcon build --symlink-install

cd "$P450_SITL_ROOT/PX4-Autopilot"
export PATH="$P450_SITL_ROOT/sim-venv/bin:$PATH"
export GZ_CONFIG_PATH="$P450_REPO/config/sitl/gz-garden"
make -j12 px4_sitl
```

`GZ_CONFIG_PATH` is required when Garden and Harmonic coexist; it keeps the PX4 v1.14 CLI on
`gz-sim7` and `gz-transport12` without removing Harmonic.

## Session-only data mount

Do not write `fstab`. Confirm the target is unmounted and empty before mounting:

```bash
mkdir -p "$P450_SITL_ROOT/sim-data"
mountpoint -q /media/p450/P450_DATA && exit 1
sudo mkdir -p /media/p450/P450_DATA
find /media/p450/P450_DATA -mindepth 1 -maxdepth 1 -print -quit
sudo mount --bind "$P450_SITL_ROOT/sim-data" /media/p450/P450_DATA
findmnt --target /media/p450/P450_DATA
```

## Launch order

Terminal A, Agent:

```bash
export LD_LIBRARY_PATH="$P450_SITL_ROOT/agent-install/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
"$P450_SITL_ROOT/agent-install/bin/MicroXRCEAgent" udp4 -p 8888 -v 4
```

Terminal B, PX4 and headless Gazebo Garden:

```bash
cd "$P450_SITL_ROOT/PX4-Autopilot"
export PATH="$P450_SITL_ROOT/sim-venv/bin:$PATH"
export GZ_CONFIG_PATH="$P450_REPO/config/sitl/gz-garden"
HEADLESS=1 make px4_sitl gz_x500
```

Terminal C, localhost-only operator link:

```bash
cd "$P450_REPO"
export PATH="$P450_SITL_ROOT/sim-venv/bin:$PATH"
python3 scripts/p450_sitl_operator_link.py
```

Terminal D, ROS and mission:

```bash
source /opt/ros/humble/setup.bash
source "$P450_SITL_ROOT/ros_ws/install/setup.bash"
export PATH="$P450_SITL_ROOT/sim-venv/bin:$PATH"
export ROS_DOMAIN_ID=0
export ROS_LOCALHOST_ONLY=0
cd "$P450_REPO"
ros2 topic list | sort
```

Require the three `/fmu/in/*` mission topics and the four mandatory `/fmu/out/*` telemetry topics
listed in Issue #1 before continuing.

## Baseline matrix

Use a new TEST_ID for every command. Reset the disarmed simulator to a non-Offboard mode between
active cases with `build/px4_sitl_default/bin/px4-commander mode auto:loiter`.

```bash
python3 -m unittest -v tests/test_p450_delivery_poc_mission.py

python3 scripts/p450_delivery_poc_mission.py --preflight-only \
  --test-id P450_YYYYMMDD_DESKTOP_SITL_SIM_P

python3 scripts/p450_delivery_poc_mission.py --ground-sequence \
  --test-id P450_YYYYMMDD_DESKTOP_SITL_SIM_G \
  --allow-armed --operator-confirmation PROPS_REMOVED_KILL_READY \
  --takeoff-height 0.5 --forward-distance 0

python3 scripts/p450_delivery_poc_mission.py --flight \
  --test-id P450_YYYYMMDD_DESKTOP_SITL_SIM_F1 \
  --allow-armed --operator-confirmation PROPS_INSTALLED_AREA_CLEAR_KILL_READY \
  --takeoff-height 0.5 --forward-distance 0

python3 scripts/p450_delivery_poc_mission.py --flight \
  --test-id P450_YYYYMMDD_DESKTOP_SITL_SIM_F2 \
  --allow-armed --operator-confirmation PROPS_INSTALLED_AREA_CLEAR_KILL_READY \
  --takeoff-height 1.0 --forward-distance 5.0
```

Baseline PASS requires exit 0, Offboard retention until Land request, `nav_state=18`, PX4
auto-disarm-land, no active failsafe, no Agent reconnect, and heartbeat gaps below 250 ms.

## Simulator-only failure injection

Run these only after saving every baseline result.

- Heartbeat: after `HOLD_AFTER_TAKEOFF`, send `SIGSTOP` to only the mission process for 600 ms,
  then `SIGCONT`. Expected: local gap above 250 ms, abort Land, auto-disarm-land, exit 12.
- Mode takeover: at the same hold, run `px4-commander mode posctl`. Expected: mission logs
  `CONTROL_RELINQUISHED`, publishes no later controls or Land, exit 20. The operator then runs
  `px4-commander land` and confirms disarmed.
- Agent stall: send `SIGSTOP` to the single Agent PID for 3 s, then `SIGCONT`. With the tested
  `COM_OF_LOSS_T=1.0` and `COM_OBL_RC_ACT=0`, PX4 reaches POSCTL before the mission's 2 s stale
  telemetry gate is observable again. Expected: stale telemetry abort followed by control
  relinquishment, exit 20, Agent session re-establishment, then operator Land and disarm.

An Agent failure-injection reconnect is expected and must not be confused with the baseline's
no-reconnect criterion.

## Evidence and cleanup

Each active test writes `MISSION_EVENTS.csv` and `HEARTBEAT.csv` below
`/media/p450/P450_DATA/builds/NX-user-storage/rosbags/TEST_ID`. PX4 ULogs are below
`PX4-Autopilot/build/px4_sitl_default/rootfs/log`.

After all processes are stopped and artifacts copied:

```bash
sudo umount /media/p450/P450_DATA
mountpoint -q /media/p450/P450_DATA && exit 1
```

Do not commit PX4/ROS/Agent build trees, install trees, caches, downloads, or Gazebo state.
