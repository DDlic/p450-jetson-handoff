# AMOV P450 Jetson Xavier NX 交接總覽

最後更新：2026-07-20（Asia/Taipei）

這份文件供 Ubuntu Codex CLI 或其他 AI 接手 P450 機載 Jetson Xavier NX 的系統重建工作。請以目前停點為起點，不要重新猜硬體型號、不要重複已完成的步驟，也不要在未確認輸出前直接刷機。

## 1. 專案目標

AMOV P450 無人機整合：

- Pixhawk 6C
- PX4 v1.14.3
- Jetson Xavier NX
- ROS 2 Humble
- `px4_msgs`、`px4_ros_com`
- Micro XRCE-DDS Agent
- 後續 Offboard 起降測試

建議的最終架構：

```text
Jetson Xavier NX
└─ JetPack 5.1.4 / Ubuntu 20.04 宿主
   ├─ Wi-Fi AP / SSH
   ├─ Pixhawk USB 或 UART
   ├─ Micro XRCE-DDS Agent
   └─ ARM64 Docker
      └─ Ubuntu 22.04 / ROS 2 Humble
         ├─ px4_msgs
         ├─ px4_ros_com
         └─ Offboard 節點
```

注意：這不是在 Xavier NX 上使用 JetPack 6。Xavier NX 的官方支援路線是 JetPack 5 / Ubuntu 20.04；Ubuntu 22.04 / ROS 2 Humble 放在容器內。

## 2. 已確認的硬體身份

已由原系統的 `/proc/device-tree`、model 與 compatible 輸出確認：

```text
Model: NVIDIA Jetson Xavier NX Developer Kit
Module: P3668-0000
Carrier: P3509-0000
SoC: Tegra194
Device tree: tegra194-p3668-all-p3509-0000.dts
```

曾看到的 compatible 包含：

```text
nvidia,p3668-0000
nvidia,p3509-0000+p3668-0000
nvidia,tegra194
```

結論：這是 P3668-0000 microSD 開發版，不是 P3668-0001／P3668-0003 eMMC 生產版。

UEFI Boot Manager 顯示 `UEFI eMMC Device` 不足以證明實體模組有 eMMC；料號 `P3668-0000` 才是關鍵判斷依據。

NVIDIA 對應設定：

```text
正確：jetson-xavier-nx-devkit
錯誤：jetson-xavier-nx-devkit-emmc
```

## 3. 舊系統狀態

原本 128 GB microSD 卡內容：

```text
Ubuntu 18.04.6 LTS
L4T R32.4.4
JetPack 4 時代
Kernel 4.9.140-tegra
root: /dev/mmcblk0p1
```

這張舊卡要保留，除非使用者明確同意格式化或重新燒錄。

目前 QSPI 已升到 JetPack 5 / R35 世代後，舊 R32 卡無法啟動是預期的版本不相容，不代表舊卡損壞。NVIDIA 文件指出，從 JetPack 5 回到 JetPack 4 必須重新刷回舊版 bootloader。

## 4. 新系統與桌機資料

Ubuntu 刷機桌機：

```text
Ubuntu 22.04.5 LTS
x86_64
user: wilson
root filesystem: /dev/nvme0n1p5
可用空間約 338 GB
```

桌機檔案：

```text
BSP archive:
/home/wilson/下載/Jetson_Linux_R35.6.0_aarch64.tbz2

預期 BSP 目錄:
/home/wilson/nvidia/JP514/Linux_for_Tegra
```

下載的 BSP 大小約 732 MB。

目前先維持桌機 Ubuntu 22.04，不要重灌或降版。若 R35.6.0 刷寫腳本在 22.04 發生明確相容性錯誤，再考慮 Ubuntu 20.04 Live USB。

## 5. SD 映像資料

Windows 上準備的官方映像：

```text
JP514-xnx-sd-card-image_b11
```

壓縮檔內的映像檔名稱：

```text
sd-blob
```

Windows 顯示的大小約：

```text
17,633,280 KB
```

這是 JetPack 5.1.4 Xavier NX SD 映像，不是一般 Ubuntu ARM64 映像，也不是 Orin 映像。

曾使用 balenaEtcher 將映像寫入 Kingston 512 GB microSD，Etcher 顯示「燒錄成功」。但先前畫面不清楚是否另外完成 Validate，因此若問題持續，需區分「寫入完成」與「驗證成功」。

## 6. QSPI 與 UEFI 現況

曾用 Ubuntu 22.04 桌機搭配 R35.6.0 BSP 進行 QSPI-only 刷寫，使用方向為：

