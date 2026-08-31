# Branch inventory — 2026-08-31

This file records repository branch intent after the 2026-08-31 curation. It is
navigation metadata, not flight or test authority. Commit counts are relative to
`main` at `b180a91a18d1bd34ed80d63680c50fba0b3842a3`.

## Live branches

| Branch | Tip at inventory | Relative to `main` | Purpose and status |
|---|---|---:|---|
| `main` | `b180a91` | default | Curated public handoff and current repository entry point. Root-level late ULog uploads have been classified under `docs/raw/captures/ULG/`. |
| `work/outdoor-v6-nx-evidence` | `c04c4a0` | 20 ahead, 6 behind | Outdoor V6/NX evidence work. Contains unique scripts, current cards, and raw evidence; retain until a dedicated audited integration PR resolves its divergence from `main`. |
| `work/ubuntu22-humble-visual-sitl` | `473f5c8` | 13 ahead, 6 behind | Ubuntu 22.04/Humble visual SITL work. Contains unique model, report, media evidence, and test code; retain until its own audited integration PR. |

The two `work/*` branches share the earlier delivery-PoC history but have unique
tips. Neither branch is current authority merely because its commit is newer.
Claims still follow the authority and same-condition rules in `AGENTS.md`.

## Archived branch tips

| Former branch | Archive tag | Reason branch ref was removed |
|---|---|---|
| `agent/document-reliable-latency-remediation` | `archive/2026-08-31/document-reliable-latency-remediation` | Fully merged into `main`; zero unique commits. |
| `codex/delivery-poc-mission` | `archive/2026-08-31/delivery-poc-mission` | Its tip is an ancestor of both retained `work/*` branches; the standalone branch ref was redundant. |

The annotated tags preserve the exact former tips. Removing the branch refs did
not delete commits or tracked files.

## Branch hygiene policy

1. Use `work/<scope>` for substantial unmerged technical work and
   `chore/<scope>` or `docs/<scope>` for short-lived curation phases.
2. Keep one coherent structural phase per PR and merge it before starting the
   next structural phase.
3. Before retiring an unmerged or consequential branch, create an annotated
   `archive/YYYY-MM-DD/<name>` tag and verify its target SHA.
4. Do not merge evidence-heavy branches merely to reduce the branch count.
   Rebase or merge from current `main`, resolve authority/index conflicts, run
   the curator audit, and validate code/checksums in a dedicated PR.
5. Delete short-lived merged branches after merge; tags are for preservation,
   not a substitute for normal branch cleanup.
