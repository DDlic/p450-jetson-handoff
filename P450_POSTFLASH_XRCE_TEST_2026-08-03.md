# P450 PX4 XRCE 回補韌體刷入後測試

日期：2026-08-03（Asia/Taipei）

## 測試前提

- 機主已使用 QGroundControl 匯出完整 PX4 參數備份。
- 已刷入 `p450-pixhawk6c-v1.14.3-xrce-ping-fix-f9bc66c6f3.px4`。
- 機主回報刷入後參數恢復及檢查正常。
- NX 使用 Micro XRCE-DDS Agent v2.4.2、`/dev/ttyTHS1`、460800 baud。
- 所有測試只訂閱 `/fmu/out/*`，沒有發布 `/fmu/in/*`、解鎖或控制馬達。

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

## 結論與限制

PX4 v1.14.3 session ping 最小回補已消除目前地面條件下觀察到的週期性 XRCE
session teardown/recreate；Pixhawk TELEM2 ↔ NX UART0 ↔ ROS 2 Foxy 的通訊
穩定性關卡通過。

目前仍不得直接進入自動飛行，因為下列關卡尚未通過：

1. GPS fix、衛星數與水平位置／速度有效性。
2. 航向可控制性與 EKF 狀態。
3. `pre_flight_checks_pass`。
4. Kill Switch、手動控制與失聯 failsafe 的無槳地面實測。
5. Offboard 心跳、模式切換、失聯退出與 setpoint 邊界測試。
6. 更長時間、不同供電與完整 power-cycle 的回歸測試。

在上述安全關卡完成前，不解鎖、不進行自動起飛。
