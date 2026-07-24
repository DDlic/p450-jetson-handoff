# P450 2026-07-24 下一步規劃：Pixhawk ↔ NX 與 ROS 2 Foxy

更新日期：2026-07-24（Asia/Taipei）

本文件是目前最新的執行指引，供 Ubuntu 桌機與 Jetson NX 上的 Codex CLI 接手使用。它不取代刷寫歷史，只更新「下一步做什麼」。

## 一、目前已完成

- Jetson Xavier NX 已確認為 P3668-0001、eMMC 版本。
- JetPack 5.1.4／L4T R35.6.0 已完整刷入 eMMC，Ubuntu 20.04 圖形介面可正常開機。
- 原本 128 GB microSD 保留，禁止格式化或重新刷寫。
- P450 機上 Wi-Fi 基地台已確認可用；手機與筆電可以連線。沒有 Internet 是預期的封閉式區域網路狀態。
- 筆電透過 P450 Wi-Fi 使用 TCP/MAVLink 連接 QGroundControl，已能讀取 Pixhawk 6C 訊息；PX4 版本為 1.14.3。
- NX 宿主使用原生 ROS 2 Foxy，不使用 Docker。
- Micro XRCE-DDS Agent v2.4.2 已安裝。
- `/home/p450/p450_ros2_ws` 的 `px4_msgs` 與 `px4_ros_com` 已建置；ROS 2 talker/listener 回環測試已通過。

## 二、目前尚未完成的核心關卡

目前沒有證據證明 Pixhawk 已直接連到 NX。QGC 的 TCP/MAVLink 路徑是：

```text
筆電 → P450 Wi-Fi → TCP/MAVLink → Pixhawk
```

這不等於：

```text
Pixhawk → NX USB/UART/網路 → uXRCE-DDS Agent → ROS 2 Foxy
```

先前 NX 檢查沒有看到 `/dev/ttyACM*` 或 `/dev/ttyUSB*`，所以必須重新確認實際接線與 transport。不要因為 QGC 已成功就直接設定 `UXRCE_DDS_CFG` 或猜測 `/dev/ttyTHS0/1/4`。

## 三、NX Codex CLI 接手流程

請 NX Codex CLI 使用繁體中文，要求使用者一次只執行一個簡短命令，等待輸出後再進下一步。使用者目前多半需要手動輸入命令，不要一次提供複雜的長腳本。

### 0. 安全前提

- 螺旋槳先拆除，或將機體可靠固定。
- 不進入 Arm，不進行自動起飛。
- 不修改 PX4 參數、不重刷 eMMC/QSPI/SD。
- 不猜測 UART 腳位、電壓、線序或 `/dev/ttyTHS*` 對應。

### 1. 先測 Pixhawk 直連 USB

請使用者將 Pixhawk 6C 以可傳輸資料的 USB 線直接接到 NX，不要經過 USB Hub。接好後只執行：

```bash
lsusb
```

若看得到新增的 Pixhawk/Autopilot/STM32/CDC ACM 類裝置，再執行：

```bash
ls -l /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
```

若仍沒有 serial 裝置，再執行：

```bash
sudo dmesg | tail -n 30
```

判定規則：

- 有穩定的 `/dev/ttyACM*` 或 `/dev/ttyUSB*`：記錄名稱，觀察至少 60 秒是否反覆消失。
- 沒有新增裝置：停止，不要猜 UART；回報 USB 線、Pixhawk 是否供電、是否直連、`lsusb` 與 `dmesg` 結果。
- USB serial 出現只代表 USB/MAVLink 可能可用，不代表 uXRCE-DDS 已經在這條線上運行。

### 2. 確認 ROS 2 工作區，不重裝

只有在實體連線有結果後，才執行下列命令；每次分開執行：

```bash
source /opt/ros/foxy/setup.bash
```

```bash
source ~/p450_ros2_ws/install/setup.bash
```

```bash
ros2 pkg list | grep -E 'px4_msgs|px4_ros_com'
```

若套件不存在，先回報，不要重新安裝整套 ROS 2。

### 3. 再決定 uXRCE-DDS transport

先在 QGroundControl 只讀取並記錄：

- `UXRCE_DDS_CFG`
- `UXRCE_DDS_PRT`
- `UXRCE_DDS_AG_IP`
- `UXRCE_DDS_DOM_ID`

不要在尚未知道 P450 實際 Pixhawk↔NX 線路前修改這些值。

transport 判斷：

- 若 P450 實際使用 Pixhawk TELEM/UART 接到 NX，先確認載板腳位、電平與線序，再選正確的 `/dev/ttyTHS*` 與 baud rate。
- 若實際使用 UDP，先確認 NX 的 IP、Pixhawk Agent 目標 IP 與 port；不可把 QGC 的 TCP 連線直接當成 uXRCE-DDS。
- 若只有 USB 連線而 PX4 沒有把 uXRCE-DDS 設在該 USB 通道，USB 只能作為診斷/MAVLink 路徑，不能直接假設可取代 UART/UDP Agent。

