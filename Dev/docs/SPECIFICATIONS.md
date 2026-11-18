# CrownDepths ForsakenIsle (SlateOne) 02 Decomp — Clean-Room Specifications & Data Contracts

**Version:** `0.2.0` (`2026-11-18`) · **Decomp Axis:** `D3` *(Re-Opened Honest Baseline, Goal: `D4`)* · **Study Axis:** `S4` *(Goal: `S5`)* · **Recomp Axis:** `R2` *(Playable; Goal: `R3` Pure Static)*

This routing index links the six specification spokes (`Dev/docs/specifications/`), the three empirical findings spokes (`Dev/docs/findings/`), their six pure-stdlib Python decoders (`Dev/scripts/`), and the machine-validated coverage ledger [`Dev/schemas/spec_coverage.json`](../schemas/spec_coverage.json) (`96 / 96` fields mapped, `unresolvedFieldCount: 0`).

---

## 1. Specification Spokes & Modular Decoders (`96 / 96` Fields Mapped)

| Specification Spoke | Parser Script | Scope & Verified Fields | Mapped Fields |
| :--- | :--- | :--- | ---: |
| [`t-archives-fnd-and-op-str.md`](specifications/t-archives-fnd-and-op-str.md) | [`kf_t_archives.py`](../scripts/kf_t_archives.py) | `.T` sector headers, `KfTArchiveSlot`, `0x12345678` checksums, `CD/FN.D`, `OP.D`/`OPU.D`, `OP/*.S` (`2,336`-B XA MDEC) | `16` |
| [`world-fdat-zones-and-cells.md`](specifications/world-fdat-zones-and-cells.md) | [`kf_world_fdat.py`](../scripts/kf_world_fdat.py) | `FDAT.T` zones `0..7` & `10`, `KfMapCell[6400]`, `FDAT[47]` (`500` RTIM), `FDAT[48]` `9`-section DB, `FDAT[49..66]` view-models | `16` |
| [`items-magic-stats-and-talk.md`](specifications/items-magic-stats-and-talk.md) | [`kf_items_magic_talk.py`](../scripts/kf_items_magic_talk.py) | `KfItemDef[64]`, `KfMagicDef[18]`, `ITEM.T` (`103` TMD + `300` TIM), `TALK.T` (`379` cards), dialogue VM `0xf0..0xff` | `16` |
| [`meshes-mo-rtmd-and-rtim.md`](specifications/meshes-mo-rtmd-and-rtim.md) | [`kf_meshes_mo_rtmd.py`](../scripts/kf_meshes_mo_rtmd.py) | `MO.T` (`108` anim + `297` static), `RTMD.T` (`240`-slot tile banks), `TMD` (`0x41`), `RTIM.T` (`KfRtimHeader`), `.TIM` | `16` |
| [`audio-vab-and-seq.md`](specifications/audio-vab-and-seq.md) | [`kf_audio_vab_seq.py`](../scripts/kf_audio_vab_seq.py) | `VAB.T` (`56` `.vh` `<IIIHHHHBBBBI` + `.vb` ADPCM), `ProgAtr`/`VagAtr`, VAG sizes, `10` `pQES` SEQ tracks | `16` |
| [`save-memcard-baslus00158.md`](specifications/save-memcard-baslus00158.md) | [`kf_save_memcard.py`](../scripts/kf_save_memcard.py) | `BASLUS-00158*` (`0x4000` B), `128 KiB` `.mcr` XOR parity, `KfSaveHeader`, `0x3c00`-B additive checksum | `16` |

---

## 2. Empirical Findings Spokes (`Dev/docs/findings/` via [FINDINGS.md](FINDINGS.md))

| Findings Spoke | Supporting Tools / Harness | Empirical & ABI Focus |
| :--- | :--- | :--- |
| [`four-exe-trampoline-and-ram-layout.md`](findings/four-exe-trampoline-and-ram-layout.md) | [`d4_harness/`](../scripts/d4_harness/), [`psx_kf_unpack.py`](../scripts/psx_kf_unpack.py) | `SLUS_001.58` trampoline loader, `OPEN`/`GAME`/`END.EXE` overlays, `2 MiB` RAM arena geometry |
| [`fdat-master-db-and-t-streaming.md`](findings/fdat-master-db-and-t-streaming.md) | [`kf_world_fdat.py`](../scripts/kf_world_fdat.py), [`kf_t_archives.py`](../scripts/kf_t_archives.py) | `FDAT[48]` `9`-section boot chain, async `.T` mode `0x10..0x40` queue, `32 KiB` RTIM DMA pacing |
| [`d3-reopen-and-mips-lp32-abi.md`](findings/d3-reopen-and-mips-lp32-abi.md) | [`build_and_verify_d4.py`](../scripts/build_and_verify_d4.py), [`verify_track_d4.py`](../scripts/verify_track_d4.py) | `D3` honest baseline re-opening, `MIPS32 LE LP32` ABI, `10/10` host parity harness, clean-room `.decomp` boundary |

---

## 3. Manifest, Clean-Room Schemas & LP32 Headers (`Dev/`)

