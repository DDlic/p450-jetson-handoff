# P450 Pixhawk 6C 測試韌體

## PX4 v1.15.4 官方原始碼乾淨編譯版

檔案：

```text
p450-pixhawk6c-v1.15.4-stock-99c40407ff.px4
```

建置與封裝驗證：

- 目標板：Pixhawk 6C／`PX4FMUv6C`
- PX4 target：`px4_fmu-v6c_default`
- 官方 tag：`v1.15.4`
- source commit：`99c40407ffd7ac184e2d7b4b293f36f10fe561ef`
- 自製 patch：無
- recursive submodules：全部位於 v1.15.4 鎖定 commit，無偏移
- 編譯器：GNU Arm Embedded Toolchain 9-2020-q2-update／GCC 9.3.1
- `.px4` 檔案大小：1,849,448 bytes
- 韌體 image size：1,961,652 bytes
- FLASH：1,961,652／1,966,080 bytes（99.77%）
- firmware `board_id`：56
- firmware `description`：`Firmware for the PX4FMUv6C board`
- firmware `git_identity`：`v1.15.4`
- SHA-256：`21af0b94edd5de84dde5360874d8e1f66a52e3be07dfbafaaffc03baa580c29a`

2026-08-04 在 NX 的 `P450_DATA` SD 資料碟上由官方 v1.15.4 source 完整執行：

```bash
make px4_fmu-v6c_default
```

建置 `1233/1233` 成功。此版本用來取代持續回補 v1.14.3 XRCE client 的路線；
它不包含 repository 內兩個 v1.14.3 XRCE patch。PX4 v1.15.4 對應的 Jetson ROS 2
message definitions 必須改用 `px4_msgs release/1.15`，不可繼續用 `release/1.14`
進行 ROS→PX4 控制測試。

此檔目前只有完成 source／submodule／板型／容量／封裝與 checksum 驗證，尚未刷入
本機飛控，也尚未通過參數遷移、感測器、RC、failsafe、XRCE 或 Offboard 地面測試。
使用 QGroundControl 刷入前仍須保持拆槳、穩定供電並保存 v1.14.3 完整參數備份；
刷入後不得直接套用控制或起飛，須先核對 airframe、校正、RC、安全開關、failsafe、
`UXRCE_DDS_CFG`、`SER_TEL2_BAUD` 與 `MAV_1_CONFIG`。

## XRCE 接收排空＋session ping 回補候選版

檔案：

```text
p450-pixhawk6c-v1.14.3-xrce-rx-drain-ping-fix-49049d8555.px4
```

建置資訊：

- 目標板：Pixhawk 6C／`PX4FMUv6C`
- PX4 target：`px4_fmu-v6c_default`
- PX4 基底：v1.14.3
- source commit：`49049d855552c39879234bf4f19229baf0939a48`
- 檔案大小：1,808,290 bytes
- SHA-256：`d371a5e7ccde6da7832c9dd0dcbce8a078d459b6239d97a79924b0b1aa0a8bdd`

此候選版保留已驗證的 session ping 回補，另回補 PX4 官方提交
[`d12a7dd11da5`](https://github.com/PX4/PX4-Autopilot/commit/d12a7dd11da521ebbdd6ba07be1987b459d39ace)
的 XRCE 接收排空修正。官方提交說明指出，每個 client 主迴圈只處理一次 session
會造成接收資料顯著延遲，甚至使已註冊的飛行模式 timeout；修正後每輪最多處理
10 次，直到沒有新 payload。實際 patch 位於
`../patches/px4-v1.14.3-uxrce-rx-drain-backport.patch`。

2026-08-04 的刷入前診斷已確認 `COM_OF_LOSS_T=1.0 s`，不是 timeout 設得過短；
NX 以 100 Hz 發送時，PX4 uORB 內最新 `offboard_control_mode` 曾落後約 0.724 秒，
與上述官方修補的問題描述一致。此韌體已完整編譯並通過 SHA-256 檢查，但尚待刷入後
以未解鎖、零推力 heartbeat 驗證，因此目前標記為候選版，不可直接裝槳飛行。

## XRCE session ping 回補版

檔案：

```text
p450-pixhawk6c-v1.14.3-xrce-ping-fix-f9bc66c6f3.px4
```

建置資訊：

- 目標板：Pixhawk 6C／`PX4FMUv6C`
- PX4 target：`px4_fmu-v6c_default`
- PX4 基底：v1.14.3
- source commit：`f9bc66c6f30d8ddcceaeba2545dc9f6d0e71faf1`
- 檔案大小：1,808,166 bytes
- SHA-256：`cb14d73274014385e809645dd3525e1ce0e33cf5d648c7d23324c41b822bf0bd`

修補來源為 PX4 官方提交
[`a1cce7e961df`](https://github.com/PX4/PX4-Autopilot/commit/a1cce7e961df) 中與
XRCE session ping 直接相關的最小回補。實際 patch 位於
`../patches/px4-v1.14.3-uxrce-session-ping-backport.patch`。

## 安全狀態

此韌體已通過完整編譯、板型中繼資料與 SHA-256 驗證。2026-08-03 機主完成
參數備份、刷入與參數恢復；10 分鐘 XRCE 純訂閱測試最大 gap 56.263 ms、
0 次超過 100 ms，120 秒詳細 Agent 測試沒有 session close/recreate。

此結果代表目前地面條件下的 XRCE 通訊穩定性通過，不代表 GPS、preflight、
failsafe、Offboard 或飛行安全已通過。

若日後重刷，必須：

1. 保持拆槳、機體固定與穩定供電。
2. 使用 QGroundControl 匯出完整參數備份。
3. 再次確認飛控為 Pixhawk 6C。
4. 刷入後核對 airframe、校正、RC、安全與 failsafe 參數。
5. 先做至少 10 分鐘純訂閱地面測試，不可直接解鎖或進入 Offboard。

完整測試結果見 `../P450_POSTFLASH_XRCE_TEST_2026-08-03.md`。
