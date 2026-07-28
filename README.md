# AMOV P450 Jetson Xavier NX Handoff

本 repository 保存 P450 Jetson Xavier NX 的系統重建、刷寫與後續 ROS/PX4 整合交接文件。

## 目前狀態

Jetson Xavier NX 已完成 JetPack 5.1.4／L4T R35.6.0 eMMC 完整刷寫，並成功進入 Ubuntu 圖形介面。

目前硬體判定以 Recovery EEPROM 為準：P3668-0001、eMMC、Board ID 3668、SKU 0001。

2026-07-28 最新硬體覆核：系統仍由 eMMC `/dev/mmcblk0p1` 開機；側邊 microSD 已由 SDMMC3 (`3440000.sdhci`) 正常辨識為 `/dev/mmcblk1`，目前卡片保持插入並掛載使用。啟用的 DTB 為 `/boot/dtb/p450-p3668-0001-p3509-0000-sdmmc3-wifi.dtb`，`extlinux.conf` 預設項目為 `p450-sdmmc3`。SD 設定固定 3.3 V、停用 1.8 V 切換，最高時脈 50 MHz；本次重開後未再看到 `Data CRC error`。開機仍保留 GPT 備份表位置警告，不得執行 GPT 修復、格式化或整碟寫入。

2026-07-28 Wi-Fi 已完成修正：外接 TP-Link USB 無線網卡使用 `wlan1`／`rtl88x2bu`，`rfkill` 顯示沒有 hard/soft block，已能掃描到 AP，且目前網路已由有線切換為 `wlan1`。內建 Intel 8265 的 `wlan0`／`iwlwifi` 持續回報 hard block，會讓 NetworkManager 全域 Wi-Fi 維持 disabled；已以 `/etc/modprobe.d/p450-disable-iwlwifi.conf` 持久停用內建 `iwlwifi`，並重新生成 initramfs。這不影響外接 `wlan1`；若要恢復內建 Wi-Fi，需移除該 blacklist 並重新生成 initramfs。

2026-07-22 歷史檢查：在 force-probe 啟用前，一般 card-detect 模式下 128 GB 與 512 GB 卡都沒有出現 `/dev/mmcblk1`。512 GB 卡經 USB 讀卡機可辨識為約 500 GB 的 `/dev/sda`，並確認內容是 JetPack 5.1.4／L4T R35.6.0 映像；該卡的 GPT 備份表位置有警告，目前未修復、未寫入。

USB 手機網路在最近一次重開機後可快速連線。2026-07-23 已在線完成原生 ROS 2 Foxy、Micro XRCE-DDS Agent v2.4.2、`px4_msgs` 與 `px4_ros_com` 安裝／建置；目前尚未啟動飛控通訊測試。

最新下一步指引：`P450_PROGRESS_2026-07-24_NEXT.md`。目前優先確認 Pixhawk 與 NX 的直接 USB/UART/網路 transport，再設定 uXRCE-DDS；不要重刷系統或直接進行飛行測試。

## 本週目標（2026-07-23）

本週大目標是先使用 Jetson 宿主上的原生 ROS 2 Foxy 完成一次自動飛行實驗，範圍先限定為起飛、短暫停留、降落。

在 ROS 2 與自動飛行之前，必須先完成 Pixhawk 飛控與 NX 的直接通訊驗證。已確認的「筆電／P450 Wi-Fi → TCP/MAVLink → Pixhawk」不能直接視為「Pixhawk ↔ NX」已通訊；NX 仍需先驗證 USB 或明確確認的 UART，再驗證 uXRCE-DDS。

## 閱讀順序

1. `P450_PROGRESS_2026-07-24_NEXT.md`
2. `P450_PROGRESS_2026-07-22_ROS2_OFFLINE.md`
3. `JETSON_HANDOFF_MASTER.md`
4. `P450_PROGRESS_2026-07-20.md`
5. `JETSON_HANDOFF_HISTORY.md`
6. `JETSON_HANDOFF_COMMANDS.md`
7. `JETSON_HANDOFF_PROMPT_FOR_CODEX_CLI.md`

## 注意

- 不要格式化原本 128 GB 舊 microSD。
- 不要使用 Orin BSP 或一般 Ubuntu ISO。
- 不要把 `.img`、BSP archive、log、密碼、token 或 key 提交到 Git。
- 大型映像與刷寫日志已由 `.gitignore` 排除。
