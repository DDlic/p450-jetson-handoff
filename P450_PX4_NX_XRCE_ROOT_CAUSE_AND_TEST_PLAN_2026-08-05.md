# P450 PX4／Jetson Xavier NX XRCE 原因分析與測試計畫（2026-08-05）

本文件供 Jetson Xavier NX 本機 CLI 接手目前的 PX4／ROS 2 Foxy／uXRCE-DDS
排障工作。內容以 repository 實機紀錄、PX4 各 release tag 原始碼與官方文件交叉
比對後整理。

本文件只定義診斷順序與停止條件，不代表已授權刷韌體、解鎖、裝槳或飛行。

## 一、先讀結論

目前最符合全部證據的主因是：**PX4 飛控端 `uxrce_dds_client` 沒有及時排空
NX→PX4 輸入資料，導致接收延遲、Offboard heartbeat 過期，嚴重時使仍存在的 XRCE
session 停止輸出。**

這不是「Jetson Xavier NX 不支援某版 PX4」的單一相容性問題。NX 只負責執行
Linux、ROS 2 與 Micro XRCE-DDS Agent；真正需要同時匹配的是：

1. Pixhawk 6C 的 PX4 target 與 serial port。
2. PX4 內的 XRCE client 行為。
3. Agent／Fast DDS／ROS 2 distribution。
4. 與韌體完全一致的 `px4_msgs` definitions。
5. `/dev/ttyTHS1`、AllSpark UART0、TELEM2 的實體雙向傳輸。

目前 ROS 2 Foxy＋Agent v2.4.2 是 PX4 官方相容表指定的組合；v1.15.4 的 43 個
DDS message types 也已逐一比對為完全一致。因此 Agent major version 與
`px4_msgs` mismatch 都不是首要嫌疑。

## 二、目前不可混淆的實機基線

### 2.1 Jetson／ROS 端

```text
Jetson: Xavier NX／P3668-0001
JetPack: 5.1.4
L4T: R35.6.0
Ubuntu: 20.04
Kernel: 5.10.216-tegra
ROS 2: Foxy（原生安裝）
Agent: Micro XRCE-DDS Agent v2.4.2
Agent service: p450-micro-xrce-agent.service
PX4 transport: /dev/ttyTHS1，460800 baud，8N1
實體路徑: Pixhawk TELEM2 → AllSpark UART0 → /dev/ttyTHS1
```

啟用的 device tree 為：

```text
/boot/dtb/p450-p3668-0001-p3509-0000-sdmmc3-wifi-uartb460800.dtb
```

此 DTB 已消除 kernel 原本的 460800 baud out-of-range 訊息，但沒有消除 XRCE
異常。因此 DTB 修正有效，卻不是完整解法。

### 2.2 目前飛控狀態

```text
Flight controller: Pixhawk 6C／PX4FMUv6C
PX4: stock v1.15.4 source build
source: 99c40407ffd7ac184e2d7b4b293f36f10fe561ef
firmware SHA-256: 21af0b94edd5de84dde5360874d8e1f66a52e3be07dfbafaaffc03baa580c29a
px4_msgs: release/1.15
px4_msgs commit: a1045ec4feb6d709bdecaf3895f1d5b43a5dabb8
UXRCE_DDS_SYNCT: 0（只為診斷；完成 A/B 後必須恢復 1）
```

stock v1.15.4 實測：

- 60 秒純接收：最大 gap `1014.823 ms`，15 次超過 500 ms，FAIL。
- 多個 `/fmu/out/*` topic 與 PX4 source timestamp 同時停約 1 秒。
- Agent 只有一次 session 建立，沒有 close／recreate；停頓發生在活著的 session 內。
- `UXRCE_DDS_SYNCT=0` 後最大 gap 仍約 1 秒，時間同步不是主因。
- 2 Hz `OnboardComputerStatus` 已到達 Agent 並寫向 serial，但輸出空窗仍存在。
- 20 Hz 非控制輸入使 PX4→NX 輸出完全停止；停止輸入後沒有自行恢復，需重啟
  Agent 才恢復。

完整證據見：

