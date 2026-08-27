# P450 戶外離線最終卡 V2（已確認）

> **SUPERSEDED：V3 已取代本卡。不得再用 V2 執行 Gate P/G/F1/F2。**
> 使用 `P450_OUTDOOR_OFFLINE_OPERATOR_CARD_V3_20260820.md`。

- 狀態：`CONFIRMED_READY_OFFLINE`
- 日期：2026-08-20
- Issue 卡：https://github.com/DDlic/p450-jetson-handoff/issues/1#issuecomment-5351719448
- 確認紀錄：https://github.com/DDlic/p450-jetson-handoff/issues/1#issuecomment-5351730261

## 已審查結論

- 已完成的室內 15 分鐘 disarmed mission-order soak B 不重跑。
- 既有正式 Gate R 的 250 ms freshness 結論仍是 FAIL；本卡不改寫該結論。
- 戶外只做一次 300 秒 disarmed soak，確認實際 Moonlight 負載下沒有 1 秒級
  Offboard continuity loss，再進短無槳 Gate G。
- 「離線」只代表拔除手機 USB Internet／外部 WAN；**eth0 基地台 LAN 必須保留**，
  供 Moonlight 與 QGC TCP。
- 全程 Moonlight 720p/30 fps 保持連線，納入正式操作負載。
- 不重啟／斷線就不重複已通過步驟。任一 Gate FAIL 立即停止，不跳關、不沿用相同
  TEST_ID。
- Offboard-loss 策略維持 `COM_OF_LOSS_T=1.0`、`COM_OBL_RC_ACT=0`
  （Position + RC 接管），不是自動 Land。不得現場自行改參數。

## 0. 出發前 artifact

NX 本機 5 分鐘 soak 已支援，soak + mission tests `21/21 PASS`。

```text
scripts/p450_disarmed_command_soak.py
sha256 663940a4fb7c70c52570e26e4971b4590b490ed3f01f1a5af95e090c77363f3e
```

注意：soak 腳本與測試目前在 NX worktree 為 untracked，尚未 commit/push。本卡只使用
上述 exact local hash。

## 1. 到場快速 baseline（無槳）

筆電連基地台、QGC 與 Moonlight 連上；拔掉手機 USB WAN，**不要關 eth0**。

NX terminal：

```bash
cd /media/p450/P450_DATA/src/p450-jetson-handoff
source /opt/ros/foxy/setup.bash
source /home/p450/p450_ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=0 ROS_LOCALHOST_ONLY=0
ip -br addr
timeout 3 ping -c 1 -W 1 1.1.1.1
systemctl show p450-micro-xrce-agent.service -p ActiveState -p MainPID -p NRestarts
systemctl --user is-active sunshine.service
sha256sum scripts/p450_disarmed_command_soak.py
```

GO：`eth0 UP 192.168.10.100/24`、Internet ping 失敗、Agent active／`NRestarts=0`、
Sunshine active、hash 相符。其餘情況 STOP。

QGC MAVLink Console：

```text
commander status
uxrce_dds_client status
param show COM_OF_LOSS_T
param show COM_OBL_RC_ACT
listener vehicle_status 1
listener failsafe_flags 1
listener vehicle_local_position 1
listener vehicle_gps_position 1
listener home_position 1
```

GO：Standby/disarmed、no failsafe、XRCE connected/Reliable、
`COM_OF_LOSS_T=1.0`、`COM_OBL_RC_ACT=0`。

Gate G 前還必須有：

- `pre_flight_checks_pass=true`
- local XY/Z/velocity/global/Home valid
- `heading_good_for_control=true`
- 非 dead reckoning

尚未有效就原地等，不繞過。

## 2. Gate S：300 秒戶外離線 loaded soak

條件：無槳、全程 Moonlight 720p/30 ON。

QGC 先清空本輪 PX4 counter：

```text
uxrce_dds_client trace reset
uxrce_dds_client status
uxrce_dds_client trace
```

必須顯示 Offboard count 0、trace count 0/frozen 0。

NX terminal：

