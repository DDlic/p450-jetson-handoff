# P450 交付期簡單 Offboard PoC：決策與 NX CLI 下一步

日期：2026-08-17（Asia/Taipei）

## 0. 文件目的與決策邊界

本文件只處理接近交付期時的最小展示目標：

```text
原地放置
→ 切入 Offboard
→ 自動解鎖
→ 起飛 1 m
→ 沿機頭方向前進 5 m
→ PX4 Land mode 降落
→ 自動上鎖
```

這不是飛行可靠性驗收，也不覆蓋既有 transport／kernel gate：

- Reliable 已在現有 60 秒與 600 秒場消除最終遺失，但 600 秒場的 PX4 receipt 最大
  gap 仍為 `601.548 ms`，250 ms freshness gate 為 FAIL。
- NX 已兩次出現同 family 的 `key_garbage_collector -> key_put()` kernel panic，kernel
  gate 仍為 FAIL。
- 因此 repository 仍不能宣稱「可安全飛行」或「已完成可靠性驗收」。若機主因交付期限
  決定做一次受控 PoC，必須明確接受殘餘風險，且由現場操作者掌握 RC mode switch、
  Kill switch 與安全區域。
- NX CLI／Codex 不得自行裝槳、改參數、解鎖或執行飛行腳本；只可在機主現場明確確認
  後逐階段執行。

正式根因修復與 gate 仍以
[`P450_RELIABLE_LATENCY_REMEDIATION_RUNBOOK_2026-08-17.md`](P450_RELIABLE_LATENCY_REMEDIATION_RUNBOOK_2026-08-17.md)
為準。本文件提供的是「不再改韌體時，如何把單次展示風險降到最低」。

## 1. 結論一：`Takeoff detected / not landed` 的真正原因

2026-08-12 無槳室外測試的時間軸是：

```text
15:25:37.969  Armed by external command
15:25:39.887  Takeoff detected
15:25:41.285  首次 Disarming denied, not landed
15:25:42.601  Failsafe / No offboard signal / Position fallback
15:26:18.449  Disarmed by kill switch
```

已證明 Arm 與 normal Disarm 都有到達 PX4；Disarm 不是傳輸遺失，而是 Commander 因
land detector 狀態主動拒絕。完整現場證據見
[`evidence/20260812_outdoor_offboard_arm_cycle/SUMMARY.md`](../../evidence/20260812_outdoor_offboard_arm_cycle/SUMMARY.md)。

PX4 v1.14.3 的 `Takeoff detected` 只表示 `vehicle_land_detected.landed` 從 true 轉為
false，不等於感測器證明無槳機體真的離地：

