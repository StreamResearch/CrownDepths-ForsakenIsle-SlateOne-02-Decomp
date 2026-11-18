# Memory Card Save Format (`BASLUS-00158*`), `.mcr` Parity & Checksums

**Specification ID:** `save-memcard-baslus00158` · **Reference Parser:** [`Dev/scripts/kf_save_memcard.py`](../../scripts/kf_save_memcard.py) · **Parent Index:** [`Dev/docs/SPECIFICATIONS.md`](../SPECIFICATIONS.md)

This specification defines the PlayStation 1 Memory Card container format (`128 KiB` `.mcr`/`.mcd` directory frames + `8,192`-byte blocks), the two-block `BASLUS-00158<digit>` (`0x4000` B = `16,384` B) save layout, the `kf_game_mc_checksum_payload` (`0x80023dd0`) additive checksum over `0x3c00` payload bytes, and the full serialization offsets in `kf_game_save_serialize_state` (`0x80049a88`).

---

## 1. Raw `128 KiB` Memory Card (`.mcr`/`.mcd`) & Directory Parity

A raw PlayStation Memory Card image (`131,072` bytes) divides into `16` blocks of `8,192` bytes (`0x2000` B): Block `0` holds the card header and `15` directory frames (`128` bytes each), and Blocks `1..15` store file data.

| Offset | Size | Region | Parity / Framing Rule |
| :--- | ---: | :--- | :--- |
| `0x0000..0x007F` | `128` B | Card Master Header | `"MC"` (`0x4D, 0x43`) at `+0x00`, zero pad, XOR byte at `+0x7F` |
| `0x0080..0x07FF` | `15 x 128` B | Directory Frames (`0..14`) | `+0x00` `alloc_state` (`0x51`=first, `0x52`=mid, `0x53`=end), `+0x04` `u32 size` (`0x4000`), `+0x08` `u16 next_block` (`0xFFFF` end), `+0x0A` ASCII filename (`"BASLUS-00158<digit>"`), `+0x7F` XOR parity |
| `0x2000..0x1FFFF` | `15 x 8,192` B | File Data Blocks | Chained via directory `next_block` links (`2` contiguous/chained blocks = `0x4000` B) |

- **Directory XOR Parity (`+0x7F`):** `frame[127] == XOR(frame[0..126])`. `kf_game_enum_memcard_saves` (`0x800231b0`) enumerates `bu00:*` entries matching `"BASLUS-00158"` (up to `15` slots, checking `0x1a000 < used_bytes` for card full status).

---

## 2. `KfSaveHeader` (`0x0000..0x03FF`, `1,024` Bytes)

Built and verified by `kf_game_save_memcard_slot` (`0x80023764`) and `kf_game_mc_load_save_slot` (`0x80023638`):

| Offset | Size | Type | Field | Verified Values & Encoding |
| :--- | ---: | :--- | :--- | :--- |
| `+0x00` | `2` | `char[2]` | `magic` | `"SC"` (`0x53, 0x43`) |
| `+0x02` | `1` | `u8` | `icon_type` | `0x13` (`3`-frame animated PS1 Memory Card icon) |
| `+0x03` | `1` | `u8` | `block_count` | `0x02` (`2` blocks = `16,384` bytes = `0x4000` B) |
| `+0x04..+0x43` | `64` | `char[64]` | `title_sjis` | Null-terminated Shift-JIS save label (`0x81 0x40` spaces + encoded metadata) |
| `+0x44..+0x5F` | `28` | `u8[28]` | `reserved_44` | Zero-filled header pad |
| `+0x60..+0x7F` | `32` | `u16[16]` | `icon_clut` | `16`-color ABGR1555 icon palette |
| `+0x80..+0x1FF` | `384` | `u8[3][128]` | `icon_frames` | Three `16x16` `4`-bpp icon bitmaps (snapped from VRAM `(800/804/808, 240+slot*16)`) |
| `+0x200..+0x203` | `4` | `s32` | `checksum` | Signed 32-bit additive byte sum of `blob[0x0400..0x3FFF]` |
| `+0x204..+0x3FF` | `508` | `u8[508]` | `reserved_204` | Zero-filled slack through `0x0400` payload boundary |

