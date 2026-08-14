以目前最新 `40bb48b...` 的乾淨 hb50 結果為基準，我認為**下一步不應再改 heartbeat、QoS、COM_OF_LOSS_T，也不應立刻做 armed/Offboard**。現在要做的是一次能把 298–600 ms 延遲「切開」的實驗。

### 第一性原理先重新定義問題

系統真正要求的是：

**NX 產生控制 heartbeat → PX4 在 deadline 內取得該 heartbeat。**

現在已知：

| 層級                |           已知結果 | 判定                   |
| ----------------- | -------------: | -------------------- |
| NX publisher      | max 119.042 ms | 正常                   |
| Reliable delivery |    1201 → 1201 | 無 final loss         |
| PX4 receipt       | max 298.884 ms | 異常                   |
| `>250 ms`         |    4 次 / 120 s | FAIL                 |
| Agent restart     |              0 | 不是 session restart   |
| framing status    |        state 0 | 沒有常駐 framing failure |
| FIONREAD errors   |              0 | syscall error 不是主因   |

所以未知時間只能存在於：

**ROS publisher → DDS/Agent → XRCE Reliable → Jetson UART TX → physical wire → PX4 UART RX → framing → Reliable reorder/recovery → PX4 callback**

而不是 Commander、Offboard mode switching、arming 或 flight controller 控制律。

更重要的是，Micro XRCE-DDS Client v2.4.2 的 Reliable input 本身具有 **head-of-line blocking** 行為：如果收到的 `seq_num` 不是下一個預期序號，就先存進 reliable buffer；只有缺失的前序 message 補回來後，後面的資料才會向上交付。

而且 Client 並不是只有收到 Agent HEARTBEAT 才發 ACKNACK；正常 Reliable message 處理後也會產生 ACKNACK，收到 HEARTBEAT 時同樣會產生 ACKNACK。

**這正好解釋為什麼 200 → 50 ms heartbeat 沒救。**
所以繼續調 25 ms、10 ms，第一性原理上已經沒有高資訊價值。

## 下一步照這個順序做

1. **P0：先做「實體 UART wire trace」，不要先改協定。** 在 NX TX → Pixhawk TELEM2 RX 線上掛高阻抗 logic analyzer，只被動監聽 115200 8N1，維持 `e6f3d83ff5`、原 200 ms Agent、Reliable、10 Hz、disarmed、目前 2.87 KB/s output。跑乾淨 120 秒。這一步只問一個問題：**發生 PX4 >250 ms gap 時，實體線上是不是也真的超過 250 ms 沒有 NX→PX4 XRCE frame？** 如果 wire 上已經有 300 ms 空窗，問題在 PX4 之前；如果 wire 仍約每 100 ms 有完整資料，問題直接縮到 PX4 UART RX/framing/Reliable 處理。Serial transport 本來就依賴 framing 來分隔 XRCE packets，所以實體 wire 是目前最靠近「真相」且不會被軟體 logging 擾動的觀測點。([GitHub][1])

2. **P0：同時做 PX4 Reliable sequence trace，而不是再看 aggregate counter。** 在 `uxr_receive_reliable_message()` 附近加一個固定大小 RAM ring buffer，**禁止在 hot path `PX4_INFO()` 狂印 log**。每個 input reliable frame只記 `hrt_absolute_time`、`seq_num`、`last_handled before/after`、`last_announced`、`message_stored`、`ready_to_read`；ACKNACK 再記 `from + nack_bitmap`，Offboard callback 再記 message timestamp + receipt timestamp。遇到 Offboard gap >250 ms 時 freeze ring，測後再 dump。v2.4.2 原始碼已直接提供 `last_handled`、`last_announced`、reliable buffer 與 `uxr_compute_acknack()`，所以沒有必要猜。

