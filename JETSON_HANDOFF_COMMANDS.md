# Jetson Xavier NX 目前命令與後續作業

最後更新：2026-07-23（Asia/Taipei）

目前 Jetson 已由 eMMC 成功進入 Ubuntu。以下命令是開機後驗證與 P450 後續作業，不要重新執行已完成的刷寫命令。

## A. Ubuntu 與儲存媒體驗證

在 Jetson Ubuntu 執行：

```bash
cat /etc/os-release
cat /etc/nv_tegra_release
uname -a
findmnt /
lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINTS
```

預期方向：

```text
Ubuntu 20.04
L4T R35.6.0
Kernel 5.10.216-tegra
根檔案系統位於 eMMC
```

## B. 網路與 SSH

先檢查裝置與連線：

```bash
ip -br link
ip -br addr
nmcli device status
```

若使用 Ethernet，先確認取得 IP，再從筆電測試：

```bash
ssh <jetson-user>@<jetson-ip>
```

若要建立 Wi-Fi AP，先確認 NetworkManager 與 Wi-Fi 介面正常，再建立 AP；不要在尚未確認基本網路前修改複雜的 systemd 或 NetworkManager 設定。

## C. Pixhawk 6C 連接確認

插入 Pixhawk USB 後，在 Jetson 執行：

```bash
lsusb
dmesg --follow
```

另開終端確認 serial 裝置：

```bash
ls -l /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
groups
```

若使用 UART，先確認實際載板腳位、電壓與線序，不要直接猜測 P450 的 UART header。

通訊測試的通過條件：

- 插入 Pixhawk 後，NX 產生穩定的 `/dev/ttyACM*` 或 `/dev/ttyUSB*`，最好使用 `/dev/serial/by-id/` 的固定名稱。
- 連續觀察至少 60 秒沒有 serial 裝置反覆消失、重連或 USB error。
- 使用能解析 MAVLink 或 uXRCE-DDS 的工具確認心跳／遙測；單純執行 `cat /dev/ttyACM0` 看到亂碼不算通訊通過。
- 記錄實際 transport、裝置名稱與 baud rate；在這些條件完成前，不修改 PX4 參數，也不猜測 UART 腳位。

## D. ROS 2 Foxy 安裝（目前已在線完成；離線包作備援）

2026-07-23 已在 NX 在線完成原生 ROS 2 Foxy 安裝、`rosdep` 依賴檢查、Micro XRCE-DDS Agent v2.4.2、`px4_msgs` 與 `px4_ros_com` 建置。以下離線包命令保留供日後無網路重建使用，目前不需重做。

目前 USB bundle 的目標是 Ubuntu 20.04 Focal、ARM64、JetPack 5／L4T R35.6.0，與 NX 宿主相符。先確認 NX 環境：

```bash
cat /etc/os-release
dpkg --print-architecture
uname -m
```

必須確認為 Ubuntu 20.04、`arm64`、`aarch64`。將 USB 的 `ROS2` 目錄重新複製到 NX 的 `~/Downloads/ROS2`，不要沿用先前已截短的副本。

先驗證曾出錯的套件：

```bash
cd ~/Downloads/ROS2
stat -c '%n %s bytes' deb/git_2.25.1-1ubuntu3_arm64.deb
sha256sum deb/git_2.25.1-1ubuntu3_arm64.deb
dpkg-deb --info deb/git_2.25.1-1ubuntu3_arm64.deb | sed -n '1,20p'
```

預期大小為 `1456282 bytes`，SHA256 為：

```text
c637afbaf34e2bffe59fac5f0e0a622026e85729f267ce0ef99353a5e52d5f34
```

確認後才執行離線安裝：

```bash
cd ~/Downloads/ROS2
sudo apt install --no-download --no-install-recommends ./deb/*.deb \
  2>&1 | tee ~/ros2_foxy_offline_install.log
```

不要執行 `apt update` 或 `apt --fix-broken install`。若再次出現 `Invalid archive`，立即停止並記錄套件檔名、大小與 SHA256；若是 missing package，保留完整錯誤輸出，不要用網路修復。

安裝完成後：

```bash
source /opt/ros/foxy/setup.bash
ros2 --help
ros2 doctor
```

這份包是 Foxy，不是 Humble。只有當後續專案明確要求 Humble 時，才另行處理 ARM64 Humble 容器；不要對 JetPack 宿主執行 `do-release-upgrade`。

## E. Micro XRCE-DDS 與 PX4 驗證順序

1. 確認 ROS 2 Foxy 原生環境可執行。
2. 建置 `px4_msgs`。
3. 建置 `px4_ros_com`。
4. 啟動 Micro XRCE-DDS Agent。
5. 確認 `/fmu/out/*` topic 可持續接收。
6. 保存 PX4 ULog。
7. 無槳測試 Kill Switch、失聯處置與定高/定點資料。
8. 最後才做起飛、短暫停留、降落。

