# Later root-level ULog uploads

This directory preserves 12 ULog files uploaded directly at repository root on
2026-08-20 and 2026-08-26. They were moved here with `git mv` during repository
curation; filenames and payloads were not changed.

- Classification: raw capture.
- Authority: none until correlated with a TEST_ID, firmware identity, vehicle
  state, QGroundControl console, NX CSV, and test conditions.
- Integrity: hashes are recorded in [`SHA256SUMS`](SHA256SUMS).
- Duplicate: `log_98_2026-8-20-14-06-02.ulg` is byte-identical to
  `../log_98_2026-8-20-14-06-02.ulg`. Both tracked paths are retained to preserve
  the upload history and the repository no-deletion invariant.

Do not infer flight readiness or a test verdict from these raw captures alone.
