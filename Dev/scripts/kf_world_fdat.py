# @module: CrownDepths.Dev.scripts.kf_world_fdat
# @purpose: Clean-room FDAT.T zone triplets, KfMapCell[6400], FDAT[47] VRAM atlas, FDAT[48] 9-sec DB, FDAT[49..66] viewmodels
# @depends-on: argparse, json, struct, sys, tempfile, pathlib, kf_t_archives, kf_meshes_mo_rtmd
# @exports: FDAT48_EXPECTED_SIZES, ZONE_S1_EXPECTED_SIZES, parse_fdat_sections, parse_fdat48_master_db, parse_zone_triplet, analyze_fdat_archive, build_synthetic_fdat_t, run_parser, main

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

from kf_meshes_mo_rtmd import parse_mo_entry, parse_rtim_stream, parse_tmd_header  # noqa: E402
from kf_t_archives import (  # noqa: E402
    assert_safe_out_dir,
    build_synthetic_t_archive,
    iter_t_entries,
    resolve_disc_files_dir,
    utc_now_iso,
    verify_sector_checksum,
    write_json_log,
)

FDAT48_EXPECTED_SIZES = (7680, 1232, 2048, 1200, 1664, 2816, 2560, 6280, 83540)
ZONE_S1_EXPECTED_SIZES = (12992, 3200, 8400, 2048)


def parse_fdat_sections(blob: bytes, max_sections: int = 16) -> list[tuple[int, int, bytes]]:
    """Decode chained [u32 section_size, payload] blocks inside FDAT slots."""
    sections: list[tuple[int, int, bytes]] = []
    pos = 0
    while len(sections) < max_sections and pos + 4 <= len(blob):
        sz = struct.unpack_from("<I", blob, pos)[0]
        if sz == 0 or pos + 4 + sz > len(blob):
            break
        sections.append((pos, sz, blob[pos + 4 : pos + 4 + sz]))
        pos += 4 + sz
    return sections


def _parse_tmd_pack(sec: bytes) -> dict[str, Any]:
    count = struct.unpack_from("<h", sec, 0)[0]
    pos, models = 4, []
    for _ in range(max(0, count)):
        if pos + 4 > len(sec):
            break
        sz = struct.unpack_from("<I", sec, pos)[0]
        if sz > 4 and pos + 4 + sz <= len(sec):
            tmd = parse_tmd_header(sec, pos + 4)
            if tmd:
                models.append(tmd)
        pos += max(4, sz)
    return {"declared_slots": count, "parsed_tmds": len(models)}


def parse_fdat48_master_db(blob: bytes) -> dict[str, Any]:
    """Decode FDAT[48] 9-section master boot database (kf_game_mount_t_archives)."""
    secs = parse_fdat_sections(blob, max_sections=9)
    sizes = [sz for _off, sz, _data in secs]
    growth_sample = []
    if len(secs) > 3 and len(secs[3][2]) >= 12:
        for lv in (0, 1, 9, 49, 98):
            if lv * 12 + 12 <= len(secs[3][2]):
                hp, mp, sg, mg, xp = struct.unpack_from("<4HI", secs[3][2], lv * 12)
                growth_sample.append({"level": lv + 1, "hp": hp, "mp": mp, "str_gain": sg, "mag_gain": mg, "next_xp": xp})
    return {
        "bytes": len(blob),
        "checksum_ok": verify_sector_checksum(blob)["valid"],
        "section_count": len(secs),
        "section_sizes": sizes,
        "sizes_match_expected": tuple(sizes) == FDAT48_EXPECTED_SIZES,
        "map_obj_def_count": len(secs[0][2]) // 24 if len(secs) > 0 else 0,
        "magic_def_count": (len(secs[1][2]) - 8) // 68 if len(secs) > 1 and len(secs[1][2]) >= 8 else 0,
        "item_def_count": len(secs[2][2]) // 32 if len(secs) > 2 else 0,
        "level_growth_count": len(secs[3][2]) // 12 if len(secs) > 3 else 0,
        "level_growth_sample": growth_sample,
        "tmd_pack_slot0": _parse_tmd_pack(secs[7][2]) if len(secs) > 7 else None,
        "tmd_pack_slot40": _parse_tmd_pack(secs[8][2]) if len(secs) > 8 else None,
    }


