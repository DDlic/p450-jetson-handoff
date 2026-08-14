# P450 QGC 筆電 Codex 專用協作交接（2026-08-14）

## 立即交給筆電 Codex 的啟動文字

機主可把下面整段直接貼給使用 QGC 的筆電 Codex：

```text
你是 P450 專案的 QGC／Pixhawk 端 Codex。先在 p450-jetson-handoff repository
執行 git pull --ff-only，完整閱讀 QGC_LAPTOP_CODEX_HANDOFF_20260814.md，並按其中
「QGC 筆電 Codex 負責」的範圍工作。不要只讀 README 或歷史結論。

目前先做環境與文件確認，不改參數、不刷韌體、不切模式、不解鎖、不發布控制命令。
你的回傳只新增到 evidence/20260814_qgc_px4/，檔名使用
QGC_RETURN_YYYYMMDD_HHMM_TESTNAME.txt，原始 console 輸出不可節錄或改寫。
不要修改 QGC_LAPTOP_CODEX_HANDOFF_20260814.md、雙端交接文件.txt 或 NX 端檔案。
完成後使用 qgc: 前綴 commit 並 push main，再把 commit SHA 告訴機主。
若文件要求等待 NX Codex 的 TEST_ID，就停在 READY_QGC，不要自行開始舊測試。
雙端狀態、TEST_ID 與交棒一律透過 GitHub Issue #1「P450 Codex Coordination」留言，
不再要求機主人工轉貼兩端訊息。
```

筆電 Codex 回覆「已讀」不算完成初始化；至少要回報目前 `HEAD`、已讀文件清單、
QGC/PX4 console 是否可用，以及 `READY_QGC` 或明確阻塞原因。

## 0. 讀者與任務

這份文件提供給連接 QGroundControl/Pixhawk 6C 的筆電 Codex。它不依賴原始聊天紀錄；讀完後應能直接與 NX Codex 分工。

當前共同目標不是立刻飛行，而是先定位 ROS 2 OffboardControlMode 經 Micro XRCE-DDS reliable serial 傳輸時，PX4 偶發 250–500 ms receipt gap 的底層來源。

目前禁止：裝槳飛行、發布 setpoint、發布 VehicleCommand、切入 Offboard、解鎖、改 PX4 參數、刷其他韌體、改接線或做阻抗／logic-analyzer 測試。若機主另有明確指示，再依新的安全條件處理。

### 文件優先級

發生內容衝突時依下列順序判定：

1. 機主在當前對話中的最新明確指示。
2. 本文件。
3. 最新日期的 `evidence/` 測試結果。
4. `README.md` 與其他歷史 handoff。

特別注意：`evidence/20260814_reliable_rx_trace_build/BUILD_AND_TEST_HANDOFF.md`
保留了一段刷入前的歷史命令，其中 `ROS_LOCALHOST_ONLY=1` 已被實機證明不適合目前
systemd Agent discovery。NX 現況一律以本文件的 `ROS_LOCALHOST_ONLY=0` 為準；QGC
筆電端不應代替 NX 執行 ROS probe。

## 1. 當前硬體與軟體真實狀態

- 機主：P450 專案擁有者。
- Companion computer：Jetson Xavier NX，Ubuntu 20.04，ROS 2 Foxy。
- Flight controller：Pixhawk 6C／PX4FMUv6C。
- NX UART：`/dev/ttyTHS1`，115200 8N1，連 Pixhawk TELEM2。
- Agent service：`p450-micro-xrce-agent.service`。
- Agent command：`/usr/local/bin/MicroXRCEAgent serial --dev /dev/ttyTHS1 -b 115200 -v 2`。
- ROS：`ROS_DOMAIN_ID=0`、`RMW_IMPLEMENTATION=rmw_fastrtps_cpp`。
- 必須使用 `ROS_LOCALHOST_ONLY=0`。設成 1 會讓 NX CLI 看不到 systemd Agent 建立的 DDS participant，造成只有 `/rosout` 與 `/parameter_events` 的假象。
- 目前刷入 PX4 診斷韌體：`v1.14.3-8-gc7a3947840`。
- 韌體檔：`firmware/p450-pixhawk6c-v1.14.3-xrce-rxtrace-c7a3947840.px4`。
- 韌體 SHA-256：`8a23631277a1a8a14707e2e999f2e0319597fa733c50bdbd788443f2b3724706`。
- Offboard input stream：reliable。

韌體只增加固定 96 筆 RAM ring trace 與既有 Offboard receipt 統計，不改飛控迴路、arming、failsafe、參數、Agent heartbeat 或 UART 設定。

## 2. 兩個不同問題，不可混為一談

### 2.1 NX kernel panic

NX 曾在 ROS CLI/`timeout` 行程退出時發生：