- **Control Manifest:** [`Dev/research.manifest.json`](../research.manifest.json) (`version = "0.2.0"`, `gameId = "kings-field"`, `platformId = "ps1"`, `engineId = "reStation"`, `serialOrHash = "SLUS-00158"`, `currentDecompTier = "D3"`, `goalDecompTier = "D4"`, `d4ParityTier = "none"`, `currentStudyTier = "S4"`, `goalStudyTier = "S5"`, `currentRecompTier = "R2"`, `goalRecompTier = "R3"`, `currentPortTier = "none"`, `recompProjectPath = "../../Personal/KingsFieldRecomp"`).
- **Clean-Room Bundle Recipe:** [`Dev/schemas/decomp_recipe.json`](../schemas/decomp_recipe.json) (`moduleId = "crowndepths-forsakenisle-slateone-02"`, `packageFileName = "CrownDepths-ForsakenIsle-SlateOne-02.decomp"`, `compatibleEngineTrack = "0.2.x"`) exported by [`export_decomp_bundle.py`](../scripts/export_decomp_bundle.py).
- **Umbrella & Modular C Headers:** [`kingsfield_types.h`](../schemas/kingsfield_types.h) plus [`primitives_and_sdk.h`](../schemas/types/primitives_and_sdk.h), [`kf_containers_and_io.h`](../schemas/types/kf_containers_and_io.h), [`kf_world_and_render.h`](../schemas/types/kf_world_and_render.h), and [`kf_actor_combat_ui.h`](../schemas/types/kf_actor_combat_ui.h) (`46` structs, `21` typedefs, `3` enums, neutral PS1 hardware/ABI comments).
- **Machine-Validated JSON Ledgers:** [`spec_coverage.json`](../schemas/spec_coverage.json) (`96/96` mapped, `0` unresolved), [`standalone_integrity.json`](../schemas/standalone_integrity.json) (`schemaVersion: 2`, `23` required `disc/files/*` digests), [`call_graph.json`](../schemas/call_graph.json) (`1,757` nodes, `strings: []`), [`clusters.json`](../schemas/clusters.json) (`5` clusters), [`globals_map.json`](../schemas/globals_map.json) (`1,549` symbols), [`functions_catalog.json`](../schemas/functions_catalog.json) (`1,632` game functions), [`d4_build_report.json`](../schemas/d4_build_report.json), and [`s4_verify_report.json`](../schemas/s4_verify_report.json).

---

## 4. Core Resident Globals & Hardware Anchors (`1,549 / 1,549`)

`globals_map.json` resolves `1,257` standalone globals and `292` `struct_member` fields across `13` parent RAM bases (`GAME.EXE` `914`, `OPEN.EXE` `324`, `END.EXE` `297`, `SLUS_001.58` `14`):

| Symbol | Address | C Type | Role |
| :--- | :--- | :--- | :--- |
| `g_kf_boot_exec_hdr` | `0x80010274` | `EXEC` | Resident child PS-X EXE loader header (`s_addr`, `s_size`) |
| `g_kf_boot_next_exe_selector` | `0x800102f0` | `u8` | Next overlay target (`0=OPEN.EXE`, `1=GAME.EXE`, `2=END.EXE`) |
| `g_kf_t_archive_slots` | `0x801b6f48` | `KfTArchiveSlot[7]` | Mounted `/CD/COM/*.T` sector offset tables and `CdlLOC` bases |
| `g_kf_entity_table` | `0x8016c544` | `KfEntityState[200]` | Active world monster/NPC/static entity instances (`0x7c` stride) |
| `g_kf_scene_control` | `0x8017e05c` | `KfSceneControl` | Map/BGM/VAB transition and fade timer state machine |
| `g_kf_gfx_env` | `0x8018e0ac` | `KfGfxEnv` | Double-buffered `DRAWENV`/`DISPENV` display environment (`0xe0` B) |
| `g_kf_camera_state` | `0x80192e78` | `KfCameraState` | First-person camera position, pitch/yaw/roll & grid origin |
| `g_kf_player_state` | `0x80199414` | `KfPlayerState` | Player XP, HP/MP, equipment, status timers & kinematics (`0x160` B) |
| `g_kf_map_cells` | `0x801c8484` | `KfMapCell[6400]` | `80x80` dual-layer floor/ceiling tile map (`64,000` B = `0xfa00`) |

---

## 5. Verification Gates & Automated Test Suites

| Gate | Axis | Status | Primary Evidence |
| :--- | :--- | :--- | :--- |
| `D0` / `S0` | Corpus & SHA-256 | Verified | [`standalone_integrity.json`](../schemas/standalone_integrity.json) + [`psx_kf_unpack.py`](../scripts/psx_kf_unpack.py) |
| `D1`–`D3` / `S1`–`S3` | Schemas, Specs & Catalog | Verified | [`spec_coverage.json`](../schemas/spec_coverage.json) (`96/96`, `0` unresolved) + `Dev/scripts/tests/` |
| `D3` *(re-opened)* / `S4` | MIPS Archive, Parsers & `10/10` Parity | Verified | [`d4_build_report.json`](../schemas/d4_build_report.json) (`28` `.o`, `27` modules, `10/10` parity) + [`s4_verify_report.json`](../schemas/s4_verify_report.json) |
| `R1`–`R2` | Downstream Native Recomp | Verified (`R2` Playable; Goal `R3` Pure Static) | `recompProjectPath = "../../Personal/KingsFieldRecomp"` + clean-room `.decomp` exporter |
| `D4`–`D5` / `S5` / `R3`+ | Clean Source, Pure Static & Byte-Match | Planned (`v0.3.0+`) | Hand-written `D4_CleanSource` (`D4a`/`D4b`), `R3` Pure Static (`isPureStaticReady`) & `1:1` ELF byte parity |

Run all isolated parser and clean-room contract tests (`0` retail media required):

```powershell
python -B -m unittest discover -s Dev/scripts/tests -v
```
