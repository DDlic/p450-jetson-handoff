# QGC／PX4 端回傳區

此目錄由使用 QGroundControl 的筆電 Codex 管理。每輪只新增一份原始回傳檔，不修改
既有檔案；完整流程與安全限制見 repository 根目錄的
`QGC_LAPTOP_CODEX_HANDOFF_20260814.md`。

檔名：

```text
QGC_RETURN_YYYYMMDD_HHMM_TESTNAME.txt
```

可直接複製的內容：

```text
TEST_ID:
COLLAB_STATE: READY_QGC
LOCAL_TIME_ASIA_TAIPEI:
REPO_HEAD_BEFORE_TEST:
FIRMWARE_VER_ALL:
VEHICLE_PROPS_REMOVED:
VEHICLE_ARMED:
VEHICLE_MODE_OR_INTENTION:
PX4_REBOOT_DURING_TEST:
QGC_USB_OR_LINK_RECONNECT:

PRE_TEST_RAW_OUTPUT:
<ver all>
<uxrce_dds_client status>
<uxrce_dds_client trace reset>
<uxrce_dds_client trace，必須顯示 count=0,frozen=0>

POST_TEST_RAW_OUTPUT:
<uxrce_dds_client status>
<uxrce_dds_client trace，保留全部 RXTRACE 行>

OPERATOR_NOTES:
<只記實際操作、畫面與中斷事件，不推測原因>
```

提交規則：

```text
git pull --ff-only
git add evidence/20260814_qgc_px4/QGC_RETURN_*.txt
git commit -m "qgc: capture <TEST_ID> PX4 trace"
git push origin main
```

禁止提交密碼、token、登入資訊、parameter backup；禁止 force-push。若 QGC/PX4 版本、
安全狀態或 TEST_ID 不符，將 `COLLAB_STATE` 改成 `ABORTED_<reason>`，保留事實後停止。

push 後到 <https://github.com/DDlic/p450-jetson-handoff/issues/1> 留言：

```text
FROM: QGC Codex
TO: NX Codex
TEST_ID: <同一 TEST_ID>
STATE: QGC_EVIDENCE_PUSHED
ACTION: 請 pull 並驗證
EXPECTED_OUTPUT: ANALYZED 或資料缺項
REPLY_REQUIRED: YES
EVIDENCE_COMMIT: <完整 commit SHA>
```
