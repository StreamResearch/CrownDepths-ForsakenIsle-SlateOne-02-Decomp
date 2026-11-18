#!/usr/bin/env python3
# @module: CrownDepths.Dev.scripts.materialize_decomp_tiers
# @purpose: Materialize Corpus/tiers/{D1_Raw,D2_Structured,D3_Mapped,D4_CleanSource} and 27 cohesive D3 modules
# @depends-on: argparse, collections, importlib, json, logging, os, re, shutil, stat, sys, tempfile, time, pathlib
# @exports: TIER_NAMES, classify_symbol, coalesce_d3_modules, materialize_tiers, main

from __future__ import annotations

import argparse
import collections
import importlib
import json
import logging
import os
import re
import shutil
import stat
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
DEV_DIR = SCRIPT_DIR.parent
REPO_ROOT = DEV_DIR.parent
TIER_NAMES = ("D1_Raw", "D2_Structured", "D3_Mapped", "D4_CleanSource")
_FUNC_RE = re.compile(r"^// Function:\s+(\S+)\s+@\s+0x([0-9a-fA-F]+)", re.M)
_SDK_RULES = (
    (frozenset({"printf", "sprintf", "rand", "srand", "memcpy", "memset", "memmove", "memcmp", "strcpy", "strncpy", "strcmp", "strncmp", "strlen", "strcat", "malloc", "free", "calloc", "realloc", "abs", "setjmp", "longjmp", "qsort", "bsearch", "exit", "atoi"}), "sdk/ps1_libc_and_mem.c"),
    (frozenset({"GPU_cw", "SetBackColor", "SetFarColor", "ReadORGB", "ReadGeomOffset", "LoadAverage12", "LoadAverage0", "SetMulMatrix", "ApplyMatrix", "SetRotMatrix", "SetLightMatrix", "SetColorMatrix", "SetTransMatrix", "AverageZ3", "rcossin"}), "sdk/ps1_gpu_and_gte.c"),
    (frozenset({"CdGetSector", "ChangeClearPAD", "PAD_dr", "StopPAD2", "PAD_init2", "_card_info", "_card_write", "InitCARD2", "firstfile2", "close", "write", "erase"}), "sdk/ps1_cd_pad_and_memcard.c"),
)
_MOD_ROUTES = {
    "kf_open_": {"cd": "open_cd_and_mdec_str", "mdec": "open_cd_and_mdec_str", "dec": "open_cd_and_mdec_str", "decode": "open_cd_and_mdec_str", "st": "open_cd_and_mdec_str", "gpu": "open_gpu_and_draw", "gs": "open_gpu_and_draw", "draw": "open_gpu_and_draw", "ss": "open_ss_seq_driver", "spu": "open_spu_voice_driver"},
    "kf_end_": {"cd": "end_cd_and_mdec_str", "mdec": "end_cd_and_mdec_str", "dec": "end_cd_and_mdec_str", "decode": "end_cd_and_mdec_str", "st": "end_cd_and_mdec_str", "gpu": "end_gpu_and_draw", "draw": "end_gpu_and_draw", "ss": "end_ss_seq_driver", "spu": "end_spu_voice_driver"},
    "kf_game_": {
        "math": "game_core_and_math/game_fixed_math", "mc": "game_cd_and_archives/game_save_and_memcard", "save": "game_cd_and_archives/game_save_and_memcard",
        **dict.fromkeys(("cd", "t", "stream", "load", "mount", "open"), "game_cd_and_archives/game_cd_and_t_archives"),
        **dict.fromkeys(("world", "map", "mapobj", "obj", "prop", "pvs", "collision", "event"), "game_world_and_entities/game_world_map_and_props"),
        **dict.fromkeys(("entity", "ai", "npc"), "game_world_and_entities/game_entity_and_ai"),
        **dict.fromkeys(("player", "combat", "proj", "input", "pad"), "game_world_and_entities/game_player_and_combat"),
        **dict.fromkeys(("gte", "tmd", "mo", "fx3d", "render"), "game_render_and_gfx/game_gte_and_tmd_meshes"),
        **dict.fromkeys(("gpu", "gfx", "gs", "draw", "dma", "submit", "upload"), "game_render_and_gfx/game_gpu_and_gfx_packets"),
        **dict.fromkeys(("ui", "inv", "item", "enum"), "game_ui_and_inventory/game_ui_menus_and_hud"),
        "audio": "game_audio_spu/game_audio_and_seq", "snd": "game_audio_spu/game_audio_and_seq", "spu": "game_audio_spu/game_spu_driver",
    },
}
_DOMAIN_LABELS = {
    "boot_slus": "SLUS Boot Dispatcher", "game_core_and_math": "Game Main & Fixed Math",
    "game_cd_and_archives": "CD Streaming & MemCard", "game_world_and_entities": "World, AI & Player",
    "game_render_and_gfx": "GTE, TMD & GPU Packets", "game_ui_and_inventory": "Menus, Inventory & Dialogue",
    "game_audio_spu": "Audio SEQ & SPU Driver", "open_title_and_fmv": "Opening Title & FMV",
    "end_credits_and_str": "Credits & STR Playback", "sdk": "PS1 BIOS, CRT & Runtime SDK",
}


