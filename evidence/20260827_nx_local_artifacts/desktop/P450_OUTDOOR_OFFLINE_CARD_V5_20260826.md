# P450 戶外離線正式測試卡 V5（2026-08-26）

## 目的

使用已修正的 PX4 v1.14.3 任務腳本，先完成只讀預檢與無槳 Ground Gate，再進入 F1/F2 正式飛行。
外部 USB Internet 可拔除；`eth0` 基地台 LAN 保留給筆電、QGC、Moonlight 與 PX4 TCP/ROS 連線。

禁止使用舊 V3/V4 離線卡與舊腳本。

## 0. NX 一次性檢查

```bash
cd /media/p450/P450_DATA/src/p450-jetson-handoff
source /opt/ros/foxy/setup.bash
source /home/p450/p450_ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=0 ROS_LOCALHOST_ONLY=0

git rev-parse HEAD
sha256sum scripts/p450_delivery_poc_mission.py
findmnt -rn -T /media/p450/P450_DATA -o TARGET,SOURCE,FSTYPE
systemctl show p450-micro-xrce-agent.service -p ActiveState -p MainPID -p NRestarts
systemctl --user is-active sunshine.service
```

必須符合：

```text
BASE FIX = 6a044024a37911f9da436228036dfe0e5cb800e6
SHA256 = 9402bfa0031f73dfa55f94f8f8ebe8efe65877cf96495cdb61fc919afd9da788
P450_DATA = /media/p450/P450_DATA（獨立 microSD ext4）
Agent = active，NRestarts = 0
Sunshine = active
```

不符合任一項立即停止。不要使用舊 TEST_ID 重跑。

## 1. 離線回歸測試（不連 PX4、不發布）

```bash
python3 -m unittest -v tests/test_p450_delivery_poc_mission.py
```

GO：`Ran 33 tests`、`OK`。

此測試特別確認：PX4 v1.14.3 的真正 landing auto-disarm reason 是 `6`；reason `7` 是
preflight auto-disarm，必須被拒絕。

## 2. P_D：實機只讀預檢

```bash
python3 scripts/p450_delivery_poc_mission.py \
  --preflight-only \
  --test-id P450_20260826_OUTDOOR_V5_PREFLIGHT_E
preflight_exit=$?
echo "PREFLIGHT_EXIT=$preflight_exit"
```

GO：`PREFLIGHT_PASS`、`publishes=0 commands=0`、`PREFLIGHT_EXIT=0`。

## 3. G_D：拆槳無槳 Arm/Land Gate

確認槳已拆除、機體固定、RC mode switch 可接管、Kill 已就緒後執行：

```bash
systemd-inhibit --what=sleep --mode=block \
  --who=P450-V5-Ground \
  --why='V5 prop-free ownership and Land gate' \
  python3 scripts/p450_delivery_poc_mission.py \
    --ground-sequence \
    --test-id P450_20260826_OUTDOOR_V5_GROUND_E \
    --allow-armed \
    --operator-confirmation PROPS_REMOVED_KILL_READY \
    --takeoff-height 0.5 \
    --forward-distance 0
ground_exit=$?
echo "GROUND_EXIT=$ground_exit"
```

GO 必須同時看到 `EKF_SETTLE_CONFIRMED stable_for=5.0s`，再看到：

```text
LAND_MODE_CONFIRMED nav_state=18
PX4 AUTO_DISARM_LAND confirmed（reason=6）
GROUND_EXIT=0
```

看到 `EKF_SETTLE_RESET` 持續重置、`EKF reset counters did not settle before Arm`、reason `7`、
`UNEXPECTED_DISARM_REASON`、任何非 0 exit、failsafe 或 Agent restart，立即 STOP，不得裝槳。

## 4. F1：0.5 m 垂直飛行

只有 P_D 與 G_D 都 GO，且裝槳、清場、Kill ready 後執行：

```bash
systemd-inhibit --what=sleep --mode=block \
  --who=P450-V5-F1 \
  --why='V5 0.5 m outdoor flight gate' \
  python3 scripts/p450_delivery_poc_mission.py \
    --flight \
    --test-id P450_20260826_OUTDOOR_V5_FLIGHT_05M_E \
    --allow-armed \
    --operator-confirmation PROPS_INSTALLED_AREA_CLEAR_KILL_READY \
    --takeoff-height 0.5 \
    --forward-distance 0
f1_exit=$?
echo "F1_EXIT=$f1_exit"
```

GO：先看到 `EKF_SETTLE_CONFIRMED stable_for=5.0s`，再起飛、定高、PX4 Land、`nav_state=18`、
reason `6`、`F1_EXIT=0`，且無 active failsafe、
Agent restart 或 heartbeat >250 ms。

## 5. F2：1 m／前進 5 m／Land

只有 F1 GO，並確認前方 5 m 路徑安全後執行：

```bash
systemd-inhibit --what=sleep --mode=block \
  --who=P450-V5-F2 \
  --why='V5 1 m 5 m delivery PoC' \
  python3 scripts/p450_delivery_poc_mission.py \
    --flight \
    --test-id P450_20260826_OUTDOOR_V5_FLIGHT_1M_5M_E \
    --allow-armed \
    --operator-confirmation PROPS_INSTALLED_AREA_CLEAR_KILL_READY \
    --takeoff-height 1 \
    --forward-distance 5
f2_exit=$?
echo "F2_EXIT=$f2_exit"
```

GO：先看到 `EKF_SETTLE_CONFIRMED stable_for=5.0s`，再 1 m 定高、前進 5 m、Land、reason `6`、
`F2_EXIT=0`。

## 立即停止條件

active failsafe、位置或 heading 無效、dead reckoning、重大 EKF reset、heartbeat gap >250 ms、
Agent restart、RC 接管、任何非 0 exit，立即停止該 Gate，不進下一階段。

Land ACK 本身不代表完成；必須看到 `LAND_MODE_CONFIRMED nav_state=18` 及 reason `6`。