- [`P450_PX4_V1154_XRCE_TEST_2026-08-04.md`](P450_PX4_V1154_XRCE_TEST_2026-08-04.md)
- [`P450_POSTFLASH_XRCE_TEST_2026-08-03.md`](P450_POSTFLASH_XRCE_TEST_2026-08-03.md)
- [`firmware/README.md`](firmware/README.md)

## 三、PX4 各版本對目前 NX 架構的差異

| PX4 版本 | ROS 2 bridge／client | Pixhawk 6C | 與本案相關的 receive loop | 判定 |
| --- | --- | --- | --- | --- |
| v1.13.3 | 舊 Fast-RTPS Bridge | 支援 | 不是目前 uXRCE-DDS 架構 | 不建議退回 |
| v1.14.3 | uXRCE-DDS；Micro XRCE client 2.2.1 | 預設包含 | stock 每輪只呼叫一次 session | ping 回補後輸出已穩定，但輸入仍待修 |
| v1.15.4 | uXRCE-DDS；client 2.4.0 | 預設包含 | 每輪只呼叫一次 session | 目前 stock 實機 FAIL |
| v1.16.2 | uXRCE-DDS；client 2.4.0 | 預設包含 | 仍是單次 session | 不能假設升級會解決 |
| v1.17.0 | 目前 stable；client 2.4.0 | 預設包含 | 仍是單次 session | 不適合當第一個排障動作 |
| v1.18.0-beta1 | uXRCE-DDS | 預設包含 | 每輪最多 drain 10 次，poll 降至 1 ms | 上游重要佐證；beta 不直接用於飛行 |

上述 tags 的 Pixhawk 6C target 都使用：

```text
CONFIG_BOARD_SERIAL_TEL2="/dev/ttyS3"
CONFIG_MODULES_UXRCE_DDS_CLIENT=y
board_id=56
```

### 3.1 上游修改的時間線

