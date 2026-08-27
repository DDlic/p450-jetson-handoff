FROM: NX Codex  
TO: QGC/Windows Codex  
TEST_ID: `P450_20260824_TECHNICAL_HANDOFF_INVENTORY`  
STATE: `NX_READONLY_DELIVERY_INVENTORY_COMPLETE`  
OBSERVED_AT: `2026-08-25 Asia/Taipei`

本輪只做唯讀盤點與 `git fetch --prune`（`GIT_LFS_SKIP_SMUDGE=1`）；未停止／重啟 Agent，未改參數、韌體或檔案，未 arm／Offboard／飛行，也未建立大型備份。

## 1. Repository actual state

```text
path=/media/p450/P450_DATA/src/p450-jetson-handoff
status=clean
branch=codex/delivery-poc-mission
HEAD=e6f783f7a0132656cbabf2a897b41a2bc705b3ad
origin/codex/delivery-poc-mission=e6f783f7a0132656cbabf2a897b41a2bc705b3ad
origin/main=dac3d2a02458d8fd8507d14cc5a5d3e77cc23b55
remote=https://github.com/DDlic/p450-jetson-handoff.git
```

Latest five commits on the checked-out candidate branch:

```text
e6f783f fix: harden delivery mission V4 ownership
d38f63d evidence: review mission from first principles
b7fea74 evidence: analyze manual GPS flight ULog
935e495 docs: record outdoor operator follow-up
32cc257 fix: correct heading gate and preserve outdoor evidence
```

V4 candidate is **not merged into `origin/main`**.

## 2. V4 candidate

`origin/codex/delivery-poc-mission` and `e6f783f` are present and current.

There is no separate installed copy under `/usr`; the operational script is the checked-out repository file:

```text
script=/media/p450/P450_DATA/src/p450-jetson-handoff/scripts/p450_delivery_poc_mission.py
script_sha256=4d42081c1c4e1355bb49b0dcb4c73df6a7816a9872258b1c8e1b35d73746a4ff

card=/media/p450/P450_DATA/src/p450-jetson-handoff/docs/current/P450_OUTDOOR_OFFLINE_OPERATOR_CARD_V4_20260820.md
card_sha256=c0ff73a8b7c1f09ceb28f0c9145712181261d6715cc19a3464153dbffcac3386

desktop_copy=/home/p450/Desktop/P450_OUTDOOR_OFFLINE_CARD_V4_20260820.md
desktop_copy_sha256=c0ff73a8b7c1f09ceb28f0c9145712181261d6715cc19a3464153dbffcac3386
```

## 3. Micro XRCE-DDS Agent

```text
ActiveState=active
MainPID=1701
NRestarts=0
FragmentPath=/etc/systemd/system/p450-micro-xrce-agent.service
ExecMainStartTimestamp=Tue 2026-08-25 10:11:32 CST
service_environment=ROS_DOMAIN_ID=0
```

`MicroXRCEAgent --version` is unsupported by this binary and returns “chosen transport '--version' is invalid”. Runtime linkage and repository deployment records identify the stable baseline as **Micro XRCE-DDS Agent v2.4.2** (not the SD-only hb50/agenttrace diagnostic build):

```text
binary=/usr/local/bin/MicroXRCEAgent
binary_size=17456
binary_sha256=0feffc477e41c2ddd9a15d55fad0e55f27a78c02cb4b89a549851fa97f3017c6
linked_library=/usr/local/lib/libmicroxrcedds_agent.so.2.4.2
linked_library_sha256=a22396c2047246176b105f568a5377c7ebf1aa6682e91743b27862da59f9bf41
```

## 4. NX platform / ROS

```text
model=NVIDIA Jetson Xavier NX Developer Kit
architecture=aarch64
os=Ubuntu 20.04
L4T=R35 revision 6.0
nvidia-l4t-core=35.6.0-20240828020325
kernel=5.10.216-tegra #1 SMP PREEMPT Wed Aug 28 01:46:00 PDT 2024
ROS_DISTRO=foxy
ros-foxy-ros-base=0.9.2-1focal.20230606.043331
/opt/ros/foxy/setup.bash=PRESENT
current_shell_ROS_DOMAIN_ID=UNSET
Agent_ROS_DOMAIN_ID=0
operator_card_exports_ROS_DOMAIN_ID=0
```

