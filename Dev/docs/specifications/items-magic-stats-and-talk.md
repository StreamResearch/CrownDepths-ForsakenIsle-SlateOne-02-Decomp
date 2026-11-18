# Items (`ITEM.T` / `KfItemDef`), Magic (`KfMagicDef`), and Dialogue Cards (`TALK.T`)

**Specification ID:** `items-magic-stats-and-talk` · **Reference Parser:** [`Dev/scripts/kf_items_magic_talk.py`](../../scripts/kf_items_magic_talk.py) · **Parent Index:** [`Dev/docs/SPECIFICATIONS.md`](../SPECIFICATIONS.md)

This specification covers `KfItemDef[64]`, `KfMagicDef[18]`, the `403` active entries in `CD/COM/ITEM.T`, the `379` pre-rendered dialogue card entries in `CD/COM/TALK.T`, the NPC dialogue VM opcodes (`0xf0..0xff`), and player inventory/spell persistence slots (`SLUS-00158`).

---

## 1. `KfItemDef[64]` Armor, Shield & Accessory Table (`0x20` B Stride)

Decoded from `FDAT[48]` section `2` (`2,048` B = `64 x 32` B) and indexed by `kf_game_player_add_equip_defenses` (`0x800243b0`) at `0x801d9a2c`:

| Offset | Size | Type | Field | Verified Role |
| :--- | ---: | :--- | :--- | :--- |
| `+0x00` | `1` | `u8` | `category` | Item classification (`0x00` armor/weapon class, key/consumable flags) |
| `+0x01` | `1` | `u8` | `equip_slot` | Target equipment slot mask (`head/body/arm/shield/feet/ring0..1`) |
| `+0x02` | `2` | `s16` | `pdef_bonus` | Physical defense modifier added to `g_kf_player_def_stats[0]` |
| `+0x04` | `2` | `s16` | `mdef_bonus` | Slash/magic base resistance modifier |
| `+0x06..+0x0A` | `6` | `s16[3]` | `slash_res, chop_res, stab_res` | Physical damage-type resistance bonuses |
| `+0x0C..+0x14` | `10` | `s16[5]` | `fire_res, earth_res, wind_res, water_res, light_res` | Five elemental defense modifiers |
| `+0x16` | `2` | `u16` | `flags` | Equip bitflags / special behavior tag |
| `+0x18` | `4` | `u32` | `price` | Shop purchase price (gold) |
| `+0x1C` | `4` | `u32` | `reserved` | Sell value / shop appraisal scalar |

---

## 2. `KfMagicDef[18]` Weapon & Cast Definition Table (`0x44` B Stride)

Decoded from `FDAT[48]` section `1` (`1,232` B = `18 x 68` B + `8`-B trailer) and indexed by `kf_game_player_load_magic_def` (`0x80026210`) & `kf_game_player_recalc_derived_stats` (`0x800244cc`):

| Offset | Size | Type | Field | Verified Role |
| :--- | ---: | :--- | :--- | :--- |
| `+0x00` | `1` | `u8` | `id` | Weapon/magic entry identifier |
| `+0x01` | `1` | `u8` | `two_handed` | Two-handed / shield-lock state flag |
| `+0x02` | `1` | `u8` | `spell_slot` | Linked spell cast slot (`0x40` / none or spell index) |
| `+0x03` | `1` | `u8` | `element_flags` | Element affinity bitmask (`0xFF` none / elemental) |
| `+0x04` | `2` | `u16` | `reserved_04` | Alignment / auxiliary weapon flags |
| `+0x06..+0x15` | `16` | `u16[8]` | `atk_stats[8]` | Eight attack power channels (`slash, chop, stab, fire, earth, wind, water, light`) |
| `+0x16..+0x1F` | `10` | `u8[10]` | `anim_data[10]` | View-model animation timing parameters |
| `+0x20..+0x23` | `4` | `u16, u16` | `swing_speed, attack_range` | Melee swing cadence and reach distance |
| `+0x24..+0x2D` | `10` | `u8[10]` | `extra[10]` | Cast origin / hitbox trajectory offsets |
| `+0x2E..+0x33` | `6` | `u16[3]` | `hitbox_delay, mp_cost, stamina_cost` | Active frame delay, MP drain, and stamina drain |
| `+0x34..+0x3B` | `8` | `u16[4]` | `sound_id, r36, cast_cost, r3a` | Triggered SPU SFX ID and special cast gauge cost |
| `+0x3C..+0x43` | `8` | `u32, u32` | `price, reserved_40` | Merchant base price and trailing camera angle offset |

