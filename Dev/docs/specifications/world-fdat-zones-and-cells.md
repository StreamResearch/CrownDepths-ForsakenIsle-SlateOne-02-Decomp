# `FDAT.T` World Zones, Map Cells, `FDAT[48]` Master DB & View-Models (`SLUS-00158`)

**Specification ID:** `world-fdat-zones-and-cells` · **Reference Parser:** [`Dev/scripts/kf_world_fdat.py`](../../scripts/kf_world_fdat.py) · **Parent Index:** [`Dev/docs/SPECIFICATIONS.md`](../SPECIFICATIONS.md)

This specification defines the `45` active slots inside `CD/COM/FDAT.T` (`70` total slots, `1,992,704` bytes): `9` map zone triplets (zones `0..7` plus test zone `10`), the `FDAT[47]` global VRAM texture atlas, the `FDAT[48]` 9-section master boot database, and `FDAT[49..66]` (`18` weapon/spell view-model `.MO` packs).

---

## 1. Length-Prefixed Section Chain (`KfFdatHeader`)

Every data-packed slot in `FDAT.T` (`3*z`, `3*z+1`, `FDAT[48]`) encodes sequential blocks headed by a `4`-byte `KfFdatHeader` (`u32 section_size`):

| Offset | Size | Type | Field | Packing Rule |
| :--- | ---: | :--- | :--- | :--- |
| `pos + 0x00` | `4` | `u32` | `section_size` | Uncompressed payload length (`N` bytes) following this header |
| `pos + 0x04` | `N` | `u8[N]` | `payload` | Contiguous section data copied via `kf_game_mem_copy_u32` |
| `pos + 4 + N` | `4` | `u32` | `next_section_size` | Immediately adjacent next `KfFdatHeader` (`0` terminates variable chains) |

---

## 2. Map Zone Triplet Layout (`Zones 0..7` at `0..23` & `Zone 10` at `30..32`)

`kf_game_step_area_load_fsm` (`0x8001689c`) streams three sequential `FDAT.T` slots per zone `(3*z, 3*z+1, 3*z+2)`:

| Triplet Slot | Index Formula | Retail Byte Range | RAM Destination & Contents |
| :--- | :--- | :--- | :--- |
| Slot `0` (`Map`) | `3 * z` | `65,536..69,632` B | `sec[0]` (`64,000` B = `KfMapCell[6400]`) -> `0x801c8484`; `sec[1]` (`0x600` dwords window) -> `0x801d8484` |
| Slot `1` (`Actors`) | `3 * z + 1` | `28,672` B (all zones) | Fixed 4-section chain `[12992, 3200, 8400, 2048]` (`26,640` B payload + `16` B headers) |
| Slot `2` (`Callbacks`) | `3 * z + 2` | `4,096..8,192` B | Zone script/callback pointer table loaded into `0x8019f07c` (`g_kf_scene_callbacks`) |

### `KfMapCell` (`0x801c8484`, `80 x 80` Grid, `0x0A` B Stride = `64,000` B)

| Offset | Size | Type | Field | Role |
| :--- | ---: | :--- | :--- | :--- |
| `+0x00` | `1` | `u8` | `lower_tile_id` | Lower floor/wall `RTMD` tile template index (`0..255`) |
| `+0x01` | `1` | `u8` | `lower_elevation` | Signed/stepped lower layer vertical height |
| `+0x02` | `1` | `u8` | `lower_tex_flags` | Lower surface orientation/texture flags (masked `& 3` on load) |
| `+0x03` | `1` | `u8` | `lower_collision` | Lower layer walkability / wall collision bitmask |
| `+0x04` | `1` | `u8` | `lower_render_flags` | Lower layer visibility/clipping flags |
| `+0x05` | `1` | `u8` | `upper_tile_id` | Upper ceiling/bridge `RTMD` tile template index |
| `+0x06` | `1` | `u8` | `upper_elevation` | Upper layer vertical offset |
| `+0x07` | `1` | `u8` | `upper_tex_flags` | Upper surface orientation/texture flags |
| `+0x08` | `1` | `u8` | `upper_collision` | Upper layer collision bitmask |
| `+0x09` | `1` | `u8` | `upper_render_flags` | Upper layer visibility/clipping flags |

