# @module: KingsField.Dev.scripts.d4_synthetic_corpus
# @purpose: Shared D4 craftsmanship regex, host stub builder, and synthetic corpus seeder
# @depends-on: logging, re, struct, pathlib
# @exports: LIBC_SYMS, PARITY_TUS, GHIDRA_CRAFT_RE, count_craftsmanship_tells, setup_logger, generate_globals_and_stubs, seed_synthetic_corpus

from __future__ import annotations

import logging
import re
import struct
from pathlib import Path

LIBC_SYMS = frozenset({
    "printf", "sprintf", "rand", "srand", "memcpy", "memset", "memmove", "memcmp",
    "strcpy", "strncpy", "strcmp", "strncmp", "strlen", "strcat", "malloc", "free",
    "calloc", "realloc", "abs", "qsort", "bsearch",
})
PARITY_TUS = (
    "src/game_core_and_math/game_fixed_math.c",
    "src/game_cd_and_archives/game_cd_and_t_archives.c",
    "src/game_cd_and_archives/game_save_and_memcard.c",
    "src/game_world_and_entities/game_player_and_combat.c",
    "src/end_credits_and_str/end_credits_and_main.c",
)
GHIDRA_CRAFT_RE = re.compile(
    r"/\*\s*WARNING:|//\s*Function:|\(void\s*\*\)\s*0x0\b|\(\*\(code\s*\*\)|@(?:callers|callees)\s+none\b"
    r"|\b(?:uVar|iVar|puVar|piVar|pcVar|pbVar|psVar|pvVar|lVar|fVar|dVar|sVar|bVar|cVar|wVar|plVar|ppuVar|CVar)[0-9A-Za-z_]*\b"
    r"|\b_?(?:local_|unaff_|in_|extraout_)[0-9A-Za-z_]*\b|\bstack0x[0-9A-Fa-f]+\b"
    r"|\b_?[A-Za-z]*Stack(?:[XY]?_[0-9A-Za-z]+|0[xX]?[0-9A-Fa-f]+)\b"
    r"|\bparam_[0-9]+\b|\bundefined[1248]?\b|\b(?:FUN|DAT|UNK|PTR|LAB|SUB|switchD)_[0-9A-Za-z_]+\b"
)

