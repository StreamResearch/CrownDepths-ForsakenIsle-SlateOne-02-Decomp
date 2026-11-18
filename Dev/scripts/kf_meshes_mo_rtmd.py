# @module: CrownDepths.Dev.scripts.kf_meshes_mo_rtmd
# @purpose: Clean-room MO.T morphs, RTMD.T multi-object TMD banks, RTIM.T VRAM streams, and TIM/PNG exporter
# @depends-on: argparse, json, struct, sys, tempfile, zlib, pathlib, kf_t_archives
# @exports: parse_tim_info, parse_and_export_tim, scan_tim_entries, parse_tmd_header, parse_mo_entry, parse_rtim_stream, build_synthetic_mesh_corpus, run_parser, main

from __future__ import annotations

import argparse
import json
import struct
import sys
import tempfile
import zlib
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from kf_t_archives import (  # noqa: E402
    assert_safe_out_dir,
    build_synthetic_t_archive,
    iter_t_entries,
    resolve_disc_files_dir,
    utc_now_iso,
    verify_sector_checksum,
    write_json_log,
)


def _abgr1555_to_rgba(c: int) -> tuple[int, int, int, int]:
    r, g, b = (c & 0x1F) << 3, ((c >> 5) & 0x1F) << 3, ((c >> 10) & 0x1F) << 3
    return (r | (r >> 5), g | (g >> 5), b | (b >> 5), 0 if c == 0 else 255)


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def _write_rgba_png(out_png: Path, width: int, height: int, rgba: bytes) -> None:
    if width <= 0 or height <= 0 or len(rgba) < width * height * 4:
        return
    stride = width * 4
    raw = b"".join(b"\x00" + rgba[y * stride : (y + 1) * stride] for y in range(height))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IDAT", zlib.compress(raw, 6)) + _png_chunk(b"IEND", b"")
    out_png.parent.mkdir(parents=True, exist_ok=True)
    out_png.write_bytes(png)


