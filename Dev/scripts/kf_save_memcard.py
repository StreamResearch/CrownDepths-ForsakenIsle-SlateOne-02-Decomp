# @module: CrownDepths.Dev.scripts.kf_save_memcard
# @purpose: Clean-room BASLUS-00158 PS1 Memory Card 8192-B block, .mcr parity, and 0x3c00 additive checksum parser
# @depends-on: argparse, json, struct, sys, tempfile, pathlib, kf_t_archives
# @exports: SAVE_FILE_BYTES, SAVE_HEADER_BYTES, SAVE_PAYLOAD_BYTES, compute_kf_payload_checksum, compute_mcr_dir_xor, decode_save_slot, extract_mcr_saves, build_synthetic_save_bytes, build_synthetic_mcr_bytes, run_parser, main

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

from kf_t_archives import assert_safe_out_dir, utc_now_iso, write_json_log  # noqa: E402

SAVE_FILE_BYTES = 0x4000
SAVE_HEADER_BYTES = 0x400
SAVE_PAYLOAD_BYTES = 0x3C00
MC_BLOCK_BYTES = 0x2000
SAVE_PREFIX = "BASLUS-00158"


def compute_kf_payload_checksum(payload: bytes) -> int:
    """Compute signed 32-bit byte-wise additive sum matching kf_game_mc_checksum_payload."""
    total = sum(payload[:SAVE_PAYLOAD_BYTES]) & 0xFFFFFFFF
    return total - 0x100000000 if (total & 0x80000000) else total


def compute_mcr_dir_xor(frame_127: bytes) -> int:
    """Compute 8-bit XOR parity byte at +0x7F for 128-byte PS1 Memory Card directory frames."""
    acc = 0
    for b in frame_127[:127]:
        acc ^= b
    return acc


def _decode_sjis_digits(blob: bytes, start: int, count: int) -> int:
    val = 0
    for i in range(count):
        word = struct.unpack_from("<H", blob, start + i * 2)[0]
        if word != 0x4081 and ((word >> 8) >= 0x4F):
            val = val * 10 + ((word >> 8) - 0x4F)
        else:
            val *= 10
    return val


def _encode_sjis_digits(buf: bytearray, end_pair_idx: int, value: int, max_digits: int) -> None:
    v = max(0, int(value))
    for i in range(max_digits):
        off = (end_pair_idx - i) * 2 + 4
        buf[off] = 0x82
        buf[off + 1] = 0x4F + (v % 10)
        v //= 10
        if v == 0:
            break


def decode_save_slot(blob: bytes) -> dict[str, Any]:
    """Decode KfSaveHeader (0x400 B), additive checksum at +0x200, and serialized player/world state."""
    if len(blob) < SAVE_FILE_BYTES:
        raise ValueError(f"Expected >= {SAVE_FILE_BYTES} save bytes, got {len(blob)}")
    magic = blob[0:2].decode("ascii", errors="replace")
    icon_type, block_cnt = blob[2], blob[3]
    stored_csum = struct.unpack_from("<i", blob, 0x200)[0]
    payload = blob[SAVE_HEADER_BYTES : SAVE_HEADER_BYTES + SAVE_PAYLOAD_BYTES]
    computed_csum = compute_kf_payload_checksum(payload)

    cur_map = struct.unpack_from("<I", payload, 0)[0]
    fade_mode = payload[4]
    event_nonzero = sum(1 for b in payload[5:0x105] if b != 0)
    inv_nonzero = sum(1 for b in payload[0x391A:0x3992] if b != 0)
    magic_learned = sum(1 for b in payload[0x3992:0x39D2] if b != 0)
    px, py, pz, stand_id = struct.unpack_from("<4i", payload, 0x39D4)
    view_yaw, look_pitch = struct.unpack_from("<2I", payload, 0x39E4)
    xp, next_xp, gold = struct.unpack_from("<IiI", payload, 0x39EC)
    hours, max_hp, cur_hp, max_mp, cur_mp, b_str, b_mag, mod_str, mod_mag = struct.unpack_from("<9h", payload, 0x39F8)
    level, active_slot = payload[0x3A2E], payload[0x3A2F]
    equip = list(payload[0x3A30:0x3A3B])

    return {
        "header": {
            "magic": magic,
            "icon_type": f"0x{icon_type:02x}",
            "block_count": block_cnt,
            "sjis_playtime_score": _decode_sjis_digits(blob, 0x2C, 6),
            "sjis_level": _decode_sjis_digits(blob, 0x3E, 2),
        },
        "checksum": {"stored": stored_csum, "computed": computed_csum, "checksum_valid": (magic == "SC" and stored_csum == computed_csum)},
        "state": {
            "cur_map": cur_map,
            "cur_fade_mode": fade_mode,
            "pos": [px, py, pz],
            "standing_entity_id": stand_id,
            "view_angles": [view_yaw, look_pitch],
            "level": level,
            "active_slot": active_slot,
            "experience": xp,
            "next_level_xp": next_xp,
            "gold": gold,
            "time_hours": hours,
            "hp": [cur_hp, max_hp],
            "mp": [cur_mp, max_mp],
            "strength": [b_str, mod_str],
            "magic": [b_mag, mod_mag],
            "equip_ids": equip,
            "event_flags_set": event_nonzero,
            "inventory_items_held": inv_nonzero,
            "learned_spells": magic_learned,
        },
    }


