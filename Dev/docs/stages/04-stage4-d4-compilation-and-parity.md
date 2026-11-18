# Stage 4: ELF32 MIPS Compilation, LP32 Host Parity & Clean-Room Verification

- **Track:** `kings-field` (`ps1` / `native_ghidra_c`)
- **Stage 4 Verdict (`v0.2.0`):** `D3` honest baseline + `Corpus/tiers/{D1_Raw..D4_CleanSource}` materialized + active `28`-object ELF32 MIPS build across `27` cohesive C modules (`-Wno-everything` on `D3` bodies pending `v0.3.0`), `0`-warning modular `d4_harness/*.c` (`-Wall -Wextra -Wno-unused-parameter`), `10/10` host parity checks, and `S4` study gate verified.

## 1. Dual-Pass Cross-Compilation & Modular Harness ([build_and_verify_d4.py](../../scripts/build_and_verify_d4.py))

`Dev/scripts/build_and_verify_d4.py` supports both live `Corpus/` and `--offline-synthetic` (`Dev/scripts/d4_synthetic_corpus.py`), generates `work/d4_build/host_parity/{globals_defs.c,host_stubs.c}` alongside Standard 18 `Dev/schemas/d4_build_report.json` (`schemaVersion: 2`), and leaves `currentDecompTier` honestly at `"D3"` (`gates.D4.passed: false`) until `v0.3.0` resolves `583` `-Wall -Wextra` errors, `2,300` warnings, and `55,791` decompiler tell hits across the `1,757` functions (with `259` raw chunks preserved in `Corpus/tiers/D2_Structured/`):

1. **Pass 1 — PS1 MIPS Compilation & Archival (`mipsel-freestanding-eabi`):**
   - Invokes `zig cc -target mipsel-freestanding-eabi -mcpu=mips2 -msoft-float -ffreestanding -fno-builtin -std=gnu11 -O1 -g0 -Wno-everything` with `-Ireadable/include -include ghidra_compat.h`.
   - Compiles all `27` coalesced `readable/{src,sdk}/**/*.c` translation units plus `globals_defs.c` (`28` object files total).
   - Verifies ELF headers (`EI_CLASS=1` ELF32, `EI_DATA=1` LE, `ET_REL=1`, `e_machine=8` MIPS) across `28 / 28` `.o` outputs and archives via `zig ar` into `work/d4_build/libkings_field_d4.a` (`1,588,042` bytes).
2. **Pass 2 — Host `LP32` Parity Runner (`x86-windows-gnu`):**
   - Compiles and links `5` coalesced `src/` modules (`game_fixed_math.c`, `game_cd_and_t_archives.c`, `game_save_and_memcard.c`, `game_player_and_combat.c`, `end_credits_and_main.c`) + `globals_defs.c` + minimal non-CRT `host_stubs.c` + Pass-2 globbed modular harness TUs under `Dev/scripts/d4_harness/` (`parity_harness.h`, `parity_abi_and_media_tests.c`, `parity_gameplay_and_str_tests.c`, `parity_runner_main.c`, each `<= 250` SLOC compiled with `-Wall -Wextra -Wno-unused-parameter` `0` warnings) into `d4_parity_runner.exe`.
   - Links under 32-bit `x86-windows-gnu` (`sizeof(void *) == 4`, `sizeof(long) == 4`) so recovered pointer/struct strides match `ps1-mipsel` `LP32` semantics without 64-bit pointer truncation.

## 2. Host Parity Suite Results (`10 / 10` Passed)

Executed via `d4_parity_runner.exe` against `--standalone-dir` (live `Corpus/standalone` or synthetic fixture directory):

| # | Test Case | Target Scope | Result |
| ---: | --- | --- | --- |
| 1 | `lp32_abi_and_struct_sizes` | `LP32` pointer/long width (`4B`) + all `17` recovered `Kf*` struct sizes (`KfPlayerState == 0x160`, `KfSaveHeader == 0x400`) | Pass |
| 2 | `retail_psx_exe_headers` | `SLUS_001.58`, `OPEN.EXE`, `GAME.EXE`, `END.EXE` `PS-X EXE` magic, `pc0`, `t_addr`, and `t_size` | Pass |
| 3 | `retail_t_archive_sector_tables` | Monotonic sector tables on all `7` `.T` archives (`2,236` total slots) + live `kf_game_t_archive_get_entry_size` | Pass |
| 4 | `retail_fnd_mo_vab_str_headers` | `CD/FN.D` (`1,188` B), `FDAT.T[0]` (`section_size == 0xfa00`), `MO.T[0]` (`KfMoHeader`), `VAB.T[0]` (`pBAV`), `OP/OP2.S` (`0x0160`) | Pass |
| 5 | `live_kf_cd_bcd_and_sector_checksum` | Live `kf_game_cd_int_to_bcd`, `kf_game_cd_bcd_to_int` (`0..99`), and `kf_game_cd_verify_sector_checksum` (`0x12345678` seed) | Pass |
| 6 | `live_kf_mc_save_checksum` | Live `kf_game_mc_checksum_payload` across full `0x3c00`-byte Memory Card save block payload | Pass |
| 7 | `live_kf_math_lerp_and_clamp` | Live `kf_game_math_step_linear_clamp`, `kf_game_math_lerp_q12`, and `kf_game_math_intervals_overlap` | Pass |
| 8 | `live_kf_math_angles_and_pose` | Live `kf_game_math_angle_diff_signed`, `kf_game_math_is_angle_cw_halfplane`, `kf_game_math_lerp_angle_q12`, `kf_game_math_lerp_pose_s16` | Pass |
| 9 | `live_kf_player_gauge_and_regen` | Live `kf_game_player_scale_gauge`, `kf_game_player_eval_combat_curve`, `kf_game_player_clamp_mp_regen`, `kf_game_player_clamp_hp_regen` | Pass |
| 10 | `live_kf_end_str_decoder_init` | Live `kf_end_init_str_decoder_state` initializing `320x240` (`0x140 x 0xf0`) double-buffered STR/MDEC upload geometry | Pass |

## 3. Standalone Verification, Decoders & Study Gate (`S4`)

- Independent verifier [verify_track_d4.py](../../scripts/verify_track_d4.py) checks `D3` baseline integrity, `Corpus/tiers/{D1_Raw..D4_CleanSource}` presence, `d4_harness/` `<= 250` SLOC and `0`-warning builds, `28` ELF32 MIPS `.o` headers (`27` coalesced `.c` + `globals_defs.c`), `10/10` parity, and `--offline-synthetic` execution (`materialize_decomp_tiers.py` also verified cleanly).
- Clean-room unpacker [psx_kf_unpack.py](../../scripts/psx_kf_unpack.py) validates all `23` disc SHA-256 checksums (`1 MiB` chunked for `> 64 MiB` media) and delegates across `6` `<= 250`-SLOC modular decoders (`kf_t_archives.py`, `kf_world_fdat.py`, `kf_items_magic_talk.py`, `kf_meshes_mo_rtmd.py`, `kf_audio_vab_seq.py`, `kf_save_memcard.py`).
- `decomp_cli.py verify --track . --tier D3` (with `clangd --check`) and `--tier S4 --no-clangd` both pass cleanly.