def _setup_logger(log_dir: Path | None) -> logging.Logger:
    logger = logging.getLogger("materialize_decomp_tiers")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_dir / "materialize_decomp_tiers.log", encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(fh)
    else:
        logger.addHandler(logging.NullHandler())
    return logger


def _heartbeat(last_ts: float, msg: str, force: bool = False) -> float:
    now = time.monotonic()
    if force or (now - last_ts) >= 12.0:
        sys.stderr.write(f"\r\x1b[K[materialize_decomp_tiers] {msg}")
        sys.stderr.flush()
        return now
    return last_ts


def _rmtree_force(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path, onexc=lambda fn, p, _: (os.chmod(p, stat.S_IWRITE | stat.S_IREAD), fn(p)))


def _clear_readonly(root: Path) -> int:
    cnt = 0
    for fp in root.rglob("*"):
        if fp.is_file():
            os.chmod(fp, stat.S_IWRITE | stat.S_IREAD)
            cnt += 1
    return cnt


def classify_symbol(src_rel: str, sym: str) -> str:
    """Map a function symbol and source path to one of 27 cohesive D3 modules."""
    if src_rel.startswith("sdk/") or not sym.startswith("kf_"):
        base = sym.split("_dup_")[0]
        return next((dst for syms, dst in _SDK_RULES if base in syms), "sdk/ps1_bios_kernel_and_events.c")
    if sym.startswith("kf_slus_") or src_rel.startswith("src/core/"):
        return "src/boot_slus/slus_boot_dispatcher.c"
    parts = sym.split("_")
    sub = parts[2] if len(parts) >= 3 else ""
    if sym.startswith("kf_open_"):
        return f"src/open_title_and_fmv/{_MOD_ROUTES['kf_open_'].get(sub, 'open_title_and_main')}.c"
    if sym.startswith("kf_end_"):
        return f"src/end_credits_and_str/{_MOD_ROUTES['kf_end_'].get(sub, 'end_credits_and_main')}.c"
    return f"src/{_MOD_ROUTES['kf_game_'].get(sub, 'game_core_and_math/game_main_and_sys')}.c"


def _rewrite_cdb_and_clangd(tree_dir: Path) -> None:
    inc, compat = (tree_dir / "include").as_posix(), (tree_dir / "include" / "ghidra_compat.h").as_posix()
    clangd_p = tree_dir / ".clangd"
    if clangd_p.is_file():
        txt = re.sub(r"(?m)^(\s*- -I).*$", rf"\1{inc}", clangd_p.read_text(encoding="utf-8", errors="replace"))
        txt = re.sub(r"(?m)^(\s*- ).*/include/ghidra_compat\.h$", rf"\1{compat}", txt)
        clangd_p.write_text(txt, encoding="utf-8", newline="\n")
    args = ["clang", "-target", "mipsel-unknown-none-elf", "-ffreestanding", "-std=gnu11", "-ferror-limit=0", f"-I{inc}", "-include", compat, "-c"]
    entries = [{"directory": tree_dir.as_posix(), "file": c.as_posix(), "arguments": [*args, c.as_posix()]} for c in sorted(tree_dir.rglob("*.c"))]
    (tree_dir / "compile_commands.json").write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8", newline="\n")


