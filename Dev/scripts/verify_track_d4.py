# @module: KingsField.Dev.scripts.verify_track_d4
# @purpose: Independent Stage D3/D4 verifier enforcing Standard 18 reports, modular harness SLOC/zero-warnings, and 28-object MIPS build
# @depends-on: argparse, json, logging, re, subprocess, sys, tempfile, pathlib, d4_synthetic_corpus, build_and_verify_d4
# @exports: count_code_sloc, run_checks, main

from __future__ import annotations

import argparse
import json
import logging
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
DEV_DIR = SCRIPT_DIR.parent
PROJ_ROOT = DEV_DIR.parent if DEV_DIR.name == "Dev" else DEV_DIR
SCHEMAS_DIR = DEV_DIR / "schemas"
MANIFEST_PATH = DEV_DIR / "research.manifest.json"
BANNED_REPORT_KEYS = frozenset({"passed", "errors", "warnings", "archiveFile", "archiveBytes", "parityTestsTotal"})

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from build_and_verify_d4 import STRICT_FLAGS, build_and_verify, check_elf_mips, resolve_zig_exe, zig_env  # noqa: E402
from d4_synthetic_corpus import count_craftsmanship_tells, seed_synthetic_corpus, setup_logger  # noqa: E402


def count_code_sloc(path: Path) -> int:
    """Count non-blank, non-comment code-only lines for C/H/Python files."""
    sloc, in_block = 0, False
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = raw.strip()
        if not s:
            continue
        if in_block:
            if "*/" in s:
                in_block = False
            continue
        if s.startswith("/*"):
            if "*/" not in s:
                in_block = True
            continue
        if s.startswith(("//", "#")):
            continue
        sloc += 1
    return sloc


def _check(name: str, ok: bool, detail: str, failures: list[str]) -> None:
    if not ok:
        failures.append(f"[{name}] {detail}")


def _find_banned_keys(obj: Any) -> list[str]:
    found: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in BANNED_REPORT_KEYS:
                found.append(k)
            found.extend(_find_banned_keys(v))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(_find_banned_keys(item))
    return sorted(set(found))


def _verify_elf_objects(obj_root: Path, min_count: int) -> tuple[int, int]:
    objs = sorted(obj_root.rglob("*.o")) if obj_root.is_dir() else []
    bad = sum(1 for obj in objs if not check_elf_mips(obj))
    return len(objs), bad if len(objs) >= min_count else max(bad, 1)


