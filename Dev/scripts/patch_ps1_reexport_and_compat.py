#!/usr/bin/env python3
# @module: KingsFieldPS1.Dev.scripts.patch_ps1_reexport_and_compat
# @purpose: Normalize PS1 reexported Ghidra C lifts, run Stage 4 assembly, dedupe multi-EXE SDKs, and patch compat headers
# @depends-on: argparse, json, logging, os, re, sys, pathlib, ps1_compat_helpers
# @exports: resolve_tools_root, patch_work_reexported, main

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DEV_DIR = SCRIPT_DIR.parent
PROJ_ROOT = DEV_DIR.parent if DEV_DIR.name == "Dev" else DEV_DIR
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from ps1_compat_helpers import (  # noqa: E402
    MARKER_BEGIN, MARKER_END, UNDEF_DECL_RE, build_compat_block, code_spans,
    map_code, mask_non_code, match_back, match_fwd,
    rewrite_deref_calls, rewrite_subpieces, rewrite_undef_and_structs, split_args,
)

VALUE_BEFORE_RE = re.compile(r"(?:[=(,?+\-*/%&|^<>!~:\[]|\breturn)\s*$")


def resolve_tools_root(tools_dir: Path | None = None) -> Path:
    """Resolve external R&D tools root from CLI flag, RD_DECOMP_TOOLS env, or relative workspace layout."""
    raw = str(tools_dir) if tools_dir else os.environ.get("RD_DECOMP_TOOLS", "").strip()
    cand = Path(raw).resolve() if raw else (PROJ_ROOT.parent.parent / "Personal" / "R&D" / "Dev" / "tools" / "decomp").resolve()
    return cand.parent if (cand / "stage4_assembler.py").is_file() else cand


