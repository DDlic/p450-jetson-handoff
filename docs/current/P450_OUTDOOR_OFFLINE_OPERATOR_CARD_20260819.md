# P450 戶外離線操作卡（2026-08-19）

本卡供筆電沒有 Internet、但透過機載基地台使用 QGC TCP 與 Moonlight/Sunshine 操作 NX
時使用。所有 ROS 2／PX4 控制皆在 NX 本機與 `/dev/ttyTHS1` 上運行，不依賴 Internet。

## 絕對停止條件

- 未明確到達對應 Gate，不執行後一段命令。
- `armed`、`Offboard`、failsafe 或設備狀態與預期不符時立即停止。
- 有槳步驟必須由操作者確認 RC mode switch、Kill switch、淨空場地及人員位置。
- 不提高 `COM_OF_LOSS_T`，不 force arm/disarm，不重複 normal Disarm。
- 任一腳本返回非 0、Agent restart、kernel warning/Oops、Offboard loss、GPS/Home/heading
  無效，該 Gate 為 FAIL。

## A. 網路與畫面

1. 筆電連機載基地台；QGC 使用既有 TCP 連接 PX4。
2. NX 透過同一基地台 LAN 提供 Sunshine；Internet 不必存在。
3. Moonlight 使用 720p / 30 fps。自動搜尋不到 NX 時，在 NX terminal 執行：

   ```bash
   ip -4 -br addr
   ```

   將基地台 LAN 介面的 IPv4 手動加入 Moonlight；不要使用手機 tether 的位址。
4. Sunshine 狀態：

   ```bash
   systemctl --user is-active sunshine.service
   ss -lnt | rg '47984|47989|47990|48010'
   ```

5. Internet 優先使用手機 USB tether。若只能使用 TP-Link `88x2bu` USB Wi-Fi，它只是
   管理網路，仍是 kernel 風險；正式 Arm／飛行前應移除該變因或明確接受殘餘風險。

## B. 戶外開機後 NX 唯讀 baseline

在 Sunshine 的 NX terminal 執行：

```bash
cd /media/p450/P450_DATA/src/p450-jetson-handoff
git branch --show-current
git log -1 --oneline
git merge-base --is-ancestor bca8d08 HEAD && echo MISSION_COMMIT_PRESENT
systemctl show p450-micro-xrce-agent.service -p ActiveState -p MainPID -p NRestarts
fuser -v /dev/ttyTHS1
systemctl --user is-active sunshine.service
source /opt/ros/foxy/setup.bash
source /home/p450/p450_ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=0 ROS_LOCALHOST_ONLY=0
ros2 topic list | sort
```

預期顯示 `MISSION_COMMIT_PRESENT`，Agent active、`NRestarts=0`、UART 僅一個 Agent holder，
且可見 `/fmu/in/offboard_control_mode`、`/fmu/in/trajectory_setpoint`、
`/fmu/in/vehicle_command` 與必要 `/fmu/out/*` topics。

## C. QGC 開機後唯讀 baseline

在 QGC MAVLink Console 逐行執行並保存完整輸出：

```text
ver all
commander status
uxrce_dds_client status
param show COM_OF_LOSS_T
param show COM_OBL_RC_ACT
param show COM_DISARM_LAND
param show MPC_LAND_SPEED
listener vehicle_status 1
listener failsafe_flags 1
listener vehicle_land_detected 1
listener vehicle_local_position 1
listener vehicle_gps_position 1
listener home_position 1
```

開始任何控制前必須同時成立：PX4 `c7a3947840`、XRCE connected／Reliable、Standby、
disarmed、非 failsafe、GPS fix／Home／local position／heading 有效、RC 未 lost、電池正常。

## D. Gate R：125 秒 Reliable heartbeat-only

槳葉保持拆除。先在 QGC 執行：

本 Gate 全程保持 Moonlight 以 720p / 30 fps 連線，納入戶外實際 Sunshine CPU／LAN 負載。

```text
commander status
uxrce_dds_client status
uxrce_dds_client trace reset
uxrce_dds_client trace
```

必須為 disarmed、非 Offboard、connected、Reliable、`count=0,frozen=0`。

然後在 NX terminal 執行；此命令不發 setpoint／VehicleCommand，不切模式、不解鎖：

