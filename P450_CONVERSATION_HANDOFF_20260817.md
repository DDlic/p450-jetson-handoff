# P450 NX 實驗全過程與新對話交接

> 文件日期：2026-08-17（Asia/Taipei）  
> 適用對象：下一個 NX Codex 對話、QGC 筆電端 Codex、機主本人  
> 專案：`DDlic/p450-jetson-handoff`  
> 目的：在不重新閱讀整段聊天紀錄的情況下，完整理解 P450 無人機、Jetson Xavier NX、Pixhawk 6C、ROS 2 Foxy 與 Micro XRCE-DDS 的目前狀態、已做實驗、已排除的方向與安全限制。

## 0. 新對話啟動方式

新對話開始時，先做以下事情，再進行任何測試：

1. 讀完本文件與 README 頁首的「目前協作入口」。
2. 依目前 Git `main` 分支檢查最新文件與 evidence；不要假設聊天中較早的版本仍是現況。
3. 先確認 SD 卡掛載於 `/media/p450/P450_DATA`，並確認 `/` 與 SD 的剩餘容量。
4. 先確認 `p450-micro-xrce-agent.service` 的目前狀態；目前不可為了切換診斷 Agent 而反覆 stop/start。
5. 任何有槳、解鎖、Offboard、模式切換或控制 setpoint 的動作，都必須由機主在當下明確授權，並重新確認安全條件。

新對話可直接使用以下開場文字：

```text
請先閱讀 /home/p450/p450-jetson-handoff/P450_CONVERSATION_HANDOFF_20260817.md、README.md
與最新 evidence。這是 P450 NX 實驗的延續，不要重做已完成的版本輪刷或 Agent stop/start。
先回報目前 Git HEAD、SD/eMMC 容量、Agent service 狀態與目前 transport/kernel gate，
再提出不會觸發 kernel panic 的下一步。
```

本文件不包含 sudo 密碼、Git token、SSH 私鑰或其他憑證。敏感資料不得寫入 Git。

## 1. 原始目標與實驗邊界

### 1.1 原始目標

本週的原始目標是：以 ROS 2 Foxy 完成一次自動飛行實驗。為了達成它，第一個必要前置條件是先建立並證明：

```text
PX4 飛控 → TELEM2/UART → Jetson NX → Micro XRCE-DDS Agent → ROS 2
```

可以長時間、低延遲、不中斷地傳輸，而且 Offboard heartbeat 不會因 gap 觸發 failsafe。

實際進展中發現，直接追求一次飛行會掩蓋底層傳輸問題，因此工作順序改成：硬體與儲存確認 → ROS 2 安裝 → UART 對應 → PX4/QGC 參數 → XRCE session → gap 根因 → kernel 穩定性 → 才考慮室外與有槳測試。

### 1.2 安全邊界

- 大部分診斷期間旋翼都已拆除。
- NX 端主要執行 readonly graph、IMU、heartbeat、Agent 與 log 測試。
- 沒有把 ROS 2 控制 publisher 當成可直接飛行控制器使用。
- QGC 筆電端 Codex 無法代替人操作 QGC；需要 QGC 的參數、刷寫、模式或解鎖操作，必須由機主本人在畫面上執行。
- 目前 transport gate 與 kernel gate 都不是飛行通過條件；在新對話中不可把「可靠傳輸零最終遺失」誤解成「已可安全飛行」。

## 2. 系統與硬體基線

### 2.1 NX

| 項目 | 已確認內容 |
|---|---|
| 主機 | Jetson Xavier NX |
| 平台 | P3668-0001，Board ID 3668，SKU 0001 |
| 系統 | Ubuntu 20.04，JetPack 5.1.4，L4T R35.6.0 |
| Kernel | `5.10.216-tegra` |
| 開機儲存 | eMMC `/dev/mmcblk0p1` |
| 外接 Wi-Fi | TP-Link USB，`wlan1`，`rtl88x2bu` |
| 內建 Wi-Fi | `wlan0`/Intel `iwlwifi` 有 hard block，已持久 blacklist，不是目前網路介面 |

