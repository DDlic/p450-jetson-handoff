# P450 repository working rules

These instructions apply to the whole repository. More specific `AGENTS.md` files may add constraints for their subtree; they may not weaken the preservation or flight-safety rules below.

## Repository purpose

This repository is the auditable handoff record for one AMOV P450 / Jetson Xavier NX / Pixhawk 6C integration. It contains operating documents, ROS 2 diagnostic scripts, PX4 firmware artifacts and patches, and experiment evidence. It is not a single buildable ROS package.

Start at `README.md`, then use `docs/INDEX.md` and `docs/current/DOC_INVENTORY.md` to find the current authority. A newer dated experiment may qualify an older conclusion; do not silently combine incompatible test conditions.

## Non-deletion and evidence preservation

- Do not delete a pre-existing tracked file during repository cleanup. Classify it, preserve it, or move it with `git mv`.
- Treat firmware binaries, CSV files, console captures, pstore/ramoops captures, patch files, and other raw payloads under `evidence/` as immutable observations. Evidence `README.md`/`SUMMARY.md` files may receive link-only maintenance during a documented structural move; do not alter their measurements or conclusions.
- Before and after a structural change, run `.agents/skills/p450-repo-curator/scripts/audit_repo.py --base-ref origin/main` and inspect `git diff --name-status --find-renames origin/main`. A plain `D` status is a stop condition.
- Preserve Git history and use one branch/PR per structural phase. Merge a phase to `main` before cutting the next phase branch.
- After moving Markdown, update every relative link in the same commit and rerun the audit.

## Authority order

When documents disagree, use this order:

1. Raw evidence and checksums for what was directly observed.
2. The newest test summary that cites that evidence and matches the same firmware, QoS, Agent, baud, topic set, duration, and vehicle state.
3. Current runbooks and explicit safety gates.
4. `README.md` and current handoff indexes.
5. Dated reports, historical handoffs, prompts, and free-form notes.

Mark conclusions as observed, inferred, or unverified. Keep counterevidence and unresolved unknowns visible. For a contested transport or flight decision, use `build-evidence-map` rather than flattening disagreement into one paragraph.

## Physical-system safety

- Repository edits do not authorize physical flight, propeller installation, arming, parameter changes, firmware flashing, Agent restarts, or service changes.
- Prefer static analysis, CSV analysis, SITL, read-only ROS graph inspection, and propeller-free ground gates.
- Any real-hardware control step requires the owner/operator's explicit confirmation at that step, a clear test ID, an emergency mode/kill path, and the stop conditions from the applicable runbook.
- Do not weaken `COM_OF_LOSS_T`, force arm/disarm, or reinterpret a repository engineering gate merely to obtain a passing demo.
- The current repository records Reliable final-delivery success but an unresolved freshness tail and an NX kernel panic gate. Do not describe the system as generally flight-safe.

## NX storage policy

- Treat the 14 GB eMMC as system/runtime storage only.
- Put clones, builds, logs, generated evidence, downloads, caches, and temporary output under `/media/p450/P450_DATA` as detailed in `config/AGENTS.md` and the SD storage runbook.
- Before writing more than 50 MB on NX, verify the SD mount and capacity. Stop rather than silently falling back to eMMC.

## Verification commands

Run from the repository root:

```bash
python3 -m compileall -q scripts .agents/skills/p450-repo-curator/scripts
python3 .agents/skills/p450-repo-curator/scripts/audit_repo.py --base-ref origin/main
(cd firmware && sha256sum -c SHA256SUMS)
git diff --check
git diff --name-status --find-renames origin/main
```

`sha256sum -c` verifies stored firmware artifacts only; it does not make a firmware safe to flash. ROS imports and hardware behavior can only be exercised in the matching NX/PX4 environment.
