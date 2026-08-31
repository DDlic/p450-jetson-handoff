# P450 文件索引

第一次閱讀先看前四項；準備操作或分析測試時，再進入對應的 runbook 與 evidence。

## 建議閱讀順序

1. [`README.md`](../README.md)：專案用途、目前狀態和安全限制。
2. [`architecture/REPOSITORY_MAP.md`](architecture/REPOSITORY_MAP.md)：系統連接方式、目錄分工和證據鏈。
3. [`current/DOC_INVENTORY.md`](current/DOC_INVENTORY.md)：每份文件的分類與目前權威關係。
4. [`current/BRANCH_INVENTORY_20260831.md`](current/BRANCH_INVENTORY_20260831.md)：分支用途、保留的舊 tip 與合併原則。
5. [`P450 delivery PoC runbook`](runbooks/P450_DELIVERY_POC_OFFBOARD_RUNBOOK_2026-08-17.md)：範圍受限的交付展示流程與停止條件。
6. [`Reliable latency remediation runbook`](runbooks/P450_RELIABLE_LATENCY_REMEDIATION_RUNBOOK_2026-08-17.md)：transport 診斷與分階段改善流程。

## 技術資料在哪裡

| 目錄 | 內容 |
| --- | --- |
| [`scripts/`](../scripts/) | ROS 2 probe、monitor、受保護的控制診斷與 NX 儲存工具 |
| [`systemd/`](../systemd/) | Micro XRCE-DDS Agent service 定義 |
| [`patches/`](../patches/) | 可審查的 PX4／XRCE 修改 |
| [`firmware/`](../firmware/) | `.px4` 韌體、SHA-256 checksum 與檔案說明 |
| [`evidence/`](../evidence/) | 依日期／TEST_ID 保存的測試摘要與原始觀測，只增不改 |
| [`config/`](../config/) | NX runtime、SD-first 儲存設定與區域規則 |

## 文件分類

| 目錄 | 用途 |
| --- | --- |
| [`current/`](current/) | 目前交接狀態與權威清單 |
| [`runbooks/`](runbooks/) | 有前置條件、停止條件和 rollback 的操作流程 |
| [`operations/`](operations/) | 安裝、設定與命令參考，不代表最新測試結論 |
| [`reports/`](reports/) | 按日期保存的測試結果、分析與計畫 |
| [`history/`](history/) | 已被取代但仍需保留來源脈絡的 handoff 與敘述 |
| [`raw/`](raw/) | 尚未驗證或測試條件不完整的筆記與 captures |

根目錄只保留 `README.md` 和 `AGENTS.md` 兩個 Markdown 入口。既有文件透過 `git mv` 分類，沒有因整理而刪除；
後來上傳到根目錄的 ULog 已索引在 [`raw/captures/ULG/`](raw/captures/ULG/README.md)。
