# P450 PX4 v1.14.3 ping 回補版雙向通訊驗證（2026-08-10）

## 1. 結論先行

本輪已確認兩件必須分開描述的事：

1. **PX4→NX 純接收與 XRCE session continuity 通過。**正式 10 分鐘測試收到
   42,718 筆 `SensorCombined`，平均 71.196 Hz，最大 gap 38.913 ms，沒有任何
   超過 100 ms 的 gap；Agent PID 與 restart count 全程不變。
2. **NX→PX4 的 2 Hz 即時新鮮度失敗。**PX4 最終曾收到正確 marker，證明路徑並非
   完全斷線；但 NX 仍以 2 Hz 持續發布時，QGC 看到的最新 uORB 樣本已落後
   58.383400 秒。這是飛控端 XRCE 收件飢餓或極端延遲，不符合 Offboard 所需的
   持續即時資料流。

因此目前判定是：**session-ping 回補解決了舊有的週期性 session teardown／recreate，
但沒有解決活 session 內的 NX→PX4 接收新鮮度。**2 Hz 雙向關卡為 FAIL，20 Hz、
Offboard、解鎖、裝槳與飛行均不得進行。

本輪原始證據位於
[`evidence/20260810_163557_px4_v1143_ping_postflash/`](evidence/20260810_163557_px4_v1143_ping_postflash/)。

## 2. 測試範圍與安全邊界

- 機體無槳、未解鎖，沒有要求馬達轉動。
- 純接收階段不發布任何 `/fmu/in/*`。
- 輸入階段只發布非控制用途的 `/fmu/in/onboard_computer_status`。
- 沒有發布模式、軌跡、姿態、推力、扭矩或 actuator setpoint。
- 沒有修改 PX4 參數，沒有切換飛行模式，也沒有執行 Offboard。
- 當 2 Hz 即時新鮮度失敗後，依停止規則取消 20 Hz 與 Offboard 測試。

## 3. 實際韌體、參數與傳輸基線

QGC `ver all` 與 repository 成品交叉確認：

```text
PX4 version: 1.14.3
source: f9bc66c6f30d8ddcceaeba2545dc9f6d0e71faf1
branch: p450-v1.14.3-xrce-fix
target: Pixhawk 6C / PX4FMUv6C
artifact: firmware/p450-pixhawk6c-v1.14.3-xrce-ping-fix-f9bc66c6f3.px4
SHA-256: cb14d73274014385e809645dd3525e1ce0e33cf5d648c7d23324c41b822bf0bd
```

實機參數與 NX 端設定：

```text
SYS_AUTOSTART=4001
UXRCE_DDS_CFG=102             # TELEM2
SER_TEL2_BAUD=460800
MAV_1_CONFIG=0
Agent=Micro XRCE-DDS Agent v2.4.2
service=p450-micro-xrce-agent.service
transport=/dev/ttyTHS1, 460800 baud
physical path=Pixhawk TELEM2 -> AllSpark UART0 -> /dev/ttyTHS1
```

此 v1.14.3 build 查不到 `UXRCE_DDS_PRT` 與 `UXRCE_DDS_SYNCT`，不能沿用 v1.15.4
文件假設這兩個參數存在。

飛控刷寫後 Agent 本身沒有重啟，ROS CLI discovery cache 曾保留舊 v1.15 entities，
導致一開始看到錯誤 topic／publisher 數。正式測試前已刻意重啟 Agent 一次並清除 ROS 2
daemon cache，得到乾淨的 v1.14 graph：13 個 `/fmu/in/*`、10 個 `/fmu/out/*`，且
`/fmu/out/sensor_combined` 只有一個 publisher。此動作發生在驗收計時開始前，不計為
continuity failure。

## 4. 測試流程與結果

### 4.1 正式 10 分鐘 PX4→NX 純接收

```text
elapsed_s=600.005
messages=42718
average_hz=71.196
median_gap_ms=12.841
max_gap_ms=38.913
gaps_over_100ms=0
gaps_over_500ms=0
gaps_over_1s=0
result=PASS
```