```text
mem_cgroup_from_obj
list_lru_del
d_lru_del
proc_flush_pid
release_task
Kernel panic - not syncing: Oops: Fatal exception
```

NX 已新增 boot 參數 `cgroup.memory=nokmem`，停用 kernel-object memory-cgroup accounting。受控重啟後：

- cmdline 確認生效；
- kmem counters 維持 0；
- 原觸發序列重跑無 panic；
- uptime 超過原 panic 的 669.85 秒，720 秒檢查 PASS；
- Agent PID 未變、`NRestarts=0`；
- kernel log 無新 Oops/panic。

這只能判定 kernel workaround 第一輪 PASS，不能拿來宣稱 XRCE gap 已修復。原始 panic 與分析位於 `evidence/20260814_nx_kernel_panic/`。

### 2.2 XRCE reliable receipt gap

同一輪 125 秒測試中，NX publisher 與 PX4 receiver 結果明顯不同。

NX 端：

```text
publishes=1251
mean_gap_ms=99.985198
max_gap_ms=120.436
over_150ms=0
over_250ms=0
over_500ms=0
subscription_count=1 for all 1251 rows
arming_state=1 (disarmed) for all rows
nav_state=4 for all rows
nav_state_user_intention=4 for all rows
failsafe=0 for all rows
```

PX4 端：

```text
Offboard RX: count 1251
max gap 506727 us
>150/250/500 ms = 83/23/1
Reliable RX trace: count 24/96
frozen 1
trigger gap 397990 us
```

結論：訊息最終 1251/1251 全到，可靠傳輸消除了最終 loss；但 PX4 實際交付時間仍有 506.727 ms long-tail。NX 發布排程不是這一輪 long-tail 的來源。

## 3. RXTRACE 欄位

PX4 console 指令：

```text
uxrce_dds_client trace reset
uxrce_dds_client status
uxrce_dds_client trace
```

欄位完整順序：

```text
i,event,t_us,stream,seq,
handled_before,handled_after,
announced_before,announced_after,
stored,ready,first_unacked,nack_bitmap,
offboard_count,offboard_gap_us,
offboard_receipt_us,offboard_timestamp
```

- `event=1`：reliable MESSAGE。
- `event=2`：XRCE HEARTBEAT。
- `stored=1, ready=0`：較後 sequence 已收到並放進 reliable buffer，但前方缺洞，所以不能交給上層。
- `ready=1`：該 sequence 現在可依序交付。
- `handled_*`：已連續處理到的 sequence。
- `announced_*`：Client 已知 Agent 發到的 sequence 上界。
- `first_unacked` 與 `nack_bitmap`：Client 要求重傳的洞。

## 4. 本次 trace 已證明的事情

### 4.1 第一個短 sequence hole

```text
seq 48 arrives while handled=46
stored=0 ready=0 first_unacked=47 nack=0x0003
seq 47 arrives
handled 46->47 ready=1 first_unacked=48 nack=0x0001
seq 48 arrives
handled 47->48 ready=1 nack=0
```

稍後又出現：

```text
seq 51 arrives while handled=48
stored=1 ready=0 first_unacked=49 nack=0x0003
seq 49 arrives, then seq 50 arrives
```

這是後方 frame 先到、前方 frame 後補的可靠重排／head-of-line blocking。

### 4.2 觸發 397.990 ms Offboard gap 的 sequence hole

關鍵行：

```text
seq 57: handled 56->57, normal delivery
seq 61: handled stays 57, announced 57->61,
        stored=1, ready=0, first_unacked=58, nack=0x0007
HEARTBEAT last=61: handled stays 57, first_unacked=58, nack=0x0007
seq 58: handled 57->58, ready=1,
        first_unacked=59, nack=0x0003,
        offboard_count 4, offboard_gap_us 397990
```

精確判讀：

1. Client 先看到 seq 61，但 seq 58、59、60 缺失。
2. reliable receive window 將 seq 61 暫存，`last_handled` 卡在 57。
3. HEARTBEAT 確認 Agent 已發到 61，Client 對 58 起送出 NACK bitmap `0x0007`。
4. seq 58 補到後才可交付，並留下 397.990 ms Offboard receipt gap；此時 59、60 仍缺，bitmap 變 `0x0003`。

因此「sequence hole + reliable head-of-line blocking」已由實機證明，不再是假設。

## 5. 尚未證明的邊界

目前 trace 位於 PX4 Client 接收窗，所以只能證明 PX4 看到 sequence hole。尚不能單憑這份資料區分：

1. Agent 的 DDS callback 本來就晚；
2. Agent 已取得 sample，但尚未及時配置／送出 sequence；
3. Agent 已送出，Linux UART write 或 Tegra serial transport 延遲；
4. 線上 frame 遺失／損壞；
5. PX4 UART bytes 已到，但 framing 未形成有效 XRCE message；
6. ACKNACK 已回到 Agent，但 Agent retransmit queue／write 延遲。

