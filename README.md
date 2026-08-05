# AMOV P450 Jetson Xavier NX Handoff

本 repository 保存 P450 Jetson Xavier NX 的系統重建、刷寫與後續 ROS/PX4 整合交接文件。

## 目前狀態

Jetson Xavier NX 已完成 JetPack 5.1.4／L4T R35.6.0 eMMC 完整刷寫，並成功進入 Ubuntu 圖形介面。

目前硬體判定以 Recovery EEPROM 為準：P3668-0001、eMMC、Board ID 3668、SKU 0001。

2026-07-29 最新硬體覆核：系統仍由 eMMC `/dev/mmcblk0p1` 開機；側邊 microSD 已由 SDMMC3 (`3440000.sdhci`) 正常辨識為 `/dev/mmcblk1`。128 GB 卡已清除舊映像並建立單一 ext4 `P450_DATA`；目前以 UUID 固定掛載於 `/media/p450/P450_DATA`，建置完成後仍可用約 108 GB。`rosbags/`、`ulog/`、`builds/` 已建立並交由 `p450` 使用者寫入。啟用的 DTB 為 `/boot/dtb/p450-p3668-0001-p3509-0000-sdmmc3-wifi-uartb460800.dtb`，`extlinux.conf` 預設項目為 `p450-sdmmc3-uartb460800`；舊 `p450-sdmmc3` 保留為 fallback。SD 設定固定 3.3 V、停用 1.8 V 切換，最高時脈 50 MHz；寫讀測試後沒有 CRC 或 I/O error。

2026-07-28 Wi-Fi 已完成修正：外接 TP-Link USB 無線網卡使用 `wlan1`／`rtl88x2bu`，`rfkill` 顯示沒有 hard/soft block，已能掃描到 AP，且目前網路已由有線切換為 `wlan1`。內建 Intel 8265 的 `wlan0`／`iwlwifi` 持續回報 hard block，會讓 NetworkManager 全域 Wi-Fi 維持 disabled；已以 `/etc/modprobe.d/p450-disable-iwlwifi.conf` 持久停用內建 `iwlwifi`，並重新生成 initramfs。這不影響外接 `wlan1`；若要恢復內建 Wi-Fi，需移除該 blacklist 並重新生成 initramfs。

2026-07-22 歷史檢查：在 force-probe 啟用前，一般 card-detect 模式下 128 GB 與 512 GB 卡都沒有出現 `/dev/mmcblk1`。512 GB 卡經 USB 讀卡機可辨識為約 500 GB 的 `/dev/sda`，並確認內容是 JetPack 5.1.4／L4T R35.6.0 映像；該卡的 GPT 備份表位置有警告，目前未修復、未寫入。

USB 手機網路在最近一次重開機後可快速連線。2026-07-23 已在線完成原生 ROS 2 Foxy、Micro XRCE-DDS Agent v2.4.2、`px4_msgs` 與 `px4_ros_com` 安裝／建置。

2026-07-28 已確認 AMOV AllSpark 外殼 `UART0` 對應 Linux `/dev/ttyTHS1`，並在 Pixhawk `TELEM2` 建立 uXRCE-DDS session；ROS 2 可看到 23 個 `/fmu/*` topics，且能讀取 IMU、姿態與里程計資料。Agent 已安裝為 `p450-micro-xrce-agent.service` 並設為開機啟動。

`SER_TEL2_BAUD` 與 Agent 已由 921600 同步降為 460800。這使先前 session 存活時間由約 2.7–4.8 秒改善到約 10–23 秒，但通訊仍不合格。2026-07-29 飛控僅以 USB 供電的 120 秒複測收到 7110 筆 IMU，最大資料空窗 2904.859 ms，10 次超過 1 秒；65 秒詳細 Agent 日誌中 session 建立 10 次、關閉 9 次。USB 供電沒有消除重連，低電壓主電池不是唯一原因。

PX4 v1.14.3 另有官方原始碼缺陷：`VehicleIMU.cpp` 未設定及重置 `delta_angle_clipping`，使 ROS 2 的 `SensorCombined.gyro_clipping` 出現未初始化隨機值；v1.15 已修正。該欄位在目前韌體不可採信，但這與整個 XRCE session 反覆重建是兩個不同問題。

USB-only 詳細測試結束後，PX4 client 一度沒有自行恢復 DDS entities；由 QGC 重啟 Vehicle 後已恢復 23 個 `/fmu/*` topics，但短時間 discovery 仍出現 `23 → 2 → 16 → 23`，QGC 的 `Running, disconnected` 是重連循環中的瞬間狀態。導航抽樣顯示 GPS `fix_type=0`、0 顆衛星、水平位置／速度無效、航向不適合控制、dead reckoning 啟用，且 45 秒沒有 TimesyncStatus 樣本。測試期間始終未解鎖、未送控制指令。

