<div align="center">

# AMOV P450 × Jetson Xavier NX

**一台 P450 無人機的 Jetson／PX4 整合與除錯紀錄**

<p>
  <img src="https://img.shields.io/badge/status-engineering_handoff-2563EB?style=flat-square" alt="Engineering handoff">
  <img src="https://img.shields.io/badge/NVIDIA_Jetson-Xavier_NX-76B900?style=flat-square&logo=nvidia&logoColor=white" alt="NVIDIA Jetson Xavier NX">
  <img src="https://img.shields.io/badge/ROS_2-Foxy-22314E?style=flat-square&logo=ros&logoColor=white" alt="ROS 2 Foxy">
  <img src="https://img.shields.io/badge/autopilot-PX4-111111?style=flat-square" alt="PX4">
</p>

[開始閱讀](docs/INDEX.md) · [系統架構](docs/architecture/REPOSITORY_MAP.md) · [目前分支](docs/current/BRANCH_INVENTORY_20260831.md) · [協作 Issue](https://github.com/DDlic/p450-jetson-handoff/issues/1)

</div>

這個 repository 記錄一台 AMOV P450 的整合與除錯過程。機上電腦是 Jetson Xavier NX，
飛控是 Pixhawk 6C，兩邊透過 ROS 2、PX4 與 Micro XRCE-DDS 通訊。這裡收的是交接文件、
診斷腳本、韌體和測試紀錄，不能當成一般 ROS package 直接編譯。

> [!CAUTION]
> 目前還不能把這套系統當成已通過飛行驗證。transport freshness 與 NX kernel panic
> 兩個關卡都還沒過。閱讀或修改這些檔案，不代表可以裝槳、解鎖、刷寫、改參數或進行
> 實機飛行。

## 專案一覽

| 項目 | 內容 |
| --- | --- |
| 飛行平台 | AMOV P450 |
| 機上電腦 | NVIDIA Jetson Xavier NX，JetPack 5.1.4／L4T R35.6.0 |
| 飛控 | Pixhawk 6C／PX4 |
| 通訊軟體 | ROS 2 Foxy、Micro XRCE-DDS Agent 2.4.2 |
| 主要鏈路 | Jetson UART ↔ Pixhawk TELEM2，115200 baud |
| 收錄內容 | 交接文件、診斷腳本、韌體來源、測試報告與原始紀錄 |

## 目前狀態

`main` 目前記錄到的結果如下。這些數字只適用於原本的測試條件。

| 關卡 | 狀態 | 已知結果 |
| --- | :---: | --- |
| Reliable 最終送達 | **已觀測** | 一次未解鎖的 600 秒測試中，送出與收到的筆數都是 `6001` |
| 250 ms freshness | **未通過** | 同一測試的最大接收間隔為 `601.548 ms` |
| NX kernel 穩定性 | **未通過** | 已保存兩次同類型的 `key_garbage_collector → key_put()` panic |
| 一般實機飛行 | **尚未確認** | 現有紀錄還不能證明解鎖後、室外環境的最差延遲能通過安全檢查 |

原始條件和判讀在以下文件：

- [Reliable 10 分鐘測試結果](evidence/20260813_first_principles_offboard_transport/TEN_MINUTE_RELIABLE_RESULT.md)
- [NX kernel panic evidence](evidence/20260817_nx_kernel_panic_key_gc_repeat/README.md)
- [Delivery PoC runbook](docs/runbooks/P450_DELIVERY_POC_OFFBOARD_RUNBOOK_2026-08-17.md)
- [Reliable latency remediation runbook](docs/runbooks/P450_RELIABLE_LATENCY_REMEDIATION_RUNBOOK_2026-08-17.md)

> [!NOTE]
> `6001/6001` 只能說明最後都有收到，不能證明每一筆都準時。`601.548 ms` 雖然低於
> 當時設定的 `COM_OF_LOSS_T=1.0 s`，但仍超過本專案採用的 250 ms 門檻。

## 從哪裡開始

| 如果你是… | 建議入口 |
| --- | --- |
| 第一次閱讀 | [文件索引](docs/INDEX.md) → [系統架構](docs/architecture/REPOSITORY_MAP.md) |
| 接手目前工作 | [文件清單](docs/current/DOC_INVENTORY.md) → [分支清單](docs/current/BRANCH_INVENTORY_20260831.md) |
| QGC／Pixhawk 操作者 | [QGC 交接文件](docs/current/QGC_LAPTOP_CODEX_HANDOFF_20260814.md) → 對應的操作手冊 |
| 檢查測試結論 | 先看 `evidence/<TEST_ID>/` 的原始資料，再看同條件的摘要或報告 |
| 開發或審查程式 | `scripts/`、`patches/`、`firmware/`，並先閱讀各區域說明 |

## 目錄結構

```text
.
├── docs/       導覽、目前交接、runbooks、reports 與歷史文件
├── evidence/   依日期／TEST_ID 保存的 summary 與原始觀測
├── scripts/    ROS 2 診斷、monitor 與受保護的測試工具
├── firmware/   PX4 artifacts、來源說明與 SHA-256 manifest
├── patches/    可審查的 PX4／XRCE 修改
├── config/     NX runtime 與 SD-first 儲存設定
└── systemd/    Micro XRCE-DDS Agent service 定義
```

缺少完整 TEST_ID 或測試條件的資料放在 [`docs/raw/`](docs/raw/)，不會拿來支持測試結論。
大型編譯檔、log、cache 與暫存資料請放在 NX 的 `/media/p450/P450_DATA`，不要塞回
14 GB eMMC。

## 開發分支

| 分支 | 用途 |
| --- | --- |
| [`main`](https://github.com/DDlic/p450-jetson-handoff/tree/main) | 目前公開的交接首頁 |
| [`work/outdoor-v6-nx-evidence`](https://github.com/DDlic/p450-jetson-handoff/tree/work/outdoor-v6-nx-evidence) | 尚未合併的 outdoor V6／NX 測試資料 |
| [`work/ubuntu22-humble-visual-sitl`](https://github.com/DDlic/p450-jetson-handoff/tree/work/ubuntu22-humble-visual-sitl) | 尚未合併的 Ubuntu 22.04／Humble visual SITL 工作 |

分支上的 commit 就算比較新，也不能直接當成 `main` 的最新結論。保留方式和合併規則寫在
[分支清單](docs/current/BRANCH_INVENTORY_20260831.md)。

## 檢查方式

```bash
python3 -m compileall -q scripts .agents/skills/p450-repo-curator/scripts
python3 .agents/skills/p450-repo-curator/scripts/audit_repo.py --base-ref origin/main
(cd firmware && sha256sum -c SHA256SUMS)
git diff --check
git diff --name-status --find-renames origin/main
```

這些命令只檢查目錄、連結、Python 語法和韌體檔案是否一致。它們不會判斷韌體能不能安全
刷入，也不能拿來證明實機可以飛行。
