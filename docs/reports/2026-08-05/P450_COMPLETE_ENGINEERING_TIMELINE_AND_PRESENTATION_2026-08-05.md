# P450／Jetson Xavier NX 完整工程歷程與簡報答辯資料

最後更新：2026-08-10（Asia/Taipei）

> **後續決策（2026-08-10）**：本文到 2026-08-05 為止的 v1.15.4 路線是歷史診斷
> 過程。最終 PX4 基線已由機主指定為 v1.14.3；其他版本的有效修正必須回補至
> v1.14.3。2026-08-10 實測已確認 ping 回補版 PX4→NX 10 分鐘 continuity PASS，
> 但 NX→PX4 2 Hz 樣本新鮮度 FAIL。最新完整結果見
> `docs/reports/2026-08-10/P450_PX4_V1143_PING_BIDIRECTIONAL_TEST_2026-08-10.md`。

## 0. 文件目的、證據界線與敏感資料處理

這份文件不是只列最終結果，而是把本專案對話中的需求變化、實際觀察、當時推論、
測試方法、被證偽的假設及下一步決策串成可供簡報與答辯使用的工程故事。

聊天平台目前沒有提供可由 NX CLI 直接匯出的逐字對話檔，因此本文件依照 Git 歷史、
本機測試報告、命令輸出與目前對話脈絡重建。數字以既有原始測試報告為準；無法由
紀錄證實的內容會明確標示，不將推論寫成事實。

對話中曾提供本機 sudo 密碼及 GitHub 登入操作。密碼、token、cookie、登入碼及其他
憑證一律不寫入本文件、不提交 Git。需要說明權限時只記為「由機主授權執行 sudo」。

## 1. 一句話摘要

原始目標是讓 AMOV P450 上的 Jetson Xavier NX 以 ROS 2 Foxy 經 Pixhawk 6C 完成一次
自動飛行。專案先修復 NX 開機與儲存，再建立 ROS 2／PX4 通訊；通訊從「完全找錯 UART」
推進到「可雙向傳輸但有 session 重建」，再推進到「session 穩定但飛控端對 ROS 輸入
出現長時間接收飢餓」。2026-08-10 的 v1.14.3 ping 回補版 10 分鐘純接收通過，但
live 2 Hz marker 在飛控端落後 58.383400 秒；目前已把問題縮小到活 session 內的 PX4
uXRCE-DDS client 接收排空與排程。下一個 v1.14.3 receive-drain 候選版已存在，但
尚未取得新的刷寫授權。

## 2. 最初需求與操作介面

1. 機主指定本機稱為「NX」，並要求全程使用台灣繁體中文溝通。
2. 第一個操作問題是中文輸入法：要求 `Shift` 切換中英、`Caps Lock` 只控制大小寫。
3. 輸入法完成後，機主授權全面檢查 NX，範圍以 Git 專案所需項目為準。
4. 機主明確要求敏感密碼不得寫入文件或上傳；此規則持續有效。
5. 週目標後來明確化為：先完成 Pixhawk ↔ NX 通訊，再以 ROS 2 Foxy 完成一次自動飛行。

這個順序很重要：若基礎平台、UART 與 DDS continuity 未先通過，直接進 Offboard 只會把
傳輸、飛控模式、定位與安全問題混在一起，無法判斷失敗層級。

## 3. NX 復原與開機基線

### 3.1 問題起點

初期 NX 有 BSP/rootfs、QSPI/eMMC 開機與舊映像混淆。處理過程先確認 Xavier NX 模組、
載板與儲存媒體，再依正確 BSP 重建 rootfs、更新 QSPI，最後完成 eMMC 完整刷寫。

### 3.2 為何不是只刷 QSPI

QSPI-only 可以更新啟動韌體，但不能替代 eMMC 上完整且匹配的 rootfs。曾經能看到 UEFI
不代表 Ubuntu 系統已正確；最後以完整 eMMC 刷寫建立可重現基線。

