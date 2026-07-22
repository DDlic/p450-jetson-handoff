# AMOV P450：2026-07-22 ROS 2 離線安裝與桌機接手狀態

更新日期：2026-07-22（Asia/Taipei）

Ubuntu 桌機 Codex CLI 請先閱讀本文件，再處理 ROS 2 離線安裝。

## 目前硬體與系統

- Jetson Xavier NX，模組 P3668-0001，eMMC 版本。
- 載板／裝置樹：P3509-0000 系列。
- JetPack 5.1.4、L4T R35.6.0。
- Ubuntu 20.04.6 LTS、Kernel 5.10.216-tegra。
- 根檔案系統：`/dev/mmcblk0p1`（eMMC）。
- 原本 128 GB microSD 保留，不要格式化。

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
- `px4_ros_com` 使用 `release/v1.14` 分支；不要使用不存在的 `release/1.14` 分支。
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
px4_ros_com release/v1.14
Micro-XRCE-DDS-Agent v2.4.2
```

## ROS 2 離線安裝目前停點

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

目前確認該檔案大小為：

```text
537262 bytes（約 525 KB）
```

因此 `git_2.25.1-1ubuntu3_arm64.deb` 疑似不完整或已損壞。尚未完成 ROS 2 安裝。

不要執行 `apt --fix-broken install`，因為 NX 沒有 Internet，可能會嘗試下載套件。

## Ubuntu 桌機接手工作

### 1. 修復 git 套件

在有 Internet 的 Ubuntu 桌機或 Windows 電腦確認同名檔案大小。若原始檔也只有 537262 bytes，重新取得 Ubuntu 20.04 Focal ARM64 的有效套件：

```text
git_2.25.1-1ubuntu3_arm64.deb
```

確認下載內容是 Debian 套件，不是 HTML 錯誤頁面；重新產生 SHA256 後，將有效檔案放回 NX：

```text
/home/p450/Downloads/ROS2/deb/
```

### 2. 重新執行 NX 的離線安裝

在 NX：

```bash
cd ~/Downloads/ROS2
sudo apt install --no-download ./deb/*.deb
```

若出現其他 `Invalid archive`，記錄檔名，回桌機重新取得該套件；不要繼續執行其他修復指令。

### 3. 基礎 ROS 2 驗證

安裝成功後在 NX：

```bash
source /opt/ros/foxy/setup.bash
ros2 --help
```

基礎環境確認後，才建立 workspace、解壓 `px4_msgs` 並進行 colcon build。

## 尚未確認的 PX4 ROS 2 事項

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
