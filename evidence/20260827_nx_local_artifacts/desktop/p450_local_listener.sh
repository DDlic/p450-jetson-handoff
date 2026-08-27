#!/usr/bin/env bash

export ROS_DOMAIN_ID=0
export ROS_LOCALHOST_ONLY=1
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp

source /opt/ros/foxy/setup.bash
source /media/p450/P450_DATA/builds/p450_ros2_ws_v115/install/setup.bash
set -u

echo "Local-only read-only listener"
echo "Do not run QGroundControl control actions during this test."
echo "The script does not publish to /fmu/in/* and will write a CSV on the Desktop."
echo "Start it in a local NX terminal, not an SSH terminal, before removing the antenna."

exec python3 /home/p450/Desktop/p450_local_listener.py "$@"
