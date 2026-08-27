# P450 戶外離線正式測試卡 V6（2026-08-26）

## 目的

V6 是單一命令的正式飛行流程：由腳本自動完成預檢、Offboard、Arm、起飛、短航線、
PX4 Land 與自動解鎖。不再要求先人工執行 G_D、F1，再執行 F2；也不要求拆槳。

目前右後槳無法拆除，因此本次測試按「全槳安裝」條件執行。操作者必須人在機體旁，
RC/Kill 隨時可接管。這個確認只需在同一條命令內完成一次。

## 執行前唯一確認

- 所有槳均已安裝且固定；右後槳不拆除。
- 空域清空，操作者在機體旁，Kill/RC 接管可立即使用。
- 不重用任何已存在的 `TEST_ID`。

## V6 單一命令

```bash
cd /media/p450/P450_DATA/src/p450-jetson-handoff
source /opt/ros/foxy/setup.bash
source /home/p450/p450_ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=0 ROS_LOCALHOST_ONLY=0

TEST_ID=P450_20260826_OUTDOOR_V6_FLIGHT_1M_5M_F
systemd-inhibit --what=sleep --mode=block \
  --who=P450-V6-Flight \
  --why='V6 single-command outdoor flight' \
  python3 scripts/p450_delivery_poc_mission.py \
    --v6-flight \
    --test-id "$TEST_ID" \
    --allow-armed \
    --operator-confirmation V6_PROPS_INSTALLED_AREA_CLEAR_KILL_READY \
    --takeoff-height 0.5 \
    --forward-distance 5
V6_EXIT=$?
echo "V6_EXIT=$V6_EXIT"
```

## 通過條件

同一輪必須看到：

```text
artifact=V6 mode=v6-flight
PREFLIGHT_PASS
EKF_SETTLE_CONFIRMED stable_for=5.0s
REQUEST_OFFBOARD ... nav_state 14
REQUEST_ARM ... arming_state 2
LAND_MODE_CONFIRMED nav_state=18
PX4 AUTO_DISARM_LAND confirmed
V6_EXIT=0
```

結果證據位於：
`/media/p450/P450_DATA/builds/NX-user-storage/rosbags/$TEST_ID/`。

## 腳本自動停止條件

腳本仍會在任何一項發生時停止控制並依狀態請求 PX4 Land 或交還 RC/Kill：

- RC/manual control 或 GCS/Offboard 失聯、PX4 failsafe、DDS endpoint 不符。
- heartbeat gap 超過 250 ms、遙測 stale、電池異常或 failure detector 啟動。
- local/global position、速度、heading 失效、dead reckoning 或重大 EKF reset。
- 起飛、航點、Land、PX4 auto-disarm 未在期限內確認。

這些是飛行期間的即時保護，不是要操作者逐項手動執行的前置 gate；V6 不會以放寬
安全門的方式掩蓋異常。任何非零 `V6_EXIT` 都是 FAIL，不得把同一 `TEST_ID` 重跑。