```bash
TEST_ID=P450_20260820_OUTDOOR_OFFLINE_DISARMED_SOAK_5M_A
systemd-inhibit --what=sleep --mode=block --who=P450-Outdoor-Soak --why='5 min outdoor offline Moonlight-loaded soak' python3 scripts/p450_disarmed_command_soak.py --test-id "$TEST_ID" --duration 300 --rate 10 --virtual-height 1 --virtual-forward 5
SOAK_EXIT=$?
echo "SOAK_EXIT=$SOAK_EXIT"
```

完成後 QGC：

```text
uxrce_dds_client status
uxrce_dds_client trace
commander status
listener vehicle_status 1
commander mode stabilized
commander status
```

Gate S GO 必須全部成立：

- NX 顯示 `SOAK COMPLETE PASS`、`SOAK_EXIT=0`、約 3030 publishes。
- 全程 disarmed、無 failsafe、無 telemetry stale／endpoint mismatch；
  NX `over_1000ms=0`。
- PX4 Offboard count 與 NX publishes 相符，max gap 小於 `1,000,000 us`，
  無 Offboard-loss/failsafe。
- `NRestarts=0`，無 kernel panic/Oops。
- 最後已回 STAB、Standby/disarmed。
- PX4 `>250 ms` 若非 0，照實記錄為既有 Gate R freshness 殘餘風險；不宣稱
  正式 Gate R PASS。

## 3. Gate P：mission no-publish preflight（無槳）

NX terminal：

```bash
python3 scripts/p450_delivery_poc_mission.py --preflight-only --test-id P450_20260820_OUTDOOR_MISSION_PREFLIGHT_B
echo "PREFLIGHT_EXIT=$?"
```

只有 `PREFLIGHT_PASS`、publishes=0、commands=0、exit 0 才能進 Gate G。

## 4. Gate G：短無槳實機 sequence

機體固定、RC mode/Kill 在手邊。

NX terminal：

```bash
systemd-inhibit --what=sleep --mode=block --who=P450-Ground-Gate --why='short prop-free ground sequence' python3 scripts/p450_delivery_poc_mission.py --ground-sequence --test-id P450_20260820_OUTDOOR_GROUND_SEQUENCE_B --allow-armed --operator-confirmation PROPS_REMOVED_KILL_READY --takeoff-height 0.5 --forward-distance 0
echo "GROUND_EXIT=$?"
```

GO：normal Arm → PX4 Land → PX4 `AUTO_DISARM_LAND(7)` → exit 0。

若出現 not-landed、不能 auto-disarm、需 Kill、腳本 abort 或非 0，Gate G FAIL，
**不裝槳**。

## 5. Gate F1：有槳 0.5 m 起降

只有 Gate S/P/G 全部 GO，RC mode/Kill、場地與人員淨空確認後：

```bash
systemd-inhibit --what=sleep --mode=block --who=P450-Flight-F1 --why='0.5 m outdoor flight gate' python3 scripts/p450_delivery_poc_mission.py --flight --test-id P450_20260820_OUTDOOR_FLIGHT_05M_B --allow-armed --operator-confirmation PROPS_INSTALLED_AREA_CLEAR_KILL_READY --takeoff-height 0.5 --forward-distance 0
echo "F1_EXIT=$?"
```

GO：穩定起飛／定高／PX4 Land／AUTO_DISARM_LAND、exit 0，無 failsafe、
無 Offboard loss、無 Agent restart。

## 6. Gate F2：最終 1 m／前進 5 m／Land

只有 F1 完整 GO 且前進方向現場核對後：

```bash
systemd-inhibit --what=sleep --mode=block --who=P450-Flight-F2 --why='1 m 5 m delivery PoC' python3 scripts/p450_delivery_poc_mission.py --flight --test-id P450_20260820_OUTDOOR_FLIGHT_1M_5M_B --allow-armed --operator-confirmation PROPS_INSTALLED_AREA_CLEAR_KILL_READY --takeoff-height 1 --forward-distance 5
echo "F2_EXIT=$?"
```

