# 從第一性原理驗證 Offboard heartbeat 底層解法

日期：2026-08-13（Asia/Taipei）

## 1. 問題的最小定義

自動飛行所需條件不是「ROS topic 看得到」，而是 PX4 commander 在任意連續
`COM_OF_LOSS_T` 視窗內都收到足夠新的 `OffboardControlMode`。

目前 `COM_OF_LOSS_T=1.0 s`，NX 目標發送率為 10 Hz，因此理想間隔是 100 ms。實機
armed 測試卻由 QGC 記錄：

```text
Armed by external command
No offboard signal
Failsafe activated, triggering fallback to position control
```

所以待解問題可精確寫成：

```text
NX 呼叫 publish 的時間序列 P(n)
PX4 成功反序列化的時間序列 R(n)

為何 max(R(n)-R(n-1)) >= COM_OF_LOSS_T？
```

任何沒有同時量到 `P(n)` 與 `R(n)` 的方法，都不能區分 Linux scheduling、DDS/Agent、
UART framing 與 PX4 client scheduling。

## 2. 不可違反的物理限制

目前 transport 是 115200 baud、8N1、無 flow control。每個 byte 需要 1 start、8 data、
1 stop，共 10 bits：

```text
115200 bit/s / 10 bit/byte = 11520 byte/s/方向
```

UART TX/RX 是 full duplex，所以兩方向各有 11,520 B/s，不能把兩方向 payload 直接相加
當作同一條 wire bandwidth。但兩方向仍共用 PX4 `uxrce_dds_client` task、session state、
CPU time、driver queue 與 flush/drain 順序，故高 output load 仍可能延後 input processing。

eProsima serial transport 還會加入 XRCE submessage 與 HDLC framing、CRC、address、length
及 byte stuffing，因此 `uxrce_dds_client status` 的 serialized payload counter 小於實際
wire traffic。上一版約 10.1 KB/s offered payload 已是理論容量 87.5%，物理餘裕不足。

## 3. 可證偽假設

### H1：NX/Linux 發送本身出現大 gap

預測：`P(n)` CSV 會出現 >150、250 或 500 ms gap。

若成立，優先處理 process priority、CPU starvation、電源／thermal throttling、Python
executor 或同時執行的 workload；改 PX4 firmware 不會修好。

### H2：PX4 output 負載使同一 XRCE task 無法及時處理 input

預測：舊版在 `P(n)` 正常時仍有 `R(n)` 大 gap；把 output offered load 從約 10.1 KB/s
降至 3.74 KB/s 後，`R(n)` gap 消失。

若成立，per-topic rate limit 是本機的底層軟體解法；之後再逐步增加必要 telemetry，
不可回到無上限輸出。

### H3：即使低負載，Jetson UART／level shifter／wire 仍破壞 input frame

預測：`P(n)` 正常且 output <5 KB/s，但 PX4 的 `R(n)` 仍有 >500 ms gap，或 raw UART
bytes 增加而 complete XRCE payload／receipt count 不增加。

若成立，rate limit 假設被否證。下一個底層動作是 3.3 V FTDI／Pixhawk USB transport
A/B，或用示波器／logic analyzer 測 bit timing、電平與 framing；不應繼續調 QoS 或
換 PX4 大版本。

### H4：DDS endpoint/session lifecycle 問題

預測：NX subscription count 不是 1、Agent session 重建、Pixhawk reboot 後 graph 殘留，
或 heartbeat count 在 endpoint 重建後歸零。

若成立，先修 session lifecycle。每次 Pixhawk-only reboot 後應重啟 NX Agent，再驗證
endpoint；不能把 stale graph 當成 connected。

### H5：關鍵 heartbeat 使用 Best-Effort，本身允許遺失

預測：即使 `P(n)` 正常、output 已低於 5 KB/s、session 沒重建，PX4 的 receipt count
仍可能小於 NX publish count。因為目前 ROS 2 DataReader QoS 與 Agent→PX4 XRCE input
stream 都是 Best-Effort，任何一層丟掉 sample 都不會重傳。

若成立，對 `OffboardControlMode` 做單一 topic Reliable A/B；其他 topic、115200、輸出
限流與 failsafe 全部不變。若 receipt count 與 gap 同時恢復，底層解法是把具 deadline
意義的 control heartbeat 可靠化，而不是繼續放寬 `COM_OF_LOSS_T`。

