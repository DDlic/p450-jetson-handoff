# PX4 v1.14.3 UART RX diagnostic firmware build

Built: 2026-08-12 (Asia/Taipei)

Status: source, patch, incremental build, firmware metadata, embedded diagnostic strings, FLASH,
and SHA-256 verified. Not flashed.

## Why this build exists

The `49049d8555` payload-count drain candidate passed ten-minute PX4-to-NX continuity but failed a
valid live 2 Hz NX-to-PX4 marker test. Its loop uses complete topic payload bytes as the break
condition, so it cannot distinguish no UART bytes from partial or invalid serial framing.

PX4 upstream commit `3169dc6b1b17d138d1e04228e400814ed79d0e63` later used transport-level
`FIONREAD` for bounded draining. Before backporting another behavior change, this diagnostic build
measures the same transport boundary on the actual P450 hardware.

## Source lineage

```text
1dacb4cdef  official v1.14.3 tag
f9bc66c6f3  session-ping backport
49049d8555  payload-count receive-drain backport
f6beb984ca  serial RX diagnostics
```

Branch: `p450-v1.14.3-xrce-rxdiag`

The diagnostic commit changes only:

```text
src/modules/uxrce_dds_client/uxrce_dds_client.cpp
src/modules/uxrce_dds_client/uxrce_dds_client.h
```

Patch: `patches/px4-v1.14.3-uxrce-rxdiag.patch`

## Diagnostic counters

`uxrce_dds_client status` gains:

```text
Serial RX pending samples
Serial RX pending bytes observed
Serial RX pending max
Serial RX FIONREAD errors
Complete payload bytes received
Serial framing: state, buffered bytes, message progress
```

The run loop performs one read-only `FIONREAD` sample before the existing receive-drain logic. It
does not alter topics, parameters, flight behavior, receive timeout, poll rate, output rate, or the
payload-count drain algorithm.

## Build verification

Incremental build completed all 22 steps successfully. The linker reported:

```text
FLASH: 1,938,252 / 1,966,080 bytes (98.58%)
AXI_SRAM: 61,480 / 524,288 bytes (11.73%)
```

Firmware package metadata:

```text
board_id: 56
description: Firmware for the PX4FMUv6C board
image_size: 1,938,252
git_identity: v1.14.3-3-gf6beb984ca
git_hash: f6beb984ca0b8805735475cc57cf1db278d53a67
```

All six expected diagnostic format strings were found in the linked ELF. The source tree and all
recursive submodules were clean after the build.

Artifact:

```text
firmware/p450-pixhawk6c-v1.14.3-xrce-rxdiag-f6beb984ca.px4
file size: 1,808,998 bytes
SHA-256: 419565d7ad6239272e0854c7b9da2a20a8133d6306f1b554475bfaa0f141b875
```

This firmware is not authorized for automatic flashing. It must remain a no-prop, disarmed,
non-control diagnostic image. The first post-flash QGC command must verify source `f6beb984ca`.