2026-07-29 已修正 Jetson UARTB 在 460800 baud 的 device-tree 容差設定；重啟後 kernel 不再回報 baud out-of-range，UARTB clock 為 7,418,181 Hz。但修正後 120 秒測試最大空窗仍為 3129 ms，28 次超過 1 秒；再次重啟後 60 秒測試最大空窗 3382 ms，15 次超過 1 秒。這證明 Jetson 設定錯誤已排除，但 XRCE session 問題仍未解決。

已從 PX4 官方提交 `a1cce7e961df` 將 session ping 修正最小回補至 v1.14.3，並在 SD 上成功建立 Pixhawk 6C 韌體。成品位於 `/media/p450/P450_DATA/builds/firmware/p450-pixhawk6c-v1.14.3-xrce-ping-fix-f9bc66c6f3.px4`，SHA-256 為 `cb14d73274014385e809645dd3525e1ce0e33cf5d648c7d23324c41b822bf0bd`。

2026-08-03 機主已完成參數完整備份、刷入回補韌體及參數恢復。NX 的 10 分鐘純訂閱測試收到 42,936 筆 IMU，最大 gap 56.263 ms，所有超過 100 ms 的 gap 為 0；Agent 全程 active 且 PID 未變。另一次 120 秒詳細 Agent 測試只有起始 `create_client=1`、`session established=1`，沒有 `delete_client` 或 `session closed`，IMU 最大 gap 35.617 ms。切回 systemd Agent 後 30 秒複驗最大 gap 33.134 ms。原本週期性 XRCE session 重建在目前地面條件下已消除，通訊穩定性關卡通過。

2026-08-04 已改刷官方 PX4 v1.15.4 source build，並完成 `px4_msgs release/1.15`
對齊。43 個 DDS message types 全部一致，但實機輸出仍週期性同步停約 1 秒；詳細
Agent 測試沒有 session close/recreate，停用 `UXRCE_DDS_SYNCT` 也沒有改善。2 Hz
非控制 status 已到達 Agent 仍無效，20 Hz 會使 PX4 輸出停止直到 Agent 重啟。
已依 PX4 官方 `d12a7dd11d` 建立 v1.15.4 接收排空候選韌體；目前 XRCE continuity
與 Offboard 仍為 FAIL。詳見
[`P450_PX4_V1154_XRCE_TEST_2026-08-04.md`](P450_PX4_V1154_XRCE_TEST_2026-08-04.md)。

2026-08-05 已刷入上述 `996b1df7a1` 候選版。保留 `UXRCE_DDS_SYNCT=0` 的 60 秒
純接收仍有 1005.408 ms 最大 gap、22 次超過 500 ms、7 次超過 1 秒；Agent PID
與 topics 穩定、飛控未解鎖，但第一個 continuity gate 即 FAIL，因此未執行 2 Hz／
20 Hz 輸入。此最小 receive-drain 候選版不能作為飛行解法。

2026-08-05 已完成 PX4 v1.13.3、v1.14.3、v1.15.4、v1.16.2、v1.17.0 與
v1.18.0-beta1 的 XRCE client 原始碼對照。v1.15.4 至 v1.17.0 仍每輪只處理一次
session；v1.18 development 的官方 `3169dc6` 才重新加入 inbound burst draining、
降低 poll latency 並改善 output buffer。現有 v1.15.4 `d12a7dd` 候選版可作最小
A/B，但不等於新版完整修正。原因分級、FTDI transport 隔離、候選韌體測試順序與
NX CLI 停止條件見
[`P450_PX4_NX_XRCE_ROOT_CAUSE_AND_TEST_PLAN_2026-08-05.md`](P450_PX4_NX_XRCE_ROOT_CAUSE_AND_TEST_PLAN_2026-08-05.md)。

2026-08-05 已獲機主授權建立 Phase 4 第二代候選版。以官方 v1.15.4 為單一基底，
回移植 `3169dc6` 的 serial 共用接收排空／排程修改；clean build `1233/1233` 成功，
`board_id=56`，image `1,961,772 / 1,966,080` bytes，SHA-256 為
`cb54e73327c95f2ceb0dbd9d53c5020b9d8c76cf1c045600e6c66106576dd660`。韌體位於
[`firmware/p450-pixhawk6c-v1.15.4-xrce-full-drain-3f118ef593.px4`](firmware/p450-pixhawk6c-v1.15.4-xrce-full-drain-3f118ef593.px4)，
目前尚未刷入或實機驗證，不可稱為修復完成。

