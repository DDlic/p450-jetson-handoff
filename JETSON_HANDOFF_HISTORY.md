# Jetson Xavier NX 工作歷程

最後更新：2026-07-20（Asia/Taipei）

## 原始系統與保存資料

- P450 原本使用 Jetson Xavier NX。
- 原本保存的 128 GB microSD 是 Ubuntu 18.04.6／L4T R32.4.4／JetPack 4 世代。
- 128 GB 舊卡未格式化，仍須保留。
- 另有 Kingston 512 GB JP5 SD 映像測試紀錄，但它不是本次成功開機來源。

## 初期判斷與修正

初期依舊系統 device-tree 將裝置判定為 P3668-0000 microSD 版本，因此先執行了 `jetson-xavier-nx-devkit-qspi` QSPI-only 刷寫，並嘗試從 SD 啟動。

後續 Recovery EEPROM 輸出反覆顯示：

```text
Board ID(3668) version(301) sku(0001) revision(G.0)
```

UEFI `map -r` 也顯示 `eMMC(0x0)` 與 `FS2:`。進入 `FS2:` 後可看到完整 Linux rootfs。這些是比舊 device-tree 更直接的硬體與儲存媒體證據，因此更正為 P3668-0001 eMMC 版本。

NVIDIA 對應設定由：

```text
jetson-xavier-nx-devkit-qspi
```

更正為完整 eMMC 刷寫：

```text
jetson-xavier-nx-devkit-emmc mmcblk0p1
```

## 刷寫時間線

### 1. Recovery 確認

主機成功辨識：

```text
0955:7e19 NVIDIA Corp. APX
```

### 2. 初次 QSPI 刷寫

初次 QSPI-only 流程最後成功，但發現：

- `python` 命令不存在。
- `qspi_bootblob_ver.txt` 的 CRC32 欄位空白。
- rootfs 只有不完整檔案，`etc` 不是目錄。
- `rootfs/lib`、`rootfs/bin` 等內容缺失。

因此初次結果不能作為完整系統刷寫的準備完成證明。

### 3. 修復主機與 rootfs

安裝：

```bash
sudo apt-get install -y python-is-python3
```

重新解壓官方 R35.6.0 sample rootfs，接著執行：

```bash
sudo ./apply_binaries.sh
```

结果：

```text
L4T BSP package installation completed!
Success!
```

### 4. 清理後 QSPI 刷寫

```bash
sudo ./flash.sh jetson-xavier-nx-devkit-qspi internal \
  2>&1 | tee ~/xavier_nx_qspi_clean.log
```

结果：

```text
Flashing completed
*** The target t186ref has been flashed successfully. ***
```

同时產生有效 CRC32：

```text
BYTES:85 CRC32:9DE52483
```

### 5. UEFI 開機排查

UEFI Shell：

```text
map -r
FS2:
dir
```

`FS2:` 顯示 `bin`、`boot`、`etc`、`usr`、`var` 等 Linux rootfs，確認 eMMC 內已有舊系統。新的 R35.6.0 QSPI 與舊 eMMC rootfs 不匹配，因此 Boot Manager 中的舊 boot 項目無法成功啟動。

### 6. 正確 eMMC 完整刷寫

```bash
sudo ./flash.sh jetson-xavier-nx-devkit-emmc mmcblk0p1 \
  2>&1 | tee ~/xavier_nx_emmc_clean.log
```

日志確認：

```text
Name: jetson-xavier-nx-devkit-emmc
flash_l4t_t194_spi_emmc_p3668.xml
system.img built successfully.
Writing partition APP with system.img
Writing partition esp with esp.img
Flashing completed
*** The target t186ref has been flashed successfully. ***
```

### 7. 最終結果

刷寫程序執行 `Coldbooting the device` 後，移除 Recovery USB、保持供電，Jetson 已進入 Ubuntu 圖形介面。

## 已排除事項

- 不是單純 SD 卡容量問題。
- 不是 Etcher 本身造成的本次 eMMC 開機問題。
- 不是 QSPI 燒錄失敗；QSPI 與 eMMC 完整刷寫均有成功訊息。
- `Warning: pub_key.key is not found` 是未熔斷開發板使用測試金鑰時的非致命警告。
- `gzip: kernel/Image: not in gzip format` 與 DT overlay warning 在成功流程中出現，未阻止刷寫。

## 目前進度

已完成：

- BSP rootfs 修復
- Python/CRC32 修復
- QSPI 刷寫
- eMMC system image 產生
- eMMC 完整刷寫
- Ubuntu 圖形介面開機

待完成：

- L4T／Kernel／root device 驗證
- Wi-Fi、Ethernet、SSH
- Pixhawk 6C USB/UART
- ROS 2 Humble ARM64 容器
- Micro XRCE-DDS Agent
- PX4 topic、ULog 與無槳飛行前測試
