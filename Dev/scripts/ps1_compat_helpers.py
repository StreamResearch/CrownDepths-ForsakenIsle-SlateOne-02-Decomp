# @module: KingsFieldPS1.Dev.scripts.ps1_compat_helpers
# @purpose: Shared C span scanners, P-code lowering rewriters, SDK deduper, and compat header builder
# @depends-on: re, pathlib, typing
# @exports: MARKER_BEGIN, MARKER_END, UNDEF_DECL_RE, code_spans, map_code, mask_non_code, match_fwd, match_back, split_args, rewrite_subpieces, rewrite_undef_and_structs, rewrite_deref_calls, build_compat_block

from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

MARKER_BEGIN = "/* === BEGIN KF_PS1_COMPAT_EXTS === */"
MARKER_END = "/* === END KF_PS1_COMPAT_EXTS === */"
SUBPIECE_TAG_RE = re.compile(r"\._(\d+)_([1234])_\b")
UNDEF_DECL_RE = re.compile(r"\bundefined1\s+([A-Za-z_][A-Za-z0-9_]*)\s*\[\s*([24])\s*\]\s*;")
DEREF_CALL_START_RE = re.compile(r"\(\*")

PS1_MMIO_16 = (
    "SPU_MAIN_VOL_L SPU_MAIN_VOL_R CURR_MAIN_VOL_L CURR_MAIN_VOL_R CD_VOL_L CD_VOL_R EXT_VOL_L EXT_VOL_R "
    "SPU_CTRL_REG_CPUCNT SPU_STATUS_REG_SPUSTAT SPU_DELAY SOUND_RAM_DATA_TRANSFER_ADDR SOUND_RAM_DATA_TRANSFER_FIFO "
    "SOUND_RAM_DATA_TRANSTER_CTRL SOUND_RAM_IRQ_ADDR SOUND_RAM_REVERB_WORK_ADDR SPU_REVERB_OUT_L SPU_REVERB_OUT_R "
    "VOICE_00_LEFT_RIGHT VOICE_00_ADPCM_SAMPLE_RATE VOICE_00_ADPCM_START_ADDR VOICE_00_ADPCM_REPEAT_ADDR "
    "VOICE_00_ADSR_ATT_DEC_SUS_REL VOICE_00_ADSR_CURR_VOLUME JOY_MCD_DATA JOY_MCD_STAT JOY_MCD_MODE JOY_MCD_CTRL "
    "JOY_MCD_BAUD TMR_DOTCLOCK_VAL TMR_DOTCLOCK_MODE TMR_DOTCLOCK_MAX TMR_HRETRACE_VAL TMR_HRETRACE_MAX "
    "TMR_SYSCLOCK_VAL TMR_SYSCLOCK_MODE TMR_SYSCLOCK_MAX I_STAT I_MASK _I_STAT _I_MASK"
).split()

PS1_MMIO_32 = (
    "CDROM_DELAY CDROM_REG0 CDROM_REG1 CDROM_REG2 CDROM_REG3 COMMON_DELAY DMA_DPCR DMA_DICR "
    "DMA_MDEC_IN_MADR DMA_MDEC_IN_BCR DMA_MDEC_IN_CHCR DMA_MDEC_OUT_MADR DMA_MDEC_OUT_BCR DMA_MDEC_OUT_CHCR "
    "DMA_GPU_MADR DMA_GPU_BCR DMA_GPU_CHCR DMA_CDROM_MADR DMA_CDROM_BCR DMA_CDROM_CHCR "
    "DMA_SPU_MADR DMA_SPU_BCR DMA_SPU_CHCR DMA_OTC_MADR DMA_OTC_BCR DMA_OTC_CHCR "
    "GPU_REG0 GPU_REG1 MDEC_REG0 MDEC_REG1 TMR_HRETRACE_MODE SPU_VOICE_KEY_ON SPU_VOICE_KEY_OFF "
    "SPU_VOICE_CHN_FM_MODE SPU_VOICE_CHN_NOISE_MODE SPU_VOICE_CHN_ON_OFF_STATUS SPU_VOICE_CHN_REVERB_MODE"
).split()

PS1_MISC_U32 = ("Status", "register0x00000074")


