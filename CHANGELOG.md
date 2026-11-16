# Changelog

All notable changes to this research repository are documented in this file.

## [Unreleased]

## [0.1.0-hf.1] - 2026-11-15
### Changed
- Retired the legacy 4th ephemeral folder and standardized Tier R layout, `.gitignore`, `active.state`, `AGENTS.md`, Root Quartet, Manual Shelf, plans/reports, and schema provenance on the **3-Folder Tier R** container standard (`Archive\`, `Corpus\`, `Dev\`).

## [0.1.0] - 2026-11-14
### Added
- Graduated **King's Field** (`SLUS-00158`, North America PS1, `native_ghidra_c` / `ps1-psyq-mipsel`) from `../../Personal/R&D\decomps\ps1\kings-field` at verified **`D4 / S4 / R3`** into standalone 3-folder **Tier R** repository `../../Research/KingsField-PlayStation` (`StreamResearch/KingsField-PlayStation` private remote).
- Locked `12` SHA-256 baseline entries in `Dev/schemas/standalone_integrity.json` (`Corpus/standalone/`, `IsReadOnly = true`), indexed `1,757` functions (`1,632` named game + `125` PS1-SDK SDK across `SLUS_001.58`, `OPEN.EXE`, `GAME.EXE`, `END.EXE`, `0` failed), mapped `1,549/1,549` globals, and normalized `46` structs / `21` typedefs / `3` enums / `93` type sizes across `kingsfield_types.h` + `4` modular LP32 headers (`268` readable files including `259` `.c`, `clangd 23.1.0` `0` errors/warnings).
- Verified Stage `D4` dual-pass build & behavioral parity ([`build_and_verify_d4.py`](Dev/scripts/build_and_verify_d4.py), [`parity_tests.c`](Dev/scripts/d4_harness/parity_tests.c), [`psx_kf_unpack.py`](Dev/scripts/psx_kf_unpack.py)): `260/260` ELF32 LE MIPS `.o` archived into `libkings_field_d4.a` (`1,841,082` B, `0` errors / `0` warnings) plus `10/10` passing `x86-windows-gnu` LP32 host parity tests.
- Linked downstream `R3` proving ground [`KingsFieldRecomp`](../../Personal/KingsFieldRecomp/README.md) (`v0.1.3` on `reStation v0.1.1` + `reEngine`, Notion `<NOTION_ROOT_PAGE_ID>`), authored the 4-Doc Research Manual Shelf (`ARCHITECTURE.md`, `SPECIFICATIONS.md`, `FINDINGS.md`, `OPERATIONS.md`), Root Quartet, `active.state`, and compact `AGENTS.md` (Notion `<NOTION_PROJECT_PAGE_ID>`).
