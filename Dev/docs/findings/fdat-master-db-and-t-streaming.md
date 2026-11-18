# `FDAT` Master Boot Database, `.T` Streaming & Media Decoding (`SLUS-00158`)

**Findings ID:** `fdat-master-db-and-t-streaming` · **Parent Hub:** [Dev/docs/FINDINGS.md](../FINDINGS.md) · **Related Specs:** [world-fdat-zones-and-cells.md](../specifications/world-fdat-zones-and-cells.md) · [audio-vab-and-seq.md](../specifications/audio-vab-and-seq.md) · **Unpacker:** [psx_kf_unpack.py](../../scripts/psx_kf_unpack.py)

This empirical report documents the sector-indexed `/CD/COM/*.T` container family (`2,236` total slots across `7` packs), the `FDAT.T` zone triplet and `FDAT[48]` `9`-section boot database decoded by `kf_game_mount_t_archives` (`0x80015dd4`), the runtime `kf_game_step_area_load_fsm` (`0x8001689c`) loader, the `VAB.T` `.vh` `<IIIHHHHBBBBI` header fix, and `BASLUS-00158` Memory Card framing.

---

## 1. Complete Inventory of `/CD/COM/*.T` Sector Packs & Companion Media

Every `.T` pack in `/CD/COM/` begins with a little-endian `KfTArchiveHeader` (`u16 entry_count` followed by `u16 sector_offsets[entry_count + 1]`). Entry `i` spans byte range `[sector_offsets[i] * 2048, sector_offsets[i + 1] * 2048)` and `sector_offsets[entry_count] * 2048 == file_size`. Empty or unused slots satisfy `sector_offsets[i + 1] == sector_offsets[i]`.

| Disc Asset | Bytes | Slots | Active | Verified Payload Breakdown & Empirical Notes |
| :--- | ---: | ---: | ---: | :--- |
| `CD/COM/FDAT.T` | `1,992,704` | `70` | `45` | Zones `0..7` (`0..23`) + `10` (`30..32`), `FDAT[47]` VRAM atlas, `FDAT[48]` boot DB, `FDAT[49..66]` view-models |
| `CD/COM/ITEM.T` | `11,110,400` | `548` | `403` | `103` `.tmd` 3D item meshes (`ver = 0x41`) + `300` `.tim` textures/icons |
| `CD/COM/MO.T` | `5,693,440` | `448` | `405` | `405` `KfMoHeader` animated monster/NPC rigs (keyframe table + embedded `.tmd`) |
| `CD/COM/RTIM.T` | `4,304,896` | `75` | `72` | `72` `KfRtimHeader` (`16` B = `RECT src_rect` + `RECT dst_rect`) VRAM pixel packs |
| `CD/COM/RTMD.T` | `1,083,392` | `9` | `9` | `9` multi-object zone static geometry `.tmd` bundles (`18` objects in `RTMD[0]`) |
| `CD/COM/TALK.T` | `13,197,312` | `755` | `379` | `379` dialogue/UI `.tim` cards (plus embedded sub-TIM cards where scanned) |
| `CD/COM/VAB.T` | `3,768,320` | `331` | `122` | `56` `pBAV` `.vh` headers + `56` paired ADPCM `.vb` bodies + `10` `pQES` `.seq` tracks |
| `CD/FN.D` | `1,188` | — | `58` | `2`-line header (`01 004 045 2 ...`) + `58` fixed-width CP932 item/key labels |
| `OP/OP.D`, `OP/OPU.D` | `552,344` ea | — | `2` | `16`-bpp `300x121` title `.TIM` images (`vram_x=640, vram_y=256`, `72,620`-B `.tim` in sector-padded wrapper) |
| `OP/OP0..2.S`, `ED0..1.S` | `206,920,544` | — | `5` | Mode 2 Form 2 `2,336`-B XA sectors (`88,579` sectors total, `320x240` `0x80010160` MDEC at `+8`) |

### `OP/*.S` MDEC Movie Stream Geometry