### 3.3 最終平台狀態

- 系統由 `/dev/mmcblk0p1` eMMC 開機。
- Ubuntu 20.04 可正常啟動。
- 舊 SD 映像不再作為系統啟動來源。
- 詳細刷寫時間線與命令保留在 `docs/history/JETSON_HANDOFF_HISTORY.md`、
  `docs/reports/2026-07-20/P450_PROGRESS_2026-07-20.md` 與
  `docs/operations/JETSON_HANDOFF_COMMANDS.md`。

簡報答辯重點：先建立可信任的 OS/BSP 基線，避免後續把 UART、Wi-Fi 或 ROS 問題錯怪給
一個不確定的開機環境。

## 4. 側邊 SD 卡與儲存策略

### 4.1 為何一開始抓不到

機主說的是 NX 側邊內建 microSD 槽，不是 USB Hub 讀卡機。初期曾更換 512 GB、128 GB
卡並做插拔觀察；這協助區分 USB storage 與 SoC SDMMC3 控制器兩條完全不同的路徑。

### 4.2 最終修正

- 啟用的控制器為 SDMMC3 (`3440000.sdhci`)。
- 128 GB 卡清除舊開機映像後建立單一 ext4。
- label：`P450_DATA`。
- UUID：`99c03936-1ba4-49e8-a8d7-b2b158418e76`。
- 固定掛載：`/media/p450/P450_DATA`。
- 64 MiB 實寫約 16 MB/s，沒有 CRC 或 I/O error。
- DTB 固定 3.3 V、停用 1.8 V 切換、最高 50 MHz；保留舊 DTB 作 fallback。

### 4.3 空間決策

NX eMMC 只有約 14 GB。ROS workspace 與系統留在 eMMC；PX4 source、ARM toolchain、
build tree、rosbag、ULog 與大型資料放到 SD。2026-08-05 建置前 eMMC 約 4.1 GB 可用，
SD 約 106 GB 可用，因此 Phase 4 也在 SD 上建置，避免 eMMC 爆滿造成系統卡死。

## 5. 網路與供電事件

1. 初期以手機 USB-C／USB 外接基地台供網，重新開機後曾短暫幾分鐘無網路。
2. 後續一次斷線實際原因是機體電池沒電，不是 ROS 安裝或網路設定損壞。
3. 充電後改用穩定有線供電，重新驗證已下載套件與安裝狀態，再繼續 ROS 流程。
4. 另完成外接 USB Wi-Fi `wlan1` 的恢復；重新開機後連線速度正常。

工程教訓：通訊失敗時要把「NX 網路」「Pixhawk 供電」「TELEM UART」「ROS DDS」分層，
不能因同一時間斷線就假設是同一原因。

## 6. ROS 2 Foxy 建置

### 6.1 方案轉折

原本準備離線安裝，因現場後來有穩定網路，改為直接線上安裝。斷電後先驗證 dpkg/apt、
ROS 套件與工作區完整性，再繼續，不直接假設半途安裝一定成功。

### 6.2 已完成項目

- ROS 2 Foxy 安裝於 `/opt/ros/foxy`。
- talker/listener 本機測試通過。
- Micro XRCE-DDS Agent v2.4.2 安裝於 `/usr/local/bin/MicroXRCEAgent`。
- systemd 服務：`p450-micro-xrce-agent.service`。
- v1.14 工作區：`/home/p450/p450_ros2_ws`。
- v1.15 對齊工作區：`/media/p450/P450_DATA/builds/p450_ros2_ws_v115`。
- v1.15 `px4_msgs release/1.15` 與 PX4 v1.15.4 的 43 個 DDS message types 對齊。

### 6.3 為何版本對齊重要

PX4 firmware 的 `dds_topics.yaml`、`px4_msgs` 與 Micro XRCE client/Agent 若跨版本不相容，
可能造成 topic 缺失或序列化錯誤。後續已逐一比對 43 個 message types，因此目前約 1 秒
空窗不能優先歸因於 message mismatch。

