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

TEST_ID=P450_20260826_OUTDOOR_V6_FLIGHT_1M_5M_A
systemd-inhibit --what=sleep --mode=block \
  --who=P450-V6-Flight \
  --why='V6 single-command outdoor flight' \
  python3 scripts/p450_delivery_poc_mission.py \
    --v6-flight \
    --test-id "$TEST_ID" \
    --allow-armed \
    --operator-confirmation V6_PROPS_INSTALLED_AREA_CLEAR_KILL_READY \
    --takeoff-height 1 \
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
