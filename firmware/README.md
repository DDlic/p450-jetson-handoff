# P450 Pixhawk 6C 測試韌體

> **2026-08-13 最新實測**：`50c989f85b` rate-limit 版已刷入並完成 Best-Effort A 組；
> NX 發 601 筆、PX4 收 586 筆，最大 receipt gap 307.002 ms，因此 receipt gate FAIL。
> `e6f3d83ff5` 只把 Offboard heartbeat 改為 Reliable；刷入後相同 B 組為 NX 601 筆、
> PX4 601 筆、最大 gap 207.733 ms、`>250/500 ms=0/0`，disarmed transport gate PASS。
> 它仍不是已驗證飛行韌體；無槳 Offboard 與長時間測試完成前禁止裝槳或飛行。

## PX4 v1.14.3 Reliable Offboard heartbeat A/B 版

檔案：

```text
p450-pixhawk6c-v1.14.3-xrce-reliable-offboard-e6f3d83ff5.px4
```

建置與封裝驗證：

- 目標板：Pixhawk 6C／`PX4FMUv6C`
- 基底：rate-limit＋receipt diagnostics `50c989f85b`
- source branch：`p450-v1.14.3-xrce-reliable-offboard`
- source commit：`e6f3d83ff5004c2fd634f12b3c4bfb2983a1c157`
- source patch：`../patches/0002-uxrce_dds_client-make-offboard-heartbeat-reliable.patch`
- compiler：GNU Arm Embedded 9-2020-q2-update／GCC 9.3.1
- clean build：`1114/1114` 成功
- firmware `git_identity`：`v1.14.3-6-ge6f3d83ff5`
- `board_id`：56，`board_revision`：0
- container size：1,805,698 bytes
- image size：1,934,700／1,966,080 bytes（FLASH 98.40%）
- container SHA-256：`da2c86fc51b89c3b8851e2a002d6debb2befc21ee586011abceee3754ac8d948`
- image SHA-256：`c5cc0920257117ba19e2b54978f0cb21518bc0bf8e420bf9970ca80231b71adb`

唯一傳輸行為變因是 `/fmu/in/offboard_control_mode` 同時使用 Reliable DDS DataReader
QoS 與 Reliable XRCE input stream；其他 12 個 input subscriptions 仍是 Best-Effort，
輸出限流、115200、commander、failsafe、arming 與 setpoint 均未更動。PX4 status 額外顯示：

```text
Offboard RX stream: reliable
```

2026-08-13 已用 NX probe 的 `--reliability reliable` 完成 10 Hz／60 秒 disarmed B 組：

```text
NX:  publishes 601, max gap 118.426 ms, >150/250/500 ms 0/0/0
PX4: count 601, max gap 207733 us, >150/250/500 ms 5/0/0
PX4: Payload tx 2860 B/s, FIONREAD errors 0, framing state 0
```

601 筆全程 subscription=1、disarmed、非 Offboard、failsafe=0；Agent PID 未變且沒有
disconnect／reset。Reliable 單一變因 transport gate PASS，但還要做長時間 disarmed
測試與無槳 Offboard gate，才能評估是否進入 armed 測試。

## PX4 v1.14.3 115200 rate-limit＋heartbeat receipt 診斷版

檔案：

```text
p450-pixhawk6c-v1.14.3-xrce-ratelimit115200-50c989f85b.px4
```

建置與封裝驗證：

- 目標板：Pixhawk 6C／`PX4FMUv6C`
- PX4 target：`px4_fmu-v6c_default`
- 基底：目前已刷的 minimal 115200 source `0438dbc6fd`
- source branch：`p450-v1.14.3-xrce-rate-limit-diagnostics`
- source commit：`50c989f85bffb6bd080540a2dba88da424f3f065`
- source patch：`../patches/0001-uxrce_dds_client-rate-limit-outputs-and-measure-offb.patch`
- compiler：GNU Arm Embedded 9-2020-q2-update／GCC 9.3.1
- clean build：`1114/1114` 成功
- firmware `git_identity`：`v1.14.3-5-g50c989f85b`
- firmware `git_hash`：`50c989f85bffb6bd080540a2dba88da424f3f065`
- `board_id`：56，`board_revision`：0
- description：`Firmware for the PX4FMUv6C board`
- container size：1,805,698 bytes
- image size：1,934,628／1,966,080 bytes（FLASH 98.40%）
- container SHA-256：`99bbf652581e0a317c8d9ecf59fcd072d19536fed938b7d86dca2077b55c7664`
- image SHA-256：`e9df68a39f7a971dbc266c3116712ef13d6287399c7fe30ab57c10e8a9450e8f`