def code_spans(text: str) -> list[tuple[int, int, bool]]:
    """Split C text into (start, end, is_code) spans excluding comments and string literals."""
    spans: list[tuple[int, int, bool]] = []
    i, n, cur = 0, len(text), 0
    while i < n:
        ch, nxt = text[i], text[i + 1] if i + 1 < n else ""
        if ch == "/" and nxt in ("/", "*"):
            if i > cur:
                spans.append((cur, i, True))
            j = text.find("\n" if nxt == "/" else "*/", i + 2)
            j = n if j < 0 else (j if nxt == "/" else j + 2)
            spans.append((i, j, False))
            i = cur = j
        elif ch in ('"', "'"):
            if i > cur:
                spans.append((cur, i, True))
            j = i + 1
            while j < n:
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == ch:
                    j += 1
                    break
                j += 1
            spans.append((i, j, False))
            i = cur = j
        else:
            i += 1
    if cur < n:
        spans.append((cur, n, True))
    return spans


def map_code(text: str, fn: Callable[[str], str]) -> str:
    """Apply transform fn exclusively to C code spans outside comments and string literals."""
    return "".join(fn(text[s:e]) if is_c else text[s:e] for s, e, is_c in code_spans(text))


def mask_non_code(text: str) -> str:
    """Replace comments and literals with spaces while preserving character offsets."""
    chars = list(text)
    for s, e, is_c in code_spans(text):
        if not is_c:
            for k in range(s, e):
                if chars[k] != "\n":
                    chars[k] = " "
    return "".join(chars)


def match_fwd(text: str, open_idx: int) -> int:
    """Find matching ')' for text[open_idx] == '('."""
    depth = 0
    for idx in range(open_idx, len(text)):
        depth += 1 if text[idx] == "(" else (-1 if text[idx] == ")" else 0)
        if depth == 0:
            return idx
    return -1


def match_back(text: str, close_idx: int, lo: str, hi: str) -> int:
    """Find matching opening lo for text[close_idx] == hi."""
    depth = 0
    for idx in range(close_idx, -1, -1):
        depth += 1 if text[idx] == hi else (-1 if text[idx] == lo else 0)
        if depth == 0:
            return idx
    return -1


def split_args(arg_text: str) -> list[str]:
    """Split a top-level C argument list respecting nested parentheses and brackets."""
    if not arg_text.strip():
        return []
    args, depth, cur = [], 0, []
    for ch in arg_text:
        depth += 1 if ch in "([" else (-1 if ch in ")]" else 0)
        if ch == "," and depth <= 0:
            args.append("".join(cur).strip())
            cur, depth = [], 0
        else:
            cur.append(ch)
    args.append("".join(cur).strip())
    return args


def rewrite_subpieces(code: str) -> str:
    """Rewrite Ghidra ._off_sz_ subpiece expressions into portable C11 loads/stores."""
    while m := SUBPIECE_TAG_RE.search(code):
        dot_idx, end_idx, off, sz = m.start(), m.end(), int(m.group(1)), int(m.group(2))
        i = dot_idx - 1
        while i >= 0 and code[i].isspace():
            i -= 1
        while i >= 0:
            c = code[i]
            if c.isalnum() or c in "_.":
                i -= 1
            elif c == "]":
                i = match_back(code, i, "[", "]") - 1
            elif c == ")" and i == dot_idx - 1:
                i = match_back(code, i, "(", ")") - 1
            elif c == ">" and i > 0 and code[i - 1] == "-":
                i -= 2
            else:
                break
        start = i + 1
        while start < dot_idx and code[start].isspace():
            start += 1
        expr = code[start:dot_idx].strip()
        if not expr:
            break
        is_arith = expr.startswith("(") and any(op in expr for op in (" + ", " - ", " << ", " >> ", " & ", " | ", "(int)", "(uint"))
        if sz == 3:
            if eq_m := re.match(r"^\s*=([^=][^;]*);", code[end_idx:]):
                repl = f"_gh_set3((uint8_t *)&({expr}) + {off}, (uint32_t)({eq_m.group(1).strip()}));"
                code = code[:start] + repl + code[end_idx + eq_m.end():]
                continue
            repl = f"(((uint32_t){expr}) >> {off * 8})" if is_arith else f"((uint32_t)_gh_get3((const uint8_t *)&({expr}) + {off}))"
        else:
            bits = sz * 8
            repl = f"((uint{bits}_t)(((uint64_t)(uint32_t){expr}) >> {off * 8}))" if is_arith else f"(*((uint{bits}_t *)((uint8_t *)&({expr}) + {off})))"
        code = code[:start] + repl + code[end_idx:]
    return code


