# CrownDepths ForsakenIsle (SlateOne) 02 Decomp — Operations, Build, `.decomp` & Pre-Public Runbook

**Version:** `0.2.0` (`2026-11-18`) · **Compiler:** `zig cc` (`ZIG_EXE` or `PATH`, `mipsel-freestanding-eabi`, `mips2`) · **Python:** `3.12+` (`python` on `PATH`)

## 1. Prerequisites, Portability & Clean-Room BYO Media

- **Required Toolchain:** `python` (`3.12+`, pure stdlib — zero external pip dependencies required for scripts or tests). Optional tools: `zig` (`ZIG_EXE` env -> `shutil.which("zig")` -> `%LOCALAPPDATA%` fallback), `clangd`, and `7z`.
- **External Decomp Tools Discovery:** [patch_ps1_reexport_and_compat.py](../scripts/patch_ps1_reexport_and_compat.py) resolves external helpers deterministically: **`--tools-dir` -> `RD_DECOMP_TOOLS` env -> relative sibling `../../Personal/R&D/Dev/tools/decomp`**.
- **Local Config & Secrets Containment:** Local workspace overrides follow [decomp_local.example.json](../schemas/decomp_local.example.json); live Notion IDs live strictly inside gitignored `Dev/data/notion_hub.local.json`; webhook delivery uses `DISCORD_WEBHOOK_FOUNDATION` from environment variables only.
- **Clean-Room BYO Media Placement:** Place legally dumped `SLUS-00158` disc files under `--data-dir` or gitignored `Corpus/standalone/disc/files/` (`SLUS_001.58`, `OPEN.EXE`, `GAME.EXE`, `END.EXE`, `SYSTEM.CNF`, `COPY.TXT`, `LICENSEA.DAT`, `license_data.dat`, `CD/FN.D`, `CD/COM/*.T`, `OP/*`). Keep `Corpus/standalone/` strictly read-only (`IsReadOnly = true`).

## 2. Reproducible Unpack, Build, Parity & `.decomp` Commands

### 2.1 Isolated Unit Tests & Offline Synthetic Verification (Zero Retail Media Needed)

```powershell
python -B -m unittest discover -s Dev/scripts/tests -v
python -B Dev/scripts/psx_kf_unpack.py --offline-synthetic --data-dir "$env:TEMP\kf-unpack" --log-dir Dev/logs
python -B Dev/scripts/materialize_decomp_tiers.py --offline-synthetic --data-dir "$env:TEMP\kf-tiers" --log-dir Dev/logs
python -B Dev/scripts/build_and_verify_d4.py --offline-synthetic --data-dir "$env:TEMP\kf-d4" --log-dir Dev/logs
python -B Dev/scripts/verify_track_d4.py --offline-synthetic --data-dir "$env:TEMP\kf-d4" --log-dir Dev/logs
```

### 2.2 Clean-Room `.decomp` Bundle Export (`reStation` `0.2.x`)

```powershell
# Export and self-validate tracked root CrownDepths-ForsakenIsle-SlateOne-02.decomp
python -B Dev/scripts/export_decomp_bundle.py --verify-cleanroom --log-dir Dev/logs
```

- Emits ZIP root `module.decomp.json` (`moduleId: "crowndepths-forsakenisle-slateone-02"`, `engineId: "reStation"`, `compatibleEngineTrack: "0.2.x"`, `targetDecompTier: "D3"`, `goalDecompTier: "D4"`, `preloadRomDir: "data/rom"`, `recipeEntryPoint: "Dev/scripts/psx_kf_unpack.py"`) plus clean-room `Dev/schemas/` and `Dev/scripts/` (excluding `Corpus/`, `Archive/`, `Dev/docs/`, `Dev/data/`, `Dev/logs/`, `Dev/scripts/tests/`, and `__pycache__/`).

### 2.3 Live BYO-Media Unpack, Modular Decoders & Universal `decomp_cli` Checks