本版保留 115200、session ping、bounded receive drain 與 UART framing diagnostics，
只增加兩個可證偽變因：

1. PX4→NX publications 使用 `uORB::SubscriptionInterval` 限速；
2. PX4 在成功反序列化 `OffboardControlMode` 時直接記錄 receipt gap。

輸出上限與 serialized payload budget：

| Topic | 上限 | 每筆 | 每秒上限 |
|---|---:|---:|---:|
| `vehicle_local_position` | 10 Hz | 184 B | 1840 B/s |
| `vehicle_global_position` | 5 Hz | 62 B | 310 B/s |
| `vehicle_gps_position` | 5 Hz | 141 B | 705 B/s |
| `vehicle_status` | 5 Hz | 71 B | 355 B/s |
| `vehicle_control_mode` | 5 Hz | 21 B | 105 B/s |
| `failsafe_flags` | 5 Hz | 85 B | 425 B/s |
| 合計 |  |  | **3740 B/s** |

115200 8N1 每方向的理論 wire capacity 是 11,520 B/s。3740 B/s 是 32.5%；即使加入
XRCE/HDLC header、CRC、byte stuffing 與 burst，也應有充足餘裕。舊版的
`position_setpoint_triplet` 與 `timesync_status` output 已移除；所有 `/fmu/in/*`
subscription 均保留。

PX4 console 的 `uxrce_dds_client status` 會新增：

```text
Offboard RX: count N, max gap X us, >150/250/500 ms A/B/C
Offboard RX last age: Y us
```

詳細第一性原理、刷後測試與真假設判定見
`../evidence/20260813_first_principles_offboard_transport/SUMMARY.md`。

## PX4 v1.14.3 UART RX 診斷版

檔案：

```text
p450-pixhawk6c-v1.14.3-xrce-rxdiag-f6beb984ca.px4
```

建置與封裝驗證：

- 目標板：Pixhawk 6C／`PX4FMUv6C`
- 基底：已測試的 receive-drain＋session-ping source `49049d8555`
- 診斷 source：`f6beb984ca0b8805735475cc57cf1db278d53a67`
- firmware `git_identity`：`v1.14.3-3-gf6beb984ca`
- firmware `git_hash`：`f6beb984ca0b8805735475cc57cf1db278d53a67`
- `board_id`：56
- image size：1,938,252／1,966,080 bytes（FLASH 98.58%）
- 檔案大小：1,808,998 bytes
- SHA-256：`419565d7ad6239272e0854c7b9da2a20a8133d6306f1b554475bfaa0f141b875`
- source patch：`../patches/px4-v1.14.3-uxrce-rxdiag.patch`

這不是新的飛行修正，而是為 2026-08-12 有效 2 Hz FAIL 建立的最小診斷版。它不改
DDS topics、控制器、參數、飛行模式、failsafe、輸出頻率或 receive-drain 行為；只在
`uxrce_dds_client status` 增加以下唯讀資訊：

- NuttX UART RX queue 出現 pending bytes 的樣本次數。
- 抽樣觀察到的 pending bytes 累計與最大值。
- `FIONREAD` 錯誤次數。
- 完整 XRCE payload 累計 bytes。
- serial framing state、ring-buffer bytes 與 message progress。

若 2 Hz 發布期間 raw pending counters 始終為 0，問題在 PX4 XRCE parser 之前，優先查
實體 RX、level shifter、UART driver／DMA。若 raw counters 增加但完整 payload 仍為 0，
則優先查 serial framing、CRC、地址或 XRCE protocol parsing。此韌體尚未刷入；必須先
取得機主明確確認，刷後只執行未解鎖的 2 Hz 非控制 marker 與 status 查詢。

## PX4 v1.15.4 XRCE 完整 transport 排空候選版

檔案：

