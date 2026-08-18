# P450 Reliable 零最終遺失後的延遲改善與驗證 Runbook

日期：2026-08-17（Asia/Taipei）

## 0. 結論與目前禁止事項

目前證據支持以下精確結論：

- 2026-08-13 的 Reliable 版本在已完成場次中消除了最終遺失：60 秒為
  `601/601`，600 秒為 `6001/6001`。
- Reliable 尚未解決新鮮度：600 秒 PX4 receipt 最大 gap 為 `601.548 ms`，
  `>250/500 ms=16/2`。
- 2026-08-14 把 Agent heartbeat period 從 200 ms 降至 50 ms，乾淨 120 秒場仍有
  `298.884 ms` 最大 gap 與 4 次 `>250 ms`，所以「只縮短 heartbeat period」已被否證。
- PX4 RX trace 已直接證明後方 `seq 61` 先到、`seq 58–60` 缺失，Reliable receive
  window 因循序交付等待補洞，造成 `397.990 ms` head-of-line stall。
- 尚未證明缺洞發生在 Agent 排程、Linux UART write、Tegra UART、線路／framing，或
  PX4 收件處理中的哪一段。
- NX 已兩次發生同 family 的 `key_garbage_collector -> key_put()` kernel panic；在
  kernel gate 恢復前，不得 stop/start Agent、執行 Agent trace A/B、裝槳或飛行。

時間軸不可倒置：2026-08-12 `247cc6b` 才是 Best-Effort ground probe／Python 地面測試；
2026-08-13 `e16e7f3` 才加入 Reliable PX4 reader／XRCE stream，且同一提交已讓 heartbeat
probe 可明確選 `--reliability reliable`。因此 8 月 12 日腳本結果不能拿來評價隔日
Reliable 版本；本 runbook 的 Reliable 結論只使用 8 月 13 日以後的成對場次。

| 場次 | NX/PX4 | NX max gap | PX4 max gap | PX4 `>250/500 ms` | 判定 |
| --- | ---: | ---: | ---: | ---: | --- |
| Best Effort 60 s | 601/586 | 119.813 ms | 307.002 ms | 4/0 | 最終遺失，FAIL |
| Reliable 60 s | 601/601 | 118.426 ms | 207.733 ms | 0/0 | 短測 PASS |
| Reliable 600 s | 6001/6001 | 159.999 ms | 601.548 ms | 16/2 | freshness FAIL |
| Reliable／Agent 50 ms／120 s | 1201/1201 | 119.042 ms | 298.884 ms | 4/0 | heartbeat 單因假設 FAIL |

因此，推薦路徑不是再猜一個 QoS 參數，而是依序完成：

```text
NX kernel 穩定性
  -> Agent 序號／UART write／ACKNACK／重傳定位
  -> 對已定位的階段修復或更換 transport
  -> 同條件 120 s / 600 s / soak A/B
  -> 最後才選 Reliable、Best-Effort 或額外 freshness policy
```

本文件內的 stop/start、module unload、transport 改接與參數修改命令都是後續維護窗口的
runbook，**不是目前立刻執行的命令**。每一階段只有在前一階段 PASS 後才能開始。

## 1. 官方文檔能解決什麼、不能解決什麼

ROS 2 QoS 把 Reliability、Deadline、Lifespan、History/Depth 視為不同政策：Reliable
允許重試；Deadline 描述預期間隔並產生 missed-deadline event；Lifespan 讓過期樣本失效；
Keep Last depth 只限制 DDS history。這些政策不能互相替代。ROS 2 的 sensor-data profile
選 Best Effort，是因為某些即時資料重視最新樣本多於每筆必達。

PX4 v1.14 文檔確認 uXRCE-DDS 可使用 serial 或 UDP；PX4 預設 input subscriber 是
Best Effort／Volatile，但 P450 的 `e6f3d83ff5` 與後續診斷韌體已把
`OffboardControlMode` 單一 reader／XRCE input stream 改成 Reliable。ROS publisher 必須
使用相容 QoS 才會匹配。