```text
P3668-0000 + P3509-0000
R35.6.0
QSPI-only
```

刷寫後能看到：

```text
Jetson UEFI firmware
version 6.0-37391689
built on 2024-08-28
```

這表示 QSPI 至少已能啟動 R35.6.0 UEFI。畫面中的 `WARNING: Test Key is used` 對開發板屬正常警告，不是故障原因。

## 7. 目前開機故障

插入 Kingston 512 GB JP5 SD 卡後：

- UEFI 能偵測到 GPT 分割區。
- UEFI Shell 執行 `map -r` 曾列出 `BLK0` 到 `BLK11`。
- 沒有出現可用的 `FS0:`。
- Boot Manager 顯示 `UEFI eMMC Device`、`UEFI NVIDIA eMMC Kernel Boot`、PXE／HTTP boot 與 `UEFI Shell`。
- 選擇本機兩個 boot 項目後都回到 Boot Manager。
- `L4T Boot Mode` 已設為 `ExtLinux`。
- `OS chain A status` 已設為 `Normal`。
- 之後會看到 `Error: Could not detect network connection.`

這是本機開機失敗後進入 PXE／HTTP 網路開機 fallback，不是目前 Wi-Fi AP 測試結果。

## 8. 容量判斷

512 GB 並沒有被 NVIDIA 文件列為禁止容量。官方 R35.6.0 只列出完整 JetPack 建議至少 64 GB，沒有列出 512 GB 上限。

但是：

- 如果 128 GB 只是原本的 Ubuntu 18.04/R32 卡，它不能作為 JP5 容量測試。
- 只有把同一個 JP514 `sd-blob` 映像燒到 128 GB 後仍失敗，才可把 512 GB 容量因素排除。

不要為了測容量而格式化原本的 128 GB 舊卡，除非使用者明確同意。

## 9. 目前停點與下一步

目前應回到 Ubuntu 22.04 桌機，重新從只讀檢查開始：

1. 確認桌機是 Ubuntu 22.04 / x86_64。
2. 確認 R35.6.0 BSP 路徑存在。
3. 確認 `jetson-xavier-nx-devkit-qspi.conf` 和相關 symlink 指向正確 P3509/P3668 設定。
4. 使用之前已成功進入 Recovery 的同一種硬體方法，不要自行猜 J14 腳位。
5. `lsusb` 確認 `0955:7e19`。
6. 保存舊 log，重新刷 QSPI-only，建立新的 log。
7. QSPI 成功後才插入 JP514 SD 卡測試。

第一階段命令請見 `JETSON_HANDOFF_COMMANDS.md`。目前不要直接執行 `flash.sh`，先貼出設定檔與 symlink 輸出。

## 10. 不可做的事

- 不要使用 `jetson-xavier-nx-devkit-emmc`。
- 不要使用 Orin BSP 或 Orin SD 映像。
- 不要把一般 Ubuntu 22.04 ARM64 ISO 燒進 NX。
- 不要在舊系統內使用不存在的 `/dev/mtd0` 方法。
- 不要執行 `do-release-upgrade`。
- 不要格式化原本 128 GB 舊卡。
- 不要在未確認載板實體標示前短接未知 J14 腳位。
- 不要在未確認輸出前直接進行完整 QSPI+SD 或整機 flash。
- 不要重複修改已正確的 `ExtLinux` 和 `OS chain A Normal`。

## 11. 後續驗證順序

系統成功開機後：

1. Ubuntu / L4T / kernel / root device
2. Wi-Fi AP 與 SSH
3. Pixhawk USB/UART
4. Micro XRCE-DDS Agent
5. ROS 2 Humble container
6. `/fmu/out/*` topic 與 ULog
7. 無槳 Kill Switch
8. 定高、定點、氣壓計、震動與 EKF 資料
9. 自動起飛、短暫停留、降落
10. 最後才做更複雜的 Offboard 航點或軌跡

## 官方參考

- [NVIDIA Xavier NX 模組與刷寫設定](https://docs.nvidia.com/jetson/archives/r35.1/DeveloperGuide/text/IN/QuickStart.html)
- [NVIDIA Xavier NX SD 卡與 JetPack 4→5 升級](https://docs.nvidia.com/jetson/archives/r35.5.0/DeveloperGuide/SD/FlashingSupport.html)
- [NVIDIA R35.6.0 Release Notes](https://docs.nvidia.com/jetson/archives/r35.6.0/ReleaseNotes/Jetson_Linux_Release_Notes_r35.6.0.pdf)
