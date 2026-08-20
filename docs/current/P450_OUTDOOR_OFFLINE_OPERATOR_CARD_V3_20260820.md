# P450 戶外離線操作卡 V3（2026-08-20 heading 修正版）

狀態：V2 已作廢；V3 為下一次戶外續測唯一操作卡。

## 已完成，不重跑

- 300 秒戶外離線 loaded soak A：operational PASS。
- NX 3042 publishes，max gap 181.068 ms，>250 ms=0。
- PX4 3042/3042，max gap 742131 us，未達 `COM_OF_LOSS_T=1.0 s`。
- 嚴格 250 ms Gate R 仍非 PASS；此殘餘風險不隱藏。
- F1/F2 的 `_B` 只留下 PRECHECK FAIL，publishes=0，沒有實際飛行。

## 本卡使用的 mission artifact

在 repo 根目錄執行：

```bash
sha256sum scripts/p450_delivery_poc_mission.py
```

必須得到：

```text
32c2360cc533507317ee036707916351a3dff783e0ab93354009e1f4bb33b53b  scripts/p450_delivery_poc_mission.py
```

V3 heading 規則：

- 地面允許 `heading_good_for_control=false`，因為 PX4 v1.14 使用磁羅盤時該 final flag 通常需飛起後才成立。
- 地面仍必須有 PX4 preflight PASS、有效 XY/Z/速度/global/Home、finite heading、非 dead reckoning、無 failsafe。
- 有槳 flight 到達起飛高度後，若 final heading 仍為 false，腳本會要求 PX4 Land 並判 FAIL。

## 1. 到場一次性準備（先不裝槳）

保留 eth0 基地台 LAN 供 QGC TCP/Moonlight，外部 USB Internet 可拔除。Moonlight 維持 720p/30。

NX terminal：

```bash
cd /media/p450/P450_DATA/src/p450-jetson-handoff
source /opt/ros/foxy/setup.bash
source /home/p450/p450_ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=0 ROS_LOCALHOST_ONLY=0
sha256sum scripts/p450_delivery_poc_mission.py
systemctl show p450-micro-xrce-agent.service -p ActiveState -p MainPID -p NRestarts
```

GO：hash 相符、Agent active、`NRestarts=0`。

QGC：

```text
commander status
uxrce_dds_client status
listener vehicle_status 1
listener failsafe_flags 1
listener vehicle_local_position 1
listener vehicle_gps_position 1
listener home_position 1
```

GO：

- Standby/disarmed、STAB、no failsafe。
- XRCE connected/Reliable。
- `pre_flight_checks_pass=true`。
- XY/Z、水平/垂直速度、global 與 Home valid。
- `dead_reckoning=false`、heading 為有限數值。
- `heading_good_for_control=false` 在地面不單獨阻擋。

## 2. Gate P_C：no-publish preflight

NX：

```bash
python3 scripts/p450_delivery_poc_mission.py --preflight-only --test-id P450_20260820_OUTDOOR_MISSION_PREFLIGHT_C
echo "PREFLIGHT_EXIT=$?"
```

GO：顯示 `PREFLIGHT_PASS`、publishes=0、commands=0、exit 0。若顯示
`PREFLIGHT_HEADING_PENDING` 可繼續 Gate G，這是預期訊息。

## 3. Gate G_C：短無槳 Arm/Land sequence

NX：

```bash
systemd-inhibit --what=sleep --mode=block --who=P450-Ground-Gate --why='short prop-free ground sequence' python3 scripts/p450_delivery_poc_mission.py --ground-sequence --test-id P450_20260820_OUTDOOR_GROUND_SEQUENCE_C --allow-armed --operator-confirmation PROPS_REMOVED_KILL_READY --takeoff-height 0.5 --forward-distance 0
echo "GROUND_EXIT=$?"
```

GO：normal Arm → 3 秒 hold → PX4 Land → `AUTO_DISARM_LAND(7)` → exit 0。

若 not-landed、無法 auto-disarm、需要 Kill、abort 或非 0：停止，不裝槳。

## 4. Gate F1_C：有槳 0.5 m 起降

只有 P_C、G_C 都 GO 後才裝槳：

```bash
systemd-inhibit --what=sleep --mode=block --who=P450-Flight-F1 --why='0.5 m outdoor flight gate' python3 scripts/p450_delivery_poc_mission.py --flight --test-id P450_20260820_OUTDOOR_FLIGHT_05M_C --allow-armed --operator-confirmation PROPS_INSTALLED_AREA_CLEAR_KILL_READY --takeoff-height 0.5 --forward-distance 0
echo "F1_EXIT=$?"
```

GO：起飛、定高、final heading 完成、PX4 Land、AUTO_DISARM_LAND、exit 0，無 failsafe、
無 Offboard loss、無 Agent restart。

若起飛後出現 `final in-flight heading alignment did not complete`，腳本應要求 PX4 Land；
該 Gate 判 FAIL，不進 F2。

## 5. Gate F2_C：1 m／前進 5 m／Land

只有 F1_C 完整 GO 且前進方向確認後：

```bash
systemd-inhibit --what=sleep --mode=block --who=P450-Flight-F2 --why='1 m 5 m delivery PoC' python3 scripts/p450_delivery_poc_mission.py --flight --test-id P450_20260820_OUTDOOR_FLIGHT_1M_5M_C --allow-armed --operator-confirmation PROPS_INSTALLED_AREA_CLEAR_KILL_READY --takeoff-height 1 --forward-distance 5
echo "F2_EXIT=$?"
```

## 通用 STOP

任一非 0、telemetry stale、failsafe、Offboard loss、position/Home 失效、dead reckoning、
Agent restart、kernel panic/Oops、QGC/Moonlight 操作失去掌握：立即以 RC mode 接管；
必要時依現場程序 Kill。停止後不跳下一 Gate，也不重用 TEST_ID。
