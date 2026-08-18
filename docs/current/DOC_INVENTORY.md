# Document inventory and authority map

Inventory date: 2026-08-18 (Asia/Taipei)
Repository baseline: `DDlic/p450-jetson-handoff`, `main`, commit `54ee3449d6e2cbb65a469a55cf50e0637cc45d42`.

## Classification rules

- **Current index**: navigation only; it must point to more specific authority.
- **Current handoff**: active cross-machine or cross-agent coordination information.
- **Runbook**: executable procedure with prerequisites, stop conditions, and rollback.
- **Report**: dated interpretation of a test or engineering phase; later evidence may supersede it.
- **History**: useful narrative or former instructions, not the current execution authority.
- **Raw note/capture**: preserved source material that must not be treated as a verified conclusion by itself.

“Superseded” means “do not execute as the newest instruction”; it does not mean “delete.”

## Classified artifacts

| Current path | Class | Authority/status |
|---|---|---|
| `README.md` | Current index | Kept at root; newest top-level warnings |
| `docs/operations/GIT_HANDOFF_SETUP.md` | Operations | Useful Git setup procedure |
| `docs/operations/JETSON_HANDOFF_COMMANDS.md` | Operations/history | Mixed command reference; dated state must be checked against current runbooks |
| `docs/history/JETSON_HANDOFF_HISTORY.md` | History | Historical NX rebuild timeline |
| `docs/history/JETSON_HANDOFF_MASTER.md` | History | Former master; README explicitly contains newer stop points |
| `docs/history/handoffs/JETSON_HANDOFF_PROMPT_FOR_CODEX_CLI.md` | History/handoff | Former CLI prompt; retain for provenance, not current authority |
| `docs/reports/2026-08-05/P450_COMPLETE_ENGINEERING_TIMELINE_AND_PRESENTATION_2026-08-05.md` | Report | Presentation/engineering synthesis dated 2026-08-05 |
| `docs/history/handoffs/P450_CONVERSATION_HANDOFF_20260817.md` | History/handoff | Conversation provenance and context, not a safety gate |
| `docs/runbooks/P450_DELIVERY_POC_OFFBOARD_RUNBOOK_2026-08-17.md` | Runbook | Current, narrow PoC authority; does not declare general flight safety |
| `docs/history/handoffs/P450_Jetson_Xavier_NX_交接文件.md` | History/handoff | Early broad handoff, superseded by later state |
| `docs/reports/2026-08-03/P450_POSTFLASH_XRCE_TEST_2026-08-03.md` | Report | Dated post-flash test record |
| `docs/reports/2026-07-20/P450_PROGRESS_2026-07-20.md` | Report | Weekly progress snapshot |
| `docs/reports/2026-07-22/P450_PROGRESS_2026-07-22_ROS2_OFFLINE.md` | Report | ROS 2/offline setup snapshot with later appendices |
| `docs/reports/2026-07-24/P450_PROGRESS_2026-07-24_NEXT.md` | Report/plan | Historical next-step plan, largely superseded |
| `docs/reports/2026-08-05/P450_PX4_NX_XRCE_ROOT_CAUSE_AND_TEST_PLAN_2026-08-05.md` | Report/test plan | Important historical root-cause plan; newer reliable evidence qualifies it |
| `docs/reports/2026-08-10/P450_PX4_V1143_FINAL_BASELINE_AND_NX_EVIDENCE_REQUEST_2026-08-10.md` | Report/handoff | v1.14.3 baseline and evidence request |
| `docs/reports/2026-08-10/P450_PX4_V1143_PING_BIDIRECTIONAL_TEST_2026-08-10.md` | Report | v1.14.3 bidirectional test result |
| `docs/reports/2026-08-04/P450_PX4_V1154_XRCE_TEST_2026-08-04.md` | Report | v1.15.4 experiment; not the installed reliable baseline |
| `docs/runbooks/P450_RELIABLE_LATENCY_REMEDIATION_RUNBOOK_2026-08-17.md` | Runbook | Current transport remediation authority |
| `docs/current/QGC_LAPTOP_CODEX_HANDOFF_20260814.md` | Current handoff | Current QGC-side coordination details; verify test IDs against evidence |
| `docs/runbooks/SD_STORAGE_POLICY_20260817.md` | Runbook | Current NX storage policy |
| `docs/raw/notes/new point.md` | Raw note | Unstructured working notes; preserved verbatim |
| `docs/raw/captures/px4_uxrce_dds_console_latest.txt` | Raw capture | Console fragment; context must be supplied by a report/evidence directory |
| `docs/raw/captures/mav_con` | Raw capture | MAVLink console fragment; extensionless, preserved verbatim |
| `docs/raw/notes/新增 文字文件.txt` | Raw note | Unstructured note; preserved verbatim |
| `docs/raw/notes/雙端交接文件.txt` | Raw handoff | Unstructured dual-end handoff; preserved verbatim |

## Non-document roots that remain stable

`.gitattributes`, `.gitignore`, `README.md`, `AGENTS.md`, `.agents/`, `config/`, `docs/`, `evidence/`, `firmware/`, `patches/`, `scripts/`, and `systemd/` remain at their conventional root paths. `evidence/` is already timestamp-partitioned and was not reorganized merely for appearance.

## Current conflict resolution

- Reliable transport has demonstrated `6001/6001` eventual receipt, but the same 600-second field contains a `601.548 ms` maximum receipt gap and fails the repository's 250 ms engineering freshness gate. “No final loss” and “deadline-safe” are different claims.
- The 601.548 ms sample remained below the configured `COM_OF_LOSS_T=1.0 s` in that disarmed test. This qualifies the immediate PoC risk but does not prove armed/outdoor tail latency or general flight safety.
- The delivery PoC runbook is a risk-accepted, operator-controlled exception path. It does not override the transport or repeated NX kernel panic gates.
- “Takeoff detected / not landed” is treated as a land-detector/state-observation issue requiring explicit touchdown/landed confirmation, not as permission to force disarm.