---

## 3. `CD/COM/ITEM.T` (`548` Slots / `403` Active, `11,110,400` Bytes)

`ITEM.T` cleanly partitions into 3D item inspection meshes (`0..119`) and 2D full-screen map/item/icon graphics (`120..547`):

| Slot Range | Active Count | Container Format | Verified Consumer Routine |
| :--- | ---: | :--- | :--- |
| `0..119` | `103` | Standard `0x41` `.TMD` (`nobj = 1`) | `kf_game_ui_show_fullscreen_tim` / `kf_game_ui_setup_item_preview_matrix` |
| `120..547` | `300` | PS1 `.TIM` textures (`4/8/16`-bpp) | `kf_game_ui_render_area_map_screen` (`0x1e0 + ...`), storage item portraits (`0x168 + id`) |

- Every active `ITEM.T` slot (`403/403`) terminates in a valid `0x12345678` CD sector checksum word.
- `kf_game_ui_filter_owned_items` (`0x80019444`) iterates `120` owned inventory slots (`g_kf_game_bss_u8_tbl_8009b52c`), building `24`-byte HUD icon descriptor packets from `0x80065b24`.
- `kf_game_ui_filter_unequipped_items` (`0x80019528`) excludes slots matching `g_kf_player_state.equip_ids[7]` (`head`, `body`, `arm`, `shield`, `feet`, `ring0`, `ring1`) when populating storage and drop lists.
- `kf_game_ui_filter_sellable_items` (`0x800196c8`) suppresses key/quest items whose shop appraisal word matches sentinel `0xc350` (`50,000`).
- `kf_game_inv_add_item` (`0x80048178`) caps per-item stack counts at `99` and coordinates crystal/flask ID checks (`0x47..0x50` via `kf_game_item_is_crystal_or_flask @ 0x80029560`).

### Verified `KfItemDef` & `KfMagicDef` Sample Contracts (`FDAT[48]`)
- **`KfItemDef[0..2]` (`sec[2]`):** `pdef_bonus` `14 / 18 / 25`, `mdef_bonus` `4 / 12 / 18`, `price` `180 / 650 / 2500`, `sell_value` `140 / 520 / 2000`.
- **`KfMagicDef[0]` (`sec[1]`):** `id=2`, `two_handed=true` (`1`), `spell_slot=64`, `atk_stats[0..2] = [39, 6, 14]`, `swing_speed=82`, `attack_range=812`, `hitbox_delay=12`, `mp_cost=0`, `stamina_cost=1`, `cast_cost=4`.

### Verified Retail `ITEM.T` Texture Geometry Breakdown (`300` TIM Slots)
- **`4`-bpp `256x256` Icon & UI Card Sheets (`276` slots):** Standard `vram_w = 64`, `height = 256` (`32,832` B with `16`-color `CLUT`), carrying inventory icons, equipment portraits, and shop cards.
- **`4`-bpp `200x200` Fullscreen Automap & Lore Screens (`24` slots):** Used by `kf_game_ui_render_area_map_screen` (`0x80019b54`) and modal crystal/map viewers (`0x1e0 + map_id`).

### Inventory Filter Ranges (`kf_game_ui_filter_owned_items` & Equip Slot Pickers)