## 7. Pixhawk 實體連線與 UART 映射

### 7.1 一開始看到的線

機主目視 NX 外殼接有 ETH、UART0、UART1。後來確認：

- NX 外殼 `UART0` 接 Pixhawk `TELEM2`。
- NX 外殼 `UART1` 有線，但尾端收在機體線槽，沒有接設備。
- AllSpark `UART0` = Linux `/dev/ttyTHS1`。
- AllSpark `UART1` = Linux `/dev/ttyTHS0`。

早期測 `/dev/ttyTHS0` 沒資料，不代表 TELEM2 壞掉；它其實是在測未接設備的 UART1。
這是整個通訊排查中最重要的實體映射修正。

### 7.2 QGC、MAVLink 與 uXRCE 的角色分離

筆電可用 USB 連 Pixhawk 跑 QGroundControl；QGC TCP/MAVLink 與 ROS uXRCE-DDS 是不同
通道。為保留 TELEM1 給 MAVLink/QGC，TELEM2 釋放給 uXRCE：

```text
MAV_0_CONFIG  = TELEM1
MAV_1_CONFIG  = Disabled
UXRCE_DDS_CFG = TELEM2 (QGC 顯示 102)
SER_TEL2_BAUD = 460800，8N1
```

曾經因參數配置改動而無法用 QGC TCP 連飛控，這不是證明乙太網路壞掉，而是同一 serial
port 的功能分配互斥。後續以筆電 USB 作為可靠的參數恢復路徑。

## 8. 第一階段通訊：從完全不通到能看到 ROS topics

在正確 `/dev/ttyTHS1` 啟動 Agent 後：

- XRCE session 可建立。
- Agent 可建立 participant、publisher、subscriber、writer、reader。
- ROS 2 最初看到 23 個 `/fmu/*` topics（13 in、10 out）。
- `sensor_combined_listener`、`vehicle_odometry`、`vehicle_status` 可讀即時資料。
- ROS→PX4 `VehicleCommand` 曾成功將模式由 STAB 切到 ALTCTL，證明雙向路徑不是完全不通。

但「能收到資料」不是「可飛」。當時仍有 GPS 無 fix、水平位置無效、preflight 未通過等
獨立條件。

## 9. 第二階段問題：XRCE session 反覆重建

### 9.1 現象

在 PX4 v1.14.3 原始韌體上，session 約每 2.7–4.8 秒重建。降到 460800 後存活時間
改善到約 9.7–19.1 秒，但仍不合格。

代表性 65 秒 IMU 測試：

```text
messages=1891
average_hz=29.092
max_gap_ms=1614.046
gaps_over_1s=4
```

僅 USB 供電的 120 秒測試仍有最大 2904.859 ms 空窗，並曾看到整個 `/fmu/*` graph
由 23 降到 0 再恢復，因此不是單一 sensor topic 掉包，而是 session teardown/recreate。

### 9.2 排除過的假設

- 降低 Agent log：無效。
- Agent FIFO 即時排程：無效。
- 測試 duplicate-pong Agent：無效，且未安裝到正式路徑。
- 改用 USB 供電：無效，所以低電壓主電池不是唯一原因。
- 單純重開 NX／飛控：無效。

### 9.3 UART baud 的真實問題與界線

kernel 曾顯示 UARTB 460800 超出 DTB 許可範圍。加入：

```text
nvidia,adjust-baud-rates = <115200 115200 100 460800 460800 100>
```

後，baud 錯誤消失；但 120 秒測試最大 gap 仍達 3129.283 ms。結論是 DTB 修正必要，
但不是 XRCE session 問題的完整解法。

## 10. v1.14.3 session ping 回補與成功 A/B

### 10.1 原因推論

