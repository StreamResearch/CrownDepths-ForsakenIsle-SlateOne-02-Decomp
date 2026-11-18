# Morph Meshes (`MO.T`), World Tiles (`RTMD.T`), and VRAM Streams (`RTIM.T` / `.TIM`)

**Specification ID:** `meshes-mo-rtmd-and-rtim` · **Reference Parser:** [`Dev/scripts/kf_meshes_mo_rtmd.py`](../../scripts/kf_meshes_mo_rtmd.py) · **Parent Index:** [`Dev/docs/SPECIFICATIONS.md`](../SPECIFICATIONS.md)

This specification documents the 3D geometry and texture containers in *King's Field* (`SLUS-00158`): animated and static `.MO` character/weapon models (`CD/COM/MO.T`, `FDAT[49..66]`), pre-partitioned world tile `.RTMD` packs (`CD/COM/RTMD.T`), standard `0x41` `.TMD` primitive fixups, chained `KfRtimHeader` VRAM uploads (`CD/COM/RTIM.T`, `FDAT[47]`), and PlayStation `.TIM` palettes/pixels.

---

## 1. `KfMoHeader` Animated Morph & Static `.MO` Containers (`MO.T`)

`CD/COM/MO.T` stores `405` active models across `448` directory slots (`5,693,440` bytes), all verified by `0x12345678` CD sector checksums and loaded by `kf_game_gfx_load_mo_cache_slot` (`0x80032f10`). Empirical analysis confirms **two distinct layout variants** sharing the leading header:

| Offset | Size | Type | Field | Animated Variant (`108` entries + `16` View-Models) | Static Variant (`297` entries) |
| :--- | ---: | :--- | :--- | :--- | :--- |
| `+0x00` | `4` | `u32` | `total_size` | Unpadded payload length | Unpadded payload length |
| `+0x04` | `4` | `u32` | `anim_count` | Number of animation clips (`1..255`) | `0` (zero animation clips) |
| `+0x08` | `4` | `u32` | `tmd_offset` | Offset to embedded `0x41` `.TMD` mesh | `0x0000000C` (immediately follows header) |
| `+0x0C` | `4` | `u32` | `keyframe_table_offset` | Byte offset to sparse keyframe data | Standard `.TMD` `version` word (`0x41`) |
| `+0x10` | `4` | `u32` | `anim_table_offset` | `0x00000014` (`sizeof(KfMoHeader)`) | Standard `.TMD` `flags` word (`0`) |

### Sparse Keyframe Pose Streaming (`GAME.EXE` `0x8003486c..0x8003507c`)
- **Clip Interpolation (`kf_game_mo_sample_anim_keyframe @ 0x8003486c`):** Resolves the current and next keyframe stream pointers plus a `Q12` (`0..4096`) blend factor for `(anim_idx, frame_idx)`.
- **Run-Length Pose Unpacking (`kf_game_mo_unpack_pose_from_base @ 0x80034934` & `kf_game_mo_patch_sparse_pose @ 0x800349f8`):** Compressed keyframe packets store signed `s16` delta commands where sentinel `-0x8000` skips unchanged joint/vertex spans copied directly from `base_pose`, compacting idle frames without inflating RAM buffers.
- **Bone Seeking & Joint Sampling (`kf_game_mo_seek_bone_stream @ 0x80034d2c` & `kf_game_gfx_sample_mo_joint_pos @ 0x8003507c`):** Allows weapon/spell projectiles (`kf_game_player_calc_cast_origin`) to query local joint coordinates from `MO` animation frames in dynamic slot `0x20`.
- **Scaling & GTE Morphing (`kf_game_mo_scale_keyframe_bones @ 0x80034a74` & `kf_game_gfx_eval_mo_keyframe @ 0x80034da8`):** Applies `Q12` bone scales via `ScaleMatrix` and binds interpolated vertex arrays before submitting transformed primitives.

---

## 2. Standard PS1 `.TMD` (`0x41`) Geometry & Primitive Fixup (`0x8002e314`)

Standard `.TMD` containers appear inside `ITEM.T` (`103` item preview models), `MO.T` (embedded inside all `405` entries), and `FDAT[48]` sections `7` and `8` (`68` base world/prop models).

### `.TMD` Header (`12` B) & Object Descriptor (`28` B = `0x1C` B)