def _extract_func_blocks(text: str) -> list[tuple[int, str, str]]:
    pos = [m.start() for m in _FUNC_RE.finditer(text)]
    starts: list[int] = []
    for i, idx in enumerate(pos):
        prev = pos[i - 1] if i > 0 else 0
        doc = text.rfind("\n/**", prev, idx)
        if doc >= 0 and "*/" in text[doc:idx]:
            starts.append(doc + 1)
        elif i == 0 and text.lstrip().startswith("/**") and "*/" in text[:idx]:
            starts.append(text.find("/**"))
        else:
            starts.append(idx)
    blocks: list[tuple[int, str, str]] = []
    for i, st in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(text)
        blk = text[st:end].strip()
        if m := _FUNC_RE.search(blk):
            blocks.append((int(m.group(2), 16), m.group(1), blk))
    return blocks


def coalesce_d3_modules(src_dir: Path, dst_dir: Path) -> dict[str, Any]:
    """Coalesce 259 structured chunks from src_dir into 27 cohesive D3 modules in dst_dir."""
    _rmtree_force(dst_dir)
    dst_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src_dir, dst_dir, ignore=shutil.ignore_patterns(".cache", "__pycache__", "overlays", "sdk", "src"))
    old_c = sorted(src_dir.rglob("*.c"))
    grouped: dict[str, list[tuple[int, str, str]]] = collections.defaultdict(list)
    sym_to_rel: dict[str, str] = {}
    dom_counts: dict[str, list[int]] = collections.defaultdict(lambda: [0, 0])
    for cf in old_c:
        rel = cf.relative_to(src_dir).as_posix()
        for addr, sym, body in _extract_func_blocks(cf.read_text(encoding="utf-8", errors="replace")):
            target = classify_symbol(rel, sym)
            grouped[target].append((addr, sym, body))
            sym_to_rel[sym] = target
    for target, items in sorted(grouped.items()):
        items.sort(key=lambda t: (t[0], t[1]))
        prefix = "../include/" if target.startswith("sdk/") else "../../include/"
        hdr = f'#include "{prefix}kingsfield_types.h"\n#include "{prefix}kingsfield_globals.h"\n#include "{prefix}kingsfield_functions.h"\n\n'
        out_p = dst_dir / target
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(hdr + "\n\n".join(b for _, _, b in items) + "\n", encoding="utf-8", newline="\n")
        top = "sdk" if target.startswith("sdk/") else target.split("/")[1]
        dom_counts[top][0] += len(items)
        dom_counts[top][1] += 1
    if (sym_p := dst_dir / "SYMBOL_MAP.md").is_file():
        row_re = re.compile(r"^(\| `0x[0-9a-fA-F]+` \| `[^`]+` \| `[^`]+` \| \d+ \| `)([^`]+)(` \| )\[`[^`]+`\]\([^)]+\)( \| .*)$")
        rows = [f"{m.group(1)}{m.group(2)}{m.group(3)}[`{sym_to_rel[m.group(2)]}`]({sym_to_rel[m.group(2)]}){m.group(4)}" if (m := row_re.match(ln)) and m.group(2) in sym_to_rel else ln for ln in sym_p.read_text(encoding="utf-8").splitlines()]
        sym_p.write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
    rows_md = [f"| `{k}` | {_DOMAIN_LABELS.get(k, k)} | {v[0]} | {v[1]} |" for k, v in sorted(dom_counts.items())]
    (dst_dir / "ARCHITECTURE_WALKTHROUGH.md").write_text("\n".join([
        "# CrownDepths ForsakenIsle (SlateOne) 02 — Cohesive Architecture Walkthrough", "",
        "- **Game ID:** `kings-field` (`ps1` / `SLUS-00158`, ABI `ps1-mipsel`)",
        f"- **Coverage:** `{len(sym_to_rel)}` functions across `{len(grouped)}` cohesive modules", "",
        "## Cohesive Modules (`src/<subsystem>/` & `sdk/`)", "| Folder | Role | Functions | Modules |", "| --- | --- | ---: | ---: |", *rows_md, "",
    ]), encoding="utf-8", newline="\n")
    _rewrite_cdb_and_clangd(dst_dir)
    return {"cFiles": len(grouped), "functions": len(sym_to_rel), "files": sum(1 for p in dst_dir.rglob("*") if p.is_file())}