eProsima 文檔確認 Reliable stream 使用 delivery confirmation 與 history 保存尚未確認、
亂序或不完整的資料；Agent build-time 參數包含 reliable stream depth 與 heartbeat
period。這解釋了為什麼 Reliable 可以補回資料，也解釋了為什麼缺洞會造成等待。

因此各候選項目的工程判定如下：

| 候選 | 文檔功能 | P450 判定 |
| --- | --- | --- |
| `UAGENT_CONFIG_HEARTBEAT_PERIOD` | 週期性宣告 Reliable stream 狀態 | 200→50 ms 已 FAIL，不再單獨下調 |
| `UAGENT_CONFIG_RELIABLE_STREAM_DEPTH` | 保存未確認的 Reliable 歷史 | 只有 trace 證明 history/window 壓力後才 A/B；不會直接消除循序阻塞 |
| ROS `deadline` | 偵測樣本間隔違約 | 監控手段，不是降低 transport latency 的手段 |
| ROS `lifespan` | 使過期 DDS sample 失效 | 可作 stale-data 保護；未證明可繞過 XRCE sequence hole |
| ROS Keep Last depth | 限制 DDS queue | 只有 Agent callback 前已有 backlog 時才有意義 |
| Best Effort | 不等待重傳，允許遺失 | 原 10 Hz 場 `586/601` 且最大 307.002 ms；不可直接退回 |
| UDP／另一條 serial path | 隔離 UART/framing/driver | 官方支援，且是定位 transport 根因的高資訊量 A/B |
| 放寬 `COM_OF_LOSS_T` | 延後 PX4 failsafe | 只掩蓋 tail latency，不是修復；目前不得採用 |

官方來源：

