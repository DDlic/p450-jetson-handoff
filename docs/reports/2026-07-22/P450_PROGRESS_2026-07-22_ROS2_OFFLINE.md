# AMOV P450：2026-07-22 ROS 2 離線安裝與桌機接手狀態

更新日期：2026-07-23（Asia/Taipei）

Ubuntu 桌機 Codex CLI 請先閱讀本文件，再處理 ROS 2 離線安裝。

> **目前狀態覆寫（2026-07-23）**：NX 已在線完成原生 ROS 2 Foxy 安裝與驗證；Micro XRCE-DDS Agent v2.4.2、`px4_msgs` 與 `px4_ros_com` 也已完成建置與安裝。下方「離線安裝停點」保留作為歷史與備援紀錄，不再是目前阻塞。

## 本週目標與目前先決條件（2026-07-23）

本週大目標是先使用 Jetson 宿主上的原生 ROS 2 Foxy 完成一次自動飛行實驗，第一階段範圍限定為起飛、短暫停留、降落。

在此之前先完成 Pixhawk 飛控與 NX 的直接通訊測試，通過後才進行 ROS 2/uXRCE-DDS 整合。測試順序為：

```text
Pixhawk ↔ NX USB 或已確認腳位的 UART
        ↓
ROS 2 Foxy 原生安裝與基礎驗證
        ↓
uXRCE-DDS Agent、px4_msgs、px4_ros_com
        ↓
/fmu/out/* 與控制流程無槳驗證
        ↓
一次自動飛行：起飛、短暫停留、降落
```

目前已知的 QGC TCP/MAVLink 路徑是 P450 Wi-Fi → TCP/MAVLink → Pixhawk；它不等於 NX 已完成 USB/UART 或 uXRCE-DDS 通訊。先前檢查時 NX 沒有看到 `/dev/ttyACM*` 或 `/dev/ttyUSB*`，因此 Pixhawk↔NX 仍列為待測項目。

## 2026-07-23 Pixhawk ↔ NX 通訊初檢

本次只讀檢查在 Pixhawk 尚未被 NX 偵測的狀態下完成：

- `lsusb` 可看到 USB Hub、Genesys 讀卡機、Zenfone RNDIS 網路與其他周邊，但沒有 Pixhawk 的 USB 裝置。
- `/dev/serial/by-id/` 不存在，且沒有 `/dev/ttyACM*` 或 `/dev/ttyUSB*`。
- 因此目前不能宣稱 Pixhawk↔NX 通訊通過；也尚未進入 MAVLink 心跳或 uXRCE-DDS topic 驗證。

下一步應將 Pixhawk 以可確認資料線直接接到 NX，先不要經 USB Hub，然後重新執行
`docs/operations/JETSON_HANDOFF_COMMANDS.md` 的 I-1 檢查。只有出現穩定 serial 裝置並能由
協定工具確認心跳／遙測後，才進入 ROS 2 Foxy 與 uXRCE-DDS 整合。

## 2026-07-23 ROS 2 Foxy 與 PX4 工作區完成狀態

已在 NX 在線完成下列項目，沒有升級 Ubuntu 或 JetPack：

- ROS 2 Foxy `ros-base` 與必要的 demo／建置工具已安裝，`ros2`、`colcon`、`rosdep`、`vcs` 可用。
- `rosdep install --from-paths ... --ignore-src -r -y` 成功完成。
- Micro XRCE-DDS Agent v2.4.2 已編譯並安裝至 `/usr/local/bin/MicroXRCEAgent`；共享函式庫已由 `ldconfig` 納入系統搜尋路徑。
- 工作區 `/home/p450/p450_ros2_ws` 已完成 `px4_msgs` 與 `px4_ros_com` 建置，套件前綴分別為 `install/px4_msgs` 與 `install/px4_ros_com`。
- `px4_msgs/msg/VehicleOdometry` 介面可由 `ros2 interface show` 正常讀取；`px4_ros_com` 的 `offboard_control`、listener 範例已列出。
- ROS 2 基礎 talker/listener DDS 回環測試已通過；目前尚未啟動飛控 Agent 或修改 PX4 參數。

