# KingsField-PlayStation — Clean-Room Specifications & Data Contracts

**Version:** `0.1.0` (2026-11-14) · **Decomp Axis:** `D4/D4` · **Study Axis:** `S4/S4` · **Recomp Axis:** `R3/R3`

## 1. Manifest & Gate Schema (`Dev/research.manifest.json`)
- **Identity:** `researchId = "kings-field-play-station"`, `gameId = "kings-field"`, `researchAxis = "hybrid"`, `platform = "ps1"`, `pipelineFamily = "native_ghidra_c"`, `serialOrHash = "SLUS-00158"`, `abiProfile = "ps1-psyq-mipsel"`.
- **Paths & Links:** `deferredStandalonePath = "../Corpus/standalone"`, `customUnpackerScript = "Dev/scripts/psx_kf_unpack.py"`, `upstreamResearchPath = "../../Personal/R&D/decomps/ps1/kings-field"`, `downstreamProjects = ["../../Personal/KingsFieldRecomp"]`.

## 2. Recovered LP32 C Headers & Schema Contracts (`Dev/schemas/`)
- Umbrella header `Dev/schemas/kingsfield_types.h` defines callback typedefs (`KfVoidCallback`, `KfIntCallback`) and includes `4` modular LP32 headers (`46` structs, `21` typedefs, `3` enums, `93` tracked type sizes total):

| Header (`Dev/schemas/types/`) | Lines | Structs | Enums | Key Recovered Contracts (`LP32` Byte Size) |
| --- | ---: | ---: | ---: | --- |
| `primitives_and_sdk.h` | `273` | `27` | `0` | `RECT` (`0x08`), `DISPENV` (`0x14`), `DRAWENV` (`0x5c`), `MATRIX` (`0x20`), `VECTOR` (`0x10`), `SVECTOR` (`0x08`), `CdlLOC` (`0x04`), `CdlFILE` (`0x18`), `DIRENTRY` (`0x28`), `EXEC` (`0x3c`), `SpuVoiceAttr` (`0x40`), `VagAtr` (`0x20`) |
| `kf_containers_and_io.h` | `102` | `8` | `2` | `KfExeSelector`, `KfTArchiveId`, `KfTArchiveSlot` (`0x0c`), `KfTArchiveHeader` (`0x04`), `KfFdatHeader` (`0x04`), `KfMoHeader` (`0x14`), `KfRtimHeader` (`0x10`), `KfItemDef` (`0x20`), `KfMagicDef` (`0x44`), `KfSaveHeader` (`0x400`) |
| `kf_world_and_render.h` | `145` | `8` | `0` | `KfGfxEnv` (`0xe0`), `KfCameraState` (`0x34`), `KfSceneControl` (`0x1c`), `KfMapCell` (`0x0a`), `KfMapObjDef` (`0x18`), `KfMapObjState` (`0x44`), `KfWorldDrop` (`0x18`), `KfTextureAnimSlot` (`0x18`) |
| `kf_actor_combat_ui.h` | `182` | `3` | `1` | `KfEntityKind`, `KfEntityDef` (`0x78`), `KfEntityState` (`0x7c`), `KfPlayerState` (`0x160`) |

- **Machine-Validated JSON Ledgers:** `standalone_integrity.json` (`12` SHA-256 baseline entries), `call_graph.json` (`1,757` nodes), `clusters.json` (`5` program clusters), `globals_index.json` / `globals_map.json` (`1,549` entries), `anchor_functions.json` (`4` resident anchors), `functions_catalog.json` (`1,632` game functions across `4` Stage 3 shards), and `d4_build_report.json`.

## 3. Retail Container & Media Binary Contracts
- **`.T` Sector Archives (`/CD/COM/*.T`):** Little-endian `u16 entry_count` + `u16 sector_offsets[entry_count + 1]`; entry `i` spans `[sector_offsets[i] * 2048, sector_offsets[i + 1] * 2048)` and `sector_offsets[entry_count] * 2048 == file_size`: `FDAT.T` (`70` slots), `ITEM.T` (`548`), `MO.T` (`448`), `RTIM.T` (`75`), `RTMD.T` (`9`), `TALK.T` (`755`), `VAB.T` (`331`).
- **`CD/FN.D` (`1,188` B):** Fixed-width Shift-JIS (`cp932`) localized item/debug descriptor table (`58` entries).
- **`OP/*.S` (`OP0..OP2.S`, `ED0..ED1.S`):** Mode 2 Form 2 `2,336`-byte XA sectors carrying `320x240` (`0x140 x 0xf0`) MDEC headers (`0x80010160`) at byte offset `+8` (`9` or `14` chunks/frame).
- **Memory Card Save (`BASLUS-00158`):** `KfSaveHeader` (`0x400` B, `"SC"` magic, Shift-JIS title, `3`-frame CLUT icon, `+0x200` `checksum`) followed by `0x3c00`-byte checksummed gameplay payload.