- [ROS 2 QoS settings](https://docs.ros.org/en/foxy/Concepts/About-Quality-of-Service-Settings.html)
- [ROS2 Taiwan：QoS](https://ros2.tw/ros2/qos/)
- [PX4 v1.14 uXRCE-DDS](https://docs.px4.io/v1.14/en/middleware/uxrce_dds)
- [PX4 v1.14 Offboard mode](https://docs.px4.io/v1.14/en/flight_modes/offboard)
- [eProsima Micro XRCE-DDS documentation](https://micro-xrce-dds.docs.eprosima.com/en/v2.4.1/)

專案原始證據：

- [`TEN_MINUTE_RELIABLE_RESULT.md`](../../evidence/20260813_first_principles_offboard_transport/TEN_MINUTE_RELIABLE_RESULT.md)
- [`AGENT_50MS_AB_RESULT.md`](../../evidence/20260813_first_principles_offboard_transport/AGENT_50MS_AB_RESULT.md)
- [`QGC_LAPTOP_CODEX_HANDOFF_20260814.md`](../current/QGC_LAPTOP_CODEX_HANDOFF_20260814.md)
- [`Agent sequence trace build/selftest`](../../evidence/20260814_agent_sequence_trace/README.md)
- [`Repeated key-GC kernel panic`](../../evidence/20260817_nx_kernel_panic_key_gc_repeat/README.md)

`250 ms` 是本專案的飛行前 transport gate，不是 PX4 官方認證值。PX4 官方要求
Offboard proof-of-life 持續高於 2 Hz，並以 `COM_OF_LOSS_T` 處理訊號遺失；P450 維持
10 Hz，使用 250 ms gate 是為 1.0 秒 failsafe 保留工程餘裕。

## 2. 統一量測模型與驗收條件

### 2.1 量測點

每一輪都必須同時量到：

```text
P(n): NX Python 呼叫 publish 的 monotonic timestamp
A0(n): Agent DDS callback begin/end
A1(n): Reliable sequence assigned / queue
A2(n): Agent send begin/end
A3(n): Linux UART write begin/end
A4(n): ACKNACK received / retransmit queued / retransmit write
R(n): PX4 成功依序交付並 deserialize OffboardControlMode 的 HRT timestamp
```

Linux `CLOCK_MONOTONIC_RAW` 和 PX4 HRT 不可直接相減。跨端只用
`(session generation, stream_id, seq_num)` 配對；階段延遲分別在各自 clock domain 計算。

### 2.2 固定條件

- 無槳、機體固定、disarmed、非 Offboard、failsafe 0。
- 只發布 `OffboardControlMode`；不發布 setpoint、`VehicleCommand`，不切模式、不解鎖。
- 10 Hz、Reliable、ROS domain 0、`ROS_LOCALHOST_ONLY=0`。
- PX4 診斷韌體 `v1.14.3-8-gc7a3947840`，除非該階段明確要求切換單一變因。
- Serial baseline：TELEM2 ↔ `/dev/ttyTHS1`、115200、8N1、無 flow control。
- Agent baseline：Micro XRCE-DDS Agent 2.4.2、heartbeat 200 ms、reliable depth 16。
- PX4→NX output 保持目前 rate-limited 約 2.9 KB/s，避免重新引入頻寬飽和變因。

### 2.3 每輪最小 PASS

Reliable 場次必須同時滿足：

- NX publisher：`max_gap <150 ms`，`>150/250/500 ms=0/0/0`。
- PX4：receipt count 等於 NX publish count，最終遺失 0。
- PX4：`max gap <250000 us`，`>250/500 ms=0/0`。
- Agent PID／session 不重建，`NRestarts=0`。
- PX4 無 framing stuck、FIONREAD error、client reconnect 或 reboot。
- 測試期間 NX 無新 Oops、panic、hung task、I/O error 或 thermal shutdown。

120 秒的 0 次違規只算 preliminary PASS；正式判定至少需要 600 秒。解除無槳地面 gate 前，
再做三輪相互獨立的 600 秒測試；解除有槳 gate 前另做一次 3600 秒 soak。這些長度是 P450
工程 gate，不是 ROS/PX4 官方保證。

## 3. Phase 0：建立測試身分與唯讀 baseline

### 3.1 建立唯一 TEST_ID

```bash
date '+P450_%Y%m%d_%H%M_RELIABLE_LATENCY_PHASE0'
```

在 GitHub Issue #1 宣告 TEST_ID。NX CSV、Agent trace、QGC console、PX4 RXTRACE、kernel
log 與最後結論都必須帶同一個 TEST_ID，禁止把不同 session 的資料拼成一場。

### 3.2 現在允許的唯讀檢查

```bash
date --iso-8601=seconds
uname -a
uptime
systemctl is-active p450-micro-xrce-agent.service
systemctl show p450-micro-xrce-agent.service -p MainPID -p NRestarts -p ExecMainStartTimestamp
sudo fuser -v /dev/ttyTHS1
lsmod | rg '^88x2bu\b'
journalctl -k -b --no-pager | rg -i 'panic|oops|key_garbage|hung task|thermal|ttyTHS1|tegra_uart'
```

ROS 環境固定為：

```bash
source /opt/ros/foxy/setup.bash
source /home/p450/p450_ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=0
export ROS_LOCALHOST_ONLY=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
ros2 topic info -v /fmu/in/offboard_control_mode
```

只允許做不發布資料的 probe preflight：

```bash
python3 /home/p450/p450-jetson-handoff/scripts/p450_offboard_heartbeat_probe.py \
  --duration 1 --rate 10 --reliability reliable --preflight-only \
  --csv /tmp/p450-heartbeat-preflight.csv
```

PASS：`HEARTBEAT_PREFLIGHT_ONLY no_messages_published=true`、disarmed、非 Offboard、唯一
匹配的 Reliable subscription。若 graph 不符，只記錄；目前不得靠 stop/start Agent 修 graph。

## 4. Phase 1：先恢復 NX kernel gate

### 4.1 維護前提

這一階段必須由機主在 NX 實體 console 或可靠的有線 SSH 執行，且：

- 無槳、Pixhawk disarmed、非 Offboard；
- 先把 evidence 與工作樹同步到 SD／Git；
- 有線網路已實際連通，預設路由不依賴 `wlan1`；
- 可接受 NX 重啟，且已知道如何讀取 `/sys/fs/pstore`；
- 不在遠端唯一連線仍走 `88x2bu` 時 unload 該 module。

先證明有線路徑：

```bash
ip -br link
ip route
nmcli -f DEVICE,TYPE,STATE,CONNECTION device status
```

### 4.2 `88x2bu` runtime A/B

兩次同 family panic 都載入 out-of-tree `88x2bu(OE)`，但 call stack 沒進入該 module；
所以它只是候選，不是已知根因。先做可回復的 runtime A/B，不先永久修改 blacklist：

```bash
lsmod | rg '^88x2bu\b'
sudo modprobe -r 88x2bu
lsmod | rg '^88x2bu\b' || true
```

若 unload 失敗、網路中斷或出現新 kernel warning，立即停止，不要反覆嘗試。module 不載入
後先維持原 Agent 不動做至少 2 小時 software-only soak，期間只收集 kernel／service 狀態。

### 4.3 受控 Agent lifecycle gate

只有 2 小時 soak 無新 Oops/panic，且操作者就在機旁時，才做一次受控 lifecycle：

```bash
sudo systemctl stop p450-micro-xrce-agent.service
systemctl is-active p450-micro-xrce-agent.service
sudo systemctl start p450-micro-xrce-agent.service
systemctl show p450-micro-xrce-agent.service -p ActiveState -p MainPID -p NRestarts
journalctl -k -b --since '-10 min' --no-pager | rg -i 'panic|oops|key_garbage|hung task' || true
```

若 NX 掛死或重開：不要重跑；重開後立刻保存 `/sys/fs/pstore/*`，Phase 1 FAIL。若
`88x2bu` 未載入時仍重現同 trace，停止 XRCE 測試主線，轉入 vendor kernel／module
memory-corruption 根因工作。

Phase 1 PASS 需要：module 未載入、一次 stop/start 成功、其後至少 8 小時 soak 無新
Oops/panic，Agent `active`、`NRestarts=0`。這只能解除「可做 Agent trace」的 gate，不能
直接解除飛行 gate。

## 5. Phase 2：完成正式 Agent sequence trace

### 5.1 切換前核對

只有 Phase 1 PASS 才執行。先找出隔離 binary，人工確認只有一個結果並核對既有 SHA-256：

```bash
find /home/p450/builds/microxrce-agent-2.4.2-agenttrace/build \
  -type f -name MicroXRCEAgent -perm -111 -print
sha256sum /實際找到的完整路徑/MicroXRCEAgent
```

預期 binary SHA-256：

```text
0cfabea315262147898fb925308b479726542bd64653fa217c789fddb8e5d3f5
```

QGC 端先執行：

```text
ver all
uxrce_dds_client status
uxrce_dds_client trace reset
uxrce_dds_client trace
```

必須是指定診斷韌體、connected、Reliable、`trace count=0`、disarmed、非 Offboard。

### 5.2 切換與正式 125 秒場

在 NX 終端 A 設定明確路徑；禁止用模糊 glob 啟動 binary：

```bash
P450_TRACE_AGENT=/實際核對過的完整路徑/MicroXRCEAgent
P450_TRACE_FILE=/dev/shm/p450_agenttrace_TEST_ID.bin
test -x "$P450_TRACE_AGENT"
sudo systemctl stop p450-micro-xrce-agent.service
sudo stty -F /dev/ttyTHS1 115200 raw -echo cs8 -parenb -cstopb -crtscts
sudo -u p450 env ROS_DOMAIN_ID=0 \
  P450_XRCE_TRACE_FILE="$P450_TRACE_FILE" \
  P450_XRCE_TRACE_STREAM=128 \
  "$P450_TRACE_AGENT" serial --dev /dev/ttyTHS1 -b 115200 -v 2
```

Agent 留在前景。QGC 看到 client reconnect 後再次回覆同一 TEST_ID 的
`READY_QGC_FINAL`。NX 終端 B 執行：

```bash
source /opt/ros/foxy/setup.bash
source /home/p450/p450_ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=0
export ROS_LOCALHOST_ONLY=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp

python3 /home/p450/p450-jetson-handoff/scripts/p450_offboard_heartbeat_probe.py \
  --duration 125 --rate 10 --reliability reliable \
  --csv /media/p450/P450_DATA/rosbags/TEST_ID_nx_heartbeat.csv
```

只要 PX4 trace `frozen=1` 或 probe 結束，就停止增加測試時間。QGC 立即保存完整：

```text
uxrce_dds_client status
uxrce_dds_client trace
```

### 5.3 收尾與資料保存

在終端 A 以一次 `Ctrl-C` 結束診斷 Agent，隨即恢復正式服務：

```bash
sudo systemctl start p450-micro-xrce-agent.service
systemctl show p450-micro-xrce-agent.service -p ActiveState -p MainPID -p NRestarts
```

轉換 trace：

```bash
python3 /home/p450/p450-jetson-handoff/scripts/p450_agent_trace_dump.py \
  /dev/shm/p450_agenttrace_TEST_ID.bin \
  --output /media/p450/P450_DATA/rosbags/TEST_ID_agenttrace.csv
python3 /home/p450/p450-jetson-handoff/scripts/p450_agent_trace_dump.py \
  /dev/shm/p450_agenttrace_TEST_ID.bin --summary-only
sha256sum \
  /dev/shm/p450_agenttrace_TEST_ID.bin \
  /media/p450/P450_DATA/rosbags/TEST_ID_agenttrace.csv \
  /media/p450/P450_DATA/rosbags/TEST_ID_nx_heartbeat.csv
```

完整 binary ring 要先複製到新的 `evidence/TEST_ID/` 再重啟 NX；`/dev/shm` 不具持久性。
若 stop/start 再觸發 panic，優先保存 pstore，這輪標為 `ABORTED_KERNEL_GATE`，不得把殘缺
trace 當正式結果。

複製模板如下；先把 `TEST_ID` 換成當輪唯一值：

```bash
P450_EVIDENCE_DIR=/home/p450/p450-jetson-handoff/evidence/TEST_ID
test ! -e "$P450_EVIDENCE_DIR" || { echo 'REFUSED: evidence directory already exists'; exit 1; }
mkdir -p "$P450_EVIDENCE_DIR"
cp --preserve=timestamps /dev/shm/p450_agenttrace_TEST_ID.bin \
  "$P450_EVIDENCE_DIR/agent_trace.bin"
cp --preserve=timestamps \
  /media/p450/P450_DATA/rosbags/TEST_ID_agenttrace.csv \
  "$P450_EVIDENCE_DIR/agent_trace.csv"
cp --preserve=timestamps \
  /media/p450/P450_DATA/rosbags/TEST_ID_nx_heartbeat.csv \
  "$P450_EVIDENCE_DIR/nx_heartbeat.csv"
sha256sum "$P450_EVIDENCE_DIR"/* > "$P450_EVIDENCE_DIR/SHA256SUMS"
```

## 6. Phase 3：依 trace 分流，不做無證據調參

### 6.1 Agent callback 已晚

判據：同一異常窗中，`DDS_CALLBACK_BEGIN` 本身相對前一筆已出現大 gap，而 callback
之後的 sequence assignment／UART write 正常。

動作：

1. 同步記錄 Agent process CPU、run queue、thermal、frequency 與 competing workload。
2. 先停止非必要 workload 做 A/B，不先上 `SCHED_FIFO`。
3. 只有一般負載隔離有效，才把 Agent systemd service 的 CPU affinity／nice 設為下一個
   單一變因；每次只改一項並重跑 120 秒、600 秒。
4. 若 callback 前仍晚，轉查 Fast DDS reader／ROS publisher 到 Agent 的排程，不修改
   PX4 或 UART。

禁止在沒有 scheduler trace 時直接加入 realtime priority；錯誤的 RT priority 可能餓死
kernel 或其他飛行所需程序。

### 6.2 Callback 正常，但 sequence／queue／首次 send 晚

判據：`DDS_CALLBACK_END` 正常，`SEQ_ASSIGNED`、`QUEUE_NEW` 或第一次 `SEND_BEGIN` 晚。

動作：定位 Agent queue lock、output stream flush 與 writer thread；用該段耗時分布建立
最小 source patch。先以現有 Agent selftest 驗證，再以 125 秒 trace 場驗證。此分支不改
UART、PX4 或 QoS。

### 6.3 首次 UART write 準時，但 PX4 先看到後方 sequence

判據：Agent 已依序完成缺少 sequence 的 UART write；PX4 卻先記到後方 sequence，或
缺少 sequence 只在 retransmit 後出現。

這把問題縮到：Linux tty/driver、Tegra UART、level shifting／wire、serial HDLC framing、
PX4 UART/framing／run loop。進入 Phase 4 transport A/B；不要調 ROS queue。

### 6.4 ACKNACK 已回 Agent，但 retransmit 晚

判據：`ACKNACK_RX` 已出現，但 `RETX_QUEUE` 或 retransmit `UART_WRITE_BEGIN` 明顯延後。

動作：針對 Agent retransmit queue／write wakeup 做最小 patch。heartbeat period 保持
200 ms，因為 50 ms 已被否證；除非 trace 顯示 ACKNACK 本身只在 heartbeat 後才出現，
否則不再調 heartbeat。

### 6.5 History/window 壓力

只有 Agent trace 顯示 depth 16 被占滿、未確認資料無位置或因此延後新資料時，才進行
depth 16→32 A/B：

```bash
cmake -S /home/p450/Micro-XRCE-DDS-Agent-2.4.2 \
  -B /media/p450/P450_DATA/builds/microxrce-agent-depth32 \
  -DUAGENT_CONFIG_RELIABLE_STREAM_DEPTH=32 \
  -DUAGENT_CONFIG_HEARTBEAT_PERIOD=200
cmake --build /media/p450/P450_DATA/builds/microxrce-agent-depth32 -j2
```

configure 必須沿用已驗證 2.4.2 build 的 dependency prefix／compiler；若 CMake 開始抓取
不同版本 dependency，或 generated constants 不是 depth 32、heartbeat 200 ms，就中止。
使用隔離 build，不覆寫 `/usr/local`。若 trace 沒有 history 壓力，禁止做此 A/B；增加
history 可能只增加 backlog 與記憶體，並不讓缺失 frame 更早抵達。

## 7. Phase 4：Transport 單一變因 A/B

Phase 4 的目的是區分「Agent/ROS」與「serial 路徑」，不是立刻永久改裝。

### 7.1 優先 A/B：PX4 支援的 UDP／Ethernet

PX4 v1.14 與 Agent 官方都支援 UDP。只有在實際 Pixhawk 6C carrier 暴露受支援 Ethernet、
韌體包含對應 driver，且已完成參數備份後才可測。先唯讀確認參數存在：

```text
param show UXRCE_DDS_CFG
param show UXRCE_DDS_PRT
param show UXRCE_DDS_AG_IP
```

Agent 測試命令為：

```bash
MicroXRCEAgent udp4 -p 8888 -v 2
```

PX4 端依官方 Ethernet 文件設定 `UXRCE_DDS_CFG`、`UXRCE_DDS_PRT=8888` 與 Agent IP；
實際參數值必須由 QGC 依板載選項選取，不在本文件猜 enum。一次只更換 transport，topic、
rate、Reliable、韌體邏輯與測試長度不變。

判定：若 UDP 連續三輪 600 秒 `>250 ms=0`，而 serial 同條件仍重現 sequence hole，
serial/HDLC/driver 路徑得到強支持；這不是證明 ROS QoS 修好了問題。

### 7.2 若無 Ethernet：獨立 3.3 V USB-UART A/B

這需要機主明確授權與實體操作：

- 只用 3.3 V TTL，相容 PX4 TELEM 電平；
- 共地；TX/RX 交叉；不要連接 5 V；
- 原 NX UART TX 必須先斷開，禁止兩個 TX driver 同時接同一條線；
- 由插拔前後 `lsusb`、`dmesg`、`ls -l /dev/ttyUSB*` 確認裝置，不猜 `/dev/ttyUSB0`；
- 先用 115200 做同速 A/B，通過後才把更高 baud 當下一個單一變因。

驗證命令模板：

```bash
lsusb
dmesg --ctime | tail -n 80
ls -l /dev/ttyUSB* 2>/dev/null
sudo fuser -v /實際確認的tty裝置
sudo /usr/local/bin/MicroXRCEAgent serial \
  --dev /實際確認的tty裝置 -b 115200 -v 2
```

如果另一 serial adapter 仍在相同 sequence 位置／頻率出洞，偏向 Agent 或 PX4 protocol
處理；若只有 Tegra `/dev/ttyTHS1` 失敗，偏向 Tegra UART／device-tree／level path。

### 7.3 Baud rate 不是第一步

115200 的 8N1 理論上限是每方向 11,520 byte/s，目前 PX4 output 約 2.9 KB/s，純粹頻寬
已不是最強假設。升 baud 只會縮短 serialization time，不保證降低 frame corruption；而
P450 過去在高 baud 有 UART clock 容差歷史。因此只能在 transport 路徑已定位後做
115200→460800 單一變因 A/B，不能與 adapter、Agent 或 QoS 同時改。

## 8. Phase 5：QoS 最終選型與 freshness 防線

### 8.1 預設保留 Reliable

在 transport 根因未修復前保留目前 Reliable baseline，因為它已證明最終 6001/6001。
不要因為 Reliable 有 head-of-line blocking 就立即回退 Best Effort；Best Effort 的 60 秒
實測已有 2.50% 遺失且違反 250 ms gate。

### 8.2 Deadline 只作告警

若未來在 ROS publisher 加入 Deadline，建議把它當作 publisher／subscriber 的本地健康
事件，不能取代 PX4 receipt counter。ROS graph 只知道 DDS policy/event；P450 的安全
判定仍以 PX4 deserialize 後 `R(n)` 為準。

### 8.3 Lifespan 只作第二層 stale-data 保護

可在 transport 已 PASS 後，以獨立分支驗證 250 ms lifespan 是否真的跨 Fast DDS／Agent／
XRCE 生效。驗證前不可宣稱它能繞過 Reliable receive window；若過期 sample 仍占用
sequence hole，lifespan 不會解決本問題。

### 8.4 Best Effort freshness A/B 的前提

只有 transport 已連續通過 Reliable 600 秒與 soak，才可使用只改 heartbeat reader/stream
與 publisher reliability 的成對韌體，重做：

```bash
python3 /home/p450/p450-jetson-handoff/scripts/p450_offboard_heartbeat_probe.py \
  --duration 600 --rate 10 --reliability best_effort \
  --csv /media/p450/P450_DATA/rosbags/TEST_ID_best_effort_10hz.csv
```

必要時再把 10→20 Hz 當下一個單一變因。Best Effort 的驗收重點不是 publish/receipt
count 完全相等，而是 PX4 receipt `max gap <250 ms`、`>250/500 ms=0/0`、無 Offboard
loss。若任何一項失敗，Reliable 仍是正式候選。

不要把 `VehicleCommand`、setpoint 與 heartbeat 一次全部改 QoS；不同語意必須分 topic
決策，否則無法知道是哪一項改動造成結果。

## 9. Phase 6：正式回歸與飛行 gate

### Gate A：120 秒 diagnosis

- 1 輪，目的是快速淘汰候選；任何 `>250 ms` 即 FAIL。
- 0 次違規只算 preliminary PASS。

### Gate B：600 秒 formal

- 3 輪，每輪建立乾淨 session/counter，輪間不混入 preflight heartbeat。
- 三輪都必須符合第 2.3 節；任何一輪 FAIL 就停止，不以平均值掩蓋 tail。

### Gate C：3600 秒 no-prop soak

- 1 輪，維持 disarmed、非 Offboard，只發布 heartbeat。
- Reliable 必須零最終遺失、`>250/500 ms=0/0`；kernel 與 Agent 也必須無錯。

### Gate D：無槳 Offboard

只有 A–C 全 PASS，才在室外定位有效、RC Kill 可用、機體固定的條件下執行無槳
Offboard 切入／切回；仍同步保存 NX CSV 與 PX4 receipt counter。任何 `No offboard
signal`、Position fallback 或 >250 ms gap 都是 FAIL。

### Gate E：無槳 armed

只有 Gate D 重複 PASS，才做無槳 armed hold。先驗證 normal disarm，不得以 Kill 作日常
收尾。若 land detector、RC loss、GPS/EKF 或 kernel 任一 gate 未過，停止。

### Gate F：有槳地面／飛行

需要機主另行明確授權與獨立風險評估；本 runbook 不自動授權裝槳或飛行。不得用提高
`COM_OF_LOSS_T` 來通過前面任何 gate。

## 10. Evidence 目錄與結果格式

每一正式場建立新目錄，不覆寫既有證據：

```text
evidence/TEST_ID/
  README.md
  nx_preflight.txt
  nx_heartbeat.csv
  agent_trace.bin
  agent_trace.csv
  qgc_pretest.txt
  px4_status_post.txt
  px4_rxtrace_post.txt
  kernel_pre.txt
  kernel_post.txt
  SHA256SUMS
```

`README.md` 必須包含：

- TEST_ID、開始／結束時間與時區；
- Git commit、PX4 `ver all`、Agent binary/library SHA-256；
- transport、baud、QoS、rate、duration；
- props/disarmed/nav/failsafe 狀態；
- NX publish 與 PX4 receipt count、max、`>150/250/500 ms`；
- Agent PID/NRestarts 與 session lifecycle；
- 是否出現 sequence hole、第一個 hole 的完整配對；
- PASS／FAIL／ABORTED 及單一理由；
- 所有 raw file checksum。

固定結果摘要：

```text
TEST_ID:
SINGLE_VARIABLE:
NX_PUBLISH_COUNT:
PX4_RECEIPT_COUNT:
FINAL_LOSS:
NX_MAX_GAP_MS:
PX4_MAX_GAP_MS:
PX4_OVER_150_250_500_MS:
FIRST_SEQUENCE_HOLE:
AGENT_RESTARTS:
KERNEL_ERRORS:
RESULT: PASS | FAIL | ABORTED | INCONCLUSIVE
NEXT_ACTION:
```

## 11. 推薦執行順序

1. **現在**：只做 Phase 0 唯讀 baseline；維持 Agent active，不發布控制資料。
2. **第一個維護窗口**：Phase 1，先做不載入 `88x2bu` 的 kernel A/B 與 soak。
3. **kernel gate PASS 後**：執行一次 Phase 2 正式 Agent trace，優先取得缺洞位置。
4. **依 trace 分支**：只修 Agent scheduling/retransmit 或只做 transport A/B，不同時改。
5. **候選初測**：120 秒；失敗即淘汰。
6. **正式驗證**：三輪 600 秒，再一輪 3600 秒 no-prop soak。
7. **最後**：比較 Reliable 與 freshness-oriented QoS；Deadline/Lifespan 只作額外防線。
8. **所有 transport 與 kernel gate 都 PASS 後**，才進入無槳 Offboard／armed 階梯。

最有資訊量的下一步仍是 Agent sequence trace；最可能真正降低 Reliable tail latency 的
方法是消除觸發重傳的 sequence hole，或更換會產生該 hole 的 transport 階段。單純把
Reliable、Deadline、Lifespan、queue depth 當成同一個旋鈕，不能由官方文檔或目前實測
支持。
