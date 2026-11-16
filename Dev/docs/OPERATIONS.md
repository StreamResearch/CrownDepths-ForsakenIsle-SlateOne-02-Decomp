# KingsField-PlayStation — Operations, Build & Parity Runbook

**Version:** `0.1.0` (2026-11-14) · **Compiler:** `zig cc` (`mipsel-freestanding-eabi`, `mips2`) · **Python:** `python`

## 1. Prerequisites & Clean-Room BYO Media
- **Required Toolchain:** `python`, LLVM WinGet `clangd_23.1.0`, `zig` (resolved via `ZIG_EXE`, `PATH`, or `%LOCALAPPDATA%\Microsoft\WinGet\Links\zig.exe`), and `C:\Program Files\7-Zip\7z.exe`.
- **Clean-Room Media Placement:** Extract legally owned retail *King's Field* (`SLUS-00158`) disc files into gitignored `Corpus/standalone/disc/files/` (`SLUS_001.58`, `OPEN.EXE`, `GAME.EXE`, `END.EXE`, `CD/FN.D`, `CD/COM/*.T`, `OP/*`). Keep `Corpus/standalone/` strictly read-only (`IsReadOnly = true`).
- **Zero-PII Guarantee:** All scripts and docs avoid hardcoded user profile paths (`ZIG_EXE` / `PATH` / `$env:USERPROFILE` / `%LOCALAPPDATA%` only).

## 2. Reproducible Unpack, Build & Parity Commands
- **Standalone Container Unpacker (`psx_kf_unpack.py`):**
```powershell
& 'python' -B '../../Research/KingsField-PlayStation\Dev\scripts\psx_kf_unpack.py' '../../Research/KingsField-PlayStation\Corpus\standalone\disc\files' --out-dir '../../Research/KingsField-PlayStation\Corpus\work\extracts\assets'
```
- **Stage D4 Full MIPS Build (`259/259` `.c` -> `260` `.o`) + LP32 Host Parity (`10/10`):**
```powershell
& 'python' -B '../../Research/KingsField-PlayStation\Dev\scripts\build_and_verify_d4.py'
```
- **Direct Host Parity Runner Execution (`10/10` deterministic JSON output):**
```powershell
& '../../Research/KingsField-PlayStation\Corpus\work\d4_build\host_parity\d4_parity_runner.exe' --standalone-dir '../../Research/KingsField-PlayStation\Corpus\standalone'
```
- **Cumulative Tier R Gate Audit (`D0`–`D4` & `S0`–`S4`):**
```powershell
& 'python' -B 'R&D/Dev/tools/decomp\decomp_cli.py' verify --track '../../Research/KingsField-PlayStation' --tier D4
& 'python' -B 'R&D/Dev/tools/decomp\decomp_cli.py' verify --track '../../Research/KingsField-PlayStation' --tier S4
```
- **Tier R 3-Folder Scaffold Audit (`scaffold_project.ps1 -Research`):**
```powershell
powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\scaffold_project.ps1" -ProjectName 'KingsField-PlayStation' -Group 'Research' -Research -AuditOnly
```

## 3. Workspace, Integrated Tasks & `clangd` Inspection
- Open [`Dev/KingsField-PlayStation.code-workspace`](Dev/KingsField-PlayStation.code-workspace) in VS Code (mounts `KingsFieldRecomp/Dev`, `Corpus/readable`, `Dev/schemas`, `Dev/docs`, `Dev/scripts`).
- `Corpus/readable/compile_commands.json` and `.clangd` configure `clangd 23.1.0` (`-target mipsel-unknown-none`) with `ghidra_compat.h` forced-included for `0`-error / `0`-warning navigation across all `259` `.c` units.
- Built-in VS Code tasks run `decomp_cli.py`: **Verify Track Gates** (default test), **Index Stage 1**, **Bundle Stage 2/3**, **Assemble Stage 4** (default build), and **Refresh Workspace & compile_commands.json**.

## 4. Dual-Track Archival, Private Remote & Stage 3 Downstream
- **Private Remote Policy:** Tracks commit to `main`, tag `v0.1.0`, and push exclusively to private `StreamResearch/KingsField-PlayStation` (zero `Corpus/` or retail assets).
- **Clean-Room `.7z` Backup (never package `Corpus/`, `Archive/`, or `.git/`):**
```powershell
& 'C:\Program Files\7-Zip\7z.exe' a -t7z -mx=9 '../../Research/KingsField-PlayStation\Archive\KingsField-PlayStation-v0.1.0-d4-s4-r3.7z' '../../Research/KingsField-PlayStation\*' '-xr!Corpus' '-xr!Corpus\*' '-xr!Archive\*' '-xr!.git\*' '-xr!__pycache__\*'
```
- **Downstream Stage 3 Link (`KingsFieldRecomp`):** [`../../Personal/KingsFieldRecomp\`](../../Personal/KingsFieldRecomp/README.md) (`v0.1.3` / `R3` on `reStation v0.1.1` + `reEngine`) links bidirectionally via `downstreamProjects` (`Dev/research.manifest.json`) while keeping `Corpus/` strictly confined here.
- **Notion Manual Page:** `Operations Runbook` (`<NOTION_OPERATIONS_PAGE_ID>`).
