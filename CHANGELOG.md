# Changelog

All notable changes to this repository are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-11-18 (Beta)

### Added
- **Clean-Room `.decomp` Exporter:** Added `Dev/scripts/export_decomp_bundle.py`, `Dev/schemas/decomp_recipe.json`, and `Dev/schemas/decomp_local.example.json` emitting root-tracked `CrownDepths-ForsakenIsle-SlateOne-02.decomp` targeting `reStation` (`0.2.x`) with `--verify-cleanroom` checks.
- **Modular Container, Mesh, Audio & Save Decoders:** Added `6` pure-stdlib Python decoders (`kf_t_archives.py`, `kf_world_fdat.py`, `kf_items_magic_talk.py`, `kf_meshes_mo_rtmd.py`, `kf_audio_vab_seq.py`, `kf_save_memcard.py`) covering all `7` `/CD/COM/*.T` packs, `FDAT[48]` `9`-section boot database, `FDAT[49..66]` view-models, `CD/FN.D`, `OP/*`, and `BASLUS-00158` saves.
- **Multi-Tier Corpus Materializer & Cohesive Module Split:** Added `Dev/scripts/materialize_decomp_tiers.py` to preserve raw and structured C trees locally alongside `27` cohesive subsystem and runtime SDK modules under `Corpus/readable/`, supporting `--offline-synthetic` and failing closed with `MISSING_CORPUS_MEDIA` when absent.
- **Standalone Verifier, Synthetic Corpus & Unit Tests:** Added `Dev/scripts/verify_track_d4.py`, `Dev/scripts/d4_synthetic_corpus.py`, `Dev/scripts/ps1_compat_helpers.py`, `Dev/scripts/tests/test_kf_parsers.py`, and `Dev/scripts/tests/test_kf_decomp_cleanroom.py` supporting zero-disc `--offline-synthetic` execution.
- **Zero-Gap Specifications, Empirical Findings & Public Policy Docs:** Added `6` format specification spokes (`96/96` mapped fields, `0` unresolved in `Dev/schemas/spec_coverage.json`), `3` empirical findings spokes under `Dev/docs/findings/`, `10`-section `Dev/docs/ARCHITECTURE.md`, `Dev/schemas/s4_verify_report.json`, `SECURITY.md`, and `CONTRIBUTING.md`.

### Changed
- **Full `23`-File + `.bin` Disc Integrity Gate:** Upgraded `Dev/schemas/standalone_integrity.json` (`schemaVersion: 2`) to verify all `23` extracted `SLUS-00158` disc files (plus optional `258,183,744`-byte `.bin`) via `1 MiB`-chunked SHA-256 hashing in `psx_kf_unpack.py`, dropping legacy project-database references and failing closed with `MISSING_CORPUS_MEDIA` JSON when absent.
- **Honest Decomp Baseline & Modular Harness Split:** Split `parity_tests.c` into `4` warning-free C files under `Dev/scripts/d4_harness/` with Pass-2 globbing while keeping `28` ELF32 MIPS objects across `27` cohesive C modules and `10/10` LP32 parity active, and re-opened clean C rewrite certification until `v0.3.0` resolves `-Wall -Wextra` warnings and decompiler tells across the `1,757` functions.
- **Clean-Room Scrub & Portable Workspace:** Renamed the IDE workspace to `Dev/CrownDepths-ForsakenIsle-SlateOne-02-Decomp.code-workspace` with coded labels and multi-tier folders, cleared all `111` embedded retail string arrays from `Dev/schemas/call_graph.json`, neutralized vendor SDK brand labels across `Dev/schemas/` and `Dev/docs/`, moved local Notion IDs into gitignored `Dev/data/notion_hub.local.json`, scrubbed workstation paths and local file-scheme URIs across root docs, `AGENTS.md`, `patch_ps1_reexport_and_compat.py`, and archived reports, and updated `.gitignore`.

### Fixed
- **`VAB.T` `.vh` Header Unpacking:** Fixed `VAB.T` `.vh` header parsing (`<IIIHHHHBBBBI` at `+4` inside `kf_audio_vab_seq.py`), resolving the `programs=16511` misalignment (`programs=2, tones=23, vags=22` on `VAB.T[0]`).

## [0.1.0-hf.1] - 2026-11-15

### Changed
- Standardized the repository on the 3-folder clean-room layout (`Archive/`, `Corpus/`, `Dev/`), ignore rules, and documentation layout.

## [0.1.0] - 2026-11-14

### Added
- Initial standalone clean-room repository for `SLUS-00158` indexing `1,757` functions (`1,632` named game + `125` runtime SDK across `SLUS_001.58`, `OPEN.EXE`, `GAME.EXE`, `END.EXE`), `1,549` mapped globals, LP32 C headers (`46` structs, `21` typedefs, `3` enums), `260` ELF32 MIPS objects (`libkings_field_d4.a`), `10/10` LP32 host parity checks, `/CD/COM/*.T` container unpacker, and technical manuals.
