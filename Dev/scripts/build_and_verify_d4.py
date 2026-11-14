#!/usr/bin/env python3
"""Compile all readable PS1 King's Field C translation units to ELF32 MIPS and run LP32 host parity tests."""
from __future__ import annotations

import json
import os
import re
import shutil
import struct
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DEV_OR_ROOT = SCRIPT_DIR.parent
PROJ_ROOT = DEV_OR_ROOT.parent if DEV_OR_ROOT.name == "Dev" else DEV_OR_ROOT
IS_TIER_R = (PROJ_ROOT / "Dev").is_dir() and (PROJ_ROOT / "Corpus").is_dir()
DEV_ROOT = PROJ_ROOT / "Dev" if IS_TIER_R else PROJ_ROOT
CORPUS_ROOT = PROJ_ROOT / "Corpus" if IS_TIER_R else PROJ_ROOT

SCHEMAS_DIR = DEV_ROOT / "schemas"
SCRIPTS_DIR = DEV_ROOT / "scripts"
READABLE_DIR = CORPUS_ROOT / "readable"
WORK_DIR = CORPUS_ROOT / "work"
STANDALONE_DIR = CORPUS_ROOT / "standalone"
MANIFEST_PATH = (DEV_ROOT / "research.manifest.json") if IS_TIER_R else (PROJ_ROOT / "decomp.manifest.json")

MIPS_TARGET = "mipsel-freestanding-eabi"
MIPS_CPU = "mips2"
PARITY_TARGET = "x86-windows-gnu"
PARITY_TUS = (
    "overlays/GAME.EXE/game_01.c",
    "overlays/GAME.EXE/game_02.c",
    "overlays/GAME.EXE/game_03.c",
    "overlays/GAME.EXE/game_04.c",
    "overlays/GAME.EXE/game_10.c",
    "overlays/END.EXE/end_01.c",
)
LIBC_SYMS = frozenset({
    "printf", "sprintf", "rand", "srand", "memcpy", "memset", "memmove", "memcmp",
    "strcpy", "strncpy", "strcmp", "strncmp", "strlen", "strcat", "malloc", "free",
    "calloc", "realloc", "abs", "setjmp", "longjmp", "qsort", "bsearch",
})


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _find_zig() -> Path:
    env_zig = os.environ.get("ZIG_EXE", "").strip()
    if env_zig and Path(env_zig).is_file():
        return Path(env_zig)
    found = shutil.which("zig")
    if found:
        return Path(found)
    winget_zig = Path.home() / "AppData/Local/Microsoft/WinGet/Links/zig.exe"
    if winget_zig.is_file():
        return winget_zig
    raise FileNotFoundError("zig executable not found in ZIG_EXE, PATH, or WinGet Links.")


def _zig_env(build_dir: Path) -> dict[str, str]:
    cache = build_dir / "zig_cache"
    cache.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["ZIG_GLOBAL_CACHE_DIR"] = str(cache)
    env["ZIG_LOCAL_CACHE_DIR"] = str(cache)
    return env


def _check_elf_mips(obj_path: Path) -> bool:
    raw = obj_path.read_bytes()
    if len(raw) < 20 or raw[:4] != b"\x7fELF":
        return False
    ei_class, ei_data = raw[4], raw[5]
    e_type, e_machine = struct.unpack_from("<HH", raw, 16)
    return ei_class == 1 and ei_data == 1 and e_type == 1 and e_machine == 8


