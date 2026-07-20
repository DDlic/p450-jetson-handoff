# Jetson Xavier NX 工作歷程與已排除事項

## 時間線

### 原始系統

- AMOV P450 使用 Jetson Xavier NX。
- 原系統 Ubuntu 18.04.6、L4T R32.4.4、Kernel 4.9.140-tegra。
- 原本 128 GB microSD 卡保留。

### 硬體確認

由 `/proc/device-tree/model` 與 compatible 確認：

```text
NVIDIA Jetson Xavier NX Developer Kit
P3668-0000
P3509-0000
Tegra194
```

因此不是 Orin NX、Nano、TX2、AGX Xavier，也不是 P3668-0001／P3668-0003 eMMC 生產模組。

### 系統方案決定

曾考慮 Ubuntu 22.04 原生安裝、論壇強制升級、ROS 2 Humble 原生與容器方案。

最後決定：

```text
JetPack 5.1.4 / Ubuntu 20.04 宿主
+ Ubuntu 22.04 / ROS 2 Humble ARM64 container
```

理由：保留 Xavier NX 官方硬體驅動、Wi-Fi、USB、UART、CUDA 與 JetPack 5 穩定性；ROS 2 Humble 放在容器內。

### SD 映像

- 官方套件：`JP514-xnx-sd-card-image_b11`
- 內含：`sd-blob`
- 影像大小約 17,633,280 KB
- 已使用 balenaEtcher 寫入 Kingston 512 GB microSD
- Etcher 顯示燒錄成功，但是否完成獨立 Validate 尚未明確保存。

### QSPI

- Ubuntu 22.04 桌機可用，x86_64。
- R35.6.0 BSP 已下載，約 732 MB。
- 預期位置：`~/nvidia/JP514/Linux_for_Tegra`。
- 曾執行 QSPI-only 刷寫。
- 刷後看到 `Jetson UEFI firmware version 6.0-37391689`，表示 R35.6.0 UEFI 能啟動。

### 開機失敗

插入 JP5 SD 後：

- UEFI 可看到 SD/GPT 區塊，`map -r` 有 BLK0～BLK11。
- `UEFI eMMC Device` 和 `UEFI NVIDIA eMMC Kernel Boot` 都回到 Boot Manager。
- `L4T Boot Mode: ExtLinux` 已正確。
- `OS chain A status: Normal` 已正確。
- 之後出現 PXE/HTTP 網路開機 fallback。

## 已排除或不可誤判的事項

### 不是因為 eMMC 版本

P3668-0000 是 microSD 開發版。UEFI 顯示 eMMC 字樣不是實體模組判斷依據。

### 不是因為用了 Etcher

NVIDIA 官方對 Xavier NX SD image 也建議使用 Etcher。

### 512 GB 尚未被證明是問題

官方沒有列 512 GB 為禁止容量。只有將同一個 JP5 image 寫到 64/128 GB 測試卡後，才可排除卡容量／卡片控制器相容性。

### 原本 128 GB 舊卡不能當成 JP5 測試

原卡是 R32/JetPack 4。現在 QSPI 是 R35/JetPack 5；舊卡回到 Boot Manager 屬於版本不匹配，不能推論 512 GB 有問題。

## 當前最合理的診斷樹

```text
R35.6.0 UEFI 可以啟動
        ↓
UEFI 可以看到 SD GPT/BLK
        ↓
若 JP5 SD 仍無法 boot
        ├─ 128 GB 是舊 R32 卡？→ 不能作為容量測試
        ├─ 128 GB 也燒同一 JP5 image？→ 容量因素大致排除
        ├─ Etcher 未完成 Validate？→ 重新驗證映像/卡
        ├─ QSPI log 有錯誤？→ 重新刷 QSPI
        └─ QSPI log 成功且多張 JP5 卡都失敗？→ 檢查 SD boot image/完整 QSPI+SD 流程
```

## 後續飛行相關需求

系統開機後優先驗證：

1. Wi-Fi AP 可建立、可連線、重開機後可恢復。
2. SSH 可從 Windows 筆電連入。
3. Pixhawk USB 或 UART 可被辨識。
4. Micro XRCE-DDS Agent 可與 PX4 通訊。
5. ROS 2 可持續取得 `/fmu/out/*`。
6. 儲存 PX4 ULog。
7. 無槳測試內部 RC Kill Switch。
8. 抓取定高／定點模式資料，分析氣壓計、震動、EKF、GPS 與控制輸出。
9. 第一次自動飛行只做起飛、短暫停留、降落。

不要一開始就做複雜航點或長時間飛行。
