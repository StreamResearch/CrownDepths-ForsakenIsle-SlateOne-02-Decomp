# Roadmap — KingsField-PlayStation

## Completed
- **`v0.1.0` (2026-11-14) — `D4 / S4 / R3` Graduation (`Tier R`):** Graduated from `../../Personal/R&D\decomps\ps1\kings-field` into standalone 4-folder **Tier R** repository (`StreamResearch/KingsField-PlayStation` private remote) with `1,757` functions (`1,632` named game + `125` PS1-SDK SDK, `0` failed), `1,549/1,549` globals, `46` structs / `21` typedefs / `3` enums / `93` type sizes, `268` readable files (`clangd 23.1.0` `0` err/warn), `260/260` ELF32 LE MIPS `.o` -> `libkings_field_d4.a` (`1,841,082` B, `0` errors / `0` warnings), `10/10` live `x86-windows-gnu` LP32 host parity tests, and bidirectional `R3` link to [`KingsFieldRecomp`](../../Personal/KingsFieldRecomp/README.md) (`v0.1.3` on `reStation v0.1.1` + `reEngine`).

## Next Horizons
- **Stage 2+ (`D5` / `S5`):** Optional `1:1` byte-matching ELF/binary reconstruction of `SLUS_001.58`, `OPEN.EXE`, `GAME.EXE`, and `END.EXE`, plus multi-corpus (`SLPS-00017` / `SLES-00201`) round-trip specification parity.
- **Stage 3+ (`R4` / `R5`):** Track downstream evolution of [`KingsFieldRecomp`](../../Personal/KingsFieldRecomp/README.md) toward `R4` (native zero-emulation `win-x64` `.NET 10.0 NativeAOT` port) and `R5` (10-platform stack) while keeping `Corpus/` strictly confined here.
