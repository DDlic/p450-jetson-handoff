# P450 NX kernel Phase 1 `88x2bu` active-soak retry

- TEST_ID: `P450_20260819_1425_KERNEL_PHASE1_88X2BU_AB_RETRY`
- Reason: the first soak entered deep suspend after about 61 active minutes.
- Conditions: `88x2bu` remains absent; original Agent PID 1670 remains active with `NRestarts=0`; no Agent lifecycle action is allowed.
- This retry uses a temporary systemd sleep inhibitor and records state every 60 seconds for at least 7200 active wall-clock seconds.
- Network access is not required. Phone USB tether may be absent, but USB devices must not be repeatedly toggled during the run.

PASS candidate requires at least 120 samples, no suspend, `88x2bu` absent, Agent active at PID 1670 with zero restarts, and zero kernel panic/Oops/key-GC/hung-task records.
