# KingsField-PlayStation — Empirical Findings & Discovery Log

**Version:** `0.1.0` (2026-11-14) · **Axis:** `hybrid` · **Serial:** `SLUS-00158`

## 1. Executive Synthesis
- Clean-room static analysis and Stage 4 C reconstruction of *King's Field* (North America, `SLUS-00158`) passed **`D0`–`D4`** and **`S0`–`S4`** before graduating to standalone **Tier R** (`../../Research/KingsField-PlayStation\`).
- All `12` baseline artifacts under `Corpus/standalone/` (`6,297` files / `716,862,355` B total, `IsReadOnly = true`) carry locked SHA-256 digests in `Dev/schemas/standalone_integrity.json`.
- Zero `DECOMPILE FAILED` markers remain across all `1,757` functions (`1,632` named game + `125` PS1-SDK SDK) and `259` `.c` translation units.

## 2. Empirical Hardware, Format & Engine Discoveries
1. **Multi-EXE Trampoline Handoff (`SLUS_001.58`):** Resident `SLUS_001.58` occupies only `0x80010000..0x80010800` (`4` game functions, `9` PS1-SDK/BIOS stubs), dedicating `0x80011000+` to mutually exclusive child executables (`OPEN.EXE`, `GAME.EXE`, `END.EXE`) dispatched by `kf_slus_main_exec_loop` via `g_kf_boot_next_exe_selector` (`0x800102f0`).
2. **March 1995 PS1-SDK SDK Horizon:** Embedded RCS stamps inside the executable (`intr.c`, `sys.c`, `pad.c`, `vsync.c`, `s_crwa.c` dated `1995/03/11`–`1995/03/14`) anchor the runtime ABI to early PS1-SDK (~3.0) with SN Systems CRT0 startup (`__SN_ENTRY_POINT`).
3. **Sector-Indexed `.T` Streaming (`FDAT.T`–`VAB.T`):** All `7` `/CD/COM/*.T` packs encode a `u16 entry_count` + `u16 sector_offsets[count + 1]` header where `sector_offsets[count] * 2048 == file_size`: `FDAT.T` (`70` slots / `45` active), `ITEM.T` (`548` / `403`: `103` `.tmd` + `300` `.tim`), `MO.T` (`448` / `405` `.mo`), `RTIM.T` (`75` / `72`), `RTMD.T` (`9` / `9`), `TALK.T` (`755` / `379` `.tim`), `VAB.T` (`331` / `122`: `56` `.vh` + `56` `.vb` + `10` `.seq`). `FDAT.T[0]` opens with `section_size = 0xfa00` (`6,400 * sizeof(KfMapCell)` = `80x80` dual-layer map).
4. **Pre-Rendered Dialogue & MDEC Offsets:** `TALK.T` stores pre-rendered `.TIM` dialogue cards rather than dynamic font glyphs for NPC speech boxes, while `OP/*.S` (`OP0..2.S`, `ED0..1.S`) embed `320x240` STR/MDEC headers (`0x80010160`) at `+8` bytes past each `2,336`-byte Mode 2 Form 2 XA subheader (`9` or `14` chunks/frame).
5. **Memory Card Framing (`BASLUS-00158`):** Save blocks wrap a `0x400`-byte `KfSaveHeader` (`"SC"` magic, Shift-JIS title, `3`-frame CLUT icon, `+0x200` checksum) ahead of a `0x3c00`-byte checksummed gameplay payload verified by `kf_game_mc_checksum_payload`.

## 3. Ghidra Lifting, Anchored Globals & LP32 Normalization Hazards
- **`patch_ps1_reexport_and_compat.py`:** Automated post-export pass normalizes Ghidra `SUBPIECE` / unaligned 3-byte loads, `undefined1[2|4]` stack temporaries, `void`-in-value-context calls, arity mismatches, and missing PS1 MMIO (`SPU_*`, `DMA_*`, `GPU_REG*`, `CDROM_*`, `TMR_*`) / GTE stubs inside `ghidra_compat.h` (`698` lines), yielding `0` `clangd 23.1.0` diagnostics without manual `.c` edits.
- **Anchored Struct Roots (`292` of `1,549` Globals):** `13` parent RAM addresses anchor typed struct fields (`g_kf_player_state` `148` members, `g_kf_entity_def_table` `25`, `g_kf_map_obj_table` `23`, `g_kf_entity_table` `19`, `g_kf_scene_control` `19`, `g_kf_map_obj_def_table` `16`, `g_kf_gfx_env` `15`, `g_kf_camera_state` `13`, `g_kf_magic_def_table` `8`, `g_kf_boot_exec_hdr` `2`, `g_kf_map_cells` `2`, `g_kf_tex_anim_slots` `1`, `g_kf_world_drop_table` `1`).
- **`LP32` Host Parity Discipline (`x86-windows-gnu`):** Linking lifted `GAME.EXE` / `END.EXE` translation units on `32`-bit `x86-windows-gnu` preserves `sizeof(void *) == 4` and `sizeof(long) == 4`, validating `17` recovered `Kf*` struct strides (`KfPlayerState == 0x160`, `KfSaveHeader == 0x400`) without 64-bit pointer inflation.