| Section | Offset | Size | Type | Field | Description |
| :--- | :--- | ---: | :--- | :--- | :--- |
| Header | `+0x00` | `4` | `u32` | `version` | `0x00000041` (`65`) for standard `.TMD` |
| Header | `+0x04` | `4` | `u32` | `flags` | `0` = offsets relative to `+0x0C`; `1` = already relocated |
| Header | `+0x08` | `4` | `u32` | `nobj` | Number of 28-byte object descriptors |
| Object `i` | `+0x00` | `4` | `u32` | `vert_top` | Offset (from `+0x0C`) to `SVECTOR` vertex array (`8` B/vertex) |
| Object `i` | `+0x04` | `4` | `u32` | `n_vert` | Vertex count |
| Object `i` | `+0x08` | `4` | `u32` | `norm_top` | Offset (from `+0x0C`) to `SVECTOR` normal array (`8` B/normal) |
| Object `i` | `+0x0C` | `4` | `u32` | `n_norm` | Normal count |
| Object `i` | `+0x10` | `4` | `u32` | `prim_top` | Offset (from `+0x0C`) to primitive packet stream |
| Object `i` | `+0x14` | `4` | `u32` | `n_prim` | Primitive packet count |
| Object `i` | `+0x18` | `4` | `s32` | `scale` | Power-of-two GTE coordinate shift factor |

### `kf_game_tmd_fixup_prim_indices` (`0x8002e314`)
Before rendering, `GAME.EXE` pre-scales primitive vertex and normal indices left by `3` (`idx << 3`) so runtime GTE loops index `8`-byte `SVECTOR` arrays directly by byte offset without multiplying inside inner triangle loops. Supported primitive opcode families (`(word >> 24) & 0xfd`) cover untextured/textured/Gouraud triangles and quads (`0x20`, `0x24`, `0x28`, `0x2c`, `0x30`, `0x34`, `0x38`, `0x3c`).

---

## 3. `CD/COM/RTMD.T` (`9` Active World Tile Banks, `1,083,392` Bytes)

`RTMD.T` holds one bank per game area (`slots 0..8`), streamed by `kf_game_step_area_load_fsm` (`0x8001689c`) and bound to bank slot `0` via `kf_game_tmd_register_bank` (`0x8002e628`).

### `RTMD` Structural Distinction vs. Standard `.TMD`
- **Header (`+0x00..+0x0B`):** Word `0` is `0x00000000` (not `0x41`), word `1` is the runtime bank tag (`18` for slots `0..7`, `16` for slot `8`), and word `2` holds active object count `nobj` (`28..190`).
- **Fixed `240`-Slot Object Table (`0x1A40` B):** Even when `nobj < 240`, `RTMD` reserves a full `240 * 28 = 6,720`-byte (`0x1A40`) object descriptor array starting at `+0x0C` so `kf_game_tmd_get_object_desc(tile_id)` (`0x8002e1bc`) indexes `(tile_id * 0x1c) + 0xc + bank_base` directly; every active entry's `vert_top`, `norm_top`, and `prim_top` sits at `>= 0x1A40`.

### Verified `RTMD.T` Bank Metrics (`9 / 9` Checksum-Valid)

| Slot | Sector Span | Bytes | Bank Tag (`+4`) | Objects (`nobj`) | Total Verts | Total Norms | Total Prims |
| ---: | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `0` | `1..107` | `217,088` | `18` | `185` | `4,761` | `5,257` | `5,257` |
| `1` | `107..165` | `118,784` | `18` | `120` | `2,728` | `2,709` | `2,709` |
| `2` | `165..247` | `167,936` | `18` | `159` | `3,890` | `3,921` | `3,921` |
| `3` | `247..350` | `210,944` | `18` | `190` | `4,871` | `5,008` | `5,008` |
| `4` | `350..408` | `118,784` | `18` | `114` | `2,606` | `2,709` | `2,709` |
| `5` | `408..448` | `81,920` | `18` | `81` | `1,806` | `1,809` | `1,809` |
| `6` | `448..495` | `96,256` | `18` | `104` | `2,217` | `2,154` | `2,154` |
| `7` | `495..516` | `43,008` | `18` | `38` | `748` | `893` | `893` |
| `8` | `516..529` | `26,624` | `16` | `28` | `528` | `413` | `413` |

---