下一個高資訊量軟體工作是 Agent 端 sequence trace，以 `(stream_id, seq_num)` 與 PX4 RXTRACE 配對。禁止把 Linux wall clock 直接減 PX4 HRT；兩端必須靠 sequence 配對，再各自在自身 clock domain 算階段延遲。

## 6. 雙 Codex 固定分工

### NX Codex 負責

1. Agent service、UART ownership、ROS graph、NX kernel health。
2. 安全 heartbeat probe 與 NX CSV。
3. Agent 端 trace 設計／編譯／執行與結果解析。
4. 統整兩端 sequence，更新主結論與測試 gate。
5. 只在真的需要刷 PX4 韌體時通知機主；目前不需要再編譯 PX4。

### QGC 筆電 Codex 負責

1. 確認 QGC MAVLink Console 可與 Pixhawk 通訊。
2. 在每輪測試前後擷取完整 PX4 console 原始輸出。
3. 測試前執行 `trace reset`，確認 `count=0,frozen=0`。
4. NX Codex 宣告 probe 完成後，立即執行 `status` 與 `trace`。
5. 將所有 `RXTRACE` 行原樣保存，不省略、不重新排版、不只寫結論。
6. 記錄 firmware `ver all`、測試開始／結束時間、是否有 PX4 reboot、USB/QGC reconnect。
7. 不自行改參數、不切模式、不解鎖、不刷韌體。

### GitHub Issue 是唯一跨端協作通道

- 固定 Issue：<https://github.com/DDlic/p450-jetson-handoff/issues/1>。
- `TEST_ID`、開始／停止條件、狀態 ACK、阻塞原因與 evidence commit SHA 都在該 Issue 留言。
- 正式程式碼、文件、CSV 與完整 raw evidence 仍提交 Git；Issue 不貼超長 raw trace。
- 機主可監督或覆寫任務，但正常流程不再依賴機主人工轉貼兩端訊息。
- 任一端需要另一端動作時，先寫清楚「要執行的命令、開始條件、停止條件、預期輸出」，
  不只寫「請測試」。
- 筆電端不得把尚未由 NX Codex 宣告的測試當成已同步；NX 端也不得把沒有 QGC pre-test
  證據的資料標成雙端測試。
- 使用同一個 `TEST_ID` 才能把 NX CSV、Agent trace 與 QGC/PX4 trace 視為同一輪。

Issue 留言固定格式：

```text
MSG_ID:
FROM: NX Codex | QGC Codex
TO: QGC Codex | NX Codex
TEST_ID:
STATE:
ACTION:
START_CONDITION:
STOP_CONDITION:
EXPECTED_OUTPUT:
REPLY_REQUIRED: YES | NO
```

需要回覆的訊息必須用新的 `MSG_ID` 留言 ACK，不能只靠 reaction。禁止在 Issue 放密碼、
token、登入資訊、parameter backup 或其他敏感資料。

## 7. 每輪協作流程

### Phase 0：建立唯一測試識別

由 NX Codex先建立：

```text
TEST_ID=YYYYMMDD_HHMM_<short-name>
EXPECTED_FIRMWARE=v1.14.3-8-gc7a3947840
PROBE_DURATION_S=<由 NX Codex 指定>
PROBE_RATE_HZ=10
PROBE_RELIABILITY=reliable
```

QGC 筆電 Codex 必須原樣使用此 `TEST_ID`。沒有 TEST_ID、韌體不符或 props/arming 狀態
不明時，只回報阻塞，不執行測試。

### Phase A：測試前，QGC 端

在確認無槳、未解鎖、非 Offboard 後執行：

```text
ver all
uxrce_dds_client status
uxrce_dds_client trace reset
uxrce_dds_client trace
```

必須看到：

```text
Running, connected
Offboard RX stream: reliable
RXTRACE summary,count=0,frozen=0,trigger_gap_us=0
```

若不是，停止並回報，不開始 probe。

### Phase B：NX 端

NX Codex檢查：

- vehicle status 新鮮；
- `arming_state=1`；
- `flag_armed=false`；
- nav state 與 user intention 均不是 Offboard；
- PX4 OffboardControlMode subscription count 至少 1；
- Agent PID 與 NRestarts 基線已記錄。

然後才啟動指定 probe。

### Phase C：測試後，QGC 端

不要先 reset 或 reboot，立即執行：

```text
uxrce_dds_client status
uxrce_dds_client trace
```

完整保存輸出。若 `frozen=1`，不需要延長同一輪測試；ring 已保留第一個 >250 ms 現場。

### Phase D：共同判讀

以 `stream=128` 與 `seq` 配對 Agent/PX4 事件，分類為：

