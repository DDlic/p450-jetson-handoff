# NX kernel panic during ROS 2 CLI diagnostics (2026-08-14)

## Outcome

The two apparent freezes/reboots were not PX4 resets and were not normal Linux reboots. The second event was captured by Jetson ramoops as a Linux kernel panic in the memory-cgroup/list-LRU path while PID 1 (`systemd`) was reaping an exited process.

ROS 2 CLI activity is a reproducible trigger candidate because the panic happened while short-lived `ros2`/`timeout` processes were being started and reaped. It is not yet evidence that ROS 2 or the PX4 firmware corrupted the kernel.

## Captured failure

- Platform: Jetson Xavier NX, L4T R35.6.0
- Kernel: `5.10.216-tegra #1 SMP PREEMPT Wed Aug 28 01:46:00 PDT 2024`
- Panic uptime: `669.850017` seconds
- Fault address: `0000000200000010`
- Faulting task: `PID 1`, `Comm: systemd`
- Kernel taint: `G OE`
- Out-of-tree module present: `88x2bu(OE)`, version `v5.13.1-30-g37e60b26a.20220819_COEX20220812-18317b7b`

The decisive call trace is:

```text
mem_cgroup_from_obj
list_lru_del
d_lru_del
select_collect
d_walk
shrink_dcache_parent
d_invalidate
proc_invalidate_siblings_dcache
proc_flush_pid
release_task
wait_consider_task
do_wait
kernel_waitid
__do_sys_waitid
```

It ended with:

```text
Kernel panic - not syncing: Oops: Fatal exception
```

There was no OOM, thermal throttle, undervoltage, NVRM Xid, or normal shutdown sequence in the captured pre-panic log. The root filesystem performed recovery on the next boot, which is consistent with an unclean reset.

Raw evidence and SHA-256 at capture time:

```text
ae29ac5ab38f9eec155ab5592e376b679e4d68e3b9653c6f9762bbd791284077  console-ramoops-0
a9166e50f5f70d0444b461fa042f91b6b9f690fbe9dcfb4cc7ec2aa82e899042  dmesg-ramoops-0
9386a92c4df8136977bd64a54aff41ba61cd60116fc0ed7d49f59df847811ff6  dmesg-ramoops-1
```

The two `dmesg-ramoops` files are records from the same captured panic, not proof that both observed reboots had an identical stack.

## Why `cgroup.memory=nokmem` is the first A/B workaround

NVIDIA's R35.6.5 `mm/memcontrol.c` states that `mem_cgroup_from_obj()` requires the caller to ensure the memcg lifetime. The R35.6.5 `mm/list_lru.c` still calls it from `list_lru_from_kmem()` in the same family of path seen in the panic.

The same NVIDIA source implements the boot option `cgroup.memory=nokmem`: `memcg_online_kmem()` returns without enabling kernel-object memory accounting. This is narrower than disabling the entire memory controller and should not affect ROS 2, DDS, PX4 UART transport, or normal userspace memory allocation.

References:

- NVIDIA Jetson Linux R35.6.5 source: <https://gitlab.com/nvidia/nv-tegra/linux-5.10/-/tree/jetson_35.6.5>
- NVIDIA Jetson Linux R35.6.5 release page: <https://developer.nvidia.com/embedded/jetson-linux-r3565>
- Linux kernel parameter documentation: <https://www.kernel.org/doc/html/v6.9/admin-guide/kernel-parameters.html>
- Related upstream list-LRU memcg lifetime discussion: <https://lore.kernel.org/linux-mm/20240718083607.2791764-1-songmuchun@bytedance.com/>

This is a workaround and an A/B test, not yet a proven permanent fix. The out-of-tree `88x2bu` Wi-Fi driver remains a secondary memory-corruption suspect because it taints the kernel, but the captured call trace is not inside that driver.

## Installed boot configuration

The default extlinux entry was changed to a new label:

```text
DEFAULT p450-sdmmc3-uartb460800-nokmem
```

Its existing custom kernel, SDMMC3/Wi-Fi/UARTB DTB, initrd, and command line are preserved; only this parameter was appended:

```text
cgroup.memory=nokmem
```

The previous default entry remains selectable as `p450-sdmmc3-uartb460800`.

On-device backup:

```text
/boot/extlinux/extlinux.conf.pre-nokmem-20260814
```

Backup SHA-256:

```text
1f735d5290b88f0abd022f42a2e5e2d1d55e78a91070b4b5a34bbee636d55e09
```

Persistent journaling was enabled by creating `/var/log/journal`, so a future crash can be inspected with `journalctl -b -1` in addition to ramoops.