PX4 v1.14.3 會在連續漏掉短週期 ping 後自行斷線。上游 `a1cce7e961df` 在有有效雙向
payload 時略過 ping 判死、把 interval/timeout 調整到 1 秒。這與「Agent 很快回覆但
client 仍主動 delete session」相符。

### 10.2 韌體與結果

回補韌體：

```text
p450-pixhawk6c-v1.14.3-xrce-ping-fix-f9bc66c6f3.px4
source=f9bc66c6f30d8ddcceaeba2545dc9f6d0e71faf1
SHA-256=cb14d73274014385e809645dd3525e1ce0e33cf5d648c7d23324c41b822bf0bd
```

刷入前先由 QGC 匯出完整參數，重灌後恢復參數並核對。2026-08-03 實測：

```text
10 分鐘：42936 筆，71.560 Hz，最大 gap 56.263 ms，>100 ms 為 0，PASS
120 秒詳細 Agent：create=1、close=0，最大 gap 35.617 ms，PASS
整機重啟後 120 秒：最大 gap 47.477 ms，PASS
```

這證明 session ping 回補解決了「週期性 teardown/recreate」，但不代表 Offboard 心跳
與飛行安全也一起通過。

## 11. 室內靜態、RC 與安全測試

### 11.1 靜態感測器

60 秒室內靜態測試：Sensor 約 72.37 Hz；加速度模長平均 9.764 m/s²、gyro norm 平均
0.00628 rad/s、無 accelerometer clipping、四元數 norm 正常，結果 PASS。

### 11.2 飛行模式

RC 三段模式經 ROS 狀態確認：STAB、ALTCTL、POSCTL。POSCTL 室內因 local/global/home
position invalid，preflight 不通過，不得解鎖。

### 11.3 RC 通道重新配置

- `RC_MAP_FLTMODE=6`，三段模式由 `COM_FLTMODE1/2/3` 決定。
- 遙控器畫面宣稱 CH5 被飛行模式占用，但搖桿測試 CH5 無反應。
- 實測 SWA 綁 CH9 可正常動作；`RC_CHAN_CNT` 當時只有 8，因此 QGC 不會提供 CH9/10。
- CH8 為緊急停機，CH7 原作解鎖；後來依機主需求把解鎖配置到左側撥桿向右下到底。
- Offboard 模式撥桿已配置並做過機主自行確認，但不能取代 DDS heartbeat。

### 11.4 RC loss 尚未通過

發射機斷電超過 20 秒後，飛控仍顯示 `manual_control_signal_lost=false`。較可能是接收機在
失聯後 Hold 最後通道值。這項為 FAIL，飛行前仍需確認接收機型號與 failsafe 輸出。

## 12. 第三階段問題：session 活著，但 Offboard heartbeat 仍間歇失聯

### 12.1 已證明的路徑

- ROS publisher 本地迴圈可穩定到約 88 Hz，最大 gap 約 14 ms。
- Agent 收到每一組 `offboard_control_mode` 與 `vehicle_rates_setpoint`。
- Agent serial send 數量一致，最大 gap 約 18–21 ms。
- Agent 無 error、warning、session teardown。
- `VehicleCommand` 確實可改變飛控模式。

### 12.2 仍失敗的現象

即使上述路徑完整，PX4 的 `offboard_control_signal_lost` 仍會間歇變 true；20 Hz、約 88 Hz、
Best Effort、Reliable、timestamp=0 與非零 timestamp 都試過，僅改善、未根治。這把異常
縮到 PX4 client 收 serial 資料之後，到反序列化／uORB heartbeat freshness 之間。

這也是為什麼不能把問題簡化為「ROS 沒發 heartbeat」；NX 與 Agent 的證據顯示已發送。

## 13. 為何改到 PX4 v1.15.4

v1.14.3 已接近維護末端，且缺少 v1.15 的 service、message 與 client 改善。為避免一直在
舊版上疊 patch，建立官方 stock v1.15.4 source build，並建立對齊的 `px4_msgs release/1.15`。

