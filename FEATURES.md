# Features & Verified Deliverables — KingsField-PlayStation

> **Container Tier:** `Tier R` Standalone Research Repository · **Baseline:** `v0.1.0` (`D4 / S4 / R3`) · **Active Horizon:** `v0.1.1` -> `v1.0.0` (`S5` Gold)
> **Legend:** `🟢 Live` (Shipped in `v0.1.0`) · `🟡 In-Dev` (Active `v0.1.1`) · `🔵 Planned` (`v0.2.0` -> `v1.0.0`)
> **Links:** [README](README.md) · [ROADMAP](ROADMAP.md) · [active.state](active.state) · [SPECIFICATIONS](Dev/docs/SPECIFICATIONS.md) · [OPERATIONS](Dev/docs/OPERATIONS.md)

---

## 1. Feature Summary Matrix

| Feature / Capability | Milestone | Status | Summary Scope | Primary Artifact / Gate |
| :--- | :--- | :--- | :--- | :--- |
| **Sealed BYO-Disc Baseline (`D0` / `S0`)** | `v0.1.0` | `🟢 Live` | `12` SHA-256 baseline entries (`SLUS-00158`, `6,297` files / `716,862,355` B read-only) | [`standalone_integrity.json`](Dev/schemas/standalone_integrity.json) |
| **4-Executable Call Graph & Schemas (`D1`–`D3`)** | `v0.1.0` | `🟢 Live` | `1,757` funcs (`1,632` game + `125` PS1-SDK), `1,549/1,549` globals, `46` structs, `268` files | [`Dev/research.manifest.json`](Dev/research.manifest.json) |
| **ELF32 MIPS Archive & LP32 Host Parity (`D4` / `S4`)** | `v0.1.0` | `🟢 Live` | `260/260` ELF32 LE MIPS `.o` (`1,841,082` B) + `10/10` `x86-windows-gnu` parity tests | [`d4_build_report.json`](Dev/schemas/d4_build_report.json) |
| **Clean-Room `/CD/COM/*.T` Unpacker (`Dev/scripts/`)** | `v0.1.0` | `🟢 Live` | Decodes `7` `/CD/COM/*.T` archives, `CD/FN.D` (`58` Shift-JIS entries), `.TIM` PNGs, `.S` STR/MDEC | [`psx_kf_unpack.py`](Dev/scripts/psx_kf_unpack.py) |
| **4-Doc Research Manual Shelf & `R3` Reference** | `v0.1.0` | `🟢 Live` | Complete Manual Shelf + read-only oracle link with [`KingsFieldRecomp`](../../Personal/KingsFieldRecomp/README.md) (`v0.1.3`) | [`Dev/docs/ARCHITECTURE.md`](Dev/docs/ARCHITECTURE.md) |
| **Standard 18 Schemas & Clean-Room Paths (`T1`)** | `v0.1.1` | `🟡 In-Dev` | Normalize `generatedAtUtc`/`isPassed`/`unresolvedFieldCount` + `MISSING_CORPUS_MEDIA` JSON | `Dev/schemas/*.json`, [`psx_kf_unpack.py`](Dev/scripts/psx_kf_unpack.py) |
| **Author `verify_track_d4.py` & Modular `d4_harness\` (`T2`–`T3`)** | `v0.1.1` | `🟡 In-Dev` | Extract verification into standalone `verify_track_d4.py`, split `<= 250` LOC TUs + globbing | `Dev/scripts/verify_track_d4.py`, `Dev/scripts/d4_harness/` |
| **`.T` Codec Decompression & Spec Spokes (`T4`–`T5`)** | `v0.2.0` | `🔵 Planned` | `.T` wrapper codecs (`VAB.T` `.vh` `16511`), `FDAT.T` (`0..7`), `ITEM`/`MAG`, `.MO`, `VAB`/`SEQ` | `Dev/scripts/*.py`, `Dev/docs/specifications/*.md` |
| **Q12 Host GTE & 4-EXE Chain Trace Parity (`T6`)** | `v0.3.0` | `🔵 Planned` | Host Q12 GTE (`COP2`) math model + `SLUS_001.58 -> OPEN -> GAME -> END` trace parity | `Dev/scripts/d4_harness/`, `Corpus/work/` |
| **Certified `S5` Gold Research Container (`T7`–`T8`)** | `v1.0.0` | `🔵 Planned` | `s5_gold_report.json` (`isPassed: true`), `unresolvedFieldCount == 0`, Gold Manual Shelf | `Dev/schemas/s5_gold_report.json` |

---

## 2. Live Capabilities (`v0.1.0`)

### 2.1 Sealed BYO-Disc Corpus & 4-Executable Analysis (`D0`–`D3`)
- **Cryptographic Corpus Seal:** [`standalone_integrity.json`](Dev/schemas/standalone_integrity.json) locks `12` SHA-256 baseline entries over read-only `Corpus/standalone/` (`6,297` files / `716,862,355` B, `IsReadOnly = true`).
- **4-Executable Clean-Room Corpus:** Maps `SLUS_001.58`, `OPEN.EXE`, `GAME.EXE`, and `END.EXE` (`1,757` functions: `1,632` named game + `125` deduplicated PS1-SDK symbols, `0` failed; `1,549/1,549` mapped globals).
- **LP32 C Types & IDE Cleanliness:** `kingsfield_types.h` + `4` modular headers (`46` structs, `21` typedefs, `3` enums, `93` type sizes) and `268` readable files (`259` `.c` + headers) passing `clangd 23.1.0` with zero errors or warnings.

### 2.2 Compiled MIPS Archive, Unpacker & Optional Reference (`D4` / `S4` / `R3`)
- **Build & Live LP32 Parity:** [`build_and_verify_d4.py`](Dev/scripts/build_and_verify_d4.py) compiles `260/260` ELF32 LE MIPS `.o` objects into `libkings_field_d4.a` (`1,841,082` B, `0` errors / `0` warnings) and passes `10/10` live `x86-windows-gnu` parity tests in [`d4_build_report.json`](Dev/schemas/d4_build_report.json).
- **`psx_kf_unpack.py`:** Decodes all `7` `/CD/COM/*.T` sector archives, `CD/FN.D` (`58` Shift-JIS filename entries), `OP/*.D` `.TIM` -> PNG assets, and `OP/*.S` STR/MDEC stream headers.
- **Bidirectional Non-Gating Reference (`R3`):** Consulted read-only by downstream [`KingsFieldRecomp`](../../Personal/KingsFieldRecomp/README.md) (`v0.1.3`); this repo operates completely independently with zero downstream gating.

---

## 3. Active In-Dev Capabilities (`v0.1.1`)

### 3.1 Standard 18 Schemas & Empty-Corpus Resilience (`T1`)
- **Schema Consistency:** Align every report schema (`d4_build_report.json`, `s4_verify_report.json`, `spec_coverage.json`) and manifest entry (`generatedAtUtc`, `isPassed`, `unresolvedFieldCount`) with Standard 18.
- **Clean Missing-Media & Synthetic Runs:** Ensure `psx_kf_unpack.py` and verification scripts write strictly into `--out-dir` / `Corpus\work\`, emit structured `"status": "MISSING_CORPUS_MEDIA"` JSON when `Corpus\` is unpopulated, and support `--offline-synthetic` smoke runs.

### 3.2 Dedicated `verify_track_d4.py` & Modular `d4_harness\` (`T2`–`T3`)
- **Extracted Verification Driver:** Split verification out of monolithic `build_and_verify_d4.py` into a first-class [`verify_track_d4.py`](Dev/scripts/verify_track_d4.py) aligned with sibling Tier R PS1 repos and `decomp_cli.py verify`.
- **Multi-TU `d4_harness\` (`<= 250` LOC/File):** Partition parity tests across compact, focused C translation units with Pass-2 globbing so `v0.2.0`/`v0.3.0` decoders and GTE vectors plug in cleanly.

---

## 4. Planned Horizon Capabilities (`v0.2.0` -> `v1.0.0`)

### 4.1 `.T` Wrapper Codec Parsers & `S5` Spec Spokes (`v0.2.0` — `T4`–`T5`)
- **Decompression & Content Parsers (`Dev/scripts/*.py` `<= 250` LOC):** Resolve `.T`-wrapped codec headers (including `VAB.T` `.vh` `programs=16511` anomalies), `CD/COM/FDAT.T` zones (`0..7`), `ITEM.T`/`MAG.T`/dialogue tables, `.MO` morph meshes, and `VAB.T`/`SEQ` audio containers.
- **Zero-Gap Spec Spokes:** Author `150–380`-line `Dev\docs\specifications\*.md` spokes linked from [`SPECIFICATIONS.md`](Dev/docs/SPECIFICATIONS.md) until `spec_coverage.json` hits `unresolvedFieldCount == 0`.

### 4.2 Q12 Host GTE & 4-Executable Chain Parity (`v0.3.0` — `T6`)
- **Q12 Fixed-Point GTE (`COP2`) Host Model:** Deterministic host emulation of PS1 GTE perspective transform (`RTPS`/`RTPT`), fog/depth cueing, and frustum culling vectors (`0x800342D8`).
- **Boot-to-Ending Trace Fixtures:** Capture golden state/math trace parity across the `SLUS_001.58 -> OPEN.EXE -> GAME.EXE -> END.EXE` handoff chain inside `Corpus\work\` / `--data-dir`.

### 4.3 Certified `S5` Gold Reference Research Container (`v1.0.0` — `T7`–`T8`)
- **`s5_gold_report.json` (`isPassed: true`):** Pass `decomp_cli.py verify --tier S5` (`0` errors/warnings, `unresolvedFieldCount == 0`) and finalize the complete 4-Doc Manual Shelf.