目前剩餘的通訊關卡是：先確認 Pixhawk↔NX 的實體 USB/UART/網路 transport，再依實際 transport 啟動 Agent、確認 `/fmu/out/*`，完成無槳測試後才進入自動飛行。

## 目前硬體與系統

- Jetson Xavier NX，模組 P3668-0001，eMMC 版本。
- 載板／裝置樹：P3509-0000 系列。
- JetPack 5.1.4、L4T R35.6.0。
- Ubuntu 20.04.6 LTS、Kernel 5.10.216-tegra。
- 根檔案系統：`/dev/mmcblk0p1`（eMMC）。
- 原本 128 GB microSD 保留，不要格式化。

## 2026-07-28 SDMMC3、wlan1 與連線狀態覆核

本次已完成底層設定、重開機與實機驗證：

- 系統仍由 eMMC `/dev/mmcblk0p1` 開機。
- 側邊 SD 卡已由 SDMMC3（`3440000.sdhci`／`mmc1`）辨識為 `/dev/mmcblk1`，目前卡片保持插入並可掛載。
- 使用 DTB `/boot/dtb/p450-p3668-0001-p3509-0000-sdmmc3-wifi.dtb`；`extlinux.conf` 預設 `p450-sdmmc3`。
- SDMMC3 設為 4-bit、3.3 V、停用 1.8 V 切換、最高 50 MHz。初始 SDR104 的 `Data CRC error` 在降速後，本次重開開機記錄未再出現。
- SD 卡的 GPT 備份表位置警告仍存在；不得執行 `sgdisk -e`、格式化、分割區調整、`dd` 或重新刷寫。
- 外接 TP-Link USB Wi-Fi 為 `wlan1`／`rtl88x2bu`，`rfkill` 無 hard/soft block，已成功掃描到 AP。
- 內建 Intel 8265 `wlan0`／`iwlwifi` 的 `phy0` 持續 hardware hard block，會使 NetworkManager 全域 Wi-Fi disabled。已安裝 `/etc/modprobe.d/p450-disable-iwlwifi.conf` 的 `blacklist iwlwifi` 並重新生成 initramfs；目前已由有線切換至 `wlan1` 連線。

上述 blacklist 只停用內建 Intel Wi-Fi，保留外接 `wlan1`。若需恢復內建 Wi-Fi，移除 blacklist、執行 `sudo update-initramfs -u` 後再重開機。

## 已確認可用功能

### P450 Wi-Fi 基地台

- P450 電池供電後，機上 Wi-Fi 基地台可正常啟動。
- 手機與筆電可以搜尋並連上 P450 Wi-Fi。
- 顯示沒有 Internet 是正常的；這是封閉式區域網路。
- Jetson 曾確認 `eth0 UP 192.168.10.100/24`。
- Jetson 內建 Intel Wireless AC 8265 曾顯示 `Hard blocked: yes`，目前不把它當作 P450 Wi-Fi 基地台，也不要為此中斷 ROS 2 工作。

### Pixhawk／QGroundControl

- 筆電透過 P450 Wi-Fi 使用 TCP 可正常連接 QGroundControl。
- QGC 可讀取 Pixhawk 6C 的飛控訊息。
- PX4 版本：1.14.3。
- QGC 可看到機架、感測器、遙控器與電源資訊。
- 已證實資料路徑：P450 Wi-Fi → TCP/MAVLink → Pixhawk。
- QGC TCP/MAVLink 成功不等於 ROS 2 已連線；ROS 2 需要獨立的 uXRCE-DDS 通道。

## ROS 2 方案決定

