# AMOV P450／Jetson Xavier NX 專案交接文件

更新日期：2026-07-20

## 給接手 GPT 的指示

本文件保留早期排查內容；目前權威狀態請先閱讀 `JETSON_HANDOFF_MASTER.md` 與 `P450_PROGRESS_2026-07-20.md`。不要重新猜硬體型號，也不要重複已完成的刷機。

目前已完成 BSP rootfs 修復、QSPI 刷寫與 eMMC 完整刷寫，Jetson 已由 eMMC 成功進入 Ubuntu 圖形介面。後續工作是驗證 Ubuntu、網路、Pixhawk、ROS 2 與 PX4。

不要讓使用者在舊系統執行 `flash_eraseall /dev/mtd0`，因為目前舊系統沒有 `/dev/mtd0`。

## 專案目標

- 飛控：Pixhawk 6C
- 飛控韌體：PX4 v1.14.3
- 機載電腦：Jetson Xavier NX Developer Kit
- 目標底層：JetPack 5／Ubuntu 20.04
- ROS 目標：ROS 2 Humble
- ROS 執行方式：Ubuntu 20.04 宿主上的 ARM64 Docker 容器
- 後續套件：Micro XRCE-DDS Agent、`px4_msgs`、`px4_ros_com`
- 後續功能：PX4／ROS 2 通訊、Offboard 起降、定高／定點資料擷取

## 已確認硬體

```text
模組：Jetson Xavier NX Developer Kit
模組料號：P3668-0001
參考載板：P3509-0000
SoC：Tegra194
```

歷史舊系統的 `/proc/device-tree/model` 和 `compatible` 曾顯示：

```text
NVIDIA Jetson Xavier NX Developer Kit
nvidia,p3509-0000+p3668-0000
nvidia,tegra194
```

Recovery EEPROM 與成功刷寫日志後續確認 Board ID 3668、SKU 0001、revision G.0；目前以 P3668-0001 eMMC 身份為準，舊 P3668-0000 判斷已過時。

## 登入資料

以下資料僅限使用者授權的專案交接使用，請勿公開張貼：

```text
帳號：prometheus
密碼：prometheus.
```

密碼最後的句點 `.` 是密碼內容的一部分。

## 舊系統狀態

原本 128 GB microSD 卡仍保留，曾經正常從此卡開機：

```text
Ubuntu：18.04.6 LTS
L4T：R32.4.4
JetPack 世代：JetPack 4.4
Kernel：4.9.140-tegra
根分割區：/dev/mmcblk0p1
儲存裝置：128 GB microSD
NVMe：目前沒有偵測到
```

## 已完成工作

### Windows 與 SD 卡

- 已安裝 balenaEtcher。
- 已下載 `JP514-xnx-sd-card-image_b11.zip`。
- Kingston 512 GB microSD 已完成燒錄；Etcher 完整 Validate 狀態尚未另外記錄。
- 原本 128 GB SD 卡仍保留，沒有覆寫。

### 刷寫完成狀態

已使用 R35.6.0 BSP 完成 QSPI 與 eMMC 刷寫：

```text
JetPack 5.1.4／L4T R35.6.0
```

完整 eMMC 刷寫命令：

```bash
sudo ./flash.sh jetson-xavier-nx-devkit-emmc mmcblk0p1
```

結果：

```text
system.img built successfully.
Flashing completed
*** The target t186ref has been flashed successfully. ***
```

## QSPI 診斷結果

在舊 Ubuntu 18.04 系統執行：

```bash
cat /proc/mtd
```

結果只有標題，沒有任何 MTD 裝置：

```text
dev:    size   erasesize   name
```

執行：

```bash
ls -l /dev/mtd* /dev/mtd/by-name 2>/dev/null
```

沒有輸出，代表沒有 `/dev/mtd0`。

工具本身存在：

```text
/usr/sbin/flash_eraseall
/usr/sbin/flashcp
```

但工具存在不等於 QSPI 裝置存在。

