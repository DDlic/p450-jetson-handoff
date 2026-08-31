# ULog raw capture archive

This directory preserves the ULog files supplied from the laptop `ULG` folder.

- Classification: raw capture; no measurements or conclusions are asserted here.
- Initial source archive: 99 `.ulg` files.
- Source archive size at import: approximately 224.5 MB.
- The filenames and binary payloads are preserved as supplied.
- No TEST_ID, matching QGroundControl console, NX CSV, parameter readback, or
  per-log result summary was supplied with this folder.

An additional 12 files that were later uploaded at repository root are preserved
under [`root_uploads_20260820_20260826/`](root_uploads_20260820_20260826/README.md).
That batch contains a second path for `log_98_2026-8-20-14-06-02.ulg`; its bytes
are identical to the original archived copy. Both tracked paths remain preserved.

Treat each log as immutable raw input. Interpret a log only after matching it
to firmware identity, test conditions, vehicle state, and the corresponding
console/CSV evidence.
