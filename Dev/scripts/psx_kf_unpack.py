# @module: R&D.Dev.tools.psx_kf_unpack
# @purpose: Clean-room FromSoftware PS1 King's Field container (.T, .MO, .TIM, .TMD, VAB, FN.D, STR) unpacker and PNG exporter
# @depends-on: argparse, json, re, struct, unicodedata, zlib, pathlib
# @exports: parse_and_export_tim, decode_fn_d, unpack_t_archive, unpack_op_assets, unpack_all, main

from __future__ import annotations

import argparse
import json
import re
import struct
import unicodedata
import zlib
from pathlib import Path
from typing import Any


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(tag + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)


def _write_rgba_png(out_png: Path, width: int, height: int, rgba: bytes) -> None:
    if width <= 0 or height <= 0 or len(rgba) < width * height * 4:
        return
    stride = width * 4
    raw = b"".join(b"\x00" + rgba[y * stride : (y + 1) * stride] for y in range(height))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IDAT", zlib.compress(raw, 6)) + _png_chunk(b"IEND", b"")
    out_png.parent.mkdir(parents=True, exist_ok=True)
    out_png.write_bytes(png)


def _abgr1555_to_rgba(c: int) -> tuple[int, int, int, int]:
    r = (c & 0x1F) << 3
    g = ((c >> 5) & 0x1F) << 3
    b = ((c >> 10) & 0x1F) << 3
    a = 0 if c == 0 else 255
    return (r | (r >> 5), g | (g >> 5), b | (b >> 5), a)


