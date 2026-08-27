#!/usr/bin/env bash
set -u

SOAK_DIR=/media/p450/P450_DATA/builds/NX-user-storage/rosbags/P450_20260819_1106_KERNEL_PHASE1_88X2BU_AB
SOAK_LOG=${SOAK_DIR}/SOAK_LOG.tsv
SOAK_RESULT=${SOAK_DIR}/SOAK_RESULT.txt
SOAK_START_ISO=$(date --iso-8601=seconds)
SOAK_END_EPOCH=$(( $(date +%s) + 7200 ))

printf 'timestamp\tuptime_s\t88x2bu\tusb1\tagent_state\tagent_pid\tnrestarts\tkernel_faults\n' > "${SOAK_LOG}"

while [ "$(date +%s)" -lt "${SOAK_END_EPOCH}" ]; do
    timestamp=$(date --iso-8601=seconds)
    uptime_s=$(cut -d. -f1 /proc/uptime)
    if lsmod | rg -q '^88x2bu\\b'; then module_state=loaded; else module_state=absent; fi
    if [ -e /sys/class/net/usb1 ]; then usb_state=$(cat /sys/class/net/usb1/operstate 2>/dev/null || echo present); else usb_state=absent; fi
    agent_state=$(systemctl is-active p450-micro-xrce-agent.service 2>/dev/null || true)
    agent_pid=$(systemctl show p450-micro-xrce-agent.service -p MainPID --value 2>/dev/null || echo unknown)
    nrestarts=$(systemctl show p450-micro-xrce-agent.service -p NRestarts --value 2>/dev/null || echo unknown)
    kernel_faults=$(journalctl -k -b --since "${SOAK_START_ISO}" --no-pager 2>/dev/null | rg -i 'panic|oops|key_garbage|hung task' | wc -l)
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
        "${timestamp}" "${uptime_s}" "${module_state}" "${usb_state}" \
        "${agent_state}" "${agent_pid}" "${nrestarts}" "${kernel_faults}" >> "${SOAK_LOG}"
    sleep 60
done

last_line=$(tail -n 1 "${SOAK_LOG}")
printf 'SOAK_COMPLETE\nSTART=%s\nEND=%s\nLAST=%s\n' \
    "${SOAK_START_ISO}" "$(date --iso-8601=seconds)" "${last_line}" > "${SOAK_RESULT}"