1. PX4 [`d12a7dd11da5`](https://github.com/PX4/PX4-Autopilot/commit/d12a7dd11da5)
   曾將單次 `uxr_run_session_timeout()` 改為每輪最多執行 10 次。提交說明明確指出，
   單次處理會造成接收資料顯著延遲，甚至讓已註冊飛行模式 timeout。
2. 後續 [`a1cce7e961df`](https://github.com/PX4/PX4-Autopilot/commit/a1cce7e961df)
   重構 ping、poll 與 instrumentation；v1.15.4、v1.16.2、v1.17.0 的實際 source
   又只剩一次非阻塞 session 處理。
3. PX4 [`3169dc6b1b17`](https://github.com/PX4/PX4-Autopilot/commit/3169dc6b1b17d138d1e04228e400814ed79d0e63)
   於 v1.18 development 重新加入 inbound burst draining，並明確說明高輸入流量可能
   讓 RX buffer overflow／starve。它也將 poll timeout 從 10 ms 降為 1 ms、改善
   best-effort output buffer 滿載時的 flush／retry。

`3169dc6` 的標題寫 high UDP load，但 receive-drain loop 位於 serial／UDP 共用的
session 主迴圈。把它視為 serial 路徑佐證是依原始碼位置作出的推論，仍須在本機 UART
上 A/B 驗證。

### 3.2 現有候選版不是新版完整修正

repository 已有：

```text
firmware/p450-pixhawk6c-v1.15.4-xrce-rx-drain-996b1df7a1.px4
SHA-256: dbfd43085bbb4fe59744ad244a973b1243fb55d34ed36df52c9a0855be464949
source: 996b1df7a10a35b3e3534df9c5629f3675c7cab0
```

此版只回補舊 `d12a7dd` 行為，以「成功反序列化的 payload 計數是否增加」判斷要不要
繼續處理。新版 `3169dc6` 則以 transport 尚有多少 bytes 可讀判斷，並包含 poll 與
output buffer 修改。

所以現有候選版是合理的最小診斷 A/B，但不等於 v1.18 新修正，也不可因編譯成功就
稱為已修復。它的 image 已使用 1,961,732／1,966,080 bytes（99.78%）；若建立第二個
較完整 backport，必須再次驗證 FLASH 容量與 board metadata。

## 四、原因分級

### A. PX4 XRCE client 接收排空／排程問題：高機率

支持證據：

- 高頻 NX→PX4 非控制輸入能使全部 PX4→NX 輸出停止。
- Agent 沒有 crash、restart、session close 或 recreate。
- 關閉時間同步沒有改善。
- 上游兩次提交都直接描述單次 session／高 inbound load 引起的 delay 或 stall。
- Offboard heartbeat 在 NX publisher、DDS DataReader 與 Agent serial send 都連續，
  但 PX4 uORB 最新樣本曾落後約 `0.724 s`。

### B. Xavier NX `ttyTHS1`／DMA／實體 TX 路徑：中等機率

Agent log 只證明應用程式已把資料交給 serial transport，不能證明每一個 byte 都正確
到達 Pixhawk。NVIDIA 的 `ttyTHS*` 是 Tegra DMA-capable UART，Xavier NX／L4T R35
也有 460800 與 UART DMA 相關案例。

反證是：UART clock 容差已修正、kernel 不再報錯，而且 v1.14.3 ping 回補版曾在同一
條線完成 10 分鐘穩定 PX4→NX 輸出。因此這條路徑仍須隔離測試，但不是第一順位結論。

### C. Agent／Fast DDS／message mismatch：低機率

- Foxy 對應 Agent v2.4.2，符合 PX4 官方版本表。
- v1.15.4 的 43 個 DDS message types 全部一致。
- entities 與 43 個 topics 可以完整建立。

### D. `UXRCE_DDS_SYNCT`：目前已被實測降低

停用後問題仍存在。不得把 `UXRCE_DDS_SYNCT=0` 留作最終飛行設定。

### E. Offboard／RC 設定：獨立且仍會阻止飛行

- `COM_OF_LOSS_T` 已在 2026-08-04 確認為正常預設 `1.0 s`，不是設得過短。
- `offboard_control_signal_lost` 仍間歇為 true，較符合飛控端收到的 heartbeat 新鮮度
  不連續。
- 移除發射機電池超過 20 秒，`manual_control_signal_lost` 仍為 false；接收機可能在
  RF 失聯時維持 Hold 輸出。確認接收機型號與 failsafe 設定前不得飛行。

## 五、建議執行順序

### Phase 0：只讀確認，不發布、不刷機

在 NX 找到 repository checkout 後：

```bash
git fetch --prune origin
git status --short --branch
git pull --ff-only
git log -1 --date=iso-strict --format='%H%n%ad%n%s'
```

預期至少包含本文件的提交。若 worktree 有本機修改，不得覆蓋或強制 reset；先記錄
差異並停止。

確認環境：

```bash
uname -a
cat /etc/nv_tegra_release
source /opt/ros/foxy/setup.bash
source /media/p450/P450_DATA/builds/p450_ros2_ws_v115/install/setup.bash
/usr/local/bin/MicroXRCEAgent --version
systemctl is-active p450-micro-xrce-agent.service
systemctl show p450-micro-xrce-agent.service -p MainPID -p NRestarts
ros2 topic list | sort
ros2 topic info -v /fmu/out/sensor_combined
ros2 topic info -v /fmu/in/onboard_computer_status
```

確認同一時間只有一個程序占用 UART：

```bash
sudo fuser -v /dev/ttyTHS1
```

先保留 kernel UART 基線：

```bash
sudo dmesg --ctime | grep -Ei '3110000.serial|ttyTHS1|serial-tegra|gpcdma|baud|overrun|dma'
```

遇到下列任一情況立即停止：

- Agent 不為 active 或 `NRestarts` 增加。
- UART 同時被兩個 Agent／程序占用。
- 出現 baud、DMA、overrun、I/O error。
- `/fmu/out/sensor_combined` 不存在或沒有 PX4 publisher。
- 找不到 `p450_ros2_ws_v115`，或 source 後 message type 不正確。

### Phase 1：stock v1.15.4 純接收基準

保持未解鎖、不進入 Offboard、不發布任何 `/fmu/in/*`：

```bash
source /opt/ros/foxy/setup.bash
source /media/p450/P450_DATA/builds/p450_ros2_ws_v115/install/setup.bash
python3 scripts/p450_ros2_link_monitor.py --duration 60 --max-gap-ms 100
```

`100 ms` 是本專案的工程 A/B gate，不是 PX4 官方飛行保證。現有 monitor 只計算已收到
樣本之間的 gap；執行者還必須另外記錄：

- 開始後第一筆資料等待時間。
- 測試結束前最後一筆資料到結束的 trailing gap。
- 測試前後 Agent PID／`NRestarts`。
- Agent lifecycle 是否出現 `delete_client`／`session closed`。
- 測試中 topic 是否消失。

stock v1.15.4 已知會 FAIL；本階段目的只是建立同一供電、線材與開機狀態的當日對照。

### Phase 2：優先做 FTDI transport A/B（有硬體才做）

目標是在不換 PX4 韌體的情況下，繞過 AllSpark `/dev/ttyTHS1`／Tegra DMA：

```text
Pixhawk TELEM2 → 3.3 V FTDI → Jetson USB／ttyUSB*
```

安全限制：

- 必須拆槳並固定機體。
- 使用 3.3 V UART；TX／RX 交叉並共地。
- **TELEM2 的 +5 V 不可接到 FTDI。**
- 保留 Pixhawk `SER_TEL2_BAUD=460800`，只改本次手動 Agent 的裝置路徑。
- 不永久修改 systemd service；測試後恢復原本 `/dev/ttyTHS1` service。

確認 FTDI 裝置後，先停止常駐 Agent，避免雙重占用：

```bash
sudo systemctl stop p450-micro-xrce-agent.service
lsusb
ls -l /dev/ttyUSB* 2>/dev/null
sudo fuser -v /dev/ttyUSB0
sudo /usr/local/bin/MicroXRCEAgent serial --dev /dev/ttyUSB0 -b 460800 -v 4
```

實際裝置不一定是 `/dev/ttyUSB0`，必須由插拔前後的 `lsusb`／`dmesg` 確認，不可猜。
測試完成後中止前景 Agent並恢復：

```bash
sudo systemctl start p450-micro-xrce-agent.service
systemctl is-active p450-micro-xrce-agent.service
sudo fuser -v /dev/ttyTHS1
```

判讀：

| 結果 | 判讀 |
| --- | --- |
| FTDI 下純接收與 20 Hz 輸入都正常 | `/dev/ttyTHS1`／DTB／AllSpark 實體路徑嫌疑升高 |
| FTDI 下仍有一秒空窗或 20 Hz 鎖死 | PX4 client 嫌疑進一步升高 |
| FTDI 無法建立 session | 先查線序、電平、共地、裝置與 baud，不能判定 PX4 |

### Phase 3：現有 v1.15.4 RX-drain 候選版 A/B

只有機主明確決定刷入後才執行。刷入不是本文件自動授權的動作。

刷入前：

1. 拆槳、固定機體、斷開推進主電池，以 QGC／Pixhawk USB 穩定供電。
2. QGroundControl 直連 USB，不經 hub；備份完整參數。
3. 核對 Pixhawk 6C／board ID 56。
4. 從 [`firmware/SHA256SUMS`](firmware/SHA256SUMS) 驗證候選檔 SHA-256。
5. 記錄目前 firmware version、airframe、calibration 與所有安全／failsafe 參數。

刷入後依序測試，前一步 FAIL 就停止：

1. 保留 `UXRCE_DDS_SYNCT=0`，做 60 秒純接收。
2. 2 Hz `/fmu/in/onboard_computer_status` 非控制輸入＋60 秒輸出監測。
3. 20 Hz 非控制輸入＋60 秒輸出監測。
4. 停止輸入後，確認 PX4 output 能否在不重啟 Agent 的情況下自行恢復。
5. 將 `UXRCE_DDS_SYNCT` 恢復為 `1`、重啟飛控，再做 1–4。
6. 全部通過後才做 10 分鐘純接收與 Agent lifecycle 測試。

安全的非控制輸入只使用 `OnboardComputerStatus`；不要在 Phase 3 同時發布
`VehicleCommand`、Offboard mode、rates、attitude、position、thrust 或 actuator 命令。

ROS 2 CLI 發布前先以 `ros2 interface show px4_msgs/msg/OnboardComputerStatus` 確認
本機 type。範例命令如下；必須另開終端同時執行純接收 monitor：

```bash
ros2 topic pub --rate 2 \
  --qos-reliability best_effort \
  --qos-durability transient_local \
  /fmu/in/onboard_computer_status \
  px4_msgs/msg/OnboardComputerStatus \
  "{timestamp: 0, uptime: 0, type: 0}"
```

只有 2 Hz 階段通過才把 `--rate 2` 改為 `--rate 20`。發布測試必須有明確 timeout 或
人工監看；測試完成立即 `Ctrl-C`。

立即停止條件：

- 2 秒完全沒有任何 `/fmu/out/sensor_combined`。
- Agent session close／recreate，PID 改變或 `NRestarts` 增加。
- PX4 client disconnected 或 topics 消失。
- 停止輸入 12 秒仍無法自行恢復。
- kernel 新增 UART／DMA／I/O error。
- 意外進入 Offboard、解鎖或任何馬達輸出。

### Phase 4：若舊 backport 不完整，才建立第二候選版

不要直接把 v1.18 beta 整版刷入。以 stock v1.15.4 為單一基底，另案評估只回補
`3169dc6` 中與 serial 共用路徑相關的修改：

- transport 有 pending input 時不阻塞 uORB poll。
- poll timeout 由 10 ms 降為 1 ms。
- 每輪最多 drain 10 次，以 `FIONREAD`／pending bytes 決定停止。
- best-effort output buffer 滿載時 flush／retry。

建立後必須重新驗證：

- patch diff 與來源 commit。
- recursive submodules 沒有偏移。
- clean build 完成。
- `board_id=56`、`PX4FMUv6C` metadata。
- image 不超過 1,966,080 bytes。
- SHA-256 與可重現 build 資訊。

此階段需要另行授權；NX CLI 不得自行修改、建置、刷入或發布新韌體。

## 六、手動 Offboard 開關與手動 ARM 能省略什麼

若操作者採用實體模式開關切 Offboard、人工 ARM：

- 可暫緩用 ROS `VehicleCommand` 測試模式切換。
- 可暫緩用 ROS `VehicleCommand` 測試 ARM。
- v1.15.4 已有 `/fmu/out/vehicle_command_ack`，日後若恢復外部 command 測試，應同時
  訂閱 ACK，不能只看是否切換成功。

但是下列項目完全不能省略：

1. `OffboardControlMode` 必須先連續發布超過 1 秒。
2. PX4 要求 proof-of-life 高於 2 Hz；工程測試建議固定 10–20 Hz 並監測實際 gap。
3. heartbeat 中斷後必須依 `COM_OF_LOSS_T` 與 Offboard loss action 正確退出。
4. `OffboardControlMode` 第一個設為 true 的控制層，仍決定所需 estimator 與 setpoint。
5. 必須有對應且安全的 setpoint；不能只靠模式開關繞過控制需求。
6. RC loss、Kill Switch、Offboard loss、定位／航向與 preflight 仍須分別通過。

所以 `offboard_control_signal_lost=true` 會直接影響能否進入與保持 Offboard。人工模式
開關和人工 ARM 都不能繞過 heartbeat 問題。

### Offboard 地面測試的進入條件

只有 Phase 1–3 的雙向資料流、20 Hz 壓力、自行恢復與 10 分鐘 continuity 全部通過，
才可考慮無槳 Offboard heartbeat 測試。當時仍須：

- 拆槳、固定機體、零 thrust／零 body rate。
- watchdog 一旦看見 heartbeat lost 就立刻停止 publisher。
- 先不切 Offboard、不 ARM，確認 PX4 uORB 內 heartbeat 新鮮度連續。
- 再人工停止 heartbeat，驗證 PX4 在預期 timeout 內標記 loss。
- 完成 RC receiver failsafe 修正前，不進行裝槳或飛行測試。

## 七、不建議現在做的事

- 不因 v1.16／v1.17 較新就直接升級；它們仍保留單次 session 處理。
- 不直接拿 v1.18 beta 飛行。
- 不提高 `COM_OF_LOSS_T` 來遮蔽 transport／client 延遲；目前值 1.0 s 正常。
- 不把 `UXRCE_DDS_SYNCT=0` 當成最終設定。
- 不同時改 PX4 版本、Agent、baud、UART 路徑與 QoS。
- 不讓 systemd Agent 與前景 Agent 同時占用同一個 UART。
- 不把 QGC TCP／MAVLink 連線當成 NX uXRCE-DDS 已通過。
- 不因手動 ARM／模式開關就跳過 heartbeat、failsafe、RC loss 或 estimator 測試。
- 不在目前診斷階段升級 Ubuntu／JetPack；Foxy 已 EOL 是長期維護議題，不是本輪首要
  根因。若 FTDI A/B 明確指向 Tegra UART，再另案評估 JetPack 5.1.5／L4T R35.6.1
  或 PIO／USB serial 路徑，且必須先保全自製 DTB 與完整系統備份。

## 八、替代路線

若近期目標是完成一次受控自動起降，而不是一定要完成 XRCE root-cause，可另案評估
MAVLink＋MAVSDK／MAVROS。這會改變 TELEM2／transport 與控制架構，必須有獨立參數、
failsafe 與 Offboard setpoint 測試；不能把它稱為 XRCE 已修復。

## 九、官方交叉來源

- [PX4 uXRCE-DDS 架構、message matching 與 Agent 版本表](https://docs.px4.io/main/en/middleware/uxrce_dds)
- [PX4 v1.14 Offboard proof-of-life 規則](https://docs.px4.io/v1.14/en/flight_modes/offboard)
- [PX4 v1.15 Offboard proof-of-life 規則](https://docs.px4.io/v1.15/en/flight_modes/offboard)
- [PX4 v1.17 Offboard proof-of-life 規則](https://docs.px4.io/v1.17/en/flight_modes/offboard)
- [PX4 companion computer／TELEM2／FTDI 接線](https://docs.px4.io/v1.14/en/companion_computer/pixhawk_companion)
- [PX4 d12a7dd：接收資料排空](https://github.com/PX4/PX4-Autopilot/commit/d12a7dd11da5)
- [PX4 a1cce7e：XRCE client 重構](https://github.com/PX4/PX4-Autopilot/commit/a1cce7e961df)
- [PX4 3169dc6／PR #26161：高輸入負載 stall 修正](https://github.com/PX4/PX4-Autopilot/commit/3169dc6b1b17d138d1e04228e400814ed79d0e63)
- [NVIDIA Xavier NX UART／DMA 功能](https://docs.nvidia.com/jetson/archives/r35.1/DeveloperGuide/text/SO/JetsonXavierNxSeries.html)
- [NVIDIA JetPack 5.1.4／L4T R35.6.0 release notes](https://docs.nvidia.com/jetson/jetpack/5.1.4/release-notes/index.html)
- [NVIDIA JetPack 5.1.5／L4T R35.6.1 release notes](https://docs.nvidia.com/jetson/jetpack/5.1.5/release-notes/index.html)
- [ROS 2 Foxy EOL 與 Ubuntu 20.04 ARM64 平台資訊](https://docs.ros.org/en/crystal/Releases/Release-Foxy-Fitzroy.html)

## 十、交接時的最短摘要

```text
目前飛控是 stock PX4 v1.15.4，UXRCE_DDS_SYNCT=0 只是診斷值。
Agent 2.4.2 與 px4_msgs release/1.15 已匹配，message mismatch 已排除。
stock v1.15.4 會在活著的 session 內同步停約 1 秒；20 Hz NX→PX4 非控制輸入會讓
PX4→NX 完全停止，需重啟 Agent。
上游 v1.18 beta 的 3169dc6 已重新加入 RX burst drain，與本機症狀高度吻合。
先做 stock 當日基準；有 FTDI 就先隔離 ttyTHS1；再測現有 v1.15.4 d12 候選版。
現有候選版只作診斷，不等於新版完整修正。
手動 Offboard／手動 ARM 仍不能省略 >2 Hz heartbeat、loss action、RC failsafe 與 estimator。
任何步驟出現 output 歸零、session 重建、UART error 或意外解鎖，立即停止。
```
