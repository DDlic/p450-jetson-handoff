#!/usr/bin/env bash
set -Eeuo pipefail

SD_MOUNT="/media/p450/P450_DATA"
SD_BASE="${SD_MOUNT}/builds/NX-user-storage"
STATE_DIR="${SD_BASE}/migration-state"
STATE_FILE="${STATE_DIR}/codex-migration.env"
CODEX_SOURCE="${HOME}/.codex"
CACHE_SOURCE="${HOME}/.cache"
CODEX_TARGET="${SD_BASE}/codex-home"
CACHE_TARGET="${SD_BASE}/xdg-cache"

log() {
    printf '[p450-sd-migrate] %s\n' "$*"
}

die() {
    printf '[p450-sd-migrate] ERROR: %s\n' "$*" >&2
    exit 1
}

usage() {
    cat <<'EOF'
Usage:
  migrate_codex_to_sd_offline.sh migrate
  migrate_codex_to_sd_offline.sh status
  migrate_codex_to_sd_offline.sh rollback
  migrate_codex_to_sd_offline.sh finalize

migrate   關閉 Codex/Firefox 後，把 ~/.codex 與 ~/.cache 搬到 SD 並建立 symlink。
status    只讀檢查掛載、symlink、備份與容量。
rollback  關閉 Codex/Firefox 後，從保留的 eMMC 備份回復。
finalize  確認 SD 版 Codex 可正常啟動後，永久刪除 eMMC 備份。
EOF
}

require_commands() {
    local command_name
    for command_name in findmnt rsync pgrep readlink df du stat; do
        command -v "${command_name}" >/dev/null 2>&1 || die "missing command: ${command_name}"
    done
}

require_sd() {
    local target fstype source
    target="$(findmnt -rn -T "${SD_MOUNT}" -o TARGET 2>/dev/null || true)"
    fstype="$(findmnt -rn -T "${SD_MOUNT}" -o FSTYPE 2>/dev/null || true)"
    source="$(findmnt -rn -T "${SD_MOUNT}" -o SOURCE 2>/dev/null || true)"

    [[ "${target}" == "${SD_MOUNT}" ]] || die "SD is not mounted at ${SD_MOUNT}"
    [[ "${fstype}" == "ext4" ]] || die "unexpected SD filesystem: ${fstype:-none}"
    [[ -w "${SD_MOUNT}/builds" ]] || die "SD builds directory is not writable"
    log "SD OK: ${source} on ${target} (${fstype})"
}

require_apps_closed() {
    if pgrep -u "$(id -u)" -x codex >/dev/null 2>&1 ||
       pgrep -u "$(id -u)" -f 'codex-code-mode-host' >/dev/null 2>&1; then
        die "Codex is still running. Close every Codex window/session, then run this script in Terminal."
    fi

    if pgrep -u "$(id -u)" -x firefox >/dev/null 2>&1; then
        die "Firefox is still running. Close it so ~/.cache can be copied consistently."
    fi
}

link_points_to() {
    local link_path="$1"
    local expected="$2"
    [[ -L "${link_path}" ]] && [[ "$(readlink -f "${link_path}")" == "${expected}" ]]
}

show_status() {
    require_sd
    printf '\n%-18s %s\n' 'eMMC:' "$(df -h / | awk 'NR==2 {print $3 " used, " $4 " available, " $5}')"
    printf '%-18s %s\n' 'P450_DATA:' "$(df -h "${SD_MOUNT}" | awk 'NR==2 {print $3 " used, " $4 " available, " $5}')"
    printf '%-18s %s\n' 'Codex source:' "$(stat -c '%F %N' "${CODEX_SOURCE}" 2>/dev/null || echo missing)"
    printf '%-18s %s\n' 'Cache source:' "$(stat -c '%F %N' "${CACHE_SOURCE}" 2>/dev/null || echo missing)"
    printf '%-18s %s\n' 'Codex target:' "$(du -sh "${CODEX_TARGET}" 2>/dev/null | awk '{print $1}' || echo missing)"
    printf '%-18s %s\n' 'Cache target:' "$(du -sh "${CACHE_TARGET}" 2>/dev/null | awk '{print $1}' || echo missing)"
    printf '%-18s %s\n' 'State file:' "${STATE_FILE}"

    if link_points_to "${CODEX_SOURCE}" "${CODEX_TARGET}"; then
        log "Codex migration: ACTIVE"
    else
        log "Codex migration: NOT ACTIVE"
    fi
}

check_capacity() {
    local required_kb available_kb
    required_kb="$(( $(du -sk "${CODEX_SOURCE}" "${CACHE_SOURCE}" | awk '{sum += $1} END {print sum}') + 262144 ))"
    available_kb="$(df -Pk "${SD_MOUNT}" | awk 'NR==2 {print $4}')"
    (( available_kb > required_kb )) || die "not enough SD space: need ${required_kb} KiB, have ${available_kb} KiB"
    log "capacity check passed: need ${required_kb} KiB including margin"
}