```powershell
# Empty --data-dir exits non-zero cleanly with {"status": "MISSING_CORPUS_MEDIA", ...} JSON
python -B Dev/scripts/psx_kf_unpack.py --data-dir "$env:TEMP\kf-empty" --log-dir Dev/logs

# Live full-disc SHA-256 verification, modular decoders, and compat normalization
python -B Dev/scripts/psx_kf_unpack.py --data-dir Corpus/standalone/disc/files --out-dir Corpus/work/extracts/assets --log-dir Dev/logs
python -B Dev/scripts/kf_t_archives.py --data-dir Corpus/standalone/disc/files --log-dir Dev/logs
python -B Dev/scripts/kf_world_fdat.py --data-dir Corpus/standalone/disc/files --log-dir Dev/logs
python -B Dev/scripts/kf_items_magic_talk.py --data-dir Corpus/standalone/disc/files --log-dir Dev/logs
python -B Dev/scripts/kf_meshes_mo_rtmd.py --data-dir Corpus/standalone/disc/files --log-dir Dev/logs
python -B Dev/scripts/kf_audio_vab_seq.py --data-dir Corpus/standalone/disc/files --log-dir Dev/logs
python -B Dev/scripts/kf_save_memcard.py --offline-synthetic --data-dir "$env:TEMP\kf-mc" --log-dir Dev/logs
python -B Dev/scripts/patch_ps1_reexport_and_compat.py --data-dir Corpus --log-dir Dev/logs
python -B Dev/scripts/materialize_decomp_tiers.py --log-dir Dev/logs

# Pass 1 (28 ELF32 MIPS .o across 27 modules) + Pass 2 (10/10 LP32 parity) + independent verifier
python -B Dev/scripts/build_and_verify_d4.py --log-dir Dev/logs
python -B Dev/scripts/verify_track_d4.py --log-dir Dev/logs

# Universal R&D decomp_cli gates (D3 + clangd & S4 study gate)
python -B "$env:RD_DECOMP_TOOLS\decomp_cli.py" verify --track . --tier D3
python -B "$env:RD_DECOMP_TOOLS\decomp_cli.py" verify --track . --tier S4 --no-clangd
```

## 3. Workspace & `clangd` Inspection

- Open [CrownDepths-ForsakenIsle-SlateOne-02-Decomp.code-workspace](../CrownDepths-ForsakenIsle-SlateOne-02-Decomp.code-workspace) in VS Code (`python.defaultInterpreterPath: "python"`, relative sibling `../../Personal/R&D/Dev/tools/decomp/decomp_cli.py` tasks, coded `SeriesMap` folder names, zero hardcoded local paths).
- Multi-tier workspace roots expose `Corpus/tiers/{D1_Raw, D2_Structured, D3_Mapped, D4_CleanSource}` alongside synced `Corpus/readable/` (`compile_commands.json` configures `-target mipsel-unknown-none-elf -ffreestanding -std=gnu11` with `ghidra_compat.h` forced-included across all `27` cohesive `.c` modules covering all `1,757` functions).

## 4. Dual-Track Archival & Pre-Public Hygiene Scrub Runbook

> [!CAUTION]
> Never run destructive history rewrites (`git-filter-repo`), `git push --force`, tag pushes, or public repository visibility changes without explicit human review sign-off (`active.state` keeps `"requireHumanReviewBeforePush": true`).

1. **Clean-Room `.7z` Backup (Always Exclude `Corpus/`, `Dev/data/`, `Archive/`, `.git/`):**
   ```powershell
   7z a -t7z -mx=9 "Archive\KingsField-PlayStation-v0.2.0-src.7z" ".\*" "-xr!Corpus" "-xr!Corpus\*" "-xr!Dev\data\*" "-xr!Dev\logs\*" "-xr!Archive\*" "-xr!.git\*" "-xr!__pycache__\*"
   ```
2. **Pre-Rewrite Backup Bundle & Zero-Leak Sweep:**
   ```powershell
   git bundle create "$env:TEMP\kf-pre-rewrite.bundle" --all
   git grep -nEi "([A-Z]:[/\\]+(?:Us[e]rs|Py[t]hon\d+|Pro[j]ects|Pro[g]rams|S[e]ts)|fi[l]e:///|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|Ps[y]Q)"
   ```
3. **Full-History Rewrite Safety:** Apply `git-filter-repo --refs main` across **every reachable commit from root commit through `HEAD`** (never a two-dot `A..B` range, which omits the root commit), confirm `0` history hits via `git log --all`, and re-run the §2.1 verification suite before human sign-off.