- [PX4 v1.14.3 Commander：Takeoff detected 狀態轉換](https://github.com/PX4/PX4-Autopilot/blob/v1.14.3/src/modules/commander/Commander.cpp#L1808-L1824)
- [PX4 v1.14.3 Commander：normal Disarm 判定](https://github.com/PX4/PX4-Autopilot/blob/v1.14.3/src/modules/commander/Commander.cpp#L545-L565)

Commander 接受 normal Disarm 的條件是 `landed || maybe_landed`。當兩者皆為 false，
external command 會得到 `Disarming denied, not landed`。

當天 `p450_offboard_ground_probe.py` 使用 position Offboard：

```text
OffboardControlMode.position = true
TrajectorySetpoint.position = 啟動時擷取的目前位置
TrajectorySetpoint.velocity = [NaN, NaN, NaN]
```

PX4 v1.14.3 land detector 在 climb-rate/position control 啟用、且已經離開
`maybe_landed/landed` 後，要重新建立 `ground_contact`，通常還要求有限且向下的速度
setpoint。原地 position hold 的 Z velocity 是 NaN，不構成 commanded descent；再加上
position controller 的推力、速度估計或旋轉門檻，狀態可能一直無法走回：

```text
ground_contact → maybe_landed → landed
```

原始碼條件見
[PX4 v1.14.3 MulticopterLandDetector](https://github.com/PX4/PX4-Autopilot/blob/v1.14.3/src/modules/land_detector/MulticopterLandDetector.cpp#L1141-L1337)。

Kill 後才執行的 `listener vehicle_land_detected` 顯示 `landed=true`，不能證明 armed
期間的感測條件已恢復；v1.14.3 在 `!armed` 時會讓相關 landed 狀態成立。

### 對交付腳本的直接修正

- 不要以「把位置 setpoint 設回地面後直接 normal Disarm」作為降落流程。
- 終點必須切換 PX4 Land mode，讓 PX4 產生正式下降要求並自行完成 land detection。
- 使用 `VEHICLE_CMD_NAV_LAND`，訂閱 `VehicleCommandAck`，確認命令 accepted 或確認 nav
  state 已進入 Land；未確認前只能有限次重送，不能無限洪泛。
- 進入 Land mode 後不再送新的移動 setpoint；等待 `landed`，再等待 PX4 依
  `COM_DISARM_LAND` 自動上鎖。
- 不在 `not landed` 時重複 normal Disarm，更不能使用 force disarm 作正常流程。

PX4 官方 Land mode 會在切入位置下降，落地後預設自動 Disarm：
[PX4 v1.14 Land Mode](https://docs.px4.io/v1.14/en/flight_modes_mc/land)。

## 2. 結論二：601.548 ms gap 對簡單飛行的實際意義

Reliable 600 秒場的原始判定為：

```text
NX publish / PX4 receipt = 6001 / 6001
最終遺失 = 0
NX max publish gap = 159.999 ms
PX4 max receipt gap = 601.548 ms
PX4 >150/250/500 ms = 80/16/2
PX4 >1000 ms = 0
COM_OF_LOSS_T = 1.0 s
```

證據見
[`evidence/20260813_first_principles_offboard_transport/TEN_MINUTE_RELIABLE_RESULT.md`](../../evidence/20260813_first_principles_offboard_transport/TEN_MINUTE_RELIABLE_RESULT.md)。

精確解讀：

1. 這個 601.548 ms 是 PX4 對 `OffboardControlMode` 的 receipt gap；該場沒有發布
   `TrajectorySetpoint` 或 `VehicleCommand`，不能宣稱所有控制 topic 都固定延遲 600 ms。
2. 目前只有 `OffboardControlMode` reader／XRCE input stream 改為 Reliable；
   `TrajectorySetpoint` 與 `VehicleCommand` 仍沿用 Best Effort。
3. PX4 姿態、位置與馬達控制迴圈都在 Pixhawk 本機執行。ROS 2 position Offboard 只要
   heartbeat 仍在 timeout 內，PX4 可以持續追蹤最後一個位置 setpoint；官方文件甚至說明
   ROS 2 `TrajectorySetpoint` 可只送一次，存活訊號則由 `OffboardControlMode` 持續提供。
4. 601.548 ms 小於目前 `COM_OF_LOSS_T=1.0 s`，所以該次 gap 本身不必然觸發 Offboard
   loss；但只剩約 398 ms 餘裕，且已低於持續 >2 Hz 所代表的理想 500 ms 間隔。
5. 測試是 disarmed、無槳、heartbeat-only；不能保證 armed、完整腳本、戶外或 NX 負載下
   不會超過 1 秒。NX kernel panic 若重現，則會直接形成持續失聯。

PX4 官方 Offboard 行為與 timeout 定義：

- [PX4 v1.14 Offboard Mode](https://docs.px4.io/v1.14/en/flight_modes/offboard)
- [PX4 v1.14 COM_OF_LOSS_T](https://docs.px4.io/v1.14/en/advanced_config/parameter_reference#COM_OF_LOSS_T)

### PoC 控制策略

單次展示只使用 position setpoint，不使用 velocity、attitude、body-rate 或直接 thrust：

- 固定 position setpoint 在 gap 期間仍代表同一個安全目標。
- 若使用 1 m/s velocity setpoint，陳舊 600 ms 理論上可能讓機體延續舊速度約 0.6 m；
  不適合目前 link。
- 不做相機／影像傳輸、不錄高頻 rosbag、不啟動無關 ROS nodes，避免把高頻寬與 CPU
  負載加入唯一一次展示。
- 不提高 heartbeat 到 20/50 Hz。維持已量測的 10 Hz，避免增加 Reliable history 與
  recovery 壓力。
- 不提高 `COM_OF_LOSS_T` 來掩蓋 tail latency；它只會讓真正的 NX 故障更晚觸發
  failsafe。

## 3. NX CLI 下次登入後的第一個工作

### 3.1 先讀，不要直接動實機

依序閱讀：

1. 本文件。
2. `README.md` 頁首最新狀態。
3. `docs/runbooks/P450_RELIABLE_LATENCY_REMEDIATION_RUNBOOK_2026-08-17.md` 的禁止事項。
4. `evidence/20260812_outdoor_offboard_arm_cycle/SUMMARY.md`。
5. `evidence/20260813_first_principles_offboard_transport/TEN_MINUTE_RELIABLE_RESULT.md`。

先確認 repository 身分與工作樹，不覆寫機主未提交內容：

```bash
git status -sb
git branch --show-current
git log -5 --oneline --decorate
```

### 3.2 只做 read-only baseline

在 NX 實體機上先保存：

```bash
date --iso-8601=seconds
uname -a
uptime
systemctl show p450-micro-xrce-agent.service \
  -p ActiveState -p MainPID -p NRestarts -p ExecMainStartTimestamp
ip -br addr
journalctl -k -b --no-pager | \
  rg -i 'panic|oops|key_garbage|hung task|thermal|ttyTHS1|tegra_uart'
```

因 kernel gate 仍為 FAIL，不要為了「清乾淨 session」隨意 stop/start Agent，也不要
unload Wi-Fi module。若 Agent、ROS graph 或 PX4 identity 不符合 baseline，停止並回報，
不要一邊修 service 一邊準備裝槳。

QGC／PX4 端至少讀回並記錄：

```text
ver all
commander status
uxrce_dds_client status
param show COM_OF_LOSS_T
param show COM_OBL_RC_ACT
param show COM_DISARM_LAND
param show MPC_LAND_SPEED
listener vehicle_status 1
listener vehicle_land_detected 1
listener vehicle_local_position 1
```

預期已知值只有 `COM_OF_LOSS_T=1.0 s`。其他參數必須以當天 readback 為準，不可從本文件
猜值。若機主選擇「NX 失聯就自動降落」，建議的候選是 `COM_OBL_RC_ACT=4`；這是參數
變更，不是韌體修改，但仍要先保存舊值、取得機主確認，並先做無槳失聯 A/B。

## 4. 要實作的最小任務腳本

建議新增單一用途腳本：

```text
scripts/p450_delivery_poc_mission.py
```

不要直接把現有 `p450_offboard_ground_probe.py` 改成飛行腳本；它是歷史證據工具，且目前
只會 hold-current-position。

### 4.1 強制設計要求

- 預設 `--dry-run` 或拒絕 armed；真正解鎖必須有明確 `--allow-armed`。
- 啟動時要求操作者輸入唯一 TEST_ID，CSV／console summary 全部帶同一 TEST_ID。
- 使用 monotonic clock 記錄 NX publish gap；不要用 ROS wall time 做本機 gap 判定。
- heartbeat timer 固定 10 Hz，與任務狀態機分離；任何等待都必須是 non-blocking，禁止
  `sleep()` 阻塞 heartbeat callback。
- `OffboardControlMode.position=true`，其餘控制層 false。
- `OffboardControlMode` publisher 使用 Reliable QoS，啟動前確認 subscription count
  恰為 1 且 QoS 相容。
- `TrajectorySetpoint` 與 `VehicleCommand` 使用與 PX4 現有 reader 相容的 Best Effort
  QoS；不要因方便把所有 topic 一起改 Reliable。
- 訂閱 `VehicleStatus`、`VehicleLocalPosition`、`VehicleLandDetected`、
  `VehicleCommandAck`；每一階段必須由回讀狀態推進，不能只靠固定秒數。
- never force arm/disarm：`VEHICLE_CMD_COMPONENT_ARM_DISARM.param2=0`。
- `VehicleCommand` 使用有限次 retry＋ACK；同一命令已 accepted 後不得繼續發送。
- 任一 abort 在已 armed 時優先要求 PX4 Land mode；Kill 只保留給現場操作者的緊急處置。

### 4.2 位置與任務狀態機

起始時擷取：

```text
x0, y0, z0, heading0
```

PX4 local frame 使用 NED，1 m 起飛目標為：

```text
takeoff = (x0, y0, z0 - 1.0)
```

若 `heading0` 已驗證為由 North 順時針增加，沿機頭方向 5 m 的候選為：

```text
x_goal = x0 + 5.0 * cos(heading0)
y_goal = y0 + 5.0 * sin(heading0)
z_goal = z0 - 1.0
```

第一次實機前必須在 dry-run 印出起點、終點與方向，現場核對不能把 NED／ENU 或機頭方向
弄反。

推薦狀態機：

```text
PRECHECK
  → STREAM_PREROLL（原地 position setpoint＋10 Hz heartbeat 至少 2 s）
  → REQUEST_OFFBOARD（ACK／VehicleStatus 確認，timeout 5 s）
  → REQUEST_ARM（ACK＋armed 確認，timeout 5 s）
  → TAKEOFF_1M（到達誤差 ≤0.20 m、|vz|≤0.20 m/s，穩定至少 1 s）
  → HOLD_AFTER_TAKEOFF（2 s）
  → MOVE_FORWARD_5M（固定終點 position setpoint）
  → HOLD_AT_GOAL（水平誤差 ≤0.30 m、|vxy|≤0.30 m/s，穩定至少 2 s）
  → REQUEST_LAND（MAV_CMD_NAV_LAND，ACK／nav state 確認）
  → WAIT_LANDED
  → WAIT_AUTO_DISARM
  → COMPLETE
```

時間上限建議：takeoff 15 s、前進 30 s、Land 30 s。任一階段 timeout、定位失效、
failsafe、電池異常、姿態異常或回讀資料 stale，都不得繼續前進到下一 waypoint。

### 4.3 stale 與失聯處理

- `VehicleLocalPosition`／`VehicleStatus` 回讀 age >1 s：凍結任務狀態，不再更新到下一個
  waypoint，但維持 heartbeat 與最後的固定 position target。
- 回讀 age >2 s 或狀態明確 failsafe：有限次要求 Land；若命令無法確認，依 PX4 已設定的
  Offboard-loss action 處理，現場操作者準備 mode switch／Kill。
- heartbeat 本機 publish gap >150 ms：記錄 WARN；>250 ms：本場 PoC 判 FAIL，即使飛行
  表面正常也不能宣稱驗收通過。
- 出現 `No offboard signal`、Position fallback、session reconnect、Agent restart、NX
  kernel warning/Oops，該場立即判 FAIL，不做第二段 5 m 移動。

## 5. 最小測試順序

即使接近交付，也不能把所有未知數放在第一趟有槳飛行：

### Gate 1：SITL 或純軟體

- 驗證 NED 座標、heading 轉換、狀態 timeout、ACK 配對與 Land 分支。
- 人工停止 heartbeat，確認腳本不會繼續推進 waypoint。

### Gate 2：無槳地面 sequence

- 實體機無槳、操作者在旁、Kill 可用。
- 驗證 preroll、Offboard、normal Arm、Land command、ACK 與最後 auto-disarm。
- 因機體不會真的到 1 m，使用明確 `--ground-sequence` 測試分支按 timer 推進命令路徑；
  此模式必須拒絕在裝槳狀態使用。
- 目標是證明新的 Land 流程不再以 normal Disarm 撞上 `not landed`。

### Gate 3：最低高度有槳功能測試

```text
起飛 0.5 m → hold → PX4 Land
```

不做 5 m 前進。確認起飛方向、定位、Land、auto-disarm、RC mode switch 與 Kill。

### Gate 4：交付 PoC

```text
起飛 1 m → hold → 沿已核對方向前進 5 m → hold → PX4 Land
```

場地必須把整條 5 m 路徑及 Offboard-loss 中途降落位置清空；禁止人員站在航線、終點或
機體下方。

## 6. 單次 PoC 的 GO／NO-GO

只有全部成立才可由機主決定 GO：

- 當次啟動後 NX 沒有新 kernel warning、Oops、panic、thermal 或 I/O error。
- Agent active、PID 穩定、`NRestarts=0`、唯一 UART holder、PX4 client connected。
- PX4 identity、Reliable Offboard reader、ROS QoS endpoint 都與已驗證版本一致。
- GPS/local position、heading、home、battery、land detector 與 preflight 全部有效。
- RC mode switch、Kill switch、Offboard-loss action 已由現場確認。
- 無相機／影像／大型 rosbag／額外高頻 topic。
- Gate 1～3 已在同一軟硬體設定通過。
- 操作者明確理解：這仍是 transport freshness FAIL 與 kernel FAIL 下的受控 PoC，不是
  飛行資格解除。

任一項不成立即 NO-GO。不得以提高 `COM_OF_LOSS_T`、force arm/disarm、略過 ACK、關閉
failsafe 或口頭認為「只飛一次」取代條件。

## 7. 每一場要保存的證據

```text
TEST_ID
git commit SHA
PX4 ver all
PX4 parameter readback
NX heartbeat/setpoint CSV
VehicleCommandAck 與狀態機 transition log
QGC messages
ULog filename
Agent PID / NRestarts before-after
kernel log before-after
結果：PASS / FAIL / ABORT 與第一個失敗條件
```

若有任何異常，不要只留下影片；影片不能代替 ULog、命令 ACK、receipt gap 或 kernel
證據。

## 8. 下次 NX CLI 的一句話任務

> 不再改 PX4 韌體；先完成 read-only baseline，然後新增並審查
> `scripts/p450_delivery_poc_mission.py`，只用 10 Hz Reliable heartbeat＋固定 position
> waypoint＋ACK 驗證＋PX4 Land mode。先 SITL、再無槳 Land sequence、再 0.5 m 起降，
> 最後才由機主決定是否執行 1 m／5 m 的受控 PoC。不得把 PoC 成功寫成 transport 或
> kernel gate PASS。
