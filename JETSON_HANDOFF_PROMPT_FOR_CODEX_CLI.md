# 給 Ubuntu Codex CLI 的目前接手提示詞

請接手 AMOV P450 的 Jetson Xavier NX 後續驗證與 ROS/PX4 整合工作。使用繁體中文，逐段帶使用者執行命令；高風險操作先說明影響，並等待輸出確認。

## 硬體與系統現況

- Jetson Xavier NX，Tegra194
- Recovery EEPROM：Board ID 3668、SKU 0001、revision G.0
- 實際儲存媒體：eMMC
- 正確完整刷寫設定：`jetson-xavier-nx-devkit-emmc mmcblk0p1`
- BSP：Jetson Linux R35.6.0／JetPack 5.1.4
- Jetson 已完成 eMMC 刷寫並進入 Ubuntu 圖形介面
- ROS 2 目前採 Ubuntu 20.04 宿主原生 Foxy 在線安裝；離線包作為備援，Humble 容器暫不執行
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
2. Pixhawk 6C USB/UART。
3. Micro XRCE-DDS Agent 與實際 transport。
4. `px4_msgs`、`px4_ros_com` 與 `/fmu/out/*`。
5. PX4 ULog、Kill Switch、定高/定點與失聯處置。
6. 無槳後，才進行起飛、短暫停留、降落測試。

不要在宿主執行 `do-release-upgrade`。不要使用 Orin BSP、不要再刷 SD、不要執行 `/dev/mtd0` 舊方法。

## 2026-07-24 最新接手指令

請先閱讀 `P450_PROGRESS_2026-07-24_NEXT.md`。目前不需要重裝 ROS 2，也不需要重刷 Jetson。下一個唯一優先關卡是確認 Pixhawk ↔ NX 的實體 transport。

執行原則：使用繁體中文；一次只給使用者一個短命令；等待輸出後再繼續。螺旋槳拆除或機體固定，不 Arm，不修改 PX4 參數。

1. 請使用者把 Pixhawk 6C 用資料 USB 線直接接到 NX，不要經過 USB Hub。
2. 依序執行 `lsusb`、`ls -l /dev/ttyACM* /dev/ttyUSB* 2>/dev/null`，必要時才執行 `sudo dmesg | tail -n 30`。
3. 若沒有新增穩定 serial 裝置，停止並回報；不要猜測 `/dev/ttyTHS0/1/4` 或 UART 腳位。
4. 若 serial 出現，先記錄裝置並觀察是否穩定；USB serial 出現不代表 uXRCE-DDS 已完成。
5. 之後才 source `/opt/ros/foxy/setup.bash` 與 `~/p450_ros2_ws/install/setup.bash`，確認 `px4_msgs`、`px4_ros_com`。
6. 在 QGroundControl 先只讀取 `UXRCE_DDS_CFG`、`UXRCE_DDS_PRT`、`UXRCE_DDS_AG_IP`、`UXRCE_DDS_DOM_ID`；依實際 UART/UDP 路徑決定 Agent，不要直接套猜測命令。
7. Agent 成功後，確認 `/fmu/out/*`、`vehicle_status`、`vehicle_odometry`；topic 不穩定就停止，不飛行。
8. 完成 ULog、Kill Switch、失聯處置、定高/定點/EKF/震動的無槳測試後，才做第一次起飛→短暫停留→降落。

QGC 的 P450 Wi-Fi→TCP/MAVLink 已成功，只代表筆電能連 Pixhawk；它不能代替 Pixhawk→NX 的 ROS 2/uXRCE-DDS 通道。Native Foxy 是目前方案；Humble/Docker 延後到確定需要對接學長專案時再規劃。
