# Stage 3: Function Catalog and Readable Source Tree

- **Track:** `kings-field` (`ps1` / `native_ghidra_c`)
- **Stage 3 Verdict:** `D3` & `S3` verified (`1,632 / 1,632` non-SDK functions cataloged, `0` failed decompilations, `0` banned names, `0` placeholder params, `clangd --check` `0` errors)

## 1. Per-Binary Function Coverage (`schemas/call_graph.json` & `schemas/functions_catalog.json`)

All `1,757` extracted functions span the resident bootloader plus three runtime overlay executables (`max_wave = 25`; `2` small 4-node audio SEQ SCC cycles in `OPEN.EXE` and `END.EXE`):

| Program | Base Address | Non-SDK Cataloged | SDK / CRT | Total | Primary Top-Wave Entry Points |
| --- | --- | ---: | ---: | ---: | --- |
| `SLUS_001.58` | `0x80010000` | 4 | 9 | 13 | `kf_slus_crt0_start` (`0x80010128`, w0), `kf_slus_main_exec_loop` (`0x80010038`, w1) |
| `OPEN.EXE` | `0x80011000` | 387 | 31 | 418 | `kf_open_entry_point` (`0x80013db8`, w12), `kf_open_main` (`0x80011ae0`, w11) |
| `GAME.EXE` | `0x80011000` | 898 | 56 | 954 | `kf_game_entry_boot` (`0x8004a628`, w25), `kf_game_main_loop` (`0x8001369c`, w23), `kf_game_player_tick_master` (`0x8002a550`, w22) |
| `END.EXE` | `0x80011000` | 343 | 29 | 372 | `kf_end_entry_point` (`0x80011cb4`, w11), `kf_end_main` (`0x800119a4`, w10) |
| **Total** | — | **1,632** | **125** | **1,757** | **100% named and typed (`0` `FUN_*` / `param_*`)** |

## 2. Domain Distribution (`schemas/functions_catalog.json`)

| Domain | Function Count | Programs Covered |
| --- | ---: | --- |
| `module_open` | 387 | `OPEN.EXE` |
| `module_end` | 343 | `END.EXE` |
| `module_game` | 202 | `GAME.EXE` |
| `audio` | 191 | `GAME.EXE` |
| `render_gfx` | 190 | `GAME.EXE` |
| `core` | 119 | `SLUS_001.58` (4), `GAME.EXE` (115) |
| `io_storage` | 90 | `GAME.EXE` |
| `ui_hud` | 82 | `GAME.EXE` |
| `input_save` | 28 | `GAME.EXE` |
| **Total** | **1,632** | `SLUS_001.58`, `OPEN.EXE`, `GAME.EXE`, `END.EXE` |

## 3. Topological Wave Stratification

Bottom-up wave indexing across `wave 0..25`:

- `wave 0..3`: `1,192` functions (`569` at `w0`, `329` at `w1`, `203` at `w2`, `91` at `w3`) covering math primitives, CD/BCD helpers, GTE transforms, SPU/VAB utilities, and state leaf setters.
- `wave 4..9`: `329` functions (`87`, `85`, `66`, `42`, `27`, `22`) covering map cell subdivision, TIM/TMD/MO loaders, entity AI, and menu renderers.
- `wave 10..25`: `111` functions spanning overlay main loops (`kf_open_main`, `kf_end_main`), SEQ event dispatchers, combat/world interaction, and top-level boot (`kf_game_entry_boot`, `w25`).

## 4. Readable C Tree & Re-export Normalization (`readable/` & `scripts/patch_ps1_reexport_and_compat.py`)

`readable/` organizes all `259` `.c` translation units and support headers (`0` `DECOMPILE FAILED` markers):

- `src/core/`: `1` `.c` file (`core_01.c`, `4` resident `SLUS_001.58` functions)
- `overlays/OPEN.EXE/`: `53` `.c` files (`open_01.c`..`open_53.c`, `387` functions)
- `overlays/GAME.EXE/`: `157` `.c` files (`game_01.c`..`game_157.c`, `898` functions)
- `overlays/END.EXE/`: `43` `.c` files (`end_01.c`..`end_43.c`, `343` functions)
- `sdk/`: `5` `.c` files (`sdk_01.c`..`sdk_05.c`, PS1-SDK/BIOS stubs deduplicated cleanly across overlays)
- `include/`: `kingsfield_types.h`, `kingsfield_globals.h`, `kingsfield_functions.h`, `ghidra_compat.h`, and `include/types/*.h`

`scripts/patch_ps1_reexport_and_compat.py` normalizes raw decompiler artifacts (`SUBPIECE` / 3-byte unaligned loads, `undefined1[2|4]` stack casts, `void`-to-`uint32_t` return promotion where callers inspect the return register, call-site arity reconciliation, and missing PS1 MMIO/GTE/label compatibility externs in `ghidra_compat.h`) so `clangd` and `zig cc` resolve every translation unit without manual C hand-patching.
