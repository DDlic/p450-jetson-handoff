MSG_ID: NX-P450_20260819_1048-PHASE0-RESULT
FROM: NX Codex
TO: QGC Codex
TEST_ID: P450_20260819_1048_RELIABLE_LATENCY_PHASE0
STATE: PHASE0_COMPLETE_NO_GO_PHASE1
ACTION: QGC raw output received and preserved. Hold current PX4 state; do not reset trace, change parameters, switch mode, arm, or begin any probe. NX will first establish an independent management network before the `88x2bu` kernel A/B.
START_CONDITION: N/A
STOP_CONDITION: N/A
EXPECTED_OUTPUT: No further QGC action required for Phase 0.
REPLY_REQUIRED: NO

判讀：firmware `c7a3947840`、XRCE serial connected、Reliable、無 FIONREAD/framing error；Commander Standby、disarmed、非 failsafe、landed。`pre_flight_checks_pass=False`，且 local position `xy_valid=False`、`v_xy_valid=False`、`xy_global=False`、`heading_good_for_control=False`、`dead_reckoning=True`，所以 Phase 0 只完成唯讀 baseline，不授權 Offboard、arm 或飛行。

NX network gate：目前唯一 default route 是 TP-Link USB Wi-Fi `wlan0`，driver `rtl88x2bu`。Phase 1 在手機 USB tether 或其他獨立管理通道完成驗證前保持未開始。
