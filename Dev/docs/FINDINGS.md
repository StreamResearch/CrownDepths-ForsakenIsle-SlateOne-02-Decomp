# CrownDepths ForsakenIsle (SlateOne) 02 Decomp — Empirical Findings & Discovery Hub

**Version:** `0.2.0` (`2026-11-18`) · **Axis:** `hybrid` (`D3 / S4 / R2 -> R3`) · **Serial:** `SLUS-00158`

---

## 1. Empirical Findings Routing Table

This hub indexes the three deep empirical findings spokes under `Dev/docs/findings/` alongside the stage pipeline dossiers under `Dev/docs/stages/`, consolidating verified PlayStation 1 (`SLUS-00158`) memory geometry, `.T` / `FDAT[48]` binary formats, and `v0.2.0` LP32/clean-room compiler discoveries.

| Findings Spoke | Primary Scope | Verified Artifacts & Targets |
| :--- | :--- | :--- |
| [four-exe-trampoline-and-ram-layout.md](findings/four-exe-trampoline-and-ram-layout.md) | `SLUS_001.58` `4,096`-B resident loader, `InitHeap` (`0x1e7d4c`), `0x80011000` shared overlay base (`OPEN.EXE`, `GAME.EXE`, `END.EXE`), `1,757` functions, `1,549` globals | `call_graph.json`, `globals_map.json`, `core_01.c`, `parity_abi_and_media_tests.c` |
| [fdat-master-db-and-t-streaming.md](findings/fdat-master-db-and-t-streaming.md) | `7` `.T` sector tables (`2,236` slots), `FDAT.T` zone `0..7`+`10` triplets, `FDAT[47]` VRAM atlas, `FDAT[48]` `9`-section boot DB, `FDAT[49..66]` weapons, `VAB.T` `.vh` fix, `BASLUS-00158` saves | `psx_kf_unpack.py`, `kf_world_fdat.py`, `kf_audio_vab_seq.py`, `kf_save_memcard.py` |
| [d3-reopen-and-mips-lp32-abi.md](findings/d3-reopen-and-mips-lp32-abi.md) | Re-opening honest `D3` baseline (`583` errors / `2,300` warnings / `55,123` tells under `-Wall -Wextra`), `ps1-mipsel` `LP32` (`4`-B pointers), P-code lowering, modular `d4_harness/` | `patch_ps1_reexport_and_compat.py`, `ps1_compat_helpers.py`, `build_and_verify_d4.py`, `verify_track_d4.py` |

- **Stage Pipeline Guides (`Dev/docs/stages/`):** [01 Call Graph & Clusters](stages/01-stage1-callgraph-and-clusters.md) · [02 Types & Globals](stages/02-stage2-types-and-globals.md) · [03 Function Catalog](stages/03-stage3-function-catalog.md) · [04 Compilation & Parity](stages/04-stage4-d4-compilation-and-parity.md).

---

## 2. Executive Synthesis (`v0.2.0`)

- **Full `23`-File + `.bin` SHA-256 Gate:** [standalone_integrity.json](../schemas/standalone_integrity.json) upgrades from `12` sample entries (which previously included `0`-byte `.gpr` metadata) to `schemaVersion: 2` covering all `23` extracted `SLUS-00158` disc files (`OP/ED1.S` `98,315,232` B included) plus optional `King's Field (USA).bin` (`258,183,744` B), hashed in `1 MiB` chunks inside [psx_kf_unpack.py](../scripts/psx_kf_unpack.py).
- **Honest `D3` Decomp Reset Pending `v0.3.0`:** Removing `-Wno-everything` and `17` `.clangd` diagnostic suppressions exposes `583` hard errors and `2,300` warnings across the `259` mechanical chunks preserved in `Corpus/tiers/D2_Structured/`, alongside `55,791` decompiler tell hits. [materialize_decomp_tiers.py](../scripts/materialize_decomp_tiers.py) preserves `D1_Raw`..`D4_CleanSource` locally and coalesces all `1,757` functions into `27` cohesive modules (`Corpus/readable/` & `D3_Mapped`), while `Dev/research.manifest.json` reports `currentDecompTier: "D3"` (`gates.D4.passed: false`, `d4ParityTier: "none"`) with an active `28`-object MIPS build and `10/10` warning-free `d4_harness/` LP32 parity suite.
- **`FDAT[48]` Master DB & `VAB.T` `.vh` Resolution:** `GAME.EXE` `kf_game_mount_t_archives` (`0x80015dd4`) unpacks `9` length-prefixed sections from `FDAT[48]` (`110,592` B) into resident gameplay tables (`KfMapObjDef[320]`, `KfMagicDef[18]`, `LevelUpGrowth[100]`, and `2` base `.TMD` packs). Fixing `VAB.T` `.vh` unpacking to `<IIIHHHHBBBBI` at `+4` (`kf_audio_vab_seq.py`) resolves the `programs=16511` anomaly cleanly (`programs=2, tones=23, vags=22` on `VAB.T[0]`).
- **Clean-Room Firewall & `.decomp` Package:** All `111` embedded retail `"strings"` arrays in [call_graph.json](../schemas/call_graph.json) are cleared to `[]`, vendor SDK brands are neutralized across `Dev/schemas/` and `Dev/docs/`, and [export_decomp_bundle.py](../scripts/export_decomp_bundle.py) emits `CrownDepths-ForsakenIsle-SlateOne-02.decomp` (`reStation` `0.2.x`) validated by `PsxCleanRoomValidator`.

---

## 3. Consolidated Hardware & Format Highlights