## 通用 STOP

任一非 0、PX4/ROS telemetry stale、failsafe、Offboard loss、位置/Home/heading 失效、
Agent restart、kernel panic/Oops、QGC/Moonlight 操作失去掌握：立即以 RC mode 接管；
必要時依現場程序 Kill。停止後不跳下一 Gate。



p450@P450-NX:~$ sha256 663940a4fb7c70c52570e26e4971b4590b490ed3f01f1a5af95e090c77363f3e
bash: sha256: command not found
p450@P450-NX:~$ cd /media/p450/P450_DATA/src/p450-jetson-handoff
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ source /opt/ros/foxy/setup.bash
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ source /home/p450/p450_ros2_ws/install/setup.bash
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ export ROS_DOMAIN_ID=0 ROS_LOCALHOST_ONLY=0
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ ip -br addr
lo               UNKNOWN        127.0.0.1/8 ::1/128 
dummy0           DOWN           
eth0             UP             192.168.10.100/24 fe80::250:f183:84b3:e0f2/64 
l4tbr0           DOWN           
rndis0           DOWN           
usb0             DOWN           
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ timeout 3 ping -c 1 -W 1 1.1.1.1
PING 1.1.1.1 (1.1.1.1) 56(84) bytes of data.
From 192.168.10.5 icmp_seq=1 Destination Host Unreachable

--- 1.1.1.1 ping statistics ---
1 packets transmitted, 0 received, +1 errors, 100% packet loss, time 0ms