def _setup_logger(log_dir: Path | None) -> logging.Logger:
    logger = logging.getLogger("patch_ps1_reexport_and_compat")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(log_dir / "patch_ps1_reexport_and_compat.log", encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(handler)
    else:
        logger.addHandler(logging.NullHandler())
    return logger


def _collect_signatures(reexport_dir: Path) -> tuple[set[str], dict[str, int]]:
    void_names: set[str] = set()
    arities: dict[str, int] = {}
    for fjson in sorted(reexport_dir.glob("*/functions.json")):
        for entry in json.loads(fjson.read_text(encoding="utf-8")).get("functions", []):
            m = re.match(r"^\s*(.+?)\s*\b([A-Za-z_0-9]+)\s*\((.*)\)\s*;?\s*$", entry.get("signature", "").strip())
            if not m:
                continue
            ret, name, params = m.group(1).strip(), entry.get("safe_name") or m.group(2), m.group(3).strip()
            if ret == "void":
                void_names.add(name)
            if "..." not in params and params != "" and name not in arities:
                arities[name] = 0 if params == "void" else len(split_args(params))
    return void_names, arities


def _find_void_value_callers(reexport_dir: Path, void_names: set[str]) -> set[str]:
    promoted: set[str] = set()
    if not void_names:
        return promoted
    call_re = re.compile(r"\b(" + "|".join(re.escape(v) for v in sorted(void_names)) + r")\s*\(")
    for cpath in sorted(reexport_dir.glob("*/funcs/*.c")):
        src = cpath.read_text(encoding="utf-8", errors="replace")
        for s, e, is_c in code_spans(src):
            if not is_c:
                continue
            seg = src[s:e]
            for m in call_re.finditer(seg):
                fn, prefix = m.group(1), seg[: m.start()]
                if re.search(r"\b(?:void|uint32_t|int)\s+$|\(\s*void\s*\)\s*$", prefix):
                    continue
                is_cast, stripped = False, prefix.rstrip()
                if stripped.endswith(")"):
                    lp = match_back(stripped, len(stripped) - 1, "(", ")")
                    if lp >= 0 and not re.search(r"\b(?:if|while|for|switch)\s*$", prefix[:lp].rstrip()):
                        is_cast = not bool(re.match(r"^\(\s*void\s*\)$", stripped[lp:]))
                close_i = match_fwd(seg, m.end() - 1)
                after_val = close_i > 0 and bool(re.match(r"^\s*(?:==|!=|[<>]=?|[+\-*/%&|^?])", seg[close_i + 1 :]))
                if is_cast or after_val or VALUE_BEFORE_RE.search(prefix):
                    promoted.add(fn)
    return promoted


def _reconcile_calls(text: str, arities: dict[str, int]) -> str:
    masked = mask_non_code(text)
    call_re = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(")
    out, i = [], 0
    while m := call_re.search(masked, i):
        fn, open_p = m.group(1), m.end() - 1
        argc, close_p = arities.get(fn), match_fwd(masked, open_p)
        skip_fn = fn in ("setCopReg", "copFunction", "printf", "sprintf", "FntPrint")
        if argc is None or skip_fn or close_p < 0 or re.match(r"^\s*\{", masked[close_p + 1 : close_p + 16]):
            out.append(text[i : m.end()])
            i = m.end()
            continue
        args = split_args(text[open_p + 1 : close_p])
        fixed = args + ["0"] * (argc - len(args)) if len(args) < argc else args[:argc]
        out.append(text[i : open_p + 1] + ", ".join(fixed) + ")")
        i = close_p + 1
    out.append(text[i:])
    return "".join(out)


def patch_work_reexported(reexport_dir: Path) -> tuple[int, int]:
    """Lower Ghidra P-code artifacts and promote void functions used in value contexts."""
    void_names, arities = _collect_signatures(reexport_dir)
    promoted = _find_void_value_callers(reexport_dir, void_names)
    for fjson in reexport_dir.glob("*/functions.json"):
        data, changed = json.loads(fjson.read_text(encoding="utf-8")), False
        for entry in data.get("functions", []):
            sig, nm = entry.get("signature", ""), entry.get("safe_name") or entry.get("name")
            new_sig = re.sub(r"\$(\d+)\b", r"reg_r\1", re.sub(r"\b2MBYTE_OBJ_B4\b", "fn_2MBYTE_OBJ_B4", sig))
            if nm in promoted and new_sig.strip().startswith("void "):
                new_sig = re.sub(r"^void\b", "uint32_t", new_sig.strip(), count=1)
            if new_sig != sig:
                entry["signature"], changed = new_sig, True
        if changed:
            fjson.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    files_changed = 0
    prom_re = re.compile(r"^(\s*)void(\s+(?:" + "|".join(re.escape(p) for p in sorted(promoted)) + r")\s*\()", re.M) if promoted else None
    for cpath in sorted(reexport_dir.glob("*/funcs/*.c")):
        orig = cpath.read_text(encoding="utf-8", errors="replace")
        stack_arrs = {v: int(sz) for v, sz in UNDEF_DECL_RE.findall(orig)}
        cur = map_code(orig, rewrite_subpieces)
        cur = map_code(cur, lambda c: rewrite_undef_and_structs(c, stack_arrs))
        cur = map_code(cur, rewrite_deref_calls)
        if (brace := cur.find("{")) > 0:
            cur = cur[:brace] + _reconcile_calls(cur[brace:], arities)
        if prom_re and prom_re.search(cur):
            cur = prom_re.sub(r"\1uint32_t\2", cur, count=1)
            cur = map_code(cur, lambda c: re.sub(r"\breturn\s*;", "return 0;", c))
        if cur != orig:
            cpath.write_text(cur, encoding="utf-8")
            files_changed += 1
    return files_changed, len(promoted)


def _dedupe_sdk_files(readable_dir: Path) -> int:
    seen_sdk, extra_protos, dups_renamed = set(), [], 0
    for sf in sorted((readable_dir / "sdk").glob("sdk_*.c")):
        blocks = re.split(r"(?=^// Function: )", sf.read_text(encoding="utf-8", errors="replace"), flags=re.M)
        out_blocks = []
        for b in blocks:
            m = re.match(r"^(// Function:\s+)([A-Za-z_][A-Za-z0-9_]*)(\s+@\s+0x([0-9a-fA-F]+).*?\n)(.*)$", b, flags=re.S)
            if not m:
                out_blocks.append(b)
                continue
            nm, addr_hex, body = m.group(2), m.group(4).lower(), m.group(5)
            if nm in seen_sdk:
                dup_nm = f"{nm}_dup_{addr_hex}"
                if sig_m := re.search(rf"^([^\n{{;]*?\b){re.escape(nm)}(\s*\([^)]*\))", body, flags=re.M):
                    extra_protos.append(f"{sig_m.group(1).strip()} {dup_nm}{sig_m.group(2)}; /* dup @ 0x{addr_hex} */")
                body = re.sub(rf"\b{re.escape(nm)}(\s*\()", rf"{dup_nm}\1", body, count=1)
                b, dups_renamed = f"{m.group(1)}{dup_nm}{m.group(3)}{body}", dups_renamed + 1
            else:
                seen_sdk.add(nm)
            out_blocks.append(b)
        sf.write_text("".join(out_blocks), encoding="utf-8", newline="\n")

    fn_h = readable_dir / "include" / "kingsfield_functions.h"
    if fn_h.is_file():
        kept_lines, seen_fn_decls = [], set()
        for ln in fn_h.read_text(encoding="utf-8", errors="replace").splitlines():
            if pm := re.match(r"^[^#/\s].*?\b([A-Za-z_][A-Za-z0-9_]*)\s*\([^;]*\)\s*;", ln):
                if pm.group(1) in seen_fn_decls:
                    continue
                seen_fn_decls.add(pm.group(1))
            kept_lines.append(ln)
        kept_lines.extend(extra_protos)
        fn_h.write_text("\n".join(kept_lines) + "\n", encoding="utf-8", newline="\n")
    return dups_renamed


def _patch_readable_headers(readable_dir: Path) -> None:
    globals_h = readable_dir / "include" / "kingsfield_globals.h"
    g_txt = re.sub(r"/\* 0x[0-9a-fA-F]+ \[[^\]]+\] (?:struct_member|submember|field): (extern [^;]+;) \*/", r"\1", globals_h.read_text(encoding="utf-8", errors="replace"))
    for ctype, syms in {
        "u32": "g_kf_end_ro_ptr_800397e0 g_kf_open_ro_ptr_8003e7cc g_kf_game_ro_ptr_8006e834",
        "s32": "g_kf_game_bss_ptr_801d9c94",
        "u16 *": "g_kf_player_equipped_spell_ptr",
        "u32 *": "g_kf_end_ro_ptr_80039b64 g_kf_open_ro_ptr_8003ebe8 g_kf_game_ro_ptr_8006eac4 g_kf_end_bss_ptr_800a15bc g_kf_open_bss_ptr_800a6648 g_kf_game_bss_ptr_8009b524 g_kf_game_ro_u32_8006e9ac g_kf_open_ro_u32_8003ea78 g_kf_end_ro_u32_80039a1c g_kf_scene_callbacks",
        "u8 *": "g_kf_end_bss_ptr_800a15c4 g_kf_open_bss_ptr_800a6658 g_kf_game_bss_ptr_801b69d0 g_kf_collision_cell_ptr g_kf_open_bss_u32_800ad170 g_kf_game_ro_u32_8006e914 g_kf_player_step_counter g_kf_player_equipped_weapon_ptr g_kf_end_bss_ptr_800a802c g_kf_open_bss_ptr_800ad0e8 g_kf_game_bss_ptr_8016c52c",
        "KfEntityState *": "g_kf_game_bss_u16_ptr_801758f0 g_kf_game_bss_ptr_801758f8",
        "KfEntityDef *": "g_kf_game_bss_u32_ptr_801758ec",
    }.items():
        g_txt = re.sub(rf"(?m)^extern [^;]+\b({'|'.join(syms.split())});", rf"extern {ctype} \1;", g_txt)
    globals_h.write_text(g_txt, encoding="utf-8")

    clangd_p = readable_dir / ".clangd"
    if clangd_p.is_file() and "-ferror-limit=0" not in (cd_txt := clangd_p.read_text(encoding="utf-8")):
        clangd_p.write_text(cd_txt.replace("    - -std=gnu11\n", "    - -std=gnu11\n    - -ferror-limit=0\n", 1), encoding="utf-8", newline="\n")

    compat_h = readable_dir / "include" / "ghidra_compat.h"
    c_txt = re.sub(re.escape(MARKER_BEGIN) + r".*?" + re.escape(MARKER_END) + r"\n?", "", compat_h.read_text(encoding="utf-8", errors="replace"), flags=re.S)
    compat_h.write_text(c_txt.rstrip() + "\n\n" + build_compat_block(g_txt, readable_dir), encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Normalize PS1 reexported C lifts and run Stage 4 assembly.")
    ap.add_argument("--tools-dir", type=Path, default=None, help="Path to external decomp tools root.")
    ap.add_argument("--data-dir", type=Path, default=None, help="Isolated corpus root containing work/reexported.")
    ap.add_argument("--log-dir", type=Path, default=None, help="Optional diagnostic log directory.")
    args = ap.parse_args(argv)

    corpus_dir = args.data_dir.resolve() if args.data_dir is not None else (PROJ_ROOT / "Corpus" if (PROJ_ROOT / "Dev").is_dir() else PROJ_ROOT)
    reexport_dir, readable_dir = corpus_dir / "work" / "reexported", corpus_dir / "readable"
    logger = _setup_logger(args.log_dir)

    if not reexport_dir.is_dir() or not any(reexport_dir.glob("*/functions.json")):
        print(json.dumps({"status": "MISSING_CORPUS_MEDIA", "missingPath": str(reexport_dir)}), file=sys.stderr)
        logger.error("MISSING_CORPUS_MEDIA: %s", reexport_dir)
        return 1

    tools_root = resolve_tools_root(args.tools_dir)
    if str(tools_root) not in sys.path:
        sys.path.insert(0, str(tools_root))
    from decomp import stage4_assembler as s4, workspace_gen as wg

    changed, prom = patch_work_reexported(reexport_dir)
    target_root = corpus_dir if args.data_dir is not None else PROJ_ROOT
    res = s4.run_stage4_assemble(target_root)
    ws_name = json.loads((DEV_DIR / "research.manifest.json").read_text(encoding="utf-8")).get("workspaceFile", "CrownDepths-ForsakenIsle-SlateOne-02-Decomp.code-workspace")
    ws_p = DEV_DIR / str(ws_name)
    ws_saved = ws_p.read_bytes() if ws_p.is_file() else None
    wg.generate_track_workspace(target_root)
    if ws_saved is not None:
        ws_p.write_bytes(ws_saved)
    sdk_dups = _dedupe_sdk_files(readable_dir)
    _patch_readable_headers(readable_dir)

    out = json.dumps({"reexportedModified": changed, "voidPromoted": prom, "sdkDupsRenamed": sdk_dups, "readableFiles": res.get("readableFiles")}, indent=2)
    logger.info("patch_ps1_reexport_and_compat complete: %s", out)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
