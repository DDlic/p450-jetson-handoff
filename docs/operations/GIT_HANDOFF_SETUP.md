# Windows ↔ Ubuntu Codex CLI Git 交接設定

## 目前遠端

```text
Repository: https://github.com/DDlic/p450-jetson-handoff.git
Branch: main
Remote: origin
```

目前文件已同步到 `origin/main`。刷寫日志、BSP、映像、密碼與 key 由 `.gitignore` 排除，不會提交到 repository。

## 筆電接手

在筆電執行：

```bash
git clone https://github.com/DDlic/p450-jetson-handoff.git
cd p450-jetson-handoff
git pull --ff-only
```

先閱讀：

```bash
less docs/reports/2026-07-22/P450_PROGRESS_2026-07-22_ROS2_OFFLINE.md
less docs/history/JETSON_HANDOFF_MASTER.md
less docs/reports/2026-07-20/P450_PROGRESS_2026-07-20.md
less docs/operations/JETSON_HANDOFF_COMMANDS.md
```

## 日常同步

開始工作前：

```bash
git pull --ff-only
```

完成文件修改後：

```bash
git add .
git commit -m "Update Jetson Xavier NX handoff"
git push origin main
```

不要使用 `git push --force`，也不要提交 `.img`、`.tbz2`、`.zip`、`.log`、credentials、`.pem` 或 `.key`。