### Shift-JIS Slot Metadata Encoding (`kf_game_mc_encode_sjis_metadata @ 0x80023cc0` & `0x8002338c`)
`kf_game_mc_encode_sjis_metadata` writes full-width Shift-JIS digits (`0x82 0x4F + digit`, space `0x81 0x40`) directly into `title_sjis`:
- **Slot Digit (`+0x22..+0x23`):** `0x82`, `0x4F + slot_digit`.
- **6-Digit Experience / Score (`+0x2C..+0x37`):** Pairs `(0x19 - i) * 2 + 4` (`i = 0..5`) encode `g_kf_player_state.experience` in decimal right-to-left.
- **2-Digit Player Level (`+0x3E..+0x41`):** Pairs `(0x1E - i) * 2 + 4` (`i = 0..1`) encode `g_kf_player_level` right-to-left; read back by `kf_game_mc_read_slot_header` (`0x8002338c`) when rendering save/load slot menus.

---

## 3. `0x3C00`-Byte Payload Additive Checksum (`kf_game_mc_checksum_payload`)

Verified identically in C (`Dev/scripts/d4_harness/parity_gameplay_and_str_tests.c`) and Python (`compute_kf_payload_checksum`):

```c
s32 kf_game_mc_checksum_payload(const u8 *payload) {
    s32 sum = 0;
    for (int i = 0; i < 0x3c00; ++i) {
        sum += (s32)payload[i];
    }
    return sum;
}
```

- On load (`kf_game_mc_load_save_slot`), `GAME.EXE` reads all `0x4000` bytes from `bu00:BASLUS-00158<digit>`, computes the sum over `payload = buf[0x400 : 0x4000]`, compares against `*(s32 *)(buf + 0x200)`, and aborts with error `2` on any single-bit discrepancy.

---

## 4. Serialized Gameplay Payload Map (`0x0400..0x3FFF`, `15,360` Bytes)

Offsets below are relative to `payload` (`file_offset - 0x400`), verified directly from `kf_game_save_serialize_state` (`0x80049a88`, `game_21.c`):

| Payload Offset | File Offset | Size | Source RAM / Struct | Serialized Fields |
| :--- | :--- | ---: | :--- | :--- |
| `+0x0000..+0x0004` | `0x0400..0x0404` | `5` B | `g_kf_scene_control` | `u32 cur_map`, `u8 cur_fade_mode` |
| `+0x0005..+0x0104` | `0x0405..0x0504` | `256` B | `0x801b3088..0x801b3187` | Persistent world/chest/dialogue event flags |
| `+0x0105..+0x3905` | `0x0505..0x3D05` | `14,336` B | `0x801b3188..0x801b6987` | Zone-delta entity/prop/door state heap |
| `+0x3906..+0x3919` | `0x3D06..0x3D19` | `20` B | `0x801b6988..0x801b699b` | Auxiliary scene/timer snapshot words |
| `+0x391A..+0x3991` | `0x3D1A..0x3D91` | `120` B | `0x8009b52c..0x8009b5a3` | Player owned item quantities (`120` inventory slots) |
| `+0x3992..+0x39D1` | `0x3D92..0x3DD1` | `64` B | `0x8019c5ec` (`0x1a` stride) | `64` learned spell flags (first byte per descriptor) |
| `+0x39D4..+0x39E3` | `0x3DD4..0x3DE3` | `16` B | `KfPlayerState` (`+0xd8..+0xe7`) | `pos_x, pos_y, pos_z, standing_entity_id` (`4 x s32`) |
| `+0x39E4..+0x39EB` | `0x3DE4..0x3DEB` | `8` B | `KfPlayerState` (`+0xf8..+0xff`) | `target_view_angles (u32)`, `target_look_pitch (u32)` |
| `+0x39EC..+0x39F7` | `0x3DEC..0x3DF7` | `12` B | `KfPlayerState` (`+0x00..+0x07, +0x2c`) | `experience (u32)`, `next_level_xp (s32)`, `gold (u32)` |
| `+0x39F8..+0x3A25` | `0x3DF8..0x3E25` | `46` B | `KfPlayerState` | `time_hours`, `max_hp`, `cur_hp`, `max_mp`, `cur_mp`, `base_str`, `base_mag`, `str_mod`, `mag_mod`, `status_timers[14]` (`23 x s16`) |
| `+0x3A2E..+0x3A40` | `0x3E2E..0x3E40` | `19` B | `KfPlayerState` | `level`, `active_slot`, `equip_ids[7]` (`head, body, arm, shield, feet, ring0, ring1`), `equipped_magic_id`, `equipped_item_id`, `equipped_shield_id`, `equipped_weapon_id`, `hud_flags[6]` |