stock v1.15.4 不再頻繁 teardown，但純接收仍在活 session 內同步出現約 1 秒空窗；加入
NX→PX4 非控制 payload 後會惡化。這表示問題從「ping 造成重建」轉成「活 session 中的
接收排程／排空不足」。

## 14. v1.15.4 第一代 RX-drain 候選版與證偽

第一代候選依上游 `d12a7dd11da5`，每輪最多呼叫 10 次
`uxr_run_session_timeout()`，以 `_pubs->num_payload_received` 是否增加決定停止。

韌體：

```text
p450-pixhawk6c-v1.15.4-xrce-rx-drain-996b1df7a1.px4
SHA-256=dbfd43085bbb4fe59744ad244a973b1243fb55d34ed36df52c9a0855be464949
```

2026-08-05 刷入後，60 秒純接收第一關：

```text
messages=2411
average_hz=40.138
max_gap_ms=1005.408
gaps_over_500ms=22
gaps_over_1s=7
Agent PID unchanged / NRestarts=0 / vehicle disarmed
result=FAIL
```

依預先定義的 stopping rule，第一關失敗後沒有跑 2 Hz／20 Hz 發送測試。這避免在已知
continuity 不合格時增加飛控輸入，亦證明第一代「用 payload counter 判空」不夠完整。

## 15. FTDI 隔離測試：為何建議、為何目前沒做

FTDI 在此指 3.3 V USB-TTL serial adapter，用來讓另一台主機直接接 TELEM2 TX/RX/GND，
隔離 AllSpark `/dev/ttyTHS1` 與 Tegra DMA。一般 NX USB-A/USB-C 直接接 Pixhawk USB-C
通常會成為 `/dev/ttyACM0` 的 USB MAVLink，不等於 FTDI TELEM2 A/B。

機主目前沒有 USB-TTL/FTDI、轉接線或可安全接 3.3 V UART 的器材，因此不勉強進行；
保留為日後硬體鑑別測試。不可把 +5 V 接入 TELEM UART。

## 16. Phase 4：第二代完整排空回移植

### 16.1 上游依據

對照 PX4 v1.15.4、v1.16.2、v1.17.0 與 v1.18 beta 後，官方
`3169dc6b1b17` 才完整加入：

- transport 有 pending input 時，不在 uORB poll 阻塞。
- 主迴圈 poll timeout 由 10 ms 降為 1 ms。
- 每輪最多排空 10 次，用 `FIONREAD` 檢查實際 transport bytes。
- best-effort output buffer 滿時先 flush、再 retry。
- transport close ownership 修正，避免重複 close fd。

第一代候選只看「已反序列化 payload counter」，可能在 transport 仍有 framing、reply 或尚未
完成 payload 時提早停止；第二代改看 UART fd 的 pending bytes，與上游新版方法一致。

### 16.2 本次移植界線

基底固定官方 tag `v1.15.4`，只帶入 serial 共用路徑；沒有移植 UDP 專用 non-blocking
socket，也沒有整版升級到 v1.18 beta。

```text
source commit=3f118ef593a45b9ac42ba7ac4cc6565c568ca5f1
patch=patches/px4-v1.15.4-uxrce-full-drain-backport.patch
firmware=firmware/p450-pixhawk6c-v1.15.4-xrce-full-drain-3f118ef593.px4
SHA-256=cb54e73327c95f2ceb0dbd9d53c5020b9d8c76cf1c045600e6c66106576dd660
```

### 16.3 建置驗證

- `make clean` 後完整 1233/1233 成功。
- ARM GCC 9.3.1 (`gcc-arm-none-eabi-9-2020-q2-update`)。
- board：PX4FMUv6C，`board_id=56`。
- `git_identity=v1.15.4-1-g3f118ef593`。
- `image_size=1,961,772`，上限 `1,966,080`，FLASH 99.78%。
- recursive submodules 無偏移，source tree clean。

