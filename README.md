<div align="center">

# AMOV P450 × Jetson Xavier NX

**ROS 2／PX4 整合交接、診斷工具、韌體來源與實驗證據庫**

<p>
  <img src="https://img.shields.io/badge/status-engineering_handoff-2563EB?style=flat-square" alt="Engineering handoff">
  <img src="https://img.shields.io/badge/NVIDIA_Jetson-Xavier_NX-76B900?style=flat-square&logo=nvidia&logoColor=white" alt="NVIDIA Jetson Xavier NX">
  <img src="https://img.shields.io/badge/ROS_2-Foxy-22314E?style=flat-square&logo=ros&logoColor=white" alt="ROS 2 Foxy">
  <img src="https://img.shields.io/badge/autopilot-PX4-111111?style=flat-square" alt="PX4">
</p>

[開始閱讀](docs/INDEX.md) · [系統架構](docs/architecture/REPOSITORY_MAP.md) · [目前分支](docs/current/BRANCH_INVENTORY_20260831.md) · [協作 Issue](https://github.com/DDlic/p450-jetson-handoff/issues/1)

</div>

這不是一個可直接編譯的 ROS package，而是 AMOV P450、Jetson Xavier NX 與
Pixhawk 6C 整合過程的可稽核工程交接庫。它把「目前能做什麼」、「哪些關卡仍失敗」
以及「結論來自哪份原始證據」分開保存。

> [!CAUTION]
> 本 repository **尚未證明系統具備一般飛行安全性**。目前仍有 transport freshness
> 與 NX kernel panic 關卡未通過。閱讀或修改 repository 不等於授權裝槳、解鎖、刷寫、
> 改參數或進行實機飛行。

## 專案一覽

| 項目 | 內容 |
| --- | --- |
| 飛行平台 | AMOV P450 |
| Companion computer | NVIDIA Jetson Xavier NX，JetPack 5.1.4／L4T R35.6.0 |
| Flight controller | Pixhawk 6C／PX4 |
| Middleware | ROS 2 Foxy、Micro XRCE-DDS Agent 2.4.2 |
| 主要鏈路 | Jetson UART ↔ Pixhawk TELEM2，115200 baud |
| Repository 角色 | 工程交接、診斷腳本、韌體 provenance、測試報告與原始 evidence |

## 目前狀態

以下是 `main` 目前可由同條件 evidence 支持的最小結論：

| 關卡 | 狀態 | 已知結果 |
| --- | :---: | --- |
| Reliable 最終送達 | **Observed** | 一次 disarmed 600 秒測試為 `6001/6001` 最終送達 |
| 250 ms freshness | **Fail** | 同一測試最大 receipt gap 為 `601.548 ms` |
| NX kernel stability | **Fail** | 已保存兩次同 family `key_garbage_collector → key_put()` panic |
| 一般實機飛行安全 | **Not established** | 尚無證據涵蓋 armed／outdoor worst-case tail 與完整安全關卡 |

詳細條件與限制：

- [Reliable 10 分鐘測試結果](evidence/20260813_first_principles_offboard_transport/TEN_MINUTE_RELIABLE_RESULT.md)
- [NX kernel panic evidence](evidence/20260817_nx_kernel_panic_key_gc_repeat/README.md)
- [Delivery PoC runbook](docs/runbooks/P450_DELIVERY_POC_OFFBOARD_RUNBOOK_2026-08-17.md)
- [Reliable latency remediation runbook](docs/runbooks/P450_RELIABLE_LATENCY_REMEDIATION_RUNBOOK_2026-08-17.md)

> [!NOTE]
> 「零最終遺失」不等於「deadline-safe」。`601.548 ms` 雖低於該次設定的
> `COM_OF_LOSS_T=1.0 s`，仍未通過 repository 的 250 ms engineering gate。

## 從哪裡開始

| 如果你是… | 建議入口 |
| --- | --- |
| 第一次閱讀 | [Repository index](docs/INDEX.md) → [Architecture map](docs/architecture/REPOSITORY_MAP.md) |
| 接手目前工作 | [Document inventory](docs/current/DOC_INVENTORY.md) → [Branch inventory](docs/current/BRANCH_INVENTORY_20260831.md) |
| QGC／Pixhawk 操作者 | [QGC handoff](docs/current/QGC_LAPTOP_CODEX_HANDOFF_20260814.md) → 適用的 runbook |
| 檢查測試結論 | 先看對應 `evidence/<TEST_ID>/`，再看同條件 summary／report |
| 開發或審查程式 | `scripts/`、`patches/`、`firmware/`，並先閱讀各區域說明 |

## Repository 地圖

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

沒有完整 TEST_ID 或測試條件的資料會隔離在 [`docs/raw/`](docs/raw/)，不會被當成
已驗證結論。大型 build、log、cache 與暫存資料應放在 NX 的
`/media/p450/P450_DATA`，不要回寫 14 GB eMMC。

## 開發分支

| 分支 | 用途 |
| --- | --- |
| [`main`](https://github.com/DDlic/p450-jetson-handoff/tree/main) | 經整理的公開交接與權威入口 |
| [`work/outdoor-v6-nx-evidence`](https://github.com/DDlic/p450-jetson-handoff/tree/work/outdoor-v6-nx-evidence) | 尚未整合的 outdoor V6／NX evidence 工作 |
| [`work/ubuntu22-humble-visual-sitl`](https://github.com/DDlic/p450-jetson-handoff/tree/work/ubuntu22-humble-visual-sitl) | 尚未整合的 Ubuntu 22.04／Humble visual SITL 工作 |

較新的 branch commit 不會自動覆蓋 `main` 的權威關係。完整保留與整合政策見
[Branch inventory](docs/current/BRANCH_INVENTORY_20260831.md)。

## Repository 驗證

```bash
python3 -m compileall -q scripts .agents/skills/p450-repo-curator/scripts
python3 .agents/skills/p450-repo-curator/scripts/audit_repo.py --base-ref origin/main
(cd firmware && sha256sum -c SHA256SUMS)
git diff --check
git diff --name-status --find-renames origin/main
```

這些檢查只驗證 repository 結構、連結、Python syntax 與 artifact identity；
**不代表韌體可安全刷入，也不代表實機可以飛行**。