同日無槳輸入方向測試仍未通過：三段 RC 模式已確認為 STAB／ALTCTL／POSCTL，但移除發射機電池後飛控沒有偵測 RC loss；NX 的 `VehicleCommand` 可切換至 ALTCTL，外部 ARM 則未被接受。Offboard 零推力心跳在 NX 本地、DDS Agent 與 UART 發送端均連續，飛控端卻間歇回報 `offboard_control_signal_lost=true`。2026-08-04 已確認 `COM_OF_LOSS_T=1.0 s`，不是 timeout 過短；PX4 uORB 內最新 heartbeat 曾落後約 0.724 秒，較符合飛控端 XRCE 收件未及時排空。所有實體馬達步驟都被 watchdog 在解鎖前中止，馬達全程未轉；完整數據見 [`P450_POSTFLASH_XRCE_TEST_2026-08-03.md`](P450_POSTFLASH_XRCE_TEST_2026-08-03.md)。

Git repository 內也保存一份可下載副本：
[`firmware/p450-pixhawk6c-v1.14.3-xrce-ping-fix-f9bc66c6f3.px4`](firmware/p450-pixhawk6c-v1.14.3-xrce-ping-fix-f9bc66c6f3.px4)。
下載後必須先依 [`firmware/SHA256SUMS`](firmware/SHA256SUMS) 驗證；安全狀態與
刷入前提見 [`firmware/README.md`](firmware/README.md)。

PX4 v1.14 官方文件說明 XRCE-DDS 自動處理 Agent／client 時間同步，因此沒有獨立 `TimesyncStatus` 樣本不是額外阻塞條件。v1.14.3 ping 回補版曾通過 PX4→NX 輸出與 session continuity；目前已刷入的 stock v1.15.4 則重新在活 session 內出現約 1 秒輸出空窗，因此目前 XRCE continuity 仍為 FAIL。NX→PX4 Offboard heartbeat、RC loss、GPS fix、水平定位／速度、航向、failsafe 與控制流程也必須分別排除，不得概括為雙向控制已通過。

最新 XRCE 原因分析與下一步指引：
[`P450_PX4_NX_XRCE_ROOT_CAUSE_AND_TEST_PLAN_2026-08-05.md`](P450_PX4_NX_XRCE_ROOT_CAUSE_AND_TEST_PLAN_2026-08-05.md)。
供簡報與答辯使用的完整前因後果工程時間線：
[`P450_COMPLETE_ENGINEERING_TIMELINE_AND_PRESENTATION_2026-08-05.md`](P450_COMPLETE_ENGINEERING_TIMELINE_AND_PRESENTATION_2026-08-05.md)。
不要重刷系統或直接進行飛行測試。

## 本週目標（2026-07-23）

本週大目標是先使用 Jetson 宿主上的原生 ROS 2 Foxy 完成一次自動飛行實驗，範圍先限定為起飛、短暫停留、降落。

在 ROS 2 與自動飛行之前，必須先完成 Pixhawk 飛控與 NX 的直接通訊驗證。已確認的「筆電／P450 Wi-Fi → TCP/MAVLink → Pixhawk」不能直接視為「Pixhawk ↔ NX」已通訊；NX 仍需先驗證 USB 或明確確認的 UART，再驗證 uXRCE-DDS。

## 閱讀順序

1. `P450_COMPLETE_ENGINEERING_TIMELINE_AND_PRESENTATION_2026-08-05.md`
2. `P450_PX4_NX_XRCE_ROOT_CAUSE_AND_TEST_PLAN_2026-08-05.md`
3. `P450_PX4_V1154_XRCE_TEST_2026-08-04.md`
4. `P450_PROGRESS_2026-07-24_NEXT.md`
5. `P450_PROGRESS_2026-07-22_ROS2_OFFLINE.md`
6. `JETSON_HANDOFF_MASTER.md`
7. `P450_PROGRESS_2026-07-20.md`
8. `JETSON_HANDOFF_HISTORY.md`
9. `JETSON_HANDOFF_COMMANDS.md`
10. `JETSON_HANDOFF_PROMPT_FOR_CODEX_CLI.md`

## 注意

- 側邊 128 GB microSD 已依機主指示清除舊開機映像，現為單一 ext4 `P450_DATA` 資料碟；不要再把它當開機碟。
- 不要使用 Orin BSP 或一般 Ubuntu ISO。
- 不要把 `.img`、BSP archive、log、密碼、token 或 key 提交到 Git。
- 大型映像與刷寫日志已由 `.gitignore` 排除。
