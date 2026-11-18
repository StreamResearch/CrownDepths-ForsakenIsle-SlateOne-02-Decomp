# @module: KingsField.Dev.scripts.build_and_verify_d4
# @purpose: Compile MIPS ELF32 objects (Pass 1) and run modular LP32 host parity tests (Pass 2)
# @depends-on: argparse, concurrent.futures, datetime, json, logging, os, re, shutil, subprocess, sys, tempfile, time, pathlib, d4_synthetic_corpus
# @exports: resolve_zig_exe, zig_env, check_elf_mips, build_and_verify, main

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
DEV_DIR = SCRIPT_DIR.parent
PROJ_ROOT = DEV_DIR.parent if DEV_DIR.name == "Dev" else DEV_DIR
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from d4_synthetic_corpus import (  # noqa: E402
    PARITY_TUS,
    count_craftsmanship_tells,
    generate_globals_and_stubs,
    seed_synthetic_corpus,
    setup_logger,
)

MIPS_TARGET = "mipsel-freestanding-eabi"
MIPS_CPU = "mips2"
PARITY_TARGET = "x86-windows-gnu"
STRICT_FLAGS = ["-Wall", "-Wextra", "-Wno-unused-parameter"]


def resolve_zig_exe(explicit_zig: Path | None = None) -> Path:
    """Resolve Zig compiler via CLI override, ZIG_EXE env, PATH, or LOCALAPPDATA."""
    cands: list[Path] = [explicit_zig] if explicit_zig is not None else []
    if env_val := os.environ.get("ZIG_EXE", "").strip():
        cands.append(Path(env_val))
    if which_hit := shutil.which("zig"):
        cands.append(Path(which_hit))
    if local_app := os.environ.get("LOCALAPPDATA", "").strip():
        b = Path(local_app)
        cands.extend([b / "Microsoft/WinGet/Links/zig.exe", b / "Programs/zig/zig.exe", *sorted((b / "Microsoft/WinGet/Packages").glob("zig*/**/zig.exe"))])
    if hit := next((c for c in cands if c.is_file()), None):
        return hit
    raise FileNotFoundError("Could not locate 'zig' executable via --zig-exe, ZIG_EXE, PATH, or LOCALAPPDATA.")


def zig_env(work_dir: Path) -> dict[str, str]:
    """Return process environment pinning Zig caches inside work_dir."""
    cache_dir = (work_dir / "zig-cache").resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    return {**os.environ, "ZIG_LOCAL_CACHE_DIR": str(cache_dir), "ZIG_GLOBAL_CACHE_DIR": str(cache_dir)}


def check_elf_mips(obj_path: Path) -> bool:
    """Return True when obj_path is a valid ELF32 little-endian MIPS relocatable object."""
    raw = obj_path.read_bytes()[:20]
    return len(raw) >= 20 and raw[:4] == b"\x7fELF" and raw[4] == 1 and raw[5] == 1 and int.from_bytes(raw[16:18], "little") == 1 and int.from_bytes(raw[18:20], "little") == 8


def _emit_heartbeat(cur: int, total: int, label: str, start_ts: float, last_ts: float, force: bool = False) -> float:
    now = time.monotonic()
    if not force and (now - last_ts) < 15.0:
        return last_ts
    msg = f"[{(cur / total) * 100.0 if total else 0.0:5.1f}%] ({cur}/{total}) {label} [Elapsed: {int(now - start_ts)}s]"
    sys.stderr.write(f"\r\x1b[K{msg}" if sys.stderr.isatty() else f"{msg}\n")
    sys.stderr.flush()
    return now