```bash
cd /media/p450/P450_DATA/src/p450-jetson-handoff
source /opt/ros/foxy/setup.bash
source /home/p450/p450_ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=0 ROS_LOCALHOST_ONLY=0
systemd-inhibit --what=sleep --mode=block --who=P450-Outdoor-Reliable --why='125 s Reliable delivery gate' python3 scripts/p450_offboard_heartbeat_probe.py --duration 125 --rate 10 --reliability reliable --csv /media/p450/P450_DATA/builds/NX-user-storage/rosbags/P450_20260819_OUTDOOR_RELIABLE_125S_A/heartbeat.csv
```

完成後在 QGC 執行：

```text
uxrce_dds_client status
uxrce_dds_client trace
commander status
```

Gate R PASS：NX exit 0、約 1251 publishes、PX4 count 相符、無最終遺失、NX/PX4 最大 gap
均不超過 250 ms、Agent restart 0、無 kernel fault、全程 disarmed／非 Offboard。

## E. Gate P：mission no-publish preflight

```bash
cd /media/p450/P450_DATA/src/p450-jetson-handoff
source /opt/ros/foxy/setup.bash
source /home/p450/p450_ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=0 ROS_LOCALHOST_ONLY=0
python3 scripts/p450_delivery_poc_mission.py --preflight-only --test-id P450_20260819_OUTDOOR_MISSION_PREFLIGHT_A
```

必須 exit 0 並顯示 `PREFLIGHT_PASS`；此模式 publishes=0。任何 REFUSED 都不得進 Gate G。

## F. Gate G：無槳 Offboard／Arm／PX4 Land sequence

只有再次實體確認「槳葉拆除、RC mode/Kill 可用、機體固定」後才能執行：

```bash
cd /media/p450/P450_DATA/src/p450-jetson-handoff
source /opt/ros/foxy/setup.bash
source /home/p450/p450_ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=0 ROS_LOCALHOST_ONLY=0
systemd-inhibit --what=sleep --mode=block --who=P450-Ground-Sequence --why='propeller-free ground sequence' python3 scripts/p450_delivery_poc_mission.py --ground-sequence --test-id P450_20260819_OUTDOOR_GROUND_SEQUENCE_A --allow-armed --operator-confirmation PROPS_REMOVED_KILL_READY --takeoff-height 0.5 --forward-distance 0
```

PASS 必須包含 Offboard、normal Arm、PX4 `AUTO_LAND`、
`latest_disarming_reason=AUTO_DISARM_LAND(7)`，且腳本 exit 0。不得以 Kill／normal Disarm
作為 PASS。

## G. Gate F1：有槳 0.5 m 起降

只有 Gate R/P/G 全部 PASS，並完成場地與操作者確認後才可使用：

```bash
cd /media/p450/P450_DATA/src/p450-jetson-handoff
source /opt/ros/foxy/setup.bash
source /home/p450/p450_ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=0 ROS_LOCALHOST_ONLY=0
systemd-inhibit --what=sleep --mode=block --who=P450-Flight-05M --why='0.5 m functional gate' python3 scripts/p450_delivery_poc_mission.py --flight --test-id P450_20260819_OUTDOOR_FLIGHT_05M_A --allow-armed --operator-confirmation PROPS_INSTALLED_AREA_CLEAR_KILL_READY --takeoff-height 0.5 --forward-distance 0
```

## H. Gate F2：最終 1 m／前進 5 m／Land

只有 Gate F1 完整 PASS、飛行方向經 dry-run 與現場確認後才可使用：

```bash
cd /media/p450/P450_DATA/src/p450-jetson-handoff
source /opt/ros/foxy/setup.bash
source /home/p450/p450_ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=0 ROS_LOCALHOST_ONLY=0
systemd-inhibit --what=sleep --mode=block --who=P450-Flight-Final --why='1 m 5 m delivery PoC' python3 scripts/p450_delivery_poc_mission.py --flight --test-id P450_20260819_OUTDOOR_FLIGHT_1M_5M_A --allow-armed --operator-confirmation PROPS_INSTALLED_AREA_CLEAR_KILL_READY --takeoff-height 1.0 --forward-distance 5.0
```

任何 Gate FAIL 都停止，不在同一 TEST_ID 重跑，不跳到後一 Gate。
