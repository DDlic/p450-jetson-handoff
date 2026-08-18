# AMOV P450 Jetson Xavier NX 交接總覽

最後更新：2026-08-17（Asia/Taipei）

> **2026-08-17 交付期 PoC 入口**：若機主因交付期限只要求一次
> `起飛 1 m → 前進 5 m → Land` 的受控展示，下一個 NX CLI 必須先讀
> [`P450_DELIVERY_POC_OFFBOARD_RUNBOOK_2026-08-17.md`](../runbooks/P450_DELIVERY_POC_OFFBOARD_RUNBOOK_2026-08-17.md)。
> 文件已納入 `Takeoff detected/not landed` 的 v1.14.3 狀態機原因、601.548 ms heartbeat
> receipt gap 的實際風險、固定 position waypoint、VehicleCommandAck、PX4 Land mode、
> fail-safe 與逐級測試流程。這條 PoC 路徑不代表 transport freshness 或 NX kernel gate
> PASS，也不授權 CLI 自行裝槳、改參數或解鎖。

> **目前權威決策**：最終 PX4 版本固定為 v1.14.3；v1.15.4 只作診斷，不能成為
> 最終韌體。任何有效的 XRCE 修改都必須回補至 v1.14.3 後重新驗收。現階段唯一
> 優先是 XRCE 雙向穩定，完成前不進行室外 GPS 或飛行測試。2026-08-10 的 Phase A、
> 10 分鐘純接收及 2 Hz 雙向測試已完成；目前停在 PX4→NX PASS、NX→PX4 新鮮度
> FAIL。下一個 v1.14.3 候選版尚未取得刷寫授權。下方 v1.15.4 內容均為歷史診斷紀錄。

## 目前狀態

### 2026-08-10 最新通訊停止點

- 實際韌體：PX4 v1.14.3，source `f9bc66c6f30d8ddcceaeba2545dc9f6d0e71faf1`，
  `p450-pixhawk6c-v1.14.3-xrce-ping-fix-f9bc66c6f3.px4`。
- 正式 10 分鐘純接收：42,718 筆、71.196 Hz、最大 gap 38.913 ms、0 次超過
  100 ms；Agent PID 與 restart count 不變，PASS。
- 2 Hz 非控制輸入期間，PX4→NX 輸出仍穩定（60 秒最大 gap 37.397 ms），但 QGC
  在 NX 持續發布時看到相同 uORB marker 已落後 58.383400 秒，故雙向新鮮度 FAIL。
- message definitions、NX 本地 publisher／DDS、Agent DataReader 與 Agent serial
  write call 已逐層排除；PX4 最終曾收到正確 marker，因此不是完全斷線，而是活
  session 內的接收飢餓或極端延遲。
- 所有測試 publisher 已停止，systemd Agent 已恢復正常。未執行 20 Hz、Offboard、
  解鎖或飛行，也未刷下一版候選韌體。

完整報告：
[`P450_PX4_V1143_PING_BIDIRECTIONAL_TEST_2026-08-10.md`](../reports/2026-08-10/P450_PX4_V1143_PING_BIDIRECTIONAL_TEST_2026-08-10.md)。
原始證據：
[`evidence/20260810_163557_px4_v1143_ping_postflash/`](../../evidence/20260810_163557_px4_v1143_ping_postflash/)。

Jetson Xavier NX 已完成 JetPack 5.1.4／L4T R35.6.0 刷寫，並已由 eMMC 成功進入 Ubuntu 圖形介面。

ROS 2 離線包已在 Ubuntu 桌機完成只讀檢查；2026-07-23 已改用在線方式在 Ubuntu 20.04 宿主完成原生 ROS 2 Foxy 安裝與驗證。離線包仍保留作為備援。

目前不要重新刷 QSPI 或 eMMC。側邊 128 GB microSD 已清除舊開機映像並改為單一 ext4 `P450_DATA` 資料碟。

2026-07-28 已確認 AMOV AllSpark 外殼 `UART0` 對應 `/dev/ttyTHS1`，不是先前測試的 `/dev/ttyTHS0`。Pixhawk `TELEM2` 已能與 Micro XRCE-DDS Agent 建立 session，ROS 2 可發現 23 個 `/fmu/*` topics 並讀取即時 IMU／里程計資料。Agent 已由 `p450-micro-xrce-agent.service` 常駐及開機啟動。

