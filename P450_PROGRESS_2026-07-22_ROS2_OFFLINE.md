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

### 內建側邊 SD 卡槽

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
