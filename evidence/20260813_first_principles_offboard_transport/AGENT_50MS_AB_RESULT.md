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

因此正式 A/B 判為 **INCONCLUSIVE / protocol contamination**，不得標示 PASS，也不應把
17 次 >250 ms 全部武斷歸給正式場。乾淨重測時必須先完成安全短測，再重建 hb50 XRCE
session 以清零 Offboard counters，確認唯一 endpoint 後直接開始正式 600 秒場，中間不得
再發布測試 heartbeat。

## 測後 kernel panic

正式場與 QGC counter 擷取完成後，原 200 ms Agent 已回復；約 11:10:13 CST，NX 在
`key_garbage_collector → key_put()` 發生 kernel panic，操作者按 RST 重開。這不是正式場內
的 Agent restart，但它是獨立的系統穩定性阻塞條件。詳見：

```text
evidence/20260814_nx_kernel_panic_key_gc/
```

在 kernel panic 原因處理前，暫停新的 10 分鐘重測、裝槳與飛行。
