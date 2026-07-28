# AMOV P450 Jetson Xavier NX 交接總覽

最後更新：2026-07-28（Asia/Taipei）

## 目前狀態

Jetson Xavier NX 已完成 JetPack 5.1.4／L4T R35.6.0 刷寫，並已由 eMMC 成功進入 Ubuntu 圖形介面。

ROS 2 離線包已在 Ubuntu 桌機完成只讀檢查；2026-07-23 已改用在線方式在 Ubuntu 20.04 宿主完成原生 ROS 2 Foxy 安裝與驗證。離線包仍保留作為備援。

目前不要重新刷 QSPI 或 eMMC。側邊 128 GB microSD 已清除舊開機映像並改為單一 ext4 `P450_DATA` 資料碟。

2026-07-28 已確認 AMOV AllSpark 外殼 `UART0` 對應 `/dev/ttyTHS1`，不是先前測試的 `/dev/ttyTHS0`。Pixhawk `TELEM2` 已能與 Micro XRCE-DDS Agent 建立 session，ROS 2 可發現 23 個 `/fmu/*` topics 並讀取即時 IMU／里程計資料。Agent 已由 `p450-micro-xrce-agent.service` 常駐及開機啟動。

目前 PX4 1.14.3 client 約每 2.7–4.8 秒主動刪除並重建 session；協定追蹤顯示 NX Agent 有快速送出回覆，提升 Agent 排程優先度也未改善。因此通訊已打通但尚未穩定，不可進入 Offboard 或自動飛行。

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

- 原本 128 GB 舊 microSD 保留，不得格式化。
- JP514 SD 映像測試屬於歷史排查，不是目前開機媒體。
- 目前成功開機來源是 eMMC，不要重新插入 SD 來判斷本次 eMMC 是否正常。

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

週報摘要見 `P450_PROGRESS_2026-07-20.md`。

## 安全規則

- 不要使用 Orin BSP 或 Orin 映像。
- 不要執行舊系統內的 `/dev/mtd0` QSPI 寫入方法。
- 不要格式化 128 GB 舊 microSD。
- 不要在未確認儲存目標前執行完整刷寫。
- 飛行測試前必須拆槳或固定機體。

## 官方參考

- [NVIDIA Jetson Linux Quick Start](https://docs.nvidia.com/jetson/l4t/Tegra%20Linux%20Driver%20Package%20Development%20Guide/quick_start.html)
- [NVIDIA Jetson Linux R35.6.0 Rootfs](https://docs.nvidia.com/jetson/l4t/Tegra%20Linux%20Driver%20Package%20Development%20Guide/rootfs_custom.html)
- [NVIDIA Jetson Linux R35.6.0 Flashing Support](https://docs.nvidia.com/jetson/archives/r35.6.0/DeveloperGuide/SD/FlashingSupport.html)