## 4. 已完成的底層實作

### 4.1 PX4 rate-limited bridge

source：

```text
branch: p450-v1.14.3-xrce-rate-limit-diagnostics
commit: 50c989f85bffb6bd080540a2dba88da424f3f065
base:   0438dbc6fd16fe4fb1df1adfda6ddf543373e47e
```

`generate_dds_topics.py` 現在驗證 YAML `rate_limit`，並轉為
`uORB::SubscriptionInterval` 的 microsecond interval。這不是只在 YAML 寫一個舊版不認識
的欄位；generated C++ 已核對為：

```text
failsafe_flags          200000 us = 5 Hz
vehicle_control_mode    200000 us = 5 Hz
vehicle_global_position 200000 us = 5 Hz
vehicle_gps_position    200000 us = 5 Hz
vehicle_local_position  100000 us = 10 Hz
vehicle_status          200000 us = 5 Hz
```

`position_setpoint_triplet` 與 `timesync_status` output 已移除，所有 input subscriptions
保持不變。

最大 serialized payload：

```text
184*10 + (85+21+62+141+71)*5 = 3740 B/s
3740 / 11520 = 32.5% theoretical wire capacity
```

### 4.2 PX4 receipt-side measurement

在 `OffboardControlMode` 通過 XRCE framing、CDR deserialize 後、publish 到 uORB 前，使用
PX4 `hrt_absolute_time()` 記錄：

- 成功 receipt count；
- 最大 receipt gap；
- >150／250／500 ms gap 次數；
- 最後一筆 receipt age。

這個量測點刻意放在反序列化成功後，所以 raw noise、CRC 失敗與不完整 XRCE frame 不會
被誤算成有效 heartbeat。

### 4.3 NX publish-side measurement

新增：

- `scripts/p450_offboard_heartbeat_probe.py`：只在 disarmed、非 Offboard 時發布
  `OffboardControlMode`；不發布 setpoint 或 VehicleCommand，若 armed／Offboard 立即停止。
- `scripts/p450_offboard_ground_probe.py --csv ...`：未來 outdoor hold 測試同步保存每次
  heartbeat/setpoint publish 時間。

CSV 使用 `time.monotonic_ns()`，不受 ROS time sync 或系統 wall clock 調整影響，並保存
DDS subscription count、arming、nav 與 failsafe 狀態。

## 5. clean build 與 artifact 證據

- compiler：ARM GCC 9.3.1。
- clean build：`1114/1114` 成功。
- image：1,934,628／1,966,080 B，FLASH 98.40%。
- 前版 image：1,934,852 B；新版本反而少 224 B。
- `board_id=56`、`board_revision=0`。
- `git_identity=v1.14.3-5-g50c989f85b`。
- container SHA-256：`99bbf652581e0a317c8d9ecf59fcd072d19536fed938b7d86dca2077b55c7664`。
- 解壓 image SHA-256：`e9df68a39f7a971dbc266c3116712ef13d6287399c7fe30ab57c10e8a9450e8f`。
- repository 內 artifact 與 build artifact 經 `cmp` 完全相同。

韌體：

```text
firmware/p450-pixhawk6c-v1.14.3-xrce-ratelimit115200-50c989f85b.px4
```

## 6. `50c989f85b` 實機 A 組結果

2026-08-13 已刷入 rate-limit 候選版。重啟 NX Agent 建立乾淨 XRCE session 後，已移除的
`position_setpoint_triplet` 與 `timesync_status` writer 消失，證明新韌體確實生效。

全程無槳、disarmed、非 Offboard，只發布 10 Hz `OffboardControlMode`，不送 setpoint、
VehicleCommand、模式切換或解鎖：

```text
NX:  publishes 601, max gap 119.813 ms, >150/250/500 ms 0/0/0
PX4: count 586, max gap 307002 us, >150/250/500 ms 11/4/0
PX4: Payload tx 2874 B/s, FIONREAD errors 0, framing state 0
PX4: Complete payload bytes received 9376
```

`9376 / 586 = 16 bytes`，精確等於每一筆成功解序列化 heartbeat 的 payload 大小；NX
發出 601 筆但 PX4 只收到 586 筆，少 15 筆（2.50%）。同場 NX publish-side 完全沒有
>150 ms gap，PX4 output 也已低於 5 KB/s，因此：

