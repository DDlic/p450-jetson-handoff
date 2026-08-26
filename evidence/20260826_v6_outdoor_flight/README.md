# V6 戶外飛行執行紀錄（2026-08-26）

本文件依操作者於 NX 終端貼出的完整執行輸出建立；未修改任何既有 ULog、mission log 或 V6 腳本。此次紀錄尚未包含 QGC/ULog 原始檔，因此數值以終端輸出為準。

## 測試紀錄

| TEST_ID | 結果 | Exit | 關鍵結果 | Heartbeat |
|---|---:|---:|---|---|
| `P450_20260826_OUTDOOR_V6_FLIGHT_1M_5M_A` | intentional preflight refusal；目錄已存在 | 2 | 未發布控制、未解鎖；既有 evidence 未修改 | 不適用 |
| `P450_20260826_OUTDOOR_V6_FLIGHT_1M_5M_B` | FAIL / safety abort | 12 | Preflight PASS；Offboard、EKF settle、Arm 成功；`TAKEOFF ABORT takeoff timeout`；Land；PX4 auto-disarm confirmed | publishes=233；max=113.421 ms；>250 ms=0 |
| `P450_20260826_OUTDOOR_V6_FLIGHT_1M_5M_C` | FAIL / safety abort | 12 | Preflight PASS；Offboard、EKF settle、Arm、takeoff/hold 成功；`EKF_Z_RESET dz=-0.589111 m`，超過 0.20 m；Land；PX4 auto-disarm confirmed | publishes=197；max=156.709 ms；>150 ms=1；>250 ms=0 |
| `P450_20260826_OUTDOOR_V6_FLIGHT_1M_5M_D` | PASS | 0 | Preflight PASS；Offboard、EKF settle、Arm、0.5 m takeoff、5 m forward、Land；PX4 auto-disarm confirmed | publishes=339；max=152.969 ms；>150 ms=1；>250 ms=0 |
| `P450_20260826_OUTDOOR_V6_FLIGHT_1M_5M_E` | FAIL / safety abort | 12 | Preflight PASS；Offboard、EKF settle、Arm 成功；`TAKEOFF ABORT takeoff timeout`；Land；PX4 auto-disarm confirmed | publishes=228；max=155.566 ms；>150 ms=2；>250 ms=0 |

## 完整狀態摘要

- A：因重用已存在的 TEST_ID 被拒絕，沒有覆蓋既有資料。
- B：完成 Offboard/Arm 後起飛逾時；腳本進入 `REQUEST_LAND_ABORT`，確認 `nav_state=18` 及 PX4 auto-disarm，exit 12。
- C：起飛後在 `HOLD_AFTER_TAKEOFF` 觀測到 Z reset `0.589111 m`，腳本依 0.20 m 門檻中止並 Land，確認 PX4 auto-disarm，exit 12。
- D：完成 0.5 m 起飛、前進 5 m、Land 與 PX4 auto-disarm，exit 0。
- E：完成 Offboard/Arm 後起飛逾時；腳本進入 `REQUEST_LAND_ABORT`，確認 `nav_state=18` 及 PX4 auto-disarm，exit 12。

## 範圍聲明

這是 V6 操作者終端輸出的轉錄紀錄，不是對機體整體飛行安全性的宣告；A–E 的原始 mission log 仍位於各自 TEST_ID 目錄，應保持不可覆寫。
