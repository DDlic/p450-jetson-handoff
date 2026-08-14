# 2026-08-14 XRCE Reliable RX RAM Trace：建置與刷後測試交接

## 結論

已完成可刷入的 Pixhawk 6C 診斷韌體：

```text
firmware/p450-pixhawk6c-v1.14.3-xrce-rxtrace-c7a3947840.px4
SHA-256 8a23631277a1a8a14707e2e999f2e0319597fa733c50bdbd788443f2b3724706
```

這一版不是再次調 heartbeat，也不是宣稱已修復。它直接記錄 PX4 Micro XRCE-DDS
Client reliable input receive window，用來判定 298–600 ms Offboard receipt gap 是否由
sequence hole 與 head-of-line blocking 造成。

本次工作分成兩條同步進行：

1. 主線製作、編譯與封裝 PX4 RAM trace 韌體。
2. 協作線以目前已刷入的 `e6f3d83ff5` 做免編譯現況檢查，並從 Agent／Client
   v2.4.2 原始碼核對 reliable 與 ACKNACK 路徑。

依機主決定，本輪明確排除改線、掛阻抗、FTDI／CP210x、logic analyzer 與其他物理方法。

## 為什麼不是再調 Agent heartbeat

Micro XRCE Client 在收到一般 reliable DATA 後就會執行 `write_submessage_acknack()`；
收到 HEARTBEAT 時也會回 ACKNACK。一般 DATA 的 ACKNACK 呼叫位於 reliable case 的
條件判斷外，因此按序、out-of-order、重複或尚不能向上交付的 frame 都會回 ACKNACK。

Client reliable input 的核心行為如下：

- `seq_num == last_handled + 1`：立即交付。
- 後方序號先到且仍在 history window：先存入 buffer，設定 `message_stored=true`，
  `ready_to_read=false`，不交付 Offboard callback。
- 缺少的前序 frame 補到後，才由 `uxr_next_input_reliable_buffer_available()` 依序排空。
- `last_announced` 與 reliable buffer 共同產生 `first_unacked + 16-bit nack_bitmap`。

因此 10 Hz DATA 流本身通常在約 100 ms 後就能揭露前一個 sequence hole；把 Agent
HEARTBEAT 從 200 ms 改成 50 ms 未改善 tail latency，符合協定行為，不是意外結果。

方向必須分清：

```text
ROS 2 → Fast DDS → Agent ReliableOutputStream
→ UART → PX4 Client InputReliableStream → uORB Offboard callback
```

雙端最可靠的關聯主鍵是 `(session generation, stream_id=128, seq_num)`。P450 目前
Offboard object ID 為 1000、PX4 reliable input history 為 4、Agent reliable depth 為 16。

## 免編譯現況檢查

協作線全程唯讀，沒有刷韌體、改參數、重啟服務或發布 Offboard heartbeat。

2026-08-14 檢查結果：

- Agent：`active/running`，PID 7904，`NRestarts=0`。
- 命令：`MicroXRCEAgent serial --dev /dev/ttyTHS1 -b 115200 -v 2`。
- `/dev/ttyTHS1` 唯一持有者為 Agent PID 7904。
- termios：115200、8N1、無 parity、1 stop bit、無 RTS/CTS。
- 使用原始 200 ms Agent library，不是 hb50。
- 2 秒內 UART interrupt 增加 35。
- Agent `rchar` 約 3580 B/s，`wchar` 約 85 B/s。
- ROS graph 可見 13 個 `/fmu/in` entities 及目前最小化 PX4 outputs。

8 秒唯讀 `/fmu/out/vehicle_local_position` baseline：

```text
messages=81
average=10.111 Hz
arrival max=127.313 ms
source max=109.153 ms
>500 ms=0
```

這只證明當下 PX4→NX output 通暢，不等於 NX→PX4 reliable Offboard deadline 已通過。
舊桌面 listener 主要監控已被最小化韌體移除的 `sensor_combined`，不可再用來判定此問題。

## 韌體新增內容

### Micro XRCE Client callback

在 Client v2.4.2 加入可選的 `uxrOnReliableInputTraceFunc`。callback 在 receive-window
處理完成、ACKNACK 傳送前呼叫，沒有啟用時不改變原本行為。

記錄兩種 event：

- `1`：reliable MESSAGE。
- `2`：HEARTBEAT。

callback snapshot 包含：

```text
stream_id
seq_num
last_handled_before / after
last_announced_before / after
message_stored
ready_to_read
first_unacked_seq_num
nack_bitmap
```

Client patch 以 tracked patch 與 idempotent CMake apply script 保存，沒有讓主 repository
依賴一個未推送的 submodule commit。

### PX4 RAM ring

`uxrce_dds_client` 內有 96 筆固定大小 ring。接收 hot path 只寫 RAM，不執行
`PX4_INFO()`、檔案 I/O 或動態 allocation。每筆再加上：

```text
PX4 hrt receipt time
Offboard receive count
第一筆 post-gap Offboard receipt time
該 Offboard message timestamp
Offboard receipt gap
```

Offboard receipt gap 首次超過 250 ms 時，ring 在記下對應 protocol snapshot 後立即
freeze。測試結束後才由 console dump，不讓 log 輸出反過來干擾待測 hot path。

指令：

