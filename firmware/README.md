# P450 Pixhawk 6C 測試韌體

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

此韌體已通過完整編譯、板型中繼資料與 SHA-256 驗證，但尚未刷入實機，也尚未
完成 10 分鐘 XRCE 穩定性測試。

刷入前必須：

1. 保持拆槳、機體固定與穩定供電。
2. 使用 QGroundControl 匯出完整參數備份。
3. 再次確認飛控為 Pixhawk 6C。
4. 刷入後核對 airframe、校正、RC、安全與 failsafe 參數。
5. 先做至少 10 分鐘純訂閱地面測試，不可直接解鎖或進入 Offboard。

完整測試程序見 `../P450_PROGRESS_2026-07-24_NEXT.md`。