執行 `dmesg` 篩選後只看到 SD 卡 tuning、HDMI 顯示等訊息，沒有 `mtd`、`qspi`、`spi-nor` 或 `nor` 裝置初始化訊息。

### 診斷結論

USB 隨身碟被舊系統讀到，與 QSPI 是兩件不同的事：

```text
USB 隨身碟：一般區塊儲存裝置，通常是 /dev/sda
QSPI：Jetson 模組上的內部 NOR Flash，應該是 /dev/mtd0
```

目前舊 L4T R32.4.4 Kernel 沒有把 QSPI 暴露成 `/dev/mtd0`，所以不能在舊系統直接執行：

```bash
sudo flash_eraseall /dev/mtd0
sudo flashcp ... /dev/mtd0
```

不要把 QSPI 檔案寫入 `/dev/sda)、USB 隨身碟或 SD 卡。

## Wi-Fi 狀態

舊系統可辨識：

```text
Wi-Fi：Intel Wireless-AC 8265
介面：wlan0
驅動：iwlwifi
Firmware：已載入 22.391740.0
```

但舊系統曾顯示：

```text
wlan0：unavailable
Hard blocked：yes
```

這表示舊系統在重灌前就已有 Wi-Fi 硬體封鎖問題。這不是目前 QSPI 主線，重灌後再驗證 Wi-Fi AP／基地台即可，不要讓此問題阻塞刷機。

## 歷史排查與目前停點

```text
Windows：Kingston 512 GB SD 卡曾燒錄測試，非目前開機來源
舊 128 GB SD 卡：仍保留
舊 eMMC rootfs：已被 R35.6.0 eMMC 刷寫覆蓋
QSPI：已更新成功
eMMC：已完成 APP、kernel、recovery、ESP 與韌體分割區刷寫
Ubuntu 桌機：Ubuntu 22.04，已完成刷寫作業
Jetson：已成功進入 Ubuntu 圖形介面
```

目前不要：

- 不要再執行 `/dev/mtd0` 指令。
- 不要格式化 128 GB 舊卡。
- 不要把 SD 卡當成目前 eMMC 開機問題的解決方案。
- 不要選 Orin NX／Orin Nano 的 BSP 或刷機設定。
- 不要在 QSPI 完成前進行飛行測試。

## 歷史步驟：Ubuntu 主機更新 QSPI（已完成，不要重複）

### 1. 下載匹配 BSP

在 Ubuntu 桌機開啟：

<https://developer.nvidia.com/embedded/jetson-linux-r3561>

在 Xavier modules and developer kits 區域下載：

```text
Driver Package (BSP)
```

預期檔名類似：

```text
jetson_linux_r35.6.1_aarch64.tbz2
```

### 2. 解壓縮 BSP

```bash
mkdir -p ~/jetson-r35
cd ~/jetson-r35
tar -xpf ~/Downloads/jetson_linux_r35.6.1_aarch64.tbz2
ls -ld Linux_for_Tegra
```

若檔名不同，先查看：

```bash
ls ~/Downloads | grep -i jetson
```

### 3. 進入 Force Recovery

當 BSP 已準備好後：

1. 讓 NX 正常關機。
2. 取出目前的 128 GB 舊 SD 卡，先不要插 Kingston 新卡。
3. 使用可傳輸資料的 USB 線，把 Ubuntu 桌機連到 Xavier NX 的 recovery／flash USB 埠。
4. 按住 RECOVERY，再按一下 RESET，稍候放開 RECOVERY。
5. 在 Ubuntu 桌機執行：

```bash
lsusb | grep -i nvidia
```

預期看到類似：

```text
0955:7019 NVIDIA Corp. APX
```

只有確認主機能看到 NVIDIA APX 後，才執行刷機命令。

### 4. 只更新 QSPI

已確認硬體是 P3509-0000 + P3668-0000。NVIDIA BSP 中有 QSPI-only 設定，例如：

```text
p3509-0000+p3668-0000-qspi.conf
jetson-xavier-nx-devkit-qspi.conf
```

下一個 GPT 應先確認 BSP 內實際存在的設定檔，再使用 QSPI-only 設定。不要使用會同時重刷整個 SD 的設定，除非使用者明確同意。

### 5. QSPI 成功後

1. 關閉 NX。
2. 插入已燒錄的 Kingston 512 GB microSD。
3. 開機完成初始設定。
4. 檢查：

```bash
cat /etc/os-release
cat /etc/nv_tegra_release
uname -a
lsblk
```

預期方向：

```text
Ubuntu 20.04
L4T R35.6.x
Kernel 5.10
```

## 預定軟體架構

```text
Jetson Xavier NX
└─ JetPack 5／Ubuntu 20.04 宿主
   ├─ NVIDIA Kernel、CUDA、Wi-Fi、USB、UART
   ├─ Docker
   └─ Ubuntu 22.04／ROS 2 Humble ARM64 容器
      ├─ Micro XRCE-DDS Agent
      ├─ px4_msgs
      ├─ px4_ros_com
      └─ Offboard 節點