整個區間內 Agent PID 為 9922，`NRestarts=0`、`ExecMainStatus=0`，service journal 沒有
lifecycle 或 error 訊息。這重現了 v1.14.3 ping 回補版的穩定 session 行為，也排除了
先前 v1.15.4 診斷韌體約 1 秒輸出空窗的現象。

### 4.2 2 Hz 非控制輸入時的 PX4→NX continuity

NX 以 2 Hz 發布 `/fmu/in/onboard_computer_status`，同時監測
`/fmu/out/sensor_combined` 60 秒：

```text
elapsed_s=60.002
messages=4273
average_hz=71.214
max_gap_ms=37.397
gaps_over_100ms=0
result=PASS
```

這只能證明 2 Hz 輸入沒有拖垮 PX4→NX 輸出，**不能**證明 PX4 持續收到輸入。第一次與
第二次 QGC `listener onboard_computer_status 1` 均顯示 `never published`。

### 4.3 排除 NX publisher 與 message mismatch

- PX4 source 與 NX `px4_msgs release/1.14` 的 `OnboardComputerStatus.msg` SHA-256
  完全相同：`4a7142a74719b1b56bdbac153e26c91bb3244a0febcac8869203576bae242998`。
- 兩份 message source 沒有 diff。
- NX 本地 unbuffered subscriber 收到三筆 `uptime=271828, type=4` marker。

所以 publisher、NX 本地 DDS 與 message definition mismatch 不是本次失敗原因。

### 4.4 Agent 前景 v5 分層追蹤

送出六筆 `uptime=424242, type=5` marker 後，Agent 記錄到：

- XRCE DataReader 收到 6/6 筆，每筆 240 bytes。
- Agent serial write call 出現 6/6 筆對應資料，每筆 252 bytes。
- 沒有 Agent error、warning 或 session 重建。

這將問題縮小到 Agent write call 之後的路徑：實體 UART、PX4 XRCE frame 接收／排程，
或 deserialization-to-uORB。追蹤結束後 systemd Agent 自動恢復為 PID 12167，乾淨
13-in／10-out graph 與 10 秒純接收複驗均通過。

### 4.5 Live 2 Hz marker：關鍵判別結果

最後在 NX 連續發布 `uptime=515151, type=6`、2 Hz 的有效期間，由 QGC 同時讀取飛控：

```text
uxrce_dds_client: Running, connected
transport: serial
Payload tx: 34551 B/s
Payload rx: 0 B/s              # 當次瞬時狀態
uORB marker: uptime=515151, type=6
uORB sample age: 58.383400 s
```

PX4 uORB 出現完全相同的 marker，證明以下路徑至少曾成功一次：NX publisher → DDS →
Agent → UART → PX4 XRCE deserialization → uORB。因此不能再把問題描述為 TX 線完全斷路、
message 定義錯誤或永遠無法反序列化。

真正失敗點是：NX 仍在 2 Hz 持續發布時，飛控最新樣本已過期 58.383400 秒。瞬時
`Payload rx=0 B/s` 單獨不能證明 callback 永遠未執行，但搭配過期 marker 已足以證明
飛控沒有持續即時消費 2 Hz stream。

## 5. 分層排除結果

| 層級 | 結果 | 證據界線 |
|---|---|---|
| PX4→NX session 與輸出 continuity | PASS | 10 分鐘最大 gap 38.913 ms，Agent 無重啟 |
| NX publisher／本地 DDS | PASS | 本地 subscriber 收到所有 marker |
| PX4／NX message definitions | PASS | SHA 相同、source 無 diff |
| Agent DataReader | PASS | 6/6 marker 被 Agent 收到 |
| Agent serial write call | PASS | 6/6 對應 write，無 error；不等同電氣層量測 |
| 實體方向是否完全斷路 | 排除 | PX4 uORB 曾收到正確 live marker |
| PX4 2 Hz 持續接收新鮮度 | **FAIL** | active publication 時樣本落後 58.383400 秒 |
| 20 Hz／Offboard | 未測且禁止 | 2 Hz gate 已失敗 |

