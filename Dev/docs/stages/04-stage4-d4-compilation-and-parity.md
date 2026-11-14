# Stage 4: ELF32 MIPS Compilation, LP32 Host Parity, and Clean-Room Asset Verification

- **Track:** `kings-field` (`ps1` / `native_ghidra_c`)
- **Stage 4 Verdict:** `D4` & `S4` verified (`259 / 259` C TUs compiled, `0` errors, `0` warnings, `10 / 10` host parity checks passed)

## 1. Dual-Pass Cross-Compilation & Parity Architecture (`scripts/build_and_verify_d4.py`)

`scripts/build_and_verify_d4.py` supports both Tier C (`decomps/ps1/kings-field/`) and graduated Tier R (`Dev/` + `Corpus/`) layouts automatically and generates `work/d4_build/gen/{globals_defs.c,host_stubs.c}` alongside `schemas/d4_build_report.json`:

1. **Pass 1 — PS1 MIPS Compilation & Archival (`mipsel-freestanding-eabi`):**
   - Invokes `zig cc -target mipsel-freestanding-eabi -mcpu=mips2 -msoft-float -ffreestanding -fno-builtin -std=gnu11 -O1 -g0 -Wno-everything` with `-Ireadable/include -include ghidra_compat.h`.
   - Compiles all `259` `readable/**/*.c` translation units plus `globals_defs.c` (`260` object files total).
   - Verifies ELF headers (`EI_CLASS=1` ELF32, `EI_DATA=1` LE, `ET_REL=1`, `e_machine=8` MIPS) across `260 / 260` `.o` outputs.
   - Archives all objects via `zig ar rcs` into `work/d4_build/libkings_field_d4.a` (`1,841,082` bytes) with `0` compiler errors and `0` warnings.
2. **Pass 2 — Host `LP32` Parity Runner (`x86-windows-gnu`):**
   - Compiles and links live lifted translation units (`game_01.c`, `game_02.c`, `game_03.c`, `game_04.c`, `game_10.c`, `end_01.c`) + `globals_defs.c` + minimal non-CRT `host_stubs.c` + `scripts/d4_harness/parity_tests.c` into `work/d4_build/host_parity/d4_parity_runner.exe`.
   - Links under 32-bit `x86-windows-gnu` (`sizeof(void *) == 4`, `sizeof(long) == 4`) so recovered pointer/struct strides match `ps1-psyq-mipsel` `LP32` semantics without 64-bit pointer truncation.

## 2. Host Parity Suite Results (`10 / 10` Passed)

Executed via `d4_parity_runner.exe --standalone-dir standalone` (`schemas/d4_build_report.json`):

| # | Test Case | Target Scope | Result |
| ---: | --- | --- | --- |
| 1 | `lp32_abi_and_struct_sizes` | `LP32` pointer/long width (`4B`) + all `17` recovered `Kf*` struct sizes (`KfPlayerState == 0x160`, `KfSaveHeader == 0x400`, etc.) | Pass |
| 2 | `retail_psx_exe_headers` | `SLUS_001.58`, `OPEN.EXE`, `GAME.EXE`, `END.EXE` `PS-X EXE` magic, `pc0`, `t_addr`, and `t_size` | Pass |
| 3 | `retail_t_archive_sector_tables` | Monotonic sector tables on all `7` `.T` archives (`2,236` total entries) + live `kf_game_t_archive_get_entry_size` | Pass |
| 4 | `retail_fnd_mo_vab_str_headers` | `CD/FN.D` (`1,188` B), `FDAT.T[0]` (`section_size == 0xfa00`), `MO.T[0]` (`KfMoHeader`), `VAB.T[0]` (`pBAV`), `OP/OP2.S` (`0x0160`) | Pass |
| 5 | `live_kf_cd_bcd_and_sector_checksum` | Live `kf_game_cd_int_to_bcd`, `kf_game_cd_bcd_to_int` (`0..99`), and `kf_game_cd_verify_sector_checksum` (`0x12345678` seed) | Pass |
| 6 | `live_kf_mc_save_checksum` | Live `kf_game_mc_checksum_payload` across full `0x3c00`-byte Memory Card save block payload | Pass |
| 7 | `live_kf_math_lerp_and_clamp` | Live `kf_game_math_step_linear_clamp`, `kf_game_math_lerp_q12`, and `kf_game_math_intervals_overlap` | Pass |
| 8 | `live_kf_math_angles_and_pose` | Live `kf_game_math_angle_diff_signed`, `kf_game_math_is_angle_cw_halfplane`, `kf_game_math_lerp_angle_q12`, `kf_game_math_lerp_pose_s16` | Pass |
| 9 | `live_kf_player_gauge_and_regen` | Live `kf_game_player_scale_gauge`, `kf_game_player_eval_combat_curve`, `kf_game_player_clamp_mp_regen`, `kf_game_player_clamp_hp_regen` | Pass |
| 10 | `live_kf_end_str_decoder_init` | Live `kf_end_init_str_decoder_state` initializing `320x240` (`0x140 x 0xf0`) double-buffered STR/MDEC upload geometry | Pass |

## 3. Standalone Clean-Room Unpacker & Study Gate (`S4`)

- Track-local unpacker archived at `scripts/psx_kf_unpack.py` (`decomp.manifest.json`: `"customUnpackerScript": "scripts/psx_kf_unpack.py"`), decoding retail `.T` containers (`FDAT.T` 70, `ITEM.T` 548, `MO.T` 448, `RTIM.T` 75, `RTMD.T` 9, `TALK.T` 755, `VAB.T` 331), `CD/FN.D`, and `OP/*.S` cleanly into `standalone/assets/`.
- `decomp_cli.py verify --track ps1/kings-field --tier D4` and `--tier S4` both pass with `0` errors and `0` warnings.
