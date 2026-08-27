# NX 本機專案資料封存（2026-08-27）

本資料夾是歸還 NX 前的本機專案資料快照，來源為 `/media/p450/P450_DATA` 與 `/home/p450`。
原始來源檔案未被刪除或覆寫。

## 內容

- `rosbags/`：NX 上完整的測試證據目錄，包含已在 Git 的檔案及本次核對發現的 49 個尚未上傳檔案。
- `tmp/`：技術盤點 issue 回覆與本機取得的 `log_98`–`log_102` ULog 副本。
- `desktop/`：桌面上的歷史操作卡、Wi-Fi device-tree/overlay、listener 腳本與 CSV；桌面上的 V5 操作卡及兩個符號連結因內容已在 Git，未重複收錄。
- `worktree_snapshots/v6-work/`：V6 工作目錄快照，保留其與最終 Git 版本不同的歷史程式/測試/操作卡。
- `worktree_snapshots/p450-patch-stage/`：早期修補暫存快照。
- `config/p450-sd-storage.sh`：NX 使用 SD 儲存的環境設定腳本。

## 排除項目

- SSH/GitHub 私鑰、GitHub 認證、Codex 原始 session/cache/plugin/model cache。
- Desktop lock 檔、PX4/Micro-XRCE/ROS 上游依賴整棵原始碼與編譯產物。
- PX4 上游副本目前只有未追蹤的 build 產物，沒有未提交的源碼修改。

所有文字檔在封存前做過敏感資訊樣式掃描；檔案雜湊列於同目錄的 `SHA256SUMS`。
此封存包含跨路徑的重複證據，目的是在 NX 歸還後保留本機資料的完整可追溯快照。
