# PX4 v1.14.3 receive-drain candidate pre-flash repackage

Collected: 2026-08-11 (Asia/Taipei)

Status: candidate artifact rebuilt and verified; not flashed yet.

## Recovery point

- Git repository began clean at commit `0bbc97d` and matched `origin/main`.
- `p450-micro-xrce-agent.service` was active with PID 1693, `NRestarts=0`, and
  `ExecMainStatus=0`.
- `/dev/ttyTHS1` had exactly one holder: the systemd Micro XRCE-DDS Agent at 460800 baud.
- No test publisher process remained.
- The ROS graph contained only `/rosout` and `/parameter_events`; the flight controller had not
  established an XRCE session at this recovery point.
- eMMC had 3.8 GB free; `P450_DATA` had 106 GB free. The firmware build remained on the SD data
  volume.

## Problem found before flashing

The existing candidate file had the expected filename, source tree, patch, image size, and SHA from
the 2026-08-04 build, but its package metadata still reported the ping-only source:

```text
candidate source HEAD: 49049d855552c39879234bf4f19229baf0939a48
old package git_identity: v1.14.3-1-gf9bc66c6f3
old package SHA-256: d371a5e7ccde6da7832c9dd0dcbce8a078d459b6239d97a79924b0b1aa0a8bdd
```

Timestamp and build-object checks showed why: the modified `uxrce_dds_client.cpp` was compiled at
11:41, the ELF/package was linked at 11:42, and source commit `49049d8555` was created at 11:43.
The receive-drain code was therefore compiled before the commit existed, leaving the generated Git
version header at `f9bc66c6f3`. This made post-flash `ver all` unable to distinguish the candidate
from the ping-only baseline.

## Source and patch verification

The SD source tree was clean at:

```text
49049d8555 backport XRCE receive queue drain fix
f9bc66c6f3 backport PX4 XRCE session ping fix
1dacb4cdef tag v1.14.3
```

The only candidate commit change is 11 insertions and one deletion in
`src/modules/uxrce_dds_client/uxrce_dds_client.cpp`. It replaces one
`uxr_run_session_timeout(&session, 0)` call with a bounded loop of at most ten calls, stopping when
`num_payload_received` no longer increases. The repository patch is
`patches/px4-v1.14.3-uxrce-rx-drain-backport.patch`.

## Corrected build

An incremental relink/package was run in the existing SD build directory. It regenerated the Git
version header, relinked the ELF, regenerated the binary, and created a new `.px4` package without
changing source code.

```text
FLASH: 1,937,764 / 1,966,080 bytes (98.56%)
board_id: 56
image_size: 1,937,764
git_identity: v1.14.3-2-g49049d8555
git_hash: 49049d855552c39879234bf4f19229baf0939a48
file_size: 1,808,290 bytes
SHA-256: ba1a57ad2b48fba9908d7caf34ad5f32d7aea8c0d7bdbe74016b2862aad8e1b5
```

The SD build output and repository artifact matched byte-for-byte. Running `sha256sum -c` from the
repository `firmware/` directory passed for all five stored firmware files.

Artifact:

```text
firmware/p450-pixhawk6c-v1.14.3-xrce-rx-drain-ping-fix-49049d8555.px4
```

The former `d371a5e7...a0a8bdd` package is superseded and must not be flashed. The corrected artifact
still requires owner-controlled QGC flashing. After flashing, `ver all` must report source
`49049d855552c39879234bf4f19229baf0939a48` before any ROS input test begins.
