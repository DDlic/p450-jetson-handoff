---
name: p450-repo-curator
description: Safely audit, classify, move, and index files in the DDlic P450 Jetson handoff repository while preserving raw evidence, Git history, safety gates, and authority relationships. Use for repository cleanup, root-document reduction, handoff consolidation, Markdown link repair, evidence provenance review, or deciding whether a P450 document is current, historical, a runbook, a report, or raw evidence.
---

# P450 Repo Curator

Preserve every pre-existing file while making current authority easy to find. Repository neatness is never a reason to erase evidence or rewrite history.

## Required references

Read both before classifying or moving files:

- [classification-policy.md](references/classification-policy.md)
- [authority-order.md](references/authority-order.md)

Also read the repository-root `AGENTS.md` and any nearer subtree instructions.

## Workflow

1. Establish repository identity with `git remote -v`, `git branch --show-current`, `git rev-parse HEAD`, and `git status --short`.
2. Inventory tracked files with `git ls-files`; inspect headings, links, Git dates, and referenced evidence. Never classify only from a filename.
3. Run `python3 .agents/skills/p450-repo-curator/scripts/audit_repo.py --base-ref origin/main` before edits.
4. Assign each document exactly one primary class from the classification policy. Record authority, supersession, and target path in `docs/current/DOC_INVENTORY.md`.
5. Keep `README.md`, `AGENTS.md`, and conventional technical directories at root. Move classified documents with `git mv`; do not recreate them under new names.
6. Repair all relative Markdown links and update `docs/INDEX.md`, `README.md`, the inventory, and architecture map in the same change.
7. Rerun the audit, Python compilation, firmware checksum validation, `git diff --check`, and `git diff --name-status --find-renames <base>`.
8. Stop if a pre-existing file has plain `D` status, a local link is broken, a raw evidence payload changed, or current authority becomes ambiguous. Evidence `README.md`/`SUMMARY.md` edits are limited to link maintenance during structural moves.
9. Commit one coherent structural phase and merge it to trunk before starting another phase.

## Handling technical claims

- Separate observation, inference, and unknown.
- Compare firmware hash, QoS, Agent version/config, baud, topic set/rates, duration, vehicle state, and test ID before combining results.
- Preserve contrary evidence. A later test qualifies an earlier result; it does not make the earlier raw data disposable.
- For a consequential disputed claim such as “Reliable is safe enough to fly,” build a `.doubt.json` with the installed `build-evidence-map` skill and validate it. Do not use an evidence graph for simple navigation work.
- Repository cleanup never authorizes hardware actions.

## Path rules

- `docs/current/`: current coordination and authority maps.
- `docs/runbooks/`: actionable procedures with gates and rollback.
- `docs/operations/`: setup and command references that are not test conclusions.
- `docs/reports/YYYY-MM-DD/`: dated test reports, plans, and engineering syntheses.
- `docs/history/handoffs/`: superseded prompts and handoff narratives.
- `docs/raw/notes/` and `docs/raw/captures/`: unverified source material preserved verbatim.
- `evidence/YYYYMMDD_*`: timestamped evidence bundles; preserve paths unless a dedicated evidence migration is explicitly requested.
- `firmware/`, `patches/`, `scripts/`, `systemd/`, and `config/`: stable technical roots.

## Deliverable

Report the old-to-new path map, any authority conflicts, validation results, and the exact Git diff status. Explicitly say whether any tracked file was deleted. Never claim flight readiness from a successful repository audit.