```text
uxrce_dds_client trace reset
uxrce_dds_client status
uxrce_dds_client trace
```

`trace` 輸出為 `RXTRACE` CSV-like 行；重要欄位順序會先由 `RXTRACE columns` 列出。

## Source 與建置紀錄

- PX4 基底：v1.14.3 累積分支 `e6f3d83ff5`。
- 新 branch：`p450-xrce-rx-trace`。
- 功能 commit：`d1841ee6d04f36a6c226a64dd7219a2e686deba9`。
- 最終 commit：`c7a39478405122a04ef9f10b69f873561751a126`。
- firmware identity：`v1.14.3-8-gc7a3947840`，無 `-dirty`。
- target：`px4_fmu-v6c_default`。
- toolchain：GNU Arm Embedded 9-2020-q2-update／GCC 9.3.1。

原始碼工作樹放在 eMMC，但數 GB build 全部放在 SD：

```text
source: /home/p450/PX4-Autopilot-xrce-trace
build:  /media/p450/P450_DATA/builds/PX4-Autopilot-xrce-trace-native/px4_fmu-v6c_default
```

建置過程遇到並排除兩個非程式碼問題：

1. 新 shell PATH 未包含 SD 上的 ARM toolchain；改為明確傳入
   `/media/p450/P450_DATA/builds/toolchains/gcc-arm-none-eabi-9-2020-q2-update/bin`。
2. build 經 symbolic link 時，Ninja 將大量 CMake dependency 解析成錯誤的相對路徑，
   造成反覆 `Re-running CMake`；改用 SD 實體 `-B` 路徑後消失。

最終 Micro XRCE ExternalProject configure／build／install、PX4 module compile、全機 ELF
link、BIN 與 PX4 container 封裝全部成功。再次 build 為 `ninja: no work to do`。

```text
FLASH:    1,954,268 / 1,966,080 bytes = 99.40%
AXI SRAM:    61,480 /   524,288 bytes = 11.73%
PX4 file: 1,813,134 bytes
BIN file: 1,954,268 bytes
```

## 刷入後最短有效測試

### 安全條件

- 維持無槳。
- 機體固定、disarmed、非 Offboard。
- 不發布 setpoint、不送 VehicleCommand、不切模式、不解鎖。
- Agent 保持原 200 ms、115200、`ttyTHS1`，不要同時改其他變因。

### 1. 刷後核對

在 QGC custom firmware 選擇上述 `.px4`。重啟後在 PX4 console：

```text
ver all
uxrce_dds_client status
uxrce_dds_client trace reset
```

應看到 firmware identity `v1.14.3-8-gc7a3947840`、`Running, connected`、
`Offboard RX stream: reliable`，以及 trace count／frozen 狀態。

### 2. NX 執行 125 秒 safe probe

```bash
source /opt/ros/foxy/setup.bash
source /home/p450/p450_ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=0
export ROS_LOCALHOST_ONLY=1
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp

python3 /home/p450/p450-jetson-handoff/scripts/p450_offboard_heartbeat_probe.py \
  --duration 125 \
  --rate 10 \
  --reliability reliable \
  --csv /tmp/p450_offboard_reliable_rxtrace_125s.csv
```

probe 只發布 `OffboardControlMode`，不發 setpoint、VehicleCommand 或解鎖命令；其安全
檢查若發現 armed、Offboard 或 subscriber 不匹配會拒絕執行。

### 3. 測後取證

PX4 console：

```text
uxrce_dds_client status
uxrce_dds_client trace
```

完整複製所有 `RXTRACE` 行到 handoff 新文字檔。若 `frozen=1`，已捕捉第一個 >250 ms
事件，不必繼續延長測試。若 125 秒 `>250 ms=0`，它只算 preliminary PASS，再 reset
trace 並重跑原 600 秒條件。

## 判讀矩陣

| Trace 現象 | 結論 |
|---|---|
| 後方 seq 先到、`stored=1`、`ready=0`、NACK bitmap 非零；補洞後 `last_handled` 一次跳進 | sequence hole＋head-of-line blocking 已證明 |
| seq 持續按序，但 Offboard callback gap 大 | PX4 session/run-loop 或 callback 路徑延遲 |
| HEARTBEAT 才使 `last_announced` 前進並產生 NACK | 最新 DATA frame 遺失且沒有後續 DATA 揭露 |
| Client trace 顯示缺洞，而 Agent 後續 trace 顯示有即時 retransmit | 問題縮到 Agent send 後至 PX4 Client receive 前 |
| Agent DDS callback 本身已晚 | ROS／Fast DDS／Agent reader 前段 |

Agent 端完整 RAM trace 尚未實作；若 PX4 ring 證明 sequence hole，再針對 Agent 的
`DDS_DATA_CB → SEQ_ASSIGNED → SEND_BEGIN/END → ACKNACK_RX → RETX_QUEUE` 做第二階段
software trace。雙端以 `(stream_id, seq_num)` 配對，不能直接拿 Linux wall clock 與
PX4 HRT 相減。

## 目前 gate

韌體只通過建置與靜態驗證，尚未刷入、尚未完成 125 秒實機測試。此階段不得宣稱
gap 已修復，也不得裝槳或飛行。下一個需要機主協作的動作只有：刷入指定韌體並重啟；
其後 NX probe 與資料整理由主對話執行。