原廠 PX4 1.14.3 client 曾主動刪除並重建 session。將 TELEM2 與 NX Agent 從 921600 同步降至 460800 後，session 存活時間由約 2.7–4.8 秒改善至約 10–23 秒，但 68 秒內仍重建 5 次；低日誌模式 65 秒 IMU 監測的最大資料空窗為 1614 ms。協定追蹤顯示 NX Agent 有快速送出回覆，提升 Agent 排程優先度及測試性重送 pong 都未消除問題。這是回補韌體刷入前的歷史基準。

2026-07-29 改用飛控 USB-only 供電複測，120 秒收到 7110 筆 IMU，平均 59.233 Hz，但最大空窗 2904.859 ms，10 次超過 1 秒；65 秒 Agent 詳細日誌中建立 10 次、關閉 9 次 session，已關閉 session 約存活 3.1–16.7 秒。USB 供電沒有消除重連，低電壓主電池不是唯一原因。測試切回 systemd Agent 後，PX4 client 一度沒有自行恢復 DDS entities；由 QGC 重啟 Vehicle 後已恢復 23 個 `/fmu/*` topics，但 18 秒內仍出現 `23 → 2 → 16 → 23`，QGC 的 `Running, disconnected` 是重連循環中的瞬間狀態。

重啟後的導航抽樣顯示 GPS `fix_type=0`、0 顆衛星、水平位置／速度無效、航向不適合控制、dead reckoning 啟用；姿態可持續讀取，但 45 秒沒有 TimesyncStatus 樣本。PX4 v1.14 官方文件說明 XRCE-DDS 已自動處理 Agent／client 時間同步，因此缺少獨立 TimesyncStatus 樣本不是額外阻塞條件。當時未解鎖且 Offboard disabled；XRCE session、定位、速度與航向仍未達自動飛行條件。

PX4 v1.14.3 官方 `VehicleIMU.cpp` 還漏掉 `delta_angle_clipping` 的設定與重置，造成 ROS 2 `SensorCombined.gyro_clipping` 為未初始化隨機值；v1.15 已補齊。message definitions 已逐行核對一致，這不是 `px4_msgs` 版本錯配，也不是 UART payload 損壞的證據。此欄位在目前韌體不可用於安全判斷。

PX4 官方提交 `a1cce7e961df`（`uxrce_dds_client: optimizations and instrumentation`）包含：有效雙向資料流時略過 session ping、將 ping timeout 放寬為 1 秒、縮短／調整 client loop。2026-07-29 已將其中 session ping 的最小修改回補至 v1.14.3，成功建置 `PX4FMUv6C` 韌體；成品位於 SD 的 `/media/p450/P450_DATA/builds/firmware/p450-pixhawk6c-v1.14.3-xrce-ping-fix-f9bc66c6f3.px4`，SHA-256 為 `cb14d73274014385e809645dd3525e1ce0e33cf5d648c7d23324c41b822bf0bd`。

2026-08-03 機主已完成參數備份、刷入上述韌體及參數恢復。10 分鐘常駐 Agent 測試收到 42,936 筆 IMU，最大 gap 56.263 ms，0 次超過 100 ms，Agent PID 全程不變；120 秒詳細 Agent 測試為 `create_client=1`、`established=1`、`delete_client=0`、`closed=0`，最大 gap 35.617 ms。恢復 systemd Agent 後 30 秒測試最大 gap 33.134 ms。XRCE 週期性 session 重建在目前地面測試條件下已消除，通訊穩定性關卡通過；這不代表 GPS、preflight、failsafe、Offboard 或飛行測試已通過。

2026-08-04 已改刷官方 PX4 v1.15.4 source build，並建立對齊的 `px4_msgs release/1.15`
工作區。43 個 DDS message types 全部逐一相符；NX 可建立 43 個 `/fmu/*` topics。
但 60 秒純接收最大 gap 約 1.015 秒，多個 outputs 與 PX4 source timestamp 會在同一
時刻一起跳過約 1 秒。45 秒 Agent v6 只有一次 session 建立，沒有 close/recreate，
表示異常發生在仍連線的 client loop 內。停用 `UXRCE_DDS_SYNCT` 也沒有改善；2 Hz
非控制 status 已到達 Agent，但空窗不變，20 Hz 更會使 PX4 輸出停止直到 Agent 重啟。