def _materialize_d1(corpus_dir: Path, tier_dir: Path, logger: logging.Logger) -> dict[str, Any]:
    src = corpus_dir / "standalone" / "decompiled"
    if not src.is_dir() or not any(src.glob("*/functions.json")):
        raise FileNotFoundError(str(src))
    ts = _heartbeat(0.0, "Copying D1_Raw...", force=True)
    _rmtree_force(tier_dir)
    shutil.copytree(src, tier_dir)
    files = _clear_readonly(tier_dir)
    _heartbeat(ts, f"D1_Raw ready ({files} files)\n", force=True)
    logger.info("D1_Raw materialized files=%d", files)
    return {"path": str(tier_dir), "files": files}


def _materialize_d2(corpus_dir: Path, tier_dir: Path, tools_dir: Path | None, logger: logging.Logger) -> dict[str, Any]:
    if tier_dir.is_dir() and sum(1 for _ in tier_dir.rglob("*.c")) == 259:
        _rewrite_cdb_and_clangd(tier_dir)
        return {"path": str(tier_dir), "cFiles": 259, "preserved": True}
    src_r = corpus_dir / "readable"
    if src_r.is_dir() and sum(1 for _ in src_r.rglob("*.c")) == 259:
        _rmtree_force(tier_dir)
        shutil.copytree(src_r, tier_dir, ignore=shutil.ignore_patterns(".cache", "__pycache__"))
        _rewrite_cdb_and_clangd(tier_dir)
        logger.info("D2_Structured captured 259 chunks from readable/")
        return {"path": str(tier_dir), "cFiles": 259}
    reexp = corpus_dir / "work" / "reexported"
    if not reexp.is_dir() or not any(reexp.glob("*/functions.json")):
        raise FileNotFoundError(str(reexp))
    t_root = tools_dir.resolve() if tools_dir else (REPO_ROOT.parent.parent / "Personal" / "R&D" / "Dev" / "tools" / "decomp")
    sys.path.insert(0, str(t_root.parent if (t_root / "stage4_assembler.py").is_file() else t_root))
    s4 = importlib.import_module("decomp.stage4_assembler")
    with tempfile.TemporaryDirectory() as tmp:
        st = Path(tmp) / "track"
        (st / "Dev").mkdir(parents=True)
        shutil.copy2(DEV_DIR / "research.manifest.json", st / "Dev" / "research.manifest.json")
        shutil.copytree(DEV_DIR / "schemas", st / "Dev" / "schemas")
        s4.run_stage4_assemble(st, export_dir=reexp)
        _rmtree_force(tier_dir)
        shutil.copytree(st / "Corpus" / "readable", tier_dir)
    _rewrite_cdb_and_clangd(tier_dir)
    return {"path": str(tier_dir), "cFiles": sum(1 for _ in tier_dir.rglob("*.c"))}


def _sync_copy(src_dir: Path, dst_dir: Path) -> dict[str, Any]:
    _rmtree_force(dst_dir)
    shutil.copytree(src_dir, dst_dir, ignore=shutil.ignore_patterns(".cache", "__pycache__"))
    _rewrite_cdb_and_clangd(dst_dir)
    return {"path": str(dst_dir), "cFiles": sum(1 for _ in dst_dir.rglob("*.c"))}


