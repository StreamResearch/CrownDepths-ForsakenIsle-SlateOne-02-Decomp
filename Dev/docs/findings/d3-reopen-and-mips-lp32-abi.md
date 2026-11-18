# Honest `D3` Re-Opening, `ps1-mipsel` `LP32` ABI & P-Code Lowering (`SLUS-00158`)

**Findings ID:** `d3-reopen-and-mips-lp32-abi` · **Parent Hub:** [Dev/docs/FINDINGS.md](../FINDINGS.md) · **Lowering Driver:** [patch_ps1_reexport_and_compat.py](../../scripts/patch_ps1_reexport_and_compat.py) · **Verifier:** [verify_track_d4.py](../../scripts/verify_track_d4.py)

This empirical report documents why `v0.2.0` honestly re-opens `currentDecompTier` to **`"D3"`** (`gates.D4.passed: false`, `d4ParityTier: "none"`) after exposing `-Wno-everything` and `.clangd` diagnostic masking, while preserving `Corpus/tiers/{D1_Raw..D4_CleanSource}`, coalescing all `259` chunks into `27` cohesive modules (`28` ELF32 MIPS `.o`), and keeping modular `-Wall -Wextra`-clean `d4_harness/` testing (`10/10` LP32 parity) active.

---

## 1. Empirical Baseline Audit: Exposing `-Wno-everything` & `.clangd` Masking

During `v0.1.0`, `Dev/scripts/build_and_verify_d4.py` passed `-Wno-everything` to `zig cc`, and `Corpus/readable/.clangd` carried `17` diagnostic suppression rules masking compiler type mismatches, implicit declarations, and uninitialized temporaries. Compiling all `259` `Corpus/readable/**/*.c` fragment files under strict `-Wall -Wextra -Wno-unused-parameter` (without `-Wno-everything` or `.clangd` suppressions) yielded these exact diagnostic counts:

| Audit Metric (`Corpus/readable/`, `259` `.c` Fragments) | Measured Count | File Coverage | `v0.2.0` Action & `v0.3.0` Target |
| :--- | ---: | ---: | :--- |
| **Hard C Compiler Errors (`-Wall -Wextra`)** | **`583`** | `162 / 259` files | Re-open `currentDecompTier: "D3"` (`gates.D4.passed: false`); fix in `v0.3.0` |
| **Compiler Warnings (`-Wall -Wextra -Wno-unused-parameter`)** | **`2,300`** | `226 / 259` files | Enforce `0` warnings on `d4_harness/*.c` now; full corpus in `v0.3.0` |
| **Decompiler Tell Hits (`6` tell families)** | **`55,123`** | `259 / 259` files | Record `craftsmanshipTellCount` in `d4_build_report.json`; eliminate in `v0.3.0` |
| **Pass-1 MIPS Archive (`-Wno-everything` baseline)** | **`28` `.o` (`1,588,042` B)** | `27` cohesive `.c` + `globals_defs.c` | Retained operational (`259` chunks in `D2_Structured`) for regression checks |
| **Pass-2 Modular `d4_harness/*.c` (`-Wall -Wextra -Wno-unused-parameter`)** | **`0` err / `0` warn (`10/10`)** | `4` modular harness files | Split `295`-line `parity_tests.c` into `<= 250`-SLOC C TUs (`T1`) |

### 1.1 The `17` `.clangd` Suppressions Scheduled for Removal in `v0.3.0`

