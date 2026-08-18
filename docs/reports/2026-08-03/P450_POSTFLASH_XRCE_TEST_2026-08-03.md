# P450 PX4 XRCE 回補韌體刷入後測試

日期：2026-08-03（Asia/Taipei）

## 測試前提

- 機主已使用 QGroundControl 匯出完整 PX4 參數備份。
- 已刷入 `p450-pixhawk6c-v1.14.3-xrce-ping-fix-f9bc66c6f3.px4`。
- 機主回報刷入後參數恢復及檢查正常。
- NX 使用 Micro XRCE-DDS Agent v2.4.2、`/dev/ttyTHS1`、460800 baud。
- 本報告前半段的 XRCE continuity、導航與靜態感測器測試只訂閱
  `/fmu/out/*`。同日後續另執行明確標示的無槳 ROS→PX4 輸入測試；該階段
  有發布零推力與模式命令，但沒有成功解鎖，馬達全程未轉動。

韌體 SHA-256：

```text
cb14d73274014385e809645dd3525e1ce0e33cf5d648c7d23324c41b822bf0bd
```

## 前置安全與連線狀態

- Agent active，UART 只有該 Agent 佔用。
- ROS 2 可發現完整 23 個 `/fmu/*` topics：13 in、10 out。
- `arming_state=1`、`armed_time=0`、`failsafe=false`。
- `battery_warning=0`、`battery_unhealthy=false`。
- `gcs_connection_lost=false`。
- `pre_flight_checks_pass=false`。
- `manual_control_signal_lost=true`、`offboard_control_signal_lost=true`，符合本輪
  未接手動控制及未送 Offboard 心跳的純訂閱條件。

## 10 分鐘常駐 Agent 連續性測試

執行：

```bash
./scripts/p450_ros2_link_monitor.py --duration 600 --max-gap-ms 100
```

結果：

```text
elapsed_s=600.004
messages=42936
average_hz=71.560
median_gap_ms=12.911
max_gap_ms=56.263
gaps_over_100ms=0
gaps_over_500ms=0
gaps_over_1s=0
result=PASS
```

同時每約 5 秒觀察 DDS graph：

- 共 72 筆採樣。
- `/fmu/*` 每次均為 23。
- 第 1 筆的第二次獨立查詢只看到 1 個 `/fmu/out/*`，之後 71 筆均為完整 10 個。
- 第 1 筆判定為測試起始時 graph 尚未暖機；後續沒有重複，且 IMU 全程沒有
  超過 100 ms 的 gap。
- Agent 測試前後均 active，PID 均為 1704，沒有服務重啟。

## 120 秒詳細 Agent lifecycle 測試

測試時暫停 systemd Agent，以相同裝置與 baud 啟動 `-v 4` 前景 Agent；結束後
自動恢復 systemd 服務。前景 Agent 的建立屬於一次預期的測試起始重連。

資料結果：

```text
elapsed_s=120.002
messages=8563
average_hz=71.357
median_gap_ms=13.163
max_gap_ms=35.617
gaps_over_100ms=0
gaps_over_500ms=0
gaps_over_1s=0
result=PASS
```

Lifecycle：

```text
create_client=1
session established=1
delete_client=0
session closed=0
```

這與舊韌體 65 秒內建立 10 次、關閉 9 次 session 形成明確 A/B 差異。

## 恢復 systemd Agent 後複驗

- 服務恢復為 active，MainPID 5183。
- Topics 恢復完整 23/10。
- 30 秒收到 2147 筆，平均 71.566 Hz。
- 最大 gap 33.134 ms，所有超過 100 ms 的 gap 為 0，結果 PASS。

## 刷入後定位與控制狀態唯讀檢查

GPS：

```text
fix_type=0
satellites_used=0
eph=4294967.5
epv=4259544.0
vel_ned_valid=false
heading=NaN
```

Local position／odometry：

```text
xy_valid=false
z_valid=true
v_xy_valid=false
v_z_valid=true
heading_good_for_control=false
xy_global=false
z_global=false
dead_reckoning=true
odometry quality=0
```

Control／vehicle status：

```text
arming_state=1
nav_state=4
flag_armed=false
flag_control_auto_enabled=true
flag_control_offboard_enabled=false
flag_control_termination_enabled=false
failsafe=false
pre_flight_checks_pass=false
```

這表示飛控保持未解鎖、沒有進入 Offboard 或 termination；當下模式選擇為
Auto，但 GPS、水平定位、速度、航向與 preflight 均未通過，不具備自動飛行
條件。不得因 XRCE 通訊穩定就嘗試解鎖。

