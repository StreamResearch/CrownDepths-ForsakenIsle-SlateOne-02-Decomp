# KingsField-PlayStation — Architecture & Recovered Subsystems

**Version:** `0.1.0` (2026-11-14) · **Platform:** `ps1` (`SLUS-00158`, North America) · **Pipeline:** `native_ghidra_c` · **ABI:** `ps1-psyq-mipsel`

## 1. Graduation Pedigree & Clean-Room Boundary
- **Upstream R&D Incubator:** Graduated cleanly from `../../Personal/R&D/decomps/ps1/kings-field` after passing `D0`–`D4` and `S0`–`S4` gates using owned retail `SLUS-00158` media only.
- **Corpus Container (`gitignored`, `-xr!Corpus\*`):**
  - `Corpus/standalone/` (`12` SHA-256 baseline files locked in `Dev/schemas/standalone_integrity.json`; `6,297` files / `716,862,355` B, `IsReadOnly = true`).
  - `Corpus/readable/` (`268` manifest-tracked code/header/doc files: `259` `.c` translation units, LP32 headers, `SYMBOL_MAP.md`, `ARCHITECTURE_WALKTHROUGH.md`, `compile_commands.json`, `.clangd`; `clangd 23.1.0` `0` errors/warnings).
  - `Corpus/work/` (`d4_build/libkings_field_d4.a`, `260` ELF32 LE MIPS `.o` objects, `d4_parity_runner.exe`, Ghidra stage bundles).
- **Control Plane (`Git-tracked`):** `Dev/research.manifest.json`, `Dev/KingsField-PlayStation.code-workspace`, `Dev/schemas/`, `Dev/scripts/`, `Dev/docs/`.

## 2. Target Binaries & Trampoline Boot Topology
- **Resident Dispatcher (`SLUS_001.58`, `4,096` B):** Loaded at `0x80010000` (`t_size = 0x800`, `pc0 = 0x80010128`). `kf_slus_crt0_start` initializes the main heap at `0x800102b8` (`g_kf_boot_heap_base`), and `kf_slus_main_exec_loop` (`0x80010038`) chains `Load()` + `Exec()` via `g_kf_boot_exec_hdr` (`0x80010274`) using `g_kf_boot_next_exe_selector` (`0x800102f0`) and `g_kf_boot_intro_seen_flag` (`0x800102f8`) to swap `OPEN.EXE`, `GAME.EXE`, or `END.EXE` at `0x80011000`.

| Binary | Role | Base Address | `.text` Span / Size | Entry (`pc0`) | Game Funcs | SDK Funcs | Total |
| --- | --- | --- | --- | --- | ---: | ---: | ---: |
| `SLUS_001.58` | `primary` | `0x80010000` | `0x800` (`4,096` B file) | `0x80010128` | `4` | `9` | `13` |
| `OPEN.EXE` | `module` | `0x80011000` | `0x2e000` (`190,464` B file) | `0x80013db8` | `387` | `31` | `418` |
| `GAME.EXE` | `module` | `0x80011000` | `0x5e000` (`387,072` B file) | `0x8004a628` | `898` | `56` | `954` |
| `END.EXE` | `module` | `0x80011000` | `0x29000` (`169,984` B file) | `0x80011cb4` | `343` | `29` | `372` |
| **Total** | `4` PS-X EXEs | — | — | — | **`1,632`** | **`125`** | **`1,757`** |

## 3. Recovered Subsystem Domain Graph (`1,757` Functions / `1,549` Globals)
- **Topological Stratification (`Dev/schemas/call_graph.json`):** `26` waves (`0..25`), `0` failed decompilations, and `2` small 4-node audio SEQ SCC cycles in `OPEN.EXE` and `END.EXE`.
- **Stage 1 Program Clusters (`Dev/schemas/clusters.json`, `5` clusters):** `core` (`4`, `84` C lines), `module_open` (`387`, `14,327` C lines), `module_game` (`898`, `46,311` C lines), `module_end` (`343`, `11,738` C lines), `sdk` (`125`, `1,873` C lines).
- **Stage 3 Functional Domains (`Dev/schemas/functions_catalog.json`, `9` domains / `1,632` game functions):**

| Functional Domain | Functions | Covered Binaries / Primary Subsystem Scope |
| --- | ---: | --- |
| `module_open` | `387` | `OPEN.EXE` title, opening cinema (`OP*.S` MDEC), menu & memory card load flow |
| `module_end` | `343` | `END.EXE` ending/credits sequence & `320x240` (`0x140 x 0xf0`) STR/MDEC decoder |
| `module_game` | `202` | `GAME.EXE` dungeon state machine, combat math, entity AI, triggers & scene control |
| `audio` | `191` | `GAME.EXE` SPU voice management, `VAB` soundbanks & `SEQ` music playback |
| `render_gfx` | `190` | `GAME.EXE` PS1 GPU ordering tables (`OT`), GTE transforms, `MIMe` morphing & VRAM |
| `core` | `119` | `SLUS_001.58` (`4` bootloader) + `GAME.EXE` (`115` main loop, heap, frame/tick) |
| `io_storage` | `90` | `GAME.EXE` CD-ROM streaming, `/CD/COM/*.T` sector archive table loader |
| `ui_hud` | `82` | `GAME.EXE` gauges, inventory/equipment menus, dialogue cards & compass HUD |
| `input_save` | `28` | `GAME.EXE` `PAD` controller polling & `BASLUS-00158` Memory Card save checksums |

## 4. Readable C Tree & LP32 Cross-Compilation Layout
- `Corpus/readable/` isolates `259` `.c` translation units with `0` `DECOMPILE FAILED` markers: `src/core/core_01.c` (`1`), `overlays/OPEN.EXE/open_01..53.c` (`53`), `overlays/GAME.EXE/game_01..157.c` (`157`), `overlays/END.EXE/end_01..43.c` (`43`), and deduplicated PS1-SDK/BIOS stubs in `sdk/sdk_01..05.c` (`5`).
- `Dev/scripts/build_and_verify_d4.py` compiles all `259` `.c` units plus generated `globals_defs.c` via `zig cc` (`mipsel-freestanding-eabi`, `mips2`) into `260/260` `ELF32` LE `MIPS` `.o` files archived in `libkings_field_d4.a` (`1,841,082` B, `0` errors / `0` warnings) and links `10/10` live `x86-windows-gnu` LP32 host parity tests.

## 5. Downstream Stage 3 Link (`KingsFieldRecomp`)
- **Stage 3 Tier A Recomp:** [`../../Personal/KingsFieldRecomp`](../../Personal/KingsFieldRecomp/README.md) (`v0.1.3` / verified `R3`, Notion `<NOTION_ROOT_PAGE_ID>`) running on [`reStation v0.1.1`](../../Personal/reStation/README.md) + [`reEngine v0.1.1`](../../Personal/reEngine/README.md), linked via `downstreamProjects` while keeping `Corpus/` strictly confined here.
- **Notion Manual Page:** `Architecture & Engineering` (`<NOTION_ARCHITECTURE_PAGE_ID>`).
