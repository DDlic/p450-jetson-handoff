# P450 PX4 v1.14.3 最終基線與 NX 證據收集需求

最後更新：2026-08-10（Asia/Taipei）

## 1. 本文件的權威性

這是 2026-08-10 經機主確認後的目前決策，覆寫舊文件中「以 PX4 v1.15.4 作為
最終版本」的方向。舊版測試文件與 v1.15.4 韌體仍保留為診斷歷史，不得刪除或改寫
成成功紀錄。

本專案過去所稱的多次「重灌」，在目前問題脈絡中是指反覆刷入不同 PX4 版本與補丁，
不是重灌 Jetson Xavier NX。NX 的 JetPack／Ubuntu／ROS 2 不列入本輪重裝範圍。

## 2. 已確定的版本與工作範圍

- 最終 PX4 基線固定為官方 **v1.14.3**。
- v1.15.4 與其他版本只用於定位問題、閱讀上游修正及 A/B；不得直接成為最終韌體。
- 任何在其他版本證明有效的 XRCE 修正，都必須最小化回補至 v1.14.3，重新建置並
  在 v1.14.3 上完成驗收。
- Jetson 端必須使用與 v1.14.3 definitions 相符的 `px4_msgs release/1.14`；
  `release/1.15` 只屬於先前 v1.15.4 測試環境。
- 目前唯一優先工作是完成 **PX4 v1.14.3 的 XRCE 雙向穩定**。
- XRCE 雙向穩定前，不到室外測 GPS、不裝槳、不解鎖、不做起飛或飛行測試。
- RC loss、GPS、Kill Switch 與完整 failsafe 仍是後續獨立關卡，但本階段不展開。

## 3. 現有證據與正確解讀

### 3.1 已通過的部分

PX4 v1.14.3 session-ping 回補版：

```text
firmware: p450-pixhawk6c-v1.14.3-xrce-ping-fix-f9bc66c6f3.px4
source:   f9bc66c6f30d8ddcceaeba2545dc9f6d0e71faf1
SHA-256: cb14d73274014385e809645dd3525e1ce0e33cf5d648c7d23324c41b822bf0bd
```

2026-08-03 實測：

- 10 分鐘收到 42,936 筆 IMU，最大 gap 56.263 ms，0 次超過 100 ms。
- 120 秒 Agent lifecycle 只有一次 create／established，沒有 close／delete。
- 這證明 v1.14.3 原始版的 session 誤判死亡問題可由 session-ping 回補消除。

目前只能把這項結果稱為「PX4→NX 純接收與 session continuity 通過」。它尚未完整
證明 NX→PX4 在 2 Hz、20 Hz 與 Offboard heartbeat 下都穩定。

### 3.2 只作診斷的部分

v1.15.4 stock 與第一代 receive-drain 候選版都曾在 session 未重建、Agent PID 穩定的
狀態下出現約 1 秒同步空窗；20 Hz 輸入曾使 PX4→NX 輸出停止，需重啟 Agent 才恢復。
這些結果可用來設計 v1.14.3 的雙向壓力測試，但不能把 v1.15.4 當成最終解法。

第二代 v1.15.4 full-drain 候選版尚未實機測試。除非機主另行明確授權，下一位執行者
不得因為檔案已存在就刷入。

現有 v1.14.3 receive-drain＋ping 候選版
`p450-pixhawk6c-v1.14.3-xrce-rx-drain-ping-fix-49049d8555.px4` 已完成建置，
但沒有足夠實機驗收紀錄，仍只是候選版，不得直接宣稱成功。

### 3.3 `gyro_clipping` 的位置

v1.14.3 `VehicleIMU.cpp` 沒有正確設定及重置 `delta_angle_clipping`，可能使 ROS 2
`SensorCombined.gyro_clipping` 出現未初始化或殘留值。這是單一狀態欄位問題，
不是 XRCE session 或約 1 秒停頓的原因。

為保持單一變因，本輪 XRCE 調查不先混入此修正，且不得使用 `gyro_clipping` 判定
UART payload 是否損壞。XRCE 雙向穩定後，再把初始化修正獨立回補至 v1.14.3 並做
回歸測試。

## 4. 尚待確認的關鍵事實

開始任何刷寫或參數修改前，必須取得以下證據：

1. Pixhawk 目前實際 firmware version、source hash 與 board 資訊。
2. `UXRCE_DDS_CFG`、`UXRCE_DDS_PRT`、`UXRCE_DDS_SYNCT`、`SER_TEL2_BAUD`、
   `MAV_1_CONFIG` 的目前值。
3. NX 上 Agent 版本、systemd PID／restart count、唯一 UART 持有者及啟動參數。
4. NX ROS workspace 中 `px4_msgs`、`px4_ros_com` 的實際 branch、commit 與 dirty 狀態。
5. `/fmu/out/sensor_combined` 的 publisher、QoS、65 秒到達 gap 與測試前後 Agent lifecycle。
6. 當前 kernel boot 內是否新增 UART、DMA、overrun、framing 或 I/O error。

