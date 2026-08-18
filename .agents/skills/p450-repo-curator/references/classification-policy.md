# P450 document classification policy

Assign one primary class to each document based on what a reader should do with it now.

## Classes

| Class | Test | Destination |
|---|---|---|
| Current index | Points to current authority; contains little procedure itself | repository root or `docs/` |
| Current handoff | Active coordination state that another machine/operator needs now | `docs/current/` |
| Runbook | Ordered procedure with prerequisites, gates, stop conditions, and rollback | `docs/runbooks/` |
| Operations | Setup/command reference not asserting a current experiment verdict | `docs/operations/` |
| Report | Dated experiment, analysis, plan, timeline, or presentation | `docs/reports/YYYY-MM-DD/` |
| History | Superseded overview, prompt, or narrative retained for provenance | `docs/history/` or `docs/history/handoffs/` |
| Raw note | Unstructured text whose claims have not been validated | `docs/raw/notes/` |
| Raw capture | Direct console/log fragment outside a timestamped evidence bundle | `docs/raw/captures/` |
| Evidence | Timestamped raw observation plus its local summary | `evidence/YYYYMMDD_*` |

## Rules

1. Content beats filename and last-modified time.
2. A runbook must contain safety prerequisites and stop conditions. Otherwise classify it as operations or a report.
3. A report remains a report even when a newer report supersedes its conclusion.
4. Do not rewrite a historical document to make it look current. Add authority metadata in the inventory/index.
5. Do not move timestamped evidence merely to make the tree symmetrical.
6. Preserve unusual names and extensions during the first move. Rename only in a separately reviewed normalization phase.
7. Never classify a firmware checksum, CSV, pstore record, console output, or patch as disposable generated output.

## No-deletion invariant

For a structural PR, every tracked path that existed at the base commit must be represented as unchanged, modified, or renamed in the final diff. Plain deletion is a failure. If a file is truly obsolete, move it to history/raw and record why.