_OPAQUE_STRUCTS = (
    ("KfCameraState", 13), ("KfSceneControl", 7), ("KfMapObjDef", 6), ("KfMapObjState", 17),
    ("KfWorldDrop", 6), ("KfTextureAnimSlot", 6), ("KfEntityDef", 30), ("KfEntityState", 31),
    ("KfPlayerState", 88), ("KfItemDef", 8), ("KfMagicDef", 17), ("KfSaveHeader", 256),
)
_HDR_COMPAT = (
    "#pragma once\n#include <stdbool.h>\n#include <stddef.h>\n#include <stdint.h>\n"
    "typedef int8_t s8; typedef uint8_t u8; typedef int16_t s16; typedef uint16_t u16;\n"
    "typedef int32_t s32; typedef uint32_t u32; typedef int64_t s64; typedef uint64_t u64;\n"
)
_HDR_TYPES = (
    "#pragma once\n#include <stdbool.h>\n#include <stddef.h>\n#include <stdint.h>\n"
    "typedef struct RECT { s16 x, y, w, h; } RECT;\n"
    "typedef struct DR_ENV { u32 tag; u32 code[15]; } DR_ENV;\n"
    "typedef struct DRAWENV { RECT clip; s16 ofs[2]; RECT tw; u16 tpage; u8 f[6]; DR_ENV dr_env; } DRAWENV;\n"
    "typedef struct DISPENV { RECT disp, screen; u8 flags[4]; } DISPENV;\n"
    "typedef struct CdlLOC { u8 minute, second, sector, track; } CdlLOC;\n"
    "typedef struct KfGfxEnv { DRAWENV draw[2]; DISPENV disp[2]; } KfGfxEnv;\n"
    "typedef struct KfMapCell { u8 lower[5], upper[5]; } KfMapCell;\n"
    "typedef struct KfTArchiveSlot { u16 *sector_offsets; CdlLOC start_loc; u32 total_size; } KfTArchiveSlot;\n"
    "typedef struct KfMoHeader { u32 total_size, anim_count, tmd_offset, kf_off, anim_table_offset; } KfMoHeader;\n"
    "typedef struct KfFdatHeader { u32 section_size; } KfFdatHeader;\n"
    + "".join(f"typedef struct {nm} {{ u32 words[{n}]; }} {nm};\n" for nm, n in _OPAQUE_STRUCTS)
)
_END_U16_ADDRS = ("7c", "7e", "80", "82", "84", "86", "88", "8a", "90", "92", "94", "96")
_HDR_GLOBALS = "\n".join([
    '#pragma once\n#include "kingsfield_types.h"',
    "extern KfTArchiveSlot g_kf_t_archive_slots[7];",
    "extern u16 g_kf_player_scale_or_light;",
    "extern s16 g_kf_player_status_dark, g_kf_player_status_paralyze, g_kf_player_status_curse, g_kf_player_status_slow;",
    "extern u32 g_kf_end_ro_table_base_80039b6c, g_kf_end_bss_table_base_80061b6c, g_kf_end_bss_table_base_80089b6c;",
    "extern void *g_kf_end_bss_ptr_8009d76c, *g_kf_end_bss_ptr_8009d770, *g_kf_end_bss_ptr_8009d778;",
    "extern u32 g_kf_end_bss_u32_8009d774, g_kf_end_bss_u32_8009d78c, g_kf_end_bss_u32_8009d798;",
    *(f"extern u16 g_kf_end_bss_u16_8009d7{hx};" for hx in _END_U16_ADDRS),
]) + "\n"
_HDR_FUNCS = "\n".join([
    '#pragma once\n#include "kingsfield_types.h"',
    "s32 kf_game_math_step_linear_clamp(s32 cur_val, s32 target_val, s32 step_delta);",
    "bool kf_game_math_is_angle_cw_halfplane(s32 angle_a, s32 angle_b);",
    "s32 kf_game_math_angle_diff_signed(s32 angle_a, s32 angle_b);",
    "bool kf_game_math_intervals_overlap(s32 pos_a, s32 neg_extent, s32 pos_b, s32 pos_extent);",
    "s32 kf_game_math_lerp_q12(s32 start_val, s32 end_val, s32 t_q12);",
    "u32 kf_game_math_lerp_angle_q12(s32 start_angle, s16 end_angle, s32 t_q12);",
    "void kf_game_math_lerp_pose_s16(s16 *src_pose, s16 *dst_pose, s16 *out_pose, s16 t_q12);",
    "s32 kf_game_cd_bcd_to_int(u32 bcd_byte); u32 kf_game_cd_int_to_bcd(u32 value);",
    "bool kf_game_cd_verify_sector_checksum(s32 *buf, s32 sector_count);",
    "s32 kf_game_t_archive_get_entry_size(u32 archive_slot, u32 entry_idx);",
    "void kf_game_player_clamp_mp_regen(void); void kf_game_player_clamp_hp_regen(void);",
    "s32 kf_game_mc_checksum_payload(u8 *payload);",
    "s32 kf_game_player_scale_gauge(s32 stat_val, s32 divisor);",
    "s32 kf_game_player_eval_combat_curve(s32 base_val, s32 bonus_val, s32 scale_step);",
    "void kf_end_init_str_decoder_state(void);",
]) + "\n"
_C_INC = '#include "kingsfield_types.h"\n#include "kingsfield_globals.h"\n#include "kingsfield_functions.h"\n'


