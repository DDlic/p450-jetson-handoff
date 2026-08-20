# ULog upload metadata summary

Source: `origin/main` commit `dac3d2a02458d8fd8507d14cc5a5d3e77cc23b55`.

The historical archive contains 99 `.ulg` Git LFS pointers under `docs/raw/captures/ULG/`. This review inspected only pointer metadata and did not download the payloads.

- Declared payload total: 224,513,881 bytes (214.113 MiB).
- Filename years: 47 from 2024, 51 from 2026, 1 unknown.
- Declared size range: 153,438 to 37,874,064 bytes.
- Three payloads exceed 10 MiB.
- Complete path, LFS SHA-256 and size inventory: `ULOG_LFS_INDEX.csv`.

Largest payloads intentionally skipped:

| Declared size | Path |
| ---: | --- |
| 36.120 MiB | `docs/raw/captures/ULG/log_0_2024-8-1-15-56-18.ulg` |
| 34.535 MiB | `docs/raw/captures/ULG/log_1_2024-8-1-16-17-02.ulg` |
| 10.107 MiB | `docs/raw/captures/ULG/log_5_2024-8-8-15-01-02.ulg` |

The full non-LFS `log_98_2026-8-20-14-06-02.ulg` was already copied, hashed and analyzed in `evidence/20260820_outdoor_offline_heading_gate/`. That log directly covers today's failed F1/F2 follow-up and is sufficient to prove the height-dependent heading flag and raw-vs-active GCS distinction.

Historical payloads should be fetched selectively only after a filename is matched to a concrete question, date, firmware, vehicle configuration and operator/QGC context. Bulk parsing the archive now would add storage and interpretation risk without changing the current script verdict.