### Slot `3*z + 1` Four-Section Breakdown (`[12992, 3200, 8400, 2048]`)
1. **Section `0` (`12,992` B):** Loaded into `g_kf_entity_def_table` (`0x80172624`, `0xcb0` dwords) and relocated via `kf_game_entity_relocate_anim_tables`.
2. **Section `1` (`3,200` B):** Zone monster/NPC initial spawn array copied via `kf_game_entity_update_vis_reset`.
3. **Section `2` (`8,400` B):** Interactive map object/door/trap spawn placements stamped onto cells via `kf_game_obj_stamp_map_cells`.
4. **Section `3` (`2,048` B):** Initial `KfWorldDrop` pickup/chest item table uploaded via `kf_game_gfx_emit_drop_sparkles`.

### Area Transition FSM Phases (`kf_game_step_area_load_fsm @ 0x8001689c`)
- **Phase `0` -> `1`:** Streams `FDAT[3 * next_map]` asynchronously into `g_kf_fdat_load_hdr`, copies `16,000` dwords (`64,000` B) into `g_kf_map_cells` (`0x801c8484`), copies `0x600` trailing dwords into `0x801d8484`, and shifts active world entities (`kf_game_world_shift_all_entities`).
- **Phase `2` -> `3`:** Streams `FDAT[3 * next_map + 1]` and `FDAT[3 * next_map + 2]`, clears previous `200` entity slots and `396` map objects (`KfMapObjState`), installs the 4 zone tables, and applies persisted save deltas (`kf_game_save_apply_zone_deltas`).
- **Phase `4` -> `6`:** Streams `RTMD.T[next_bgm]`, queues `RTIM.T[next_vab]`, swaps area VAB soundbanks, and triggers `VAB.T[0x140 + track_id]`.

---

## 3. `FDAT[47]` (`0x2F`, `503,808` Bytes) — Resident Global VRAM Atlas

`kf_game_mount_t_archives` schedules `kf_game_load_rtim_to_heap(5, 0x2f)` to stream `FDAT[47]` into PS1 VRAM via `kf_game_upload_rtim_vram_queue` (`0x80016fc8`).
- Contains **`500` sequential `KfRtimHeader` + 16-bit pixel blocks** spanning `503,616` bytes (`0x00000..0x7AF3F`) followed by `188` bytes of zero padding and the `4`-byte `0x12345678` CD sector checksum at `0x7AFFC`.
- Houses shared HUD fonts, compass strips, inventory icons, CLUT rows (`(576, 258+y, 16, 1)`), and global `32x128` texture pages (`(320+x, 0, 32, 128)`).

---

## 4. `FDAT[48]` (`0x30`, `110,592` Bytes) — 9-Section Master Boot Database

Loaded once at boot by `kf_game_mount_t_archives` (`0x80015dd4`) into `0x8009bfe4` (`109,056` bytes active = `36` header bytes + `109,020` payload bytes):

