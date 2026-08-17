# 2026-08-17 NX repeated `key_garbage_collector` kernel panic

## 結論

操作者執行 `sudo systemctl stop p450-micro-xrce-agent.service` 後，NX 立即失去回應並
重新開機。ramoops/pstore 證明這不是 MicroXRCEAgent userspace crash，也不是正常重啟：
Jetson Linux `5.10.216-tegra` 的 `events` workqueue 在
`key_garbage_collector -> key_put()` 對無效位址 `0x0000000200000000` 取值，最後發生
`Kernel panic - not syncing: Oops: Fatal exception`。

這與 2026-08-14 保存的事件在 fault address、PC/LR 與完整 call chain 上相同，已達到
「相同 trace 再次出現才提升為 kernel root-cause 工作」的門檻。停止 Agent 與 panic
時間緊鄰，但 pstore 無法證明 `systemctl stop` 是根因；Agent 本身沒有能力直接在 kernel
位址 `key_put()` 製造這條 call trace。

在釐清或完成有效隔離前：

- 不再反覆 stop/start Agent；
- 暫停 Agent trace A/B 與有槳飛行；
- 原 systemd Agent 在重開後維持 `active`，先保留現況；
- 仍可做不需切換 Agent、且不發布控制命令的唯讀工作。

## 本次原始證據

- kernel monotonic time：`3167.085194 s`；
- fault VA／`x19`：`0000000200000000`；
- CPU／task：CPU 1、`kworker/1:2`、PID 5617；
- workqueue：`events key_garbage_collector`；
- PC/LR：`key_put+0x30/0xb0`、`key_put+0x1c/0xb0`；
- kernel：`5.10.216-tegra #1`，L4T package `35.6.0-20240828020325`；
- taint：`G OE`，當時載入 out-of-tree `88x2bu`；
- 沒有在 fatal trace 前找到 OOM、EXT4/I/O error、過熱或 soft/hard lockup。

Call chain：

```text
key_put
keyring_free_object
assoc_array_destroy_subtree.part.0
assoc_array_destroy
keyring_destroy
key_gc_unused_keys.constprop.0
key_garbage_collector
process_one_work
worker_thread
kthread
ret_from_fork
```

完整原始 ramoops 已保留，未刪除或改寫：

| 檔案 | bytes | SHA-256 |
| --- | ---: | --- |
| `console-ramoops-0` | 3,999 | `b28cf54f2105680b0fea4e2e22cc9a6cb107587418e70b7dae9bf295ea01c626` |
| `dmesg-ramoops-0` | 104,314 | `45f5ad1d9115b434623dfb8ccf6eaf4795dd73549214b598fc5f61602ee5f318` |
| `dmesg-ramoops-1` | 104,641 | `d95168992eb116713ecdfe92220e1bffbe37444e730778978089fbed49bfcf29` |

## 與 2026-08-14 事件比對

| 特徵 | 2026-08-14 | 2026-08-17 |
| --- | --- | --- |
| fault address | `0x0000000200000000` | `0x0000000200000000` |
| PC | `key_put+0x30/0xb0` | `key_put+0x30/0xb0` |
| workqueue | `key_garbage_collector` | `key_garbage_collector` |
| call chain | keyring destroy/GC chain | 同一條 chain |
| out-of-tree module | `88x2bu(OE)` | `88x2bu(OE)` |

因此兩次應視為同一 crash family，而不是兩個無關的隨機重啟。

## 已排除與尚未證明

1. `cgroup.memory=nokmem` 只隔離先前 `mem_cgroup_from_obj/list_lru_del` panic；本次是另一條
   keyring GC 路徑，boot 參數無法涵蓋它。
2. 事後一度看到 eMMC 94%，是本次 panic 之後為比對官方 kernel source 建立的兩個
   `/tmp` clone 所造成；clone 清除後立即回到 74%。所以 94% 滿碟不可能是稍早 panic
   的原因。後續清理完成後為 64%、可用 4.8 GB。
3. Linux CVE-2025-21893 雖然名稱也是 `key_put()` UAF，但官方記錄指出它由 Linux 6.10
   才引入；本機為 vendor 5.10，不能把本事件直接命名為該 CVE。
4. NVIDIA 官方 `linux-5.10` 的 `l4t-35.6.0-5.10` (`9665f098`) 與
   `l4t-r35.6.5-5.10` (`1b0a8b8c`) 在 `security/keys` 和 `include/linux/key.h` 沒有
   差異。升到 35.6.5 可能包含其他 driver/security 修正，但目前沒有證據顯示它直接修了
   這條 keyring call chain。
5. 兩次 panic 都載入 `88x2bu(OE)`，而 pstore 在 crash 前也有該 driver 的 scan warnings。
   這使外部 Wi-Fi driver 成為需要做軟體 A/B 的候選，但 stack 沒有進入該 module，不能
   只憑 taint 判定它是根因。

## 下一步 gate

1. 在不影響目前網路工作的維護窗口，以「不載入 `88x2bu`」做 software-only soak A/B；
   不採用 UART 掛阻抗或其他物理改線方案。
2. 若仍會重現，再取得可對應 vendor build 的完整 kernel symbols/source，檢查 keyring
   object 是自身 race 還是被其他 module 寫壞。
3. NVIDIA BSP 升級只能作為整體穩定性 A/B，不能宣稱是已知直接修正；升級前需先備份
   boot/kernel/DTB 與目前可開機組態。
4. 未通過長時間 NX stability soak 前，不恢復有槳 Offboard 飛行 gate。

參考：

- 2026-08-14 同類事件：[`../20260814_nx_kernel_panic_key_gc/README.md`](../20260814_nx_kernel_panic_key_gc/README.md)
- [NVIDIA Jetson Linux 35.6.5](https://developer.nvidia.com/embedded/jetson-linux-r3565)
- [Linux CVE announcement：CVE-2025-21893](https://lists.openwall.net/linux-cve-announce/2025/03/31/1)

