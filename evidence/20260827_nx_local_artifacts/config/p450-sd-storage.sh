#!/bin/sh
# P450 user-session storage policy. Source from ~/.profile and ~/.bashrc.
P450_SD_MOUNT="/media/p450/P450_DATA"
P450_SD_RUNTIME="${P450_SD_MOUNT}/builds/NX-user-storage"
P450_SD_SOURCE_ROOT="${P450_SD_MOUNT}/src"

if [ "$(findmnt -rn -T "${P450_SD_MOUNT}" -o TARGET 2>/dev/null)" = "${P450_SD_MOUNT}" ]; then
    export P450_SD_MOUNT P450_SD_RUNTIME P450_SD_SOURCE_ROOT
    export TMPDIR="${P450_SD_RUNTIME}/tmp"
    export ROS_LOG_DIR="${P450_SD_RUNTIME}/ros/ros-log"
    export COLCON_LOG_PATH="${P450_SD_RUNTIME}/ros/colcon-log"
    export PIP_CACHE_DIR="${P450_SD_RUNTIME}/xdg-cache/pip"
    export NPM_CONFIG_CACHE="${P450_SD_RUNTIME}/xdg-cache/npm"
    export CUDA_CACHE_PATH="${P450_SD_RUNTIME}/xdg-cache/nvidia/ComputeCache"
    export CCACHE_DIR="${P450_SD_RUNTIME}/ccache"

    if [ -L "${HOME}/.cache" ] &&
       [ "$(readlink -f "${HOME}/.cache")" = "${P450_SD_RUNTIME}/xdg-cache" ]; then
        export XDG_CACHE_HOME="${P450_SD_RUNTIME}/xdg-cache"
    fi
fi
