# ROS 2 Offboard heartbeat 現況、根因分級與正確修法

日期：2026-08-12（Asia/Taipei）

## 一、結論先講

目前不是「ROS 2 完全不能控制飛控」，也不應再用反覆換 PX4 大版本碰運氣。

已經實機證明的控制鏈如下：

```text
NX ROS 2 VehicleCommand
  -> Micro XRCE-DDS Agent
  -> Jetson ttyTHS1 / Pixhawk TELEM2
  -> PX4 uXRCE-DDS client
  -> commander
  -> 外部命令解鎖成功
```

正常 Disarm 命令也到達 PX4，只是當時 land detector 已判定 `Takeoff detected`／
`not landed`，所以 commander 依安全規則拒絕正常上鎖。這與 heartbeat 是兩個不同問題。

真正阻止 Offboard 的問題是：armed 後 PX4 多次記錄 `No offboard signal`，並由
Offboard 退回 Position。PX4 官方要求 ROS 2 的 `OffboardControlMode` 持續高於 2 Hz；
超過 `COM_OF_LOSS_T` 沒收到就必須執行失聯動作。本機 QGC 紀錄完全符合官方
Offboard-loss 行為，不是模式參數名稱搞錯。

目前最高可信度的工程判斷是兩個問題疊加：

1. Xavier NX 內建 `ttyTHS1` 的高速 UART 路徑有明確的 rate-dependent framing／clock／
   signal-integrity 問題。460800 無有效 XRCE frame、230400 偶發、115200 才能穩定
   解碼，且 NVIDIA 官方論壇有高度相似案例。
2. 降到 115200 後，現有 PX4 v1.14.3 bridge 的 PX4→NX serialized／offered payload
   約 10.1 KB/s，已佔
   11.52 KB/s 理論 8N1 線速的 87.5%，還未計 XRCE/HDLC header、CRC 與 byte stuffing。
   所以雖然 115200 修復了 frame 解碼，卻把輸出方向推到幾乎無餘裕。

第二項很可能放大 PX4 XRCE 單一迴圈的延遲，但 UART 是 full duplex，不能僅憑 TX
接近線速就宣稱它必然塞住 RX。下一版必須同時記錄 NX 本地 heartbeat send gap 與
PX4 uORB receipt gap，才可完成最後因果判定。

## 二、2026-08-12 15:50 左右的即時狀態

- Git：`main` 與 `origin/main` 同步，寫檔前 `git pull --ff-only` 回報 up to date。
- Agent：`p450-micro-xrce-agent.service` active，PID 1779。
- Agent 參數：`/dev/ttyTHS1`、115200 baud、verbosity 2。
- 實際 termios：115200、8N1、無 RTS/CTS、raw mode。
- UART 只有 MicroXRCEAgent 一個使用者。
- ROS 控制 publisher：
  - `/fmu/in/offboard_control_mode`：0
  - `/fmu/in/trajectory_setpoint`：0
  - `/fmu/in/vehicle_command`：0
- `/fmu/out/vehicle_status` DDS endpoint 仍存在，但 3 秒唯讀 echo 沒收到新 sample。
  因此現在不能只靠 graph 宣稱飛控資料流 connected；可能是飛控未供電、session
  entity 殘留或資料流停滯。沒有為了改變現況而重啟 Agent，也沒有發布控制資料。
- 網路：`eth0=192.168.10.100/24`，`wlan0=10.138.63.38/24`。
- 儲存：14 GB eMMC 尚餘約 3.7 GB；128 GB SD 卡尚餘約 106 GB。

安全狀態：NX 上沒有任何 Offboard、setpoint 或 command publisher；本次工作沒有解鎖、
切模式或發控制命令。

## 三、哪些事情已證明，哪些還沒證明

| 判斷 | 證據等級 | 說明 |
|---|---:|---|
| ROS 2 `VehicleCommand` 能到 commander | 已證明 | QGC 記錄 `Armed by external command` |
| 正常 Disarm 命令有到 PX4 | 已證明 | QGC 反覆記錄 `Disarming denied, not landed` |
| armed 後 PX4 遺失 Offboard proof-of-life | 已證明 | QGC `No offboard signal`，nav 14/2 反覆切換 |
| 460800 的 NX→PX4 raw bytes 無法組成有效 XRCE payload | 已證明 | PX4 raw RX 增加，但 complete payload=0，listener 無 marker |
| 115200 能正確完成 NX→PX4 XRCE 解碼 | 已證明 | exact marker 進入 PX4 uORB，complete payload 增加 |
| 高速 UART 問題具有 rate dependency | 已證明 | 460800 fail、230400 partial、115200 pass |
| 115200 PX4→NX offered output 幾乎沒有線速餘裕 | 已證明 | serialized payload 約 10.1 KB/s；理論 wire 11.52 KB/s，payload 尚未含 framing |
| Wi-Fi 是主要根因 | 不支持 | 過去已量到 publisher 與 Agent send gap 約 14–21 ms，飛控仍報 lost；UART A/B 更直接 |
| 目前 outdoor run 的 Python heartbeat 本地永遠無 gap | 尚未證明 | process 未停止，但該次沒有保存 monotonic send trace |
| PX4→NX 高負載必然導致 NX→PX4 heartbeat loss | 高度懷疑、未完成因果證明 | full-duplex UART 兩方向線路容量分離，但同一 XRCE task／driver／CPU 資源仍可能互相影響 |
| 單純增加 `COM_OF_LOSS_T` 可修好 | 否 | 只能延後 failsafe，會掩蓋傳輸問題，不修復資料連續性 |
| 單純升級 PX4 1.15.4 可修好 | 否 | 本機 1.15.4 路線已出現秒級 gap；官方較新的改善也不是 1.15.4 全部具備 |