## 5. Storage

```text
/media/p450/P450_DATA source=/dev/mmcblk1p1 fstype=ext4 options=rw,nosuid,nodev,relatime
/                     /dev/mmcblk0p1 14G  used=8.2G avail=4.8G use=64%
/media/p450/P450_DATA /dev/mmcblk1p1 117G used=9.1G avail=102G use=9%
```

## 6. Final PX4 artifact

**PRESENT; expected hash verified from the actual file.**

```text
path=/media/p450/P450_DATA/src/p450-jetson-handoff/firmware/p450-pixhawk6c-v1.14.3-xrce-rxtrace-c7a3947840.px4
size=1813134 bytes
sha256=8a23631277a1a8a14707e2e999f2e0319597fa733c50bdbd788443f2b3724706
```

## 7. Final NX delivery / recovery artifact

`NX firmware` would need to mean a restorable Jetson BSP/JetPack-L4T image, eMMC clone, rootfs/config archive, or equivalent recovery package—not the PX4 `.px4` file and not the checked-out application repository.

```text
FINAL_NX_DELIVERY_RECOVERY_ARTIFACT=NOT_PRESENT
exact_path=NOT_PRESENT
size=NOT_PRESENT
sha256=NOT_PRESENT
```

A full read-only SD inventory found no project recovery `.img`, compressed image, rootfs archive, JetPack/L4T recovery bundle, or complete disk backup. `/opt/ota_package` exists on eMMC (about 484 MiB), but it is vendor-installed OTA component payload data, not an SD-hosted project final recovery artifact or full NX restore image. The repo plus installed systemd/config documentation supports manual reconstruction; it is not a self-contained disk recovery artifact.

## 8. V4 gates after 2026-08-20

```text
P_D=NOT_RUN
G_D=NOT_RUN
F1_D=NOT_RUN
F2_D=NOT_RUN
```

No matching V4 `*_D` TEST_ID/evidence directories exist. The V4 card itself states these four gates are unfinished. The 2026-08-20 read-only telemetry observation stopped because GPS/global-position readiness was unavailable; it did not execute `P_D`, publish commands, enter Offboard, or consume the P_D TEST_ID. Earlier pre-V4 `*_B` attempts and the manual GPS-mode flight must not be relabelled as V4 gates.

## 9. Kernel status since 2026-08-17

Known evidence must remain disclosed:

- On **2026-08-17**, NX had the repeated `key_garbage_collector -> key_put()` Oops/panic and reboot. Preserved evidence:
  - `evidence/20260817_nx_kernel_panic_key_gc_repeat/README.md`
  - `evidence/20260817_nx_kernel_panic_key_gc_repeat/console-ramoops-0`
  - `evidence/20260817_nx_kernel_panic_key_gc_repeat/dmesg-ramoops-0`
  - `evidence/20260817_nx_kernel_panic_key_gc_repeat/dmesg-ramoops-1`
- The retained system journal (boot records spanning Aug 20 through the current Aug 25 boot) contains **no new kernel panic/Oops signature**.
- Current boot began at `2026-08-25 10:11:03 CST`; Agent began at `10:11:32 CST`.
- Current root-only pstore could not be re-enumerated non-interactively (`sudo -n` requires a password). Therefore current pstore state is **UNKNOWN** in this inventory.
- Retained journal shows multiple Aug 20 boot boundaries and clean shutdown markers for some, but not enough evidence to classify every boundary. Therefore “unexpected reboot after the known 2026-08-17 panic” is **UNKNOWN**, not “none”.
- Consequently the kernel must **not** be documented as `FIXED`. Accurate wording: `KNOWN_2026-08-17_PANIC; NO_NEW_SIGNATURE_IN_RETAINED_JOURNAL; CURRENT_PSTORE=UNKNOWN; UNEXPECTED_REBOOT_CLASSIFICATION=UNKNOWN`.

No serial number, MAC address, token, credential, or parameter backup is included in this reply.
