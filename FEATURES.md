# Features

Overview of what *CrownDepths ForsakenIsle (SlateOne) 02 Decomp* (`SLUS-00158`) supports today and what is scheduled across upcoming releases. For milestone sequencing, see [ROADMAP.md](ROADMAP.md).

## Feature Summary

| Feature | Status | Since | Primary Code | What It Does |
| :--- | :--- | :--- | :--- | :--- |
| **Disc Integrity & Unpacker** | `Live` | `v0.1.0` | `Dev/scripts/psx_kf_unpack.py` | Verifies full `23`-file + `.bin` SHA-256 digests and extracts `.T` packs. |
| **4-EXE Call Graph & LP32 Headers** | `Live` | `v0.1.0` | `Dev/schemas/types/` | Indexes `1,757` functions, `1,549` globals, and `46` typed structs across `4` EXEs. |
| **MIPS Build & Modular Parity Harness** | `Live` | `v0.2.0` | `Dev/scripts/d4_harness/` | Coalesces `259` chunks into `27` cohesive modules (`28` MIPS objects) + `10` LP32 checks. |
| **Multi-Tier Corpus Materializer** | `Live` | `v0.2.0` | `Dev/scripts/materialize_decomp_tiers.py` | Preserves raw, structured, and cohesive module snapshots side-by-side locally. |
| **Standalone Verifier & Synthetic CI** | `Live` | `v0.2.0` | `Dev/scripts/verify_track_d4.py` | Validates reports, harness SLOC/warnings, and `--offline-synthetic` builds. |
| **Clean-Room `.decomp` Exporter** | `Live` | `v0.2.0` | `Dev/scripts/export_decomp_bundle.py` | Packages schemas and Python transforms for `reStation` with zero retail leaks. |
| **Modular `.T`, Mesh, Audio & Save Decoders** | `Live` | `v0.2.0` | `Dev/scripts/kf_*.py` | Decodes all `7` `.T` packs, `FDAT[48]`, `VAB.T` `.vh`, `.MO`, `SEQ`, and saves. |
| **Zero-Gap Spec & Empirical Spokes** | `Live` | `v0.2.0` | `Dev/docs/` | Maps `96/96` format fields across `6` spec spokes + `3` findings spokes. |
| **Idiomatic Human C Rewrite & `(program, addr)` Shards** | `Planned` | `v0.3.0` | `Dev/schemas/d4_rewrites/` | Rewrites all `1,757` functions in the `27` cohesive modules with zero warnings. |
| **Q12 Host GTE & 4-EXE Trace Parity** | `Planned` | `v0.4.0` | `Dev/scripts/d4_harness/` | Validates fixed-point `COP2` math and multi-EXE zone traces offline. |
| **Gold Reference Certification** | `Planned` | `v1.0.0` | `Dev/schemas/s5_gold_report.json` | Certifies complete format coverage, behavioral parity, and final manuals. |
| **1:1 Byte-Exact Matching** | `Planned` | `v2.0.0` | `Dev/schemas/d5_byte_match.json` | Verifies optional matching-compiler byte parity across all `4` executables. |

## Capability Details

### Disc Integrity & Unpacker
- **What it does:** Validates user-supplied `SLUS-00158` media across all `23` disc files (including chunked hashing for `> 64 MiB` `.S` streams and optional `258,183,744`-byte `.bin` images) before extraction, failing closed with `MISSING_CORPUS_MEDIA` JSON when absent and supporting `--offline-synthetic`.
- **Entry Points:** [psx_kf_unpack.py](Dev/scripts/psx_kf_unpack.py), [standalone_integrity.json](Dev/schemas/standalone_integrity.json)

### 4-EXE Call Graph & LP32 Headers
- **What it does:** Maps `SLUS_001.58`, `OPEN.EXE`, `GAME.EXE`, and `END.EXE` (`1,757` functions, `1,549` globals, `46` structs, `21` typedefs, `3` enums) into modular LP32 C headers ([kingsfield_types.h](Dev/schemas/kingsfield_types.h)) with embedded retail strings stripped from [call_graph.json](Dev/schemas/call_graph.json) and neutral MIPS32 ABI comments.
- **Entry Points:** [kingsfield_types.h](Dev/schemas/kingsfield_types.h), [call_graph.json](Dev/schemas/call_graph.json), [globals_map.json](Dev/schemas/globals_map.json)

### Modular Container, Mesh, Audio & Save Decoders
- **What it does:** Pure-stdlib Python decoders covering all `7` `/CD/COM/*.T` packs (`FDAT.T` zones `0..7`+`10`, `FDAT[48]` `9`-section master boot DB, `FDAT[49..66]` view-models, `ITEM.T`, `MO.T`, `RTIM.T`, `RTMD.T`, `TALK.T`, `VAB.T` with fixed `<IIIHHHHBBBBI` `.vh` unpacking), `CD/FN.D`, `OP/*`, and `BASLUS-00158` saves.
- **Entry Points:** [kf_t_archives.py](Dev/scripts/kf_t_archives.py), [kf_world_fdat.py](Dev/scripts/kf_world_fdat.py), [kf_items_magic_talk.py](Dev/scripts/kf_items_magic_talk.py), [kf_meshes_mo_rtmd.py](Dev/scripts/kf_meshes_mo_rtmd.py), [kf_audio_vab_seq.py](Dev/scripts/kf_audio_vab_seq.py), [kf_save_memcard.py](Dev/scripts/kf_save_memcard.py)
- **Tests:** [test_kf_parsers.py](Dev/scripts/tests/test_kf_parsers.py)

### MIPS Build, Verifier, `.decomp` Exporter & Technical Manuals
- **What it does:** Preserves multi-tier local C trees (`materialize_decomp_tiers.py`), coalesces all `259` fragments into `27` cohesive domain and runtime SDK modules (`28` ELF32 MIPS objects in `libkings_field_d4.a`), runs `10` deterministic `x86-windows-gnu` LP32 host parity checks across modular `d4_harness/` files (`0` `-Wall -Wextra -Wno-unused-parameter` warnings), exports validated `CrownDepths-ForsakenIsle-SlateOne-02.decomp`, and documents `96/96` specification fields.
- **Entry Points:** [materialize_decomp_tiers.py](Dev/scripts/materialize_decomp_tiers.py), [build_and_verify_d4.py](Dev/scripts/build_and_verify_d4.py), [verify_track_d4.py](Dev/scripts/verify_track_d4.py), [export_decomp_bundle.py](Dev/scripts/export_decomp_bundle.py), [SPECIFICATIONS.md](Dev/docs/SPECIFICATIONS.md), [FINDINGS.md](Dev/docs/FINDINGS.md)
- **Tests:** [test_kf_decomp_cleanroom.py](Dev/scripts/tests/test_kf_decomp_cleanroom.py)
