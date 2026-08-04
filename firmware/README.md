# P450 Pixhawk 6C 測試韌體

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
