# Stage 2: LP32 Data Types and Global Symbol Mapping

- **Track:** `kings-field` (`ps1` / `native_ghidra_c`, ABI `ps1-mipsel`, `pointer_bytes=4`)
- **Stage 2 Verdict:** `D2` & `S2` verified (`1,549` mapped globals, `4` domain type headers, `46` structs, `3` enums)

## 1. Type Header Architecture (`schemas/types/` & `readable/include/types/`)

[kingsfield_types.h](../../schemas/kingsfield_types.h) serves as the `LP32` umbrella header over four modular domain headers (plus callback typedefs `KfVoidCallback` and `KfIntCallback`) with neutral PS1 hardware/ABI comments:

| Header | Lines | Structs | Enums | Key Recovered Layouts (`LP32` Byte Size) |
| :--- | ---: | ---: | ---: | :--- |
| [primitives_and_sdk.h](../../schemas/types/primitives_and_sdk.h) | `273` | `27` | `0` | `RECT` (`0x08`), `DISPENV` (`0x14`), `DRAWENV` (`0x5c`), `MATRIX` (`0x20`), `VECTOR` (`0x10`), `SVECTOR` (`0x08`), `CdlLOC` (`0x04`), `CdlFILE` (`0x18`), `DIRENTRY` (`0x28`), `EXEC` (`0x3c`), `SpuVoiceAttr` (`0x40`), `VagAtr` (`0x20`) |
| [kf_containers_and_io.h](../../schemas/types/kf_containers_and_io.h) | `102` | `8` | `2` | `KfExeSelector`, `KfTArchiveId`, `KfTArchiveSlot` (`0x0c`), `KfTArchiveHeader` (`0x04`), `KfFdatHeader` (`0x04`), `KfMoHeader` (`0x14`), `KfRtimHeader` (`0x10`), `KfItemDef` (`0x20`), `KfMagicDef` (`0x44`), `KfSaveHeader` (`0x400`) |
| [kf_world_and_render.h](../../schemas/types/kf_world_and_render.h) | `145` | `8` | `0` | `KfGfxEnv` (`0xe0`), `KfCameraState` (`0x34`), `KfSceneControl` (`0x1c`), `KfMapCell` (`0x0a`), `KfMapObjDef` (`0x18`), `KfMapObjState` (`0x44`), `KfWorldDrop` (`0x18`), `KfTextureAnimSlot` (`0x18`) |
| [kf_actor_combat_ui.h](../../schemas/types/kf_actor_combat_ui.h) | `182` | `3` | `1` | `KfEntityKind`, `KfEntityDef` (`0x78`), `KfEntityState` (`0x7c`), `KfPlayerState` (`0x160`) |

## 2. Mapped Global Symbol Inventory (`schemas/globals_map.json`)

- **Total mapped entries:** `1,549` (`310` `high` confidence, `1,239` `medium` confidence).
- **Kind breakdown:** `1,257` `standalone`, `292` `struct_member` (all verified on 32-bit `LP32` offsets inside `d4_parity_runner.exe`).
- **Declarations in `readable/include/kingsfield_globals.h`:** `1,660` lines (`1,549` mapped + `107` raw fallback declarations).

| Scope (`program_scope`) | Domain | Standalone | Struct Member | Total |
| :--- | --- | ---: | ---: | ---: |
| `GAME.EXE` | `module_game` | `624` | `290` | `914` |
| `OPEN.EXE` | `module_open` | `324` | `0` | `324` |
| `END.EXE` | `module_end` | `297` | `0` | `297` |
| `resident` (`SLUS_001.58`) | `core` | `12` | `2` | `14` |
| **Total** | — | **`1,257`** | **`292`** | **`1,549`** |

## 3. Anchored Parent Struct Blocks (`struct_member` Roots)

Thirteen recovered base addresses anchor the `292` struct-member globals:

| Parent Address | Anchored Struct / Subsystem | Members |
| :--- | --- | ---: |
| `0x80010274` | `g_kf_boot_exec_hdr` (`EXEC` overlay loader header, resident) | `2` |
| `0x8016c544` | `g_kf_entity_table[200]` (`KfEntityState`, `0x7c` stride) | `19` |
| `0x80172624` | `g_kf_entity_def_table[40]` (`KfEntityDef`, `0x78` stride) | `25` |
| `0x80175914` | `g_kf_map_obj_def_table[320]` (`KfMapObjDef`, `0x18` stride) | `16` |
| `0x80177714` | `g_kf_map_obj_table[396]` (`KfMapObjState`, `0x44` stride) | `23` |
| `0x8017e05c` | `g_kf_scene_control` (`KfSceneControl`) | `19` |
| `0x8018e0ac` | `g_kf_gfx_env` (`KfGfxEnv` double-buffered `DRAWENV`/`DISPENV`) | `15` |
| `0x80192d58` | `g_kf_tex_anim_slots[8]` (`KfTextureAnimSlot`, `0x18` stride) | `1` |
| `0x80192e78` | `g_kf_camera_state` (`KfCameraState`) | `13` |
| `0x80195174` | `g_kf_world_drop_table[128]` (`KfWorldDrop`, `0x18` stride) | `1` |
| `0x80199414` | `g_kf_player_state` (`KfPlayerState`, `0x160` bytes) | `148` |
| `0x801c7fbc` | `g_kf_magic_def_table[18]` (`KfMagicDef`, `0x44` stride) | `8` |
| `0x801c8484` | `g_kf_map_cells[6400]` (`KfMapCell`, `80x80` dual-layer map) | `2` |