## 4. `CD/COM/RTIM.T` (`75` Slots / `72` Active) & `KfRtimHeader` DMA Slicing

`RTIM.T` (`4,304,896` B) stores zone-specific VRAM texture/CLUT bundles loaded asynchronously in mode `0x40` (`kf_game_load_rtim_to_heap @ 0x80016f5c`), bypassing the `0x12345678` sector checksum check.

### `KfRtimHeader` (`16` Bytes = `RECT src_rect` + `RECT dst_rect`)

| Offset | Size | Type | Field | Verified Rule (`kf_game_upload_rtim_vram_queue @ 0x80016fc8`) |
| :--- | ---: | :--- | :--- | :--- |
| `+0x00..+0x07` | `8` | `RECT` (`4 x s16`) | `src_rect` | Source VRAM coordinates `(x, y, w, h)`; `src_rect.x == -1` terminates stream |
| `+0x08..+0x0F` | `8` | `RECT` (`4 x s16`) | `dst_rect` | Destination VRAM coordinates `(x, y, w, h)` (must equal `src_rect` with `w, h > 0`) |
| `+0x10..` | `w * h * 2` | `u16[]` | `pixels_16bpp` | Raw 16-bit VRAM words uploaded via `kf_game_gpu_load_image` |

- **32 KiB Frame Budget (`0x8000` B/tick):** `kf_game_upload_rtim_vram_queue` caps VRAM uploads per frame at `32,768` bytes (`iVar10 <= 0x8000`). If an image slice exceeds remaining budget, the uploader emits `uVar7 = budget / w / 2` scanlines (`LoadImage`), decrements `h` remaining, advances `dst_rect.y`, and resumes the remaining rows on the next tick.

---

## 5. PlayStation `.TIM` Texture Container (`4 / 8 / 16 / 24`-bpp)

Used across `ITEM.T` (`300` entries), `TALK.T` (`379` entries), and `OP/*.D` (`8` frames each):

| Section | Offset | Size | Type | Field | Decoding Formula |
| :--- | :--- | ---: | :--- | :--- | :--- |
| Header | `+0x00` | `4` | `u32` | `magic` | `0x00000010` |
| Header | `+0x04` | `4` | `u32` | `flags` | `pmode = flags & 7` (`0=4bpp, 1=8bpp, 2=16bpp, 3=24bpp`), `has_clut = (flags & 8) != 0` |
| CLUT (opt.) | `+0x08` | `12 + C` | `u32, 4x u16, u16[]` | `bnum, cx, cy, cw, ch, clut[]` | `ABGR1555` (`R = (c & 0x1f)<<3`, `G = (c>>5 & 0x1f)<<3`, `B = (c>>10 & 0x1f)<<3`, `A = 0 if c == 0 else 255`) |
| Pixels | `pos` | `12 + P` | `u32, 4x u16, u8[]` | `bnum, px, py, pw, ph, data[]` | Pixel width = `pw*4` (4bpp), `pw*2` (8bpp), `pw` (16bpp), `(pw*2)//3` (24bpp) |

---

## 6. `MO.T` & `RTIM.T` Empirical Verification Metrics (`405` + `72` Entries)

| Container | Active Entries | Sub-Format Breakdown | Sector Checksum (`0x12345678`) |
| :--- | ---: | :--- | :--- |
| `CD/COM/MO.T` | `405` | `108` `animated_mo` (`1..14` clips) + `297` `static_mo_tmd` (`anim_count = 0`) | `405 / 405` Pass (`mode 0x10`) |
| `CD/COM/RTMD.T` | `9` | `8` banks w/ tag `18`, `1` bank (`slot 8`) w/ tag `16`; `28..190` objs | `9 / 9` Pass (`mode 0x10`) |
| `CD/COM/RTIM.T` | `72` | `16..122` chained `KfRtimHeader` 16-bpp VRAM uploads per slot | Bypassed (`mode 0x40`) |
| `FDAT[47]` | `1` | `500` chained `KfRtimHeader` blocks (`503,616` B active) | `1 / 1` Pass (`mode 0x10`) |