這是診斷候選版，不是已驗證飛行韌體；必須刷入後通過 A/B 才能決定是否保留。

## 17. 當時規劃的 v1.15.4 實機順序（歷史）

本節是 2026-08-05 的診斷計畫，已被 2026-08-10 的 v1.14.3 最終基線決策覆寫，
不得直接照此刷入 v1.15.4。

1. 旋翼保持拆除、機體固定、穩定供電、飛控未解鎖。
2. QGC 確認已保存完整參數；刷入第二代韌體。
3. 重啟後核對 `UXRCE_DDS_CFG=102`、`SER_TEL2_BAUD=460800`、
   `MAV_1_CONFIG=0`，並核對 RC、安全、airframe 與校正。
4. NX 清潔重啟 Agent，確認唯一占用 `/dev/ttyTHS1`、PID 與 `NRestarts`。
5. 先跑 60 秒純接收。任何 gap >100 ms 即 FAIL，停止，不發 `/fmu/in/*`。
6. 60 秒通過後跑 10 分鐘純接收，要求 session/topic/PID 全程穩定。
7. 再以非控制訊息做 2 Hz，通過才做 20 Hz；停止輸入後需自行恢復。
8. 只有前述全部通過，才做無槳 Offboard heartbeat；仍不得直接自動起飛。
9. 任一時刻若意外解鎖、進 Offboard、馬達輸出、Agent 重建或 topics 消失，立即停止。

## 18. 目前仍未完成的飛行安全關卡

即使 Phase 4 修正通訊，以下仍是獨立阻塞項：

1. 室外 GPS fix、衛星數、水平位置與速度有效。
2. heading good for control、EKF 與 home position。
3. `pre_flight_checks_pass` 在實際飛行模式下通過。
4. RC receiver 失聯時不能 Hold；必須讓 PX4 正確偵測 RC loss。
5. Kill Switch、RC loss action、Offboard loss action 與 `COM_OF_LOSS_T`。
6. Offboard proof-of-life >2 Hz、正確 setpoint、heartbeat 中斷退出。
7. 無槳解鎖、模式切換、setpoint 邊界與人工接管測試。
8. 室外低高度、繫留／安全區域測試計畫與現場人員分工。

## 19. 簡報時最容易被問的問題

### Q1：為什麼花很多時間在 SD、Wi-Fi 和開機，而不是直接 ROS 飛行？

因為 NX 原本連可靠 OS、儲存與網路基線都不確定。ROS/PX4 編譯體積又會塞滿 14 GB eMMC。
先修復平台與 SD，才有可重現、可保存 log、不中途爆滿的測試環境。

### Q2：ROS topic 看得到，為什麼不能說通訊完成？

能 discovery 只代表某時刻 entity 存在。自動控制要求時間連續性；1 秒空窗已遠超 PX4
Offboard >2 Hz proof-of-life 的需求，因此「有 topic」不等於「可控制」。

### Q3：如何知道不是 NX Python 發太慢？

ROS publisher 約 88 Hz、最大 gap 約 14 ms；Agent reader 與 serial send 筆數完全一致、
最大 gap 約 21 ms，Agent 沒 error 或重建，但飛控仍回報 heartbeat loss。因此問題在 Agent
送出之後的飛控接收路徑，這是用逐層時間戳與計數器縮小範圍，不是猜測。

### Q4：v1.14.3 patch 不是已經解決了嗎？

它解決的是 client 因 session ping 判斷造成的 teardown/recreate。後來暴露的是活 session
內的 inbound 處理空窗，屬於不同 failure mode。

### Q5：為什麼不直接刷 v1.18？

整版升級會同時改變飛控行為、參數、messages、drivers 與安全邏輯，A/B 無法歸因。
機主已固定最終基線為 v1.14.3，因此現在只允許把與接收 stall 直接相關的最小修改
回補至 v1.14.3，再與已通過純接收的 ping-only 版本做單一變因 A/B。過去 v1.15.4
路線只保留作根因診斷。