飛行測試前必須拆槳或固定機體。

## F. 已完成的刷寫命令（僅供紀錄，不要重複執行）

### Rootfs BSP 套用

```bash
cd ~/nvidia/JP514/Linux_for_Tegra
sudo ./apply_binaries.sh
```

### QSPI-only

```bash
sudo ./flash.sh jetson-xavier-nx-devkit-qspi internal \
  2>&1 | tee ~/xavier_nx_qspi_clean.log
```

### 最終 eMMC 完整刷寫

```bash
sudo ./flash.sh jetson-xavier-nx-devkit-emmc mmcblk0p1 \
  2>&1 | tee ~/xavier_nx_emmc_clean.log
```

最終 eMMC 刷寫日志必須包含：

```text
system.img built successfully.
Flashing completed
*** The target t186ref has been flashed successfully. ***
```

## G. 重要保存規則

- 側邊 128 GB microSD 已依機主指示清除舊映像並改為 `P450_DATA`；不要再刷入
  開機映像，也不要對未確認裝置執行格式化。
- 不要使用 Orin BSP 或 Orin 映像。
- 不要使用舊系統內的 `/dev/mtd0` 方法。
- 不要把 `jetson-xavier-nx-devkit-qspi` 當作完整 eMMC 系統刷寫設定。
- 不要在未確認裝置名稱前使用 `dd`、Etcher 或其他整碟寫入工具。
- 不要把密碼、token、`.pem`、`.key` 或大型映像提交到 Git。

## H. SD 與 USB 讀卡機檢查

### H-1. 2026-07-28 已完成的 SD／Wi-Fi 修正

目前系統的實際狀態：

```text
root：/dev/mmcblk0p1（eMMC）
側邊 microSD：/dev/mmcblk1
SD host：mmc1 = 3440000.sdhci = SDMMC3
DTB：/boot/dtb/p450-p3668-0001-p3509-0000-sdmmc3-wifi-uartb460800.dtb
外接 Wi-Fi：wlan1／rtl88x2bu
```

`extlinux.conf` 的預設項目為 `p450-sdmmc3-uartb460800`，舊
`p450-sdmmc3` 保留為 fallback。SDMMC3 設為 4-bit、3.3 V、停用 1.8 V
切換、最高 50 MHz，並以 `non-removable` 方式探測。初始 SDR104 的 CRC 錯誤
在降速後消失。128 GB 卡的舊映像與 GPT 已依機主指示清除，現在是單一 ext4
`P450_DATA`，不是開機媒體。

內建 Intel 8265／`iwlwifi` 的 `phy0` 有不可解除的 hardware hard block，會關閉 NetworkManager 全域 Wi-Fi。為確保 `wlan1` 可用，已安裝：

```text
/etc/modprobe.d/p450-disable-iwlwifi.conf
blacklist iwlwifi
```

該設定已透過 `sudo update-initramfs -u` 納入 initrd。`wlan1` 已能掃描 AP，並已由有線切換為目前連線介面。若要恢復內建 Wi-Fi，移除 blacklist、重新生成 initramfs 後再重開機。

### H-2. 歷史 SD 與 USB 讀卡機檢查

2026-07-22 初始檢查結果：當時 eMMC `/dev/mmcblk0p1` 是開機 root；側邊 SD 控制器的 `mmc1` host 已啟用，但在一般 card-detect 模式下，128 GB 與 512 GB 卡都沒有出現 `/dev/mmcblk1`。當時已安裝的 force-probe 設定預設使用 `sd-force`；後續已由 H-1 的 SDMMC3 DTB 取代並完成重開驗證：

```bash
cat /boot/extlinux/extlinux.conf
lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS,MODEL
findmnt /
sudo dmesg | grep -Ei 'mmc|sdhci|mmcblk|card|gpio'
```

512 GB 卡經 USB 讀卡機目前可辨識為約 500 GB 的 `/dev/sda`，並可讀到 R35.6.0 Jetson 映像。該卡顯示 GPT 備份表未在裝置末端的警告，可能是小容量映像複製到大容量卡造成；在確認資料與開機需求前，不要執行以下任何寫入操作：

```text
fdisk 的自動修復、sgdisk -e、格式化、分割區調整、dd 或重新刷寫。
```

USB 手機網路最近一次重開機後已快速連線；檢查時請以實際出現的 `usb0`／`usb1` 介面為準：

```bash
nmcli device status
ip -br addr
ip route
```

## I. 本週目標：先做 Pixhawk ↔ NX 通訊，再做 ROS 2 Foxy 自動飛行