| Diagnostic Group Masked in `Corpus/readable/.clangd` | Underlying Ghidra Artifact Cause | `v0.3.0` Cleanup Strategy |
| :--- | :--- | :--- |
| `int-conversion`, `pointer-integer-compare`, `incompatible-pointer-types` | Untyped `u32`/`void *` pointer arithmetic & raw address integers | Explicit `(uintptr_t)` casts & typed pointers (`d4_rewrites/`) |
| `incompatible-function-pointer-types`, `deprecated-non-prototype`, `strict-prototypes` | Empty-arg `()` prototypes on indirect callbacks (`code *`) | Typed `KfVoidCallback` / `KfIntCallback` & explicit `(void)` args |
| `incompatible-library-redeclaration`, `implicit-function-declaration` | Duplicate SDK/CRT stubs across `OPEN`/`GAME`/`END` | Cohesive `sdk/` TUs & explicit header prototypes |
| `return-type`, `pointer-sign`, `constant-conversion` | Void promotion mismatches & `u8 *` vs `char *` strings | Explicit return types & matching signedness |
| `shift-count-overflow`, `shift-count-negative`, `uninitialized` | Decompiler `ZEXT`/`SUBPIECE` & ABI register read-before-write | Remove dead bit shifts & explicit local initializers |
| `unused-value`, `unused-variable`, `unused-parameter` | Dead register scratch temporaries (`in_*`, `extraout_*`) | Prune unused temps (`-Wno-unused-parameter` kept only where ABI requires) |

### 1.2 Breakdown of `55,123` Raw Decompiler Artifact & Tell Hits Across `Corpus/readable/*.c`

| Artifact / Tell Category (`D3` Baseline) | Observed Pattern Families | Measured Hits | `v0.3.0` Resolution |
| :--- | :--- | ---: | :--- |
| **Raw Ghidra Tokens & Prefixes** | `uVar*`/`iVar*`/`puVar*`, `DAT_*`/`UNK_*`/`PTR_*`/`LAB_*`/`SUB_*`/`switchD_*` | `40,200` | AST context locals + `(program, address)` globals |
| **Undefined Types & Stack / ABI Temporaries** | `undefined[1248]`, `unaff_*`, `in_*`, `extraout_*`, `*Stack*`, `stack0x*` | `10,483` | Standardized `u8..s64` types & explicit structs |
| **Diagnostic Comments & Legacy Headers** | `/* WARNING: ... */`, `// Function: ...` fragment headers | `4,007` | Cohesive Doxygen `@symbol`/`@address` blocks |
| **Raw Pointer Casts & Unstructured Loops** | `(void *)0x0`, `(*(code *)`, `goto LAB_*`, `while (true)` | `1,101` | `NULL`, typed `Kf*Callback` casts, structured C loops |
| **Unaligned Subpiece / Shift Emulations** | `*(uint8_t *)&...`, `_gh_get*`/`_gh_set*`, byte-shift extraction | `122` | Clean struct field accesses & `Q12` helpers |

- **Honest Tier Policy (`v0.2.0`):** `Dev/research.manifest.json` sets `currentDecompTier: "D3"`, `goalDecompTier: "D4"`, and `gates.D4.passed: false`, while `Dev/schemas/d4_build_report.json` (`schemaVersion: 2`) explicitly logs `craftsmanshipTellCount` (`55,791` live verifier count / `55,123` baseline recon / `0` synthetic) alongside `compilerErrorCount: 0` (baseline archive pass) and `assertionsPassedCount: 10` (`10/10` parity).

---

## 2. `ps1-mipsel` `LP32` ABI Invariants & `x86-windows-gnu` Parity

Sony PlayStation R3000A binaries adhere strictly to `LP32` (`sizeof(int) == sizeof(long) == sizeof(void *) == 4`, little-endian). Compiling host parity runners on 64-bit Windows (`LLP64`, `8`-byte pointers) or 64-bit Linux (`LP64`, `8`-byte `long` and pointers) silently inflates embedded `void *` fields inside `KfEntityDef`, `KfEntityState`, `KfPlayerState`, `KfTArchiveSlot`, `KfSceneControl`, and `KfTextureAnimSlot`.