## 四、歷史分層測試如何排除 NX／Wi-Fi 假說

先前完整 trace 曾在 NX 端以約 88 Hz 發送：

```text
ROS publisher：最大 gap 約 13–14 ms
Agent DataReader：最大 gap 約 14–15 ms
Agent serial send：最大 gap 約 18–21 ms
Agent error/warning：0
Agent session teardown/recreate：0
PX4：仍曾回報 offboard_control_signal_lost
```

所以至少在該次重現中，Linux Python 排程、DDS discovery、Agent 收件與 Agent 呼叫
serial send 都不是一秒級 gap 的來源。Wi-Fi／CLI 同時使用可能造成一般系統 jitter，
但現有證據不足以把它列為主要根因；拔除網路天線也不能修復 Jetson UART clock 或
Pixhawk 端 XRCE receive scheduling。

本次 outdoor 腳本是另一個程式版本，仍應重新加入本地 send-gap 計時，避免把歷史測試
當成當次測試的直接證據。

## 五、官方資料對照

### 5.1 PX4 對 Offboard 的正式要求

PX4 官方文件要求外部控制器持續提供 2 Hz 以上的 proof-of-life。ROS 2 使用
`OffboardControlMode` 作為 proof-of-life；中斷超過 `COM_OF_LOSS_T`，PX4 就退出
Offboard 並依 `COM_OBL_RC_ACT` 執行 failsafe。官方範例採 100 ms timer，即 10 Hz。

來源：