### 2.2 飛控與線路

- 飛控：Pixhawk 6C / PX4FMUv6C。
- 機體外殼可見 `ETH`、`UART0`、`UART1`。
- 已確認 NX `UART0` 對應 Linux `/dev/ttyTHS1`。
- 已確認 `UART0` 線接到飛控 `TELEM2`。
- `UART1` 雖有線材，但線尾沒有接到任何裝置，收在機體線槽內；不要把它當成目前資料路徑。
- 最終可工作的串列路徑是：

```text
Pixhawk TELEM2 ↔ NX UART0 ↔ /dev/ttyTHS1 ↔ MicroXRCEAgent
```

### 2.3 網路與 QGC

- 外出時曾以手機 USB/Wi-Fi 基地台供 NX 網路；重開後曾經恢復很快。
- 室內時筆電可同時使用網路與連線機體；室外規劃是筆電沒有網際網路，只透過 Wi-Fi/TCP 連回無人機，供 QGC 與 Moonlight 使用。
- QGC TCP 曾經因 UXRCE 參數與重啟而消失，後續主要以 USB QGC 做參數和刷寫，再用 TCP 做檢查。
- 「QGC 顯示 `Running, disconnected`」曾是 XRCE 重連循環的瞬間狀態，不可單獨當作根因。

## 3. 儲存與 SD 卡處理歷程

### 3.1 SD 卡辨識與用途

早期側邊 microSD 插槽無法看到原本的 512 GB 卡；經 USB 讀卡機可看到約 500 GB，確認內容是 JetPack 5.1.4/L4T R35.6.0 的舊開機映像，並非普通資料卡。後來測試 128 GB 卡，也曾把 512 GB 卡插入 USB hub。

最後採用側邊 SD 作為資料儲存，不再把它當成 NX 開機碟：

- 單一 ext4 分割區，label `P450_DATA`。
- UUID：`99c03936-1ba4-49e8-a8d7-b2b158418e76`。
- 掛載點：`/media/p450/P450_DATA`。
- `/etc/fstab` 使用 `rw,nosuid,nodev,nofail,x-systemd.device-timeout=10`。
- `rosbags/`、`ulog/`、`builds/`、source、evidence、logs 與診斷輸出以 SD 為優先。

### 3.2 曾經的 eMMC 空間問題

一次 kernel panic 後看到 eMMC 使用率接近 94%，但追查發現是 panic 後在 `/tmp` 產生的兩份大型 kernel source clone；暫存目錄自動清理後，這不是 panic 根因。這件事仍確立了規則：NX 的 `/tmp` 在 eMMC 上，禁止把大型 source、build 或 trace 寫入 `/tmp`。

### 3.3 目前 SD-first 遷移狀態

目前已完成以下遷移／符號連結：

- `~/.codex` → SD 的 `builds/NX-user-storage/codex-home`
- `~/.cache` → SD 的 `builds/NX-user-storage/xdg-cache`
- `~/Downloads`、ROS `build/`、ROS `log/`、`~/.ros/log`
- Micro XRCE source/build、CMake toolchain、Python user site、診斷 builds
- `~/builds` → SD 的 Agent builds
- `~/p450-jetson-handoff` → SD source repo
- `~/bin/codex` 與 `~/bin/git-clone-sd` 使用 SD-first wrapper

當前參考容量：約 eMMC 14 GB 中使用 8 GB、可用 5 GB；SD 約使用 8.7 GB、可用 103 GB。建立超過 50 MB 的新內容前仍要重新檢查兩者容量與 SD mount。

為保留 rollback，遷移腳本留下兩份 eMMC backup：

- `~/.codex.emmc-backup-20260817_121342`，約 468 MB。
- `~/.cache.emmc-backup-20260817_121342`，約 15 MB。

在新 Codex 確認可正常啟動、更新、讀寫 session 後，才可執行：

```bash
~/Desktop/migrate_codex_to_sd_offline.sh finalize
```