- H1 在本場否證：不是 NX 10 Hz scheduler 產生 1 秒停頓；
- H2 的「單純頻寬飽和」不足：限流成功但 receipt gate 仍 FAIL；
- H4 在本場否證：Agent PID/session 穩定，沒有 reconnect；
- 問題已縮到 ROS 2 publisher 之後、PX4 deserialize 之前；
- 本場最大 gap 307 ms，沒有重現 1 秒 failsafe，但已違反 250 ms 工程 gate，且
  Best-Effort 遺失具機率性，不能據此允許飛行。

原始 NX CSV：

```text
live_20260813_heartbeat_10hz.csv
SHA-256 4f3f2d0548bab86a526e7dc3dc024856134922d9e89de492e7e117502d40b3cf
```

## 7. 刷入後的嚴格驗證流程

### 7.1 刷入與身分

安全前提：無槳、穩定供電、QGC 完整參數備份、飛控為 Pixhawk 6C。

刷入後由 QGC MAVLink Console 核對：

```text
ver all
param show SER_TEL2_BAUD
uxrce_dds_client status
```

必須看到 hash `50c989f85b...`、TELEM2 115200、serial transport。Pixhawk reboot 後在
NX 執行一次：

```bash
sudo systemctl restart p450-micro-xrce-agent.service
```

ROS graph 必須只有六個 `/fmu/out/*`：

```text
failsafe_flags
vehicle_control_mode
vehicle_global_position
vehicle_gps_position
vehicle_local_position
vehicle_status
```

### 7.2 Gate A：無 input 的 output 負載

保持所有 `/fmu/in/*` publisher 為 0，查詢：

```text
uxrce_dds_client status
```

PASS：`Payload tx` 穩態 <5000 B/s，Agent/session 不重建。若仍約 10 KB/s，代表刷錯
artifact、舊 Agent entity 或 rate limit 未生效，立即停止。

### 7.3 Gate B：disarmed heartbeat 雙端 gap

NX：

```bash
source /opt/ros/foxy/setup.bash
source /home/p450/p450_ros2_ws/install/setup.bash
python3 scripts/p450_offboard_heartbeat_probe.py \
  --duration 60 --rate 10 \
  --csv /media/p450/P450_DATA/rosbags/offboard-heartbeat-10hz.csv
```

這個 probe 不發 setpoint、不發 command，且拒絕 armed／Offboard。執行中及結束時從 QGC
查：

```text
uxrce_dds_client status
```

PASS 必須同時滿足：

- NX `max_gap_ms <150`，`over_150ms=0`；
- PX4 receipt count 約為 NX publish count；
- PX4 `max gap <250000 us`；
- PX4 `>250/500 ms = 0/0`；
- `Offboard RX last age` 在 publisher 運行時 <250000 us；
- 無 Agent session restart、無 framing stuck、無 FIONREAD error。

`250 ms` 是工程 gate，保留在官方 2 Hz 最低需求與 1 秒 failsafe 前的四倍餘裕；不是 PX4
官方飛行認證值。

### 7.4 A/B 判定矩陣

| NX send gap | PX4 receipt gap | 低負載 | 結論 |
|---|---|---|---|
| PASS | PASS | PASS | H2 支持：rate limit 解決 client/transport 壓力 |
| FAIL | 不論 | PASS | H1：Linux publisher scheduling |
| PASS | FAIL | PASS | H2 否證；轉查 H3 UART/level shifter/framing |
| PASS | count 不增 | PASS | frame 未成功反序列化，查 raw RX／CRC／地址 |
| PASS | PASS 後突然歸零 | PASS | H4 session reset／Pixhawk power event |

### 7.5 Gate C：無槳 Offboard

只有 Gate A/B PASS，才在室外 GPS 穩定、無槳、RC Kill 可用的條件下，用已加入 CSV 的
ground probe 重做 Offboard 切入／切回。再通過後才可做 normal Arm hold。任何一次
`No offboard signal`、Position fallback 或 >250 ms receipt gap 都是 FAIL。

### 7.6 Gate D：Reliable 單一變因 A/B

因 A 組 receipt gate 已 FAIL，Gate C 暫停。刷入 `e6f3d83ff5` 後，NX 改用：

