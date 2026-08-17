# P450 NX workspace rules

## Storage policy

- Treat the 14 GB eMMC as system/runtime storage only.
- Put every new Git clone under `/media/p450/P450_DATA/src`.
- Put build trees, downloaded archives, logs, traces, generated evidence and temporary output on
  `/media/p450/P450_DATA`, normally below `builds/NX-user-storage`.
- Use `git-clone-sd`/`sdclone` instead of cloning into `/home/p450` or `/tmp`.
- Honor `TMPDIR`, `ROS_LOG_DIR`, `COLCON_LOG_PATH`, `PIP_CACHE_DIR` and `XDG_CACHE_HOME`.
- Before creating more than 50 MB, verify the SD is mounted and check `df -h / /media/p450/P450_DATA`.
- Do not place large temporary kernel or source clones in `/tmp`; `/tmp` is backed by eMMC on this NX.
- Preserve `/usr`, `/opt/ros`, `/opt/ota_package`, ROS workspace `install/`, boot files and active
  system services on eMMC unless the owner explicitly authorizes a system-layout change.
- If the SD is unavailable, stop large write operations instead of silently falling back to eMMC.