- Agent callback 前已晚；
- Agent callback 正常但 sequence/send 晚；
- Agent 已送但 PX4 首次只看到後方 sequence；
- NACK 已產生但 retransmit 晚；
- sequence 按序但上層 callback 晚。

### Git 非同步交棒狀態

每輪只使用下列狀態，避免「完成」語意不清：

- `READY_QGC`：QGC 已完成 pre-test，trace 為空，等待 NX 開始。
- `RUNNING_NX`：NX 正在執行該 TEST_ID，QGC 不 reset、不 reboot。
- `NX_DONE_WAIT_QGC`：NX probe 已停，QGC 立即抓 post-test status/trace。
- `QGC_EVIDENCE_PUSHED`：QGC 原始證據已 commit/push，附 SHA。
- `ANALYZED`：NX 已拉取並完成雙端配對判讀。
- `ABORTED_<reason>`：安全條件、連線、重啟或版本不符，中止且不可把資料併入正式結果。

## 8. 停止條件與飛行 gate

任一條成立即停止該輪：

- vehicle armed；
- Offboard selected/intended；
- subscription count 變 0；
- Agent PID 改變或 restart；
- PX4 disconnected；
- NX kernel Oops/panic；
- `frozen=1`；
- PX4 `>250 ms > 0`。

目前本輪 PX4 `>250 ms=23`、`>500 ms=1`，所以 transport gate 明確 FAIL。不可因 NX CSV 漂亮、最終 loss=0 或加大 `COM_OF_LOSS_T` 就進入有槳 Offboard 飛行。

即使後續 125 秒 PASS，也只算 preliminary PASS；還需 600 秒同條件、Agent restart、NX reboot、PX4 reboot、正式 telemetry/CPU/network load 與 RC/failsafe 接管測試。

## 9. Git 協作規則

Repo：`https://github.com/DDlic/p450-jetson-handoff.git`，branch `main`。

為避免兩端改同檔衝突：

- NX Codex擁有這份主交接文件、`scripts/`、Agent patch 與 NX evidence。
- QGC 筆電 Codex只新增 `evidence/20260814_qgc_px4/` 下的新檔，不直接改這份主文件。
- 每輪建立獨立檔，例如：
  `evidence/20260814_qgc_px4/QGC_RETURN_YYYYMMDD_HHMM_TESTNAME.txt`。
- QGC commit message 使用 `qgc:` 前綴；NX 使用 `nx:` 或 `evidence:`。
- 寫入前 `git pull --ff-only`；push 前再 fetch，避免覆蓋他端提交。
- 禁止 force-push、reset、覆寫其他 evidence。
- 禁止提交密碼、token、GitHub session、QGC parameter backup 或其他憑證。
- raw evidence 與分析分開：QGC return 檔只放事實與原始輸出，原因判讀由 NX 端另寫。
- push 完成後，QGC Codex 必須在 Issue #1 以 `QGC_EVIDENCE_PUSHED` 回覆 commit SHA；
  NX Codex 拉取並驗證後再回覆 `ANALYZED`。

QGC 回傳檔格式：

```text
TEST_ID:
LOCAL_TIME_ASIA_TAIPEI:
FIRMWARE_VER_ALL:
VEHICLE_PROPS_REMOVED:
VEHICLE_ARMED:
PX4_REBOOT_DURING_TEST:
QGC_USB_OR_LINK_RECONNECT:

PRE_TEST_RAW_OUTPUT:
<ver/status/reset/empty trace 原樣貼上>

POST_TEST_RAW_OUTPUT:
<status 與全部 RXTRACE 原樣貼上>

OPERATOR_NOTES:
<只寫實際發生的操作，不推測原因>
```

## 10. 必读相關文件

1. `evidence/20260814_reliable_rx_trace_build/BUILD_AND_TEST_HANDOFF.md`
2. `evidence/20260814_nx_kernel_panic/README.md`
3. `evidence/20260814_nx_kernel_panic/post_nokmem_heartbeat_10hz_reliable_125s.csv`
4. `雙端交接文件.txt`（本次 QGC 原始 status/RXTRACE）
5. `firmware/README.md`

## 11. 當前下一步

不再重跑相同的 PX4-only 125 秒測試，也不改 heartbeat period。RXTRACE 已證明 Client sequence hole；下一步由 NX Codex建立 Agent 端 sequence/send/ACKNACK/retransmit trace。QGC 筆電 Codex先完成環境確認、讀取上述文件、建立自己的 `evidence/20260814_qgc_px4/` 回傳檔模板，等待 NX Codex通知同步測試開始。

目前筆電端的正確停止點是 `READY_QGC`。尚未收到 NX Codex 發出的新 `TEST_ID` 前，
不要重跑 125 秒 probe，也不要 reset 現有 trace 後自行測試。