def extract_mcr_saves(mcr: bytes) -> list[dict[str, Any]]:
    """Scan a 128 KiB .mcr/.mcd Memory Card image for BASLUS-00158 2-block saves and verify directory XOR."""
    saves: list[dict[str, Any]] = []
    if len(mcr) < 131072 or mcr[:2] != b"MC":
        return saves
    for slot in range(15):
        dir_off = (slot + 1) * 128
        frame = mcr[dir_off : dir_off + 128]
        if frame[0] != 0x51:
            continue
        fname = frame[10:30].split(b"\x00", 1)[0].decode("ascii", errors="replace")
        if not fname.startswith(SAVE_PREFIX):
            continue
        dir_xor_ok = compute_mcr_dir_xor(frame) == frame[127]
        blocks, cur, chain_ok = bytearray(), slot, dir_xor_ok
        for _ in range(2):
            c_off = (cur + 1) * 128
            c_frame = mcr[c_off : c_off + 128]
            chain_ok = chain_ok and (compute_mcr_dir_xor(c_frame) == c_frame[127])
            b_off = (cur + 1) * MC_BLOCK_BYTES
            blocks.extend(mcr[b_off : b_off + MC_BLOCK_BYTES])
            nxt = struct.unpack_from("<H", c_frame, 8)[0]
            if nxt == 0xFFFF or nxt >= 15:
                break
            cur = nxt
        if len(blocks) >= SAVE_FILE_BYTES:
            saves.append({"slot_name": fname, "dir_slot": slot, "dir_xor_valid": chain_ok, **decode_save_slot(bytes(blocks[:SAVE_FILE_BYTES]))})
    return saves


def build_synthetic_save_bytes(slot: int = 1, cur_map: int = 2, level: int = 12, hp: int = 180, mp: int = 95, gold: int = 4200, xp: int = 3100) -> bytes:
    """Build a valid checksummed 0x4000-byte BASLUS-00158 save slot container."""
    out = bytearray(SAVE_FILE_BYTES)
    out[0:4] = b"SC\x13\x02"
    for off in range(4, 0x44, 2):
        out[off : off + 2] = b"\x81\x40"
    out[0x22], out[0x23] = 0x82, 0x4F + (slot % 10)
    _encode_sjis_digits(out, 0x19, xp, 6)
    _encode_sjis_digits(out, 0x1E, level, 2)
    struct.pack_into("<16H", out, 0x60, 0x0000, *([0x7FFF] * 15))

    payload = bytearray(SAVE_PAYLOAD_BYTES)
    struct.pack_into("<IB", payload, 0, cur_map, 0)
    payload[5] = 0x01
    payload[0x391A] = 3
    payload[0x3992] = 1
    struct.pack_into("<4i2I", payload, 0x39D4, 0x11800, -0x3200, 0x18000, -1, 0x9C40000, 0)
    struct.pack_into("<IiI9h", payload, 0x39EC, xp, xp + 900, gold, 5, hp, hp, mp, mp, 24, 22, 2, 1)
    payload[0x3A2E], payload[0x3A2F] = level & 0xFF, slot & 0xFF
    payload[0x3A30:0x3A3B] = bytes([0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x00])

    csum = compute_kf_payload_checksum(bytes(payload))
    struct.pack_into("<i", out, 0x200, csum)
    out[SAVE_HEADER_BYTES:] = payload
    return bytes(out)


