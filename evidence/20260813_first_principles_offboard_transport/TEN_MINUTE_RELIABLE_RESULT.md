# Reliable Offboard heartbeat 10 分鐘雙端結果

日期：2026-08-13（Asia/Taipei）

## 結論先行

`e6f3d83ff5` Reliable 候選版解決了「最終遺失」，但尚未解決「deadline 內送達」。

```text
NX publish: 6001
PX4 receipt: 6001
最終遺失: 0
NX max publish gap: 159.999 ms
PX4 max receipt gap: 601.548 ms
PX4 >150/250/500 ms: 80/16/2
```

因此：

- PASS：6001/6001，Reliable 保證本場所有 heartbeat 最終到達；
- PASS：Agent/session 全程存活，沒有 reconnect 或 FIONREAD error；
- PASS：最大值仍低於目前 `COM_OF_LOSS_T=1.0 s`；
- FAIL：自行定義的 250 ms 飛行前 transport gate；
- 禁止：不能由此進入裝槳或飛行測試。

## 測試條件

- PX4：v1.14.3 custom `e6f3d83ff5004c2fd634f12b3c4bfb2983a1c157`。
- board：Pixhawk 6C／FMUv6C。
- transport：TELEM2 ↔ NX UART0，115200 baud、8N1、無 flow control。
- Agent：Micro XRCE-DDS Agent 2.4.2，`/dev/ttyTHS1 -b 115200 -v 2`。
- ROS 2 publisher：10 Hz、Reliable QoS、600 秒。
- PX4 DataReader：Reliable DDS QoS＋Reliable XRCE input stream。
- 機體：無槳、disarmed、非 Offboard、failsafe 0。
- publisher 只送 `OffboardControlMode`；沒有 setpoint、VehicleCommand、模式切換或解鎖。
- 測試前重啟 Agent，等待 DDS discovery 收斂為唯一一個 Reliable subscription。

## NX 發送端證據

指令：

```bash
python3 scripts/p450_offboard_heartbeat_probe.py \
  --duration 600 --rate 10 --reliability reliable \
  --csv evidence/20260813_first_principles_offboard_transport/live_20260813_heartbeat_reliable_10hz_10min.csv
```

結果：

```text
publishes=6001
median gap=101.612 ms
max gap=159.999 ms
>150/250/500 ms=1/0/0
```

CSV 6001 列全部為：

```text
reliability=reliable
subscription_count=1
arming_state=1
nav_state=4
nav_state_user_intention=4
failsafe=0
```

CSV SHA-256：

```text
8e4c68aea44a5733b4dcc91004c94de161c32303419f90b23f027615ea95e860
```

測試前後 Agent PID 都是 `48152`，結束後 ROS graph 為 publisher 0、subscription 1。
Agent journal 沒有 session closed、delete、disconnect、reset、framing error 或 warning。

## PX4 接收端證據

QGC MAVLink Console：

```text
INFO  [uxrce_dds_client] Running, connected
INFO  [uxrce_dds_client] Using transport: serial
INFO  [uxrce_dds_client] Payload tx: 2998 B/s
INFO  [uxrce_dds_client] Payload rx: 0 B/s
INFO  [uxrce_dds_client] Serial RX pending samples: 16108
INFO  [uxrce_dds_client] Serial RX pending bytes observed: 242422
INFO  [uxrce_dds_client] Serial RX pending max: 255 B
INFO  [uxrce_dds_client] Serial RX FIONREAD errors: 0
INFO  [uxrce_dds_client] Complete payload bytes received: 105632
INFO  [uxrce_dds_client] Serial framing: state 0, buffered 0 B, message 36/36 B
INFO  [uxrce_dds_client] Offboard RX: count 6001, max gap 601548 us, >150/250/500 ms 80/16/2
INFO  [uxrce_dds_client] Offboard RX stream: reliable
INFO  [uxrce_dds_client] Offboard RX last age: 572659023 us
```

`Payload rx: 0 B/s` 與 `last age` 是測試停止約 572 秒後查詢的瞬時值，不代表測試中
沒有接收。判定使用 receipt count 與累計 gap。

`Complete payload bytes received` 沒有在 Agent reconnect 時歸零；它包含前一輪短測：

```text
6001 * 16 = 96016 B   本輪 heartbeat
 601 * 16 =  9616 B   前一輪 heartbeat
                 ----
total       = 105632 B
```