- `kf_game_save_deserialize_state` (`0x8004a040`) mirrors every offset in reverse and restores derived player combat stats via `kf_game_player_refresh_equip_fx`.

### Memory Card BIOS Event Loop & Directory Helpers (`GAME.EXE`)
- **`kf_game_mc_open_card_events` (`0x80022f2c`) & `kf_game_mc_poll_card_events` (`0x80023df4`):** Opens and polls the four Memory Card hardware events (`0xf4000001`: IOE, error, timeout, new-card) ahead of `StartCARD2()` / `_bu_init()`.
- **`kf_game_mc_reset_card_detect` (`0x8004ac44`) & `kf_game_mc_format_slot0` (`0x8002360c`):** Resets card swap state via `_new_card()` + dummy sector `0x3f` probe and exposes `format("bu00:")`.
- **`kf_game_ui_run_memcard_save_flow` (`0x8001c624`) & `kf_game_mc_collect_save_slots_ui` (`0x8001b7a8`):** Scans all `15` directory slots, displays Shift-JIS playtime/level summaries, confirms overwrites, and verifies write-back via immediate re-read checksum comparison (`game_100.c` lines `237–245`).

---

## 5. Mapped Specification Coverage Ledger (`16 / 16` Fields)

| # | `spec_coverage.json` Field Key | Binary / Struct Location | Verification Rule |
| ---: | :--- | :--- | :--- |
| `1` | `MCR.128kb_card_and_mc_header` | `.mcr` `0x0000..0x007F` (`131,072` B) | `"MC"` magic at `+0x00`, `16 x 8,192` B blocks |
| `2` | `MCR.dir_frame_128b_0x51_chain` | `.mcr` `0x0080..0x07FF` | `alloc_state = 0x51`, `next_block` (`0xFFFF` end) |
| `3` | `MCR.dir_frame_xor_parity_0x7f` | Frame `+0x7F` (`1` B) | `XOR(frame[0..126]) == frame[127]` |
| `4` | `BASLUS00158.two_block_0x4000_size` | `BASLUS-00158<digit>` | `0x4000` B (`2 x 8,192` B blocks) |
| `5` | `KfSaveHeader.sc_magic_0x13_2_blocks` | `KfSaveHeader` `+0x00..+0x03` | `"SC"`, `icon_type=0x13`, `block_count=2` |
| `6` | `KfSaveHeader.sjis_title_64_bytes` | `KfSaveHeader` `+0x04..+0x43` | `64`-B Shift-JIS title (`0x81 0x40` spaces) |
| `7` | `KfSaveHeader.sjis_slot_xp_level_encoding` | `title_sjis` `+0x22/+0x2C/+0x3E` | Full-width `0x82 0x4F+d` slot, XP, level |
| `8` | `KfSaveHeader.icon_clut_and_3_frames` | `KfSaveHeader` `+0x60..+0x1FF` | `32`-B `ABGR1555` CLUT + `3 x 128`-B icons |
| `9` | `KfSaveHeader.additive_checksum_0x200` | `KfSaveHeader` `+0x200..+0x203` | Signed `s32` sum of `payload[0..0x3bff]` |
| `10` | `SavePayload.0x3c00_byte_span` | File `0x0400..0x3FFF` | `15,360`-B serialized gameplay payload |
| `11` | `SavePayload.cur_map_and_fade_mode` | Payload `+0x0000..+0x0004` | `u32 cur_map`, `u8 cur_fade_mode` |
| `12` | `SavePayload.event_flags_and_zone_deltas` | Payload `+0x0005..+0x3919` | `256`-B flags + `14,336`-B heap + `20`-B tail |
| `13` | `SavePayload.inventory_120_and_spells_64` | Payload `+0x391A..+0x39D1` | `120` owned item qty + `64` learned spells |
| `14` | `SavePayload.pos_angles_xp_gold_hours` | Payload `+0x39D4..+0x39F9` | `pos[3]`, `stand_id`, `angles[2]`, `xp`, `gold`, `hours` |
| `15` | `SavePayload.hp_mp_str_mag_statuses` | Payload `+0x39FA..+0x3A25` | `max/cur` HP/MP, `base/mod` STR/MAG, `14` timers |
| `16` | `SavePayload.level_slot_and_equip_ids` | Payload `+0x3A2E..+0x3A40` | `level`, `active_slot`, `equip[7]`, equipped IDs, `hud[6]` |

