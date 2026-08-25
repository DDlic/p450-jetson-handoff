# P450 戶外離線操作卡 V4（2026-08-20）

狀態：修正版 V4 已完成 Ubuntu 22.04/Humble/Gazebo SITL；NX 尚未完成
P_D／G_D／F1_D／F2_D。原始 V4 與 V3 卡禁止再用。

已完成的 300 秒 loaded soak 不重跑。戶外保持 eth0 基地台 LAN 給 QGC/Moonlight；拔掉外部 USB Internet 即可，任務不依賴 Internet。Moonlight 以實際操作負載維持 720p/30。

## 0. 一次性準備

NX：

```bash
cd /media/p450/P450_DATA/src/p450-jetson-handoff
source /opt/ros/foxy/setup.bash
source /home/p450/p450_ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=0 ROS_LOCALHOST_ONLY=0
sha256sum scripts/p450_delivery_poc_mission.py
systemctl show p450-micro-xrce-agent.service -p ActiveState -p MainPID -p NRestarts
findmnt -rn -T /media/p450/P450_DATA -o TARGET,SOURCE,FSTYPE
```

hash 必須是：

```text
825966c9e5f978c8cd6c9c39e2367d068187a3d77da10321b62da4b8f1d17f95  scripts/p450_delivery_poc_mission.py
```

`findmnt` 的 TARGET 必須精確為 `/media/p450/P450_DATA`，SOURCE 必須是 NX 的獨立
microSD ext4。若仍為原始 hash `4d42081c...`、SD 未掛載、Agent 非 active、PID 為 0，
或 `NRestarts` 非預期增加，立即 STOP。

在任何 Arm 前先跑離線回歸測試：

```bash
python3 -m unittest -v tests/test_p450_delivery_poc_mission.py
```

必須為 29/29 PASS。這包含兩個 NX 相容性保護：同檔案系統 bind mount 能正確辨識；
PX4 v1.14.3 真正 landing reason `6` 才能通過，preflight inactivity reason `7` 必須失敗。

## 1. P_D：只讀 preflight，不發布

```bash
python3 scripts/p450_delivery_poc_mission.py --preflight-only --test-id P450_20260820_OUTDOOR_V4_PREFLIGHT_D
echo "PREFLIGHT_EXIT=$?"
```

GO：`PREFLIGHT_PASS`、`PREFLIGHT_ONLY publishes=0 commands=0`、exit 0。

`PREFLIGHT_HEADING_PENDING` 與 raw `GCS_CONNECTION_DIAGNOSTIC ... lost=1` 可接受；active failsafe 不可接受。

## 2. G_D：無槳 Arm／Land

```bash
systemd-inhibit --what=sleep --mode=block --who=P450-V4-Ground --why='V4 prop-free ownership and Land gate' python3 scripts/p450_delivery_poc_mission.py --ground-sequence --test-id P450_20260820_OUTDOOR_V4_GROUND_D --allow-armed --operator-confirmation PROPS_REMOVED_KILL_READY --takeoff-height 0.5 --forward-distance 0
echo "GROUND_EXIT=$?"
```

GO：normal Arm → 3 秒 hold → `LAND_MODE_CONFIRMED nav_state=18` →
`PX4 AUTO_DISARM_LAND confirmed`（reason `6`）→ exit 0。

若出現 auto-preflight disarm／reason `7`、`UNEXPECTED_DISARM_REASON` 或任何非 0 exit，
G_D 為 FAIL；不得把「未確認真正 landing path 的自行解除鎖定」當成 PASS，也不得進入 F1_D。

## 3. F1_D：裝槳，0.5 m 垂直起降

只有 P_D、G_D 都 GO 才執行：

```bash
systemd-inhibit --what=sleep --mode=block --who=P450-V4-F1 --why='V4 0.5 m outdoor flight gate' python3 scripts/p450_delivery_poc_mission.py --flight --test-id P450_20260820_OUTDOOR_V4_FLIGHT_05M_D --allow-armed --operator-confirmation PROPS_INSTALLED_AREA_CLEAR_KILL_READY --takeoff-height 0.5 --forward-distance 0
echo "F1_EXIT=$?"
```

GO：起飛、0.5 m hold、`LAND_MODE_CONFIRMED nav_state=18`、reason `6` 的
AUTO_DISARM_LAND、exit 0；無 active failsafe、無 Agent restart。

## 4. F2_D：1 m／前進 5 m／Land

只有 F1_D GO 且確認機頭前方 5 m 路徑後執行：

```bash
systemd-inhibit --what=sleep --mode=block --who=P450-V4-F2 --why='V4 1 m 5 m delivery PoC' python3 scripts/p450_delivery_poc_mission.py --flight --test-id P450_20260820_OUTDOOR_V4_FLIGHT_1M_5M_D --allow-armed --operator-confirmation PROPS_INSTALLED_AREA_CLEAR_KILL_READY --takeoff-height 1 --forward-distance 5
echo "F2_EXIT=$?"
```

## 判讀與 STOP

- RC 切離 Offboard：應顯示 `CONTROL_RELINQUISHED`、exit 20；腳本不再送 Land/Disarm。這是安全接管成功，但該 Gate 判 FAIL。
- Land ACK 不是完成；必須看到 `LAND_MODE_CONFIRMED nav_state=18`。
- PX4 v1.14.3 的真正 auto-disarm-land reason 是 `6`；reason `7` 是 auto-disarm-preflight，
  必須拒絕。這是固定韌體的實際 enum，不得使用生成訊息內錯位的常數 `7` 判定 landing。
- `heading_good_for_control=false` 與 raw GCS lost 只是診斷，不單獨 STOP。
- active failsafe、position/global invalid、dead reckoning、material EKF reset、heartbeat >250 ms、Agent restart、非 0 exit：該 Gate 立即停止，不進下一步。
- 需要人工接管時用 RC mode switch；必要時依現場程序 Kill。不要重用 TEST_ID。