| Cross-Compilation Constraint | Verified `ps1-mipsel` / `x86-windows-gnu` Solution |
| :--- | :--- |
| **`LP32` `4`-Byte Pointer & `long` Width** | Pass 2 targets **`x86-windows-gnu`** (`sizeof(void *) == 4`, `sizeof(long) == 4`), validating exact `sizeof(...)` across all `17` `Kf*` structs (`KfGfxEnv == 0xe0`, `KfCameraState == 0x34`, `KfSceneControl == 0x1c`, `KfMapCell == 0x0a`, `KfMapObjDef == 0x18`, `KfMapObjState == 0x44`, `KfWorldDrop == 0x18`, `KfTextureAnimSlot == 0x18`, `KfEntityDef == 0x78`, `KfEntityState == 0x7c`, `KfPlayerState == 0x160`, `KfTArchiveSlot == 0x0c`, `KfItemDef == 0x20`, `KfMagicDef == 0x44`, `KfSaveHeader == 0x400`, `KfMoHeader == 0x14`, `KfFdatHeader == 0x04`). |
| **Zig MIPS CPU Selection (`-mcpu=mips2`)** | Pass 1 compiles with `zig cc -target mipsel-freestanding-eabi -mcpu=mips2 -msoft-float -ffreestanding -fno-builtin -std=gnu11 -O1` (`-mcpu=mips1` hits LLVM `MipsISD::Sync` crashes), producing verified little-endian O32 ELF32 `ET_REL` `e_machine=8` objects (`28 / 28`: `27` cohesive modules + `globals_defs.c`). |
| **MinGW `<string.h>` Collision Avoidance** | `Dev/scripts/d4_harness/` includes `kingsfield_types.h` and `kingsfield_globals.h` directly while omitting `kingsfield_functions.h`, and `build_and_verify_d4.py` / `d4_synthetic_corpus.py` filter `21` `LIBC_SYMS` (`printf`, `sprintf`, `rand`, `srand`, `memcpy`, `memset`, `memmove`, `memcmp`, `strcpy`, `strncpy`, `strcmp`, `strncmp`, `strlen`, `strcat`, `malloc`, `free`, `calloc`, `realloc`, `abs`, `qsort`, `bsearch`) out of generated `host_stubs.c` while keeping `typedef struct __jmp_buf_tag __jmp_buf_tag;` and `builtin_strncpy` for Win32 MinGW parity. |
| **Zero-Media Offline CI (`--offline-synthetic`)** | `d4_synthetic_corpus.py` synthesizes minimal valid `PS-X EXE` headers, `.T` sector tables, `CD/FN.D`, `OP/OP2.S`, and `LP32` C translation units inside `--data-dir` so both `build_and_verify_d4.py --offline-synthetic` and `verify_track_d4.py --offline-synthetic` execute all `10/10` parity assertions with zero retail disc files. |

### 2.1 Modular Type Headers (`Dev/schemas/types/*.h` — `3` Enums, `21` Typedefs, `46` Structs)

| Header File (`Dev/schemas/types/`) | Lines | Structs | Enums | Clean-Room `v0.2.0` Status |
| :--- | ---: | ---: | ---: | :--- |
| [primitives_and_sdk.h](../../schemas/types/primitives_and_sdk.h) | `273` | `27` | `0` | Vendor SDK prose neutralized to neutral PS1 GPU/GTE/CD/SPU ABI labels |
| [kf_containers_and_io.h](../../schemas/types/kf_containers_and_io.h) | `102` | `8` | `2` | `KfExeSelector`, `KfTArchiveId`, `.T`/`FDAT`/`MO`/`RTIM`/`Item`/`Magic`/`Save` |
| [kf_world_and_render.h](../../schemas/types/kf_world_and_render.h) | `145` | `8` | `0` | `KfGfxEnv`, `KfCameraState`, `KfSceneControl`, `KfMapCell`, `KfMapObj*`, `KfWorldDrop` |
| [kf_actor_combat_ui.h](../../schemas/types/kf_actor_combat_ui.h) | `182` | `3` | `1` | `KfEntityKind`, `KfEntityDef`, `KfEntityState`, `KfPlayerState` (`0x160` B) |

### 2.2 Verified `LP32` Struct Sizes (`test_lp32_abi_and_struct_sizes`)