p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ systemctl show p450-micro-xrce-agent.service -p ActiveState -p MainPID -p NRestarts
MainPID=1645
NRestarts=0
ActiveState=active
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ systemctl --user is-active sunshine.service
active
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ sha256sum scripts/p450_disarmed_command_soak.py
663940a4fb7c70c52570e26e4971b4590b490ed3f01f1a5af95e090c77363f3e  scripts/p450_disarmed_command_soak.py
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ TEST_ID=P450_20260820_OUTDOOR_OFFLINE_DISARMED_SOAK_5M_A
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ systemd-inhibit --what=sleep --mode=block --who=P450-Outdoor-Soak --why='5 min outdoor offline Moonlight-loaded soak' python3 scripts/p450_disarmed_command_soak.py --test-id "$TEST_ID" --duration 300 --rate 10 --virtual-height 1 --virtual-forward 5
SOAK_LOG_DIR=/media/p450/P450_DATA/builds/NX-user-storage/rosbags/P450_20260820_OUTDOOR_OFFLINE_DISARMED_SOAK_5M_A
SOAK_COMMAND_ALLOWLIST=[21, 176] ARM_DISARM_COMMAND=400 blocked=true
SOAK PRECHECK START test_id=P450_20260820_OUTDOOR_OFFLINE_DISARMED_SOAK_5M_A duration=300.0 rate=10.0
SOAK PRECHECK PREFLIGHT_PASS start=(-14.653192520141602, 10.461546897888184, -17.073301315307617, 0.902247428894043) heading_good=0 xy_valid=1 z_valid=1
SOAK REQUEST_OFFBOARD_DISARMED COMMAND_SEND command=176 confirmation=0
SOAK REQUEST_OFFBOARD_DISARMED COMMAND_SEND command=176 confirmation=1
SOAK REQUEST_OFFBOARD_DISARMED COMMAND_SEND command=176 confirmation=2
SOAK REQUEST_OFFBOARD_DISARMED COMMAND_SEND command=176 confirmation=3
SOAK REQUEST_OFFBOARD_DISARMED COMMAND_STATE_CONFIRMED command=176 nav_state=14
SOAK REQUEST_OFFBOARD_DISARMED OFFBOARD_CONFIRMED vehicle remains disarmed
SOAK VIRTUAL_TAKEOFF PHASE_TARGET target=(-14.653192520141602, 10.461546897888184, -18.073301315307617)
SOAK HOLD_AFTER_TAKEOFF PHASE_TARGET target=(-14.653192520141602, 10.461546897888184, -18.073301315307617)
SOAK VIRTUAL_FORWARD PHASE_TARGET target=(-11.553952878307244, 14.385156669830653, -18.073301315307617)
SOAK REQUEST_LAND_DISARMED COMMAND_SEND command=21 confirmation=0
SOAK REQUEST_LAND_DISARMED COMMAND_SEND command=21 confirmation=1
SOAK REQUEST_LAND_DISARMED COMMAND_STATE_CONFIRMED command=21 nav_state=18
SOAK COMPLETE PASS mission-order soak complete; Offboard held while disarmed; PX4 Land ACK accepted
SOAK COMPLETE SUMMARY publishes=3042 max_gap_ms=181.068 over_150ms=8 over_250ms=0 over_500ms=0 over_1000ms=0
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ SOAK_EXIT=$?
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ echo "SOAK_EXIT=$SOAK_EXIT"
SOAK_EXIT=0
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ systemd-inhibit --what=sleep --mode=block --who=P450-Flight-F1 --why='0.5 m outdoor flight gate' python3 scripts/p450_delivery_poc_mission.py --flight --test-id P450_20260820_OUTDOOR_FLIGHT_05M_B --allow-armed --operator-confirmation PROPS_INSTALLED_AREA_CLEAR_KILL_READY --takeoff-height 0.5 --forward-distance 0
MISSION_LOG_DIR=/media/p450/P450_DATA/builds/NX-user-storage/rosbags/P450_20260820_OUTDOOR_FLIGHT_05M_B
MISSION PRECHECK START mode=flight test_id=P450_20260820_OUTDOOR_FLIGHT_05M_B
MISSION PRECHECK ARMING_STATE 1
MISSION PRECHECK NAV_STATE 15
MISSION PRECHECK PREFLIGHT_REFUSED local/global position or heading is not flight-valid
python3 failed with exit status 2.
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ echo "F1_EXIT=$?"
F1_EXIT=2
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ systemd-inhibit --what=sleep --mode=block --who=P450-Flight-F1 --why='0.5 m outdoor flight gate' python3 scripts/p450_delivery_poc_mission.py --flight --test-id P450_20260820_OUTDOOR_FLIGHT_05M_B --allow-armed --operator-confirmation PROPS_INSTALLED_AREA_CLEAR_KILL_READY --takeoff-height 0.5 --forward-distance 0
Traceback (most recent call last):
  File "scripts/p450_delivery_poc_mission.py", line 963, in <module>
    raise SystemExit(main())
  File "scripts/p450_delivery_poc_mission.py", line 950, in main
    log_dir.mkdir(parents=True, exist_ok=False)
  File "/usr/lib/python3.8/pathlib.py", line 1288, in mkdir
    self._accessor.mkdir(self, mode)
FileExistsError: [Errno 17] File exists: '/media/p450/P450_DATA/builds/NX-user-storage/rosbags/P450_20260820_OUTDOOR_FLIGHT_05M_B'
python3 failed with exit status 1.
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ systemd-inhibit --what=sleep --mode=block --who=P450-Flight-F2 --why='1 m 5 m delivery PoC' python3 scripts/p450_delivery_poc_mission.py --flight --test-id P450_20260820_OUTDOOR_FLIGHT_1M_5M_B --allow-armed --operator-confirmation PROPS_INSTALLED_AREA_CLEAR_KILL_READY --takeoff-height 1 --forward-distance 5
MISSION_LOG_DIR=/media/p450/P450_DATA/builds/NX-user-storage/rosbags/P450_20260820_OUTDOOR_FLIGHT_1M_5M_B
MISSION PRECHECK START mode=flight test_id=P450_20260820_OUTDOOR_FLIGHT_1M_5M_B
MISSION PRECHECK ARMING_STATE 1
MISSION PRECHECK NAV_STATE 15
MISSION PRECHECK PREFLIGHT_REFUSED local/global position or heading is not flight-valid
python3 failed with exit status 2.
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ echo "F2_EXIT=$?"
F2_EXIT=2
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ 