2026-08-05 進一步對照 PX4 release tags 與最新上游修正：v1.15.4、v1.16.2、
v1.17.0 的 client loop 都仍只執行一次非阻塞 session；v1.18 development 的官方
`3169dc6` 才重新加入每輪最多 10 次的 inbound burst draining、1 ms poll 與 output
buffer 改善。這與本機 20 Hz NX→PX4 輸入造成活 session 停止輸出的症狀高度吻合。
現有 `d12a7dd` 候選版仍可作最小 A/B，但不等於新版完整修正。完整版本矩陣、FTDI
隔離路徑、NX CLI 命令與停止條件見
[`P450_PX4_NX_XRCE_ROOT_CAUSE_AND_TEST_PLAN_2026-08-05.md`](../reports/2026-08-05/P450_PX4_NX_XRCE_ROOT_CAUSE_AND_TEST_PLAN_2026-08-05.md)。

上述結果與 PX4 官方 `d12a7dd11d` 所述的 XRCE input 每輪只處理一次、造成接收顯著
延遲相符。已建立 v1.15.4 最小接收排空候選韌體
`firmware/p450-pixhawk6c-v1.15.4-xrce-rx-drain-996b1df7a1.px4`，SHA-256 為
`dbfd43085bbb4fe59744ad244a973b1243fb55d34ed36df52c9a0855be464949`。2026-08-05
機主已刷入此候選版；保留 `UXRCE_DDS_SYNCT=0` 的 60 秒純接收仍有 1005.408 ms
最大 gap、22 次超過 500 ms、7 次超過 1 秒，第一關即 FAIL，因此沒有繼續 2 Hz／
20 Hz 輸入。XRCE／Offboard 關卡仍為 FAIL。完整結果見
`docs/reports/2026-08-04/P450_PX4_V1154_XRCE_TEST_2026-08-04.md`。

2026-08-05 已完成 Phase 4 第二代 v1.15.4 候選版：source `3f118ef593`，只回移植
上游 `3169dc6` 中與 serial 共用的 1 ms poll、pending-input 零等待、`FIONREAD`
bounded drain、output buffer flush/retry 與 fd close ownership。clean build
`1233/1233` 成功，image `1,961,772 / 1,966,080` bytes，`board_id=56`，SHA-256
`cb54e73327c95f2ceb0dbd9d53c5020b9d8c76cf1c045600e6c66106576dd660`。目前尚未刷入或
實機驗證；完整脈絡與簡報答辯資料見
`docs/reports/2026-08-05/P450_COMPLETE_ENGINEERING_TIMELINE_AND_PRESENTATION_2026-08-05.md`。

同日後續無槳控制檢查確認三段 RC 模式為 STAB／ALTCTL／POSCTL；POSCTL 因室內沒有有效 local/global position 與 Home 而不通過 preflight。移除發射機電池超過 20 秒後，飛控仍回報 `manual_control_signal_lost=false`，與接收機失聯 Hold 輸出相符，RC loss 關卡為 FAIL。ROS→PX4 的 `VehicleCommand` 已能由 NX 將 STAB 切至 ALTCTL，但外部 ARM 未被接受，且 Offboard 零推力心跳會間歇被判為 lost。詳細 Agent v6 記錄證明 1491 組心跳／rate setpoint 全數由 DDS 收到並寫入 UART，沒有 Agent error、warning 或 session 重建；異常已縮小到飛控端 XRCE 收件／uORB 新鮮度判定。2026-08-04 已確認 `COM_OF_LOSS_T=1.0 s`，不是 timeout 過短；PX4 uORB 內最新 heartbeat 曾落後約 0.724 秒。所有解鎖／馬達測試均被 watchdog 安全中止，飛控最終為 STAB、未解鎖、馬達未轉；詳見 `docs/reports/2026-08-03/P450_POSTFLASH_XRCE_TEST_2026-08-03.md`。