| File | Bytes | `2,336`-B Sectors | Frame Header Offset | Magic | Chunks / Frame | Dimensions |
| :--- | ---: | ---: | ---: | :--- | ---: | :--- |
| `OP/OP0.S` | `3,417,568` | `1,463` | `+8` | `0x80010160` | `9` | `320 x 240` |
| `OP/OP1.S` | `6,650,592` | `2,847` | `+8` | `0x80010160` | `9` | `320 x 240` |
| `OP/OP2.S` | `38,494,944` | `16,479` | `+8` | `0x80010160` | `14` | `320 x 240` |
| `OP/ED0.S` | `60,042,208` | `25,703` | `+8` | `0x80010160` | `14` | `320 x 240` |
| `OP/ED1.S` | `98,315,232` | `42,087` | `+8` | `0x80010160` | `14` | `320 x 240` |

- **Runtime Slot Mounting (`kf_game_open_t_archive_slot @ 0x800185a0`):** `GAME.EXE` maps `KF_T_MO=0`, `KF_T_RTMD=1`, `KF_T_RTIM=2`, `KF_T_TALK=3`, `KF_T_VAB=4`, `KF_T_FDAT=5`, and `KF_T_ITEM=6` into `g_kf_t_archive_slots[16]` (`KfTArchiveSlot`, `0x0c` B: `u16 *sector_offsets`, `CdlLOC start_loc`, `u32 total_size`).
- **Entry Size Invariant (`kf_game_t_archive_get_entry_size @ 0x80018164`):** Computes `(sector_offsets[entry_idx + 1] - sector_offsets[entry_idx]) * 2048` directly, verified in [parity_abi_and_media_tests.c](../../scripts/d4_harness/parity_abi_and_media_tests.c).

---

## 2. `FDAT.T` Architecture: Zone Triplets & `FDAT[48]` Master Boot Database

Prior assumptions looked for a standalone `MAG.T` file on disc; inspecting `/CD/COM/` and `kf_game_mount_t_archives` (`0x80015dd4`) proved `MAG.T` does not exist. All core gameplay lookup tables reside in **`FDAT.T[48]` (`0x30`)**, loaded once at `GAME.EXE` startup (`kf_world_fdat.py`).

### 2.1 Map Zone Triplets (`Zones 0..7` at Slots `0..23`, `Zone 10` at Slots `30..32`)

| Zone | Slots (`3z..3z+2`) | Slot `3z` Bytes | Slot `3z+1` Bytes | Slot `3z+2` Bytes | Verified Payload Contract |
| :--- | :--- | ---: | ---: | ---: | :--- |
| `Zone 0` | `0, 1, 2` | `67,584` | `28,672` | `4,096` | `0xfa00` `KfMapCell[6400]`; `4` secs `[12992, 3200, 8400, 2048]`; VRAM |
| `Zone 1` | `3, 4, 5` | `69,632` | `28,672` | `8,192` | `0xfa00` `KfMapCell[6400]`; `4` secs `[12992, 3200, 8400, 2048]`; VRAM |
| `Zone 2` | `6, 7, 8` | `69,632` | `28,672` | `4,096` | `0xfa00` `KfMapCell[6400]`; `4` secs `[12992, 3200, 8400, 2048]`; VRAM |
| `Zone 3` | `9, 10, 11` | `69,632` | `28,672` | `6,144` | `0xfa00` `KfMapCell[6400]`; `4` secs `[12992, 3200, 8400, 2048]`; VRAM |
| `Zone 4` | `12, 13, 14` | `67,584` | `28,672` | `8,192` | `0xfa00` `KfMapCell[6400]`; `4` secs `[12992, 3200, 8400, 2048]`; VRAM |
| `Zone 5` | `15, 16, 17` | `67,584` | `28,672` | `6,144` | `0xfa00` `KfMapCell[6400]`; `4` secs `[12992, 3200, 8400, 2048]`; VRAM |
| `Zone 6` | `18, 19, 20` | `69,632` | `28,672` | `6,144` | `0xfa00` `KfMapCell[6400]`; `4` secs `[12992, 3200, 8400, 2048]`; VRAM |
| `Zone 7` | `21, 22, 23` | `65,536` | `28,672` | `8,192` | `0xfa00` `KfMapCell[6400]`; `4` secs `[12992, 3200, 8400, 2048]`; VRAM |
| `Zone 10` | `30, 31, 32` | `67,584` | `28,672` | `6,144` | `0xfa00` `KfMapCell[6400]`; `4` secs `[12992, 3200, 8400, 2048]`; VRAM |

*(Slots `24..29`, `33..46`, `56..57`, and `67..69` are zero-length empty slots in `FDAT.T`.)*

### 2.2 `FDAT[47]`, `FDAT[48]` (`110,592` B, `9` Sections), and `FDAT[49..66]` View-Models