def _generate_globals_and_stubs(gen_dir: Path) -> tuple[Path, Path]:
    gen_dir.mkdir(parents=True, exist_ok=True)
    inc = READABLE_DIR / "include"
    g_txt = re.sub(r"/\*.*?\*/", "", (inc / "kingsfield_globals.h").read_text(encoding="utf-8"), flags=re.S)
    c_txt = (inc / "ghidra_compat.h").read_text(encoding="utf-8")
    m = re.search(r"KF_PS1_COMPAT_EXTS\s*===\s*\*/(.*?)/\*\s*===\s*END KF_PS1_COMPAT_EXTS", c_txt, flags=re.S)
    ext_txt = m.group(1) if m else ""

    seen_vars: set[str] = set()
    var_lines = ['#include "kingsfield_types.h"', '#include "kingsfield_globals.h"', ""]
    stub_lines = [
        '#include "kingsfield_types.h"', '#include "kingsfield_globals.h"',
        "void halt_baddata(void) {}", "int syscall(long code_num, ...) { (void)code_num; return 0; }",
        "void trap(int trap_code, ...) { (void)trap_code; }",
        "void IME(uint8_t v) { (void)v; }", "uint8_t daaOperand(uint8_t a, ...) { return a; }",
        "void halt(void) {}", "void stop(void) {}",
    ]
    for line in (g_txt + "\n" + ext_txt).splitlines():
        s = line.strip()
        if not s.startswith("extern ") or not s.endswith(";"):
            continue
        body = re.sub(r"^extern\s+", "", s[:-1].strip()).strip()
        if body.endswith("()"):
            fn_m = re.match(r"^(.+?\b)([A-Za-z_][A-Za-z0-9_]*)\(\)$", body)
            if fn_m and fn_m.group(2) not in seen_vars:
                seen_vars.add(fn_m.group(2))
                stub_lines.append(f"{fn_m.group(1).strip()} {fn_m.group(2)}() {{ return 0; }}")
            continue
        arr_empty = re.match(r"^(.+?)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\[\s*\]$", body)
        arr_sized = re.match(r"^(.+?)\s+([A-Za-z_][A-Za-z0-9_]*)\s*(\[[^\]]+\])$", body)
        sym_m = re.search(r"([A-Za-z_][A-Za-z0-9_]*)\s*(?:\[.*\])?$", body)
        if not sym_m or sym_m.group(1) in seen_vars:
            continue
        seen_vars.add(sym_m.group(1))
        if arr_empty:
            var_lines.append(f"{arr_empty.group(1)} {arr_empty.group(2)}[64] = {{0}};")
        elif arr_sized:
            var_lines.append(f"{arr_sized.group(1)} {arr_sized.group(2)}{arr_sized.group(3)} = {{0}};")
        else:
            var_lines.append(f"{body} = {{0}};")

    defined_in_parity: set[str] = set()
    called_in_parity: set[str] = set()
    for rel in PARITY_TUS:
        txt = (READABLE_DIR / rel).read_text(encoding="utf-8", errors="replace")
        defined_in_parity.update(re.findall(r"^// Function:\s+(\S+)\s+@", txt, re.M))
        called_in_parity.update(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", txt))

    fn_txt = (inc / "kingsfield_functions.h").read_text(encoding="utf-8")
    for raw_ln in fn_txt.splitlines():
        ln = re.sub(r"/\*.*?\*/", "", raw_ln).strip()
        pm = re.match(r"^(.+?)\s*\b([A-Za-z_][A-Za-z0-9_]*)\s*\((.*)\)\s*;$", ln)
        if not pm:
            continue
        ret_t, fname, params = pm.group(1).strip(), pm.group(2), pm.group(3).strip()
        if fname not in called_in_parity or fname in defined_in_parity or fname in LIBC_SYMS or fname in seen_vars:
            continue
        seen_vars.add(fname)
        if ret_t == "void":
            stub_lines.append(f"void {fname}({params}) {{}}")
        else:
            stub_lines.append(f"{ret_t} {fname}({params}) {{ {ret_t} _rv = {{0}}; return _rv; }}")

    globals_c = gen_dir / "globals_defs.c"
    stubs_c = gen_dir / "host_stubs.c"
    globals_c.write_text("\n".join(var_lines) + "\n", encoding="utf-8", newline="\n")
    stubs_c.write_text("\n".join(stub_lines) + "\n", encoding="utf-8", newline="\n")
    return globals_c, stubs_c


def _compile_one(zig_exe: Path, src: Path, obj: Path, inc: Path, compat_h: Path, env: dict[str, str]) -> tuple[str, int, str]:
    obj.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(zig_exe), "cc", "-target", MIPS_TARGET, f"-mcpu={MIPS_CPU}", "-msoft-float",
        "-ffreestanding", "-fno-builtin", "-std=gnu11", "-O1", "-g0", "-Wno-everything",
        f"-I{inc}", "-include", str(compat_h), "-c", str(src), "-o", str(obj),
    ]
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return str(src.relative_to(READABLE_DIR)), proc.returncode, (proc.stderr or "").strip()