^[	p450@P450-NX:~$ ^C
p450@P450-NX:~$ cd /media/p450/P450_DATA/src/p450-jetson-handoff
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ source /opt/ros/foxy/setup.bash
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ source /home/p450/p450_ros2_ws/install/setup.bash
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ export ROS_DOMAIN_ID=0 ROS_LOCALHOST_ONLY=0
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ 
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ TEST_ID=P450_20260826_OUTDOOR_V6_FLIGHT_1M_5M_A
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ systemd-inhibit --what=sleep --mode=block \
>   --who=P450-V6-Flight \
>   --why='V6 single-command outdoor flight' \
>   python3 scripts/p450_delivery_poc_mission.py \
>     --v6-flight \
>     --test-id "$TEST_ID" \



>     --allow-armed \
>     --operator-confirmation V6_PROPS_INSTALLED_AREA_CLEAR_KILL_READY \
>     --takeoff-height 1 \
>     --forward-distance 5
REFUSED: mission log directory already exists: /media/p450/P450_DATA/builds/NX-user-storage/rosbags/P450_20260826_OUTDOOR_V6_FLIGHT_1M_5M_A; choose a new --test-id; existing evidence was not modified
python3 failed with exit status 2.
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ V6_EXIT=$?
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ echo "V6_EXIT=$V6_EXIT"
V6_EXIT=2
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ ^C
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ cd /media/p450/P450_DATA/src/p450-jetson-handoff
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ source /opt/ros/foxy/setup.bash
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ source /home/p450/p450_ros2_ws/install/setup.bash
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ export ROS_DOMAIN_ID=0 ROS_LOCALHOST_ONLY=0
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ 
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ TEST_ID=P450_20260826_OUTDOOR_V6_FLIGHT_1M_5M_B
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ systemd-inhibit --what=sleep --mode=block \
>   --who=P450-V6-Flight \
>   --why='V6 single-command outdoor flight' \
>   python3 scripts/p450_delivery_poc_mission.py \
>     --v6-flight \
>     --test-id "$TEST_ID" \
>     --allow-armed \
>     --operator-confirmation V6_PROPS_INSTALLED_AREA_CLEAR_KILL_READY \
>     --takeoff-height 1 \
>     --forward-distance 5
MISSION_LOG_DIR=/media/p450/P450_DATA/builds/NX-user-storage/rosbags/P450_20260826_OUTDOOR_V6_FLIGHT_1M_5M_B
MISSION PRECHECK START artifact=V6 mode=v6-flight test_id=P450_20260826_OUTDOOR_V6_FLIGHT_1M_5M_B
MISSION PRECHECK OFFBOARD_CONTROL_DIAGNOSTIC enabled=0
MISSION PRECHECK HEADING_GOOD_DIAGNOSTIC value=0
MISSION PRECHECK ARMING_STATE 1
MISSION PRECHECK NAV_STATE 15
MISSION PRECHECK GCS_CONNECTION_DIAGNOSTIC raw_status_lost=0
MISSION PRECHECK ROUTE start=(-3.964207172393799, -4.624656677246094, 9.741174697875977, -3.1064751148223877) takeoff=(-3.964207172393799, -4.624656677246094, 8.741174697875977) goal=(-8.961124385409047, -4.800208282969122, 8.741174697875977) reset_counters={'xy': 4, 'z': 4, 'vxy': 4, 'vz': 2, 'heading': 2}
MISSION PRECHECK PREFLIGHT_HEADING_PENDING PX4 final heading alignment is expected after liftoff when using magnetometer fusion
MISSION PRECHECK PREFLIGHT_PASS offboard_subscriptions=1 setpoint_subscriptions=1 command_subscriptions=1
MISSION STREAM_PREROLL TRANSITION
MISSION REQUEST_OFFBOARD TRANSITION
MISSION REQUEST_OFFBOARD COMMAND_BEGIN command=176
MISSION REQUEST_OFFBOARD COMMAND_SEND command=176 attempt=1
MISSION REQUEST_OFFBOARD COMMAND_SEND command=176 attempt=2
MISSION REQUEST_OFFBOARD NAV_STATE 14
MISSION REQUEST_OFFBOARD OFFBOARD_CONTROL_DIAGNOSTIC enabled=1
MISSION REQUEST_OFFBOARD EKF_SETTLE_WAIT require reset counters stable for 5.0s before Arm
MISSION WAIT_EKF_SETTLE TRANSITION
MISSION WAIT_EKF_SETTLE EKF_SETTLE_RESET counters=(4, 4, 4, 2, 2); restart 5.0s window
MISSION WAIT_EKF_SETTLE EKF_SETTLE_CONFIRMED stable_for=5.0s counters=(4, 4, 4, 2, 2)
MISSION REQUEST_ARM TRANSITION
MISSION REQUEST_ARM COMMAND_BEGIN command=400
MISSION REQUEST_ARM COMMAND_SEND command=400 attempt=1
MISSION REQUEST_ARM COMMAND_SEND command=400 attempt=2
MISSION REQUEST_ARM ARMING_STATE 2
MISSION TAKEOFF TRANSITION
MISSION TAKEOFF ABORT takeoff timeout
MISSION REQUEST_LAND_ABORT TRANSITION takeoff timeout
MISSION REQUEST_LAND_ABORT COMMAND_BEGIN command=21
MISSION REQUEST_LAND_ABORT COMMAND_SEND command=21 attempt=1
MISSION REQUEST_LAND_ABORT NAV_STATE 18
MISSION REQUEST_LAND_ABORT LAND_MODE_CONFIRMED nav_state=18 ack=None
MISSION REQUEST_LAND_ABORT LAND_FEEDBACK_FALLBACK VehicleLandDetected is not bridged; require AUTO_DISARM_LAND reason
MISSION WAIT_AUTO_DISARM_FALLBACK TRANSITION
MISSION WAIT_AUTO_DISARM_FALLBACK OFFBOARD_CONTROL_DIAGNOSTIC enabled=0
MISSION WAIT_AUTO_DISARM_FALLBACK ARMING_STATE 1
MISSION FAILED TRANSITION PX4 AUTO_DISARM_LAND confirmed
MISSION FAILED HEARTBEAT_SUMMARY publishes=233 max_gap_ms=113.421 over_150ms=0 over_250ms=0 over_500ms=0
python3 failed with exit status 12.
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ V6_EXIT=$?
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ echo "V6_EXIT=$V6_EXIT"
V6_EXIT=12
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ cd /media/p450/P450_DATA/src/p450-jetson-handoff
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ source /opt/ros/foxy/setup.bash
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ source /home/p450/p450_ros2_ws/install/setup.bash
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ export ROS_DOMAIN_ID=0 ROS_LOCALHOST_ONLY=0
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ 
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ TEST_ID=P450_20260826_OUTDOOR_V6_FLIGHT_1M_5M_B
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ systemd-inhibit --what=sleep --mode=block \
>   --who=P450-V6-Flight \
>   --why='V6 single-command outdoor flight' \
>   python3 scripts/p450_delivery_poc_mission.py \
>     --v6-flight \
>     --test-id "$TEST_ID" \
>     --allow-armed \
>     --operator-confirmation V6_PROPS_INSTALLED_AREA_CLEAR_KILL_READY \
>     --takeoff-height 1 \
>     --forward-distance 5
REFUSED: mission log directory already exists: /media/p450/P450_DATA/builds/NX-user-storage/rosbags/P450_20260826_OUTDOOR_V6_FLIGHT_1M_5M_B; choose a new --test-id; existing evidence was not modified
python3 failed with exit status 2.
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ V6_EXIT=$?
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ echo "V6_EXIT=$V6_EXIT"^C
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ cd /media/p450/P450_DATA/src/p450-jetson-handoff
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ source /opt/ros/foxy/setup.bash
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ source /home/p450/p450_ros2_ws/install/setup.bash
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ export ROS_DOMAIN_ID=0 ROS_LOCALHOST_ONLY=0
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ 
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ TEST_ID=P450_20260826_OUTDOOR_V6_FLIGHT_1M_5M_C
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ systemd-inhibit --what=sleep --mode=block \
>   --who=P450-V6-Flight \
>   --why='V6 single-command outdoor flight' \
>   python3 scripts/p450_delivery_poc_mission.py \
>     --v6-flight \
>     --test-id "$TEST_ID" \
>     --allow-armed \
>     --operator-confirmation V6_PROPS_INSTALLED_AREA_CLEAR_KILL_READY \
>     --takeoff-height 1 \
>     --forward-distance 5
MISSION_LOG_DIR=/media/p450/P450_DATA/builds/NX-user-storage/rosbags/P450_20260826_OUTDOOR_V6_FLIGHT_1M_5M_C
MISSION PRECHECK START artifact=V6 mode=v6-flight test_id=P450_20260826_OUTDOOR_V6_FLIGHT_1M_5M_C
MISSION PRECHECK HEADING_GOOD_DIAGNOSTIC value=0
MISSION PRECHECK ARMING_STATE 1
MISSION PRECHECK NAV_STATE 15
MISSION PRECHECK GCS_CONNECTION_DIAGNOSTIC raw_status_lost=0
MISSION PRECHECK OFFBOARD_CONTROL_DIAGNOSTIC enabled=0
MISSION PRECHECK ROUTE start=(-85.97161102294922, 2.3199379444122314, 13.029838562011719, 0.7588479518890381) takeoff=(-85.97161102294922, 2.3199379444122314, 12.029838562011719) goal=(-82.34346502190783, 5.760367655237225, 12.029838562011719) reset_counters={'xy': 4, 'z': 5, 'vxy': 4, 'vz': 2, 'heading': 2}
MISSION PRECHECK PREFLIGHT_HEADING_PENDING PX4 final heading alignment is expected after liftoff when using magnetometer fusion
MISSION PRECHECK PREFLIGHT_PASS offboard_subscriptions=1 setpoint_subscriptions=1 command_subscriptions=1
MISSION STREAM_PREROLL TRANSITION
MISSION REQUEST_OFFBOARD TRANSITION
MISSION REQUEST_OFFBOARD COMMAND_BEGIN command=176
MISSION REQUEST_OFFBOARD COMMAND_SEND command=176 attempt=1
MISSION REQUEST_OFFBOARD COMMAND_SEND command=176 attempt=2
MISSION REQUEST_OFFBOARD NAV_STATE 14
MISSION REQUEST_OFFBOARD OFFBOARD_CONTROL_DIAGNOSTIC enabled=1
MISSION REQUEST_OFFBOARD EKF_SETTLE_WAIT require reset counters stable for 5.0s before Arm
MISSION WAIT_EKF_SETTLE TRANSITION
MISSION WAIT_EKF_SETTLE EKF_SETTLE_RESET counters=(4, 5, 4, 2, 2); restart 5.0s window
MISSION WAIT_EKF_SETTLE EKF_SETTLE_CONFIRMED stable_for=5.0s counters=(4, 5, 4, 2, 2)
MISSION REQUEST_ARM TRANSITION
MISSION REQUEST_ARM COMMAND_BEGIN command=400
MISSION REQUEST_ARM COMMAND_SEND command=400 attempt=1
MISSION REQUEST_ARM ARMING_STATE 2
MISSION TAKEOFF TRANSITION
MISSION HOLD_AFTER_TAKEOFF TRANSITION
MISSION HOLD_AFTER_TAKEOFF EKF_Z_RESET counter=6 dz=-0.589111 magnitude=0.589111
MISSION HOLD_AFTER_TAKEOFF ABORT material EKF Z reset 0.589 m exceeded 0.20 m
MISSION REQUEST_LAND_ABORT TRANSITION material EKF Z reset 0.589 m exceeded 0.20 m
MISSION REQUEST_LAND_ABORT COMMAND_BEGIN command=21
MISSION REQUEST_LAND_ABORT COMMAND_SEND command=21 attempt=1
MISSION REQUEST_LAND_ABORT NAV_STATE 18
MISSION REQUEST_LAND_ABORT LAND_MODE_CONFIRMED nav_state=18 ack=None
MISSION REQUEST_LAND_ABORT LAND_FEEDBACK_FALLBACK VehicleLandDetected is not bridged; require AUTO_DISARM_LAND reason
MISSION WAIT_AUTO_DISARM_FALLBACK TRANSITION
MISSION WAIT_AUTO_DISARM_FALLBACK OFFBOARD_CONTROL_DIAGNOSTIC enabled=0
MISSION WAIT_AUTO_DISARM_FALLBACK EKF_HEADING_RESET counter=3 delta_rad=0.101484
MISSION WAIT_AUTO_DISARM_FALLBACK HEADING_GOOD_DIAGNOSTIC value=1
MISSION WAIT_AUTO_DISARM_FALLBACK HEADING_GOOD_DIAGNOSTIC value=0
MISSION WAIT_AUTO_DISARM_FALLBACK ARMING_STATE 1
MISSION FAILED TRANSITION PX4 AUTO_DISARM_LAND confirmed
MISSION FAILED HEARTBEAT_SUMMARY publishes=197 max_gap_ms=156.709 over_150ms=1 over_250ms=0 over_500ms=0
python3 failed with exit status 12.
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ V6_EXIT=$?
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ echo "V6_EXIT=$V6_EXIT"
V6_EXIT=12
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ cd /media/p450/P450_DATA/src/p450-jetson-handoff
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ source /opt/ros/foxy/setup.bash
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ source /home/p450/p450_ros2_ws/install/setup.bash
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ export ROS_DOMAIN_ID=0 ROS_LOCALHOST_ONLY=0
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ 
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ TEST_ID=P450_20260826_OUTDOOR_V6_FLIGHT_1M_5M_D
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ systemd-inhibit --what=sleep --mode=block \
>   --who=P450-V6-Flight \
>   --why='V6 single-command outdoor flight' \
>   python3 scripts/p450_delivery_poc_mission.py \
>     --v6-flight \
>     --test-id "$TEST_ID" \
>     --allow-armed \
>     --operator-confirmation V6_PROPS_INSTALLED_AREA_CLEAR_KILL_READY \
>     --takeoff-height 0.5 \
>     --forward-distance 5
MISSION_LOG_DIR=/media/p450/P450_DATA/builds/NX-user-storage/rosbags/P450_20260826_OUTDOOR_V6_FLIGHT_1M_5M_D
MISSION PRECHECK START artifact=V6 mode=v6-flight test_id=P450_20260826_OUTDOOR_V6_FLIGHT_1M_5M_D
MISSION PRECHECK HEADING_GOOD_DIAGNOSTIC value=0
MISSION PRECHECK ARMING_STATE 1
MISSION PRECHECK NAV_STATE 15
MISSION PRECHECK GCS_CONNECTION_DIAGNOSTIC raw_status_lost=0
MISSION PRECHECK OFFBOARD_CONTROL_DIAGNOSTIC enabled=0
MISSION PRECHECK ROUTE start=(-87.25861358642578, 5.1844987869262695, 7.174842834472656, 0.9194157123565674) takeoff=(-87.25861358642578, 5.1844987869262695, 6.674842834472656) goal=(-84.22718901941775, 9.160736342020305, 6.674842834472656) reset_counters={'xy': 4, 'z': 12, 'vxy': 4, 'vz': 2, 'heading': 3}
MISSION PRECHECK PREFLIGHT_HEADING_PENDING PX4 final heading alignment is expected after liftoff when using magnetometer fusion
MISSION PRECHECK PREFLIGHT_PASS offboard_subscriptions=1 setpoint_subscriptions=1 command_subscriptions=1
MISSION STREAM_PREROLL TRANSITION
MISSION REQUEST_OFFBOARD TRANSITION
MISSION REQUEST_OFFBOARD COMMAND_BEGIN command=176
MISSION REQUEST_OFFBOARD COMMAND_SEND command=176 attempt=1
MISSION REQUEST_OFFBOARD NAV_STATE 14
MISSION REQUEST_OFFBOARD OFFBOARD_CONTROL_DIAGNOSTIC enabled=1
MISSION REQUEST_OFFBOARD EKF_SETTLE_WAIT require reset counters stable for 5.0s before Arm
MISSION WAIT_EKF_SETTLE TRANSITION
MISSION WAIT_EKF_SETTLE EKF_SETTLE_RESET counters=(4, 12, 4, 2, 3); restart 5.0s window
MISSION WAIT_EKF_SETTLE EKF_SETTLE_CONFIRMED stable_for=5.0s counters=(4, 12, 4, 2, 3)
MISSION REQUEST_ARM TRANSITION
MISSION REQUEST_ARM COMMAND_BEGIN command=400
MISSION REQUEST_ARM COMMAND_SEND command=400 attempt=1
MISSION REQUEST_ARM ARMING_STATE 2
MISSION TAKEOFF TRANSITION
MISSION HOLD_AFTER_TAKEOFF TRANSITION
MISSION HOLD_AFTER_TAKEOFF ROUTE_REFRESH origin=(-87.21243286132812,5.174169063568115,6.670780658721924) heading=0.8933029174804688 goal=(-84.07822289045806, 9.06990106904522, 6.674842834472656)
MISSION MOVE_FORWARD TRANSITION
MISSION REQUEST_LAND TRANSITION
MISSION REQUEST_LAND COMMAND_BEGIN command=21
MISSION REQUEST_LAND COMMAND_SEND command=21 attempt=1
MISSION REQUEST_LAND OFFBOARD_CONTROL_DIAGNOSTIC enabled=0
MISSION REQUEST_LAND NAV_STATE 18
MISSION REQUEST_LAND LAND_MODE_CONFIRMED nav_state=18 ack=None
MISSION REQUEST_LAND LAND_FEEDBACK_FALLBACK VehicleLandDetected is not bridged; require AUTO_DISARM_LAND reason
MISSION WAIT_AUTO_DISARM_FALLBACK TRANSITION
MISSION WAIT_AUTO_DISARM_FALLBACK ARMING_STATE 1
MISSION WAIT_AUTO_DISARM_FALLBACK NAV_STATE 14
MISSION COMPLETE TRANSITION PX4 AUTO_DISARM_LAND confirmed
MISSION COMPLETE HEARTBEAT_SUMMARY publishes=339 max_gap_ms=152.969 over_150ms=1 over_250ms=0 over_500ms=0
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ V6_EXIT=$?
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ echo "V6_EXIT=$V6_EXIT"
V6_EXIT=0
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ cd /media/p450/P450_DATA/src/p450-jetson-handoff
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ source /opt/ros/foxy/setup.bash
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ source /home/p450/p450_ros2_ws/install/setup.bash
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ export ROS_DOMAIN_ID=0 ROS_LOCALHOST_ONLY=0
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ 
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ TEST_ID=P450_20260826_OUTDOOR_V6_FLIGHT_1M_5M_E
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ systemd-inhibit --what=sleep --mode=block \
>   --who=P450-V6-Flight \
>   --why='V6 single-command outdoor flight' \
>   python3 scripts/p450_delivery_poc_mission.py \
>     --v6-flight \
>     --test-id "$TEST_ID" \
>     --allow-armed \
>     --operator-confirmation V6_PROPS_INSTALLED_AREA_CLEAR_KILL_READY \
>     --takeoff-height 0.5 \
>     --forward-distance 5
MISSION_LOG_DIR=/media/p450/P450_DATA/builds/NX-user-storage/rosbags/P450_20260826_OUTDOOR_V6_FLIGHT_1M_5M_E
MISSION PRECHECK START artifact=V6 mode=v6-flight test_id=P450_20260826_OUTDOOR_V6_FLIGHT_1M_5M_E
MISSION PRECHECK HEADING_GOOD_DIAGNOSTIC value=0
MISSION PRECHECK OFFBOARD_CONTROL_DIAGNOSTIC enabled=0
MISSION PRECHECK ARMING_STATE 1
MISSION PRECHECK NAV_STATE 15
MISSION PRECHECK GCS_CONNECTION_DIAGNOSTIC raw_status_lost=0
MISSION PRECHECK ROUTE start=(-90.40975189208984, 7.329860687255859, 18.912399291992188, 0.8262202143669128) takeoff=(-90.40975189208984, 7.329860687255859, 18.412399291992188) goal=(-87.02145111744149, 11.006736788039962, 18.412399291992188) reset_counters={'xy': 4, 'z': 14, 'vxy': 4, 'vz': 2, 'heading': 3}
MISSION PRECHECK PREFLIGHT_HEADING_PENDING PX4 final heading alignment is expected after liftoff when using magnetometer fusion
MISSION PRECHECK PREFLIGHT_PASS offboard_subscriptions=1 setpoint_subscriptions=1 command_subscriptions=1
MISSION STREAM_PREROLL TRANSITION
MISSION REQUEST_OFFBOARD TRANSITION
MISSION REQUEST_OFFBOARD COMMAND_BEGIN command=176
MISSION REQUEST_OFFBOARD COMMAND_SEND command=176 attempt=1
MISSION REQUEST_OFFBOARD NAV_STATE 14
MISSION REQUEST_OFFBOARD OFFBOARD_CONTROL_DIAGNOSTIC enabled=1
MISSION REQUEST_OFFBOARD EKF_SETTLE_WAIT require reset counters stable for 5.0s before Arm
MISSION WAIT_EKF_SETTLE TRANSITION
MISSION WAIT_EKF_SETTLE EKF_SETTLE_RESET counters=(4, 14, 4, 2, 3); restart 5.0s window
MISSION WAIT_EKF_SETTLE EKF_SETTLE_CONFIRMED stable_for=5.0s counters=(4, 14, 4, 2, 3)
MISSION REQUEST_ARM TRANSITION
MISSION REQUEST_ARM COMMAND_BEGIN command=400
MISSION REQUEST_ARM COMMAND_SEND command=400 attempt=1
MISSION REQUEST_ARM COMMAND_SEND command=400 attempt=2
MISSION REQUEST_ARM ARMING_STATE 2
MISSION TAKEOFF TRANSITION
MISSION TAKEOFF ABORT takeoff timeout
MISSION REQUEST_LAND_ABORT TRANSITION takeoff timeout
MISSION REQUEST_LAND_ABORT COMMAND_BEGIN command=21
MISSION REQUEST_LAND_ABORT COMMAND_SEND command=21 attempt=1
MISSION REQUEST_LAND_ABORT NAV_STATE 18
MISSION REQUEST_LAND_ABORT LAND_MODE_CONFIRMED nav_state=18 ack=None
MISSION REQUEST_LAND_ABORT LAND_FEEDBACK_FALLBACK VehicleLandDetected is not bridged; require AUTO_DISARM_LAND reason
MISSION WAIT_AUTO_DISARM_FALLBACK TRANSITION
MISSION WAIT_AUTO_DISARM_FALLBACK OFFBOARD_CONTROL_DIAGNOSTIC enabled=0
MISSION WAIT_AUTO_DISARM_FALLBACK ARMING_STATE 1
MISSION FAILED TRANSITION PX4 AUTO_DISARM_LAND confirmed
MISSION FAILED HEARTBEAT_SUMMARY publishes=228 max_gap_ms=155.566 over_150ms=2 over_250ms=0 over_500ms=0
python3 failed with exit status 12.
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ V6_EXIT=$?
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ echo "V6_EXIT=$V6_EXIT"
V6_EXIT=12
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ ^C
p450@P450-NX:/media/p450/P450_DATA/src/p450-jetson-handoff$ 

