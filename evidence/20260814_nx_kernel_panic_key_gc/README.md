# 2026-08-14 NX kernel panic after Agent 50 ms A/B

## 結論

NX 的「卡死」不是 eMMC 空間不足、OOM，也不是 MicroXRCEAgent process crash。pstore 證明
Jetson Linux `5.10.216-tegra` 在 `key_garbage_collector` workqueue 執行 `key_put()` 時發生
kernel data abort，最後 `Kernel panic - not syncing: Oops: Fatal exception`。操作者之後按機體
RST 才恢復。

panic 發生於 heartbeat 正式測試與 PX4 counter 擷取完成之後，且在原 200 ms Agent 已回復
之後。因此它不會改寫已落盤的 6001 筆 CSV 或 QGC 擷取值，但它本身是新的獨立飛行阻塞條件。

## 證據

- kernel：`5.10.216-tegra-35.6.0-20240828020325`；
- fault VA：`0x0000000200000000`；
- worker：`kworker/2:4`；
- workqueue：`events key_garbage_collector`；
- PC/LR：`key_put+0x30/0xb0`、`key_put+0x1c/0xb0`；
- call chain：`key_put → keyring_free_object → assoc_array_destroy → keyring_destroy →
  key_gc_unused_keys → key_garbage_collector`；
- panic 時間：kernel monotonic 2031.563 秒，推算約 2026-08-14 11:10:13 CST；
- 完整選錄見 [`PSTORE_EXCERPT.txt`](PSTORE_EXCERPT.txt)。

重開後：

- CSV 仍為 6002 行，SHA-256
  `48f395f51f12e08cf439547d61dcbb11b06cd5c84407fe579ebdbdddc1c8841a`；
- eMMC 72%，可用 3.7 GB；RAM available 約 5.0 GiB，swap 0；
- eMMC 與 P450_DATA 均為 ext4 `rw`；
- 原 `/usr/local/bin/MicroXRCEAgent` 200 ms 服務自動恢復；
- UART 只有該 Agent 占用；
- `/fmu/in/offboard_control_mode` 為 0 publisher／1 Reliable subscription。

## 原因界線

公開 Linux 資料已有 `key_put()`／key garbage collector use-after-free 修正，公開 crash
討論也出現高度相似 call trace。但 CVE-2025-21893 的官方 upstream 受影響範圍從 Linux
6.10 開始，本機是 NVIDIA vendor `5.10.216-tegra`。因此目前只能判斷「症狀高度相似」，
不能直接宣稱本機就是該 CVE，也不能未經 NVIDIA 5.10 source 對照便套用 upstream patch。

kernel taint 包含 `OE`，當時載入外部 `88x2bu` USB Wi-Fi module。這表示 vendor kernel
之外還有 out-of-tree code，但 panic stack 沒有進入該 driver，不能只憑 taint 把原因歸給
Wi-Fi。

## 下一步

1. 暫停裝槳、飛行及新的長時間 Offboard 測試。
2. 保留 pstore；若再次發生，先擷取新 pstore 並比對 fault address、PC 與 call trace。
3. 取得 NVIDIA L4T R35.6.0 完整 kernel source，對照 `security/keys/key.c`、`gc.c`、
   `keyring.c` 與 NVIDIA 後續 BSP 修正。
4. 查明修正版 kernel 前，不以重跑 ROS 測試掩蓋核心 panic。
5. 若要隔離 out-of-tree module，再規劃「停用 88x2bu／改用有線網路」的長時間 soak；
   此動作會影響 NX 網路，需另開維護窗口。

參考：

- [Linux Kernel Key Retention Service](https://www.kernel.org/doc/html/latest/security/keys/core.html)
- [CVE-2025-21893 / upstream `key_put()` UAF 描述與 patch links](https://nvd.nist.gov/vuln/detail/CVE-2025-21893)
- [NVIDIA forum：Xavier NX `key_garbage_collector` hung-task 案例](https://forums.developer.nvidia.com/t/xavier-nx-reboot-test-hung-up-log-task-systemd-1-blocked-for-more-than-120-seconds/274651)