它會要求人工輸入 `DELETE-EMMC-BACKUP` 才刪除備份；未確認前不要刪除。若遷移失敗，可使用同腳本的 `rollback`。完整政策見 [`SD_STORAGE_POLICY_20260817.md`](SD_STORAGE_POLICY_20260817.md)。

## 4. ROS 2 與 Agent 建置歷程

### 4.1 已完成安裝

- 已在線安裝 ROS 2 Foxy。
- 已建置 `px4_msgs` 與 `px4_ros_com`。
- ROS workspace 為 `/home/p450/p450_ros2_ws`；`src/` 與 `install/` 保留在 eMMC，`build/` 與 `log/` 已導向 SD。
- `ROS_DOMAIN_ID=0`。
- 使用 Fast DDS。
- 實機跨程序／跨主機測試必須使用 `ROS_LOCALHOST_ONLY=0`；設成 `1` 會把 systemd Agent participant 隱藏，造成「ROS graph 沒有 topic」的假象。

### 4.2 Agent 服務

服務名稱：`p450-micro-xrce-agent.service`。

目前正常服務命令的核心內容：

```text
/usr/local/bin/MicroXRCEAgent serial --dev /dev/ttyTHS1 -b 115200 -v 2
```

目前穩定基線為 Micro XRCE-DDS Agent v2.4.2、115200 8N1、無 flow control。診斷用的 Agent trace/hb50 build 另存於 SD；不可因為要切換 binary 就直接停止目前 service，因為 2026-08-17 停止服務時再次觸發 NX kernel panic。

## 5. PX4、參數與韌體歷程

### 5.1 版本路線

先後考慮／測試了 PX4 1.14.3、1.15.4，以及不同的 1.14.3 自訂修補。1.15.4 與其他版本沒有自然消除週期性 gap，因此回到 1.14.3 做可控的 instrumentation；不是因為已證明 1.14.3 是最終飛行版本。

已使用或保存的關鍵版本：

| 用途 | 版本／commit | 判讀 |
|---|---|---|
| 早期基線 | PX4 1.14.3 | 可建立 ROS graph，但 session/gap 問題存在 |
| 1.15.4 | source build | 仍有週期性約 1 秒 gap，未解決根因 |
| ping 最小回補 | 官方 `a1cce7e961df` 回補至 1.14.3 | 參數備份／還原成功，但非完整解法 |
| Offboard reliable | `e6f3d83ff5` | 將 heartbeat input 改為 Reliable；降低最終遺失，不消除 deadline gap |
| RX trace | `c7a39478405122a04ef9f10b69f873561751a126` | 增加 96-entry RAM ring trace，不改 flight loop、arming、failsafe、UART |
| RX trace firmware | `p450-pixhawk6c-v1.14.3-xrce-rxtrace-c7a3947840.px4` | SHA-256 `8a23631277a1a8a14707e2e999f2e0319597fa733c50bdbd788443f2b3724706` |
| preflight probe | `3410424` | 只設定 heartbeat 的 position intention；`--preflight-only` 不發布控制資料 |

PX4 1.14.3 另有 `VehicleIMU.cpp` 未初始化／重置 `delta_angle_clipping` 的已知缺陷，會令 `SensorCombined.gyro_clipping` 不可採信；這與 XRCE session 反覆重建是兩個獨立問題。

### 5.2 串列 baud 與 device tree

曾用 921600，後降至 460800，再做 Jetson UARTB device-tree clock/baud tolerance 修正；修正後 kernel 不再顯示 baud out-of-range，UARTB clock 約 7,418,181 Hz。但修正後 120 秒最大 gap 仍 3129 ms，重啟後 60 秒仍 3382 ms，因此 baud warning 不是根因。

後來以 115200 8N1 作為可靠基線，已證明能把完整 XRCE marker 解碼進 PX4，且較適合在 115200 UART 上進行可重現實驗；這不代表它已通過 Offboard deadline。

### 5.3 QGC 與 RC 設定歷程