- 自動飛行測試先使用原生 ROS 2 Foxy，因為宿主是 Ubuntu 20.04。
- 先不使用 Docker，降低延遲、即時性與硬體存取的不確定性。
- 只有需要對接學長的 ROS 2 Humble 專案時，再處理 Humble 相容性。
- PX4 v1.14 的 `px4_msgs` 使用 `release/1.14` 分支。
- `px4_ros_com` 使用 `release/1.14` 分支；USB 內的來源說明與封存檔均以此版本為準。
- Micro XRCE-DDS Agent 暫定使用 v2.4.2。

## NX 上的離線安裝包

資料夾：

```text
/home/p450/Downloads/ROS2
```

內容包含：

```text
deb/
metadata/
sources/
README_offline_install.txt
SHA256SUMS.txt
```

來源壓縮檔包含：

```text
px4_msgs release/1.14
px4_ros_com release/1.14
Micro-XRCE-DDS-Agent v2.4.2
```

## 歷史：ROS 2 離線安裝停點（目前已繞過）

使用錯誤的絕對路徑 `/Downloads/ROS2` 時，系統找不到資料夾；正確路徑是使用者家目錄下的 `~/Downloads/ROS2`。

改用正確相對路徑後執行：

```bash
sudo apt install --no-download ./deb/*.deb
```

安裝停止於：

```text
Invalid archive member header
Could not read meta data from .../deb/git_2.25.1-1ubuntu3_arm64.deb
```

筆電當時傳到 NX 的副本大小為：

```text
537262 bytes（約 525 KB）
```

因此當時 NX 內的 `git_2.25.1-1ubuntu3_arm64.deb` 是截短副本；不能據此判定 USB 原始包損壞。尚未完成 ROS 2 安裝。

Ubuntu 桌機目前已對 USB 原始檔完成只讀檢查：

```text
大小：1456282 bytes
檔案格式：Debian binary package (format 2.0)
SHA256：c637afbaf34e2bffe59fac5f0e0a622026e85729f267ce0ef99353a5e52d5f34
```

USB 的 360 個 `.deb` 與 manifest 完全相符；SHA256 清單中除清單檔自身的自我雜湊項目外，其餘 379 個檔案均通過。問題判斷已由「原始包損壞」修正為「複製到 NX 的檔案被截短或未使用目前 USB 版本」。

另外，bundle README 的安裝指令未關閉 Recommends；離線環境可能因 `apt-utils` 或 `python3-dulwich` 等未收錄的建議套件中止，後續使用：

```bash
sudo apt install --no-download --no-install-recommends ./deb/*.deb
```

不要執行 `apt --fix-broken install`，因為 NX 沒有 Internet，可能會嘗試下載套件。

## Ubuntu 桌機接手工作

### 1. 重新複製並驗證 git 套件

不要重新下載或修改整個 bundle。從目前已驗證的 USB `ROS2/deb` 重新複製到 NX 的 `~/Downloads/ROS2/deb/`，覆蓋先前截短的同名檔案。

```text
git_2.25.1-1ubuntu3_arm64.deb
```

在 NX 確認：

```text
大小：1456282 bytes
SHA256：c637afbaf34e2bffe59fac5f0e0a622026e85729f267ce0ef99353a5e52d5f34
dpkg-deb --info 可正常讀取
```

### 2. 重新執行 NX 的離線安裝

在 NX：

```bash
cd ~/Downloads/ROS2
cat /etc/os-release
dpkg --print-architecture
uname -m
stat -c '%n %s bytes' deb/git_2.25.1-1ubuntu3_arm64.deb
sha256sum deb/git_2.25.1-1ubuntu3_arm64.deb
dpkg-deb --info deb/git_2.25.1-1ubuntu3_arm64.deb | sed -n '1,20p'
sudo apt install --no-download --no-install-recommends ./deb/*.deb \
  2>&1 | tee ~/ros2_foxy_offline_install.log
```

預期系統為 Ubuntu 20.04、`arm64`、`aarch64`。若出現其他 `Invalid archive`，記錄檔名、大小與 SHA256，停止安裝；不要執行 `apt update` 或 `apt --fix-broken install`。

### 3. 基礎 ROS 2 驗證

安裝成功後在 NX：