def run_build_and_verify() -> int:
    zig_exe = _find_zig()
    build_dir = WORK_DIR / "d4_build"
    obj_dir = build_dir / "obj"
    parity_dir = build_dir / "host_parity"
    shutil.rmtree(obj_dir, ignore_errors=True)
    shutil.rmtree(parity_dir, ignore_errors=True)
    obj_dir.mkdir(parents=True, exist_ok=True)
    parity_dir.mkdir(parents=True, exist_ok=True)

    env = _zig_env(build_dir)
    inc_dir = READABLE_DIR / "include"
    compat_h = inc_dir / "ghidra_compat.h"
    globals_c, stubs_c = _generate_globals_and_stubs(build_dir / "gen")

    c_files = sorted(READABLE_DIR.rglob("*.c"))
    if not c_files:
        raise RuntimeError(f"No readable .c files found under {READABLE_DIR}")

    comp_errors = 0
    comp_warnings = 0
    objs: list[Path] = []
    with ThreadPoolExecutor(max_workers=min(8, os.cpu_count() or 4)) as pool:
        futs = [
            pool.submit(_compile_one, zig_exe, src, (obj_dir / src.relative_to(READABLE_DIR)).with_suffix(".o"), inc_dir, compat_h, env)
            for src in c_files
        ]
        for fut in futs:
            rel, rc, err_txt = fut.result()
            if rc != 0:
                comp_errors += 1
                print(f"[MIPS FAIL] {rel}: {err_txt}", file=sys.stderr)
            else:
                if err_txt and "warning:" in err_txt.lower():
                    comp_warnings += len(re.findall(r"\bwarning:", err_txt, re.I))
                objs.append((obj_dir / rel).with_suffix(".o"))

    globals_obj = obj_dir / "__globals_defs.o"
    g_proc = subprocess.run(
        [str(zig_exe), "cc", "-target", MIPS_TARGET, f"-mcpu={MIPS_CPU}", "-msoft-float",
         "-ffreestanding", "-fno-builtin", "-std=gnu11", "-O1", "-g0", "-Wno-everything",
         f"-I{inc_dir}", "-include", str(compat_h), "-c", str(globals_c), "-o", str(globals_obj)],
        env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if g_proc.returncode != 0:
        comp_errors += 1
        print(f"[MIPS FAIL] globals_defs.c: {g_proc.stderr}", file=sys.stderr)
    else:
        objs.append(globals_obj)

    elf_ok = sum(1 for o in objs if _check_elf_mips(o))
    if elf_ok != len(objs):
        comp_errors += len(objs) - elf_ok

    archive_path = build_dir / "libkings_field_d4.a"
    archive_path.unlink(missing_ok=True)
    ar_proc = subprocess.run(
        [str(zig_exe), "ar", "rcs", str(archive_path)] + [str(o) for o in objs],
        env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if ar_proc.returncode != 0:
        comp_errors += 1
        print(f"[AR FAIL] {ar_proc.stderr}", file=sys.stderr)

    # Pass 2: x86-windows-gnu ILP32 (sizeof(void*) == 4) host parity runner
    runner_exe = parity_dir / "d4_parity_runner.exe"
    parity_c = SCRIPTS_DIR / "d4_harness" / "parity_tests.c"
    host_srcs = [str(READABLE_DIR / rel) for rel in PARITY_TUS] + [str(globals_c), str(stubs_c), str(parity_c)]
    host_cmd = [
        str(zig_exe), "cc", "-target", PARITY_TARGET, "-std=gnu11", "-O1", "-g0", "-Wno-everything",
        "-fno-builtin", f"-I{inc_dir}", "-include", str(compat_h), *host_srcs, "-o", str(runner_exe),
    ]
    h_proc = subprocess.run(host_cmd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    parity_data: dict = {"tests": [], "passed": 0, "failed": 1, "total": 0}
    if h_proc.returncode != 0:
        comp_errors += 1
        print(f"[HOST BUILD FAIL] {h_proc.stderr}", file=sys.stderr)
    else:
        r_proc = subprocess.run(
            [str(runner_exe), "--standalone-dir", str(STANDALONE_DIR)],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
        )
        if r_proc.returncode != 0 or not r_proc.stdout.strip():
            print(f"[PARITY RUN FAIL] rc={r_proc.returncode}\n{r_proc.stdout}\n{r_proc.stderr}", file=sys.stderr)
        if r_proc.stdout.strip():
            parity_data = json.loads(r_proc.stdout)

    parity_passed = int(parity_data.get("passed", 0))
    parity_total = int(parity_data.get("total", 0))
    parity_ok = parity_total >= 8 and parity_passed == parity_total and int(parity_data.get("failed", 1)) == 0
    overall_ok = comp_errors == 0 and comp_warnings == 0 and len(objs) >= len(c_files) and parity_ok
    now = _utc_now()

    report = {
        "schemaVersion": 1,
        "gameId": "kings-field",
        "verifiedAtUtc": now,
        "zigTarget": MIPS_TARGET,
        "zigCpu": MIPS_CPU,
        "readableFiles": len(c_files),
        "compiledFiles": len(c_files) if comp_errors == 0 else max(0, len(c_files) - comp_errors),
        "totalObjects": len(objs),
        "elf32MipsVerifiedObjects": elf_ok,
        "archiveFile": "work/d4_build/libkings_field_d4.a",
        "archiveBytes": archive_path.stat().st_size if archive_path.is_file() else 0,
        "compilerErrors": comp_errors,
        "compilerWarnings": comp_warnings,
        "errors": comp_errors,
        "warnings": comp_warnings,
        "parityTarget": PARITY_TARGET,
        "parityTestsPassed": parity_passed,
        "parityTestsTotal": parity_total,
        "parityPassed": parity_ok,
        "passed": overall_ok,
        "parityResults": parity_data,
    }
    (SCHEMAS_DIR / "d4_build_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if overall_ok:
        manifest["currentDecompTier"] = "D4"
        manifest["goalDecompTier"] = "D4"
        manifest["currentStudyTier"] = "S4"
        manifest["goalStudyTier"] = "S4"
        gates = manifest.setdefault("gates", {})
        gates["D4"] = {"passed": True, "verifiedAtUtc": now}
        gates["S4"] = {"passed": True, "verifiedAtUtc": now}
        manifest["updatedAtUtc"] = now
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({
        "passed": overall_ok, "compiledFiles": report["compiledFiles"],
        "elf32MipsVerifiedObjects": elf_ok, "archiveBytes": report["archiveBytes"],
        "compilerErrors": comp_errors, "compilerWarnings": comp_warnings,
        "parityTestsPassed": parity_passed, "parityTestsTotal": parity_total,
    }, indent=2))
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(run_build_and_verify())