- QGC USB 連線用於參數確認、重灌與還原。
- `UXRCE_DDS_CFG` 曾為 disabled，後來配置到 telemetry 路徑。
- `TELEM2` 使用 `TEL2_BAUD=115200`；早期有 921600、460800 的嘗試。
- `RC_MAP_FLTMODE=6`，`OFFB_SW=0`。
- CH5 在遙控器／QGC 顯示上與 flight mode 有特殊佔用現象，CH9/CH10 曾用作額外 switch。
- CH8 作為緊急停機，CH7 後來綁定解鎖 switch。
- 室外曾在無槳條件下確認 GPS mode 可解鎖，再由機主切換與 Kill；這是地面／安全測試，不是飛行認證。

## 6. XRCE gap 實驗時間線與判讀

### 6.1 初期 session 反覆重建

在 921600／460800 時，session 存活時間約 2.7–4.8 秒，降 baud 後一度改善到約 10–23 秒，但仍持續 reconnect。只用 USB 供電也沒有消除問題，因此低電壓主電池不是唯一原因。

完成 PX4 重灌、參數備份／還原後，ROS graph 曾看到 23 個 `/fmu/*` topics，也能讀 IMU、姿態、里程計；但短時間 discovery 出現 `23 → 2 → 16 → 23`，說明 session/entity 層仍在重建。

### 6.2 早期短暫通過與其限制

2026-08-03 的純接收地面條件曾得到：10 分鐘 42,936 筆 IMU，最大 gap 56.263 ms，無超過 100 ms；120 秒最大 35.617 ms；30 秒 systemd 最大 33.134 ms。這證明某些低負載、特定 session 條件可連續，但不能推導出已排除間歇性 failure。

### 6.3 輸出負載與 drain 嘗試

- 曾將 PX4→NX output 壓到約 2874 B/s；仍有 Best-Effort heartbeat 遺失。
- 1.15.4 output 仍出現接近 1 秒週期 gap。
- `SYNCT=0` 沒改善。
- 20 Hz 版本曾令 output 停止，需重啟 Agent。
- receive-drain candidate `996b1df7a1` 在 60 秒中出現最大 1005.408 ms、22 次超過 500 ms、7 次超過 1 秒，未通過。

因此「單純 PX4 output 太多」、「單純 Linux publish scheduling」、「只升級 PX4 版本」都不能單獨解釋現象。

### 6.4 Best-Effort 與 Reliable 對照

第一性原理測試的關鍵結果如下：

| 測試 | NX 發布 | PX4 收到 | PX4 最大 receipt gap | 結論 |
|---|---:|---:|---:|---|
| Best-Effort 10 Hz／60 s | 601 | 586 | 307.002 ms | 有遺失，FAIL |
| Reliable 10 Hz／60 s | 601 | 601 | 207.733 ms | 短測零遺失、短測 PASS |
| Reliable 10 Hz／600 s | 6001 | 6001 | 601.548 ms | 最終零遺失，但 250 ms deadline FAIL |
| Agent heartbeat 50 ms／NX 120 s | 1201 | 1201 | 298.884 ms | recovery 更快但仍有 65 次 >150 ms、4 次 >250 ms |

NX publisher 自身在 hb50 clean test 的最大 gap 只有 119.042 ms，說明「NX publisher 完全卡住」不足以解釋 PX4 端 298.884 ms／601.548 ms 的 receipt gap。Reliable 解決的是最終補回，不是即時 deadline。

### 6.5 125 秒 RX trace：目前最有資訊量的證據

2026-08-14／17 的 QGC Phase A/B 以 10 Hz reliable heartbeat 執行，NX 最大 publish gap 為 120.436 ms，而 PX4 最大 receipt gap 為 506.727 ms。PX4 自訂 RX trace 捕捉到：

- sequence 61 先到。
- sequence 58、59、60 暫時缺失。
- 直到缺失資料補上後才繼續交付。
- head-of-line stall 約 397.990 ms。

這把責任範圍縮到 ROS 2 publisher 之後、PX4 deserialize／deliver 之前的 reliable 傳輸路徑，至少包含串列送出、Agent reliable stream、ACKNACK/retransmit、PX4 client history 或其交付順序。