本週大目標是使用原生 ROS 2 Foxy 完成一次起飛、短暫停留、降落的自動飛行實驗。飛行前置順序固定如下：

```text
Pixhawk ↔ NX 直接通訊
        ↓
ROS 2 Foxy 原生環境
        ↓
uXRCE-DDS 與 /fmu/out/* topic
        ↓
拆槳地面測試與安全檢查
        ↓
一次自動飛行：起飛 → 短暫停留 → 降落
```

### I-1. 已確認的 Pixhawk ↔ NX UART

AMOV AllSpark 外殼 `UART0` 對應 `/dev/ttyTHS1`，並接到 Pixhawk `TELEM2`。外殼 `UART1` 才是 `/dev/ttyTHS0`，且目前尾端未接設備。不要再用 `/dev/ttyTHS0` 測 TELEM2。

確認常駐 Agent：

```bash
systemctl is-active p450-micro-xrce-agent.service
systemctl --no-pager --full status p450-micro-xrce-agent.service
```

手動診斷前必須先停止常駐服務，避免兩個 Agent 同時開啟 UART：

```bash
sudo systemctl stop p450-micro-xrce-agent.service
sudo timeout 20s /usr/local/bin/MicroXRCEAgent serial --dev /dev/ttyTHS1 -b 460800 -v 4
sudo systemctl start p450-micro-xrce-agent.service
```

### I-1a. USB 備援檢查

插入 Pixhawk 前後各執行一次：

```bash
date
lsusb
ls -l /dev/serial/by-id/ /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
sudo dmesg | tail -n 80
```

插入後若沒有新的 serial 裝置，不要把 QGC 已成功的 TCP/MAVLink 連線當成 NX 通訊成功，也不要直接猜測 UART。先保留 `lsusb`、`dmesg`、裝置名稱與線材／接法資訊，再排查 USB 線、Pixhawk 電源、USB Hub 與實際載板 UART 腳位。

### I-2. ROS 2 唯讀驗證

ROS 2 Foxy、Agent、`px4_msgs`、`px4_ros_com` 均已完成，不需重裝。驗證命令：

```bash
source /opt/ros/foxy/setup.bash
source /home/p450/p450_ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=0
export ROS_LOCALHOST_ONLY=0

ros2 topic list | grep '^/fmu/'
ros2 run px4_ros_com sensor_combined_listener
ros2 topic echo /fmu/out/vehicle_status px4_msgs/msg/VehicleStatus \
  --qos-reliability best_effort \
  --qos-durability transient_local
```

Foxy 有時無法替 bare DDS publisher 自動推導型別，因此 `vehicle_status` 應明確指定 message type 與 QoS。

連續性測試：

```bash
cd /home/p450/p450-jetson-handoff
./scripts/p450_ros2_link_monitor.py --duration 65 --max-gap-ms 100
```

目前 460800 baud 下 session 約每 10–23 秒重建，65 秒 IMU 最大空窗約 1.6 秒，仍不合格。所有參數變更與飛行測試都必須拆槳或固定機體；在連續通訊、topic、模式切換、Kill Switch 與失聯處置未驗證前，不進行自動起飛。

### I-3. PX4 v1.14.3 XRCE ping 回補韌體（已建置、尚未刷入）

成品位於 SD：

```text
/media/p450/P450_DATA/builds/firmware/p450-pixhawk6c-v1.14.3-xrce-ping-fix-f9bc66c6f3.px4
```

刷入前先核對：

```bash
sha256sum /media/p450/P450_DATA/builds/firmware/p450-pixhawk6c-v1.14.3-xrce-ping-fix-f9bc66c6f3.px4
```

預期 SHA-256：

```text
cb14d73274014385e809645dd3525e1ce0e33cf5d648c7d23324c41b822bf0bd
```

這是 `PX4FMUv6C`／board ID 56 的 Pixhawk 6C 韌體。刷入前必須：

1. 保持拆槳與穩定供電。
2. 用 QGC 匯出完整參數備份。
3. 再次確認硬體是 Pixhawk 6C。
4. 由 QGC Firmware 的 Advanced／Custom firmware file 選擇上述檔案。
5. 刷完後核對 airframe、校正、RC、安全與 failsafe，並確認
   `UXRCE_DDS_CFG=102`、`SER_TEL2_BAUD=460800`、`MAV_1_CONFIG=0`。
6. 先執行至少 10 分鐘唯讀 ROS 2 continuity 測試；不得直接解鎖或進入
   Offboard。

通過條件：10 分鐘內無 session close/recreate、`/fmu/*` topics 不消失、
IMU 最大 gap 小於 100 ms。完整背景、build commit 與失敗後的線路 A/B 清單見
`P450_PROGRESS_2026-07-24_NEXT.md`。