3. **P0：把每一次 >250 ms 事件分類。** 我只接受五種結論之一：① Agent 根本沒及時送；② Agent 送了但 wire frame 缺失/損壞；③ PX4 UART 已收到 bytes，但 framing 沒形成有效 XRCE message；④ XRCE 發生 sequence hole，後續 message 被 Reliable buffer 卡住，等待 retransmission；⑤ XRCE message 已完整進來，但 PX4 session/run-loop 延遲處理。**在能分類以前不要做「修復」。** 目前最大的嫌疑是③/④/⑤，而④尤其符合「Reliable 1201/1201、Best-Effort 會 loss、Reliable 卻出現長 tail」這種症狀，但現在仍只是高優先假設，不是已證實根因。

4. **P1：定位後才做 transport A/B。** 如果 trace 顯示 sequence hole 或 framing loss，下一個單變因不是改 heartbeat，而是把 **Jetson Tegra UART 路徑換掉**：NX USB → FTDI/CP210x 3.3 V UART → Pixhawk TELEM2，PX4 firmware、Agent、115200、QoS、topic、rate 全部不變。若 >250 ms 消失，責任集中到 Jetson `ttyTHS1` driver/clock/electrical path；若完全保留，則集中到 Pixhawk UART / XRCE software path。這比再刷 PX4 大版本資訊量高很多。

5. **P1：再做 full-duplex load scaling。** 目前 PX4 TX 約 2869 B/s；115200 8N1 理論 wire capacity 約 11.52 kB/s，所以單看平均頻寬並不接近飽和。現在 `Serial RX pending max=166 B`，換算純 wire time也只有約 14.4 ms，與 299 ms 相差一個數量級；但這個 counter可能漏掉瞬間 backlog，所以不能只靠它排除 driver scheduling。 應在完成 sequence trace 後再做 PX4→NX output ≈0、目前 2.9 KB/s、較高實際 telemetry 三點 A/B，看 tail latency 是否隨 full-duplex load 成比例改變。

6. **最後才回到飛行 gate。** 修正後先重新跑相同 120 秒；`>250 ms > 0` 就立即 FAIL。120 秒為 0 只能算 preliminary PASS；接著至少重跑原本 600 秒條件，確認 `>250 ms=0`，再做長時間 soak、Agent restart、NX reboot、PX4 reboot、正式 telemetry/rosbag/CPU load。這些都通過後，才進無槳 Offboard → armed Offboard → normal Disarm；裝槳是最後一關。現在不能用 `COM_OF_LOSS_T` 加大去掩蓋 transport latency。

### 我目前最想驗證的根因模型

目前最符合所有證據的是：

**偶發的一個 XRCE Reliable frame沒有被 PX4正常接收/處理 → 後續 sequence 已到但因 Reliable ordering 被 buffer → ACKNACK/retransmission 補回缺口 → 所有資料最終 1201/1201，因此「零 loss」，但 callback 出現 200–600 ms head-of-line stall。**

Micro XRCE-DDS v2.4.2 原始碼確實會在不是下一個 sequence 時把 message 存入 reliable buffer，而不是直接向上交付；只有順序重新連續後才繼續讀 buffered messages。

這個模型同時解釋：

**Best-Effort：** frame 出問題 → 永久 loss。
**Reliable：** frame 出問題 → 最後補回 → 0 loss，但產生 tail latency。
**hb50：** recovery heartbeat 變快仍 FAIL → heartbeat period 不是主要 bottleneck。

但目前還缺最關鍵的一張證據：

> **那 298.884 ms gap 裡，有沒有實際 XRCE sequence hole？**

所以如果 NX 端現在只能做**一件事**，我會指定：

**做 `XRCE reliable sequence/ACKNACK ring trace + 120 秒乾淨重現`。**

如果硬體上有 logic analyzer，就和 NX→TELEM2 RX wire capture 同時做。這兩份證據一拿到，下一步大概率可以直接判斷該修 **Agent/DDS、Jetson UART、serial framing、Reliable retransmission，還是 PX4 run-loop**，而不是繼續靠 A/B 猜。

[1]: https://github.com/micro-ROS/micro_ros_setup/issues/676?utm_source=chatgpt.com "Continuous Serialization and Image Data Streaming · Issue #676 · micro-ROS/micro_ros_setup"