def parse_zone_triplet(s0: bytes, s1: bytes, s2: bytes, zone_id: int) -> dict[str, Any]:
    """Decode a zone's (3*z, 3*z+1, 3*z+2) map cells, entity/prop sections, and callback table."""
    secs0 = parse_fdat_sections(s0, max_sections=4)
    cell_bytes = secs0[0][2] if secs0 else b""
    non_empty_cells = sum(1 for i in range(0, min(len(cell_bytes), 64000), 10) if any(cell_bytes[i : i + 10]))
    secs1 = parse_fdat_sections(s1, max_sections=4)
    s1_sizes = [sz for _off, sz, _d in secs1]
    return {
        "zone_id": zone_id,
        "slot_base": zone_id * 3,
        "map_cell_bytes": len(cell_bytes),
        "map_cells_expected": len(cell_bytes) == 64000,
        "non_empty_cells": non_empty_cells,
        "slot0_extra_bytes": secs0[1][1] if len(secs0) > 1 else 0,
        "slot1_section_sizes": s1_sizes,
        "slot1_sizes_expected": tuple(s1_sizes) == ZONE_S1_EXPECTED_SIZES,
        "slot2_bytes": len(s2),
        "checksums_ok": all(verify_sector_checksum(b)["valid"] for b in (s0, s1, s2)),
    }


def analyze_fdat_archive(raw: bytes) -> dict[str, Any]:
    """Decode FDAT.T zone triplets, FDAT[47], FDAT[48], and FDAT[49..66] weapon view-models."""
    entries = dict((i, c) for i, _, _, c in iter_t_entries(raw))
    zones = [parse_zone_triplet(entries[3 * z], entries[3 * z + 1], entries[3 * z + 2], z) for z in range(16) if all((3 * z + k) in entries for k in range(3))]
    f47 = parse_rtim_stream(entries[47], max_blocks=1024) if 47 in entries else None
    f48 = parse_fdat48_master_db(entries[48]) if 48 in entries else None
    viewmodels = [{"slot": idx, "bytes": len(entries[idx]), **(parse_mo_entry(entries[idx]) or {})} for idx in range(49, 67) if idx in entries]
    return {"active_slots": len(entries), "zone_count": len(zones), "zones": zones, "fdat_47_vram": f47, "fdat_48_master_db": f48, "weapon_viewmodel_count": len(viewmodels), "weapon_viewmodels": viewmodels}


def build_synthetic_fdat_t() -> bytes:
    """Build deterministic synthetic FDAT.T covering zone 0 triplet, FDAT[47], FDAT[48] 9 sections, and FDAT[49]."""
    z0_s0 = struct.pack("<I", 64000) + (b"\x01\x10\x00\x01\x00\x00\x00\x00\x00\x00" * 100 + b"\x00" * (64000 - 1000)) + struct.pack("<II", 16, 0) + b"\x00" * 12
    z0_s1 = b"".join(struct.pack("<I", sz) + b"\x00" * sz for sz in ZONE_S1_EXPECTED_SIZES)
    z0_s2 = struct.pack("<4I", 0x8019F104, 0x8019F10C, 0x8019F114, 0x8019F0FC)
    f47 = struct.pack("<8h", 576, 258, 16, 1, 576, 258, 16, 1) + b"\x00" * 32
    secs48 = []
    for idx, sz in enumerate(FDAT48_EXPECTED_SIZES):
        buf = bytearray(sz)
        if idx == 3:
            struct.pack_into("<4HI", buf, 0, 50, 30, 20, 20, 50)
        elif idx in (7, 8):
            tmd = struct.pack("<3I7I", 0x41, 0, 1, 28, 1, 40, 1, 48, 1, 0) + b"\x00" * 32
            struct.pack_into("<hHI", buf, 0, 1, 0, 4 + len(tmd))
            buf[8 : 8 + len(tmd)] = tmd
        secs48.append(struct.pack("<I", sz) + bytes(buf))
    f48 = b"".join(secs48) + b"\x00" * 16
    tmd_vm = struct.pack("<3I7I", 0x41, 0, 1, 28, 2, 44, 1, 52, 1, 0) + b"\x00" * 32
    f49 = struct.pack("<5I", 0x20 + len(tmd_vm), 1, 0x20, 0x1C, 0x14) + b"\x00" * 12 + tmd_vm
    return build_synthetic_t_archive({0: z0_s0, 1: z0_s1, 2: z0_s2, 47: f47, 48: f48, 49: f49}, total_slots=70)


