# Stage 3: Function Catalog and Readable Source Tree

- **Track:** `kings-field` (`ps1` / `native_ghidra_c`)
- **Stage 3 Verdict:** `D3` & `S3` verified (`1,632 / 1,632` non-SDK functions cataloged, `0` failed decompilations, `0` banned names, `0` placeholder params)

## 1. Per-Binary Function Coverage (`schemas/call_graph.json` & `schemas/functions_catalog.json`)

All `1,757` extracted functions span the resident bootloader plus three runtime overlay executables (`max_wave = 25`; `2` small 4-node audio SEQ SCC cycles in `OPEN.EXE` and `END.EXE`):

| Program | Base Address | Non-SDK Cataloged | SDK / CRT | Total | Primary Top-Wave Entry Points |
| :--- | --- | ---: | ---: | ---: | --- |
| `SLUS_001.58` | `0x80010000` | `4` | `9` | `13` | `kf_slus_crt0_start` (`0x80010128`, w0), `kf_slus_main_exec_loop` (`0x80010038`, w1) |
| `OPEN.EXE` | `0x80011000` | `387` | `31` | `418` | `kf_open_entry_point` (`0x80013db8`, w12), `kf_open_main` (`0x80011ae0`, w11) |
| `GAME.EXE` | `0x80011000` | `898` | `56` | `954` | `kf_game_entry_boot` (`0x8004a628`, w25), `kf_game_main_loop` (`0x8001369c`, w23), `kf_game_player_tick_master` (`0x8002a550`, w22) |
| `END.EXE` | `0x80011000` | `343` | `29` | `372` | `kf_end_entry_point` (`0x80011cb4`, w11), `kf_end_main` (`0x800119a4`, w10) |
| **Total** | — | **`1,632`** | **`125`** | **`1,757`** | **100% named and typed (`0` `FUN_*` / `param_*`)** |

## 2. Domain Distribution (`schemas/functions_catalog.json`)

| Domain | Function Count | Programs Covered |
| :--- | ---: | --- |
| `module_open` | `387` | `OPEN.EXE` |
| `module_end` | `343` | `END.EXE` |
| `module_game` | `202` | `GAME.EXE` |
| `audio` | `191` | `GAME.EXE` |
| `render_gfx` | `190` | `GAME.EXE` |
| `core` | `119` | `SLUS_001.58` (`4`), `GAME.EXE` (`115`) |
| `io_storage` | `90` | `GAME.EXE` |
| `ui_hud` | `82` | `GAME.EXE` |
| `input_save` | `28` | `GAME.EXE` |
| **Total** | **`1,632`** | `SLUS_001.58`, `OPEN.EXE`, `GAME.EXE`, `END.EXE` |

## 3. Topological Wave Stratification

Bottom-up wave indexing across `wave 0..25`:

- `wave 0..3`: `1,192` functions (`569` at `w0`, `329` at `w1`, `203` at `w2`, `91` at `w3`) covering math primitives, CD/BCD helpers, GTE transforms, SPU/VAB utilities, and state leaf setters.
- `wave 4..9`: `329` functions (`87`, `85`, `66`, `42`, `27`, `22`) covering map cell subdivision, TIM/TMD/MO loaders, entity AI, and menu renderers.
- `wave 10..25`: `111` functions spanning overlay main loops (`kf_open_main`, `kf_end_main`), SEQ event dispatchers, combat/world interaction, and top-level boot (`kf_game_entry_boot`, `w25`).

## 4. Multi-Tier C Tree, `27`-Module Coalescing & Normalization (`materialize_decomp_tiers.py` & `patch_ps1_reexport_and_compat.py`)

[materialize_decomp_tiers.py](../../scripts/materialize_decomp_tiers.py) preserves the `259` structured Ghidra chunks inside `Corpus/tiers/D2_Structured/` (`src/core/core_01.c`, `overlays/{OPEN,GAME,END}.EXE/*_NN.c`, `sdk/sdk_01..05.c`) alongside `Corpus/tiers/D1_Raw/` (`2,064` raw exports), then coalesces all `1,757` functions (`1,632` game + `125` SDK, `0` `DECOMPILE FAILED` markers) into **`27` cohesive logical `.c` modules** (`39` total files with headers) across `Corpus/tiers/D3_Mapped/` and `Corpus/readable/`:

- `src/boot_slus/` (`1`): `slus_boot_dispatcher.c` (`4` resident `SLUS_001.58` functions)
- `src/game_core_and_math/` (`2`): `game_main_and_sys.c` (`75`), `game_fixed_math.c` (`48`)
- `src/game_cd_and_archives/` (`2`): `game_cd_and_t_archives.c` (`88`), `game_save_and_memcard.c` (`23`)
- `src/game_world_and_entities/` (`3`): `game_world_map_and_props.c` (`51`), `game_entity_and_ai.c` (`55`), `game_player_and_combat.c` (`102`)
- `src/game_render_and_gfx/` (`2`): `game_gte_and_tmd_meshes.c` (`62`), `game_gpu_and_gfx_packets.c` (`117`)
- `src/game_ui_and_inventory/` (`1`): `game_ui_menus_and_hud.c` (`86`)
- `src/game_audio_spu/` (`2`): `game_audio_and_seq.c` (`143`), `game_spu_driver.c` (`48`)
- `src/open_title_and_fmv/` (`5`): `open_title_and_main.c` (`111`), `open_cd_and_mdec_str.c` (`78`), `open_gpu_and_draw.c` (`29`), `open_spu_voice_driver.c` (`45`), `open_ss_seq_driver.c` (`124`)
- `src/end_credits_and_str/` (`5`): `end_credits_and_main.c` (`99`), `end_cd_and_mdec_str.c` (`78`), `end_gpu_and_draw.c` (`18`), `end_spu_voice_driver.c` (`43`), `end_ss_seq_driver.c` (`105`)
- `sdk/` (`4`): `ps1_bios_kernel_and_events.c` (`47`), `ps1_cd_pad_and_memcard.c` (`22`), `ps1_gpu_and_gte.c` (`29`), `ps1_libc_and_mem.c` (`27`)
- `include/` (`12` headers): `kingsfield_types.h`, `kingsfield_globals.h`, `kingsfield_functions.h`, `ghidra_compat.h`, and `include/types/*.h`

[patch_ps1_reexport_and_compat.py](../../scripts/patch_ps1_reexport_and_compat.py) and [ps1_compat_helpers.py](../../scripts/ps1_compat_helpers.py) normalize raw decompiler artifacts (`SUBPIECE` / unaligned 3-byte loads, `undefined1[2|4]` stack casts, `void`-to-`uint32_t` return promotion where callers inspect the return register, call-site arity reconciliation, and missing PS1 MMIO/GTE/label compatibility externs in `ghidra_compat.h`). Hand-crafted zero-warning `D4_CleanSource` C translation units (`0` tells, `-Wall -Wextra`, staged in `Corpus/tiers/D4_CleanSource/`, clearing `D4a` Subsystem Parity) are scheduled for `v0.3.0`.