- **`FDAT[47]` (`0x2f`, `503,808` B):** Global resident VRAM texture/CLUT atlas stream loaded via `kf_game_load_rtim_to_heap(5, 0x2f)` (`139` embedded `0x00000010` TIM headers detected across the pack).
- **`FDAT[48]` (`0x30`, `110,592` B):** Loaded into `&g_kf_game_bss_table_base_8009bfe4` and unpacked sequentially across `9` `[u32 byte_len][payload]` blocks by `kf_game_mount_t_archives` (`0x80015dd4`):

| Section | Offset | Payload Bytes | Destination Symbol & Address | Decoded Struct / Purpose |
| ---: | ---: | ---: | :--- | :--- |
| `0` | `0` | `7,680` | `g_kf_map_obj_def_table` (`0x80175914`) | `KfMapObjDef[320]` (`320 * 0x18` B) |
| `1` | `7,684` | `1,232` | `g_kf_magic_def_table` (`0x801c7fbc`) | `KfMagicDef[18]` (`1,224` B) + `8`-B trailer |
| `2` | `8,920` | `2,048` | `g_kf_game_bss_table_base_801d9ccc` | `64 * 0x20` B (`KfItemDef`-stride table near `0x801d9a2c`) |
| `3` | `10,972` | `1,200` | `g_kf_game_bss_u16_8007682c` | `LevelUpGrowth[100]` (`100 * 12` B/level table) |
| `4` | `12,176` | `1,664` | `g_kf_game_bss_table_base_8019c5ec` | Spell / shop or progression parameter table |
| `5` | `13,844` | `2,816` | `g_kf_game_ro_table_base_800679a0` | Resident read-only lookup table (`GAME.EXE` `.data`) |
| `6` | `16,664` | `2,560` | `g_kf_game_bss_s16_801989d8` | Audio / SFX or combat table |
| `7` | `19,228` | `6,280` | `g_kf_game_bss_table_base_800fb014` | Base `.TMD` pack mounted via `kf_game_mo_mount_tmd_pack(0, ...)` |
| `8` | `25,512` | `83,540` | `g_kf_game_bss_table_base_800864e4` | Large `.TMD` pack mounted via `kf_game_mo_mount_tmd_pack(0x28, ...)` |

- **`FDAT[49..66]` (`0x31 + magic_id`, `18` Slots):** `kf_game_player_load_magic_def` (`0x80026210`) streams `FDAT[0x31 + magic_id]` and mounts it via `kf_game_tmd_mount_dynamic_slot(0x20, ...)` for equipped first-person weapons and spell view-models (`16` populated slots; `56..57` empty).

### 2.3 Weapon & Spell View-Model Slots (`FDAT[49..66]`, `kf_game_player_load_magic_def @ 0x80026210`)

```c
/* Clean-room summary of kf_game_player_load_magic_def (0x80026210) */
if (magic_id != 0xff) {
    g_kf_player_equipped_weapon_ptr = &g_kf_magic_def_table[magic_id];
    kf_game_stream_t_entry(KF_T_FDAT, (u32)magic_id + 0x31, g_kf_player_weapon_anim_ptr);
    kf_game_tmd_mount_dynamic_slot(0x20, g_kf_player_weapon_anim_ptr);
}
```