def _compile_list(cmd_base: list[str], pairs: list[tuple[Path, Path]], root_a: Path, root_b: Path, env: dict[str, str], label: str) -> tuple[list[str], int]:
    def _one(pair: tuple[Path, Path]) -> tuple[str, int, str]:
        src, dst = pair
        dst.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run([*cmd_base, "-c", str(src), "-o", str(dst)], env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        base = root_a if src.is_relative_to(root_a) else root_b
        return str(src.relative_to(base)), r.returncode, r.stderr or ""

    fails, warn_cnt, start_ts, last_ts = [], 0, time.monotonic(), time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(12, os.cpu_count() or 4)) as ex:
        for idx, (rel, rc, err) in enumerate(ex.map(_one, pairs), start=1):
            last_ts = _emit_heartbeat(idx, len(pairs), f"{label} {rel}", start_ts, last_ts)
            warn_cnt += len(re.findall(r"\bwarning:", err))
            if rc != 0:
                fails.append(f"{rel}: {err[:200]}")
    _emit_heartbeat(len(pairs), len(pairs), f"{label} finished", start_ts, last_ts, force=True)
    return fails, warn_cnt


def build_and_verify(
    zig_exe: Path,
    readable_dir: Path,
    work_dir: Path,
    standalone_dir: Path,
    game_id: str,
    logger: logging.Logger,
    report_out: Path,
    archive_base: Path,
    *,
    strict_corpus: bool = False,
) -> dict[str, Any]:
    """Compile MIPS ELF32 objects (Pass 1) and run globbed d4_harness LP32 tests (Pass 2)."""
    build_root = work_dir / "d4_build"
    obj_root, host_root = build_root / "obj", build_root / "host_parity"
    shutil.rmtree(build_root, ignore_errors=True)
    obj_root.mkdir(parents=True, exist_ok=True)
    host_root.mkdir(parents=True, exist_ok=True)

    c_files = sorted(readable_dir.rglob("*.c"))
    if not c_files:
        raise RuntimeError(f"No readable .c files found under {readable_dir}")
    parity_sources = [readable_dir / rel for rel in PARITY_TUS]
    globals_defs_c, host_stubs_c = generate_globals_and_stubs(readable_dir, host_root, PARITY_TUS)

    env, inc, compat = zig_env(work_dir), str(readable_dir / "include"), str(readable_dir / "include/ghidra_compat.h")
    pass1_warn_flags = STRICT_FLAGS if strict_corpus else ["-Wno-everything"]
    mips_flags = [str(zig_exe), "cc", "-target", MIPS_TARGET, f"-mcpu={MIPS_CPU}", "-msoft-float", "-ffreestanding", "-fno-builtin", "-fno-strict-aliasing", "-std=gnu11", "-O1", "-g0", *pass1_warn_flags, f"-I{inc}", "-include", compat]
    all_tus = [(p, obj_root / p.relative_to(readable_dir).with_suffix(".o")) for p in c_files] + [(globals_defs_c, obj_root / "globals_defs.o")]
    fails, warn_cnt = _compile_list(mips_flags, all_tus, readable_dir, host_root, env, "MIPS compile")
    elf_bad = sum(1 for _, obj in all_tus if not obj.is_file() or not check_elf_mips(obj))

    archive_path, rel_objs, ar_rc = build_root / "libkings_field_d4.a", [obj.relative_to(obj_root).as_posix() for _, obj in all_tus], 0
    for i in range(0, len(rel_objs), 80):
        ar_res = subprocess.run([str(zig_exe), "ar", "rcS" if i == 0 else "rS", str(archive_path.resolve()), *rel_objs[i : i + 80]], cwd=obj_root, env=env, capture_output=True, text=True)
        if ar_res.returncode != 0:
            ar_rc = ar_res.returncode
            break
    if ar_rc == 0:
        ar_rc = subprocess.run([str(zig_exe), "ar", "s", str(archive_path.resolve())], env=env, capture_output=True, text=True).returncode
    if fails or warn_cnt or elf_bad or ar_rc != 0:
        raise RuntimeError(f"Pass1 failed: fails={len(fails)} warn_cnt={warn_cnt} elf_bad={elf_bad} ar_rc={ar_rc}\n{fails[:5]}")

    harness_dir = SCRIPT_DIR / "d4_harness"
    d4_sources = sorted(harness_dir.glob("*.c"))
    if not d4_sources:
        raise RuntimeError("No C translation units found in Dev/scripts/d4_harness/")
    corpus_hflags = [str(zig_exe), "cc", "-target", PARITY_TARGET, "-ffreestanding", "-fno-builtin", "-std=gnu11", "-O1", "-fno-strict-aliasing", *pass1_warn_flags, f"-I{inc}", f"-I{harness_dir}", "-include", compat]
    harness_hflags = [str(zig_exe), "cc", "-target", PARITY_TARGET, "-std=gnu11", "-O1", "-fno-strict-aliasing", *STRICT_FLAGS, f"-I{inc}", f"-I{harness_dir}", "-include", compat]

    corpus_pairs = [(src, host_root / f"p2_{idx}_{src.stem}.o") for idx, src in enumerate([*parity_sources, globals_defs_c, host_stubs_c])]
    harness_pairs = [(src, host_root / f"h_{src.stem}.o") for src in d4_sources]
    cf1, cw1 = _compile_list(corpus_hflags, corpus_pairs, readable_dir, host_root, env, "Host corpus")
    cf2, cw2 = _compile_list(harness_hflags, harness_pairs, harness_dir, host_root, env, "Host harness")
    warn_cnt += cw1 + cw2
    if cf1 or cf2 or cw1 or cw2:
        raise RuntimeError(f"Pass2 compile failed: corpus={cf1} harness={cf2} warns={cw1 + cw2}")

    runner_exe = host_root / "d4_parity_runner.exe"
    link_cmd = [str(zig_exe), "cc", "-target", PARITY_TARGET, "-std=gnu11", *STRICT_FLAGS, *[str(o) for _, o in [*corpus_pairs, *harness_pairs]], "-o", str(runner_exe)]
    link_res = subprocess.run(link_cmd, env=env, capture_output=True, text=True)
    link_warns = len(re.findall(r"\bwarning:", link_res.stderr or ""))
    warn_cnt += link_warns
    if link_res.returncode != 0 or link_warns != 0:
        raise RuntimeError(f"Pass2 link failed (warns={link_warns}):\n{(link_res.stderr or '')[:1200]}")

    run_res = subprocess.run([str(runner_exe), "--standalone-dir", str(standalone_dir)], capture_output=True, text=True, timeout=30)
    if run_res.returncode != 0 or not run_res.stdout.strip():
        raise RuntimeError(f"Pass2 parity runner failed:\n{run_res.stdout}\n{run_res.stderr}")
    pj = json.loads(run_res.stdout.strip())
    passed_cnt = int(pj.get("assertionsPassedCount", pj.get("passed", 0)))
    total_cnt = int(pj.get("assertionsTotalCount", pj.get("total", 0)))
    _, tell_cnt = count_craftsmanship_tells(c_files)

    now_utc = dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    tells_ok = (tell_cnt == 0) if strict_corpus else True
    is_passed = len(fails) == 0 and warn_cnt == 0 and tells_ok and total_cnt >= 10 and passed_cnt == total_cnt
    report = {
        "schemaVersion": 2, "gameId": game_id, "generatedAtUtc": now_utc, "verifiedAtUtc": now_utc,
        "zigTarget": MIPS_TARGET, "zigCpu": MIPS_CPU, "readableFiles": len(c_files),
        "compiledFileCount": len(c_files), "compiledFiles": len(c_files), "totalObjects": len(all_tus),
        "elf32MipsVerifiedObjects": len(all_tus) - elf_bad, "archivePath": archive_path.relative_to(archive_base).as_posix(),
        "fileSizeBytes": archive_path.stat().st_size, "compilerErrorCount": len(fails), "compilerWarningCount": warn_cnt,
        "craftsmanshipTellCount": tell_cnt, "compilerFlags": pass1_warn_flags,
        "compilerErrors": len(fails), "compilerWarnings": warn_cnt, "parityTarget": PARITY_TARGET,
        "assertionsPassedCount": passed_cnt, "assertionsTotalCount": total_cnt, "parityTestsPassed": passed_cnt,
        "parityPassed": is_passed, "isPassed": is_passed,
        "parityResults": [{"name": t["name"], "isPassed": bool(t.get("isPassed", t.get("passed")))} for t in pj.get("tests", [])],
    }
    report_out.parent.mkdir(parents=True, exist_ok=True)
    report_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    logger.info("D4 build complete: compiled=%d objs=%d tells=%d assertions=%d/%d", len(c_files), len(all_tus), tell_cnt, passed_cnt, total_cnt)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build MIPS ELF32 objects and run modular D4 LP32 parity tests.")
    parser.add_argument("--data-dir", type=Path, default=None)
    parser.add_argument("--log-dir", type=Path, default=None)
    parser.add_argument("--zig-exe", type=Path, default=None)
    parser.add_argument("--offline-synthetic", action="store_true")
    args = parser.parse_args(argv)

    logger, zig_exe = setup_logger("build_and_verify_d4", args.log_dir), resolve_zig_exe(args.zig_exe)
    manifest = json.loads((DEV_DIR / "research.manifest.json").read_text(encoding="utf-8"))
    if args.offline_synthetic:
        with tempfile.TemporaryDirectory() as tmp:
            base = args.data_dir if args.data_dir is not None else Path(tmp)
            standalone, readable, work = seed_synthetic_corpus(base)
            rep = build_and_verify(zig_exe, readable, work, standalone, manifest["gameId"], logger, work / "d4_build_report.json", base, strict_corpus=True)
            print(json.dumps({"mode": "offline-synthetic", "isPassed": rep["isPassed"], "compiledFileCount": rep["compiledFileCount"], "totalObjects": rep["totalObjects"], "fileSizeBytes": rep["fileSizeBytes"], "craftsmanshipTellCount": rep["craftsmanshipTellCount"], "assertionsPassedCount": rep["assertionsPassedCount"], "assertionsTotalCount": rep["assertionsTotalCount"]}, indent=2))
            return 0 if rep["isPassed"] else 1

    corpus_dir = args.data_dir if args.data_dir is not None else (PROJ_ROOT / "Corpus")
    readable_dir, work_dir, standalone_dir = corpus_dir / "readable", corpus_dir / "work", corpus_dir / "standalone"
    if args.data_dir is None and not standalone_dir.is_dir() and (def_raw := str(manifest.get("deferredStandalonePath") or "").strip()):
        standalone_dir = Path(def_raw) if Path(def_raw).is_absolute() else (DEV_DIR / def_raw).resolve()
    if not (readable_dir / "include/kingsfield_globals.h").is_file() or not standalone_dir.is_dir():
        print(json.dumps({"status": "MISSING_CORPUS_MEDIA", "message": "Missing Corpus/readable or Corpus/standalone media.", "dataDir": str(corpus_dir)}, indent=2))
        return 1
    report_out = (work_dir / "d4_build_report.json") if args.data_dir is not None else (DEV_DIR / "schemas/d4_build_report.json")
    rep = build_and_verify(zig_exe, readable_dir, work_dir, standalone_dir, manifest["gameId"], logger, report_out, corpus_dir, strict_corpus=False)
    print(json.dumps({"mode": "corpus", "isPassed": rep["isPassed"], "compiledFileCount": rep["compiledFileCount"], "totalObjects": rep["totalObjects"], "fileSizeBytes": rep["fileSizeBytes"], "craftsmanshipTellCount": rep["craftsmanshipTellCount"], "assertionsPassedCount": rep["assertionsPassedCount"], "assertionsTotalCount": rep["assertionsTotalCount"]}, indent=2))
    return 0 if rep["isPassed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