copy_and_verify() {
    local source_path="$1"
    local target_path="$2"
    local verify_output

    [[ -d "${source_path}" ]] || die "source is not a directory: ${source_path}"
    [[ ! -L "${source_path}" ]] || die "source is already a symlink: ${source_path}"
    [[ ! -e "${target_path}" ]] || die "target already exists: ${target_path}; do not merge it manually"

    mkdir -p "${target_path}"
    log "copying ${source_path} -> ${target_path}"
    rsync -aHAX --numeric-ids "${source_path}/" "${target_path}/"

    log "checksum dry-run verification: ${source_path}"
    verify_output="$(rsync -aHAXnc --delete --itemize-changes "${source_path}/" "${target_path}/")"
    [[ -z "${verify_output}" ]] || {
        printf '%s\n' "${verify_output}" >&2
        die "verification failed for ${source_path}; source was NOT removed"
    }
}

do_migrate() {
    local timestamp codex_backup cache_backup

    require_sd
    require_apps_closed

    if link_points_to "${CODEX_SOURCE}" "${CODEX_TARGET}" &&
       link_points_to "${CACHE_SOURCE}" "${CACHE_TARGET}"; then
        log "migration is already active"
        show_status
        return 0
    fi

    [[ ! -L "${CODEX_SOURCE}" ]] || die "unexpected ~/.codex symlink; inspect manually"
    [[ ! -L "${CACHE_SOURCE}" ]] || die "unexpected ~/.cache symlink; inspect manually"
    check_capacity

    mkdir -p "${STATE_DIR}"
    copy_and_verify "${CODEX_SOURCE}" "${CODEX_TARGET}"
    copy_and_verify "${CACHE_SOURCE}" "${CACHE_TARGET}"

    timestamp="$(date +%Y%m%d_%H%M%S)"
    codex_backup="${HOME}/.codex.emmc-backup-${timestamp}"
    cache_backup="${HOME}/.cache.emmc-backup-${timestamp}"

    mv "${CODEX_SOURCE}" "${codex_backup}"
    ln -s "${CODEX_TARGET}" "${CODEX_SOURCE}"
    mv "${CACHE_SOURCE}" "${cache_backup}"
    ln -s "${CACHE_TARGET}" "${CACHE_SOURCE}"

    cat >"${STATE_FILE}" <<EOF
CODEX_BACKUP='${codex_backup}'
CACHE_BACKUP='${cache_backup}'
CODEX_TARGET='${CODEX_TARGET}'
CACHE_TARGET='${CACHE_TARGET}'
MIGRATED_AT='${timestamp}'
EOF

    link_points_to "${CODEX_SOURCE}" "${CODEX_TARGET}" || die "Codex symlink validation failed"
    link_points_to "${CACHE_SOURCE}" "${CACHE_TARGET}" || die "cache symlink validation failed"
    [[ -x "${CODEX_SOURCE}/packages/standalone/current/bin/codex" ]] || die "migrated Codex binary is missing"

    log "migration complete"
    log "eMMC backups retained: ${codex_backup} and ${cache_backup}"
    log "start Codex normally and verify it works; later run this script with 'finalize' to free backup space"
}

load_state() {
    [[ -r "${STATE_FILE}" ]] || die "state file not found: ${STATE_FILE}"
    # This file is generated only by this script and stored in the user-owned SD directory.
    # shellcheck disable=SC1090
    source "${STATE_FILE}"
    [[ -n "${CODEX_BACKUP:-}" && -n "${CACHE_BACKUP:-}" ]] || die "invalid state file"
}

do_rollback() {
    require_sd
    require_apps_closed
    load_state

    link_points_to "${CODEX_SOURCE}" "${CODEX_TARGET}" || die "unexpected ~/.codex state"
    link_points_to "${CACHE_SOURCE}" "${CACHE_TARGET}" || die "unexpected ~/.cache state"
    [[ -d "${CODEX_BACKUP}" && -d "${CACHE_BACKUP}" ]] || die "eMMC backup is missing"

    rm "${CODEX_SOURCE}"
    mv "${CODEX_BACKUP}" "${CODEX_SOURCE}"
    rm "${CACHE_SOURCE}"
    mv "${CACHE_BACKUP}" "${CACHE_SOURCE}"
    log "rollback complete; SD copies were preserved"
}

do_finalize() {
    local confirmation
    require_sd
    require_apps_closed
    load_state

    link_points_to "${CODEX_SOURCE}" "${CODEX_TARGET}" || die "Codex is not using the SD target"
    link_points_to "${CACHE_SOURCE}" "${CACHE_TARGET}" || die "cache is not using the SD target"
    [[ -x "${CODEX_TARGET}/packages/standalone/current/bin/codex" ]] || die "SD Codex binary is missing"

    printf 'This permanently deletes:\n  %s\n  %s\n' "${CODEX_BACKUP}" "${CACHE_BACKUP}"
    read -r -p "Type DELETE-EMMC-BACKUP to continue: " confirmation
    [[ "${confirmation}" == "DELETE-EMMC-BACKUP" ]] || die "finalize cancelled"

    rm -rf -- "${CODEX_BACKUP}" "${CACHE_BACKUP}"
    log "eMMC backups deleted; SD migration remains active"
    show_status
}

main() {
    require_commands
    case "${1:-migrate}" in
        migrate) do_migrate ;;
        status) show_status ;;
        rollback) do_rollback ;;
        finalize) do_finalize ;;
        -h|--help|help) usage ;;
        *) usage; exit 2 ;;
    esac
}

main "$@"
