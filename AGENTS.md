# Context: KingsField-PlayStation

- **Tier R (`ps1`, `v0.2.0`):** `D3/S4/R2` (`P: none`, `goalDecompTier: D4`, `goalStudyTier: S5`, `goalRecompTier: R3`, target engine `reStation` `0.2.x`). Zero `Builds`/`Installers`/`Releases`; `Corpus` & `Dev/data/` gitignored (`-xr!Corpus\*`, `standalone/` RO).
- **Control:** [research.manifest.json](Dev/research.manifest.json) | [CrownDepths-ForsakenIsle-SlateOne-02-Decomp.code-workspace](Dev/CrownDepths-ForsakenIsle-SlateOne-02-Decomp.code-workspace) | Downstream: `KingsFieldRecomp` (`read-only`)

## 1. Quartet, Security & State
- [README.md](README.md) | [FEATURES.md](FEATURES.md) | [ROADMAP.md](ROADMAP.md) | [CHANGELOG.md](CHANGELOG.md) | [SECURITY.md](SECURITY.md) | [active.state](active.state)

## 2. Manuals (`Dev/docs/`)
- [ARCHITECTURE.md](Dev/docs/ARCHITECTURE.md) | [SPECIFICATIONS.md](Dev/docs/SPECIFICATIONS.md) | [FINDINGS.md](Dev/docs/FINDINGS.md) | [OPERATIONS.md](Dev/docs/OPERATIONS.md)
- **Specs, Spokes, Plans & Reports:** [specifications/](Dev/docs/specifications/) | [findings/](Dev/docs/findings/) | [stages/](Dev/docs/stages/) | Local-only gitignored: `Dev/docs/plans/`, `Dev/docs/reports/`

## 3. Governance & Notion
- **Notion:** `<NOTION_PROJECT_PAGE_ID>` (`<NOTION_TASK_LIST_COLLECTION>` — local IDs in gitignored `Dev/data/notion_hub.local.json`)
- **Commit `/post` Hook:** Every commit & release pushes `/post` via `active.state` -> `discordPost` (`DISCORD_WEBHOOK_FOUNDATION`), tagging `@StreamDoesDev`.