def count_craftsmanship_tells(c_files: list[Path]) -> tuple[int, int]:
    """Return (files_with_tells, total_tell_hits) across readable C sources."""
    tell_files, tell_hits = 0, 0
    for cf in c_files:
        if hits := len(GHIDRA_CRAFT_RE.findall(cf.read_text(encoding="utf-8", errors="replace"))):
            tell_files += 1
            tell_hits += hits
    return tell_files, tell_hits


def setup_logger(name: str, log_dir: Path | None) -> logging.Logger:
    """Create a quiet logger writing to log_dir/<name>.log when log_dir is provided."""
    logger = logging.getLogger(name)
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_dir / f"{name}.log", encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(fh)
    else:
        logger.addHandler(logging.NullHandler())
    return logger


def _dox(sym: str, body: str) -> str:
    return f"/** @symbol {sym} */\n{body}\n"


def _synth_tus() -> dict[str, str]:
    g1 = _C_INC + "".join([
        _dox("kf_game_math_step_linear_clamp",
             "s32 kf_game_math_step_linear_clamp(s32 cur_val, s32 target_val, s32 step_delta) { s32 step = (step_delta < 0) ? -step_delta : step_delta; if (cur_val < target_val) { s32 n = cur_val + step; return (n > target_val) ? target_val : n; } if (cur_val > target_val) { s32 n = cur_val - step; return (n < target_val) ? target_val : n; } return cur_val; }"),
        _dox("kf_game_math_is_angle_cw_halfplane",
             "bool kf_game_math_is_angle_cw_halfplane(s32 angle_a, s32 angle_b) { return ((u32)(angle_a - angle_b) & 0xfffu) < 0x801u; }"),
        _dox("kf_game_math_angle_diff_signed",
             "s32 kf_game_math_angle_diff_signed(s32 angle_a, s32 angle_b) { u32 d = (u32)(angle_b - angle_a) & 0xfffu; return (d > 0x800u) ? (s32)(d - 0x1000u) : (s32)d; }"),
        _dox("kf_game_math_intervals_overlap",
             "bool kf_game_math_intervals_overlap(s32 pos_a, s32 neg_extent, s32 pos_b, s32 pos_extent) { return (pos_b < pos_a) ? (pos_b >= pos_a - neg_extent) : (pos_a >= pos_b - pos_extent); }"),
    ])
    g2 = _C_INC + "".join([
        _dox("kf_game_math_lerp_q12",
             "s32 kf_game_math_lerp_q12(s32 start_val, s32 end_val, s32 t_q12) { return ((end_val - start_val) * t_q12 >> 12) + start_val; }"),
        _dox("kf_game_math_lerp_angle_q12",
             "u32 kf_game_math_lerp_angle_q12(s32 start_angle, s16 end_angle, s32 t_q12) { u32 d = (u32)((s32)end_angle - (s32)(s16)start_angle) & 0xfffu; s32 sd = (d > 0x800u) ? (s32)(d - 0x1000u) : (s32)d; return (u32)(start_angle + ((sd * t_q12) >> 12)) & 0xfffu; }"),
        _dox("kf_game_math_lerp_pose_s16",
             "void kf_game_math_lerp_pose_s16(s16 *src_pose, s16 *dst_pose, s16 *out_pose, s16 t_q12) { for (s32 i = 0; i < 9; ++i) out_pose[i] = (s16)(src_pose[i] + (((s32)dst_pose[i] - (s32)src_pose[i]) * (s32)t_q12 >> 12)); }"),
    ])
    g3 = _C_INC + "".join([
        _dox("kf_game_cd_bcd_to_int", "s32 kf_game_cd_bcd_to_int(u32 bcd_byte) { return (s32)(((bcd_byte & 0xffu) >> 4) * 10u + (bcd_byte & 0xfu)); }"),
        _dox("kf_game_cd_int_to_bcd", "u32 kf_game_cd_int_to_bcd(u32 value) { u32 v = value & 0xffu; return ((v / 10u) << 4) | (v % 10u); }"),
        _dox("kf_game_cd_verify_sector_checksum",
             "bool kf_game_cd_verify_sector_checksum(s32 *buf, s32 sector_count) { u32 acc = 0x12345678u; s32 words = sector_count * 0x200 - 1; for (s32 i = 0; i < words; ++i) acc += (u32)buf[i]; return (s32)acc != buf[words]; }"),
        _dox("kf_game_t_archive_get_entry_size",
             "s32 kf_game_t_archive_get_entry_size(u32 archive_slot, u32 entry_idx) { const u16 *offs = g_kf_t_archive_slots[archive_slot & 0xffffu].sector_offsets; u32 i = entry_idx & 0xffffu; return ((s32)offs[i + 1] - (s32)offs[i]) * 0x800; }"),
    ])
    g4 = _C_INC + "".join([
        _dox("kf_game_player_clamp_mp_regen", "void kf_game_player_clamp_mp_regen(void) { if (g_kf_player_status_dark > 0x40) { g_kf_player_status_dark = 0x40; g_kf_player_status_paralyze = 0; } }"),
        _dox("kf_game_player_clamp_hp_regen", "void kf_game_player_clamp_hp_regen(void) { if (g_kf_player_status_curse > 0x40) { g_kf_player_status_curse = 0x40; g_kf_player_status_slow = 0; } }"),
    ])
    g10 = _C_INC + "".join([
        _dox("kf_game_mc_checksum_payload", "s32 kf_game_mc_checksum_payload(u8 *payload) { s32 s = 0; for (s32 i = 0; i < 0x3c00; ++i) s += (s32)payload[i]; return s; }"),
        _dox("kf_game_player_scale_gauge", "s32 kf_game_player_scale_gauge(s32 stat_val, s32 divisor) { s32 v = (stat_val << 6) / (divisor + 1) + 1; return (v < 5000) ? v : 5000; }"),
        _dox("kf_game_player_eval_combat_curve",
             "s32 kf_game_player_eval_combat_curve(s32 base_val, s32 bonus_val, s32 scale_step) { s32 s = scale_step * 0x10; if (s == 0) return 0; s32 t = ((base_val * (s32)g_kf_player_scale_or_light) >> 8) + bonus_val * 0x10; s32 d = (s > t) ? (s - t) : 0; if (t == 0) t = 0x10; return (d + (s * s) / (t << 1)) / 5; }"),
    ])
    end1 = _C_INC + _dox(
        "kf_end_init_str_decoder_state",
        "void kf_end_init_str_decoder_state(void) { g_kf_end_bss_ptr_8009d76c = &g_kf_end_ro_table_base_80039b6c; g_kf_end_bss_ptr_8009d770 = &g_kf_end_bss_table_base_80061b6c; g_kf_end_bss_u32_8009d774 = 0u; g_kf_end_bss_ptr_8009d778 = &g_kf_end_bss_table_base_80089b6c; g_kf_end_bss_u32_8009d78c = 0u; g_kf_end_bss_u32_8009d798 = 0u; g_kf_end_bss_u16_8009d77c = 0u; g_kf_end_bss_u16_8009d77e = 0u; g_kf_end_bss_u16_8009d780 = 0x140u; g_kf_end_bss_u16_8009d782 = 0xf0u; g_kf_end_bss_u16_8009d784 = 0u; g_kf_end_bss_u16_8009d786 = 0xf0u; g_kf_end_bss_u16_8009d788 = 0x140u; g_kf_end_bss_u16_8009d78a = 0xf0u; g_kf_end_bss_u16_8009d790 = 0u; g_kf_end_bss_u16_8009d792 = 0u; g_kf_end_bss_u16_8009d794 = 0x10u; g_kf_end_bss_u16_8009d796 = 0xf0u; }",
    )
    slus = _C_INC + _dox("kf_slus_crt0_start", "void kf_slus_crt0_start(void) { g_kf_player_scale_or_light = 0x100u; }")
    return {
        "src/boot_slus/slus_boot_dispatcher.c": slus,
        "src/game_core_and_math/game_fixed_math.c": g1 + g2,
        "src/game_cd_and_archives/game_cd_and_t_archives.c": g3,
        "src/game_cd_and_archives/game_save_and_memcard.c": g10,
        "src/game_world_and_entities/game_player_and_combat.c": g4,
        "src/end_credits_and_str/end_credits_and_main.c": end1,
    }


