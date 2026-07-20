# 可直接貼給 Ubuntu Codex CLI 的接手提示詞

```text
請接手 AMOV P450 的 Jetson Xavier NX 系統重建工作。請用繁體中文，逐段帶我執行；每一段命令執行後先等我貼輸出，再給下一段。不要重複猜硬體型號，也不要在未確認輸出前執行破壞性刷機。

硬體已確認：
- NVIDIA Jetson Xavier NX Developer Kit
- module P3668-0000
- carrier P3509-0000
- Tegra194
- Device Tree: tegra194-p3668-all-p3509-0000.dts
- 這是 microSD 開發版，不是 eMMC 版。
- 正確設定為 jetson-xavier-nx-devkit；不要使用 jetson-xavier-nx-devkit-emmc。

舊系統：
- Ubuntu 18.04.6
- L4T R32.4.4 / JetPack 4
- Kernel 4.9.140-tegra
- 原本 128 GB microSD 必須保留，不要格式化。

目標：
- JetPack 5.1.4 / L4T R35.6.0
- Ubuntu 20.04 宿主
- Ubuntu 22.04 + ROS 2 Humble 放 ARM64 Docker
- PX4 v1.14.3、Pixhawk 6C、px4_msgs、px4_ros_com、Micro XRCE-DDS Agent、Offboard

Ubuntu 桌機：
- Ubuntu 22.04.5 LTS
- x86_64
- user wilson
- 根目錄約有 338 GB 可用空間
- BSP: /home/wilson/下載/Jetson_Linux_R35.6.0_aarch64.tbz2
- BSP 預期目錄: /home/wilson/nvidia/JP514/Linux_for_Tegra

SD 映像：
- 官方套件 JP514-xnx-sd-card-image_b11
- 內含 sd-blob，大小約 17,633,280 KB
- 曾用 balenaEtcher 寫入 Kingston 512 GB microSD
- Etcher 顯示燒錄成功，但 Validate 狀態尚未明確記錄

已完成的 QSPI 狀態：
- 曾用 R35.6.0 BSP 執行 QSPI-only 刷寫
- 刷後可看到 Jetson UEFI firmware version 6.0-37391689
- 代表 R35.6.0 UEFI 至少能啟動

目前故障：
- Kingston JP5 SD 卡插入後，UEFI 可偵測到 GPT，map -r 有 BLK0～BLK11
- Boot Manager 中 UEFI eMMC Device 與 UEFI NVIDIA eMMC Kernel Boot 都回到 Boot Manager
- L4T Boot Mode 已是 ExtLinux
- OS chain A status 已是 Normal
- 之後會進入 PXE/HTTP fallback，顯示 Could not detect network connection
- 這不是 Wi-Fi 測試結果

重要判斷：
- UEFI 顯示 eMMC 不代表硬體是 eMMC；P3668-0000 已確認為 microSD 版。
- NVIDIA 官方支持 P3668-0000 使用 jetson-xavier-nx-devkit 與 microSD。
- 512 GB 沒有被官方列為禁止容量；若 128 GB 只是舊 R32 卡，不能作為容量測試。
- 從 R35 QSPI 直接啟動舊 R32 SD 卡失敗是預期的版本不匹配。

目前請從這裡開始，先不要連 NX，也不要執行 flash.sh：

cat /etc/os-release

uname -m

df -h ~

ls -lh ~/下載/Jetson_Linux_R35.6.0_aarch64.tbz2

ls -ld ~/nvidia/JP514/Linux_for_Tegra

cd ~/nvidia/JP514/Linux_for_Tegra

ls -l jetson-xavier-nx-devkit-qspi.conf jetson-xavier-nx-devkit.conf p3509-0000+p3668-0000-qspi.conf 2>/dev/null

readlink -f jetson-xavier-nx-devkit-qspi.conf

確認 BSP 與設定檔後，再使用之前已成功進入 Recovery 的同一種硬體方法；不要猜測 P450 載板 J14 腳位。桌機執行：

lsusb | grep -i nvidia

只有看到 0955:7e19 才繼續。

之後重新刷 QSPI-only 並保存 log：

cd ~/nvidia/JP514/Linux_for_Tegra

sudo ./flash.sh jetson-xavier-nx-devkit-qspi internal 2>&1 | tee ~/xavier_nx_qspi_rerun.log

若有任何錯誤、timeout、permission、Python 或 board mismatch，立即停止，不要自行換參數。不要使用 eMMC 設定、Orin BSP、一般 Ubuntu 22.04 ISO、do-release-upgrade 或舊系統 /dev/mtd0 方法。

刷寫成功後才插入 JP514 SD 卡測試。若仍回 Boot Manager，不要重複刷 QSPI，改分析 SD image、Validate、UEFI 啟動鏈或完整 QSPI+SD 流程。

系統成功開機後，再依序驗證 Wi-Fi AP、SSH、Pixhawk USB/UART、Micro XRCE-DDS、ROS 2 topic、PX4 ULog、Kill Switch、定高/定點資料，最後才做起飛—短暫停留—降落測試。
```