def rewrite_undef_and_structs(code: str, stack_arrs: dict[str, int]) -> str:
    """Normalize unaligned stack array assignments, jump-table symbols, and KF struct casts."""
    code = re.sub(
        r"\b([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\(undefined\d*\s*\[\s*([24])\s*\]\)\s*([^;]+);",
        lambda m: f"*(uint{int(m.group(2)) * 8}_t *)(void *)({m.group(1)}) = (uint{int(m.group(2)) * 8}_t)({m.group(3).strip()});",
        code,
    )
    for var, sz in stack_arrs.items():
        bits = sz * 8
        code = re.sub(
            rf"(?<!\*)\b{re.escape(var)}\s*=\s*([^=;][^;]*);",
            lambda m, v=var, b=bits: (
                f"*(uint{b}_t *)(void *)({v}) = *(uint{stack_arrs[m.group(1).strip()] * 8}_t *)(void *)({m.group(1).strip()});"
                if m.group(1).strip() in stack_arrs
                else f"*(uint{b}_t *)(void *)({v}) = (uint{b}_t)({m.group(1).strip()});"
            ),
            code,
        )
    for pat, rep in (
        (r"\bswitchD_([0-9A-Fa-f]+)::switchdataD_([0-9A-Fa-f]+)\b", r"switchD_\1_switchdataD_\2"),
        (r"\b(?:2MBYTE_OBJ_B4|_MBYTE_OBJ_B4)\b", "fn_2MBYTE_OBJ_B4"),
        (r"\$(\d+)\b", r"reg_r\1"),
        (r"\b_([A-Za-z0-9_]*Stack_[0-9A-Fa-f]+)\s*=(?!=)\s*([^;]+);", r"*(uint32_t *)(void *)(\1) = (uint32_t)(\2);"),
        (r"\b_(g_kf_[A-Za-z0-9_]+)\s*=(?!=)\s*([^;]+);", r"*(uint32_t *)&(\1) = (uint32_t)(\2);"),
        (r"\b_(g_kf_[A-Za-z0-9_]+)\b", r"\1"),
        (r"(?<!&)\b(g_kf_player_state|g_kf_scene_control|g_kf_camera_state|g_kf_fdat_load_hdr)\b(?!\s*(?:\.|\[|->))", r"(*(uint32_t *)&\1)"),
        (r"=\s*\(\*\(uint32_t \*\)&CStack_68\.pos\);", "= CStack_68.pos;"),
        (r"\(uint\)CStack_68\.pos\b", "(uint)(*(uint32_t *)&CStack_68.pos)"),
        (r"\((g_kf_(?:end|game|open)_ro_u32_800(?:39a1c|6e9ac|3ea78))\s*-\s*\(int\)puVar6\b", r"((int)\1 - (int)puVar6"),
        (r"\bframe_addr\s*-\s*\((?!s32\)\(uintptr_t\))", "frame_addr - (s32)(uintptr_t)("),
        (r"\(&\s*(g_kf_map_obj_table|g_kf_map_obj_def_table)\s*\)\[", r"((uint8_t *)&\1)["),
        (r"(?<!&)\bg_kf_player_pos_x->", "((VECTOR *)&g_kf_player_pos_x)->"),
    ):
        code = re.sub(pat, rep, code)
    return code


def rewrite_deref_calls(code: str) -> str:
    """Wrap raw (*expr)(...) function-pointer calls in portable (*(code *)(uintptr_t)(...))."""
    out, i = [], 0
    while m := DEREF_CALL_START_RE.search(code, i):
        open_idx, close_idx = m.start(), match_fwd(code, m.start())
        if close_idx < 0:
            break
        k = close_idx + 1
        while k < len(code) and code[k].isspace():
            k += 1
        inner = code[open_idx + 2 : close_idx].strip()
        if k < len(code) and code[k] == "(" and inner and not inner.startswith(("(code", "code ")):
            out.extend((code[i:open_idx], f"(*(code *)(uintptr_t)({inner}))"))
        else:
            out.append(code[i : close_idx + 1])
        i = close_idx + 1
    out.append(code[i:])
    return "".join(out)