| `FDAT.T` Slot | `magic_id` | Padded Chunk (B) | Header Size Word | Slot Status |
| ---: | ---: | ---: | :--- | :--- |
| `49` (`0x31`) | `0` | `14,336` | `13,380` (`0x3444`) | Active view-model pack |
| `50` (`0x32`) | `1` | `12,288` | `11,332` (`0x2c44`) | Active view-model pack |
| `51` (`0x33`) | `2` | `22,528` | `22,184` (`0x56a8`) | Active view-model pack |
| `52` (`0x34`) | `3` | `24,576` | `24,352` (`0x5f20`) | Active view-model pack |
| `53` (`0x35`) | `4` | `24,576` | `23,060` (`0x5a14`) | Active view-model pack |
| `54` (`0x36`) | `5` | `22,528` | `20,592` (`0x5070`) | Active view-model pack |
| `55` (`0x37`) | `6` | `22,528` | `21,360` (`0x5370`) | Active view-model pack |
| `56..57` | `7..8` | `0` | `—` | Empty (`sector_offsets[i+1] == sector_offsets[i]`) |
| `58` (`0x3a`) | `9` | `38,912` | `37,696` (`0x9340`) | Active view-model pack |
| `59` (`0x3b`) | `10` | `24,576` | `23,736` (`0x5cb8`) | Active view-model pack |
| `60` (`0x3c`) | `11` | `18,432` | `17,940` (`0x4614`) | Active view-model pack |
| `61` (`0x3d`) | `12` | `30,720` | `29,772` (`0x744c`) | Active view-model pack |
| `62` (`0x3e`) | `13` | `36,864` | `34,836` (`0x8814`) | Active view-model pack |
| `63` (`0x3f`) | `14` | `43,008` | `41,196` (`0xa0ec`) | Active view-model pack |
| `64` (`0x40`) | `15` | `63,488` | `61,888` (`0xf1c0`) | Active view-model pack |
| `65` (`0x41`) | `16` | `18,432` | `16,484` (`0x4064`) | Active view-model pack |
| `66` (`0x42`) | `17` | `28,672` | `27,684` (`0x6c24`) | Active view-model pack |

---

## 3. Area-Load FSM (`kf_game_step_area_load_fsm @ 0x8001689c`)

When `g_kf_scene_control.state == 1`, `kf_game_step_area_load_fsm` advances zone transitions asynchronously across `6` active phases (`0xf0` acts as async DMA wait barrier):

1. **Phase `0`:** Clears active `g_kf_map_obj_table` slots (`396` entries, `0x44` stride) and queues `FDAT[next_map * 3]` (`KfMapCell[6400]` + map cell extension).
2. **Phase `1`:** Copies `64,000` B into `g_kf_map_cells`, copies `6,144` B (`0x600` words) into `0x801d8484`, shifts world coordinates if `fade_r != 0x7f`, and queues `FDAT[next_map * 3 + 2]` (zone VRAM stream).
3. **Phase `2`:** Queues `FDAT[next_map * 3 + 1]` (`[12992, 3200, 8400, 2048]`) into `&g_kf_fdat_load_hdr` (`0x801b6fa8`).
4. **Phase `3`:** Queues `RTMD[next_bgm]` (when `!= 0xff`), releases old entity/object 3D slots, copies `0xcb0` words (`12,992` B) into `g_kf_entity_def_table`, invokes `kf_game_entity_relocate_anim_tables()`, `kf_game_entity_update_vis_reset()`, `kf_game_obj_stamp_map_cells()`, `kf_game_gfx_emit_drop_sparkles()`, and replays saved deltas via `kf_game_save_apply_zone_deltas(next_map)`.
5. **Phase `4 -> 5 -> 6`:** Queues `RTIM[next_vab]`, fades active BGM over `0x3c` ticks (`kf_game_snd_set_reverb_pan_1838`), loads new `VAB` (`next_env + 1`) and `SEQ` (`VAB[next_fade_mode % 100 + 0x140]`), starts playback, and clears `g_kf_scene_control.state = 0`.

---

## 4. `VAB.T` `.vh` Header Bug Fix, `RTIM`/`RTMD`, `MO.T` & `BASLUS-00158` Saves

### 4.1 `VAB.T` `.vh` `<IIIHHHHBBBBI` Unpack Fix ([kf_audio_vab_seq.py](../../scripts/kf_audio_vab_seq.py))

Legacy `psx_kf_unpack.py` unpacked 32-byte `pBAV` headers past magic `"pBAV"` using `<IIIIIIHHH`, consuming `mvol`/`mpan`/`attr` bytes inside a shifted integer and producing impossible counts (`programs=16511`). Unpacking at `+4` with **`<IIIHHHHBBBBI`** yields exact PS1 soundbank headers across all `56` `.vh` entries (`56` `.vb` ADPCM bodies + `10` `pQES` `SEQ`s):

| `VAB.T` Slot | Format | `ver` | `vid` | `fsize` (B) | `res_sys` | `programs` | `tones` | `vags` | `mvol` / `mpan` |
| ---: | :--- | ---: | ---: | ---: | :--- | ---: | ---: | ---: | :--- |
| `0` | `pBAV` `.vh` | `6` | `0` | `142,912` | `0xeeee` | `2` | `23` | `22` | `127` / `64` |
| `2` | `pBAV` `.vh` | `6` | `0` | `162,304` | `0xeeee` | `9` | `25` | `12` | `127` / `64` |
| `4` | `pBAV` `.vh` | `6` | `0` | `161,072` | `0xeeee` | `9` | `14` | `11` | `127` / `64` |
| `6` | `pBAV` `.vh` | `6` | `0` | `158,192` | `0xeeee` | `12` | `15` | `11` | `127` / `63` |
| `8` | `pBAV` `.vh` | `6` | `0` | `159,456` | `0xeeee` | `7` | `13` | `13` | `127` / `64` |

