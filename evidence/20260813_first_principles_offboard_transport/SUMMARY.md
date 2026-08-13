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

## 6. 目前仍未完成的驗證

截至寫檔時飛控沒有建立新 DDS graph：Agent active、UART 為 115200 8N1、沒有控制
publisher，但 `/fmu/out/vehicle_status` 沒有 publisher。最可能是飛控未供電；本輪沒有
重啟 Agent、沒有發布 heartbeat、沒有切模式或解鎖。

因此目前完成的是：

- PASS：問題可測量化；
- PASS：rate-limit／雙端 gap 診斷 source 可生成及編譯；
- PASS：artifact identity、board、flash 與 hash；
- PENDING：刷入後實機 transport A/B；
- PENDING：是否真正消除 Offboard loss；
- FAIL／禁止：尚未具備飛行許可。

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

## 8. 真正的底層解法界線

若本候選通過，解法不是「把 baud 降到 115200」本身，而是：

```text
可靠可解碼的 baud
+ 有明確 budget 的 telemetry rate
+ receive-side deadline measurement
+ session lifecycle reset
+ 在 COM_OF_LOSS_T 前保留數倍 timing margin
```

若本候選在 3.74 KB/s 下仍失敗，軟體限速不是底層答案；最短路徑是替換 transport 並做
電氣量測，而不是繼續修改 QoS、timeout 或 commander failsafe。