| Picker Category | ID Window | Verified Routine (`GAME.EXE`) | Target Equipment / Menu Role |
| :--- | :--- | :--- | :--- |
| Consumables & Maps | `0x43..0x77` | `kf_game_ui_run_use_item_menu` (`0x80019204`) | Maps (`0x43..0x45`), crystals/keys (`0x47..0x50`), herbs |
| Weapons (`slot 0`) | `0x00..0x14` | `kf_game_ui_run_equip_slot_picker` (`0x8001a6e8`) | Sword/melee slot picker |
| Shields (`slot 2`) | `0x22..0x28` | `kf_game_ui_run_equip_slot_picker` | Left-hand shield picker |
| Helms / Armor / Hands / Feet | `0x15..0x34` | `kf_game_ui_run_equip_slot_picker` | Head (`0x15..0x1b`), body (`0x1c..0x21`), arm (`0x29..0x2e`), feet (`0x2f..0x34`) |
| Rings (`slots 7/8`) | `0x35..0x3b` | `kf_game_ui_run_equip_slot_picker` | Dual accessory ring slots |

---

## 4. `CD/COM/TALK.T` (`755` Slots / `379` Active, `13,197,312` Bytes)

Unlike sprite-sheet bitmap font engines, *King's Field* stores NPC speech, item pick-up banners, and stone/signpost messages in `TALK.T` as **pre-rendered `256x256` `4`-bpp `.TIM` dialogue cards**:

| Byte Span | Size | Structure | Verified Parameters |
| :--- | ---: | :--- | :--- |
| `0x0000..0x0007` | `8` B | `.TIM` Header | `magic = 0x00000010`, `flags = 0x00000008` (`pmode = 0` = `4`-bpp, `has_clut = true`) |
| `0x0008..0x0033` | `44` B | `.TIM` CLUT Block | `bnum = 0x2c`, `vram_x = 640`, `vram_y = 511`, `w = 16`, `h = 1` (`16` ABGR1555 colors) |
| `0x0034..0x803F` | `32,780` B | `.TIM` Pixel Block | `bnum = 0x800c`, `vram_w = 64` words (`256` px), `h = 256` lines |
| `0x8040..0x87FB` | `1,980` B | Sector Alignment Slack | Zero-filled alignment tail to `17 * 2,048 = 34,816` B |
| `0x87FC..0x87FF` | `4` B | CD Sector Checksum | `0x12345678` additive checksum verified on `379 / 379` cards |

- Clean-room policy: `kf_items_magic_talk.py` extracts dimensions, VRAM rectangles, CLUT geometry, and checksum status strictly without exporting copyrighted script prose.

---

## 5. NPC Dialogue VM (`kf_game_event_run_dialogue_vm @ 0x80047000`) & Spell Slots

NPC interaction records start with signature byte `0x70`, track an instruction cursor at `script_base[0x10]`, and dispatch bytecode opcodes ahead of `kf_game_gfx_stream_and_show_cg(KF_T_TALK, base_card + id)`:

| Bytecode | Operands | Verified Behavior (`game_154.c`) |
| :--- | :--- | :--- |
| `0x00..0xEF` | `0` B | Streams `TALK.T` dialogue card `script_base[0x0c..0x0d] + opcode` |
| `0xF0` / `0xF8` | `u8 jump_back` | Sets repeat latch (`0xF0`) and rewinds instruction offset by `jump_back` |
| `0xF2` | `u8 skip` | Advances cursor by `2` bytes |
| `0xF4` | `u8 arg` | Invokes area callback slot `g_kf_scene_callbacks[4](entity, arg)` |
| `0xF5` | `u8 multi_count` | Chains `multi_count` sequential dialogue cards before closing |
| `0xF7` | `u8 flag_idx, u8 val` | Writes persistent event byte `g_kf_game_bss_u8_801b3088[flag_idx] = val` |
| `0xF9` | `u8 flag_idx, u8 cmp, u8 lbl` | Conditional jump via `kf_game_npc_seek_dialogue_branch` when `flag == cmp` |
| `0xFF` | `0` B | Terminates dialogue and opens shop (`0x00`), fountain (`0x10`), or storage (`0x20`/`0x30`) |

