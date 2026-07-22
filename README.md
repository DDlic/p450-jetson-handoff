# AMOV P450 Jetson Xavier NX Handoff

本 repository 保存 P450 Jetson Xavier NX 的系統重建、刷寫與後續 ROS/PX4 整合交接文件。

## 目前狀態

Jetson Xavier NX 已完成 JetPack 5.1.4／L4T R35.6.0 eMMC 完整刷寫，並成功進入 Ubuntu 圖形介面。

目前硬體判定以 Recovery EEPROM 為準：P3668-0001、eMMC、Board ID 3668、SKU 0001。

## 閱讀順序

1. `P450_PROGRESS_2026-07-22_ROS2_OFFLINE.md`
2. `JETSON_HANDOFF_MASTER.md`
3. `P450_PROGRESS_2026-07-20.md`
4. `JETSON_HANDOFF_HISTORY.md`
5. `JETSON_HANDOFF_COMMANDS.md`
6. `JETSON_HANDOFF_PROMPT_FOR_CODEX_CLI.md`

## 注意

- 不要格式化原本 128 GB 舊 microSD。
- 不要使用 Orin BSP 或一般 Ubuntu ISO。
- 不要把 `.img`、BSP archive、log、密碼、token 或 key 提交到 Git。
- 大型映像與刷寫日志已由 `.gitignore` 排除。
