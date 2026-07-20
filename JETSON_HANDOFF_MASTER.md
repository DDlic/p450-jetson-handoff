# AMOV P450 Jetson Xavier NX 交接總覽

最後更新：2026-07-20（Asia/Taipei）

## 目前狀態

Jetson Xavier NX 已完成 JetPack 5.1.4／L4T R35.6.0 刷寫，並已由 eMMC 成功進入 Ubuntu 圖形介面。

目前不要重新刷 QSPI、不要重新刷 SD，也不要覆蓋原本的 128 GB 舊 microSD。

## 專案目標

AMOV P450 整合：

- Pixhawk 6C
- PX4 v1.14.3
- Jetson Xavier NX
- JetPack 5.1.4／Ubuntu 20.04 宿主
- Ubuntu 22.04／ROS 2 Humble ARM64 容器
- Micro XRCE-DDS Agent、`px4_msgs`、`px4_ros_com`
- 後續 Offboard 起降與飛行資料擷取

建議架構：

```text
Jetson Xavier NX
└─ JetPack 5.1.4 / Ubuntu 20.04（eMMC）
   ├─ NVIDIA kernel、CUDA、Wi-Fi、USB、UART
   ├─ Docker
   └─ Ubuntu 22.04 / ROS 2 Humble ARM64 container
      ├─ Micro XRCE-DDS Agent
      ├─ px4_msgs
      ├─ px4_ros_com
      └─ Offboard 節點
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

## 後續工作順序

1. 驗證 L4T、Ubuntu、Kernel 與 eMMC root device。
2. 驗證 Ethernet、Wi-Fi、SSH 與重開機後網路恢復。
3. 連接 Pixhawk 6C，確認 USB/UART 裝置與權限。
4. 建立 Ubuntu 22.04／ROS 2 Humble ARM64 容器。
5. 安裝與測試 Micro XRCE-DDS Agent。
6. 建置 `px4_msgs`、`px4_ros_com`。
7. 驗證 `/fmu/out/*` topic 與 PX4 ULog。
8. 無槳測試 Kill Switch、定高、定點、EKF 與失聯處置。
9. 最後才進行起飛、短暫停留、降落與 Offboard 測試。

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