### Q6：第一代 drain patch 為什麼失敗？

它用「已收到 payload bytes 是否增加」判斷 queue 是否空；但 UART 可能仍有 framing、reply
或未完成資料。第二代直接用 `FIONREAD` 看 transport pending bytes，並降低 poll latency。

### Q7：目前可不可以飛？

不可以。v1.14.3 ping-only 版雖通過 10 分鐘 PX4→NX 純接收，但 2 Hz NX→PX4
新鮮度已明確 FAIL；20 Hz 與 Offboard 因此沒有執行。RC loss、GPS／定位、heading、
preflight、Kill Switch 與 Offboard loss 也仍需各自驗證。

## 20. 原始證據索引

- NX 刷寫與恢復：`docs/history/JETSON_HANDOFF_HISTORY.md`
- ROS、SD、UART、Wi-Fi 與 7 月測試：
  `docs/reports/2026-07-22/P450_PROGRESS_2026-07-22_ROS2_OFFLINE.md`、
  `docs/reports/2026-07-24/P450_PROGRESS_2026-07-24_NEXT.md`
- v1.14.3 刷入後完整數據：`docs/reports/2026-08-03/P450_POSTFLASH_XRCE_TEST_2026-08-03.md`
- v1.15.4 stock／第一候選：`docs/reports/2026-08-04/P450_PX4_V1154_XRCE_TEST_2026-08-04.md`
- v1.14.3 ping-only 最終雙向驗證：
  `docs/reports/2026-08-10/P450_PX4_V1143_PING_BIDIRECTIONAL_TEST_2026-08-10.md`
- 2026-08-10 原始證據：`evidence/20260810_163557_px4_v1143_ping_postflash/`
- 根因分級與停止規則：
  `docs/reports/2026-08-05/P450_PX4_NX_XRCE_ROOT_CAUSE_AND_TEST_PLAN_2026-08-05.md`
- 可重現韌體與 SHA：`firmware/README.md`、`firmware/SHA256SUMS`
- 原始 console 範例：`docs/raw/captures/px4_uxrce_dds_console_latest.txt`

## 21. 文件可信度標記

- `PASS/FAIL`：有命令輸出與數值門檻。
- 「機主確認」：由現場目視、QGC 或遙控器操作回報，NX 無法獨立量測。
- 「推論」：由多層證據支持，但仍需 A/B 才能定案。
- 「未測」：不得在簡報中說成已完成。

## 22. 2026-08-10 v1.14.3 回復與雙向驗證

機主依權威決策刷回 v1.14.3 ping 回補版，QGC 確認 source `f9bc66c6f3`，NX 則切回
`px4_msgs release/1.14` 對應 graph。清除舊 ROS discovery cache 後，正式 10 分鐘
純接收得到 42,718 筆、平均 71.196 Hz、最大 gap 38.913 ms、0 次超過 100 ms，
Agent PID 與 restart count 不變。

接著只發布 2 Hz 非控制 `OnboardComputerStatus`。PX4→NX 輸出仍穩定，但 QGC 起初
兩次顯示 `never published`。message SHA、NX 本地 echo、Agent DataReader 與 serial
write call 均通過後，live marker 終於在 PX4 uORB 出現；然而該樣本在 NX 仍發布時
已落後 58.383400 秒。這個結果排除「完全斷線」，並把失敗定義得更精確：飛控端沒有
持續即時消費 2 Hz 輸入。

因此目前最重要的答辯表述是：**ping 修正解決 session continuity，卻沒有解決
inbound freshness；2 Hz gate 已以實機證據判定 FAIL。**所有 publisher 已停止，
20 Hz／Offboard 未測。下一個 v1.14.3 receive-drain＋ping 候選版只能在機主重新明確
授權後刷入並做單一變因 A/B，不能把「已建置」說成「已修復」。
