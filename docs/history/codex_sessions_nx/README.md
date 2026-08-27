# NX Codex 專案對話紀錄

這個資料夾保存 NX 端與 P450 專案直接相關的 Codex 主對話匯出，供總報告與筆電 Codex 交接使用。

## 匯出規則

- 共 15 份主對話，依原始 session 日期/檔名分層保存。
- 只保留 user/assistant 的文字訊息，未包含 Codex tool call、tool output、system metadata、plugin、cache 或 model cache。
- 已移除偵測到的 GitHub token、密碼、private key 與認證字串。
- 62 份內部 subagent/guardian session 未匯出，因為不是操作者主對話，且可能重複或包含內部審查資料。
- 原始 session 仍留在 NX 的 Codex home，沒有被刪除或覆寫。

## 來源

來源根目錄：`/media/p450/P450_DATA/builds/NX-user-storage/codex-home/sessions/`

這些 Markdown 是可公開的工程交接副本，不宣稱是 Codex 原始資料的逐位元備份。