從 Agent 原始碼邏輯看，reliable DATA 若 out-of-order 到達會先存放、`ready_to_read=false` 並送 ACKNACK；缺少 sequence 到達後才會排空 buffer。此行為正好能解釋「零最終遺失但中間出現長 gap」。

目前最重要的 QGC evidence：

- [`QGC_RETURN_20260817_1040_AGENTTRACE_RELIABLE_125S_B.txt`](evidence/20260814_qgc_px4/QGC_RETURN_20260817_1040_AGENTTRACE_RELIABLE_125S_B.txt)
- [`QGC/PX4 README`](evidence/20260814_qgc_px4/README.md)
- [`第一性原理總結`](evidence/20260813_first_principles_offboard_transport/SUMMARY.md)
- [`10 分鐘 Reliable 結果`](evidence/20260813_first_principles_offboard_transport/TEN_MINUTE_RELIABLE_RESULT.md)

## 7. Kernel panic：目前必須優先處理的獨立風險

### 7.1 第一次 panic

2026-08-14 pstore 顯示 memcg/list-LRU 路徑：

```text
mem_cgroup_from_obj → list_lru_del → d_lru_del → proc_flush_pid
→ release_task → Kernel panic
```

加入 `cgroup.memory=nokmem` 後第一輪 controlled check 通過，kmem counters 為零；但這只能視為針對該 family 的 workaround，不能宣稱整台 NX 已修好。

### 7.2 第二次 panic（重複，gate 升級 FAIL）

2026-08-17 機主執行：

```bash
sudo systemctl stop p450-micro-xrce-agent.service
```

NX 隨後 freeze/reboot。不能說 stop 指令已被證明是直接原因，但時間上相關；pstore 明確顯示第二次與 2026-08-14 相同 family：

- uptime 約 3167 秒。
- task `kworker/1:2`，workqueue `events key_garbage_collector`。
- fault address `0x0000000200000000`。
- `key_put+0x30/0xb0`。
- call chain：`key_put → keyring_free_object → assoc_array_destroy → keyring_destroy → key_gc_unused_keys → key_garbage_collector`。
- kernel `5.10.216-tegra`，taint `G OE`，載入外接 `88x2bu(OE)`。
- pstore 沒有先出現 OOM、EXT4/I/O、thermal 或 soft/hard lockup。

外接 `rtl88x2bu` 因 taint 與 crash 前的 scan warning 是候選因素，但 stack 沒有進入 driver，還不能定罪。NVIDIA 35.6.0/35.6.5 `security/keys` 對照沒有直接 key-GC 修正，因此不能把升級 35.6.5 當成已驗證解法。

目前 kernel gate：**FAIL**。在完成 software-only A/B、或更換已知穩定 kernel 前：

- 不要反覆 stop/start Agent。
- 不要執行長時間 trace A/B。
- 不要在有槳狀態進行 Offboard 或自動飛行。
- 先保留 pstore 與目前 service，避免新的操作覆蓋證據。

完整原始證據見 [`20260817 repeated key GC panic`](evidence/20260817_nx_kernel_panic_key_gc_repeat/README.md)。

## 8. 目前真正狀態（交接時以此為準）

1. NX 能正常開機，ROS 2 Foxy、PX4 messages、Agent、workspace 已安裝。
2. `p450-micro-xrce-agent.service` 目前應保持 active；上次確認 MainPID 1708、NRestarts 0。
3. UART 路徑是 `/dev/ttyTHS1` ↔ Pixhawk TELEM2，115200 8N1、無 flow control。
4. ROS graph 與 PX4 topic 曾能正常建立，代表硬體和基本協定不是完全不通。
5. Reliable heartbeat 可零最終遺失，但中間 receipt gap 可達約 506–601 ms；250 ms deadline 尚未通過。
6. RX trace 已觀察到可靠序列缺洞與 head-of-line stall；這是目前最可信的 transport 根因方向。
7. Agent 50 ms heartbeat 不能把 PX4 gap 壓到 250 ms 以內，原本 200 ms Agent 已恢復。
8. kernel key-GC panic 已重複兩次，kernel gate FAIL。
9. SD-first 遷移已啟用；Codex/cache 的 eMMC rollback backup 尚未刪除。
10. 目前沒有「可以安全有槳飛行」的結論；室外 GPS 地面測試與無槳解鎖測試不能替代 transport gate。