def generate_globals_and_stubs(readable_dir: Path, out_dir: Path, parity_tus: tuple[str, ...]) -> tuple[Path, Path]:
    """Emit host global definitions and stub definitions for Pass 1 and Pass 2 linking."""
    out_dir.mkdir(parents=True, exist_ok=True)
    inc = readable_dir / "include"
    g_txt = re.sub(r"/\*.*?\*/", "", (inc / "kingsfield_globals.h").read_text(encoding="utf-8"), flags=re.S)
    c_txt = (inc / "ghidra_compat.h").read_text(encoding="utf-8")
    m = re.search(r"KF_PS1_COMPAT_EXTS\s*===\s*\*/(.*?)/\*\s*===\s*END KF_PS1_COMPAT_EXTS", c_txt, flags=re.S)
    seen, vars_out = set(), ['#include "kingsfield_types.h"', '#include "kingsfield_globals.h"', ""]
    stubs_out = [
        '#include "kingsfield_types.h"', '#include "kingsfield_globals.h"',
        "typedef struct __jmp_buf_tag __jmp_buf_tag;",
        "void halt_baddata(void) {} int syscall(long c, ...) { (void)c; return 0; }",
        "void trap(int c, ...) { (void)c; } void IME(uint8_t v) { (void)v; }",
        "uint8_t daaOperand(uint8_t a, ...) { return a; } void halt(void) {} void stop(void) {}",
        "char *builtin_strncpy(char *d, const char *s, u32 n) { (void)s; (void)n; return d; }",
    ]
    for ln in (g_txt + "\n" + (m.group(1) if m else "")).splitlines():
        s = ln.strip()
        if not s.startswith("extern ") or not s.endswith(";"):
            continue
        body = re.sub(r"^extern\s+", "", s[:-1].strip()).strip()
        if body.endswith("()"):
            if (fm := re.match(r"^(.+?\b)([A-Za-z_][A-Za-z0-9_]*)\(\)$", body)) and fm.group(2) not in seen:
                seen.add(fm.group(2))
                stubs_out.append(f"{fm.group(1).strip()} {fm.group(2)}(void) {{ return 0; }}")
            continue
        if "," in body:
            for item in re.findall(r"([A-Za-z_][A-Za-z0-9_]*)", body):
                seen.add(item)
            vars_out.append(body + ";")
            continue
        if not (sm := re.search(r"([A-Za-z_][A-Za-z0-9_]*)\s*(?:\[.*\])?$", body)) or sm.group(1) in seen:
            continue
        seen.add(sm.group(1))
        vars_out.append(re.sub(r"\[\s*\]$", "[64]", body) + ";")

    defined_fns, called_fns = set(), set()
    for rel in parity_tus:
        if (fp := readable_dir / rel).is_file():
            txt = fp.read_text(encoding="utf-8", errors="replace")
            defined_fns.update(re.findall(r"^// Function:\s+(\S+)\s+@", txt, re.M))
            defined_fns.update(re.findall(r"^[A-Za-z_][A-Za-z0-9_*\s]*?\b([A-Za-z_][A-Za-z0-9_]*)\s*\([^;{}]*\)\s*\{", txt, re.M))
            called_fns.update(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\b", txt))
    for raw_ln in (inc / "kingsfield_functions.h").read_text(encoding="utf-8").splitlines():
        ln = re.sub(r"/\*.*?\*/", "", raw_ln).strip()
        if not (pm := re.match(r"^(.+?)\s*\b([A-Za-z_][A-Za-z0-9_]*)\s*\((.*)\)\s*;$", ln)):
            continue
        ret_t, fn, params = pm.group(1).strip(), pm.group(2), pm.group(3).strip() or "void"
        if fn not in called_fns or fn in defined_fns or fn in LIBC_SYMS or fn in seen:
            continue
        seen.add(fn)
        stubs_out.append(f"void {fn}({params}) {{}}" if ret_t == "void" else f"{ret_t} {fn}({params}) {{ {ret_t} _rv = {{0}}; return _rv; }}")

    gc, sc = out_dir / "globals_defs.c", out_dir / "host_stubs.c"
    gc.write_text("\n".join(vars_out) + "\n", encoding="utf-8", newline="\n")
    sc.write_text("\n".join(stubs_out) + "\n", encoding="utf-8", newline="\n")
    return gc, sc


def seed_synthetic_corpus(base: Path) -> tuple[Path, Path, Path]:
    """Seed an offline clean-room synthetic corpus with 0 Ghidra tells and 10/10 parity fixtures."""
    standalone, readable, work = base / "standalone", base / "readable", base / "work"
    disc_dir, inc_dir = standalone / "disc" / "files", readable / "include"
    for d in (disc_dir / "CD" / "COM", disc_dir / "OP", inc_dir, work):
        d.mkdir(parents=True, exist_ok=True)
    for rel, sz, pc0, ta, ts in (
        ("SLUS_001.58", 4096, 0x80010128, 0x80010000, 0x800), ("OPEN.EXE", 190464, 0x80013db8, 0x80011000, 0x2e000),
        ("GAME.EXE", 387072, 0x8004a628, 0x80011000, 0x5e000), ("END.EXE", 169984, 0x80011cb4, 0x80011000, 0x29000),
    ):
        buf = bytearray(sz)
        struct.pack_into("<8s8xI4xII", buf, 0, b"PS-X EXE", pc0, ta, ts)
        (disc_dir / rel).write_bytes(bytes(buf))
    (disc_dir / "CD" / "FN.D").write_bytes(b"01 004 045 2\r\n" + b"\x00" * (1188 - 14))
    for name, cnt in (("FDAT.T", 70), ("ITEM.T", 548), ("MO.T", 448), ("RTIM.T", 75), ("RTMD.T", 9), ("TALK.T", 755), ("VAB.T", 331)):
        blob = bytearray((cnt + 1) * 2048)
        struct.pack_into(f"<H{cnt + 1}H", blob, 0, cnt, *(1 + i for i in range(cnt + 1)))
        if name == "FDAT.T":
            struct.pack_into("<I", blob, 2048, 64000)
        elif name == "MO.T":
            struct.pack_into("<5I", blob, 2048, 0x0a64, 4, 0, 0, 0x14)
        elif name == "VAB.T":
            blob[2048:2052] = b"pBAV"
        (disc_dir / "CD" / "COM" / name).write_bytes(bytes(blob))
    op2 = bytearray(32)
    struct.pack_into("<I4xH", op2, 0, 0x80420101, 0x0160)
    (disc_dir / "OP" / "OP2.S").write_bytes(bytes(op2))

    for fn, txt in (("ghidra_compat.h", _HDR_COMPAT), ("kingsfield_types.h", _HDR_TYPES), ("kingsfield_globals.h", _HDR_GLOBALS), ("kingsfield_functions.h", _HDR_FUNCS)):
        (inc_dir / fn).write_text(txt, encoding="utf-8", newline="\n")
    for rel, code in _synth_tus().items():
        fp = readable / rel
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(code, encoding="utf-8", newline="\n")
    return standalone, readable, work
