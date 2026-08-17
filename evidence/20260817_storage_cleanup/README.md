# 2026-08-17 eMMC 清理與 SD 分流

## 結果

- 清理前正常基線：約 74%、可用 2.8 GB。
- kernel source 暫存 clone 期間曾短暫到 94%、只剩約 834 MB；暫存清除後恢復。
- 最終：eMMC 64%、可用 4.8 GB。
- `P450_DATA`：117 GB，使用 7.6 GB，可用約 104 GB。
- MicroXRCEAgent systemd service 清理後仍為 `active`，`NRestarts=0`。

## 直接清除：無需保存、可重建

- Codex 舊版 `0.145.0`、`0.146.0`；保留 current `0.147.0`。
- Codex plugin staging、Firefox web cache、pip cache。
- APT package cache。
- journal archived files 88 MB，保留目前 journal 並限制歸檔總量。
- `/var/crash` 中舊 Sunshine 與 ROS 2 crash dump。
- `/home/p450/micro_xrce_dds_agent-2.4.2`：只有 500 MB build，系統服務實際使用
  `/usr/local/bin/MicroXRCEAgent` 與 `/usr/local/lib`，故刪除該可重建 build。

## 搬到 SD：仍有後續價值

`/home/p450/builds` 的 Agent 診斷 builds 已移到：

```text
/media/p450/P450_DATA/builds/NX-Agent-builds-20260817
```

原路徑保留為 symlink，因此既有命令不需修改：

```text
/home/p450/builds -> /media/p450/P450_DATA/builds/NX-Agent-builds-20260817
```

搬移前後皆為 200 個 regular files。關鍵檔案 checksum：

```text
MicroXRCEAgent
0cfabea315262147898fb925308b479726542bd64653fa217c789fddb8e5d3f5

libmicroxrcedds_agent.so.2.4.2
49478f6957421e3210df81a24324fbaa6a3d471acffdfa93ece9550dc33a1cc1
```

## PX4 worktree 特例

`/home/p450/PX4-Autopilot-xrce-trace` 是 SD 主 repository 登錄的 Git worktree，且包含
NuttX submodules。檔案已 checksum 複製到：

```text
/media/p450/P450_DATA/builds/PX4-Autopilot-xrce-trace-worktree
```

來源與副本皆為 29,044 個 regular files，HEAD 都是 `c7a39478405122a04ef9f10b69f873561751a126`。
但是 submodule `.git` 使用相對路徑，副本在新位置直接執行 `git status` 會失敗。因此：

- eMMC 原 worktree 暫時保留，沒有強制切換；
- SD 副本目前只視為完整檔案備份，不視為可直接建置的 Git worktree；
- 後續若要正式遷移，必須使用 Git worktree/submodule repair 流程，不可直接刪除原件。

## 不可直接手動搬移／刪除

- `/usr`：系統套件、shared libraries、headers；只透過 apt/dpkg 管理。
- `/opt/ros`：ROS 2 Foxy runtime。
- `/opt/ota_package`：由 NVIDIA bootloader/kernel/xusb packages 擁有。
- `/home/p450/p450_ros2_ws`：目前 ROS runtime workspace。
- `/home/p450/.codex` 的 current release 與 session 資料。

## 後續 SD-first 遷移

同日已追加 SD-first policy，將 Downloads、ROS build/log、Agent sources、CMake tool、Python
user packages 搬到 `P450_DATA`，原路徑全部保留 symlink。`~/.codex` 與 `~/.cache` 因目前
Codex/Firefox 仍在使用，改由桌面離線腳本在程式關閉後執行。詳細路徑、guard、rollback 與
finalize 流程見 [`../../SD_STORAGE_POLICY_20260817.md`](../../SD_STORAGE_POLICY_20260817.md)。