| Subsystem | Key Empirical Finding | Source Evidence |
| :--- | :--- | :--- |
| **`SLUS_001.58` Trampoline** | `pc0 = 0x80010128`, `t_addr = 0x80010000`, `t_size = 0x800` (`2,048` B); `InitHeap(..., 0x1e7d4c)` -> `Load`/`Exec` loop at `0x80011000` (`OPEN`, `GAME`, `END`) | [four-exe-trampoline-and-ram-layout.md](findings/four-exe-trampoline-and-ram-layout.md) |
| **`.T` Sector Tables** | `u16 count + u16 offs[count+1]` where `offs[count] * 2048 == size`: `FDAT` (`70`/`45`), `ITEM` (`548`/`403`), `MO` (`448`/`405`), `RTIM` (`75`/`72`), `RTMD` (`9`/`9`), `TALK` (`755`/`379`), `VAB` (`331`/`122`) | [t-archives-fnd-and-op-str.md](specifications/t-archives-fnd-and-op-str.md) |
| **`FDAT.T` Map & Boot DB** | Zones `0..7` (`0..23`) + `10` (`30..32`) triplets (`KfMapCell[6400]`, `[12992, 3200, 8400, 2048]`, VRAM); `FDAT[47]` (`503,808` B); `FDAT[48]` `9` tables; `FDAT[49..66]` (`16` active view-models) | [fdat-master-db-and-t-streaming.md](findings/fdat-master-db-and-t-streaming.md) |
| **`VAB.T` `.vh` & `SEQ`** | `<IIIHHHHBBBBI` at `+4` fixes `VAB.T[0]` (`ver=6, fsize=142912, progs=2, tones=23, vags=22`); `10` `pQES` tracks (`res=480` PPQN, `3`-byte BE tempo) | [audio-vab-and-seq.md](specifications/audio-vab-and-seq.md) |
| **`BASLUS-00158` Saves** | `0x400`-B `KfSaveHeader` (`"SC"`, `0x13` `3`-frame icon, `+0x200` `checksum`) + `0x3c00`-B byte-sum payload (`kf_game_mc_checksum_payload @ 0x80023dd0`) | [save-memcard-baslus00158.md](specifications/save-memcard-baslus00158.md) |
| **`LP32` Build & Harness** | `28` ELF32 MIPS `.o` (`27` modules + `globals_defs`) -> `libkings_field_d4.a` (`1,588,042` B); `4`-file `d4_harness/` `0` warn (`10/10`) | [d3-reopen-and-mips-lp32-abi.md](findings/d3-reopen-and-mips-lp32-abi.md) |

---

## 4. Empirical Validation Ledger (`v0.2.0` — `D3 / S4 / R2 -> R3`)

| Verification Check | Measured Result | Reference Artifact |
| :--- | :--- | :--- |
| **MIPS ELF32 Static Build (`Pass 1`)** | `27` cohesive `.c` + `globals_defs.c` = `28` `ET_REL` `e_machine=8` `.o` (`259` raw chunks kept in `D2_Structured`; `55,791` tells in `d4_build_report.json`) | [d4_build_report.json](../schemas/d4_build_report.json) |
| **Host LP32 Parity (`Pass 2`)** | `10/10` assertions (`LP32` `17` structs, `4` EXEs, `7` `.T` packs, `FN.D`/`MO`/`VAB`/`OP2.S`, CD BCD/CRC, MC save, math/lerp, angles/pose, player gauges, STR init); `d4_harness/*.c` `0` warnings | [parity_runner_main.c](../scripts/d4_harness/parity_runner_main.c), [verify_track_d4.py](../scripts/verify_track_d4.py) |
| **Clean-Room Decoders & Specs** | `96/96` spec fields mapped (`unresolvedFieldCount: 0`), `6` modular decoders + `psx_kf_unpack.py`, isolated `unittest` suite (`--offline-synthetic` & live) | [spec_coverage.json](../schemas/spec_coverage.json), [s4_verify_report.json](../schemas/s4_verify_report.json) |
| **Clean-Room `.decomp` & Hygiene** | `111/111` `call_graph.json` string arrays cleared to `[]`; zero vendor brand or host path leaks; `CrownDepths-ForsakenIsle-SlateOne-02.decomp` validated | [call_graph.json](../schemas/call_graph.json), [export_decomp_bundle.py](../scripts/export_decomp_bundle.py) |

---

## 5. Open Horizons (`v0.3.0 -> v1.0.0 -> v2.0.0`)

- **`v0.3.0` (Human C `D4_CleanSource` & `reSlate` Cutover):** Using the `Corpus/tiers/{D1_Raw,D2_Structured,D3_Mapped,D4_CleanSource}/` layout and `27` cohesive modules seeded in `v0.2.0`, key rewrites by `(program, address)`, rewrite all `1,757` functions to `0` warnings under `-Wall -Wextra -Wno-unused-parameter` (`0` tells), re-certify `D4` (`D4a` Subsystem Parity minimum, progressing toward `D4b` Execution Parity lockstep and downstream `R3` Pure Static), and switch `.decomp` `engineId` to `"reSlate"`.
- **`v0.4.0` (Deterministic `Q12` GTE & 4-EXE Trace Parity):** Add `kf_gte_cop2.h` fixed-point math and stitched `SLUS -> OPEN -> GAME -> END` zone `0..7` traces (`--offline-synthetic` + live).
- **`v1.0.0` (`S5` Gold) -> `v2.0.0` (`D5_ByteExact`):** Certify `s5_gold_report.json` (`0` unresolved fields) and optional `1:1` matching-compiler `d5_byte_match.json` (`MISSING_TOOLCHAIN` fail-closed fallback), gated on upstream `R&D` verifier and data-dictionary alignment.
