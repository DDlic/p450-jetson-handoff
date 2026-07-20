# Jetson Xavier NX 目前命令與後續作業

最後更新：2026-07-20（Asia/Taipei）

目前 Jetson 已由 eMMC 成功進入 Ubuntu。以下命令是開機後驗證與 P450 後續作業，不要重新執行已完成的刷寫命令。

## A. Ubuntu 與儲存媒體驗證

在 Jetson Ubuntu 執行：

```bash
cat /etc/os-release
cat /etc/nv_tegra_release
uname -a
findmnt /
lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINTS
```

預期方向：

```text
Ubuntu 20.04
L4T R35.6.0
Kernel 5.10.216-tegra
根檔案系統位於 eMMC
```

## B. 網路與 SSH

先檢查裝置與連線：

```bash
ip -br link
ip -br addr
nmcli device status
```

若使用 Ethernet，先確認取得 IP，再從筆電測試：

```bash
ssh <jetson-user>@<jetson-ip>
```

若要建立 Wi-Fi AP，先確認 NetworkManager 與 Wi-Fi 介面正常，再建立 AP；不要在尚未確認基本網路前修改複雜的 systemd 或 NetworkManager 設定。

## C. Pixhawk 6C 連接確認

插入 Pixhawk USB 後，在 Jetson 執行：

```bash
lsusb
dmesg --follow
```

另開終端確認 serial 裝置：

```bash
ls -l /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
groups
```

若使用 UART，先確認實際載板腳位、電壓與線序，不要直接猜測 P450 的 UART header。

## D. ROS 2 Humble 容器方向

目標是保留 JetPack 5／Ubuntu 20.04 宿主，將 ROS 2 Humble 放在 ARM64 容器內。先確認 Docker：

```bash
docker --version
docker info
```

不要在 Xavier NX 宿主直接執行 Ubuntu 20.04 → 22.04 `do-release-upgrade`，以免破壞 NVIDIA 驅動、CUDA、GUI 或 kernel 套件。

## E. Micro XRCE-DDS 與 PX4 驗證順序

1. 建立或安裝 ARM64 ROS 2 Humble 容器。
2. 建置 `px4_msgs`。
3. 建置 `px4_ros_com`。
4. 啟動 Micro XRCE-DDS Agent。
5. 確認 `/fmu/out/*` topic 可持續接收。
6. 保存 PX4 ULog。
7. 無槳測試 Kill Switch、失聯處置與定高/定點資料。
8. 最後才做起飛、短暫停留、降落。

飛行測試前必須拆槳或固定機體。

## F. 已完成的刷寫命令（僅供紀錄，不要重複執行）

### Rootfs BSP 套用

```bash
cd ~/nvidia/JP514/Linux_for_Tegra
sudo ./apply_binaries.sh
```

### QSPI-only

```bash
sudo ./flash.sh jetson-xavier-nx-devkit-qspi internal \
  2>&1 | tee ~/xavier_nx_qspi_clean.log
```

### 最終 eMMC 完整刷寫

```bash
sudo ./flash.sh jetson-xavier-nx-devkit-emmc mmcblk0p1 \
  2>&1 | tee ~/xavier_nx_emmc_clean.log
```

最終 eMMC 刷寫日志必須包含：

```text
system.img built successfully.
Flashing completed
*** The target t186ref has been flashed successfully. ***
```

## G. 重要保存規則

- 不要格式化原本 128 GB 舊 microSD。
- 不要使用 Orin BSP 或 Orin 映像。
- 不要使用舊系統內的 `/dev/mtd0` 方法。
- 不要把 `jetson-xavier-nx-devkit-qspi` 當作完整 eMMC 系統刷寫設定。
- 不要在未確認裝置名稱前使用 `dd`、Etcher 或其他整碟寫入工具。
- 不要把密碼、token、`.pem`、`.key` 或大型映像提交到 Git。
