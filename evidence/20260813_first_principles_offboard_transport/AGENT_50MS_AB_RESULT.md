# MicroXRCEAgent 50 ms heartbeat A/B 結果

日期：2026-08-14（Asia/Taipei）

## 目的與單一變因

前一輪 PX4 v1.14.3 custom `e6f3d83ff5`、Agent v2.4.2 預設 200 ms 的 Reliable 10 分鐘
測試為 6001/6001、零最終遺失，但 PX4 最大 receipt gap 601.548 ms，`>250/500 ms=16/2`。
本輪只把 NX MicroXRCEAgent 的 `UAGENT_CONFIG_HEARTBEAT_PERIOD` 從 200 改成 50 ms：

- PX4 firmware 不變；
- `RELIABLE_STREAM_DEPTH=16` 不變；
- TELEM2 ↔ `/dev/ttyTHS1`、115200 8N1、不用 flow control 不變；
- topic、rate、QoS、failsafe 與 `COM_OF_LOSS_T=1.0 s` 不變。

## 隔離建置與驗證

build：

```text
/home/p450/builds/microxrce-agent-2.4.2-hb50/build
```

generated constants：

```text
RELIABLE_STREAM_DEPTH = 16
HEARTBEAT_PERIOD = 50
```

SHA-256：

```text
9090ce2547f9762ca9902fb1884bb54f3b31999726af517d63aa8ee66718aa3e  MicroXRCEAgent hb50
09a7a7fccf07c657b261802c0cf9d5d1eea3c94d431fc1054a4328d7a5580bf1  libmicroxrcedds_agent.so.2.4.2 hb50
0feffc477e41c2ddd9a15d55fad0e55f27a78c02cb4b89a549851fa97f3017c6  /usr/local/bin/MicroXRCEAgent 200 ms
a22396c2047246176b105f568a5377c7ebf1aa6682e91743b27862da59f9bf41  /usr/local/lib/libmicroxrcedds_agent.so.2.4.2 200 ms
```

hb50 binary 的 RUNPATH 與 process maps 均確認載入 hb50 build tree 的 Agent library，而非
`/usr/local/lib`。它以 transient systemd service 運行，測試期間 PID 6621、重啟 0 次；
原 200 ms service 當時為 inactive。

## 安全條件

全程無槳、disarmed、非 Offboard。probe 只發布 `OffboardControlMode`，不發布 setpoint、
`VehicleCommand`、模式切換或 ARM 命令；狀態不安全即停止。

hb50 正式場之前先跑 2 秒前測：21 publishes、NX max gap 115.733 ms、`>150/250/500=0/0/0`。

## NX 正式 600 秒結果

CSV：

```text
live_20260814_heartbeat_reliable_10hz_10min_agent_hb50.csv
SHA-256 48f395f51f12e08cf439547d61dcbb11b06cd5c84407fe579ebdbdddc1c8841a
```

正式場時間 10:52:55–11:02:55 CST：

```text
publishes:                  6001
gaps:                       6000
mean publish gap:           99.998467 ms
max publish gap:            121.037 ms
>150/250/500 ms:            0/0/0
sequence errors:            0
unsafe or unmatched rows:   0
```

6001 列全部為 Reliable、subscription=1、arming_state=1、nav_state=4、
nav_state_user_intention=4、failsafe=0。

## PX4 測後 counter 與邊界污染

QGC 原始輸出保存在 repository 根目錄 `雙端交接文件.txt`：

```text
Running, connected
Payload tx: 3018 B/s
Serial RX FIONREAD errors: 0
Complete payload bytes received: 96688
Serial framing: state 0, buffered 0 B, message 36/36 B
Offboard RX: count 6022, max gap 25953892 us, >150/250/500 ms 475/18/1
Offboard RX stream: reliable
```

`6022 = 21 前測 + 6001 正式場`，表示這兩個發布窗口最終都沒有遺失。PX4 counter 沒有在
前測後重設，因此把兩場間的人工停頓也算成 receipt gap：

```text
前測最後一筆 NX timestamp: 10:52:29 CST
正式場第一筆 NX timestamp: 10:52:55 CST
NX boundary gap:             25.858848 s
PX4 max receipt gap:         25.953892 s
差值:                        約 95 ms
```

所以 25.953892 s 明確是測試邊界，不是正式 10 分鐘內的 transport gap。扣除邊界那一次後，
兩個有效發布窗口合計為：

```text
>150/250/500 ms = 474/17/0
```