def build_synthetic_mcr_bytes(slot: int = 1, **save_kwargs: Any) -> bytes:
    """Build a valid 128 KiB .mcr card image containing one 2-block BASLUS-00158 save."""
    save = build_synthetic_save_bytes(slot=slot, **save_kwargs)
    mcr = bytearray(131072)
    mcr[0:2] = b"MC"
    mcr[127] = compute_mcr_dir_xor(mcr[0:127])
    for blk in range(2):
        d_off = (blk + 1) * 128
        mcr[d_off] = 0x51 if blk == 0 else 0x53
        struct.pack_into("<IH", mcr, d_off + 4, SAVE_FILE_BYTES, 1 if blk == 0 else 0xFFFF)
        if blk == 0:
            name = f"{SAVE_PREFIX}{slot}".encode("ascii")
            mcr[d_off + 10 : d_off + 10 + len(name)] = name
        mcr[d_off + 127] = compute_mcr_dir_xor(mcr[d_off : d_off + 127])
        b_off = (blk + 1) * MC_BLOCK_BYTES
        mcr[b_off : b_off + MC_BLOCK_BYTES] = save[blk * MC_BLOCK_BYTES : (blk + 1) * MC_BLOCK_BYTES]
    return bytes(mcr)


def _find_save_files(roots: list[Path]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for root in roots:
        if not root.is_dir():
            continue
        for fp in sorted(root.rglob("*")):
            if not fp.is_file():
                continue
            if fp.name.startswith(SAVE_PREFIX) and fp.stat().st_size >= SAVE_FILE_BYTES:
                found.append({"slot_name": fp.name, "dir_xor_valid": True, **decode_save_slot(fp.read_bytes()[:SAVE_FILE_BYTES])})
            elif fp.suffix.lower() in (".mcr", ".mcd"):
                found.extend(extract_mcr_saves(fp.read_bytes()))
    return found


def run_parser(data_dir: Path | None, out_dir: Path | None, log_dir: Path | None, offline_synthetic: bool) -> tuple[int, dict[str, Any]]:
    """Decode BASLUS-00158 save files or .mcr/.mcd images with checksum verification."""
    explicit_dir = data_dir is not None
    work_dir = (out_dir or (data_dir / "save_parsed" if data_dir is not None else (Path(tempfile.gettempdir()) / "kf_synthetic" / "save" if offline_synthetic else REPO_ROOT / "Corpus" / "work" / "save"))).resolve()
    now_utc = utc_now_iso()
    if not offline_synthetic:
        roots = [data_dir] if explicit_dir else [REPO_ROOT / "Corpus" / "work" / "saves"]
        slots = _find_save_files(roots)
        if not slots:
            err = {"status": "MISSING_CORPUS_MEDIA", "errorCode": "MISSING_CORPUS_MEDIA", "parser": "kf_save_memcard", "dataDir": str(data_dir or work_dir), "required": ["BASLUS-00158* or *.mcr/*.mcd"], "generatedAtUtc": now_utc}
            write_json_log(log_dir, "kf_save_memcard", err)
            return 2, err
    else:
        slots = extract_mcr_saves(build_synthetic_mcr_bytes(slot=1))
    assert_safe_out_dir(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    all_ok = all(s["checksum"]["checksum_valid"] and s.get("dir_xor_valid", True) for s in slots)
    out_file = work_dir / "save_memcard_report.json"
    out_file.write_text(json.dumps({"status": "OK", "mode": "offline-synthetic" if offline_synthetic else "corpus-media", "generatedAtUtc": now_utc, "slot_count": len(slots), "all_checksums_valid": all_ok, "slots": slots}, indent=2) + "\n", encoding="utf-8")
    summary = {"status": "OK", "mode": "offline-synthetic" if offline_synthetic else "corpus-media", "slot_count": len(slots), "all_checksums_valid": all_ok, "output": str(out_file)}
    write_json_log(log_dir, "kf_save_memcard", summary)
    return 0, summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Parse SLUS-00158 BASLUS-00158 saves and .mcr/.mcd Memory Cards.")
    parser.add_argument("--data-dir", type=Path, default=None, help="Input directory containing BASLUS-00158* or *.mcr.")
    parser.add_argument("--out-dir", type=Path, default=None, help="Output report directory.")
    parser.add_argument("--log-dir", type=Path, default=None, help="Optional JSON log directory.")
    parser.add_argument("--offline-synthetic", action="store_true", help="Run with synthetic 128 KiB .mcr save (0 retail files).")
    args = parser.parse_args(argv)
    code, payload = run_parser(args.data_dir, args.out_dir, args.log_dir, args.offline_synthetic)
    print(json.dumps(payload, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