文件目前對飛控是 stock v1.15.4 或 `996b1df7a1` 候選版有互相矛盾的歷史敘述，
因此不得只引用 Markdown 判定實機版本，必須以新的 `ver all` 輸出為準。

## 5. 給 NX Codex CLI 的 Phase A：只讀證據收集

### 5.1 停止條件

本階段只允許讀取與 ROS 訂閱。不得：

- 刷 PX4、重啟 Pixhawk、修改 PX4 參數或切換飛行模式。
- 停止／重啟 Agent、另開第二個 Agent、搶占 `/dev/ttyTHS1`。
- 發布任何 `/fmu/in/*`、Offboard、VehicleCommand 或 actuator 訊息。
- 裝槳、解鎖、測馬達或移動到室外。
- 切換 `px4_msgs` branch、重新建置 workspace 或安裝／移除套件。

若 Agent 不為 active、UART 有多個持有者、ROS workspace 缺失或指令可能中斷現有
session，只記錄現況後停止，不要自行修復。

### 5.2 建立證據目錄

在 NX 執行；這只會在交接 repository 內建立文字證據：

```bash
cd /home/p450/p450-jetson-handoff
evidence_stamp="$(date +%Y%m%d_%H%M%S)"
evidence_dir="evidence/${evidence_stamp}_nx_v1143_baseline"
mkdir -p "$evidence_dir"
printf '%s\n' "$evidence_dir"
```

不要把密碼、Wi-Fi 密碼、token、SSH private key、完整環境變數或個人憑證放進
證據檔。

### 5.3 NX、Agent 與 UART 基線

```bash
cd /home/p450/p450-jetson-handoff
evidence_dir="$(find evidence -maxdepth 1 -type d -name '*_nx_v1143_baseline' | sort | tail -n 1)"
test -n "$evidence_dir"
{
  date --iso-8601=seconds
  uname -a
  cat /etc/os-release
  cat /etc/nv_tegra_release
  printf '\n--- repository ---\n'
  git status --short --branch
  git log -1 --date=iso --pretty=fuller
  printf '\n--- agent binary and service ---\n'
  /usr/local/bin/MicroXRCEAgent --version 2>&1
  systemctl is-active p450-micro-xrce-agent.service
  systemctl show p450-micro-xrce-agent.service \
    -p MainPID -p NRestarts -p ExecMainStatus -p FragmentPath
  systemctl cat p450-micro-xrce-agent.service
  printf '\n--- UART device and holders ---\n'
  ls -l /dev/ttyTHS1
  udevadm info --query=property --name=/dev/ttyTHS1
  fuser -v /dev/ttyTHS1 2>&1 || true
  lsof /dev/ttyTHS1 2>&1 || true
  printf '\n--- recent agent journal ---\n'
  journalctl -u p450-micro-xrce-agent.service -n 300 --no-pager
  printf '\n--- current-boot UART/kernel warnings ---\n'
  journalctl -k -b --no-pager | \
    grep -Ei 'ttyTHS|3110000.serial|uart|dma|overrun|framing|I/O error' || true
} 2>&1 | tee "$evidence_dir/nx_agent_uart_baseline.txt"
```

若 `fuser` 或 `lsof` 因權限不足只顯示部分資訊，保留原始錯誤即可；不要為了完整輸出
中斷 Agent。

### 5.4 ROS workspace 與 message 版本

```bash
cd /home/p450/p450-jetson-handoff
evidence_dir="$(find evidence -maxdepth 1 -type d -name '*_nx_v1143_baseline' | sort | tail -n 1)"
test -n "$evidence_dir"
source /opt/ros/foxy/setup.bash
source /home/p450/p450_ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=0
export ROS_LOCALHOST_ONLY=0

{
  date --iso-8601=seconds
  printf '\n--- px4_msgs source ---\n'
  git -C /home/p450/p450_ros2_ws/src/px4_msgs status --short --branch
  git -C /home/p450/p450_ros2_ws/src/px4_msgs rev-parse HEAD
  printf '\n--- px4_ros_com source ---\n'
  git -C /home/p450/p450_ros2_ws/src/px4_ros_com status --short --branch
  git -C /home/p450/p450_ros2_ws/src/px4_ros_com rev-parse HEAD
  printf '\n--- installed ROS packages ---\n'
  ros2 pkg prefix px4_msgs
  ros2 pkg prefix px4_ros_com
  ros2 interface show px4_msgs/msg/SensorCombined
  printf '\n--- FMU topics and sensor publisher ---\n'
  ros2 topic list | sort
  ros2 topic info -v /fmu/out/sensor_combined
} 2>&1 | tee "$evidence_dir/ros_workspace_and_topics.txt"
```

如果 source 路徑不存在，保留錯誤並另外記錄實際 workspace 路徑；不得先切 branch。
期望最終回到 `release/1.14`，但 Phase A 只確認、不修改。

### 5.5 65 秒唯讀 continuity 快照

