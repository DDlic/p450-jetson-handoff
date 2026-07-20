# Jetson Xavier NX 接手命令清單

這份文件是給 Ubuntu Codex CLI 逐段帶使用者執行的命令。每一段執行後都要等輸出確認，再進入下一段。

## A. 桌機只讀確認（目前第一步）

不要連接 NX，不要執行刷機：

```bash
cat /etc/os-release
```

```bash
uname -m
```

```bash
df -h ~
```

```bash
ls -lh ~/下載/Jetson_Linux_R35.6.0_aarch64.tbz2
```

```bash
ls -ld ~/nvidia/JP514/Linux_for_Tegra
```

預期：

```text
Ubuntu 22.04.5 LTS
x86_64
至少約 30 GB 可用空間
```

## B. 確認 BSP 與板型設定檔

```bash
cd ~/nvidia/JP514/Linux_for_Tegra
```

```bash
ls -l \
jetson-xavier-nx-devkit-qspi.conf \
jetson-xavier-nx-devkit.conf \
p3509-0000+p3668-0000-qspi.conf \
2>/dev/null
```

```bash
readlink -f jetson-xavier-nx-devkit-qspi.conf
```

可再檢查可用設定檔：

```bash
find . -maxdepth 2 -type f \
  \( -iname '*xavier*nx*.conf' -o -iname '*p3509*p3668*.conf' \) \
  | sort
```

正確方向：

```text
P3668-0000 + P3509-0000
jetson-xavier-nx-devkit
```

錯誤方向：

```text
jetson-xavier-nx-devkit-emmc
Orin
```

## C. 確認刷機工具存在

```bash
ls -l flash.sh
```

```bash
ls -l tools/l4t_flash_prerequisites.sh
```

```bash
ls -l tools/kernel_flash/l4t_initrd_flash.sh
```

若前置工具尚未執行，且使用者同意安裝依賴，才執行：

```bash
sudo ./tools/l4t_flash_prerequisites.sh
```

## D. 進入 Force Recovery

使用之前已成功讓裝置出現 `0955:7e19` 的同一種方法。不要因網路文字自行猜測 P450 載板上的 J14 腳位。

進入 Recovery 後，在 Ubuntu 桌機執行：

```bash
lsusb | grep -i nvidia
```

預期：

```text
0955:7e19
```

若沒有看到 `0955`，不要執行 `flash.sh`。先處理 USB 線、電源、Recovery 操作或載板按鈕問題。

## E. 重新刷寫 QSPI-only（確認前不可執行）

只有 A～D 都確認後才執行：

```bash
cd ~/nvidia/JP514/Linux_for_Tegra
```

```bash
sudo ./flash.sh jetson-xavier-nx-devkit-qspi internal 2>&1 | tee ~/xavier_nx_qspi_rerun.log
```

注意：

- 這是 QSPI-only 路線，不是整張 SD 卡重灌。
- 不要拔 USB。
- 不要斷電。
- 不要按 Reset。
- 若出現錯誤、timeout、Python、permission 或 board mismatch，停止並保留完整輸出。

完成後可查看 log 尾端：

```bash
tail -n 50 ~/xavier_nx_qspi_rerun.log
```

## F. QSPI 完成後測試 SD

1. 完全斷電。
2. 移除 Recovery 狀態。
3. 移除 Micro-USB。
4. 插入已燒錄的 JP514 `sd-blob` microSD。
5. 不要按住 REC。
6. 接螢幕、鍵盤與電源。
7. 開機等待 3～5 分鐘。

如果仍回到 Boot Manager，不要再次重刷 QSPI；先記錄：

- UEFI firmware version
- Boot Manager 完整項目
- `map -r` 結果
- 是否仍只有 BLK0～BLK11、沒有 FS0
- 是否進入 PXE/HTTP fallback

## G. 若需要重新產生 SD 映像（暫不執行）

只有確認原本 `sd-blob` 來源或版本有問題時，才考慮由 R35.6.0 BSP 產生：

```bash
cd ~/nvidia/JP514/Linux_for_Tegra/tools
```

```bash
sudo ./jetson-disk-image-creator.sh \
  -o sd-blob-r35.6.0-xavier-nx.img \
  -b jetson-xavier-nx-devkit \
  -r 100
```

這會產生新的原始 SD image，之後才用 Etcher 或 Linux `dd` 寫入 SD。不要在還沒確認 rootfs、映像內容與磁碟目標前執行。

## H. 不要使用的命令／方向

```bash
sudo ./flash.sh jetson-xavier-nx-devkit-emmc ...
```

```bash
sudo do-release-upgrade
```

```bash
sudo flash_eraseall /dev/mtd0
```

舊系統曾確認沒有有效的 `/dev/mtd0`，不可再走舊系統內寫 QSPI 的方法。