Every struct size below is asserted directly at compile/runtime inside Pass-2 `x86-windows-gnu` parity builds (`sizeof(void *) == 4`, `sizeof(long) == 4`):

| Struct (`Dev/schemas/types/*.h`) | Header Module | Verified `LP32` Bytes | Hex Size |
| :--- | :--- | ---: | :--- |
| `KfFdatHeader` | `kf_containers_and_io.h` | `4` | `0x04` |
| `KfMapCell` | `kf_world_and_render.h` | `10` | `0x0a` |
| `KfTArchiveSlot` | `kf_containers_and_io.h` | `12` | `0x0c` |
| `KfRtimHeader` | `kf_containers_and_io.h` | `16` | `0x10` |
| `KfMoHeader` | `kf_containers_and_io.h` | `20` | `0x14` |
| `KfMapObjDef` | `kf_world_and_render.h` | `24` | `0x18` |
| `KfWorldDrop` | `kf_world_and_render.h` | `24` | `0x18` |
| `KfTextureAnimSlot` | `kf_world_and_render.h` | `24` | `0x18` |
| `KfSceneControl` | `kf_world_and_render.h` | `28` | `0x1c` |
| `KfItemDef` | `kf_containers_and_io.h` | `32` | `0x20` |
| `KfCameraState` | `kf_world_and_render.h` | `52` | `0x34` |
| `KfMagicDef` | `kf_containers_and_io.h` | `68` | `0x44` |
| `KfMapObjState` | `kf_world_and_render.h` | `68` | `0x44` |
| `KfEntityDef` | `kf_actor_combat_ui.h` | `120` | `0x78` |
| `KfEntityState` | `kf_actor_combat_ui.h` | `124` | `0x7c` |
| `KfGfxEnv` | `kf_world_and_render.h` | `224` | `0xe0` |
| `KfPlayerState` | `kf_actor_combat_ui.h` | `352` | `0x160` |
| `KfSaveHeader` | `kf_containers_and_io.h` | `1,024` | `0x400` |

### 2.3 Modular `d4_harness/` Split & `10/10` Parity Matrix (`<= 250` SLOC / TU)

Replacing the monolithic `295`-line `parity_tests.c`, Pass-2 globbing compiles `4` modular harness files (`-Wall -Wextra -Wno-unused-parameter`, `0` warnings):

| Harness File (`Dev/scripts/d4_harness/`) | Responsibility & Verified Checks |
| :--- | :--- |
| `parity_harness.h` | Shared `Kf*` test declarations, `read_le16`/`read_le32`, `read_file_alloc`, `ParityTest` struct |
| `parity_abi_and_media_tests.c` | Tests `1..4`: `lp32_abi_and_struct_sizes`, `retail_psx_exe_headers`, `retail_t_archive_sector_tables`, `retail_fnd_mo_vab_str_headers` |
| `parity_gameplay_and_str_tests.c` | Tests `5..10`: `live_kf_cd_bcd_and_sector_checksum`, `live_kf_mc_save_checksum`, `live_kf_math_lerp_and_clamp`, `live_kf_math_angles_and_pose`, `live_kf_player_gauge_and_regen`, `live_kf_end_str_decoder_init` |
| `parity_runner_main.c` | CLI `--standalone-dir` runner emitting deterministic JSON parity summary (`10/10`) |

---

## 3. Pre-Assembly P-Code Lowering & Compat Pipeline ([ps1_compat_helpers.py](../../scripts/ps1_compat_helpers.py))

Before Stage 4 compiles `Corpus/work/reexported/<program>/funcs/*.c`, [patch_ps1_reexport_and_compat.py](../../scripts/patch_ps1_reexport_and_compat.py) + [ps1_compat_helpers.py](../../scripts/ps1_compat_helpers.py) apply deterministic code-span transforms (skipping comments and string literals via `code_spans`):