def _find_fdat_file(data_dir: Path | None) -> Path | None:
    disc_dir, _ = resolve_disc_files_dir(data_dir)
    if disc_dir is None:
        return None
    for cand in (disc_dir / "CD" / "COM" / "FDAT.T", disc_dir / "FDAT.T"):
        if cand.is_file():
            return cand
    return None


def run_parser(data_dir: Path | None, out_dir: Path | None, log_dir: Path | None, offline_synthetic: bool) -> tuple[int, dict[str, Any]]:
    """Run FDAT.T zone triplet + FDAT[47]/FDAT[48]/FDAT[49..66] parser."""
    work_dir = (out_dir or (data_dir / "fdat_parsed" if data_dir is not None else (Path(tempfile.gettempdir()) / "kf_synthetic" / "fdat" if offline_synthetic else REPO_ROOT / "Corpus" / "work" / "fdat"))).resolve()
    now_utc = utc_now_iso()
    if not offline_synthetic:
        fdat_path = _find_fdat_file(data_dir)
        if fdat_path is None:
            err = {"status": "MISSING_CORPUS_MEDIA", "errorCode": "MISSING_CORPUS_MEDIA", "parser": "kf_world_fdat", "dataDir": str(data_dir or work_dir), "required": ["CD/COM/FDAT.T"], "generatedAtUtc": now_utc}
            write_json_log(log_dir, "kf_world_fdat", err)
            return 2, err
        parsed = analyze_fdat_archive(fdat_path.read_bytes())
    else:
        parsed = analyze_fdat_archive(build_synthetic_fdat_t())
    assert_safe_out_dir(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    out_file = work_dir / "fdat_report.json"
    out_file.write_text(json.dumps({"status": "OK", "mode": "offline-synthetic" if offline_synthetic else "corpus-media", "generatedAtUtc": now_utc, **parsed}, indent=2) + "\n", encoding="utf-8")
    f48 = parsed.get("fdat_48_master_db") or {}
    summary = {"status": "OK", "mode": "offline-synthetic" if offline_synthetic else "corpus-media", "zone_count": parsed["zone_count"], "fdat48_sections": f48.get("section_count", 0), "fdat48_sizes_ok": f48.get("sizes_match_expected", False), "weapon_viewmodel_count": parsed["weapon_viewmodel_count"], "output": str(out_file)}
    write_json_log(log_dir, "kf_world_fdat", summary)
    return 0, summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Parse SLUS-00158 FDAT.T zones, FDAT[47] VRAM, FDAT[48] master DB, and weapon view-models.")
    parser.add_argument("--data-dir", type=Path, default=None, help="Input directory containing CD/COM/FDAT.T.")
    parser.add_argument("--out-dir", type=Path, default=None, help="Output report directory.")
    parser.add_argument("--log-dir", type=Path, default=None, help="Optional JSON log directory.")
    parser.add_argument("--offline-synthetic", action="store_true", help="Run with synthetic FDAT.T (0 retail files).")
    args = parser.parse_args(argv)
    code, payload = run_parser(args.data_dir, args.out_dir, args.log_dir, args.offline_synthetic)
    print(json.dumps(payload, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
