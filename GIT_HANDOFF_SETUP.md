# Windows ↔ Ubuntu Codex CLI Git 交接設定

## 目前本地狀態

- Git for Windows 已安裝：Git 2.55.0.windows.3
- 專用本地 repository 位於本資料夾的 `outputs/`
- 分支：`main`
- 交接文件已 staged，尚未 commit 或 push
- 尚未設定 GitHub remote
- 映像檔、BSP、log、密碼與 secrets 已由 `.gitignore` 排除

## 建立 GitHub repository

在 GitHub 建立 Private repository，例如 `p450-jetson-handoff`。建立時不要勾選 README、`.gitignore` 或 license。

建立後取得 HTTPS URL：`https://github.com/<USERNAME>/p450-jetson-handoff.git`

## Windows 推送

在 Windows PowerShell 執行下列命令，將 URL、姓名與 email 換成自己的資料：

- `$git = "C:\Program Files\Git\cmd\git.exe"`
- `$repo = "C:\Users\User\Documents\Codex\2026-07-15\jetson-chatgpt-conversation-6a5482fd-13f0-83ee\outputs"`
- `& $git -C $repo config user.name "YOUR NAME"`
- `& $git -C $repo config user.email "YOUR GITHUB EMAIL"`
- `& $git -C $repo remote add origin "https://github.com/YOUR_USERNAME/p450-jetson-handoff.git"`
- `& $git -C $repo commit -m "Add Jetson Xavier NX handoff documentation"`
- `& $git -C $repo push -u origin main`

Git Credential Manager 應在第一次 push 時開啟瀏覽器登入流程。不要把 GitHub 密碼或 Personal Access Token 寫進文件或命令歷史。

若 `origin` 已存在，使用 `& $git -C $repo remote set-url origin "https://github.com/YOUR_USERNAME/p450-jetson-handoff.git"`。

## Ubuntu Codex CLI clone

在 Ubuntu 執行：

- `sudo apt update`
- `sudo apt install -y git`
- `git clone https://github.com/YOUR_USERNAME/p450-jetson-handoff.git`
- `cd p450-jetson-handoff`
- `git config user.name "YOUR NAME"`
- `git config user.email "YOUR GITHUB EMAIL"`
- `less JETSON_HANDOFF_MASTER.md`
- `less JETSON_HANDOFF_COMMANDS.md`

## 日常同步

Ubuntu 端開始工作前：`git pull --ff-only`

Ubuntu 端新增紀錄後：`git add .`、`git commit -m "Record QSPI flashing diagnosis"`、`git push`

Windows 端接手：`& $git -C $repo pull --ff-only`

## 交接規則

- 每次刷機前先 commit 診斷紀錄。
- 不把 `.img`、`.tbz2`、`.zip`、`.log` 或 credential 加入 Git。
- 不使用 `git push --force`。
- 不使用 `git reset --hard`，除非使用者明確同意。
- 高風險實驗可使用 `diagnosis/qspi-rerun` 分支。