```text
p450-pixhawk6c-v1.15.4-xrce-full-drain-3f118ef593.px4
```

建置與封裝驗證：

- 目標板：Pixhawk 6C／`PX4FMUv6C`
- PX4 target：`px4_fmu-v6c_default`
- 基底：官方 tag `v1.15.4`／`99c40407ffd7ac184e2d7b4b293f36f10fe561ef`
- 修補後 source：`3f118ef593a45b9ac42ba7ac4cc6565c568ca5f1`
- 上游依據：PX4 `3169dc6b1b17d138d1e04228e400814ed79d0e63`
- 自製 patch：`../patches/px4-v1.15.4-uxrce-full-drain-backport.patch`
- recursive submodules：無偏移
- 編譯器：GNU Arm Embedded 9-2020-q2-update／GCC 9.3.1
- clean build：`1233/1233` 成功
- firmware `board_id`：56
- firmware `description`：`Firmware for the PX4FMUv6C board`
- firmware `git_identity`：`v1.15.4-1-g3f118ef593`
- image size：1,961,772／1,966,080 bytes（FLASH 99.78%）
- SHA-256：`cb54e73327c95f2ceb0dbd9d53c5020b9d8c76cf1c045600e6c66106576dd660`

這是第一代 `996b1df7a1` 候選版失敗後的第二代診斷韌體。它以官方 v1.15.4 為
單一基底，回移植新版 client 中與 serial 共用的低延遲 poll、`FIONREAD` bounded
burst draining、best-effort buffer flush/retry 與 transport fd close ownership。
沒有帶入 UDP 專用 non-blocking socket，也沒有修改 commander、控制器、failsafe、
參數預設值或 DDS message definitions。

2026-08-05 只完成 source、clean build、metadata、FLASH、SHA 與 submodule 驗證；
尚未刷入、尚未實機 A/B，因此不得稱為已修復或飛行韌體。刷入後必須先通過 60 秒與
10 分鐘純接收 continuity，再依 2 Hz／20 Hz 非控制輸入順序測試。

## PX4 v1.15.4 XRCE 接收排空候選版

檔案：

```text
p450-pixhawk6c-v1.15.4-xrce-rx-drain-996b1df7a1.px4
```

建置與封裝驗證：

- 目標板：Pixhawk 6C／`PX4FMUv6C`
- PX4 target：`px4_fmu-v6c_default`
- 基底：官方 tag `v1.15.4`
- 基底 commit：`99c40407ffd7ac184e2d7b4b293f36f10fe561ef`
- 修補後 source commit：`996b1df7a10a35b3e3534df9c5629f3675c7cab0`
- 上游修補來源：PX4 `d12a7dd11da521ebbdd6ba07be1987b459d39ace`
- 自製 patch：`../patches/px4-v1.15.4-uxrce-rx-drain-backport.patch`
- `.px4` 檔案大小：1,849,474 bytes
- 韌體 image size：1,961,732 bytes
- FLASH：1,961,732／1,966,080 bytes（99.78%）
- firmware `board_id`：56
- firmware `description`：`Firmware for the PX4FMUv6C board`
- firmware `git_identity`：`v1.15.4-1-g996b1df7a1`
- SHA-256：`dbfd43085bbb4fe59744ad244a973b1243fb55d34ed36df52c9a0855be464949`