- **`pQES` `SEQ` Music Tracks (`10` slots, e.g. `320..324`):** Big-endian `>4sIHBBB` header after magic `"pQES"` yields `version = 1`, `resolution = 480` PPQN, and `24`-bit tempo values (`821,917`, `689,655`, `1,016,949`, `740,740`, `428,571` microseconds/quarter-note).

### `VabHdr` (`32`-Byte Header) & `pQES` Field Layout

| Offset | Field (`<IIIHHHHBBBBI`) | Size | Verified `VAB.T[0]` Value | Legacy `<IIIIIIHHH` Defect |
| :--- | :--- | ---: | :--- | :--- |
| `+0x00` | `form[4]` (`"pBAV"`) | `4` B | `"pBAV"` (`0x56414270`) | Matched magic |
| `+0x04` | `ver` (`u32`) | `4` B | `6` | Matched |
| `+0x08` | `vid` (`u32`) | `4` B | `0` | Matched |
| `+0x0c` | `fsize` (`u32`) | `4` B | `142,912` B (`0x022e40`) | Misread as `waveform_bytes` |
| `+0x10` | `res_sys` (`u16`) | `2` B | `0xeeee` | Merged into `u32` |
| `+0x12` | `ps` (`u16` program count) | `2` B | `2` | Merged with `res_sys` -> `16511` |
| `+0x14` | `ts` (`u16` tone count) | `2` B | `23` | Misaligned by 2 bytes |
| `+0x16` | `vs` (`u16` VAG count) | `2` B | `22` | Misaligned by 4 bytes |
| `+0x18..+0x1b` | `mvol`, `mpan`, `attr1`, `attr2` | `4` B | `127`, `64`, `0`, `0` | Consumed into shifted ints |
| `+0x1c` | `reserved2` (`u32`) | `4` B | `0xffffffff` | Trailing header sentinel |

### 4.2 `RTIM.T`, `RTMD.T`, `MO.T` & `BASLUS-00158` Memory Card Checksum

- **`RTIM.T` (`75`/`72`) & `RTMD.T` (`9`/`9`):** `RTIM` packs lead with `KfRtimHeader` (`16` B = `RECT src_rect` + `RECT dst_rect`; `RTIM[0]` = `(448, 510, 16, 1)`) uploaded to PS1 VRAM in `32 KB` slices (`kf_game_upload_rtim_vram_queue @ 0x80016fc8`). `RTMD[0]` opens with `u32 count = 0x12` (`18` objects) and offset/attribute pairs (`0x0, 0x12, 0xb9, 0x1a80, ...`).
- **`MO.T` (`448`/`405`):** Opens with `KfMoHeader` (`0x14` B: `total_size`, `anim_count`, `tmd_offset`, `keyframe_table_offset`, `anim_table_offset`; `MO.T[0]`: `total_size=0x0a64`, `anim_count=4`, `anim_table_offset=0x14`) embedding a standard `0x41` `.tmd` mesh.
- **Memory Card Saves (`BASLUS-00158`, `0x4000` B = `2` MC blocks, [kf_save_memcard.py](../../scripts/kf_save_memcard.py)):** `KfSaveHeader` (`0x400` B: `"SC"` at `+0x00`, `icon_type=0x13` `3`-frame `16`-color CLUT icon, `block_count=2`, `64`-B Shift-JIS title at `+0x04`, `+0x200` `s32 checksum`) precedes a `0x3c00`-B payload summed byte-for-byte by `kf_game_mc_checksum_payload` (`0x80023dd0`), packing `10` zone-delta heap offsets via `kf_game_save_pack_zone_offsets` (`0x800491fc`).

```c
/* Exact byte-sum checksum over 0x3c00 save payload (kf_game_mc_checksum_payload @ 0x80023dd0) */
s32 sum = 0;
for (s32 i = 0; i < 0x3c00; ++i) {
    sum += (s32)payload[i];
}
```