- Player spell progression persists `64` learned-spell status bytes (`g_kf_game_bss_table_base_8019c5ec`, `0x1a` stride in RAM, packed to `64` contiguous bytes in save payload).

---

## 6. Mapped Specification Coverage Ledger (`16 / 16` Fields)

| # | `spec_coverage.json` Field Key | Binary / Struct Location | Verification Rule |
| ---: | :--- | :--- | :--- |
| `1` | `KfItemDef.category_and_equip_slot` | `KfItemDef` `+0x00..+0x01` | `u8 category`, `u8 equip_slot` |
| `2` | `KfItemDef.pdef_and_mdef_bonuses` | `KfItemDef` `+0x02..+0x05` | `s16 pdef_bonus, mdef_bonus` |
| `3` | `KfItemDef.physical_and_elemental_res` | `KfItemDef` `+0x06..+0x15` | `8 x s16` damage/element resistances |
| `4` | `KfItemDef.flags_price_sell` | `KfItemDef` `+0x16..+0x1F` | `u16 flags`, `u32 price, reserved` |
| `5` | `KfMagicDef.id_handed_slot_elem` | `KfMagicDef` `+0x00..+0x03` | `id, two_handed, spell_slot, element_flags` |
| `6` | `KfMagicDef.atk_stats_8` | `KfMagicDef` `+0x06..+0x15` | `u16[8]` attack power array |
| `7` | `KfMagicDef.swing_range_hitbox` | `KfMagicDef` `+0x20..+0x2F` | `swing_speed, attack_range, hitbox_delay` |
| `8` | `KfMagicDef.mp_stamina_sound_cast_price` | `KfMagicDef` `+0x30..+0x43` | `mp_cost, stamina_cost, sound_id, cast_cost, price` |
| `9` | `ITEM_T.slots_0_to_119_tmd_models` | `ITEM.T[0..119]` | `103` `0x41` `.TMD` (`nobj = 1`) |
| `10` | `ITEM_T.slots_120_to_547_tim_cards` | `ITEM.T[120..547]` | `300` `.TIM` (`276` `256x256` + `24` `200x200`) |
| `11` | `TALK_T.379_dialogue_cards` | `TALK.T` (`755` slots) | `379` active `34,816`-B cards |
| `12` | `TALK_T.256x256_4bpp_tim_frame` | `TALK[i]` `0x0000..0x803F` | `pmode=0` (`4`-bpp), `64 x 256` words |
| `13` | `TALK_T.clut_640_511_16x1` | `TALK[i]` `0x0008..0x0033` | `16x1` CLUT at VRAM `(640, 511)` |
| `14` | `TALK_T.sector_slack_and_checksum` | `TALK[i]` `0x8040..0x87FF` | `1,980` B zero pad + `0x12345678` checksum |
| `15` | `DialogueVM.opcodes_0xf0_to_0xff` | `kf_game_event_run_dialogue_vm` | `0xf0..0xff` branch/shop/flag VM |
| `16` | `Inventory.120_slots_and_64_spells` | `0x8009b52c` & `0x8019c5ec` | `120` owned qty + `64` learned spells |

---

## 7. Clean-Room Parser Usage & Verification

```powershell
# Offline synthetic ITEM.T + TALK.T + KfItemDef + KfMagicDef check
python -B Dev/scripts/kf_items_magic_talk.py --offline-synthetic --data-dir "$env:TEMP\kf-work" --log-dir "$env:TEMP\kf-logs"

# Fail-closed empty directory check (exits 2 with MISSING_CORPUS_MEDIA JSON)
python -B Dev/scripts/kf_items_magic_talk.py --data-dir "$env:TEMP\kf-empty"
```

Verified schemas: [`Dev/schemas/types/kf_containers_and_io.h`](../../schemas/types/kf_containers_and_io.h), [`Dev/schemas/spec_coverage.json`](../../schemas/spec_coverage.json).