1. **Balanced Subpiece Rewrites (`._off_sz_` for `1/2/3/4` bytes):** Walks backward across balanced `[...]`, `(...)`, `->`, and `.` lvalues:
   - `3`-byte unaligned loads/stores (`sz == 3`) emit `_gh_set3((uint8_t *)&(expr) + off, ...)` for assignments or `_gh_get3(...)` / shifted arithmetic reads.
   - `1`/`2`/`4`-byte accesses rewrite to `(*((uint{8,16,32}_t *)((uint8_t *)&(expr) + off)))` on lvalues or shifted casts on arithmetic expressions.
2. **Unaligned Stack Arrays & Target Struct Casts:** Converts `undefined1 buf[2|4]` stack buffers and `_Stack_*` stores into `*(uint{16,32}_t *)(void *)(buf) = ...`, flattens `switchD_<hex>::switchdataD_<hex>`, renames `2MBYTE_OBJ_B4` -> `fn_2MBYTE_OBJ_B4` and `$N` -> `reg_rN`, and resolves `CStack_68.pos`, `g_kf_player_pos_x->`, and `g_kf_map_obj_table` address-of indexing.
3. **Cross-Overlay Void-Return Promotion & Arity Alignment:** `_find_void_value_callers` detects `void`-prototyped functions whose return value is cast, assigned, compared, or returned across any of the `4` executables, promoting both `functions.json` signatures and bodies to `uint32_t` with `return 0;`, while `_reconcile_calls` aligns non-variadic argument counts (`0`-padding or trimming extra register parameters; exempting `setCopReg`, `copFunction`, `printf`, `sprintf`, `FntPrint`).
4. **Multi-EXE SDK Deduplication (`_dedupe_sdk_files`):** Because `SLUS_001.58`, `OPEN.EXE`, `GAME.EXE`, and `END.EXE` each link copies of PS1 SDK routines (`125` total SDK entries across `sdk_01..sdk_05.c`), `_dedupe_sdk_files` renames repeated definitions to `<name>_dup_<addr>` and deduplicates `kingsfield_functions.h` prototypes so Pass-1/Pass-2 compilation never hits multiple-definition linker errors.
5. **`KF_PS1_COMPAT_EXTS` Hardware MMIO & GTE Stubs (`ghidra_compat.h`):** Emits `SUB84`/`SUB82`/`SUB81`, `ZEXT48`/`ZEXT44`/`SEXT48`, `ABS`, `_gh_get{3,5,6,7}`/`_gh_set{3,5,6,7}`, `setCopReg`/`copFunction` no-op stubs, `41` `PS1_MMIO_16` hardware registers (`SPU_*`, `VOICE_00_*`, `JOY_MCD_*`, `TMR_*`, `I_STAT`/`I_MASK`), `37` `PS1_MMIO_32` registers (`CDROM_*`, `DMA_*`, `GPU_REG*`, `MDEC_REG*`, `SPU_VOICE_KEY_*`), and unresolved `PTR_*`/`LAB_*`/`SUB_*`/`stack0x*`/`_UNK_*`/`gte_*` extern declarations.

| Transformation | Raw Ghidra Pattern | Lowered C11 Output (`patch_ps1_reexport_and_compat.py`) |
| :--- | :--- | :--- |
| **`3`-Byte Subpiece Write** | `x._1_3_ = val;` | `_gh_set3((uint8_t *)&(x) + 1, (uint32_t)(val));` |
| **`1`/`2`/`4`-Byte Subpiece** | `field._0_2_ = s;` | `(*((uint16_t *)((uint8_t *)&(field) + 0))) = s;` |
| **Unaligned Stack Store** | `undefined1 buf[4]; buf = v;` | `*(uint32_t *)(void *)(buf) = (uint32_t)(v);` |
| **Indirect Callback Call** | `(*cb_expr)(arg);` | `(*(code *)(uintptr_t)(cb_expr))(arg);` |
| **Multi-EXE Duplicate SDK** | Repeated `sdk_01..05.c` symbol | Renamed `<sym>_dup_<addr>` + prototype in `kingsfield_functions.h` |