### `GAME.EXE` 3D Rendering & Arena Allocation Helpers
- **`kf_game_tmd_bind_object_verts` (`0x8002e1f0`):** Binds active object `obj_idx` vertex buffer (`obj.vert_top + 0x0c + bank_base`) ahead of `kf_game_tmd_xform_verts_view3d`.
- **`kf_game_mo_mount_tmd_pack` (`0x80034734`):** Unpacks multi-model length-prefixed `.TMD` bundles from `FDAT[48]` `sec[7]` (slot `0`) and `sec[8]` (slot `0x28`), fixing primitive indices on each slot.
- **`kf_game_tmd_fixup_arena_asset` (`0x80032d40`):** Relocates `.MO`-embedded `.TMD` primitives (`asset_hdr + asset_hdr[2]`) upon async CD completion and marks arena block tag `2`.

---

## 7. Mapped Specification Coverage Ledger (`16 / 16` Fields)

| # | `spec_coverage.json` Field Key | Binary / Struct Location | Verification Rule |
| ---: | :--- | :--- | :--- |
| `1` | `KfMoHeader.total_size_and_anim_count` | `KfMoHeader` `+0x00..+0x07` | `total_size`, `anim_count` (`0..14`) |
| `2` | `KfMoHeader.tmd_kf_anim_offsets` | `KfMoHeader` `+0x08..+0x13` | `tmd_offset`, `kf_offset`, `0x14` |
| `3` | `MO_T.108_animated_morph_models` | `MO.T` (`anim_table_offset == 0x14`) | `108` animated `.MO` models |
| `4` | `MO_T.297_static_zero_anim_tmds` | `MO.T` (`anim_count == 0`) | `297` static `tmd_offset == 0x0c` models |
| `5` | `MO.sparse_bone_keyframe_stream` | `0x80034934` / `0x800349f8` | `-0x8000` skip sentinel unpacking |
| `6` | `TMD.standard_0x41_header` | `.TMD` `+0x00..+0x0B` | `version=0x41`, `flags in {0,1}`, `nobj` |
| `7` | `TMD.object_desc_28_bytes` | `.TMD` `+0x0C` (`28` B stride) | `vert/norm/prim` tops & counts, `scale` |
| `8` | `TMD.prim_vertex_normal_lshift3` | `kf_game_tmd_fixup_prim_indices` | `(idx << 3)` byte-offset scaling |
| `9` | `RTMD_T.runtime_header_flags_16_18` | `RTMD.T` `+0x00..+0x0B` | `version=0`, `tag in {16,18}`, `nobj` |
| `10` | `RTMD_T.240_slot_desc_table_0x1a40` | `RTMD.T` `+0x0C..+0x1A4B` | Fixed `240 x 28` B descriptor reservation |
| `11` | `KfRtimHeader.src_and_dst_rect` | `KfRtimHeader` (`16` B) | `src_rect == dst_rect`, `w/h > 0` |
| `12` | `RTIM_T.72_chained_vram_streams` | `CD/COM/RTIM.T` | `72` active multi-block VRAM streams |
| `13` | `RTIM.32kb_per_frame_dma_slices` | `kf_game_upload_rtim_vram_queue` | `0x8000` B/frame slice budget |
| `14` | `TIM.header_magic_and_flags` | `.TIM` `+0x00..+0x07` | `0x10`, `pmode = flags & 7`, `has_clut` |
| `15` | `TIM.clut_abgr1555_palette` | `.TIM` CLUT block | `12`-B header + `ABGR1555` palette |
| `16` | `TIM.pixel_modes_4_8_16_24bpp` | `.TIM` pixel block | Width scaling for `4/8/16/24` bpp |

---

## 8. Clean-Room Parser Usage & Verification

```powershell
# Offline synthetic MO.T + RTMD.T + RTIM.T parser verification
python -B Dev/scripts/kf_meshes_mo_rtmd.py --offline-synthetic --data-dir "$env:TEMP\kf-work" --log-dir "$env:TEMP\kf-logs"

# Fail-closed empty directory check (exits 2 with MISSING_CORPUS_MEDIA JSON)
python -B Dev/scripts/kf_meshes_mo_rtmd.py --data-dir "$env:TEMP\kf-empty"
```

Verified schemas: [`Dev/schemas/types/kf_containers_and_io.h`](../../schemas/types/kf_containers_and_io.h), [`Dev/schemas/types/primitives_and_sdk.h`](../../schemas/types/primitives_and_sdk.h), [`Dev/schemas/spec_coverage.json`](../../schemas/spec_coverage.json).