## Post-reboot validation

Do not resume flight-related testing until these checks pass:

1. Confirm `/proc/cmdline` contains `cgroup.memory=nokmem`.
2. Confirm the custom DTB behavior remains intact: SD card, Wi-Fi, and UART `/dev/ttyTHS1`.
3. Confirm `p450-micro-xrce-agent.service` owns `/dev/ttyTHS1` and remains active.
4. Use `ROS_LOCALHOST_ONLY=0`; `ROS_LOCALHOST_ONLY=1` hides the Agent-created DDS participant and falsely shows only `/rosout` and `/parameter_events`.
5. Repeat the exact read-only ROS topic discovery/subscription sequence that preceded the panic.
6. Keep the system up past the prior 670-second panic point and inspect current kernel logs/pstore.
7. Only after the kernel A/B passes, run the 125-second 10 Hz reliable OffboardControlMode heartbeat probe. It must remain disarmed and non-Offboard and must not publish setpoints or vehicle commands.

If the same panic recurs with `nokmem`, the next software-only A/B is to avoid loading `88x2bu` and use another network path. The long-term options are an exact NVIDIA-kernel backport or a validated newer BSP/kernel; a blind point-release upgrade is not considered proof because the R35.6.5 source still contains the relevant old list-LRU implementation.

## Post-reboot A/B result

The controlled reboot at 2026-08-14 15:24 CST loaded the intended workaround:

```text
CMDLINE_NOKMEM=PASS
cgroup.memory=nokmem
```

The existing custom hardware configuration survived the boot:

- `/media/p450/P450_DATA` mounted from `/dev/mmcblk1p1`.
- `wlan0` associated normally.
- `/dev/ttyTHS1` existed and was exclusively owned by the active
  `p450-micro-xrce-agent.service`.
- Agent `NRestarts=0`.
- The complete `/fmu/in/*` and `/fmu/out/*` ROS graph was discovered with
  `ROS_LOCALHOST_ONLY=0`.

The exact ROS CLI/`timeout` process-exit sequence that preceded the captured panic was
repeated after reboot. The host remained alive, the kernel log contained no new panic/oops,
and kernel-memory cgroup counters stayed at zero before and after the sequence:

```text
memory.kmem.usage_in_bytes=0
memory.kmem.max_usage_in_bytes=0
memory.kmem.failcnt=0
```

A disarmed-only reliable OffboardControlMode probe then ran at 10 Hz for 125 seconds.
It published no setpoint and no vehicle command. Result:

```text
publishes=1251
mean_gap_ms=99.985198
min_gap_ms=82.593
p50_ms=103.699
p95_ms=115.929
p99_ms=118.034
p999_ms=119.186
max_gap_ms=120.436
over_150ms=0
over_250ms=0
over_500ms=0
```

All 1251 rows reported:

```text
subscription_count=1
arming_state=1 (disarmed)
nav_state=4
nav_state_user_intention=4
failsafe=0
```

Raw CSV:

```text
post_nokmem_heartbeat_10hz_reliable_125s.csv
SHA-256 89c4a1e80ac8f441584e71d98afddfa494cf180a78b57bb805ade5fcb002e1e8
```

The host stayed healthy past the previous 669.85-second panic point. At 727 seconds:

```text
Agent active
Agent NRestarts=0
kernel Oops/panic=0
memory available approximately 5.0 GiB
```

Therefore `cgroup.memory=nokmem` passes this first kernel-panic A/B. This is not proof of
long-term kernel reliability, but it is sufficient to resume controlled software-only ROS/XRCE
diagnostics while persistent journal and ramoops remain enabled.

The PX4-side status/trace was also captured. It showed a separate transport failure despite the
clean NX publisher CSV:

```text
Offboard RX count=1251
max_gap_us=506727
over_150/250/500_ms=83/23/1
trace frozen=1
trace trigger_gap_us=397990
```

The ring records later reliable sequences arriving while earlier sequences were absent. In the
trigger event, seq 61 arrived while `last_handled=57`; `first_unacked=58` and NACK bitmap
`0x0007`. Seq 58 later arrived and unblocked delivery, producing the 397.990 ms Offboard
receipt gap. This proves a reliable sequence hole with head-of-line blocking at the PX4 Client.
It does not yet distinguish Agent send delay from UART/framing loss before the Client.

The dedicated two-Codex coordination and QGC capture procedure is documented in
`../../QGC_LAPTOP_CODEX_HANDOFF_20260814.md`. The raw PX4 console output remains in
`../../雙端交接文件.txt`.