### Integrity Verification Rules (`kf_save_memcard.py`)
1. **Tamper Sensitivity:** Mutating any byte in `payload[0..0x3bff]` invalidates `checksum_valid` (`computed != stored`).
2. **Directory Frame Parity:** Mutating any directory frame byte `[0..0x7E]` in `.mcr` images invalidates `dir_xor_valid`.
3. **Header Structural Bounds:** Rejects containers `< 0x4000` bytes, mismatched `"SC"` magic, non-`2` block count, or invalid Shift-JIS metadata bounds.
4. **Synthetic Round-Trip:** `build_synthetic_save_bytes` and `build_synthetic_mcr_bytes` generate deterministic `16,384`-B / `131,072`-B containers passing all checks with zero retail files.

### Memory Card Directory Frame Byte Layout (`128` B per Slot `0..14`)

| Offset | Size | Type | Field | Verified PS1 Card Convention |
| :--- | ---: | :--- | :--- | :--- |
| `+0x00..+0x03` | `4` | `u32` | `alloc_state` | `0x51` (start), `0x52` (middle), `0x53` (end), `0xA0` (free) |
| `+0x04..+0x07` | `4` | `u32` | `file_size` | `0x4000` (`16,384` B = `2` blocks for `BASLUS-00158*`) |
| `+0x08..+0x09` | `2` | `u16` | `next_block` | Chained `0..14` block index or `0xFFFF` terminator |
| `+0x0A..+0x1E` | `21` | `char[21]` | `filename` | Null-terminated ASCII `"BASLUS-00158<digit>"` |
| `+0x1F..+0x7E` | `96` | `u8[96]` | `reserved` | Zero-filled directory padding |
| `+0x7F` | `1` | `u8` | `dir_xor` | `XOR(frame[0..126])` directory frame integrity byte |

### Save & Load Return Codes (`kf_game_mc_load_save_slot` & `kf_game_save_memcard_slot`)
- **Return `0`:** Save written/loaded, `0x4000` I/O count verified, and `+0x200` additive checksum matched.
- **Return `1`:** Memory Card `open`/`read`/`write` I/O failure or insufficient free blocks (`> 0x1a000` bytes allocated).
- **Return `2`:** Additive payload checksum mismatch (`*(s32 *)(hdr + 0x200) != kf_game_mc_checksum_payload(payload)`).

### Post-Load Hydration Sequence (`kf_game_mc_load_save_slot` -> `kf_game_main_loop`)
1. `kf_game_mc_load_save_slot(slot_digit)` opens `bu00:BASLUS-00158<digit>`, reads `0x4000` bytes into `g_kf_save_io_buffer_ptr` (`0x8006eb3c`), and validates `*(s32 *)(hdr + 0x200) == kf_game_mc_checksum_payload(payload)`.
2. `kf_game_save_deserialize_state(payload)` restores `cur_map`, `256` event flags, `14,336`-B zone-delta heap, `120` inventory quantities, `64` spell states, `KfPlayerState`, and `7` equipped IDs.
3. `kf_game_main_loop` calls `kf_game_player_refresh_equip_fx` (`0x800240b8`) to reload the equipped weapon `.MO` view-model (`FDAT[0x31 + weapon_id]`) and recompute derived attack/defense totals (`kf_game_player_recalc_derived_stats`).
4. `kf_game_commit_area_transition` triggers `kf_game_step_area_load_fsm` for `cur_map` and calls `kf_game_save_apply_zone_deltas` (`game_134.c` line `152`) so opened chests, unlocked doors, and defeated bosses remain persisted.

---

## 6. Clean-Room Parser Usage & Verification

```powershell
# Offline synthetic 128 KiB .mcr + BASLUS-00158 round-trip checksum & state decode
python -B Dev/scripts/kf_save_memcard.py --offline-synthetic --data-dir "$env:TEMP\kf-work" --log-dir "$env:TEMP\kf-logs"

# Fail-closed empty directory check (exits 2 with MISSING_CORPUS_MEDIA JSON)
python -B Dev/scripts/kf_save_memcard.py --data-dir "$env:TEMP\kf-empty"
```

Verified schemas: [`Dev/schemas/types/kf_containers_and_io.h`](../../schemas/types/kf_containers_and_io.h), [`Dev/schemas/types/kf_actor_combat_ui.h`](../../schemas/types/kf_actor_combat_ui.h), [`Dev/schemas/spec_coverage.json`](../../schemas/spec_coverage.json).