但因 21 筆前測沒有獨立的 PX4 counter snapshot，無法把這 474/17 次誠實分配到「2 秒前測」
與「600 秒正式場」，也無法得出正式場的精確 PX4 max gap。

`96688 - 6022*16 = 336 = 21*16 bytes`。這多出的 21 筆是切換 Agent 前 200 ms 前測留下的
complete-payload 累積值，再次證明 complete-payload counter 與 Offboard receipt counter
的 lifecycle 不相同。

## 判定

本輪可證明：

- hb50 可建置、正確載入並維持 session；
- NX 正式場排程完整穩定；
- 21+6001 Reliable samples 最終全部到達 PX4；
- 有效發布窗口內沒有 >500 ms receipt gap。

本輪不能證明：

- 正式 600 秒場是否達成 `PX4 >250 ms = 0`；
- 50 ms 是否比 200 ms 明確降低正式場 max gap。

因此第一次正式 A/B 判為 **INCONCLUSIVE / protocol contamination**，不得標示 PASS，
也不應把 17 次 >250 ms 全部武斷歸給正式場。乾淨重測時必須先完成安全短測，再重建
hb50 XRCE session 以清零 Offboard counters，確認唯一 endpoint 後直接開始正式場，中間
不得再發布測試 heartbeat。

## 乾淨 120 秒重測

600 秒並非初步判斷所需的最短時間：200 ms Agent 的舊 600 秒場有 16 次 >250 ms，平均
每 37.5 秒一次；若事件率不變，120 秒抓到至少一次的機率約 96%。60 秒則曾得到假性的
`>250 ms=0`，已知不足。因此本輪採 120 秒作最短判別；任何一次 >250 ms 即 FAIL，0 次
也只能算 preliminary PASS。

流程：

1. 在原 200 ms Agent 上跑 2 秒安全前測，確認 disarmed、非 Offboard；
2. 停止原 Agent，啟動 hb50 transient service，使 PX4 Offboard counters 清零；
3. 唯讀確認 hb50 PID/library、UART 與 0 publisher／1 Reliable subscriber；
4. 切換後不再跑 hb50 前測，直接執行正式 120 秒。

乾淨重測的 hb50 PID 為 7464、`NRestarts=0`；測後已停止 hb50 並恢復原 200 ms Agent。

NX CSV：

```text
live_20260814_heartbeat_reliable_10hz_120s_agent_hb50_clean.csv
SHA-256 0d6abec5f6965452c36ed74bd9e0b59e3ff363d6b515af49a7da9a29e397e9bc
```

NX：

```text
publishes:                  1201
gaps:                       1200
mean publish gap:           99.987829 ms
max publish gap:            119.042 ms
>150/250/500 ms:            0/0/0
sequence errors:            0
unsafe or unmatched rows:   0
```

PX4 QGC：

```text
Running, connected
Payload tx: 2869 B/s
Serial RX pending max: 166 B
Serial RX FIONREAD errors: 0
Serial framing: state 0, buffered 0 B, message 36/36 B
Offboard RX: count 1201, max gap 298884 us, >150/250/500 ms 65/4/0
Offboard RX stream: reliable
```

`count=1201` 精確等於本場 NX 1201 筆，沒有前測、人工邊界或最終遺失。NX 本身完全沒有
>150 ms，但 PX4 有 65 次 >150 ms、4 次 >250 ms，最大 298.884 ms。因此乾淨 120 秒
250 ms gate **FAIL**；停止測試，不需要延長到 600 秒。

這否證「601.548 ms 主要由 Agent 預設 200 ms heartbeat 的 1–3 個 recovery cycle 造成，
降到 50 ms 即可解決」這個單因假設。短場最大值低於舊 600 秒場不能當成改善證據，因為
觀察窗口長度不同；而 >250 ms 已非零，已足以否決目前 deadline gate。下一步不再繼續
調低 Agent heartbeat，而是量測 XRCE sequence／ACKNACK／retransmission，或做 transport
與 UART driver／電氣隔離。

## 測後 kernel panic

正式場與 QGC counter 擷取完成後，原 200 ms Agent 已回復；約 11:10:13 CST，NX 在
`key_garbage_collector → key_put()` 發生 kernel panic，操作者按 RST 重開。這不是正式場內
的 Agent restart，而是獨立觀察到的系統穩定性風險。詳見：

```text
evidence/20260814_nx_kernel_panic_key_gc/
```

這次 panic 先視為單次事件保留證據，不繼續死查，也不阻塞無槳地面主線；若再次發生相同
trace 才升級處理。裝槳／飛行前仍需完成 NX 穩定性 soak。