## 室內 60 秒靜態 IMU／姿態檢查

機體保持靜止，使用純訂閱工具：

```bash
./scripts/p450_sensor_static_check.py --duration 60
```

結果：

```text
elapsed_s=60.000
sensor_samples=4342
sensor_average_hz=72.366
attitude_samples=4341
attitude_average_hz=72.349
accel_norm_mean_m_s2=9.763735
accel_norm_std_m_s2=0.025857
accel_norm_min_m_s2=9.665857
accel_norm_max_m_s2=9.852389
gyro_norm_mean_rad_s=0.006282
gyro_norm_std_rad_s=0.002582
gyro_norm_max_rad_s=0.016183
accelerometer_clipping_samples=0
quaternion_norm_mean=1.000000037
quaternion_norm_max_error=0.000000120
gyro_clipping_field=IGNORED_known_px4_v1.14.3_uninitialized_field
result=PASS
```

加速度模長接近重力、靜止陀螺儀幅度低、沒有 accelerometer clipping，姿態
四元數維持正規化。PX4 v1.14.3 已知未初始化的 `gyro_clipping` 欄位仍明確忽略，
不納入判定。

## NX 再次開機後 XRCE 回歸

NX 於 15:12 再次整機開機後：

- `p450-micro-xrce-agent.service` 自動啟動。
- Agent `NRestarts=0`，不是 Agent crash 後由 systemd 拉起。
- ROS 2 topics 為完整 23/10。
- 60 秒室內靜態感測器測試已在這次 boot 內通過。

另執行 120 秒 continuity：

```text
elapsed_s=120.017
messages=8719
average_hz=72.648
median_gap_ms=12.216
max_gap_ms=47.477
gaps_over_100ms=0
gaps_over_500ms=0
gaps_over_1s=0
result=PASS
```

因此回補韌體在整機重新開機後仍可自動恢復並維持穩定 XRCE session。

系統記錄顯示 15:04–15:12 的前一個短 boot 沒有正常 shutdown marker，但系統
沒有啟用 persistent journal，無法追查最後事件。若該次不是人工斷電或 Reset，
需另列為供電／主機穩定性待查；這與目前 Agent 的 `NRestarts=0` 不同。

## 無槳 RC 模式與失聯測試

測試全程拆除旋翼、機體未解鎖，遙控器保持可用；只有在準備解鎖測試時要求
油門最低。三段飛行模式開關已由 ROS 2 `VehicleStatus` 確認：

```text
第一格：STAB   nav_state_user_intention=15, nav_state=15
第二格：ALTCTL nav_state_user_intention=1,  nav_state=1
第三格：POSCTL nav_state_user_intention=2,  nav_state=2
```

STAB 與 ALTCTL 時 RC 正常、`failsafe=false`；STAB 的
`pre_flight_checks_pass=true`。POSCTL 雖可被選取，但室內狀態為
`local_position_invalid=true`、`global_position_invalid=true`、
`home_position_invalid=true`，因此 `pre_flight_checks_pass=false`，不得解鎖。

RC loss 測試時，因發射機在飛控開機期間無法用一般流程關閉，機主直接移除
發射機電池以確保 RF 發射端完全停止。飛控在超過 20 秒、四次連續抽樣中仍為：

```text
manual_control_signal_lost=false
failsafe=false
arming_state=1
nav_state=15
```

`failsafe=false` 在未解鎖狀態下不意外，但 `manual_control_signal_lost=false`
表示飛控沒有偵測到 RC 失聯；這與接收機失聯後持續輸出最後通道值（Hold）相符，
尚未取得接收機型號確認。此項測試為 FAIL，必須在飛行前將接收機設定為失聯時
停止輸出，或使用低油門失聯值並正確設定 `RC_FAILS_THR`，再重測。

## ROS→PX4 Offboard／控制輸入診斷

### 已確認通過的部分

- `/fmu/in/offboard_control_mode`、`vehicle_rates_setpoint`、`vehicle_command`
  均有一個 PX4 DDS subscriber。
- 發布端使用 PX4 v1.14 範例的 Best Effort／Transient Local QoS 後，飛控可收到
  Offboard 心跳；Volatile 發布雖能 DDS match，但本機測試未清除
  `offboard_control_signal_lost`。