def materialize_tiers(data_dir: Path | None = None, tools_dir: Path | None = None, tier: str = "all", offline_synthetic: bool = False, log_dir: Path | None = None) -> dict[str, Any]:
    """Materialize Corpus/tiers/{D1_Raw..D4_CleanSource} and sync cohesive Corpus/readable/."""
    logger = _setup_logger(log_dir)
    corpus = data_dir.resolve() if data_dir is not None else (Path(tempfile.mkdtemp(prefix="kf_tiers_syn_")) if offline_synthetic else (REPO_ROOT / "Corpus"))
    selected = list(TIER_NAMES) if tier == "all" else [tier]
    if offline_synthetic:
        samples = {
            "D1_Raw": ("SLUS_001.58/funcs/80010128_kf_slus_crt0_start.c", "void kf_slus_crt0_start(void) {}\n"),
            "D2_Structured": ("overlays/GAME.EXE/game_01.c", "void kf_game_math_step_linear_clamp(void) {}\n"),
            "D3_Mapped": ("src/game_core_and_math/game_fixed_math.c", "s32 kf_game_math_step_linear_clamp(s32 c, s32 t, s32 d) { return c; }\n"),
            "D4_CleanSource": ("src/game_core_and_math/game_fixed_math.c", "s32 kf_game_math_step_linear_clamp(s32 cur_val, s32 target_val, s32 step_delta) { return cur_val; }\n"),
        }
        out = {}
        for t in selected:
            td = corpus / "tiers" / t
            _rmtree_force(td)
            fp = td / samples[t][0]
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(samples[t][1], encoding="utf-8", newline="\n")
            out[t] = {"path": str(td), "cFiles": 1, "synthetic": True}
        return {"status": "OK", "mode": "offline-synthetic", "dataDir": str(corpus), "tiers": out}
    tiers_root, out = corpus / "tiers", {}
    if "D1_Raw" in selected:
        out["D1_Raw"] = _materialize_d1(corpus, tiers_root / "D1_Raw", logger)
    if any(t in selected for t in ("D2_Structured", "D3_Mapped", "D4_CleanSource")):
        out["D2_Structured"] = _materialize_d2(corpus, tiers_root / "D2_Structured", tools_dir, logger)
    if any(t in selected for t in ("D3_Mapped", "D4_CleanSource")):
        d3_info = coalesce_d3_modules(tiers_root / "D2_Structured", tiers_root / "D3_Mapped")
        out["D3_Mapped"] = {"path": str(tiers_root / "D3_Mapped"), **d3_info}
        out["readableSync"] = _sync_copy(tiers_root / "D3_Mapped", corpus / "readable")
    if "D4_CleanSource" in selected:
        out["D4_CleanSource"] = _sync_copy(tiers_root / "D3_Mapped", tiers_root / "D4_CleanSource")
    return {"status": "OK", "mode": "live", "dataDir": str(corpus), "tiers": out}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Materialize multi-tier snapshots under Corpus/tiers/ and coalesce 27 D3 modules.")
    ap.add_argument("--data-dir", type=Path, default=None)
    ap.add_argument("--tools-dir", type=Path, default=None)
    ap.add_argument("--log-dir", type=Path, default=None)
    ap.add_argument("--tier", choices=["all", *TIER_NAMES], default="all")
    ap.add_argument("--offline-synthetic", action="store_true")
    args = ap.parse_args(argv)
    try:
        res = materialize_tiers(args.data_dir, args.tools_dir, args.tier, args.offline_synthetic, args.log_dir)
    except FileNotFoundError as exc:
        print(json.dumps({"status": "MISSING_CORPUS_MEDIA", "errorCode": "MISSING_CORPUS_MEDIA", "missingPath": str(exc)}, indent=2))
        return 2
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
