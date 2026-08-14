# Micro XRCE-DDS Agent sequence/send/ACKNACK trace（2026-08-14）

## 目前狀態

NX 端已完成 Micro XRCE-DDS Agent 2.4.2 的 software-only 診斷版本第一輪建置與自測。
正式 systemd Agent 尚未被替換，實機 UART trace 尚未執行；因此本文件只代表
`BUILD + SELFTEST PASS`，不代表 XRCE gap 已修復或根因已定位完成。

基底 source：

```text
/home/p450/Micro-XRCE-DDS-Agent-2.4.2
UAGENT_CONFIG_HEARTBEAT_PERIOD=200
Reliable stream depth=16
```

隔離 source／build：

```text
/home/p450/Micro-XRCE-DDS-Agent-2.4.2-agenttrace
/home/p450/builds/microxrce-agent-2.4.2-agenttrace/build
```

現行 `/usr/local/bin/MicroXRCEAgent` 與 `p450-micro-xrce-agent.service` 沒有被覆寫。

## 觀測事件

trace 只接受 `stream=128`，每筆 64 bytes，固定 32768 筆 ring，總量約 2 MiB：

```text
DDS_CALLBACK_BEGIN / DDS_CALLBACK_END
SEQ_ASSIGNED
QUEUE_NEW
SEND_BEGIN / SEND_END
UART_WRITE_BEGIN / UART_WRITE_END
ACKNACK_RX
RETX_QUEUE
ACK_UPDATE
HEARTBEAT_QUEUE
```

時間使用 `CLOCK_MONOTONIC_RAW`。hot path 不印 log、不做 CSV formatting、不做每包檔案
write；只以 atomic index 寫入 memory-mapped ring。檔案預定放在 `/dev/shm`，測後再由
`scripts/p450_agent_trace_dump.py` 轉 CSV。

雙端不可直接相減 Linux monotonic time 與 PX4 HRT。配對主鍵仍是
`(session_id, stream_id, seq_num)`，兩端分別在自身 clock domain 計算階段延遲。

## 自測結果

自測建立 18 筆事件，包含 seq 57 正常送出、heartbeat 宣告 last seq 61、ACKNACK
`first_unacked=58,nack_bitmap=0x0007`、seq 58 retransmit，以及分段 UART write：

```text
write_index=18
capacity=32768
valid=18
unstable=0
```

所有預期 event count 均相符，Python parser 通過 `py_compile`。完整 Agent 重新編譯完成，
無 compiler warning/error；binary RUNPATH 指向隔離 build 與既有 2.4.2 dependencies。

目前 build checksum：

```text
MicroXRCEAgent
SHA-256 0cfabea315262147898fb925308b479726542bd64653fa217c789fddb8e5d3f5

libmicroxrcedds_agent.so.2.4.2
SHA-256 49478f6957421e3210df81a24324fbaa6a3d471acffdfa93ece9550dc33a1cc1
```

## Patch 與重建

同目錄的 `0001-trace-add-P450-XRCE-Agent-shared-memory-timing-ring.patch` 包含全部
9 個 source/CMake 變更。套用到本機 2.4.2 baseline 後可使用既有 2.4.2 dependency
prefix 建置。Patch 必須先用 `git apply --check`；不要直接改 `/usr/local`。

```text
patch SHA-256  bc80d02e4d6b8717a4bef2a8905d28e01ad2e99c445cd7c94e269def7c9a925b
parser SHA-256 4f2265d0e1d68e3c4d2cdc845c458ad5b1e47a29f0a38a27df8acfb273497cec
```

已在另一份乾淨 2.4.2 source copy 完成 `git apply --check`、實際 apply 與逐檔
`diff -rq`；套用後內容和編譯用隔離 source 完全一致。

## 實機前 gate

1. QGC Codex 在 Issue #1 對唯一 TEST_ID 回覆 `READY_QGC`。
2. QGC pre-test 確認診斷韌體、disarmed、非 Offboard、trace reset 後為空。
3. NX 記錄正式 Agent PID/NRestarts/kernel baseline。
4. 僅在測試窗口停止正式 service，前景啟動隔離 binary 與 `/dev/shm` ring。
5. 確認 XRCE reconnected 與 ROS graph 後才執行 safe probe。
6. 任一停止條件成立，立即終止隔離 Agent並恢復正式 service。

實機結果需另存新 evidence；不得覆寫此 build/selftest 文件。