def parse_tim_info(blob: bytes, offset: int = 0) -> dict[str, Any] | None:
    if offset + 20 > len(blob):
        return None
    magic, flags = struct.unpack_from("<II", blob, offset)
    if magic != 0x00000010 or (flags & ~0xF) != 0:
        return None
    pmode = flags & 0x7
    if pmode not in (0, 1, 2, 3):
        return None
    has_clut = bool(flags & 0x8)
    pos = offset + 8
    clut_meta: dict[str, Any] | None = None
    palette: list[tuple[int, int, int, int]] = []
    if has_clut:
        if pos + 12 > len(blob):
            return None
        clut_bnum, cx, cy, cw, ch = struct.unpack_from("<IHHHH", blob, pos)
        if clut_bnum < 12 or pos + clut_bnum > len(blob) or cw == 0 or ch == 0:
            return None
        clut_meta = {"bytes": clut_bnum, "vram_x": cx, "vram_y": cy, "w": cw, "h": ch}
        pal_raw = blob[pos + 12 : pos + clut_bnum]
        palette = [_abgr1555_to_rgba(struct.unpack_from("<H", pal_raw, i)[0]) for i in range(0, min(len(pal_raw), cw * 2), 2)]
        pos += clut_bnum
    if pos + 12 > len(blob):
        return None
    px_bnum, px, py, pw, ph = struct.unpack_from("<IHHHH", blob, pos)
    if px_bnum < 12 or pos + px_bnum > len(blob) or pw == 0 or ph == 0 or ph > 2048:
        return None
    width = {0: pw * 4, 1: pw * 2, 2: pw, 3: (pw * 2) // 3}[pmode]
    if width <= 0 or width > 2048:
        return None
    return {
        "offset": offset, "pmode": pmode, "bpp": {0: 4, 1: 8, 2: 16, 3: 24}[pmode],
        "has_clut": has_clut, "clut": clut_meta, "vram_x": px, "vram_y": py,
        "vram_w": pw, "width": width, "height": ph, "total_bytes": (pos + px_bnum) - offset,
        "px_data_offset": pos + 12, "px_data_bytes": px_bnum - 12, "palette": palette,
    }


def parse_and_export_tim(blob: bytes, out_png: Path, offset: int = 0) -> dict[str, Any] | None:
    info = parse_tim_info(blob, offset=offset)
    if not info:
        return None
    w, h, pmode = info["width"], info["height"], info["pmode"]
    px_bytes = blob[info["px_data_offset"] : info["px_data_offset"] + info["px_data_bytes"]]
    pal: list[tuple[int, int, int, int]] = info.pop("palette")
    rgba = bytearray(w * h * 4)
    if pmode == 0:
        row_bytes = info["vram_w"] * 2
        for y in range(h):
            row = px_bytes[y * row_bytes : (y + 1) * row_bytes]
            for x in range(min(w, len(row) * 2)):
                b = row[x >> 1]
                idx = (b & 0xF) if (x & 1) == 0 else (b >> 4)
                c = pal[idx] if idx < len(pal) else (idx * 17, idx * 17, idx * 17, 255)
                rgba[(y * w + x) * 4 : (y * w + x + 1) * 4] = bytes(c)
    elif pmode == 1:
        row_bytes = info["vram_w"] * 2
        for y in range(h):
            row = px_bytes[y * row_bytes : (y + 1) * row_bytes]
            for x in range(min(w, len(row))):
                idx = row[x]
                c = pal[idx] if idx < len(pal) else (idx, idx, idx, 255)
                rgba[(y * w + x) * 4 : (y * w + x + 1) * 4] = bytes(c)
    elif pmode == 2:
        for i in range(min(w * h, len(px_bytes) // 2)):
            c = _abgr1555_to_rgba(struct.unpack_from("<H", px_bytes, i * 2)[0])
            rgba[i * 4 : (i + 1) * 4] = bytes(c)
    elif pmode == 3:
        for i in range(min(w * h, len(px_bytes) // 3)):
            r, g, b = px_bytes[i * 3 : i * 3 + 3]
            rgba[i * 4 : (i + 1) * 4] = bytes((r, g, b, 255))
    _write_rgba_png(out_png, w, h, bytes(rgba))
    info["png"] = str(out_png)
    return info


def decode_fn_d(fn_d_path: Path, assets_dir: Path) -> dict[str, Any]:
    raw = fn_d_path.read_bytes()
    decoded = raw.decode("cp932", errors="replace")
    lines = [ln.rstrip("\r\n") for ln in decoded.splitlines() if ln.strip()]
    rows: list[dict[str, Any]] = []
    for ln in lines[2:]:
        m = re.match(r"^\s*(\d+)\s+(\d+)\s+(.*)$", ln)
        if m:
            raw_name = m.group(3).strip()
            rows.append({"id": int(m.group(1)), "category": int(m.group(2)), "raw_jp": raw_name, "name_jp": unicodedata.normalize("NFKC", raw_name)})
    out_json = assets_dir / "FN_D_items.json"
    out_md = assets_dir / "FN_D_items.md"
    out_json.write_text(json.dumps({"header": lines[:2], "count": len(rows), "entries": rows}, indent=2, ensure_ascii=False), encoding="utf-8")
    md = ["# `/CD/FN.D` Decoded Item & Key Table", "", f"- **Header:** `{' | '.join(lines[:2])}`", f"- **Entries:** `{len(rows)}`", "", "| ID | Cat | Half-Width CP932 | Normalized JP |", "| :---: | :---: | :--- | :--- |"]
    for r in rows:
        md.append(f"| `{r['id']:03d}` | `{r['category']:02d}` | `{r['raw_jp']}` | `{r['name_jp']}` |")
    out_md.write_text("\n".join(md) + "\n", encoding="utf-8")
    return {"count": len(rows), "json": str(out_json), "md": str(out_md)}


def _parse_tmd_summary(blob: bytes, offset: int = 0) -> dict[str, Any] | None:
    if offset + 12 > len(blob):
        return None
    ver, flags, nobj = struct.unpack_from("<III", blob, offset)
    if ver != 0x41 or flags not in (0, 1) or nobj == 0 or nobj > 256 or offset + 12 + nobj * 28 > len(blob):
        return None
    objs = []
    for i in range(min(nobj, 8)):
        _, n_vert, _, n_norm, _, n_prim, scale = struct.unpack_from("<IIIIIIi", blob, offset + 12 + i * 28)
        objs.append({"verts": n_vert, "norms": n_norm, "prims": n_prim, "scale": scale})
    return {"nobj": nobj, "flags": flags, "objects_preview": objs, "total_verts": sum(o["verts"] for o in objs), "total_prims": sum(o["prims"] for o in objs)}


def _scan_embedded_tims(chunk: bytes, out_dir: Path, stem: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    pos = 0
    while len(found) < 16:
        idx = chunk.find(b"\x10\x00\x00\x00", pos)
        if idx < 0:
            break
        if idx % 4 == 0:
            tinfo = parse_tim_info(chunk, offset=idx)
            if tinfo and tinfo["width"] >= 8 and tinfo["height"] >= 8:
                png_path = out_dir / f"{stem}_subtim_{len(found):02d}_0x{idx:x}.png"
                exp = parse_and_export_tim(chunk, png_path, offset=idx)
                if exp:
                    found.append(exp)
                    pos = idx + tinfo["total_bytes"]
                    continue
        pos = idx + 4
    return found


def _classify_chunk(arch_name: str, idx: int, chunk: bytes, out_dir: Path, expect_vb: bool) -> tuple[str, dict[str, Any], bool]:
    stem = f"entry_{idx:04d}"
    if expect_vb:
        return "vb", {"role": "VAB_body_adpcm", "bytes": len(chunk)}, False
    if chunk[:4] == b"pBAV" and len(chunk) >= 32:
        sys_id, ver, vab_id, form, wf_sz, progs, tones, vags = struct.unpack_from("<IIIIIIHH", chunk, 4)[:8] if len(chunk) >= 36 else (0,)*8
        vh = struct.unpack_from("<IIIIIIHHH", chunk, 4)
        return "vh", {"vab_id": vh[2], "waveform_bytes": vh[4], "programs": vh[5], "tones": vh[6], "vags": vh[7]}, True
    if chunk[:4] == b"pQES" and len(chunk) >= 16:
        ver, res, tempo = struct.unpack_from(">IHI", chunk, 4)
        return "seq", {"version": ver, "resolution": res, "tempo": tempo & 0xFFFFFF}, False
    tim = parse_and_export_tim(chunk, out_dir / f"{stem}.png")
    if tim:
        return "tim", tim, False
    tmd = _parse_tmd_summary(chunk)
    if tmd:
        return "tmd", tmd, False
    if arch_name == "MO.T" and len(chunk) >= 16:
        total_sz, count, off0 = struct.unpack_from("<III", chunk, 0)
        if total_sz <= len(chunk) and count < 256 and 12 <= off0 < len(chunk):
            # Locate first embedded TMD header within MO container
            tmd_off = chunk.find(b"\x41\x00\x00\x00")
            base_tmd = _parse_tmd_summary(chunk, tmd_off) if tmd_off >= 0 else None
            return "mo", {"declared_size": total_sz, "header_count": count, "first_off": hex(off0), "tmd_offset": hex(tmd_off) if tmd_off >= 0 else None, "base_tmd": base_tmd}, False
    if arch_name == "RTIM.T" and len(chunk) >= 12:
        w, h, _ = struct.unpack_from("<HHI", chunk, 0)
        return "rtim", {"w_words": w, "h_lines": h, "head16": chunk[:16].hex()}, False
    if arch_name == "RTMD.T" and len(chunk) >= 16:
        words = struct.unpack_from("<4I", chunk, 0)
        return "rtmd", {"head_words": [hex(x) for x in words]}, False
    if arch_name == "FDAT.T" and len(chunk) >= 16:
        words = struct.unpack_from("<4I", chunk, 0)
        return "fdat", {"head_words": [hex(x) for x in words]}, False
    meta: dict[str, Any] = {"head16": chunk[:16].hex()}
    if arch_name in ("TALK.T", "ITEM.T"):
        sub_tims = _scan_embedded_tims(chunk, out_dir, stem)
        if sub_tims:
            meta["embedded_tims"] = sub_tims
        ascii_hits = [m.group(0).decode("ascii", "replace") for m in re.finditer(rb"[A-Za-z0-9 ,.!?'\":;\-]{6,}", chunk)][:6]
        if ascii_hits:
            meta["text_samples"] = ascii_hits
    return "bin", meta, False


def unpack_t_archive(t_path: Path, assets_dir: Path) -> dict[str, Any]:
    raw = t_path.read_bytes()
    n = struct.unpack_from("<H", raw, 0)[0]
    offs = struct.unpack_from(f"<{n + 1}H", raw, 2)
    out_dir = assets_dir / t_path.name
    out_dir.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, Any]] = []
    counts_by_ext: dict[str, int] = {}
    expect_vb = False
    for idx in range(n):
        s0, s1 = offs[idx], offs[idx + 1]
        if s1 <= s0:
            continue
        chunk = raw[s0 * 2048 : s1 * 2048]
        ext, meta, next_vb = _classify_chunk(t_path.name, idx, chunk, out_dir, expect_vb)
        expect_vb = next_vb
        fpath = out_dir / f"entry_{idx:04d}.{ext}"
        fpath.write_bytes(chunk)
        counts_by_ext[ext] = counts_by_ext.get(ext, 0) + 1
        entries.append({"index": idx, "sector_start": s0, "sectors": s1 - s0, "bytes": len(chunk), "ext": ext, "file": fpath.name, "meta": meta})
    manifest = {"archive": t_path.name, "total_slots": n, "non_empty_entries": len(entries), "total_bytes": len(raw), "formats": counts_by_ext, "entries": entries}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {"archive": t_path.name, "total_slots": n, "non_empty": len(entries), "formats": counts_by_ext, "manifest": str(out_dir / "manifest.json")}


def unpack_op_assets(disc_files_dir: Path, assets_dir: Path) -> dict[str, Any]:
    op_dir = disc_files_dir / "OP"
    tim_out = assets_dir / "OP_TIM"
    tim_out.mkdir(parents=True, exist_ok=True)
    tim_results: list[dict[str, Any]] = []
    for name in ("OP.D", "OPU.D"):
        p = op_dir / name
        if p.is_file():
            blob = p.read_bytes()
            exp = parse_and_export_tim(blob, tim_out / f"{p.stem}.png")
            if exp:
                exp["source"] = p.name
                tim_results.append(exp)
    (tim_out / "manifest.json").write_text(json.dumps(tim_results, indent=2), encoding="utf-8")
    str_results: list[dict[str, Any]] = []
    for p in sorted(op_dir.glob("*.S")):
        head = p.read_bytes()[:64]
        off = head.find(b"\x60\x01\x01\x80")
        if off >= 0 and off + 20 <= len(head):
            magic, chunk_no, chunks_per_frame, frame_num, sector_bytes, w, h = struct.unpack_from("<IHHIIHH", head, off)
            str_results.append({"file": p.name, "bytes": p.stat().st_size, "sectors_2336": p.stat().st_size // 2336, "str_offset": off, "magic": hex(magic), "chunks_per_frame": chunks_per_frame, "width": w, "height": h})
        else:
            str_results.append({"file": p.name, "bytes": p.stat().st_size, "sectors_2336": p.stat().st_size // 2336, "magic": "unknown"})
    str_manifest = assets_dir / "OP_STR_manifest.json"
    str_manifest.write_text(json.dumps(str_results, indent=2), encoding="utf-8")
    return {"op_tims": tim_results, "op_streams": str_results, "str_manifest": str(str_manifest)}


def unpack_all(disc_files_dir: Path, assets_dir: Path) -> dict[str, Any]:
    assets_dir.mkdir(parents=True, exist_ok=True)
    summary: dict[str, Any] = {"fn_d": None, "archives": [], "op": None}
    fn_d = disc_files_dir / "CD" / "FN.D"
    if fn_d.is_file():
        summary["fn_d"] = decode_fn_d(fn_d, assets_dir)
    com_dir = disc_files_dir / "CD" / "COM"
    if com_dir.is_dir():
        for tfile in sorted(com_dir.glob("*.T")):
            summary["archives"].append(unpack_t_archive(tfile, assets_dir))
    if (disc_files_dir / "OP").is_dir():
        summary["op"] = unpack_op_assets(disc_files_dir, assets_dir)
    (assets_dir / "assets_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Unpack FromSoftware King's Field (PS1) .T containers, FN.D, TIM, TMD, MO, VAB, and OP assets.")
    parser.add_argument("disc_files", type=Path, help="Path to dumpsxiso extracted disc/files directory.")
    parser.add_argument("--out-dir", type=Path, required=True, help="Output assets directory.")
    args = parser.parse_args(argv)
    res = unpack_all(args.disc_files, args.out_dir)
    print(f"Unpacked {len(res['archives'])} .T archives into {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