同日也針對 Jetson `3110000.serial` 的 460800 baud out-of-range kernel 錯誤建立 UARTB device-tree 修正。預設 DTB 現為 `/boot/dtb/p450-p3668-0001-p3509-0000-sdmmc3-wifi-uartb460800.dtb`，舊 DTB 保留為 fallback；重啟後 kernel 錯誤消失。但修正後 120 秒測試最大空窗仍為 3129 ms、28 次超過 1 秒，再次重啟後 60 秒最大空窗 3382 ms、15 次超過 1 秒。因此 DTB 修正有效排除主機設定錯誤，卻不是 XRCE session 重建的最終解法。

側邊 `P450_DATA` 已恢復為可寫 ext4，並以 UUID 寫入 `/etc/fstab` 固定掛載於 `/media/p450/P450_DATA`。已建立 `rosbags/`、`ulog/`、`builds/`；eMMC 保留程式與 ROS workspace，大型資料改存 SD。2026-07-29 建置完成後 eMMC 使用 66%、尚有 4.5 GB，SD 使用 3%、尚有 108 GB；PX4 source、工具鏈、build 與韌體都放在 SD。

### 2026-07-22 最新硬體檢查

- 目前根檔案系統仍是 eMMC `/dev/mmcblk0p1`，沒有把任何 SD 卡設為開機 root。
- 內建側邊 SD 控制器已透過 `/boot/extlinux/extlinux.conf` 的 `sd-force` 預設項目啟用；同一份設定保留 `sd-enabled` 與 `original` 回退項目。force-probe device tree 已安裝，但尚待下一次重開機驗證。
- 在一般 card-detect 模式下，側邊槽插入 128 GB 與 512 GB 卡都沒有產生 `/dev/mmcblk1`。`mmc1` host 存在，但 `PG.07` card-detect 腳位持續為 high（該訊號為 active-low）。這表示目前不能把問題判定為容量或檔案系統問題。
- 512 GB 卡經 USB Hub 內的讀卡機可正常辨識為 `/dev/sda`，容量約 500 GB；可讀到 Ubuntu 20.04.6 與 L4T R35.6.0，檔案系統未留在掛載狀態。`sgdisk -v`／`fdisk` 顯示 GPT 備份表沒有位於裝置末端，符合小容量 Jetson 映像複製到較大媒體的情況；目前未執行修復或寫入。
- USB 手機網路在最近一次重開機後可快速連線。USB RNDIS 介面名稱可能是 `usb0` 或 `usb1`，不可在腳本中硬編碼其中一個名稱。

上述 SD force-probe 設定只用於偵測側邊卡，不改變 eMMC 開機來源。驗證前不要執行 `dd`、格式化、`sgdisk -e` 或任何會寫入 512 GB 卡的修復命令。

## 本週目標與執行順序（2026-07-23）

本週大目標：使用 Jetson 宿主上的原生 ROS 2 Foxy 完成一次自動飛行實驗，第一階段只做起飛、短暫停留、降落。

執行順序與通過條件：

1. **先驗證 Pixhawk ↔ NX 直接通訊**：優先插接 Pixhawk USB，確認 NX 穩定產生 serial 裝置；若改用 UART，必須先確認 P450 實際腳位、電壓與線序，不猜測 `/dev/ttyTHS*` 對應。
2. **再處理 ROS 2 Foxy**：已完成原生安裝與 `ros2` 基礎檢查。
3. **建立 PX4 ROS 2 通道**：已完成 Micro XRCE-DDS Agent、`px4_msgs`、`px4_ros_com` 建置，也已建立 UART session 與 `/fmu/*` topics；尚待排除週期性 session 重建。
4. **無槳驗證資料流與控制流程**：通訊連續穩定後，再確認模式切換、Kill Switch 與失聯處置。
5. **最後才做一次自動飛行實驗**：拆槳完成地面測試後，才在安全場地執行起飛、短暫停留、降落。

目前已知的 QGC TCP/MAVLink 路徑只證明 P450 網路與 Pixhawk 可通訊，不代表 NX 已經完成 USB/UART 或 uXRCE-DDS 驗證。

## 專案目標

AMOV P450 整合：

- Pixhawk 6C
- PX4 v1.14.3
- Jetson Xavier NX
- JetPack 5.1.4／Ubuntu 20.04 宿主
- ROS 2 Foxy 原生在線安裝環境（目前方案；離線包作為備援）
- Ubuntu 22.04／ROS 2 Humble ARM64 容器（只有需要 Humble 專案時才評估）
- Micro XRCE-DDS Agent、`px4_msgs`、`px4_ros_com`
- 後續 Offboard 起降與飛行資料擷取