## 9. 建議的新工作順序

### 優先級 A：先保護系統與證據

1. 只做 readonly 檢查：`findmnt`、`df`、`systemctl status`、`journalctl`、`dmesg`、pstore 是否仍存在。
2. 確認 SD 掛載；所有新 CSV、trace、build、clone、下載與 ROS log 都寫 SD。
3. 不以 stop/start service 作為一般診斷手段。
4. 若要切換 Agent binary，先設計不需在運行中 stop service 的離線／下次開機方案，並先取得機主同意。

### 優先級 B：不重新編譯的低風險分析

1. 解析現有 RX trace、Agent trace、NX publisher CSV，建立同一個 `TEST_ID` 的時間線。
2. 對照 reliable stream 的 sequence、ACKNACK、retransmit 與 PX4 receipt timestamp。
3. 只讀取 service、UART owner、網路介面與 CPU／memory／I/O 狀態，不進行重啟。
4. 若要測 Wi-Fi 影響，先以不改 Agent、不停止 service 的短 readonly/低負載對照進行，並分離 USB Wi-Fi、TCP QGC、ROS 2 CLI 的流量。

### 優先級 C：需要機主協作的測試

這些測試必須先向機主列出步驟，再由機主操作 QGC／飛控：

- PX4 參數讀取、刷寫、reboot。
- QGC USB/TCP 連線切換。
- 外接 Wi-Fi 天線拔插與 network A/B。
- 戶外 GPS、EKF、mode 與無槳解鎖。
- 任何有槳測試、Offboard arming、setpoint 或自動飛行。

## 10. 重要文件索引

- [`README.md`](README.md)：目前協作入口、摘要與硬體基線。
- [`QGC_LAPTOP_CODEX_HANDOFF_20260814.md`](QGC_LAPTOP_CODEX_HANDOFF_20260814.md)：筆電 QGC Codex 專用交接。
- [`SD_STORAGE_POLICY_20260817.md`](SD_STORAGE_POLICY_20260817.md)：SD-first 儲存規範與 rollback。
- [`evidence/20260813_first_principles_offboard_transport/SUMMARY.md`](evidence/20260813_first_principles_offboard_transport/SUMMARY.md)：Reliable、Best-Effort、hb50 與第一性原理分析。
- [`evidence/20260814_qgc_px4/README.md`](evidence/20260814_qgc_px4/README.md)：QGC Phase A/B 與 RX trace 交接。
- [`evidence/20260814_agent_sequence_trace/README.md`](evidence/20260814_agent_sequence_trace/README.md)：Agent sequence trace patch 與失敗／中止紀錄。
- [`evidence/20260814_nx_kernel_panic/README.md`](evidence/20260814_nx_kernel_panic/README.md)：第一次 kernel panic 與 `cgroup.memory=nokmem`。
- [`evidence/20260817_nx_kernel_panic_key_gc_repeat/README.md`](evidence/20260817_nx_kernel_panic_key_gc_repeat/README.md)：第二次相同 key-GC panic，當前 kernel gate FAIL。
- [`evidence/20260817_storage_cleanup/README.md`](evidence/20260817_storage_cleanup/README.md)：空間清理與 SD 遷移背景。

## 11. 一句話交接結論

P450 已完成 NX、ROS 2 Foxy、PX4 1.14.3、TELEM2/UART0 與 Micro XRCE-DDS 的基本串接；目前真正未解的是 reliable stream 的序列缺洞造成 300–600 ms 級 PX4 receipt gap，以及重複出現的 Jetson 5.10 keyring garbage-collection kernel panic。下一個對話應先維持系統穩定、分析既有證據並使用 SD-first，不能把版本重刷、Agent 50 ms 或地面 GPS 測試誤當成已完成自動飛行條件。