```bash
python3 scripts/p450_offboard_heartbeat_probe.py \
  --duration 60 --rate 10 --reliability reliable \
  --csv /media/p450/P450_DATA/rosbags/offboard-heartbeat-reliable-10hz.csv
```

PX4 console 必須先看到：

```text
Offboard RX stream: reliable
```

B 組 PASS 必須同時滿足：NX subscription count 1、NX 601 筆左右、PX4 receipt count
與 NX 差值不超過起停邊界 1 筆、PX4 `>250/500 ms=0/0`、session 不重建。若 Reliable
仍遺失或出現大 gap，才轉做 FTDI／USB transport 與實體電氣 A/B。

2026-08-13 實測結果：

```text
NX:  publishes 601, max gap 118.426 ms, >150/250/500 ms 0/0/0
PX4: count 601, max gap 207733 us, >150/250/500 ms 5/0/0
PX4: Complete payload bytes received 9616 = 601 * 16
PX4: Payload tx 2860 B/s, FIONREAD errors 0, framing state 0
PX4: Offboard RX stream: reliable
```

CSV 的 601 列全部為 `reliability=reliable`、subscription count 1、arming state 1、
nav state／intention 4、failsafe 0。Agent 使用同一 PID `47593`，測試期間沒有 session
重建、disconnect、reset 或 framing error。CSV：

```text
live_20260813_heartbeat_reliable_10hz.csv
SHA-256 913fd6e709c09b3582e187e1df20d5f103bcddcd66c1001f67c7446f5495993a
```

Gate D：**PASS**。Reliable 相較 Best-Effort 將 receipt loss 從 15/601 降為 0/601，
將 >250 ms gap 從 4 次降為 0 次。5 次 >150 ms 表示仍存在可被 Reliable stream
吸收的短暫延遲／重傳；目前 207.733 ms 最大值通過 250 ms 工程 gate，但不應把
60 秒結果外推為飛行可靠性保證。

## 8. 真正的底層解法界線

Best-Effort A 組證明限流是必要但不充分條件；Reliable B 組則以相同 10 Hz、115200、
output load 與飛控狀態通過，支持以下底層解法：

```text
可靠可解碼的 baud
+ 有明確 budget 的 telemetry rate
+ 對 deadline-critical heartbeat 使用端到端 Reliable stream
+ receive-side deadline measurement
+ session lifecycle reset
+ 在 COM_OF_LOSS_T 前保留數倍 timing margin
```

不能用增大 `COM_OF_LOSS_T` 掩蓋遺失，因為那只延後 commander 發現失聯。本次 60 秒
結果證明 Reliable 在目前地面條件可恢復 Best-Effort 遺失；後續仍須以長時間 disarmed
與無槳 Offboard 測試確認尾端風險。若再出現 >250 ms 或 count mismatch，才轉做 transport
替換與 UART 電氣／driver 量測。

## 9. Reliable Offboard B 組候選韌體

source：

```text
branch: p450-v1.14.3-xrce-reliable-offboard
commit: e6f3d83ff5004c2fd634f12b3c4bfb2983a1c157
base:   50c989f85bffb6bd080540a2dba88da424f3f065
```

最小修改只有：

- YAML 允許 subscription 選擇 `reliable: true`；
- `offboard_control_mode` DataReader QoS 改為 Reliable；
- 該 DataReader 的 XRCE delivery stream 改為 `reliable_in_stream_id`；
- 其他 12 個 PX4 input subscriptions 仍是 Best-Effort；
- NX probe 新增 `--reliability reliable`；
- commander、failsafe、setpoint、arming 與輸出限流完全不變。

clean build `1114/1114` 成功，ARM GCC 9.3.1，FMUv6C image
1,934,700／1,966,080 B（98.40%）。容器 metadata：`board_id=56`、
`git_identity=v1.14.3-6-ge6f3d83ff5`。container SHA-256：
`da2c86fc51b89c3b8851e2a002d6debb2befc21ee586011abceee3754ac8d948`；image SHA-256：
`c5cc0920257117ba19e2b54978f0cb21518bc0bf8e420bf9970ca80231b71adb`。

此版本已刷入並通過 60 秒 disarmed Reliable B 組。尚未完成長時間與無槳 Offboard／armed
測試，因此仍禁止裝槳與飛行。