只有 transport、裝置與 baud/port 都確認後，才啟動 Agent。不要先試一串猜測命令。

### 4. 驗證 ROS 2 訊息

Agent 啟動後，另開終端重新 source：

```bash
source /opt/ros/foxy/setup.bash
```

```bash
source ~/p450_ros2_ws/install/setup.bash
```

```bash
ros2 topic list | grep /fmu
```

若出現 PX4 topic，再逐一檢查：

```bash
ros2 topic echo /fmu/out/vehicle_status --once
```

```bash
ros2 topic echo /fmu/out/vehicle_odometry --once
```

沒有穩定的 `/fmu/out/*` 時，不進入 Offboard，也不飛行。

### 5. 無槳安全測試

topic 穩定後才安排：

- PX4 ULog 記錄。
- Kill Switch 是否由遙控器內部通道獨立作用。
- ROS 2/Agent 中斷時的 failsafe。
- Altitude/Position 模式資料、氣壓計、垂直速度、姿態、EKF 與震動資訊。

ROS 2 只讀資料與安全控制流程通過後，才規劃第一次自動飛行：

```text
自動起飛 → 短暫停留 → 自動降落
```

第一次不加入航點、水平位移或複雜軌跡。

## 四、目前不要做

- 不要在 Ubuntu 20.04 宿主執行 `do-release-upgrade`。
- 不要因為學長使用 Humble 就立刻改 Docker；目前先用原生 Foxy，只有確定需要對接 Humble 專案時再另案規劃。
- 不要再處理側邊 SD 卡 force-probe、GPT 修復或容量問題，除非另有明確需求；目前系統由 eMMC 正常運作。
- 不要把 Pixhawk 的 QGC TCP/MAVLink 連線誤判成 ROS 2/uXRCE-DDS 已完成。

## 五、回報格式

NX Codex CLI 每完成一個小步驟後，回報：

1. 實際執行的命令。
2. 是否新增 serial 裝置或 topic。
3. 若失敗，完整錯誤與停止位置。
4. 下一步前先等待使用者確認，不自行跳過實體 transport 判斷。

## 六、2026-07-24 TELEM2／UART0 實測結果

### 已確認的接線與 PX4 參數

- 使用者確認 NX `UART0` 接到 Pixhawk `TELEM2`。
- NX `UART1` 雖有線材，但尾端未接到任何設備，暫不列為測試通道。
- Pixhawk 已透過 USB 直接連接筆電 QGroundControl，作為參數恢復與診斷路徑。
- 為保留 QGC TCP/MAVLink，`MAV_0_CONFIG` 保持 `TELEM1`。
- `MAV_1_CONFIG` 設為 `Disabled`，釋放 `TELEM2` 給 uXRCE-DDS。
- `UXRCE_DDS_CFG` 設為 `TELEM2`，QGC 顯示值為 102。
- `SER_TEL2_BAUD` 為 `921600`（8N1）。

上述參數由 Git 中的 `mav_con` 記錄確認：

```text
param show UXRCE_DDS_CFG  -> 102
param show MAV_1_CONFIG   -> 0
param show SER_TEL2_BAUD  -> 921600
uxrce_dds_client status   -> Running, disconnected
transport                 -> serial
```

### NX 端 Agent 測試

在 NX 主機執行一次 20 秒測試：

```bash
sudo timeout 20s /usr/local/bin/MicroXRCEAgent serial --dev /dev/ttyTHS0 -b 921600
```

結果：

- `/dev/ttyTHS0` 可開啟，Agent 回報 `running`。
- 測試期間沒有出現 XRCE-DDS client session。
- PX4 端同時回報 `Running, disconnected`。
- 因此目前尚未出現 `/fmu/out/*` ROS 2 topics，也不得進入 Offboard 或飛行測試。

系統 device-tree 顯示 `serial0` 指向 `3100000.serial`，而 `ttyTHS0` 對應該 serial 裝置；這只能確認 Linux 裝置映射，不能單獨證明 P450 載板的實體腳位、線序或電平正確。

### 目前判定與停止點

ROS 2 Foxy、`px4_msgs`、`px4_ros_com`、Micro XRCE-DDS Agent 與 PX4 端 uXRCE-DDS 啟動條件均已完成；目前失敗點在 PX4 TELEM2 到 NX UART0 之間沒有建立 XRCE-DDS session。

仍需實體確認：

- TELEM2 與 UART0 兩端是否真的接通。
- TX/RX 是否交叉正確，且共用 GND。
- P450 載板 UART 腳位的電壓電平是否相容。
- 載板 UART0 的 pinmux 與實際 Linux 裝置映射是否一致。

在上述項目確認前，不再猜測其他 `/dev/ttyTHS*`、不再改 PX4 參數、不重刷系統，也不進行解鎖或飛行。