## 4. Empirical Validation Ledger (`260/260` MIPS + `10/10` Parity)
| Verification Check | Measured Result | Reference Artifact |
| --- | --- | --- |
| MIPS ELF32 Build (`zig cc -target mipsel-freestanding-eabi`) | `259/259` `.c` + `globals_defs.c` = `260` `ET_REL` `e_machine=8` `.o`, `0` errors / `0` warnings, `1,841,082` B `.a` | `Dev/schemas/d4_build_report.json` |
| `clangd 23.1.0 --check` (`compile_commands.json`) | `rc = 0`, `0` errors / `0` warnings across `kingsfield_types.h`, `core_01.c`, `open_01.c`, `game_01.c`, `end_01.c`, `sdk_01.c` | `Corpus/readable/compile_commands.json` |
| Parity Tests 1–4 (ABI & Retail Media Contracts) | `lp32_abi_and_struct_sizes`, `retail_psx_exe_headers`, `retail_t_archive_sector_tables`, `retail_fnd_mo_vab_str_headers` PASS | `Dev/scripts/d4_harness/parity_tests.c` |
| Parity Tests 5–6 (CD Checksum & Save Block) | `live_kf_cd_bcd_and_sector_checksum` (`0..99` BCD + `0x12345678` seed) & `live_kf_mc_save_checksum` (`0x3c00` B) PASS | `Corpus/readable/overlays/GAME.EXE/` |
| Parity Tests 7–10 (Math, Player Gauges & MDEC Init) | `live_kf_math_lerp_and_clamp`, `live_kf_math_angles_and_pose`, `live_kf_player_gauge_and_regen`, `live_kf_end_str_decoder_init` (`0x140 x 0xf0`) PASS | `Dev/scripts/d4_harness/parity_tests.c` |
| Standalone Clean-Room Unpacker (`psx_kf_unpack.py`) | Unpacked `7` `.T` archives, `FN.D` (`58` cp932 items), `2` `OP_TIM`, `5` `OP_STR` cleanly | `Dev/scripts/psx_kf_unpack.py` |

## 5. Clean-Room Constraints & Reproducibility Notes
- Zero retail binaries, `.gpr` databases, PII paths, or copyrighted assets are tracked in Git or packaged into `Archive/` snapshots (`-xr!Corpus\*`).
- All verification scripts live under `Dev/scripts/` and operate strictly over user-supplied read-only `Corpus/standalone/` media.
- Upstream decompilation and static verification avoid external prior-art sources cleanly (100% original analysis from `SLUS-00158` disc binaries).

## 6. Open Questions & Next Horizons (`D5` / `S5` / `R4+`)
- **Stage 2+ (`D5` / `S5`):** Evaluate `1:1` byte-matching `SLUS_001.58` / `OPEN.EXE` / `GAME.EXE` / `END.EXE` linker reconstruction and multi-region (`SLPS-00017` / `SLES-00201`) cross-corpus parity checks.
- **Stage 3 (`R3 -> R4/R5`):** Coordinate ongoing native PC (`win-x64`) & multi-platform advances in [`KingsFieldRecomp`](../../Personal/KingsFieldRecomp/README.md) (`v0.1.3` / `R3` on `reStation v0.1.1` + `reEngine`).
- **Stage 3 Boundary:** Keep runnable C# / SDL3 / OpenGL code strictly inside `../../Personal/KingsFieldRecomp` while retaining clean-room research artifacts here.
- **Notion Manual Page:** `Empirical Findings` (`<NOTION_FINDINGS_PAGE_ID>`).