建議架構：

```text
Jetson Xavier NX
└─ JetPack 5.1.4 / Ubuntu 20.04（eMMC）
   ├─ NVIDIA kernel、CUDA、Wi-Fi、USB、UART
   ├─ ROS 2 Foxy（原生、在線安裝）
   │  ├─ Micro XRCE-DDS Agent
   │  ├─ px4_msgs
   │  ├─ px4_ros_com
   │  └─ Offboard 節點
   └─ 可選：Ubuntu 22.04 / ROS 2 Humble ARM64 container
```

## 已確認硬體身份

目前以 Recovery EEPROM 與成功刷寫日志為準：

```text
Board ID: 3668
Board version: 301
Board SKU: 0001
Board revision: G.0
SoC: Tegra 194
Carrier/device-tree family: P3509-0000
```

實際模組是 P3668-0001 eMMC 版本。先前交接文件根據舊系統 device-tree 記載的 P3668-0000 microSD 判斷已被新的 Recovery EEPROM 證據取代；後續不得再使用舊判斷。

NVIDIA 對應的刷寫設定：

```text
正確：jetson-xavier-nx-devkit-emmc
儲存目標：mmcblk0p1
不要使用：jetson-xavier-nx-devkit-qspi 作為完整系統刷寫設定
```

## 主機與 BSP

```text
Host: Ubuntu 22.04.5 LTS x86_64
BSP: Jetson Linux R35.6.0
BSP path: /home/wilson/nvidia/JP514/Linux_for_Tegra
Rootfs archive: /home/wilson/下載/Tegra_Linux_Sample-Root-Filesystem_R35.6.0_aarch64.tbz2
```

主機已安裝：

```text
python-is-python3
python -> Python 3.10.12
```

## 已完成工作

### 1. 修復 BSP rootfs

原本 `Linux_for_Tegra/rootfs` 不完整，`etc` 是錯誤的普通檔案，且缺少 `bin`、`lib` 等目錄，導致完整 system image 無法可靠產生。

已重新解壓官方 R35.6.0 sample rootfs，並完成：

```bash
sudo ./apply_binaries.sh
```

結果：

```text
L4T BSP package installation completed!
Success!
```

### 2. QSPI-only 刷寫

曾完成 QSPI-only 刷寫，確認 R35.6.0 UEFI、BCT、bootloader 與相關韌體可寫入 QSPI。

修復 Python 後，`qspi_bootblob_ver.txt` 已產生有效 CRC32：

```text
BYTES:85 CRC32:9DE52483
```

### 3. 判定 eMMC 儲存媒體

UEFI Shell 執行 `map -r` 時顯示：

```text
eMMC(0x0)
FS2:
BLK0 ～ BLK13
```

進入 `FS2:` 後可看到完整舊 Linux rootfs，表示 eMMC 不是空白媒體。舊 eMMC rootfs 與新的 R35.6.0 QSPI 不匹配，因此無法正常啟動。

### 4. eMMC 完整刷寫

使用：

```bash
cd ~/nvidia/JP514/Linux_for_Tegra
sudo ./flash.sh jetson-xavier-nx-devkit-emmc mmcblk0p1 \
  2>&1 | tee ~/xavier_nx_emmc_clean.log
```

日志確認：

```text
Name: jetson-xavier-nx-devkit-emmc
flash_l4t_t194_spi_emmc_p3668.xml
system.img built successfully.
Writing partition APP with system.img
Writing partition esp with esp.img
Flashing completed
*** The target t186ref has been flashed successfully. ***
Coldbooting the device
```

完成後 Jetson 已由 eMMC 進入 Ubuntu 圖形介面。

## 失敗原因總結

先前無法開機不是單一 SD 卡故障，主要原因為：

1. 實際硬體 SKU 是 P3668-0001 eMMC 版本。
2. 先前只刷 QSPI，沒有寫入 eMMC 的 APP/rootfs。
3. eMMC 內原有舊版 Linux，與 R35.6.0 bootloader 不匹配。
4. BSP rootfs 原先不完整。
5. 主機原先缺少 `python` 命令，造成 QSPI CRC32 欄位空白。