```bash
source /opt/ros/foxy/setup.bash
ros2 --help
ros2 doctor
```

基礎環境確認後，才建立 workspace、解壓 `px4_msgs` 並進行 colcon build。

## 尚未確認的 PX4 ROS 2 事項

- Pixhawk↔NX 直接通訊尚未通過；下一步先確認 USB serial 或明確的 UART transport。
- QGC 中 `UXRCE_DDS_CFG` 目前顯示 Disabled，尚未修改。
- 尚未確認 Pixhawk 對應哪一個 Jetson UART。
- NX 目前只看到：

  ```text
  /dev/ttyTHS0
  /dev/ttyTHS1
  /dev/ttyTHS4
  ```

- 沒有看到 `/dev/ttyACM*` 或 `/dev/ttyUSB*`。
- 需先確認 `UXRCE_DDS_CFG`、`UXRCE_DDS_PRT`、`UXRCE_DDS_AG_IP`、`UXRCE_DDS_DOM_ID`，再決定使用 UART、UDP 或 TCP。
- 不可把 QGC 的 TCP/MAVLink 連線直接當成 ROS 2/uXRCE-DDS 連線。

## 測試限制

- ROS 2、uXRCE-DDS 與參數測試先拆槳或確保馬達無法啟動。
- 尚未完成 ROS 2 topic 與 ULog 驗證前，不進行自動起飛。
- 首次自動飛行只規劃起飛、短暫停留、降落，確認訊息抓取正常後才進下一階段。
- 不要格式化舊 128 GB 卡，不要使用 Orin BSP 或一般 Ubuntu ISO。

## 2026-07-22 後續硬體與儲存檢查

### 內建側邊 SD 卡槽（2026-07-22 初始狀態；後續已由上方覆核完成）

以下 bullet 是修正前的歷史狀態；目前請以本文件上方的 2026-07-28 覆核為準。

- 目前系統仍由 eMMC `/dev/mmcblk0p1` 開機。
- 原本 active SD controller 為 disabled；已建立並安裝可回退的 force-probe device tree，`/boot/extlinux/extlinux.conf` 目前預設 `sd-force`，並保留 `sd-enabled`、`original` 兩個回退項目。force-probe 會移除 card-detect GPIO，並以 `non-removable` 方式讓控制器嘗試探測；尚待下一次重開機驗證。
- 使用一般 card-detect 模式測試 128 GB 與 512 GB 卡時，`mmc1` host 可見，但沒有 `/dev/mmcblk1`；`PG.07` card-detect 讀值持續為 high，而該訊號是 active-low。20 秒按壓卡片測試也沒有改變讀值，因此目前不能歸因於容量或檔案系統。

### USB Hub 讀卡機

- 512 GB 卡插入 USB Hub 讀卡機後可正常辨識為 `/dev/sda`，容量約 500 GB，包含 `sda1` 至 `sda22`。
- 只讀掛載後確認卡內是 Ubuntu 20.04.6、L4T R35.6.0 的 Jetson 映像；檢查完成後已卸載，沒有對卡片寫入。
- `fdisk -l`／`sgdisk -v` 顯示 GPT 備份表的 self-pointer 不在裝置末端，符合約 16 GB Jetson 映像複製到 512 GB 媒體的現象。尚未執行 GPT 修復，也不應在未確認資料用途前執行 `sgdisk -e`、格式化、分割區調整或重新刷寫。

### USB 手機網路

- 最近一次重開機後，USB RNDIS 網路可快速建立連線；介面名稱可能在 `usb0`、`usb1` 間變化，應以 NetworkManager 實際狀態為準。
- 先前開機後短暫無法連線，判斷與 USB Hub／RNDIS enumeration 時序有關；目前尚未重現相同延遲。

### 後續驗證界線

下一次重開機只驗證 force-probe 是否讓側邊卡出現 `/dev/mmcblk1`，並確認 root 仍是 `/dev/mmcblk0p1`。在結果明確前，不從 SD 開機、不修改 GPT、不格式化任何 SD 卡。