```

不要一開始在 Xavier NX 上直接執行 Ubuntu 20.04 → Ubuntu 22.04 原地升級。這是非官方路線，可能破壞 NVIDIA 驅動、GUI、CUDA 或 Docker。現在選擇容器路線，是為了保留 JetPack 5 的硬體支援。

## 後續測試順序

1. JetPack／L4T／Kernel。
2. SD 容量與根分割區。
3. Wi-Fi 晶片、基地台、SSH、重開機後自動恢復。
4. Pixhawk USB 或 UART 實際連接埠。
5. Docker 與 ARM64 ROS 2 Humble 容器。
6. ROS 2 talker/listener。
7. Micro XRCE-DDS Agent。
8. PX4 ROS 2 topic，例如 `/fmu/out/*`。
9. 無槳測試緊急撥桿與失聯處置。
10. 讀取定高、定點、氣壓計、姿態、速度與 EKF 資訊。
11. 第一次自動飛行只做起飛、短暫停留、降落。
12. 確認 ROS 訊息與 PX4 ULog 正常後，才進行更複雜的 Offboard 控制。

飛行測試前必須拆槳或固定機體。緊急撥桿使用飛控內部通道，需在無槳狀態實測，不能只依賴理論判斷。

## 官方連結

- JetPack 5.1.5：<https://developer.nvidia.com/embedded/jetpack-sdk-515>
- Jetson Linux 35.6.1 BSP：<https://developer.nvidia.com/embedded/jetson-linux-r3561>
- Jetson Linux 35.6.1 Flashing Guide：<https://docs.nvidia.com/jetson/archives/r35.6.1/DeveloperGuide/SD/FlashingSupport.html>
- NVIDIA SDK Manager 系統需求：<https://docs.nvidia.com/sdk-manager/system-requirements/>
- QSPI 初次更新包：<https://developer.nvidia.com/embedded/l4t/r35_release_v1.0/qspi-img/jetson_xavier_nx_qspi_35.1.tbz2>

## 給下一個 GPT 的最短摘要

這是一台由 Recovery EEPROM 確認為 P3668-0001／P3509-0000 的 Jetson Xavier NX eMMC 版本。舊 128 GB microSD 是 Ubuntu 18.04.6／L4T R32.4.4／Kernel 4.9.140-tegra，仍須保留。Ubuntu 22.04 桌機已完成 R35.6.0 rootfs 修復、Python/CRC32 修復、QSPI 刷寫與 `jetson-xavier-nx-devkit-emmc mmcblk0p1` 完整 eMMC 刷寫；Jetson 現已進入 Ubuntu。後續進行 Ubuntu、網路、Pixhawk、ROS 2、Micro XRCE-DDS 與 PX4 驗證，不要重刷舊卡、不要使用 Orin 設定、不要使用 `/dev/mtd0` 舊方法。
