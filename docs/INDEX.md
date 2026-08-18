# P450 repository index

This index separates current decision material from dated history and raw evidence. No pre-existing file was removed to create it.

## Start here

1. [`README.md`](../README.md) — current top-level state and warnings.
2. [`current/DOC_INVENTORY.md`](current/DOC_INVENTORY.md) — authority, class, and planned location for every root-level handoff artifact.
3. [`architecture/REPOSITORY_MAP.md`](architecture/REPOSITORY_MAP.md) — repository architecture, runtime path, verification surface, and known contradictions.
4. [`P450 delivery PoC runbook`](../P450_DELIVERY_POC_OFFBOARD_RUNBOOK_2026-08-17.md) — narrowly scoped delivery demonstration path and safety boundary.
5. [`Reliable latency remediation runbook`](../P450_RELIABLE_LATENCY_REMEDIATION_RUNBOOK_2026-08-17.md) — transport diagnosis and staged remediation.

## Stable technical areas

- [`scripts/`](../scripts/) — ROS 2 probes, monitors, guarded control diagnostics, and NX storage helpers.
- [`systemd/`](../systemd/) — installed Micro XRCE-DDS Agent service definition.
- [`patches/`](../patches/) — PX4 XRCE changes, preserved as reviewable patches.
- [`firmware/`](../firmware/) — versioned `.px4` artifacts, checksums, and artifact-specific safety notes.
- [`evidence/`](../evidence/) — timestamped experiment results and raw captures. Treat as append-only.
- [`config/`](../config/) — NX runtime/storage configuration and subtree instructions.

The next structural phase will move root-level reports and handoffs into `docs/` with `git mv`, then update all links. Until that phase is merged, the inventory's “planned path” column is a plan, not the current path.