算式與 PX4 counter 完全一致。`Offboard RX count` 在新 session init 時有歸零，因此本輪
6001 receipt 可直接與 NX 6001 publish 比較。

## 與 60 秒結果的差異

| 測試 | NX/PX4 count | NX max | PX4 max | PX4 >250 ms | PX4 >500 ms | 判定 |
|---|---:|---:|---:|---:|---:|---|
| Best-Effort 60 s | 601/586 | 119.813 ms | 307.002 ms | 4 | 0 | 遺失，FAIL |
| Reliable 60 s | 601/601 | 118.426 ms | 207.733 ms | 0 | 0 | 短測 PASS |
| Reliable 600 s | 6001/6001 | 159.999 ms | 601.548 ms | 16 | 2 | deadline FAIL |

短測沒有觀察到尾端事件，不代表尾端不存在。10 分鐘結果推翻「Reliable 已完整解決
deadline」的過早結論，但保留「Reliable 解決最終遺失」的結論。

## 第一性原理解釋

NX 自身最大 publish gap 159.999 ms，PX4 receipt 最大 gap 601.548 ms，因此額外延遲
發生在 ROS 2 publish 之後、PX4 CDR deserialize 之前。output 只有約 3 KB/s，Agent
session 沒重建，故不能歸因為 NX timer、11.52 KB/s payload 飽和或 session lifecycle。

本機實際安裝設定：

```text
/usr/local/include/uxr/agent/config.hpp
RELIABLE_STREAM_DEPTH = 16
HEARTBEAT_PERIOD = 200 ms
```

Agent 2.4.2 `Server::heartbeat_loop()` 每 `HEARTBEAT_PERIOD` 呼叫一次
`check_heartbeats()`。官方文件說明 Reliable stream 以 delivery confirmation、history 與
重送換取不遺失；Agent 2.4.2 官方 build 預設 heartbeat period 也是 200 ms：

- https://micro-xrce-dds.docs.eprosima.com/en/v2.4.1/client.html
- https://github.com/eProsima/Micro-XRCE-DDS-Agent/blob/v2.4.2/CMakeLists.txt

```text
601.548 ms / 200 ms = 3.008 個 recovery period
```

所以目前最符合數據的推論是：Best-Effort 原本直接遺失的 sample，在 Reliable 版本中
經 HEARTBEAT／ACKNACK 後被恢復；少數 sample 等待 1–3 個 200 ms recovery cycle，於是
count 完整但 deadline gap 拉長。這是由結果與實作共同支持的推論，尚未直接量到 XRCE
sequence number／ACKNACK，因此不能宣稱已證明 UART 電氣丟包。

## 已證明與未證明

已證明：

- Linux publisher 不是 601 ms gap 的來源；
- 目前 output payload 不是線速飽和；
- Best-Effort 會丟 heartbeat；
- Reliable 可在本場恢復所有 6001 筆；
- Reliable 預設 recovery timing 仍可能造成 601 ms receipt gap。

未證明：

- 第一個缺失 frame 發生在 Fast DDS、Agent queue、Jetson UART driver、level shifter、線材
  或 Pixhawk UART 哪一層；
- 601 ms 是否必然由三次 200 ms重傳造成；
- armed、Wi-Fi workload 或戶外環境下最大 gap 不會超過 1 秒。

## 下一個最小 A/B

先不修改 PX4、`COM_OF_LOSS_T`、baud、topic rate 或機體狀態。只重新編譯 Agent 2.4.2：

```text
UAGENT_CONFIG_HEARTBEAT_PERIOD: 200 ms -> 50 ms
RELIABLE_STREAM_DEPTH: 保持 16
```

以獨立 binary／systemd test service 做相同 10 Hz、600 秒 disarmed 測試。若缺失仍約需
三個 recovery period，預測尾端會由約 600 ms 降至約 150 ms。

PASS：6001/6001、PX4 max <250 ms、`>250/500 ms=0/0`、session 不重建。

FAIL：count mismatch、max >=250 ms、history full／session reset，或 UART framing/error
惡化。FAIL 時不再調 timeout，改做 Agent ACKNACK／retransmission sequence instrumentation
及 FTDI／USB transport 或 logic analyzer A/B。

降低 Agent heartbeat period 是 deadline mitigation，不是 UART 根因證明。即使通過，仍需
再做長時間 disarmed、無槳 Offboard，最後才考慮無槳 armed gate。
