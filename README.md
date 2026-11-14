# KingsField-PlayStation

> **Standalone Clean-Room Research Repository (`Tier R`)** for **King's Field** (North America `SLUS-00158`, `ps1` / `native_ghidra_c`, ABI `ps1-psyq-mipsel`), graduated from `../../Personal/R&D/decomps/ps1/kings-field` on `2026-11-14`.

## Overview
- **Research ID:** `kings-field-play-station` (`v0.1.0`, `axis=hybrid`, private remote `StreamResearch/KingsField-PlayStation`)
- **Verified Tiers:** Decomp **`D4 / D4`** · Study **`S4 / S4`** · Recomp **`R3 / R3`** (downstream [`KingsFieldRecomp`](../../Personal/KingsFieldRecomp/README.md) `v0.1.3` on [`reStation v0.1.1`](../../Personal/reStation/README.md) + [`reEngine v0.1.1`](../../Personal/reEngine/README.md))
- **Target Binaries (`4` PS-X EXEs):** Resident `SLUS_001.58` (`0x80010000`, `4` game + `9` SDK) chaining `OPEN.EXE` (`0x80011000`, `387` game + `31` SDK), `GAME.EXE` (`0x80011000`, `898` game + `56` SDK), and `END.EXE` (`0x80011000`, `343` game + `29` SDK).
- **Coverage & D4 Build:** `1,757` total functions (`1,632` named game + `125` PS1-SDK SDK, `0` failed), `1,549/1,549` mapped globals, `46` structs / `21` typedefs / `3` enums / `93` type sizes (`kingsfield_types.h` + `4` LP32 headers), `268` readable files (`259` `.c` + headers, `clangd 23.1.0` `0` err/warn), `260/260` ELF32 LE MIPS `.o` -> `libkings_field_d4.a` (`1,841,082` B, `0` errors / `0` warnings), and `10/10` live `x86-windows-gnu` LP32 host parity tests.

## Repository Layout (`Tier R` 4-Folder Standard)
- [`Corpus\`](Corpus/) *(gitignored BYO-ROM/extracted artifacts)*: `standalone\` (`12` SHA-256 baseline files, `IsReadOnly = true`), `readable\` (`259` `.c` + `.h` + `compile_commands.json`), `work\` (`libkings_field_d4.a`, host runner, stage artifacts)
- [`Dev\`](Dev/): [`research.manifest.json`](Dev/research.manifest.json), [`KingsField-PlayStation.code-workspace`](Dev/KingsField-PlayStation.code-workspace), `schemas\`, `scripts\`, `docs\`
- [`Sandbox\`](Sandbox/) *(gitignored)*: `data\`, `logs\`, `extracts\`
- [`Archive\`](Archive/): `-xr!Corpus\*` `-mx=9` `.7z` snapshots

## Research Manual Shelf (`Dev\docs\`)
- [ARCHITECTURE.md](Dev/docs/ARCHITECTURE.md) — Target binaries (`SLUS_001.58`, `OPEN`, `GAME`, `END`), trampoline layout, and subsystem domain graph
- [SPECIFICATIONS.md](Dev/docs/SPECIFICATIONS.md) — Clean-room LP32 structs (`46`), typedefs (`21`), enums (`3`), `.T`/`FN.D`/`OP` contracts, and D4 report schema
- [FINDINGS.md](Dev/docs/FINDINGS.md) — Empirical `SLUS-00158` discoveries, Ghidra/LP32 normalization notes, `10/10` parity checks, and `D5`/`S5` horizons
- [OPERATIONS.md](Dev/docs/OPERATIONS.md) — Reproducible `psx_kf_unpack.py`, `zig cc` D4 build, `clangd 23.1.0`, `decomp_cli.py`, and Stage 3 workflows

## Clean-Room & Zero Shipping Binaries Rule
Zero retail ROMs, ISOs, `.gpr` databases, `Corpus\` files, or shipping binaries exist in Git or `Archive\`. Downstream runnable ports reside in Stage 3 `Tier A` [`KingsFieldRecomp`](../../Personal/KingsFieldRecomp/README.md) (`downstreamProjects`).
