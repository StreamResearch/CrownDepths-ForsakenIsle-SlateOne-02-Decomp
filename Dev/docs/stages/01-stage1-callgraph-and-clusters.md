# Stage 1 Call Graph, Waves & Domain Clusters — King's Field

- **Game ID:** `kings-field` (`ps1` / `native_ghidra_c`)
- **Functions:** `1,757` total (`1,632` game, `125` PS1 SDK, `0` failed decompilations)
- **Globals:** `1,549` | **Max Topological Wave:** `25` | **Nontrivial SCCs:** `2`

## Domains (`5`)

| Domain | Functions | Programs | C Lines |
| :--- | ---: | :--- | ---: |
| `core` | `4` | `SLUS_001.58` | `84` |
| `module_end` | `343` | `END.EXE` | `11,738` |
| `module_game` | `898` | `GAME.EXE` | `46,311` |
| `module_open` | `387` | `OPEN.EXE` | `14,327` |
| `sdk` | `125` | `END.EXE`, `GAME.EXE`, `OPEN.EXE`, `SLUS_001.58` | `1,873` |

## Memory Regions

| Region | Globals |
| :--- | ---: |
| `CODE` | `449` |
| `RAM` | `1,099` |
| `SPU_VOICES` | `1` |

- **Clean-Room Hygiene (`v0.2.0`):** All `111` non-empty retail `"strings"` arrays in [call_graph.json](../../schemas/call_graph.json) are cleared to `[]` while preserving call edges and `meta.strings_json_counts`.