def parse_tim_info(blob: bytes, offset: int = 0) -> dict[str, Any] | None:
    """Parse a PS1 .TIM header, optional CLUT block, and pixel block dimensions."""
    if offset + 20 > len(blob):
        return None
    magic, flags = struct.unpack_from("<II", blob, offset)
    if magic != 0x10 or (flags & ~0xF) != 0 or (flags & 0x7) not in (0, 1, 2, 3):
        return None
    pmode, has_clut, pos = flags & 0x7, bool(flags & 0x8), offset + 8
    clut_meta, palette = None, []
    if has_clut:
        if pos + 12 > len(blob):
            return None
        cb, cx, cy, cw, ch = struct.unpack_from("<IHHHH", blob, pos)
        if cb < 12 or pos + cb > len(blob) or cw == 0 or ch == 0:
            return None
        clut_meta = {"bytes": cb, "vram_x": cx, "vram_y": cy, "w": cw, "h": ch}
        pal_raw = blob[pos + 12 : pos + cb]
        palette = [_abgr1555_to_rgba(struct.unpack_from("<H", pal_raw, i)[0]) for i in range(0, min(len(pal_raw), cw * 2), 2)]
        pos += cb
    if pos + 12 > len(blob):
        return None
    pb, px, py, pw, ph = struct.unpack_from("<IHHHH", blob, pos)
    if pb < 12 or pos + pb > len(blob) or pw == 0 or ph == 0 or ph > 2048:
        return None
    width = {0: pw * 4, 1: pw * 2, 2: pw, 3: (pw * 2) // 3}[pmode]
    if width <= 0 or width > 2048:
        return None
    return {"offset": offset, "pmode": pmode, "bpp": {0: 4, 1: 8, 2: 16, 3: 24}[pmode], "has_clut": has_clut, "clut": clut_meta, "vram_x": px, "vram_y": py, "vram_w": pw, "width": width, "height": ph, "total_bytes": (pos + pb) - offset, "px_data_offset": pos + 12, "px_data_bytes": pb - 12, "palette": palette}


def parse_and_export_tim(blob: bytes, out_png: Path, offset: int = 0) -> dict[str, Any] | None:
    info = parse_tim_info(blob, offset=offset)
    if not info:
        return None
    w, h, pmode = info["width"], info["height"], info["pmode"]
    px_bytes = blob[info["px_data_offset"] : info["px_data_offset"] + info["px_data_bytes"]]
    pal = info.pop("palette")
    rgba = bytearray(w * h * 4)
    row_bytes = info["vram_w"] * 2
    if pmode in (0, 1):
        for y in range(h):
            row = px_bytes[y * row_bytes : (y + 1) * row_bytes]
            for x in range(w if pmode == 1 else min(w, len(row) * 2)):
                if pmode == 0:
                    idx = (row[x >> 1] & 0xF) if (x & 1) == 0 else (row[x >> 1] >> 4)
                    c = pal[idx] if idx < len(pal) else (idx * 17, idx * 17, idx * 17, 255)
                else:
                    idx = row[x] if x < len(row) else 0
                    c = pal[idx] if idx < len(pal) else (idx, idx, idx, 255)
                rgba[(y * w + x) * 4 : (y * w + x + 1) * 4] = bytes(c)
    elif pmode == 2:
        for i in range(min(w * h, len(px_bytes) // 2)):
            rgba[i * 4 : (i + 1) * 4] = bytes(_abgr1555_to_rgba(struct.unpack_from("<H", px_bytes, i * 2)[0]))
    else:
        for i in range(min(w * h, len(px_bytes) // 3)):
            rgba[i * 4 : (i + 1) * 4] = px_bytes[i * 3 : i * 3 + 3] + b"\xff"
    _write_rgba_png(out_png, w, h, bytes(rgba))
    info["png"] = str(out_png)
    return info


def scan_tim_entries(chunk: bytes, out_dir: Path | None, stem: str, limit: int = 16) -> list[dict[str, Any]]:
    found, pos = [], 0
    while len(found) < limit and (idx := chunk.find(b"\x10\x00\x00\x00", pos)) >= 0:
        if idx % 4 == 0 and (tinfo := parse_tim_info(chunk, offset=idx)) and tinfo["width"] >= 4 and tinfo["height"] >= 4:
            if out_dir is not None and (exp := parse_and_export_tim(chunk, out_dir / f"{stem}_subtim_{len(found):02d}_0x{idx:x}.png", offset=idx)):
                found.append(exp)
            else:
                tinfo.pop("palette", None)
                found.append(tinfo)
            pos = idx + tinfo["total_bytes"]
            continue
        pos = idx + 4
    return found


def parse_tmd_header(blob: bytes, offset: int = 0, allow_rtmd: bool = False) -> dict[str, Any] | None:
    """Parse standard PS1 TMD (version=0x41) or RTMD runtime table (version=0, bank_tag in {16,18})."""
    if offset + 12 > len(blob):
        return None
    ver, flags, nobj = struct.unpack_from("<III", blob, offset)
    is_std = ver == 0x41 and flags in (0, 1)
    is_rtmd = allow_rtmd and ver == 0 and flags in (16, 18)
    if not (is_std or is_rtmd) or nobj == 0 or nobj > 512 or offset + 12 + nobj * 28 > len(blob):
        return None
    objs = []
    tot_v = tot_n = tot_p = 0
    for i in range(nobj):
        vtop, nv, ntop, nn, ptop, np, scale = struct.unpack_from("<IIIIIIi", blob, offset + 12 + i * 28)
        tot_v, tot_n, tot_p = tot_v + nv, tot_n + nn, tot_p + np
        if i < 8:
            objs.append({"vert_top": f"0x{vtop:x}", "verts": nv, "norm_top": f"0x{ntop:x}", "norms": nn, "prim_top": f"0x{ptop:x}", "prims": np, "scale": scale})
    return {"kind": "rtmd" if is_rtmd else "tmd", "version": ver, "flags": flags, "nobj": nobj, "total_verts": tot_v, "total_norms": tot_n, "total_prims": tot_p, "objects_preview": objs}


def parse_mo_entry(blob: bytes) -> dict[str, Any] | None:
    """Parse KfMoHeader animated morph container (0x14) or static 0-anim TMD wrapper (tmd_offset=0x0c)."""
    if len(blob) < 20:
        return None
    total_sz, anim_cnt, tmd_off, kf_off, anim_off = struct.unpack_from("<5I", blob, 0)
    if anim_cnt == 0 and tmd_off == 12 and blob[12:16] == b"\x41\x00\x00\x00":
        return {"variant": "static_mo_tmd", "declared_size": total_sz, "anim_count": 0, "tmd_offset": "0x0c", "base_tmd": parse_tmd_header(blob, 12)}
    if anim_off == 0x14 and 0 < anim_cnt < 256 and 12 <= tmd_off < len(blob):
        return {"variant": "animated_mo", "declared_size": total_sz, "anim_count": anim_cnt, "tmd_offset": f"0x{tmd_off:x}", "keyframe_table_offset": f"0x{kf_off:x}", "anim_table_offset": f"0x{anim_off:x}", "base_tmd": parse_tmd_header(blob, tmd_off)}
    return None


def parse_rtim_stream(blob: bytes, max_blocks: int = 512) -> dict[str, Any]:
    """Parse sequential KfRtimHeader (src_rect + dst_rect + 16bpp pixel data) blocks."""
    blocks, pos = [], 0
    while len(blocks) < max_blocks and pos + 16 <= len(blob):
        sx, sy, sw, sh, dx, dy, dw, dh = struct.unpack_from("<8h", blob, pos)
        if sx == -1 or sw <= 0 or sh <= 0 or dw <= 0 or dh <= 0 or dw > 1024 or dh > 512:
            break
        px_bytes = dw * dh * 2
        if pos + 16 + px_bytes > len(blob):
            break
        if len(blocks) < 16:
            blocks.append({"offset": f"0x{pos:05x}", "src_rect": [sx, sy, sw, sh], "dst_rect": [dx, dy, dw, dh], "pixel_bytes": px_bytes})
        pos += 16 + px_bytes
    return {"block_count": len(blocks) if pos == 0 or len(blocks) < 16 else _count_rtim_blocks(blob, max_blocks), "parsed_bytes": pos, "blocks_preview": blocks}


def _count_rtim_blocks(blob: bytes, max_blocks: int) -> int:
    cnt, pos = 0, 0
    while cnt < max_blocks and pos + 16 <= len(blob):
        sx, _sy, sw, sh, _dx, _dy, dw, dh = struct.unpack_from("<8h", blob, pos)
        if sx == -1 or sw <= 0 or sh <= 0 or dw <= 0 or dh <= 0 or dw > 1024 or dh > 512 or pos + 16 + dw * dh * 2 > len(blob):
            break
        pos += 16 + dw * dh * 2
        cnt += 1
    return cnt


def build_synthetic_mesh_corpus() -> tuple[bytes, bytes, bytes]:
    tmd0 = struct.pack("<3I7I", 0x41, 0, 1, 28, 3, 52, 1, 60, 1, 0) + b"\x00" * 64
    mo_anim = struct.pack("<5I", 128, 2, 0x20, 0x1C, 0x14) + b"\x00" * 12 + tmd0
    mo_static = struct.pack("<3I", len(tmd0) + 12, 0, 12) + tmd0
    mo_t = build_synthetic_t_archive({0: mo_anim, 9: mo_static}, total_slots=10)
    rtmd_body = struct.pack("<3I2I5I", 0, 18, 1, 0x1A80, 4, 0x1AA0, 2, 0x1A40, 2, 0) + b"\x00" * 0x1B00
    rtmd_t = build_synthetic_t_archive({0: rtmd_body}, total_slots=2)
    rtim_blk = struct.pack("<8h", 448, 510, 16, 1, 448, 510, 16, 1) + b"\x00" * 32
    rtim_t = build_synthetic_t_archive({0: rtim_blk * 2}, total_slots=2, stamp_checksum=False)
    return mo_t, rtmd_t, rtim_t


def _find_mesh_files(data_dir: Path | None) -> tuple[Path | None, Path | None, Path | None]:
    disc_dir, _ = resolve_disc_files_dir(data_dir)
    if disc_dir is None:
        return None, None, None
    cands = [disc_dir / "CD" / "COM", disc_dir]
    for base in cands:
        mo, rtmd, rtim = base / "MO.T", base / "RTMD.T", base / "RTIM.T"
        if mo.is_file() or rtmd.is_file() or rtim.is_file():
            return (mo if mo.is_file() else None), (rtmd if rtmd.is_file() else None), (rtim if rtim.is_file() else None)
    return None, None, None


def run_parser(data_dir: Path | None, out_dir: Path | None, log_dir: Path | None, offline_synthetic: bool) -> tuple[int, dict[str, Any]]:
    """Analyze MO.T, RTMD.T, and RTIM.T containers."""
    work_dir = (out_dir or (data_dir / "meshes_parsed" if data_dir is not None else (Path(tempfile.gettempdir()) / "kf_synthetic" / "meshes" if offline_synthetic else REPO_ROOT / "Corpus" / "work" / "meshes"))).resolve()
    now_utc = utc_now_iso()
    if not offline_synthetic:
        mo_p, rtmd_p, rtim_p = _find_mesh_files(data_dir)
        if not any((mo_p, rtmd_p, rtim_p)):
            err = {"status": "MISSING_CORPUS_MEDIA", "errorCode": "MISSING_CORPUS_MEDIA", "parser": "kf_meshes_mo_rtmd", "dataDir": str(data_dir or work_dir), "required": ["CD/COM/MO.T", "CD/COM/RTMD.T", "CD/COM/RTIM.T"], "generatedAtUtc": now_utc}
            write_json_log(log_dir, "kf_meshes_mo_rtmd", err)
            return 2, err
        mo_raw, rtmd_raw, rtim_raw = (mo_p.read_bytes() if mo_p else b""), (rtmd_p.read_bytes() if rtmd_p else b""), (rtim_p.read_bytes() if rtim_p else b"")
    else:
        mo_raw, rtmd_raw, rtim_raw = build_synthetic_mesh_corpus()
    mo_res = [{"index": i, "bytes": len(c), "checksum_ok": verify_sector_checksum(c)["valid"], **(parse_mo_entry(c) or {})} for i, _, _, c in iter_t_entries(mo_raw)] if mo_raw else []
    rtmd_res = [{"index": i, "bytes": len(c), "checksum_ok": verify_sector_checksum(c)["valid"], **(parse_tmd_header(c, 0, allow_rtmd=True) or {})} for i, _, _, c in iter_t_entries(rtmd_raw)] if rtmd_raw else []
    rtim_res = [{"index": i, "bytes": len(c), **parse_rtim_stream(c)} for i, _, _, c in iter_t_entries(rtim_raw)] if rtim_raw else []
    assert_safe_out_dir(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    out_file = work_dir / "meshes_report.json"
    out_file.write_text(json.dumps({"status": "OK", "mode": "offline-synthetic" if offline_synthetic else "corpus-media", "generatedAtUtc": now_utc, "mo_count": len(mo_res), "rtmd_count": len(rtmd_res), "rtim_count": len(rtim_res), "mo_entries": mo_res, "rtmd_entries": rtmd_res, "rtim_entries": rtim_res}, indent=2) + "\n", encoding="utf-8")
    summary = {"status": "OK", "mode": "offline-synthetic" if offline_synthetic else "corpus-media", "mo_count": len(mo_res), "rtmd_count": len(rtmd_res), "rtim_count": len(rtim_res), "output": str(out_file)}
    write_json_log(log_dir, "kf_meshes_mo_rtmd", summary)
    return 0, summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Parse SLUS-00158 MO.T, RTMD.T, and RTIM.T mesh/texture containers.")
    parser.add_argument("--data-dir", type=Path, default=None, help="Input directory containing COM/{MO,RTMD,RTIM}.T.")
    parser.add_argument("--out-dir", type=Path, default=None, help="Output report directory.")
    parser.add_argument("--log-dir", type=Path, default=None, help="Optional JSON log directory.")
    parser.add_argument("--offline-synthetic", action="store_true", help="Run with synthetic containers (0 retail files).")
    args = parser.parse_args(argv)
    code, payload = run_parser(args.data_dir, args.out_dir, args.log_dir, args.offline_synthetic)
    print(json.dumps(payload, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