def _check_harness_zero_warnings(zig_exe: Path, inc_dir: Path, work_dir: Path, harness_c: list[Path], failures: list[str]) -> None:
    env = zig_env(work_dir)
    compat = inc_dir / "ghidra_compat.h"
    cmd_base = [str(zig_exe), "cc", "-target", "x86-windows-gnu", "-std=gnu11", "-O1", "-fno-strict-aliasing", *STRICT_FLAGS, f"-I{inc_dir}", f"-I{SCRIPT_DIR / 'd4_harness'}", "-include", str(compat)]
    bad: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        for src in harness_c:
            res = subprocess.run([*cmd_base, "-c", str(src), "-o", str(Path(tmp) / f"{src.stem}.o")], env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
            warns = len(re.findall(r"\bwarning:", res.stderr or ""))
            if res.returncode != 0 or warns != 0:
                bad.append(f"{src.name}(rc={res.returncode},w={warns})")
    _check("D4.harness_zero_warnings", not bad, f"failed={bad}", failures)


def _check_synthetic_build(data_dir: Path | None, zig_exe: Path, harness_c: list[Path], logger: logging.Logger, failures: list[str]) -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        base = data_dir if (data_dir is not None and (data_dir / "work" / "d4_build").is_dir()) else Path(tmp)
        work_dir = base / "work"
        if not (work_dir / "d4_build" / "obj").is_dir():
            standalone, readable, work_dir = seed_synthetic_corpus(base)
            s_rep = build_and_verify(zig_exe, readable, work_dir, standalone, manifest["gameId"], logger, work_dir / "d4_build_report.json", base, strict_corpus=True)
        else:
            readable = base / "readable"
            rep_file = work_dir / "d4_build_report.json"
            s_rep = json.loads(rep_file.read_text(encoding="utf-8")) if rep_file.is_file() else {}
        if s_rep:
            _check("D4.synthetic_parity", s_rep.get("isPassed") is True and int(s_rep.get("assertionsPassedCount", 0)) >= 10, f"passed={s_rep.get('assertionsPassedCount')}/{s_rep.get('assertionsTotalCount')}", failures)
        tell_files, tell_hits = count_craftsmanship_tells(sorted(readable.rglob("*.c")))
        _check("D4.synthetic_craftsmanship", tell_hits == 0, f"hits={tell_hits} files={tell_files}", failures)
        _check_harness_zero_warnings(zig_exe, readable / "include", work_dir, harness_c, failures)
        arch = work_dir / "d4_build" / "libkings_field_d4.a"
        obj_cnt, bad_elf = _verify_elf_objects(work_dir / "d4_build" / "obj", 7)
        _check("D4.synthetic_archive", arch.is_file() and arch.stat().st_size > 0, f"archive={arch.name} size={arch.stat().st_size if arch.is_file() else 0}", failures)
        _check("D4.synthetic_elf32_mips", obj_cnt >= 7 and bad_elf == 0, f"objs={obj_cnt} bad_elf={bad_elf}", failures)


def run_checks(data_dir: Path | None, offline_synthetic: bool, zig_exe: Path | None, logger: logging.Logger) -> tuple[dict[str, Any], list[str]]:
    """Run independent D3/D4 schema, harness SLOC/zero-warnings, archive, and ELF32 MIPS checks."""
    failures: list[str] = []
    resolved_zig = resolve_zig_exe(zig_exe)
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    rep_path = SCHEMAS_DIR / "d4_build_report.json"
    _check("D4.report_exists", rep_path.is_file(), f"Missing {rep_path}", failures)
    rep = json.loads(rep_path.read_text(encoding="utf-8")) if rep_path.is_file() else {}

    banned_d4 = _find_banned_keys(rep)
    bridge_ok = all(k in rep for k in ("verifiedAtUtc", "compiledFiles", "compilerErrors", "compilerWarnings", "parityTestsPassed", "parityPassed"))
    _check("D4.report_schema", not banned_d4 and rep.get("schemaVersion") == 2 and bool(rep.get("generatedAtUtc")) and bridge_ok, f"banned={banned_d4} schemaVersion={rep.get('schemaVersion')} bridge={bridge_ok}", failures)
    if (s4_path := SCHEMAS_DIR / "s4_verify_report.json").is_file():
        s4_rep = json.loads(s4_path.read_text(encoding="utf-8"))
        banned_s4 = _find_banned_keys(s4_rep)
        _check("D4.s4_report_schema", not banned_s4 and s4_rep.get("schemaVersion") == 2 and s4_rep.get("isPassed") is True, f"banned={banned_s4} isPassed={s4_rep.get('isPassed')}", failures)

    comp_cnt = int(rep.get("compiledFileCount", rep.get("compiledFiles", 0)))
    err_cnt = int(rep.get("compilerErrorCount", rep.get("compilerErrors", -1)))
    warn_cnt = int(rep.get("compilerWarningCount", rep.get("compilerWarnings", -1)))
    passed_cnt = int(rep.get("assertionsPassedCount", rep.get("parityTestsPassed", 0)))
    total_cnt = int(rep.get("assertionsTotalCount", passed_cnt))
    tell_cnt = int(rep.get("craftsmanshipTellCount", 0))
    _check("D4.compile_counts", comp_cnt in (6, 27) and int(rep.get("totalObjects", 0)) == comp_cnt + 1 and err_cnt == 0 and warn_cnt == 0, f"compiled={comp_cnt} objs={rep.get('totalObjects')} err={err_cnt} warn={warn_cnt}", failures)
    _check("D4.parity", rep.get("isPassed") is True and rep.get("parityPassed") is True and passed_cnt >= 10 and passed_cnt == total_cnt, f"isPassed={rep.get('isPassed')} assertions={passed_cnt}/{total_cnt}", failures)

    tier = manifest.get("currentDecompTier")
    d4_gate_ok = ((manifest.get("gates") or {}).get("D4") or {}).get("passed")
    manifest_ok = (tier == "D3" and d4_gate_ok is False) or (tier == "D4" and d4_gate_ok is True and tell_cnt == 0)
    _check("D4.manifest", manifest_ok, f"tier={tier} d4Gate={d4_gate_ok} tells={tell_cnt}", failures)

    harness_dir = SCRIPT_DIR / "d4_harness"
    harness_c, harness_h = sorted(harness_dir.glob("*.c")), sorted(harness_dir.glob("*.h"))
    _check("D4.modular_harness", len(harness_c) >= 3 and len(harness_h) >= 1 and not (harness_dir / "parity_tests.c").exists(), f"c={len(harness_c)} h={len(harness_h)}", failures)
    sloc_over = [f"{p.name}({count_code_sloc(p)})" for p in [*harness_c, *harness_h, SCRIPT_DIR / "d4_synthetic_corpus.py", SCRIPT_DIR / "build_and_verify_d4.py", SCRIPT_DIR / "verify_track_d4.py", SCRIPT_DIR / "materialize_decomp_tiers.py"] if p.is_file() and count_code_sloc(p) > 250]
    _check("D4.sloc_limits", not sloc_over, f"over_250_sloc={sloc_over}", failures)

    stage_doc = DEV_DIR / "docs" / "stages" / "04-stage4-d4-compilation-and-parity.md"
    _check("D4.stage_doc_exists", stage_doc.is_file(), f"Missing {stage_doc}", failures)

    if offline_synthetic:
        _check_synthetic_build(data_dir, resolved_zig, harness_c, logger, failures)
    else:
        corpus_dir = data_dir if data_dir is not None else (PROJ_ROOT / "Corpus")
        readable_dir, work_dir = corpus_dir / "readable", corpus_dir / "work"
        if not readable_dir.is_dir():
            _check("D4.corpus_media", False, f"MISSING_CORPUS_MEDIA: missing {readable_dir}", failures)
        else:
            c_files = sorted(readable_dir.rglob("*.c"))
            _check("D4.c_files", len(c_files) == 27 and comp_cnt == 27, f"found={len(c_files)} compiled={comp_cnt}", failures)
            missing_tiers = [t for t in ("D1_Raw", "D2_Structured", "D3_Mapped") if not (corpus_dir / "tiers" / t).is_dir()]
            if not any((corpus_dir / "tiers" / d4).is_dir() for d4 in ("D4_CleanSource", "D4_FunctionalRewrite")):
                missing_tiers.append("D4_CleanSource")
            _check("D4.tiers_present", not missing_tiers, f"missing_tiers={missing_tiers}", failures)
            _check_harness_zero_warnings(resolved_zig, readable_dir / "include", work_dir, harness_c, failures)
            arch = corpus_dir / str(rep.get("archivePath") or "work/d4_build/libkings_field_d4.a")
            exp_sz = int(rep.get("fileSizeBytes", 0))
            _check("D4.archive", arch.is_file() and arch.stat().st_size > 100000 and (exp_sz == 0 or arch.stat().st_size == exp_sz), f"archive={arch.name} size={arch.stat().st_size if arch.is_file() else 0}", failures)
            obj_cnt, bad_elf = _verify_elf_objects(work_dir / "d4_build" / "obj", 28)
            _check("D4.elf32_mips", obj_cnt == 28 and bad_elf == 0, f"objs={obj_cnt} bad_elf={bad_elf}", failures)
            compat = readable_dir / "include" / "ghidra_compat.h"
            has_rec = compat.is_file() and bool(re.search(r'^\s*#include\s+"[^"]*_types\.h"', compat.read_text(encoding="utf-8"), re.M))
            _check("D4.compat_hygiene", compat.is_file() and not has_rec, f"recursive_include={has_rec}", failures)

    summary = {
        "isPassed": not failures, "mode": "offline-synthetic" if offline_synthetic else "corpus",
        "compiledFileCount": comp_cnt, "craftsmanshipTellCount": tell_cnt,
        "assertionsPassedCount": passed_cnt, "assertionsTotalCount": total_cnt, "failures": failures,
    }
    logger.info("verify_track_d4 mode=%s isPassed=%s failures=%d", summary["mode"], summary["isPassed"], len(failures))
    return summary, failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify D3/D4 MIPS build artifacts, harness modularity, and report contracts.")
    parser.add_argument("--data-dir", type=Path, default=None, help="Isolated corpus/work directory.")
    parser.add_argument("--log-dir", type=Path, default=None, help="Optional diagnostic log directory.")
    parser.add_argument("--zig-exe", type=Path, default=None, help="Optional explicit zig compiler path.")
    parser.add_argument("--offline-synthetic", action="store_true", help="Verify D4 reports, modular harness, and synthetic Zig ELF32 build.")
    args = parser.parse_args(argv)

    logger = setup_logger("verify_track_d4", args.log_dir)
    summary, failures = run_checks(args.data_dir, args.offline_synthetic, args.zig_exe, logger)
    print(json.dumps(summary, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
