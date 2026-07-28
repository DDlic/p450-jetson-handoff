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

## 六、2026-07-24 至 2026-07-28 TELEM2／UART0 實測結果

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

### 正確的 NX UART 映射

AMOV AllSpark 官方手冊確認：

- 外殼 `UART0` = Linux `/dev/ttyTHS1`
- 外殼 `UART1` = Linux `/dev/ttyTHS0`
- 兩者皆為 3.3 V CMOS，四線依序為 3V3、RX、TX、GND

因此先前 `/dev/ttyTHS0` 的 20 秒無 session 測試其實是在測未接設備的外殼 `UART1`，不是接到 Pixhawk `TELEM2` 的 `UART0`。

官方資料：

- <https://wiki.amovlab.com/public/prometheuswiki/P450%E4%BD%BF%E7%94%A8%E6%89%8B%E5%86%8C/%E7%A1%AC%E4%BB%B6%E4%BB%8B%E7%BB%8D.html>
- <https://wiki.amovlab.com/static/pdf/AllSpark%E4%BD%BF%E7%94%A8%E6%89%8B%E5%86%8C.pdf>

### 已通過的 ROS 2 資料測試

在正確裝置啟動 Agent：

```bash
sudo /usr/local/bin/MicroXRCEAgent serial --dev /dev/ttyTHS1 -b 921600
```

實測結果：

- PX4 client 建立 XRCE session，Agent 成功建立 participant、publisher、subscriber、data writer 與 data reader。
- ROS 2 發現 23 個 `/fmu/*` topics，其中有 10 個 `/fmu/out/*`。
- `px4_ros_com sensor_combined_listener` 能持續讀到即時陀螺儀與加速度計資料。
- `/fmu/out/vehicle_odometry` 能讀到即時位置、速度、姿態與 variance。
- 明確指定 message type 及 QoS 後，`/fmu/out/vehicle_status` 能讀到狀態。
- 當時狀態包含 `failsafe: false`、`power_input_valid: true`，但同時為 `gcs_connection_lost: true`、`pre_flight_checks_pass: false`，里程計 `quality: 0`；不得據此解鎖或起飛。

Agent 已安裝為 systemd 服務：

```bash
sudo systemctl status p450-micro-xrce-agent.service
```

服務檔來源為 `systemd/p450-micro-xrce-agent.service`，已 enabled，人工重啟後可重新建立 session 與 topics。

### 尚未通過：session 穩定性

目前不是「完全不通」，而是 session 約每 2.7–4.8 秒重建：

- Agent 日誌可見 PX4 依序送出 `delete_client`、`session closed`，隨即再 `create_client`。
- 10 秒協定追蹤量到飛控至 NX 約 26.8 kB/s、NX 至飛控約 0.6 kB/s。
- 協定層追蹤顯示 Agent 在收到要求後約 0.2 ms 內產生回覆。
- 降低 Agent 日誌量及用 FIFO 即時排程執行，均未消除重建。
- PX4 v1.14.3 原始碼在連續漏掉約三次短週期 ping 回覆後就斷線；PX4 v1.15 已改為有有效 payload 收發時不以 ping 判死，並放寬 ping timeout。這使 PX4 1.14.3 的判定成為目前的重要因素。

目前優先採低風險排查：

1. 由 QGC 把 `SER_TEL2_BAUD` 從 921600 改為 460800 並重啟 Pixhawk。
2. 同步把 NX Agent baud 改為 460800。
3. 連續監測至少 60 秒，要求沒有 `delete_client`／`session closed`，且 `/fmu/out/sensor_combined`、`vehicle_odometry`、`vehicle_status` 持續可讀。
4. 若 460800 仍反覆重建，再檢查 TELEM2→UART0 的 TX/RX/GND 接點與線材；最後才評估升級 PX4 或回補新版 uXRCE ping 修正。

460800 的理論有效負載高於目前約 26.8 kB/s 的量測值，但仍須實測確認。完成上述穩定性關卡前，不進入 Offboard、不送控制指令、不解鎖。