## 4. Mapped Globals & Anchored Struct Roots (`1,549 / 1,549`)
`globals_map.json` resolves `1,257` standalone globals and `292` `struct_member` fields anchored on `13` parent bases (`GAME.EXE` `914`, `OPEN.EXE` `324`, `END.EXE` `297`, `SLUS_001.58` `14`):

| Symbol | Address | C Type | Role |
| --- | --- | --- | --- |
| `g_kf_boot_exec_hdr` | `0x80010274` | `EXEC` | Resident child PS-X EXE loader header (`s_addr`, `s_size`) |
| `g_kf_boot_next_exe_selector` | `0x800102f0` | `u8` | Next overlay target (`0=OPEN.EXE`, `1=GAME.EXE`, `2=END.EXE`) |
| `g_kf_entity_table` | `0x8016c544` | `KfEntityState[200]` | Active world monster/NPC/static entity instances (`0x7c` stride) |
| `g_kf_scene_control` | `0x8017e05c` | `KfSceneControl` | Map/BGM/VAB transition and fade timer state machine |
| `g_kf_gfx_env` | `0x8018e0ac` | `KfGfxEnv` | Double-buffered `DRAWENV`/`DISPENV` display environment (`0xe0` B) |
| `g_kf_camera_state` | `0x80192e78` | `KfCameraState` | First-person camera position, pitch/yaw/roll & grid origin |
| `g_kf_player_state` | `0x80199414` | `KfPlayerState` | Player XP, HP/MP, equipment, status timers & kinematics (`0x160` B) |
| `g_kf_map_cells` | `0x801c8484` | `KfMapCell[6400]` | `80x80` dual-layer floor/ceiling tile map (`64,000` B = `0xfa00`) |

## 5. Clean-Room Specification Contracts
- **IP & Corpus Boundary:** All specifications derive from deterministic static analysis and executable parity assertions without committing or redistributing retail binaries.
- **Spoke & Stage Navigation:** Granular per-stage engineering dossiers live under `Dev/docs/stages/01..04-*.md`, paired with machine-validated contracts in `Dev/schemas/`.

## 6. Verification Report Contract (`Dev/schemas/d4_build_report.json`)
- **Timestamp:** `verifiedAtUtc = "2026-11-14T08:16:49.623Z"` (`schemaVersion = 1`, `gameId = "kings-field"`).
- **Pass 1 (`mipsel-freestanding-eabi`, `mips2`):** `readableFiles = 259`, `compiledFiles = 259`, `totalObjects = 260`, `elf32MipsVerifiedObjects = 260`, `archiveFile = "work/d4_build/libkings_field_d4.a"`, `archiveBytes = 1841082`, `compilerErrors = 0`, `compilerWarnings = 0`.
- **Pass 2 (`x86-windows-gnu`, `LP32`):** `parityTarget = "x86-windows-gnu"`, `parityTestsPassed = 10`, `parityTestsTotal = 10`, `parityPassed = true`, `passed = true`.

## 7. Verification Gates Matrix (`Notion: <NOTION_SPECIFICATIONS_PAGE_ID>`)
| Gate | Tier Axis | Status | Primary Evidence |
| --- | --- | --- | --- |
| `D0` / `S0` | Corpus & SHA-256 | Verified | `Dev/schemas/standalone_integrity.json` (`12` baseline files) |
| `D1`–`D3` / `S1`–`S3` | Schemas, Catalog & `clangd` | Verified | `Dev/schemas/` + `Corpus/readable/` (`0` errors/warnings) |
| `D4` / `S4` | ELF32 MIPS & LP32 Parity | Verified | `Dev/schemas/d4_build_report.json` (`260/260` `.o`, `10/10` parity) |
| `R1`–`R3` | Downstream Native Recomp | Verified (`R3`) | `../../Personal/KingsFieldRecomp` (`v0.1.3` on `reStation v0.1.1`) |
| `D5` / `S5` / `R4`–`R5` | Byte-Match / NativeAOT | Planned | Future 1:1 ELF match & `.NET 10 NativeAOT` port milestones |