### 3.1 `KF_PS1_COMPAT_EXTS` Register, Clean-Room Scrub & Macro Inventory

- **Schema & Header Clean-Room Scrub (`v0.2.0`):** `call_graph.json` zeroes all `111` embedded retail `"strings"` arrays (`strings: []`) while preserving edges and `meta.strings_json_counts`; `Dev/schemas/types/primitives_and_sdk.h`, `globals_map.json`, `functions_catalog.json`, and `shards/stage3_*.json` neutralize vendor SDK brand mentions to neutral PS1 ABI descriptions; and `Dev/schemas/s4_verify_report.json` follows Standard 18 `schemaVersion: 2`.
- **Portable Pipeline Resolution:** `patch_ps1_reexport_and_compat.py` resolves external R&D helpers via `--tools-dir`, `RD_DECOMP_TOOLS`, or relative sibling paths (`../../Personal/R&D/Dev/tools/decomp`), supports `--data-dir` / `--log-dir`, and fails closed with `MISSING_CORPUS_MEDIA` JSON when `work/reexported` is absent.

| Compatibility Layer Component | Symbol / Macro Count | Purpose in `Corpus/readable/` Builds |
| :--- | ---: | :--- |
| `PS1_MMIO_16` (`volatile uint16_t`) | `41` | `SPU_MAIN_VOL_*`, `VOICE_00_*`, `JOY_MCD_*`, `TMR_*`, `I_STAT`, `I_MASK` |
| `PS1_MMIO_32` (`volatile uint32_t`) | `37` | `CDROM_REG0..3`, `DMA_*`, `GPU_REG0..1`, `MDEC_REG0..1`, `SPU_VOICE_KEY_*` |
| Unaligned Load/Store Helpers | `8` (`_gh_get*`, `_gh_set*`) | Portable `3`/`5`/`6`/`7`-byte endian-safe subpiece memory helpers |
| Width & GTE Macros | `9` | `SUB84`/`82`/`81`, `ZEXT48`/`44`, `SEXT48`, `ABS`, `setCopReg`, `copFunction` |

---

## 4. `v0.3.0` Convergence Path (`D3 -> D4_CleanSource` / `D4a`) & Verification Commands

To eliminate all `583` compiler errors, `2,300` warnings, and `55,123` decompiler tells permanently while keeping `Corpus/readable/` auditable:

1. **Preserve Multi-Tier Snapshots Locally (`Corpus/tiers/`):** Seeded in `v0.2.0` via `Dev/scripts/materialize_decomp_tiers.py`: `D1_Raw` (from `standalone/decompiled/`), `D2_Structured` (`259` chunks from `work/reexported/`), `D3_Mapped` (`27` cohesive modules), and `D4_CleanSource` (synced to `Corpus/readable/`).
2. **`(program, address)` Clean-Room Shards (`Dev/schemas/d4_rewrites/`):** Store declarative rewrite metadata (zero C bodies or retail strings) keyed by `(program, address)` so `OPEN.EXE`, `GAME.EXE`, and `END.EXE` never collide at `0x80011000`.
3. **Human-Readable Function Rewrites (`v0.3.0`):** Within the `27` cohesive domain and PS1 SDK translation units established in `v0.2.0`, convert raw global arrays/pointers into typed C declarations, rewrite all `1,757` functions to `-Wall -Wextra -Wno-unused-parameter` `0`-warning / `0`-tell C, and cut `.decomp` `engineId` over from `"reStation"` to `"reSlate"`.

```powershell
# Reproducible v0.2.0 offline & live build/verifier workflow
python -B Dev/scripts/build_and_verify_d4.py --offline-synthetic --data-dir "$env:TEMP\kf-d4" --log-dir Dev/logs
python -B Dev/scripts/verify_track_d4.py --offline-synthetic --data-dir "$env:TEMP\kf-d4" --log-dir Dev/logs
python -B Dev/scripts/patch_ps1_reexport_and_compat.py --data-dir "$env:TEMP\kf-empty" --log-dir Dev/logs
```