先記錄 service 狀態，再執行 repository 既有的只讀訂閱工具：

```bash
cd /home/p450/p450-jetson-handoff
evidence_dir="$(find evidence -maxdepth 1 -type d -name '*_nx_v1143_baseline' | sort | tail -n 1)"
test -n "$evidence_dir"
source /opt/ros/foxy/setup.bash
source /home/p450/p450_ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=0
export ROS_LOCALHOST_ONLY=0

{
  date --iso-8601=seconds
  systemctl show p450-micro-xrce-agent.service -p MainPID -p NRestarts
  ./scripts/p450_ros2_link_monitor.py --duration 65 --max-gap-ms 100
  systemctl show p450-micro-xrce-agent.service -p MainPID -p NRestarts
  journalctl -u p450-micro-xrce-agent.service --since '-90 seconds' --no-pager
} 2>&1 | tee "$evidence_dir/ros2_readonly_continuity_65s.txt"
```

這份快照只描述「目前未知韌體／目前 workspace」的狀態，不直接作為 v1.14.3 最終
驗收。若 topic 不存在或工具報 message mismatch，保留輸出後停止。

### 5.6 PX4/QGC 只讀證據

TELEM2 正由 XRCE 使用，NX CLI 不得為了取得 NSH 而開啟 `/dev/ttyTHS1`。請由使用者
在 QGroundControl MAVLink Console 逐項執行，將完整輸出原樣貼入：

```text
evidence/<同一 evidence_stamp>_nx_v1143_baseline/px4_qgc_readonly.txt
```

命令如下：

```text
ver all
uxrce_dds_client status
param show UXRCE_DDS_CFG
param show UXRCE_DDS_PRT
param show UXRCE_DDS_SYNCT
param show SER_TEL2_BAUD
param show MAV_1_CONFIG
listener vehicle_status 1
listener failsafe_flags 1
```

只執行 `show`、`status`、`listener` 與 `ver`，不要執行 `param set`、`reboot`、
`uxrce_dds_client stop/start` 或任何控制命令。

### 5.7 下一次推送前檢查

NX CLI 應先讀取三份證據，新增簡短的
`evidence/<...>/SUMMARY.md`，列出：

- 實際 PX4 version／source hash。
- `px4_msgs` 與 `px4_ros_com` branch／commit。
- Agent version、PID、`NRestarts`、UART 持有者數量。
- topic 數、`sensor_combined` publisher／QoS。
- 65 秒 messages、平均頻率、最大 gap、超過 100 ms 次數。
- kernel／Agent 是否有 UART、session close/recreate 或 I/O error。
- 哪些證據缺失，以及缺失原因。

提交前執行：

```bash
git status --short
git diff --check
git diff -- evidence/
```

確認沒有密碼、token、private key、大型 raw log 或無關個資後，才提交及推送。不得在
同一提交內刷韌體、改 PX4 參數、切 ROS branch 或加入主動發布測試。

## 6. 收到 Phase A 證據後的測試順序

以下不是 Phase A 的立即執行命令，必須先審查證據並由機主再次確認：

1. 以 v1.14.3 session-ping 回補版與 `px4_msgs release/1.14` 建立乾淨基準。
2. 先做 10 分鐘純接收：session/topic/PID 穩定，最大 gap 小於 100 ms，
   0 次超過 100 ms。
3. 再做 2 Hz 非控制輸入，確認 PX4→NX continuity 不退化。
4. 再做 20 Hz 非控制壓力，確認輸入停止後不需重啟 Agent 即可維持／恢復輸出。
5. 最後才做未解鎖、零推力的 Offboard heartbeat／uORB 新鮮度測試。
6. 若 session-ping 版仍在輸入壓力下失敗，才評估將必要的 receive-drain／poll 修正
   最小回補到 v1.14.3；一次只改一組可解釋的變因。
7. XRCE 雙向全部通過後，才獨立加入 `gyro_clipping` 初始化修正並回歸。

任一階段若出現 session close/recreate、Agent restart、topic 消失、輸出完全停止、
意外模式切換或任何解鎖跡象，立即停止，不進入下一階段。

## 7. XRCE 雙向穩定的最低驗收條件

- 最終 firmware 為 v1.14.3 基線加已列明、可追溯的最小 backport。
- NX 使用與該 firmware 完全相符的 `px4_msgs release/1.14` definitions。
- 10 分鐘內 Agent PID 不變、`NRestarts=0`，沒有 session close/recreate。
- `/fmu/out/sensor_combined` 最大到達 gap `< 100 ms`，且 `>100 ms` 次數為 0。
- 2 Hz 與 20 Hz NX→PX4 輸入均可到達飛控端，且不造成 PX4→NX topics 停頓。
- 停止壓力輸入後，不需重啟 Agent或飛控即可保持／恢復正常輸出。
- Offboard heartbeat 在未解鎖地面測試中不再間歇被判 lost。
- 全程不解鎖、馬達不轉；這項通過也不等於允許戶外或飛行。
