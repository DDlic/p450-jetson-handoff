# P450 NX SD-first storage policy

## 目標

14 GB eMMC 只保留 Ubuntu、Jetson BSP、`/usr`、`/opt/ros`、ROS runtime install 與必要的
使用者啟動程式。Git repositories、Codex updates/session、build、log、cache、download 與
temporary files 優先放在 128 GB ext4 `P450_DATA`。

固定掛載點：

```text
/media/p450/P450_DATA
```

使用者資料根目錄：

```text
/media/p450/P450_DATA/builds/NX-user-storage
```

## 目錄分工

| 資料 | SD 位置 | 原路徑／入口 |
| --- | --- | --- |
| Codex home、updates、sessions | `NX-user-storage/codex-home` | `~/.codex` symlink |
| XDG/cache | `NX-user-storage/xdg-cache` | `~/.cache` symlink |
| temporary output | `NX-user-storage/tmp` | `TMPDIR` |
| new Git clones | `P450_DATA/src` | `git-clone-sd` / `sdclone` |
| handoff repository | `P450_DATA/src/p450-jetson-handoff` | `~/p450-jetson-handoff` symlink |
| ROS logs | `NX-user-storage/ros/ros-log` | `ROS_LOG_DIR`、`~/.ros/log` |
| colcon logs | `NX-user-storage/ros/colcon-log` | `COLCON_LOG_PATH` |
| ROS workspace build/log | `NX-user-storage/ros/p450_ros2_ws/{build,log}` | workspace symlinks |
| downloads | `NX-user-storage/downloads` | `~/Downloads` symlink |
| Agent diagnostic builds | `P450_DATA/builds/NX-Agent-builds-20260817` | `~/builds` symlink |
| Python user packages | `NX-user-storage/python-user-site-packages` | `~/.local/lib/python3.8/site-packages` symlink |

## 2026-08-17 已完成

以下目錄已先複製、通過 `rsync -c --dry-run --delete` 零差異驗證，才刪除 eMMC 副本並
建立 symlink：

- `~/Downloads`；
- `~/p450_ros2_ws/build`、`~/p450_ros2_ws/log`；
- `~/.ros/log`；
- `~/Micro-XRCE-DDS-Agent-2.4.2`；
- `~/Micro-XRCE-DDS-Agent-2.4.2-agenttrace`；
- `~/micro_xrce_dds_agent-2.4.3`；
- `~/cmake-3.22.6-linux-aarch64`；
- `~/.local/lib/python3.8/site-packages`；
- `~/builds`（前一階段已完成）。
- `~/p450-jetson-handoff`（main repository 本身）。

已安裝：

- `~/.config/p450-sd-storage.sh`：設定 SD temp/cache/ROS/colcon 路徑；
- `~/bin/codex`：SD mount 與 Codex migration guard；
- `~/bin/git-clone-sd`，互動 shell alias `sdclone`；
- `~/AGENTS.md`：要求後續 Codex 把大型寫入放到 SD；
- `~/Desktop/migrate_codex_to_sd_offline.sh`：離線遷移入口。

尚待機主關閉目前 Codex/Firefox 後執行：`~/.codex` 與 `~/.cache` 的最終切換。腳本未執行
前，`~/bin/codex` 會明確拒絕啟動新 Codex session，避免更新與 session 繼續寫入 eMMC。

上述線上可搬項目完成後，eMMC 為 62%、可用約 5.1 GB；SD 為 8%、可用約 103 GB。

## Codex 離線遷移

目前 Codex 執行時不可搬動自己的 executable、session 與 lock。關閉 Codex 和 Firefox 後，
在一般 Terminal 執行：

```bash
~/Desktop/migrate_codex_to_sd_offline.sh migrate
```

腳本先 rsync，再以 checksum dry-run 驗證，最後才切換 symlink。首次切換後保留 eMMC 備份。
確認新 Codex 能正常啟動，再關閉 Codex並執行：

```bash
~/Desktop/migrate_codex_to_sd_offline.sh finalize
```

如果新 Codex 無法啟動：

```bash
~/Desktop/migrate_codex_to_sd_offline.sh rollback
```

`finalize` 會永久刪除 eMMC 備份，而且要求輸入完整確認字串；`rollback` 不刪 SD 副本。

## Git clone

不要在 `~` 或 `/tmp` 直接 clone。使用：

```bash
sdclone https://github.com/OWNER/REPO.git
sdclone https://github.com/OWNER/REPO.git custom-name --depth=1
```

結果一律位於 `/media/p450/P450_DATA/src/`。

## 失效保護

- SD 掛載使用 `/etc/fstab` UUID、ext4、`nofail`。卡片遺失時系統仍可由 eMMC 開機。
- `codex` wrapper 在 SD 未掛載或 `~/.codex` 尚未切到 SD 時拒絕啟動，不會默默回寫 eMMC。
- 環境檔只有在 SD 掛載正確時才設定 `TMPDIR`、`XDG_CACHE_HOME`、`PIP_CACHE_DIR`、
  `ROS_LOG_DIR` 與 `COLCON_LOG_PATH`。
- `/usr`、`/opt/ros`、`/opt/ota_package` 與 ROS workspace `install/` 不搬，避免 SD 掛載問題
  破壞開機與 ROS runtime。
- PX4 `p450-xrce-rx-trace` worktree 含多層 NuttX submodules，目前仍是 eMMC 例外；其 Git
  common repository 與 firmware/build 已在 SD。正式遷移前不可直接移動該 worktree。

## 必要的 eMMC 例外

- Ubuntu、Jetson BSP、`/usr`、`/var/lib/dpkg`、`/opt/ros`、`/opt/ota_package`；
- ROS workspace `src/` 與 `install/`，確保 SD 暫時未掛載時系統與已安裝 runtime 仍可診斷；
- `~/.local/bin` 小型啟動入口；其大型 Python packages 已由 symlink 分流；
- Firefox profile、SSH/Git credentials 與桌面設定，不為節省少量空間增加登入／憑證風險；
- 上述 PX4 registered worktree，直到能在不破壞 submodule gitdir 的維護窗口重建。