## 6. 根因解讀

目前最符合全部證據的解釋仍是 **PX4 `uxrce_dds_client` 在活 session 內沒有及時處理
NX→PX4 輸入**。舊故障與新故障不可混為一談：

- ping 回補前：session 週期性被刪除並重建，PX4→NX 會有秒級 gap。
- ping 回補後：session 與 PX4→NX output 穩定，但 NX→PX4 input 仍可能長時間停滯。

這也解釋了為何「ROS topics 看得到」仍不足以放行 Offboard：可見的 output graph 與
穩定 telemetry 不代表 input heartbeat 新鮮。

## 7. 本輪停止點與下一步

本輪結束時：

- live 2 Hz publisher 已停止，該 topic 的 NX publisher count 已回到 0。
- systemd Agent 正常運作，PID 12167，沒有 restart。
- 沒有任何 `/fmu/in/*` 測試 publisher 留在背景。
- 未刷下一版韌體，未執行 20 Hz 或 Offboard。

下一個單一變因 A/B 候選為：

```text
firmware/p450-pixhawk6c-v1.14.3-xrce-rx-drain-ping-fix-49049d8555.px4
source: 49049d855552c39879234bf4f19229baf0939a48
git_identity: v1.14.3-2-g49049d8555
SHA-256: ba1a57ad2b48fba9908d7caf34ad5f32d7aea8c0d7bdbe74016b2862aad8e1b5
```

2026-08-11 刷寫前發現舊封裝 metadata 仍顯示 ping-only hash，已由相同
`49049d8555` source 重新連結／封裝並以上述新 SHA 取代；功能變因不變，但刷後可由
QGC `ver all` 明確識別。舊 SHA `d371a5e7…a0a8bdd` 已淘汰。

這個候選版**尚未取得新的刷寫授權**。下次只有在機主明確同意後，才能先備份／核對
目前韌體與參數、刷入候選版，再依相同順序重做乾淨 graph、純接收 continuity 與 live
2 Hz freshness A/B。只有 2 Hz 新鮮度通過後，才可討論 20 Hz；Offboard 仍需另行安全
授權與獨立關卡。

## 8. 原始證據索引

- [`SUMMARY.md`](evidence/20260810_163557_px4_v1143_ping_postflash/SUMMARY.md)：本輪英文摘要。
- [`nx_postflash_graph.txt`](evidence/20260810_163557_px4_v1143_ping_postflash/nx_postflash_graph.txt)：韌體後 graph 與 Agent 基線。
- [`ros2_readonly_continuity_600s.txt`](evidence/20260810_163557_px4_v1143_ping_postflash/ros2_readonly_continuity_600s.txt)：正式 10 分鐘數值。
- [`px4_qgc_postflash.txt`](evidence/20260810_163557_px4_v1143_ping_postflash/px4_qgc_postflash.txt)：QGC 韌體、參數與狀態。
- [`ros2_noncontrol_2hz_60s.txt`](evidence/20260810_163557_px4_v1143_ping_postflash/ros2_noncontrol_2hz_60s.txt)：2 Hz 時的 output continuity。
- [`ros2_noncontrol_local_echo_check.txt`](evidence/20260810_163557_px4_v1143_ping_postflash/ros2_noncontrol_local_echo_check.txt)：本地 marker echo。
- [`agent_verbose_2hz_trace.txt`](evidence/20260810_163557_px4_v1143_ping_postflash/agent_verbose_2hz_trace.txt)：Agent DataReader／serial write 追蹤。
- [`px4_qgc_live_2hz_result.txt`](evidence/20260810_163557_px4_v1143_ping_postflash/px4_qgc_live_2hz_result.txt)：live marker 與 58.383400 秒樣本年齡。
- [`ros2_live_2hz_window.txt`](evidence/20260810_163557_px4_v1143_ping_postflash/ros2_live_2hz_window.txt)：live publisher 執行窗口與停止紀錄。
