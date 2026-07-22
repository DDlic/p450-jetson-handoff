# 給 Ubuntu Codex CLI 的目前接手提示詞

請接手 AMOV P450 的 Jetson Xavier NX 後續驗證與 ROS/PX4 整合工作。使用繁體中文，逐段帶使用者執行命令；高風險操作先說明影響，並等待輸出確認。

## 硬體與系統現況

- Jetson Xavier NX，Tegra194
- Recovery EEPROM：Board ID 3668、SKU 0001、revision G.0
- 實際儲存媒體：eMMC
- 正確完整刷寫設定：`jetson-xavier-nx-devkit-emmc mmcblk0p1`
- BSP：Jetson Linux R35.6.0／JetPack 5.1.4
- Jetson 已完成 eMMC 刷寫並進入 Ubuntu 圖形介面
- ROS 2 目前採 Ubuntu 20.04 宿主原生 Foxy 離線安裝；Humble 容器暫不執行
- 原本 128 GB 舊 microSD 必須保留，不要格式化

注意：舊交接資料曾將裝置寫成 P3668-0000 microSD；新的 Recovery EEPROM、UEFI `eMMC(0x0)`、最終刷寫設定與 `p3668-0001` DTB 已證明該判斷過時。後續以 P3668-0001/eMMC 為準。

## 已完成，不要重複

- 安裝 `python-is-python3`
- 重新解壓 R35.6.0 sample rootfs
- 執行 `apply_binaries.sh`
- QSPI-only 刷寫
- eMMC 完整刷寫
- Ubuntu 圖形介面開機

成功日志位於主機：

```text
/home/wilson/xavier_nx_qspi_clean.log
/home/wilson/xavier_nx_emmc_clean.log
```

## 現在先執行的驗證

在 Jetson Ubuntu：

```bash
cat /etc/os-release
cat /etc/nv_tegra_release
uname -a
findmnt /
lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINTS
```

接著依序驗證：

1. Ethernet、Wi-Fi、SSH。
2. 從 USB 重新複製 ROS 2 Foxy 離線包，確認 `git` 套件大小與 SHA256。
3. 原生安裝並驗證 ROS 2 Foxy。
4. Pixhawk 6C USB/UART。
5. Micro XRCE-DDS Agent。
6. `px4_msgs`、`px4_ros_com` 與 `/fmu/out/*`。
7. PX4 ULog、Kill Switch、定高/定點與失聯處置。
8. 無槳後，才進行起飛、短暫停留、降落測試。

不要在宿主執行 `do-release-upgrade`。不要使用 Orin BSP、不要再刷 SD、不要執行 `/dev/mtd0` 舊方法。
