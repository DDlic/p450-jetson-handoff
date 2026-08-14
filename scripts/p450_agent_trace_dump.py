#!/usr/bin/env python3
"""Convert the P450 Micro XRCE-DDS Agent shared-memory trace to CSV."""

import argparse
import csv
import mmap
import os
import struct
import sys
from collections import Counter


MAGIC = 0x4543525830353450
HEADER = struct.Struct("<QIIIIQQIIQQ")
RECORD = struct.Struct("<QQQIIIIiHHHHHBBII")
NO_SEQUENCE = 0xFFFF

EVENT_NAMES = {
    1: "DDS_CALLBACK_BEGIN",
    2: "DDS_CALLBACK_END",
    3: "SEQ_ASSIGNED",
    4: "QUEUE_NEW",
    5: "SEND_BEGIN",
    6: "UART_WRITE_BEGIN",
    7: "UART_WRITE_END",
    8: "SEND_END",
    9: "ACKNACK_RX",
    10: "RETX_QUEUE",
    11: "ACK_UPDATE",
    12: "HEARTBEAT_QUEUE",
}

CSV_COLUMNS = (
    "logical_index",
    "event",
    "event_name",
    "t_ns",
    "relative_ms",
    "delta_ms",
    "tid",
    "session_id",
    "stream_id",
    "seq_num",
    "first_unacked",
    "nack_bitmap",
    "object_id",
    "callback_id",
    "client_key",
    "len",
    "result",
    "aux",
)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", help="Binary trace file, normally under /dev/shm")
    parser.add_argument("--output", "-o", help="CSV path; stdout when omitted")
    parser.add_argument("--summary-only", action="store_true", help="Do not emit CSV rows")
    return parser.parse_args()


def load_records(path):
    with open(path, "rb") as source:
        with mmap.mmap(source.fileno(), 0, access=mmap.ACCESS_READ) as mapped:
            if len(mapped) < HEADER.size:
                raise ValueError("trace file is smaller than its header")

            (magic, version, header_size, record_size, capacity, start_ns,
             write_index, pid, stream_filter, _reserved0, _reserved1) = HEADER.unpack_from(mapped, 0)

            if magic != MAGIC:
                raise ValueError(f"bad trace magic: 0x{magic:016x}")
            if version != 1:
                raise ValueError(f"unsupported trace version: {version}")
            if header_size != HEADER.size or record_size != RECORD.size:
                raise ValueError(
                    f"layout mismatch: header={header_size}/{HEADER.size}, "
                    f"record={record_size}/{RECORD.size}")
            expected_size = header_size + capacity * record_size
            if len(mapped) != expected_size:
                raise ValueError(f"file size mismatch: {len(mapped)} != {expected_size}")

            first_index = max(0, write_index - capacity)
            records = []
            unstable = 0
            for logical_index in range(first_index, write_index):
                offset = header_size + (logical_index % capacity) * record_size
                raw = mapped[offset:offset + record_size]
                values = RECORD.unpack(raw)
                commit = values[0]
                commit_after = struct.unpack_from("<Q", mapped, offset)[0]
                if commit != logical_index + 1 or commit_after != commit:
                    unstable += 1
                    continue

                (commit, t_ns, aux, callback_id, client_key, tid, length, result,
                 event, seq_num, first_unacked, nack_bitmap, object_id,
                 session_id, stream_id, _r0, _r1) = values
                records.append({
                    "logical_index": logical_index,
                    "event": event,
                    "event_name": EVENT_NAMES.get(event, f"UNKNOWN_{event}"),
                    "t_ns": t_ns,
                    "tid": tid,
                    "session_id": session_id,
                    "stream_id": stream_id,
                    "seq_num": seq_num,
                    "first_unacked": first_unacked,
                    "nack_bitmap": nack_bitmap,
                    "object_id": object_id,
                    "callback_id": callback_id,
                    "client_key": client_key,
                    "len": length,
                    "result": result,
                    "aux": aux,
                })

            metadata = {
                "version": version,
                "capacity": capacity,
                "start_ns": start_ns,
                "write_index": write_index,
                "pid": pid,
                "stream_filter": stream_filter,
                "unstable_records": unstable,
            }
            return metadata, records


def add_timing(records):
    previous = None
    first = records[0]["t_ns"] if records else 0
    for row in records:
        row["relative_ms"] = f"{(row['t_ns'] - first) / 1_000_000:.6f}"
        row["delta_ms"] = "" if previous is None else f"{(row['t_ns'] - previous) / 1_000_000:.6f}"
        previous = row["t_ns"]


def print_summary(metadata, records):
    counts = Counter(row["event_name"] for row in records)
    print(
        "TRACE_SUMMARY "
        f"pid={metadata['pid']} stream={metadata['stream_filter']} "
        f"write_index={metadata['write_index']} capacity={metadata['capacity']} "
        f"valid={len(records)} unstable={metadata['unstable_records']}",
        file=sys.stderr,
    )
    for event_id in sorted(EVENT_NAMES):
        name = EVENT_NAMES[event_id]
        if counts[name]:
            print(f"TRACE_EVENT {name}={counts[name]}", file=sys.stderr)

    for event_name in ("DDS_CALLBACK_BEGIN", "SEQ_ASSIGNED", "SEND_BEGIN"):
        times = [row["t_ns"] for row in records if row["event_name"] == event_name]
        if len(times) > 1:
            max_gap_ms = max(b - a for a, b in zip(times, times[1:])) / 1_000_000
            print(f"TRACE_MAX_GAP {event_name}={max_gap_ms:.6f}ms", file=sys.stderr)


def write_csv(records, output_path):
    stream = open(output_path, "w", newline="", encoding="utf-8") if output_path else sys.stdout
    try:
        writer = csv.DictWriter(stream, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in records:
            formatted = dict(row)
            formatted["seq_num"] = "" if row["seq_num"] == NO_SEQUENCE else row["seq_num"]
            formatted["nack_bitmap"] = f"0x{row['nack_bitmap']:04x}"
            formatted["client_key"] = f"0x{row['client_key']:08x}"
            writer.writerow(formatted)
    finally:
        if output_path:
            stream.close()


def main():
    args = parse_args()
    metadata, records = load_records(args.trace)
    add_timing(records)
    print_summary(metadata, records)
    if not args.summary_only:
        write_csv(records, args.output)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