def build_compat_block(globals_txt: str, readable_dir: Path) -> str:
    """Build KF_PS1_COMPAT_EXTS compatibility block for ghidra_compat.h."""
    lines = [
        MARKER_BEGIN, "#ifndef KF_PS1_COMPAT_EXTS", "#define KF_PS1_COMPAT_EXTS", "typedef struct __jmp_buf_tag __jmp_buf_tag;",
        "#define SUB84(x, n) ((uint32_t)(((uint64_t)(x)) >> ((n) * 8)))", "#define SUB82(x, n) ((uint16_t)(((uint64_t)(x)) >> ((n) * 8)))",
        "#define SUB81(x, n) ((uint8_t)(((uint64_t)(x)) >> ((n) * 8)))", "#define ZEXT48(x) ((uint64_t)(uint32_t)(x))",
        "#define ZEXT44(x) ((uint32_t)(x))", "#define SEXT48(x) ((int64_t)(int32_t)(x))", "#define ABS(x) ((x) < 0 ? -(x) : (x))",
        "#define setCopReg(c, r, ...) ((void)0)", "#define copFunction(c, fn) ((void)0)",
        "static inline uint32_t _gh_get3(const void *p){const uint8_t*b=(const uint8_t*)p;return b[0]|((uint32_t)b[1]<<8)|((uint32_t)b[2]<<16);}",
        "static inline uint64_t _gh_getN(const void *p,int n){uint64_t v=0;for(int i=0;i<n;i++)v|=((uint64_t)((const uint8_t*)p)[i])<<(i*8);return v;}",
        "#define _gh_get5(p) _gh_getN((p),5)", "#define _gh_get6(p) _gh_getN((p),6)", "#define _gh_get7(p) _gh_getN((p),7)",
        "static inline void _gh_set3(void *p,uint32_t v){uint8_t*b=(uint8_t*)p;b[0]=v;b[1]=v>>8;b[2]=v>>16;}",
        "static inline void _gh_setN(void *p,uint64_t v,int n){for(int i=0;i<n;i++)((uint8_t*)p)[i]=(uint8_t)(v>>(i*8));}",
        "#define _gh_set5(p,v) _gh_setN((p),(v),5)", "#define _gh_set6(p,v) _gh_setN((p),(v),6)", "#define _gh_set7(p,v) _gh_setN((p),(v),7)",
    ]
    seen = set(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\b(?:\[[^\]]*\])?;", globals_txt))
    for syms, fmt in ((PS1_MMIO_16, "extern volatile uint16_t {};"), (PS1_MMIO_32, "extern volatile uint32_t {};"), (PS1_MISC_U32, "extern uint32_t {};")):
        for sym in syms:
            if sym not in seen:
                lines.append(fmt.format(sym))
                seen.add(sym)
    ptr_syms, arr_syms, stack_syms, unk_syms, gte_syms = set(), set(), set(), set(), set()
    for cpath in readable_dir.rglob("*.c"):
        txt = cpath.read_text(encoding="utf-8", errors="replace")
        ptr_syms.update(re.findall(r"\bPTR_[A-Za-z0-9_]+\b", txt))
        arr_syms.update(re.findall(r"\b(?:(?:LAB|SUB)_[A-Za-z0-9_]+(?!\s*:)|switchD_[0-9A-Fa-f]+_switchdataD_[0-9A-Fa-f]+)\b", txt))
        stack_syms.update(re.findall(r"\b(?:stack0x|unique0x)[0-9A-Fa-f]+\b", txt))
        unk_syms.update(re.findall(r"\b_UNK_[0-9A-Fa-f]+\b", txt))
        gte_syms.update(re.findall(r"\b(gte_[A-Za-z0-9_]+)\s*\(", txt))
    for syms, fmt in ((stack_syms, "extern uint32_t {};"), (unk_syms, "extern uint16_t {};"), (ptr_syms, "extern uint8_t *{};"), (arr_syms, "extern uint8_t {}[];"), (gte_syms, "extern uint32_t {}();")):
        for sym in sorted(syms - seen):
            lines.append(fmt.format(sym))
            seen.add(sym)
    lines.extend(["#endif", MARKER_END])
    return "\n".join(lines) + "\n"
