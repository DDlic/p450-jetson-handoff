# Post-soak controlled Agent lifecycle checklist

Do not execute this checklist before the retry soak reports `PRELIMINARY_PASS` after at least 120 active samples.

## Verified static identities

- Current Agent binary: `/usr/local/bin/MicroXRCEAgent`
- Current binary SHA-256: `0feffc477e41c2ddd9a15d55fad0e55f27a78c02cb4b89a549851fa97f3017c6`
- Current Agent library SHA-256: `a22396c2047246176b105f568a5377c7ebf1aa6682e91743b27862da59f9bf41`
- Diagnostic binary: `/home/p450/builds/microxrce-agent-2.4.2-agenttrace/build/MicroXRCEAgent`
- Diagnostic binary SHA-256: `0cfabea315262147898fb925308b479726542bd64653fa217c789fddb8e5d3f5`
- Diagnostic library SHA-256: `49478f6957421e3210df81a24324fbaa6a3d471acffdfa93ece9550dc33a1cc1`
- Agent trace patch SHA-256: `bc80d02e4d6b8717a4bef2a8905d28e01ad2e99c445cd7c94e269def7c9a925b`
- Trace parser SHA-256: `4f2265d0e1d68e3c4d2cdc845c458ad5b1e47a29f0a38a27df8acfb273497cec`
- Diagnostic binary RUNPATH resolves its Agent library from the isolated build tree.

These checks prepare Phase 2 only. They do not authorize starting the diagnostic binary.

## Preconditions after the two-hour retry

1. `SOAK_RESULT.txt` says `RESULT=PRELIMINARY_PASS` and `SAMPLES>=120`.
2. `88x2bu` is still absent.
3. Operator is physically present; propellers removed; Pixhawk disarmed and non-Offboard.
4. Phone tether or local console is available; an unexpected NX reboot is acceptable.
5. Agent remains active at PID 1670 with `NRestarts=0` before the lifecycle test.
6. No new kernel panic/Oops/key-GC/hung-task record exists.

## Exactly one lifecycle test

Run only after Codex reviews the completed soak:

```bash
sudo systemctl stop p450-micro-xrce-agent.service
systemctl is-active p450-micro-xrce-agent.service
sudo systemctl start p450-micro-xrce-agent.service
systemctl show p450-micro-xrce-agent.service -p ActiveState -p MainPID -p NRestarts
journalctl -k -b --since '-10 min' --no-pager | rg -i 'panic|oops|key_garbage|hung task' || true
```

If NX hangs or reboots, do not repeat. Preserve `/sys/fs/pstore/*` after reboot and mark Phase 1 FAIL.

If the lifecycle succeeds, Phase 1 is still not complete: keep `88x2bu` absent and perform the required eight-hour post-lifecycle soak. Agent trace/Phase 2 remains blocked until that soak passes.