| Section | Payload Offset | Size (B) | RAM Target | Decoded Contract & Record Count |
| :---: | :--- | ---: | :--- | :--- |
| `0` | `0x00004` | `7,680` | `0x80175914` | `KfMapObjDef[320]` (`0x18` = `24` B/entry; props, doors, traps, triggers) |
| `1` | `0x01E08` | `1,232` | `0x801c7fbc` | `KfMagicDef[18]` (`0x44` = `68` B/entry = `1,224` B) + `8`-B trailer (`3200000800000300`) |
| `2` | `0x022DC` | `2,048` | `0x801d9ccc` / `0x801d9a2c` | `KfItemDef[64]` (`0x20` = `32` B/entry; armor/ring/equip bonuses & prices) |
| `3` | `0x02AE0` | `1,200` | `0x8007682c` | `LevelUpGrowth[100]` (`12` B/entry `<4HI`: `hp, mp, str_gain, mag_gain, next_xp`, levels `1..99` at `0..98`) |
| `4` | `0x02F94` | `1,664` | `0x8019c5ec` | Spell/learnable magic & HUD lookup descriptor table (`64` x `0x1a` B) |
| `5` | `0x03618` | `2,816` | `0x800679a0` | `80`-entry base map tile geometry / lighting transform templates |
| `6` | `0x0411C` | `2,560` | `0x801989d8` | Auxiliary world/render parameter table |
| `7` | `0x04B20` | `6,280` | `0x800fb014` | Base `.TMD` pack mounted via `kf_game_mo_mount_tmd_pack(0, ...)` (`17` slots) |
| `8` | `0x063AC` | `83,540` | `0x800864e4` | Base `.TMD` pack mounted via `kf_game_mo_mount_tmd_pack(0x28, ...)` (`51` slots) |

### Verified `LevelUpGrowth` Progression Sample (`FDAT[48]` Section `3`)

| Slot Index | Player Level | Max HP | Max MP | `str_gain` / `mag_gain` | `next_level_xp` |
| ---: | ---: | ---: | ---: | :--- | ---: |
| `0` | `1` (Boot) | `50` | `30` | `20` / `20` *(base stats)* | `50` |
| `10` | `11` | `128` | `74` | `1` / `1` | `1,932` |
| `50` | `51` | `613` | `360` | `3` / `1` | `150,104` |
| `98` | `99` (Cap) | `999` | `999` | `2` / `3` | `999,999` |

### Complete Retail Zone Triplet Table (`9` Active Zones in `FDAT.T`)

| Zone ID | Slots | `slot0` Payload (`64,000 + extra`) | `slot1` (`[12992, 3200, 8400, 2048]`) | `slot2` Callback Table | Checksums (`0x12345678`) |
| ---: | :--- | :--- | :--- | ---: | :--- |
| `0` | `0..2` | `64,000` B + `3,376` B | `26,640` B (`4/4` exact) | `4,096` B | `3 / 3` Pass |
| `1` | `3..5` | `64,000` B + `3,864` B | `26,640` B (`4/4` exact) | `8,192` B | `3 / 3` Pass |
| `2` | `6..8` | `64,000` B + `4,810` B | `26,640` B (`4/4` exact) | `4,096` B | `3 / 3` Pass |
| `3` | `9..11` | `64,000` B + `4,228` B | `26,640` B (`4/4` exact) | `6,144` B | `3 / 3` Pass |
| `4` | `12..14` | `64,000` B + `3,450` B | `26,640` B (`4/4` exact) | `8,192` B | `3 / 3` Pass |
| `5` | `15..17` | `64,000` B + `2,934` B | `26,640` B (`4/4` exact) | `6,144` B | `3 / 3` Pass |
| `6` | `18..20` | `64,000` B + `3,812` B | `26,640` B (`4/4` exact) | `6,144` B | `3 / 3` Pass |
| `7` | `21..23` | `64,000` B + `1,414` B | `26,640` B (`4/4` exact) | `8,192` B | `3 / 3` Pass |
| `10` | `30..32` | `64,000` B + `2,194` B | `26,640` B (`4/4` exact) | `6,144` B | `3 / 3` Pass |

---

## 5. `FDAT[49..66]` (`0x31 + magic_id`) — Weapon & Spell View-Models (`16` Active)

When `kf_game_player_load_magic_def(magic_id)` (`0x80026210`) equips a weapon or combat stance, it streams slot `0x31 + magic_id` (`49..55` for melee weapons `anim_count=1`, `58..66` for special/magic weapons `anim_count=2`; slots `56..57` empty) as a `KfMoHeader` container (`12,288..63,488` B) and mounts its embedded `.TMD` into dynamic slot `0x20` (`kf_game_tmd_mount_dynamic_slot`).