此候選版只把每個 XRCE client loop 的輸入處理由一次改為最多 10 次，收到的 payload
排空後立即停止；沒有修改 commander、飛行控制、解鎖、failsafe、DDS message definitions
或參數預設值。修補行為來自 PX4 官方提交
[`d12a7dd11da5`](https://github.com/PX4/PX4-Autopilot/commit/d12a7dd11da521ebbdd6ba07be1987b459d39ace)，
其提交說明指出每輪只處理一次會造成接收資料顯著延遲，甚至讓已註冊飛行模式 timeout。

建立此版前的 stock v1.15.4 實機結果：純接收、多 topic 與
`UXRCE_DDS_SYNCT=0` 測試都反覆出現約 1 秒同步空窗；2 Hz
`OnboardComputerStatus` 已由 Agent 確認送入 UART，但空窗不變；提高至 20 Hz 後
PX4→NX 輸出完全停止，需重啟 Agent 才恢復。這些結果符合飛控端 XRCE 輸入未及時
排空的症狀。2026-08-05 候選版已刷入，但保留 `UXRCE_DDS_SYNCT=0` 的 60 秒純接收
仍有 1005.408 ms 最大 gap、22 次超過 500 ms、7 次超過 1 秒；第一個 continuity
gate 即 FAIL，因此沒有繼續 2 Hz／20 Hz 輸入，不能視為已修復或用於飛行。

第一次刷入測試先保留 `UXRCE_DDS_SYNCT=0`，保持單一變因，依序測純訂閱、2 Hz
非控制狀態 heartbeat 與 20 Hz 壓力；若通過再將 `UXRCE_DDS_SYNCT` 恢復為預設值
`1`、重啟並重測。時間同步停用不是最終飛行設定。

## PX4 v1.15.4 官方原始碼乾淨編譯版

檔案：

```text
p450-pixhawk6c-v1.15.4-stock-99c40407ff.px4
```

建置與封裝驗證：

- 目標板：Pixhawk 6C／`PX4FMUv6C`
- PX4 target：`px4_fmu-v6c_default`
- 官方 tag：`v1.15.4`
- source commit：`99c40407ffd7ac184e2d7b4b293f36f10fe561ef`
- 自製 patch：無
- recursive submodules：全部位於 v1.15.4 鎖定 commit，無偏移
- 編譯器：GNU Arm Embedded Toolchain 9-2020-q2-update／GCC 9.3.1
- `.px4` 檔案大小：1,849,448 bytes
- 韌體 image size：1,961,652 bytes
- FLASH：1,961,652／1,966,080 bytes（99.77%）
- firmware `board_id`：56
- firmware `description`：`Firmware for the PX4FMUv6C board`
- firmware `git_identity`：`v1.15.4`
- SHA-256：`21af0b94edd5de84dde5360874d8e1f66a52e3be07dfbafaaffc03baa580c29a`

2026-08-04 在 NX 的 `P450_DATA` SD 資料碟上由官方 v1.15.4 source 完整執行：

```bash
make px4_fmu-v6c_default
```

建置 `1233/1233` 成功。此版本用來取代持續回補 v1.14.3 XRCE client 的路線；
它不包含 repository 內兩個 v1.14.3 XRCE patch。PX4 v1.15.4 對應的 Jetson ROS 2
message definitions 必須改用 `px4_msgs release/1.15`，不可繼續用 `release/1.14`
進行 ROS→PX4 控制測試。

2026-08-04 已刷入本機飛控並完成參數恢復。`px4_msgs release/1.15` 的 43 個 DDS
message types 已逐一核對，與韌體 `dds_topics.yaml` 全部一致；NX 可建立 43 個
`/fmu/*` topics，Agent 與 UART session 可連線。但 60 秒純訂閱最大空窗約 1.015 秒，
多個 PX4 outputs 會在相同時間同步跳過約 1 秒。詳細 Agent 測試只有一次
`create_client/session established`，沒有 session close/recreate，因此 stock 版目前
不通過 XRCE continuity 與 Offboard 地面關卡，不可進入自動飛行。

## XRCE 接收排空＋session ping 回補候選版

檔案：

```text
p450-pixhawk6c-v1.14.3-xrce-rx-drain-ping-fix-49049d8555.px4
```

建置資訊：

- 目標板：Pixhawk 6C／`PX4FMUv6C`
- PX4 target：`px4_fmu-v6c_default`
- PX4 基底：v1.14.3
- source commit：`49049d855552c39879234bf4f19229baf0939a48`
- 檔案大小：1,808,290 bytes
- firmware `git_identity`：`v1.14.3-2-g49049d8555`
- firmware `git_hash`：`49049d855552c39879234bf4f19229baf0939a48`
- image size：1,937,764 bytes
- SHA-256：`ba1a57ad2b48fba9908d7caf34ad5f32d7aea8c0d7bdbe74016b2862aad8e1b5`

此候選版保留已驗證的 session ping 回補，另回補 PX4 官方提交
[`d12a7dd11da5`](https://github.com/PX4/PX4-Autopilot/commit/d12a7dd11da521ebbdd6ba07be1987b459d39ace)
的 XRCE 接收排空修正。官方提交說明指出，每個 client 主迴圈只處理一次 session
會造成接收資料顯著延遲，甚至使已註冊的飛行模式 timeout；修正後每輪最多處理
10 次，直到沒有新 payload。實際 patch 位於
`../patches/px4-v1.14.3-uxrce-rx-drain-backport.patch`。

2026-08-04 的刷入前診斷已確認 `COM_OF_LOSS_T=1.0 s`，不是 timeout 設得過短；
NX 以 100 Hz 發送時，PX4 uORB 內最新 `offboard_control_mode` 曾落後約 0.724 秒，
與上述官方修補的問題描述一致。此韌體已完整編譯並通過 SHA-256 檢查，但尚待刷入後
驗證。2026-08-10 ping-only 版的 live 2 Hz marker 又在 PX4 uORB 落後
58.383400 秒，使此候選版成為下一個合理的單一變因 A/B；但它**尚未取得新的刷寫
授權**，目前只可列為候選，不可自動刷入或直接裝槳飛行。

2026-08-11 刷寫前覆核發現舊封裝雖已在 source commit 前編譯 receive-drain object，
但 `.px4` 的版本字串仍沿用 ping-only `f9bc66c6f3`，刷後無法由 QGC 唯一辨識。已在
同一 clean source `49049d8555` 上重新增量連結與封裝；FLASH 仍為 1,937,764 bytes，
新檔 metadata 正確顯示 `v1.14.3-2-g49049d8555`。舊 SHA
`d371a5e7ccde6da7832c9dd0dcbce8a078d459b6239d97a79924b0b1aa0a8bdd` 已淘汰，
不得再拿來刷寫或驗證。

## XRCE session ping 回補版

檔案：

```text
p450-pixhawk6c-v1.14.3-xrce-ping-fix-f9bc66c6f3.px4
```

建置資訊：

- 目標板：Pixhawk 6C／`PX4FMUv6C`
- PX4 target：`px4_fmu-v6c_default`
- PX4 基底：v1.14.3
- source commit：`f9bc66c6f30d8ddcceaeba2545dc9f6d0e71faf1`
- 檔案大小：1,808,166 bytes
- SHA-256：`cb14d73274014385e809645dd3525e1ce0e33cf5d648c7d23324c41b822bf0bd`

修補來源為 PX4 官方提交
[`a1cce7e961df`](https://github.com/PX4/PX4-Autopilot/commit/a1cce7e961df) 中與
XRCE session ping 直接相關的最小回補。實際 patch 位於
`../patches/px4-v1.14.3-uxrce-session-ping-backport.patch`。

## 安全狀態

此韌體已通過完整編譯、板型中繼資料與 SHA-256 驗證。2026-08-03 機主完成
參數備份、刷入與參數恢復；10 分鐘 XRCE 純訂閱測試最大 gap 56.263 ms、
0 次超過 100 ms，120 秒詳細 Agent 測試沒有 session close/recreate。

2026-08-10 再次刷入並核對 source 後，正式 10 分鐘純接收最大 gap 38.913 ms、
0 次超過 100 ms，session continuity 再次 PASS；但 2 Hz NX→PX4 active stream 的
最新 uORB marker 落後 58.383400 秒，因此此版本的**雙向新鮮度 FAIL**。20 Hz 與
Offboard 依停止規則未測。完整結果見
`../P450_PX4_V1143_PING_BIDIRECTIONAL_TEST_2026-08-10.md`。

此結果不代表 GPS、preflight、failsafe、Offboard 或飛行安全已通過。

若日後重刷，必須：

1. 保持拆槳、機體固定與穩定供電。
2. 使用 QGroundControl 匯出完整參數備份。
3. 再次確認飛控為 Pixhawk 6C。
4. 刷入後核對 airframe、校正、RC、安全與 failsafe 參數。
5. 先做至少 10 分鐘純訂閱地面測試，不可直接解鎖或進入 Offboard。

2026-08-03 初次結果見 `../P450_POSTFLASH_XRCE_TEST_2026-08-03.md`；2026-08-10
雙向結果見 `../P450_PX4_V1143_PING_BIDIRECTIONAL_TEST_2026-08-10.md`。