- NX 發出的 `VEHICLE_CMD_DO_SET_MODE` 成功將飛控由 STAB 切至 ALTCTL，證明
  `VehicleCommand` 的 ROS→PX4 路徑可工作。測試後由實體模式開關恢復 STAB。
- PX4 與 NX ROS clock 的一次抽樣差約 20 ms，沒有固定的大幅時間基準錯位。

### 未通過的部分

- 未解鎖時的 Offboard 模式要求沒有進入 `nav_state=14`。
- 外部 ARM 命令未被接受；當時 `pre_flight_checks_pass=true`、
  `safety_button_available=true`、`safety_off=true`、`usb_connected=false`，但目前
  DDS topic 清單沒有 `VehicleCommandAck`，因此尚未取得精確拒絕原因。
- 原先準備以人工 ARM 配合 NX 零推力 watchdog 繼續測試，但 watchdog 在人工操作
  前偵測到 Offboard heartbeat loss 並自動中止。沒有人工解鎖、沒有進入
  Offboard、沒有施加低推力，馬達全程未轉動。

### 心跳連續性數據

使用零 body-rate、零 thrust 的純地面心跳測試；NX 本地發布迴圈本身穩定：

```text
非零 ROS timestamp，約 88 Hz：1499 筆，最大發布 gap 13.261 ms
FailsafeFlags：9 / 32 筆 offboard_control_signal_lost=true

timestamp=0，約 87 Hz：1482 筆，最大發布 gap 13.984 ms
FailsafeFlags：2 / 29 筆 offboard_control_signal_lost=true

timestamp=0，約 16.2 Hz：275 筆，最大發布 gap 70.547 ms
FailsafeFlags：12 / 31 筆 offboard_control_signal_lost=true
```

設定 20 Hz（實測約 16.2 Hz）與設定 100 Hz（實測約 87–88 Hz）、Best Effort 與 Reliable 均測過；Reliable 沒有改善。PX4 v1.14.3
反序列化器會把輸入 `timestamp=0` 改為飛控收件時間，能降低但未消除失聯判定。

另暫停 systemd Agent，以 v6 詳細模式記錄一次約 88 Hz 測試後自動恢復服務：

```text
ROS 本地發布：1491 組 offboard_control_mode + vehicle_rates_setpoint
Agent DataReader：1491 + 1491，最大 gap 14.522 / 14.620 ms
Agent serial send：1491 + 1491，最大 gap 17.596 / 21.018 ms
Agent error=0, warning=0，沒有 session teardown/recreate
```

因此目前證據把異常範圍縮小到飛控端 XRCE client 接收／轉成 uORB 後的心跳新鮮度
判定，不是 NX Python 排程、DDS discovery、Agent 收件或 Agent UART 發送遺失。
PX4 v1.14.3 `OffboardChecks` 使用
`offboard_control_mode.timestamp + COM_OF_LOSS_T` 判斷資料是否仍新鮮；目前行為高度
懷疑恢復的 `COM_OF_LOSS_T` 值過短，但尚未由 QGC 讀取確認。後續第一步是用 QGC
查詢該參數的完整目前值，確認前不得繞過 watchdog 或強行解鎖。

## 本輪結束安全狀態

```text
arming_state=1
nav_state_user_intention=15
nav_state=15
failsafe=false
pre_flight_checks_pass=true
safety_off=true
usb_connected=false
manual_control_signal_lost=false
battery_warning=0
p450-micro-xrce-agent.service=active
Agent NRestarts=0
```

## 結論與限制

PX4 v1.14.3 session ping 最小回補已消除目前地面條件下觀察到的週期性 XRCE
session teardown/recreate；Pixhawk TELEM2 ↔ NX UART0 ↔ ROS 2 Foxy 的通訊
穩定性關卡通過。

目前仍不得直接進入自動飛行，因為下列關卡尚未通過：

1. GPS fix、衛星數與水平位置／速度有效性。
2. 航向可控制性與 EKF 狀態。
3. `pre_flight_checks_pass`。
4. RC loss 未被飛控偵測；確認接收機型號並修正 Hold／failsafe 輸出後重測。
5. 由 QGC 讀取並核對 `COM_OF_LOSS_T`，排除 Offboard 心跳間歇過期。
6. 取得外部 ARM／Offboard 命令拒絕原因；目前未解鎖、馬達未轉。
7. Kill Switch、Offboard 失聯退出與 setpoint 邊界的無槳地面實測。
8. 更長時間、不同供電與完整 power-cycle 的回歸測試。

在上述安全關卡完成前，不解鎖、不進行自動起飛。
