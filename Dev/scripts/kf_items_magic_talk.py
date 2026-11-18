# @module: CrownDepths.Dev.scripts.kf_items_magic_talk
# @purpose: Clean-room ITEM.T, TALK.T dialogue cards, KfItemDef[64], and KfMagicDef[18] parser
# @depends-on: argparse, json, struct, sys, tempfile, pathlib, kf_t_archives, kf_meshes_mo_rtmd, kf_world_fdat
# @exports: decode_item_defs, decode_magic_defs, parse_item_t, parse_talk_t, build_synthetic_item_talk, run_parser, main

from __future__ import annotations

import argparse
import json
import struct
import sys
import tempfile
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from kf_meshes_mo_rtmd import parse_and_export_tim, parse_tim_info, parse_tmd_header, scan_tim_entries  # noqa: E402
from kf_t_archives import (  # noqa: E402
    assert_safe_out_dir,
    build_synthetic_t_archive,
    iter_t_entries,
    resolve_disc_files_dir,
    utc_now_iso,
    verify_sector_checksum,
    write_json_log,
)
from kf_world_fdat import parse_fdat_sections  # noqa: E402


def decode_item_defs(sec2: bytes) -> list[dict[str, Any]]:
    """Decode FDAT[48] section 2 KfItemDef[64] (stride 0x20)."""
    items = []
    for idx in range(len(sec2) // 32):
        cat, eq_slot, pdef, mdef, sl, ch, st, fi, ea, wi, wa, li, flags, price, sell = struct.unpack_from("<2B10hH2I", sec2, idx * 32)
        items.append({"item_id": idx, "category": cat, "equip_slot": eq_slot, "pdef_bonus": pdef, "mdef_bonus": mdef, "resists": {"slash": sl, "chop": ch, "stab": st, "fire": fi, "earth": ea, "wind": wi, "water": wa, "light": li}, "flags": f"0x{flags:04x}", "price": price, "sell_value": sell})
    return items


def decode_magic_defs(sec1: bytes) -> dict[str, Any]:
    """Decode FDAT[48] section 1 KfMagicDef[18] (stride 0x44) plus 8-byte trailer."""
    magics = []
    for idx in range((len(sec1) - 8) // 68 if len(sec1) >= 8 else len(sec1) // 68):
        off = idx * 68
        mid, two_h, spell_slot, elem, r04 = struct.unpack_from("<4BH", sec1, off)
        atk = list(struct.unpack_from("<8H", sec1, off + 6))
        swing_spd, atk_rng = struct.unpack_from("<2H", sec1, off + 0x20)
        hb_delay, mp_cost, stam_cost, snd_id, _r36, cast_cost, _r3a, price, _r40 = struct.unpack_from("<7H2I", sec1, off + 0x2E)
        magics.append({"index": idx, "id": mid, "two_handed": bool(two_h), "spell_slot": spell_slot, "element_flags": f"0x{elem:02x}", "atk_stats": atk, "swing_speed": swing_spd, "attack_range": atk_rng, "hitbox_delay": hb_delay, "mp_cost": mp_cost, "stamina_cost": stam_cost, "sound_id": snd_id, "cast_cost": cast_cost, "price": price})
    trailer = sec1[len(magics) * 68 : len(magics) * 68 + 8].hex() if len(sec1) >= len(magics) * 68 + 8 else ""
    return {"count": len(magics), "trailer_hex": trailer, "entries": magics}


def parse_item_t(raw: bytes, png_dir: Path | None = None) -> dict[str, Any]:
    """Decode ITEM.T (3D item TMD models + 2D HUD/map/card TIM images + checksums)."""
    tmds, tims, other = [], [], []
    for idx, _, _, chunk in iter_t_entries(raw):
        csum_ok = verify_sector_checksum(chunk)["valid"]
        if chunk[:4] == b"\x41\x00\x00\x00" and (tmd := parse_tmd_header(chunk)):
            tmds.append({"index": idx, "bytes": len(chunk), "checksum_ok": csum_ok, **tmd})
        elif chunk[:4] == b"\x10\x00\x00\x00" and (tinfo := parse_tim_info(chunk)):
            if png_dir is not None:
                exp = parse_and_export_tim(chunk, png_dir / f"item_{idx:04d}.png")
                meta = exp if exp else {k: v for k, v in tinfo.items() if k != "palette"}
            else:
                meta = {k: v for k, v in tinfo.items() if k != "palette"}
            tims.append({"index": idx, "bytes": len(chunk), "checksum_ok": csum_ok, **meta})
        else:
            other.append({"index": idx, "bytes": len(chunk), "checksum_ok": csum_ok, "sub_tims": len(scan_tim_entries(chunk, None, f"item_{idx:04d}"))})
    return {"active_entries": len(tmds) + len(tims) + len(other), "tmd_count": len(tmds), "tim_count": len(tims), "other_count": len(other), "tmds_preview": tmds[:16], "tims_preview": tims[:16]}


def parse_talk_t(raw: bytes, png_dir: Path | None = None) -> dict[str, Any]:
    """Decode TALK.T pre-rendered dialogue card TIM metrics and sector checksums (zero script prose)."""
    cards, bad_csum, total_subtims = [], 0, 0
    for idx, _, _, chunk in iter_t_entries(raw):
        csum_ok = verify_sector_checksum(chunk)["valid"]
        if not csum_ok:
            bad_csum += 1
        tinfo = parse_tim_info(chunk)
        tim_end = tinfo["total_bytes"] if tinfo else 0
        sub_tims = scan_tim_entries(chunk[tim_end:], None, f"talk_{idx:04d}") if tim_end < len(chunk) else []
        total_subtims += len(sub_tims)
        if png_dir is not None and tinfo:
            parse_and_export_tim(chunk, png_dir / f"talk_{idx:04d}.png")
        cards.append({"index": idx, "bytes": len(chunk), "checksum_ok": csum_ok, "width": tinfo["width"] if tinfo else 0, "height": tinfo["height"] if tinfo else 0, "bpp": tinfo["bpp"] if tinfo else 0, "vram": [tinfo["vram_x"], tinfo["vram_y"]] if tinfo else None, "tail_bytes": len(chunk) - tim_end})
    return {"card_count": len(cards), "checksum_valid_count": len(cards) - bad_csum, "secondary_tim_count": total_subtims, "cards_preview": cards[:16]}


def build_synthetic_item_talk() -> tuple[bytes, bytes, bytes, bytes]:
    """Build deterministic synthetic ITEM.T, TALK.T, MagicDef[18], and ItemDef[64]."""
    tmd0 = struct.pack("<3I7I", 0x41, 0, 1, 28, 3, 52, 1, 60, 1, 0) + b"\x00" * 64
    clut = struct.pack("<IHHHH16H", 44, 640, 511, 16, 1, *([0x7FFF] * 16))
    px = struct.pack("<IHHHH", 12 + 32, 320, 256, 4, 4) + b"\x11" * 32
    tim0 = struct.pack("<II", 0x10, 0x08) + clut + px
    item_t = build_synthetic_t_archive({0: tmd0, 120: tim0}, total_slots=125)
    talk_px = struct.pack("<IHHHH", 12 + 32768, 320, 256, 64, 256) + b"\x22" * 32768
    talk_tim = struct.pack("<II", 0x10, 0x08) + clut + talk_px
    talk_t = build_synthetic_t_archive({0: talk_tim + b"\x00" * 1984}, total_slots=2)
    sec1 = bytearray(18 * 68 + 8)
    struct.pack_into("<4BH8H", sec1, 0, 2, 7, 64, 0xFF, 0, 39, 6, 14, 0, 0, 0, 0, 0)
    struct.pack_into("<7H2I", sec1, 0x2E, 1, 12, 4, 2, 0, 12, 0, 500, 0)
    sec2 = bytearray(64 * 32)
    struct.pack_into("<2B10hH2I", sec2, 0, 0, 10, 14, 4, 2, 0, 0, 1, 0, 1, 0, 0, 0, 180, 140)
    return item_t, talk_t, bytes(sec1), bytes(sec2)


def _locate_inputs(data_dir: Path | None) -> tuple[Path | None, Path | None, Path | None]:
    disc_dir, _ = resolve_disc_files_dir(data_dir)
    if disc_dir is None:
        return None, None, None
    for base in (disc_dir / "CD" / "COM", disc_dir):
        it, tk, fd = base / "ITEM.T", base / "TALK.T", base / "FDAT.T"
        if it.is_file() or tk.is_file():
            return (it if it.is_file() else None), (tk if tk.is_file() else None), (fd if fd.is_file() else None)
    return None, None, None


def run_parser(data_dir: Path | None, out_dir: Path | None, log_dir: Path | None, offline_synthetic: bool, export_pngs: bool = False) -> tuple[int, dict[str, Any]]:
    """Run ITEM.T, TALK.T, KfItemDef[64], and KfMagicDef[18] decoding."""
    work_dir = (out_dir or (data_dir / "items_talk_parsed" if data_dir is not None else (Path(tempfile.gettempdir()) / "kf_synthetic" / "items_talk" if offline_synthetic else REPO_ROOT / "Corpus" / "work" / "items_talk"))).resolve()
    now_utc = utc_now_iso()
    if not offline_synthetic:
        it_p, tk_p, fd_p = _locate_inputs(data_dir)
        if it_p is None and tk_p is None:
            err = {"status": "MISSING_CORPUS_MEDIA", "errorCode": "MISSING_CORPUS_MEDIA", "parser": "kf_items_magic_talk", "dataDir": str(data_dir or work_dir), "required": ["CD/COM/ITEM.T", "CD/COM/TALK.T"], "generatedAtUtc": now_utc}
            write_json_log(log_dir, "kf_items_magic_talk", err)
            return 2, err
        it_raw = it_p.read_bytes() if it_p else b""
        tk_raw = tk_p.read_bytes() if tk_p else b""
        sec1, sec2 = b"", b""
        if fd_p:
            f_ents = dict((i, c) for i, _, _, c in iter_t_entries(fd_p.read_bytes()))
            if 48 in f_ents and len(secs := parse_fdat_sections(f_ents[48], 9)) >= 3:
                sec1, sec2 = secs[1][2], secs[2][2]
    else:
        it_raw, tk_raw, sec1, sec2 = build_synthetic_item_talk()
    assert_safe_out_dir(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    png_dir = (work_dir / "tim_previews") if export_pngs else None
    item_res = parse_item_t(it_raw, png_dir=png_dir) if it_raw else {}
    talk_res = parse_talk_t(tk_raw, png_dir=png_dir) if tk_raw else {}
    magic_res = decode_magic_defs(sec1) if sec1 else {"count": 0, "entries": []}
    item_defs = decode_item_defs(sec2) if sec2 else []
    out_file = work_dir / "items_magic_talk_report.json"
    out_file.write_text(json.dumps({"status": "OK", "mode": "offline-synthetic" if offline_synthetic else "corpus-media", "generatedAtUtc": now_utc, "item_t": item_res, "talk_t": talk_res, "magic_defs": magic_res, "item_def_count": len(item_defs), "item_defs_preview": item_defs[:16]}, indent=2) + "\n", encoding="utf-8")
    summary = {"status": "OK", "mode": "offline-synthetic" if offline_synthetic else "corpus-media", "item_tmds": item_res.get("tmd_count", 0), "item_tims": item_res.get("tim_count", 0), "talk_cards": talk_res.get("card_count", 0), "magic_defs": magic_res.get("count", 0), "item_defs": len(item_defs), "output": str(out_file)}
    write_json_log(log_dir, "kf_items_magic_talk", summary)
    return 0, summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Parse SLUS-00158 ITEM.T, TALK.T, KfItemDef[64], and KfMagicDef[18].")
    parser.add_argument("--data-dir", type=Path, default=None, help="Input directory containing COM/{ITEM,TALK,FDAT}.T.")
    parser.add_argument("--out-dir", type=Path, default=None, help="Output report directory.")
    parser.add_argument("--log-dir", type=Path, default=None, help="Optional JSON log directory.")
    parser.add_argument("--offline-synthetic", action="store_true", help="Run with synthetic containers (0 retail files).")
    parser.add_argument("--export-pngs", action="store_true", help="Export PNG previews into out-dir/tim_previews.")
    args = parser.parse_args(argv)
    code, payload = run_parser(args.data_dir, args.out_dir, args.log_dir, args.offline_synthetic, args.export_pngs)
    print(json.dumps(payload, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