| `FDAT` Slot | `magic_id` | Bytes | `anim_count` | `tmd_offset` | Verts / Prims |
| ---: | ---: | ---: | ---: | :--- | :--- |
| `49`..`55` | `0..6` | `12,288..24,576` | `1` | `0x12e4..0x2390` | `96..219` V / `176..422` P |
| `56`..`57` | `7..8` | `0` *(empty)* | — | — | Unused view-model slots |
| `58`..`66` | `9..17` | `18,432..63,488` | `2` | `0x1414..0x9298` | `139..340` V / `269..672` P |

---

## 6. Mapped Specification Coverage Ledger (`16 / 16` Fields)

| # | `spec_coverage.json` Field Key | Binary / Struct Location | Verification Rule |
| ---: | :--- | :--- | :--- |
| `1` | `KfFdatHeader.section_size` | `FDAT` section `+0x00` (`u32`) | Length-prefixed chain |
| `2` | `FDAT.zone_triplets_0_to_7_and_10` | Slots `0..23`, `30..32` | `9` active zone triplets |
| `3` | `FDAT.slot_3z_kf_map_cell_6400` | Slot `3*z` `sec[0]` | `64,000` B (`80x80` grid) |
| `4` | `KfMapCell.lower_and_upper_layers` | `0x801c8484` (`10` B/cell) | Lower `[0..4]` + upper `[5..9]` |
| `5` | `FDAT.slot_3z_plus_1_four_sections` | Slot `3*z + 1` | Exact `[12992, 3200, 8400, 2048]` |
| `6` | `FDAT.slot_3z_plus_2_vram_callbacks` | Slot `3*z + 2` | `0x8019f07c` callback table |
| `7` | `FDAT.slot_47_resident_vram_atlas` | Slot `47` (`503,808` B) | `500` `KfRtimHeader` blocks |
| `8` | `FDAT.slot_48_nine_boot_sections` | Slot `48` (`110,592` B) | `9` sections (`109,056` B active) |
| `9` | `FDAT48.sec0_KfMapObjDef_320` | `sec[0]` (`7,680` B) | `320 x 24` B (`0x80175914`) |
| `10` | `FDAT48.sec1_KfMagicDef_18` | `sec[1]` (`1,232` B) | `18 x 68` B + `8`-B tail |
| `11` | `FDAT48.sec2_KfItemDef_64` | `sec[2]` (`2,048` B) | `64 x 32` B (`0x801d9a2c`) |
| `12` | `FDAT48.sec3_LevelUpGrowth_100` | `sec[3]` (`1,200` B) | `100 x 12` B (`0x8007682c`) |
| `13` | `FDAT48.sec4_to_6_spell_tile_aux` | `sec[4..6]` (`1664/2816/2560`) | Spell, tile, aux tables |
| `14` | `FDAT48.sec7_tmd_pack_slot0` | `sec[7]` (`6,280` B) | `17`-slot `.TMD` pack |
| `15` | `FDAT48.sec8_tmd_pack_slot40` | `sec[8]` (`83,540` B) | `51`-slot `.TMD` pack |
| `16` | `FDAT.slots_49_to_66_weapon_viewmodels` | Slots `49..66` (`16` active) | `KfMoHeader` `anim_count` `1..2` |

---

## 7. Clean-Room Parser Usage & Verification

```powershell
# Offline synthetic FDAT.T check (zone 0 triplet + FDAT[47] + 9-section FDAT[48] + FDAT[49])
python -B Dev/scripts/kf_world_fdat.py --offline-synthetic --data-dir "$env:TEMP\kf-work" --log-dir "$env:TEMP\kf-logs"

# Fail-closed empty directory check (exits 2 with MISSING_CORPUS_MEDIA JSON)
python -B Dev/scripts/kf_world_fdat.py --data-dir "$env:TEMP\kf-empty"
```

Verified schemas: [`Dev/schemas/types/kf_world_and_render.h`](../../schemas/types/kf_world_and_render.h), [`Dev/schemas/types/kf_containers_and_io.h`](../../schemas/types/kf_containers_and_io.h), [`Dev/schemas/spec_coverage.json`](../../schemas/spec_coverage.json).