## 舊 SD 卡與映像

- 原本 128 GB microSD 在早期排查時曾要求保留；2026-07-28 已依機主明確指示
  清除舊映像並改為單一 ext4 `P450_DATA` 資料碟。
- JP514 SD 映像測試屬於歷史排查，不是目前開機媒體。
- 目前成功開機來源是 eMMC；側邊卡只作為資料碟，不要用它判斷 eMMC 開機。

## Ubuntu 初次開機後驗證

完成 Ubuntu 初始設定後，在 Jetson 執行：

```bash
cat /etc/nv_tegra_release
cat /etc/os-release
uname -a
findmnt /
lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINTS
```

預期：

```text
L4T R35.6.0
Ubuntu 20.04
Kernel 5.10.216-tegra
根檔案系統位於 eMMC
```

## ROS 2 離線包現況

USB 內的 `ROS2` bundle 與 Jetson 目前系統相容：目標為 Ubuntu 20.04 Focal、ARM64、JetPack 5／L4T R35.6.0。實際檢查結果為 360 個 Debian 套件（261 個 arm64、99 個 all），manifest 與檔案數量一致。

USB 上的 `git_2.25.1-1ubuntu3_arm64.deb` 為有效 Debian 套件，大小 1,456,282 bytes，SHA256 為：

```text
c637afbaf34e2bffe59fac5f0e0a622026e85729f267ce0ef99353a5e52d5f34
```

筆電先前在 NX 使用的 537,262-byte 檔案是截短副本，不是 USB 原始檔。後續必須從 USB 重新複製，並在 NX 上用 `stat`、`sha256sum`、`dpkg-deb --info` 驗證後才安裝。安裝指令需加入 `--no-install-recommends`，避免離線環境因未收錄的建議套件中止。

這份包是 ROS 2 Foxy，不是 Humble；不要在 Ubuntu 22.04 或 x86_64 環境安裝。

## 後續工作順序

1. 驗證 L4T、Ubuntu、Kernel 與 eMMC root device。
2. 驗證 Ethernet、Wi-Fi、SSH 與重開機後網路恢復。
3. 從 USB 重新複製 ROS 2 Foxy 離線包至 eMMC，完成完整性驗證。
4. 原生安裝並驗證 ROS 2 Foxy。
5. 建置 Micro XRCE-DDS Agent、`px4_msgs`、`px4_ros_com`。
6. 先連接 Pixhawk 6C，完成 NX 直接通訊驗證，再確認 USB/UART、uXRCE-DDS 參數與通道。
7. 驗證 `/fmu/out/*` topic 與 PX4 ULog。
8. 無槳測試 Kill Switch、定高、定點、EKF 與失聯處置。
9. 若學長專案強制要求 Humble，再另行建立 ARM64 Humble 容器；不升級宿主 Ubuntu。
10. 最後才進行起飛、短暫停留、降落與 Offboard 測試。

## 相關日志

日志因 `.gitignore` 排除，保留在主機：

```text
/home/wilson/xavier_nx_qspi_rerun.log
/home/wilson/xavier_nx_qspi_clean.log
/home/wilson/xavier_nx_emmc_clean.log
```

週報摘要見 `docs/reports/2026-07-20/P450_PROGRESS_2026-07-20.md`。

## 安全規則

- 不要使用 Orin BSP 或 Orin 映像。
- 不要執行舊系統內的 `/dev/mtd0` QSPI 寫入方法。
- 128 GB 側邊卡目前是 `P450_DATA`；不要再刷入開機映像或對未確認裝置格式化。
- 不要在未確認儲存目標前執行完整刷寫。
- 飛行測試前必須拆槳或固定機體。

## 官方參考

- [NVIDIA Jetson Linux Quick Start](https://docs.nvidia.com/jetson/l4t/Tegra%20Linux%20Driver%20Package%20Development%20Guide/quick_start.html)
- [NVIDIA Jetson Linux R35.6.0 Rootfs](https://docs.nvidia.com/jetson/l4t/Tegra%20Linux%20Driver%20Package%20Development%20Guide/rootfs_custom.html)
- [NVIDIA Jetson Linux R35.6.0 Flashing Support](https://docs.nvidia.com/jetson/archives/r35.6.0/DeveloperGuide/SD/FlashingSupport.html)