- [PX4 Offboard Mode](https://docs.px4.io/main/en/flight_modes/offboard.html)
- [PX4 ROS 2 Offboard Control Example](https://docs.px4.io/main/en/ros2/offboard_control.html)
- [PX4 Parameter Reference: COM_OF_LOSS_T](https://docs.px4.io/main/en/advanced_config/parameter_reference.html#COM_OF_LOSS_T)

因此 QGC 的 `No offboard signal` 是 PX4 正常安全機制被觸發，不應用 force arm、關閉
failsafe 或把 timeout 拉很長來繞過。

### 5.2 PX4 官方已承認 XRCE receive loop 會造成 timeout

PX4 commit `d12a7dd11d` 明確寫出：每圈只執行一次 session receive 會造成顯著資料
延遲，甚至使 registered flight modes timeout；修法是每圈最多 drain 10 次，直到沒有
新 payload。本機 v1.14.3 custom firmware 已回補此修正，所以它是必要修正，但實測證明
它不是本機的充分條件。

來源：[PX4 d12a7dd11d](https://github.com/PX4/PX4-Autopilot/commit/d12a7dd11da521ebbdd6ba07be1987b459d39ace)

### 5.3 PX4 2026 年合併的高負載 stall 改善

PX4 PR #26161 針對高 inbound UDP 負載下的 client stall，合併了降低主迴圈 latency、
transport 有資料時不等待 uORB poll、每圈 drain inbound burst、best-effort output batch
flush，以及 buffer full 後 retry。它的重現是 UDP 800–1200 Hz，不等同本機 UART 10 Hz，
所以不能直接宣稱是同一 bug；但官方修法支持「XRCE 單一迴圈排程與 flush 策略會在負載
下造成 stall／不穩定」這條根因路徑。

來源：

- [PX4 issue #26160](https://github.com/PX4/PX4-Autopilot/issues/26160)
- [PX4 PR #26161](https://github.com/PX4/PX4-Autopilot/pull/26161)

### 5.4 PX4 已加入 topic rate limit

PX4 最新文件允許 publication 在 `dds_topics.yaml` 加 `rate_limit`。PR #27688 又補上
unlimited／drain 語意，目標就是減少 burst topic 的 jitter 與 delay。這個功能於
2026-07-03 合併到較新的 main，不存在於目前 v1.14.3 template；本機 v1.15.4 tag 的
template 也只有共同的 10 ms poll interval，沒有現行 per-topic `rate_limit` 生成邏輯。

來源：

- [PX4 uXRCE-DDS middleware / DDS Topics YAML](https://docs.px4.io/main/en/middleware/uxrce_dds.html#dds-topics-yaml)
- [PX4 PR #27688](https://github.com/PX4/PX4-Autopilot/pull/27688)
- [PX4 d0f7b7d8](https://github.com/PX4/PX4-Autopilot/commit/d0f7b7d8fcb905fe7fad54f2cb2bdfc3204c2fe5)

這是目前最貼近本機 115200 bandwidth 問題的正式上游方向。不能只在 YAML 寫一個
v1.14.3 不認識的欄位；必須回補生成器／template，或直接使用
`uORB::SubscriptionInterval` 實作等價限速。

### 5.5 eProsima serial framing 的成本

eProsima 官方文件說明 serial 是 stream-oriented transport，Micro XRCE-DDS 會加入 HDLC
begin flag、source/destination、length、CRC，並對特殊 octet 做 byte stuffing。也就是
PX4 顯示的 serialized topic payload 並不是 UART 上的全部 bytes。

來源：[eProsima Micro XRCE-DDS Transport and Stream Framing](https://micro-xrce-dds.docs.eprosima.com/en/latest/transport.html#stream-framing-protocol)

### 5.6 NVIDIA Xavier NX 高速 UART 已知相似案例

NVIDIA 官方論壇有 Xavier NX 在 460800 收不到外部資料、但 loopback 可用的案例；NVIDIA
工程師要求檢查實際電平與示波器波形。另一個 `ttyTHS1` 460800 案例在 L4T 更新後從每數
小時一個 CRC error 惡化為每秒多個，論壇回覆指出高於 115200 時 UART clock tolerance
可能失準，並建議以 2 stop bits 作診斷。Pixhawk 目前固定 8N1，不能單邊改 8N2 當正式
修法，但這些資料與本機 rate A/B 方向一致。

來源：

- [NVIDIA Forum: Xavier NX 460800 receive issue](https://forums.developer.nvidia.com/t/xavier-nx-460800/314197)
- [NVIDIA Forum: ttyTHS1 less reliable at 460800 after L4T upgrade](https://forums.developer.nvidia.com/t/serial-port-less-reliable-after-upgrade-to-35-1/232396)

## 六、現有 v1.14.3 bridge 為何特別不利

目前 source commit `0438dbc6fd` 的 `dds_topics.h.em` 對每個更新 topic 都依序：

1. `uORB::Subscription::update()`；
2. serialize；
3. `uxr_prepare_output_stream()`；
4. 立刻 `uxr_flash_output_streams()`；
5. 所有 output 做完後才進 `uxr_run_session_timeout()` drain input。

serial fd 以 `O_NONBLOCK` 開啟，eProsima serial platform 最後使用 `write()`／`read()`。
所以不能簡化成「TX write 一定阻塞 RX」；但每 topic 個別 flush、先 output 後 input、
非阻塞 TX queue 滿時的短寫入／EAGAIN，以及 PX4 同一 task 內的工作量，都是合理的 latency
候選。這也是為什麼下一版應先減少 output，再考慮回補較新的 loop／batch-flush 改善。

目前保留 topic 的 serialized payload 大小：

| Topic | 每筆 payload |
|---|---:|
| `failsafe_flags` | 85 B |
| `position_setpoint_triplet` | 269 B |
| `timesync_status` | 44 B |
| `vehicle_control_mode` | 21 B |
| `vehicle_global_position` | 62 B |
| `vehicle_gps_position` (`sensor_gps`) | 141 B |
| `vehicle_local_position` | 184 B |
| `vehicle_status` | 71 B |

`vehicle_local_position` 實測約 20.65 Hz，光是 serialized payload 就約 3.8 KB/s；再加其餘
topic、XRCE submessage 與 HDLC framing，很容易逼近 115200 的上限。v1.14.3 的
`num_payload_sent` 在 output stream prepare／serialize 後累加，不保證後續非阻塞 serial
write 的每個 byte 都成功上線；因此 10.1 KB/s 應解讀為 offered load，不是 wire capture。

## 七、建議的正確解法順序

### Phase A：先完成因果量測，不刷版

修改地面 probe，使每次 publish 都保存：

- monotonic send timestamp；
- 實際 send interval；
- send gap >150、250、500 ms 的次數；
- publisher DDS match count；
- armed 前、armed 後、failsafe 前後的時間線。

同時由 PX4 console 對 `offboard_control_mode` 取樣／計數，或在 custom client 加一個只計
receipt gap 的診斷 counter。必須能回答：

```text
NX publish gap 正常，但 PX4 uORB gap > COM_OF_LOSS_T ？
```

若答案為是，才完成「問題在 Agent serial send 之後」的本次韌體證據閉環。

### Phase B：製作 v1.14.3 rate-limited minimal firmware

保持已證明可用的 115200 與現有 d12 receive-drain，對 PX4→NX publications 做限速，
把 payload 目標壓到 5.0 KB/s 以下；這約是 115200 理論線速的 43%，尚能保留 framing、
burst 與 task latency 餘裕。

建議第一個 A/B 候選：

| Topic | 建議上限 | 理由 |
|---|---:|---|
| `vehicle_local_position` | 10 Hz | 地面／低速位置控制回授 |
| `vehicle_global_position` | 5 Hz | 導航與記錄 |
| `vehicle_gps_position` | 2–5 Hz | GPS 健康監看，不是 Offboard heartbeat |
| `vehicle_status` | 5 Hz | arm/nav/failsafe 狀態 |
| `vehicle_control_mode` | 5 Hz | 控制旗標 |
| `failsafe_flags` | 5 Hz | 安全監看 |
| `position_setpoint_triplet` | 0–2 Hz 或移除 | ROS Offboard 輸入不依賴此 output |
| `timesync_status` | 0–1 Hz 或移除 | 診斷用途；XRCE session 自行 time sync |

這些數字是本專案的工程 A/B 起點，不是 PX4 官方飛行保證。實作方式優先採
`SubscriptionInterval`／per-topic rate limit；只刪 topic 雖可快速降流量，但會降低診斷
能力。

目前 image 已用 98.41% flash。新 patch 必須 clean build 並檢查 flash；必要時先移除既有
FIONREAD 詳細診斷或非必要 publication 騰出空間，不可刷入 overflow 或身分不明 artifact。

### Phase C：選擇性回補新 client 改善

在 Phase B 已顯著降低 payload 後，才分開 A/B 下列變更，避免一次改太多無法歸因：

1. output batch flush，buffer full retry；
2. transport pending 時優先 drain receive；
3. 更低的 XRCE loop latency；
4. per-topic rate-limit generator。

PR #26161 的 UDP nonblocking socket 部分不適用 serial，不應整包照抄；通用的 loop、
drain 與 batch-flush 部分才值得移植。

### Phase D：硬體 transport A/B

若有器材，最乾淨的驗證仍是繞過 Xavier NX Tegra UART：

- Pixhawk TELEM2 → 3.3 V FTDI → NX USB；或
- Pixhawk USB 直接到 NX；或
- 改用 PX4 Ethernet/UDP。

但目前沒有 FTDI，且目前 FMUv6C default NuttX build 的 `.config` 顯示
`CONFIG_NET is not set`、`CONFIG_STM32H7_ETHMAC is not set`，所以雖然 PX4 source／官方
文件支援 Ethernet transport，這個已刷韌體不能直接把 `UXRCE_DDS_CFG` 改成 Ethernet。
要走 Ethernet 必須先確認 AllSpark 實際線路，再建立啟用 networking 的新 board config，
並面對目前 flash 已 98.41% 的空間限制。

### Phase E：由低風險到高風險驗收

1. Disarmed、無控制 publisher：60 秒 output continuity。
2. Disarmed heartbeat：60 秒，NX local max send gap <150 ms，PX4 receipt gap <250 ms。
3. 停止 heartbeat：確認 `COM_OF_LOSS_T` 與 failsafe 時序正確。
4. 室外 GPS 穩定、無槳、RC Kill 可用：Offboard 切入／切回。
5. 無槳 arm hold：全程不得出現 `No offboard signal` 或 Position fallback。
6. 只有前面全部 PASS，才討論裝槳與受控低高度飛行。

## 八、不要再做的重複工作

- 不再只因一次 graph 有 topic 就判定 connected。
- 不再只看 publisher process 還活著就判定 heartbeat 無 gap。
- 不再用 Reliable QoS 重試；過去已測過且沒有改善，還可能增加壅塞。
- 不用拉長 `COM_OF_LOSS_T` 掩蓋通訊缺口。
- 不用 force arm／停用 failsafe 驗證鏈路。
- 不再在沒有單一變因與 pass criteria 的情況下反覆刷 1.14.3／1.15.4。
- 不把正常 Disarm 被 `not landed` 拒絕與 heartbeat loss 混成同一根因。

## 九、下一個實際產出

下一步應做的不是飛行，而是：

1. 為 probe 加入本地 heartbeat gap CSV；
2. 製作 `v1.14.3 + 115200 + receive-drain + per-topic rate limit` 韌體；
3. 預先計算／實測 output payload，目標 <5 KB/s；
4. disarmed 60 秒雙端 gap A/B；
5. PASS 後才重做一次無槳 armed Offboard hold。

這條路能直接驗證目前最有證據的兩個瓶頸，不需要再大版本輪刷，也不需要先更改飛行
failsafe 安全規則。
