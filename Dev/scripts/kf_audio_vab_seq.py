# @module: CrownDepths.Dev.scripts.kf_audio_vab_seq
# @purpose: Clean-room VAB.T (.vh <IIIHHHHBBBBI + ProgAtr + VagAtr + .vb) and pQES SEQ music sequence parser
# @depends-on: argparse, json, struct, sys, tempfile, pathlib, kf_t_archives
# @exports: parse_vab_header, parse_vab_tables, parse_seq_header, analyze_vab_archive, build_synthetic_vab_t, run_parser, main

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

from kf_t_archives import (  # noqa: E402
    assert_safe_out_dir,
    build_synthetic_t_archive,
    iter_t_entries,
    resolve_disc_files_dir,
    utc_now_iso,
    verify_sector_checksum,
    write_json_log,
)


def parse_vab_header(blob: bytes, offset: int = 0) -> dict[str, Any] | None:
    """Parse 32-byte PS1 VABp (pBAV) header with fixed <IIIHHHHBBBBI layout."""
    if offset + 0x20 > len(blob) or blob[offset : offset + 4] != b"pBAV":
        return None
    ver, vid, fsize, res_sys, progs, tones, vags, mvol, mpan, a1, a2, res2 = struct.unpack_from("<IIIHHHHBBBBI", blob, offset + 4)
    if ver not in (5, 6, 7) or progs > 128 or fsize > 0x400000:
        return None
    return {
        "offset": f"0x{offset:06x}",
        "version": ver,
        "vab_id": vid,
        "declared_bytes": fsize,
        "reserved_sys": f"0x{res_sys:04x}",
        "programs": progs,
        "tones": tones,
        "vags": vags,
        "master_vol": mvol,
        "master_pan": mpan,
        "attr": [a1, a2],
        "reserved2": f"0x{res2:08x}",
    }


def parse_vab_tables(blob: bytes, offset: int = 0) -> dict[str, Any] | None:
    """Decode ProgAtr[128], VagAtr[progs*16], and VAG size table inside a .vh header."""
    hdr = parse_vab_header(blob, offset)
    if hdr is None:
        return None
    max_progs = 128 if hdr["version"] >= 5 else 64
    prog_base = offset + 0x20
    tone_base = prog_base + max_progs * 16
    vag_tbl_base = tone_base + hdr["programs"] * 16 * 32
    if vag_tbl_base + 512 > len(blob):
        return {**hdr, "truncated": True}
    progs_active = []
    for p_idx in range(max_progs):
        tones_cnt, mvol, prior, mode, mpan, res0, attr, r1, r2 = struct.unpack_from("<BBBBbbHII", blob, prog_base + p_idx * 16)
        if tones_cnt > 0:
            progs_active.append({"prog_id": p_idx, "tones": tones_cnt, "mvol": mvol, "prior": prior, "mode": mode, "mpan": mpan, "attr": attr})
    tones_list = []
    for t_idx in range(hdr["programs"] * 16):
        prior, mode, vol, pan, center, shift, kmin, kmax, vw, vt, pw, pt, pbm, pbx, r1, r2, adsr1, adsr2, prog, vag = struct.unpack_from("<16BHHhh", blob, tone_base + t_idx * 32)
        if vag > 0 or adsr1 != 0 or adsr2 != 0:
            tones_list.append({"slot": t_idx, "prog": prog, "vag": vag, "vol": vol, "pan": pan, "center": center, "shift": shift, "range": [kmin, kmax], "adsr1": f"0x{adsr1:04x}", "adsr2": f"0x{adsr2:04x}"})
    shift_pow = 3 if hdr["version"] >= 5 else 2
    vag_words = struct.unpack_from("<256H", blob, vag_tbl_base)
    vag_sizes = [{"vag_id": i, "bytes": w << shift_pow} for i, w in enumerate(vag_words) if w > 0]
    vh_bytes = (vag_tbl_base + 512) - offset
    vb_declared = hdr["declared_bytes"] - vh_bytes
    return {
        **hdr,
        "vh_bytes": vh_bytes,
        "vb_declared_bytes": vb_declared,
        "active_programs": progs_active,
        "active_tone_count": len(tones_list),
        "tones_preview": tones_list[:24],
        "vag_table_count": len(vag_sizes),
        "vag_table_total_bytes": sum(v["bytes"] for v in vag_sizes),
        "vag_sizes": vag_sizes,
    }


def parse_seq_header(blob: bytes, offset: int = 0) -> dict[str, Any] | None:
    """Parse big-endian PS1 pQES music sequence header (>IH5B)."""
    if offset + 15 > len(blob) or blob[offset : offset + 4] != b"pQES":
        return None
    ver, res, t0, t1, t2, r_num, r_den = struct.unpack_from(">IH5B", blob, offset + 4)
    tempo_us = (t0 << 16) | (t1 << 8) | t2
    bpm = round(60_000_000.0 / tempo_us, 2) if tempo_us > 0 else 0.0
    return {"offset": f"0x{offset:06x}", "version": ver, "resolution_ppqn": res, "tempo_us_per_qn": tempo_us, "bpm": bpm, "rhythm": f"{r_num}/{1 << min(r_den, 6)}"}


def analyze_vab_archive(raw: bytes) -> dict[str, Any]:
    """Decode all VAB (.vh+.vb) pairs and pQES SEQ entries inside VAB.T."""
    entries = dict((i, c) for i, _, _, c in iter_t_entries(raw))
    vabs, seqs, paired_vb = [], [], set()
    for idx in sorted(entries):
        if idx in paired_vb:
            continue
        chunk = entries[idx]
        if chunk[:4] == b"pBAV":
            meta = parse_vab_tables(chunk)
            if meta is None:
                continue
            vb_chunk = entries.get(idx + 1, b"")
            if idx + 1 in entries:
                paired_vb.add(idx + 1)
            vabs.append({"index": idx, "vh_sector_bytes": len(chunk), "vb_sector_bytes": len(vb_chunk), "checksum_ok": verify_sector_checksum(chunk)["valid"], "vb_size_ok": len(vb_chunk) >= meta["vb_declared_bytes"], **meta})
        elif chunk[:4] == b"pQES":
            seq_meta = parse_seq_header(chunk)
            if seq_meta:
                seqs.append({"index": idx, "bytes": len(chunk), "checksum_ok": verify_sector_checksum(chunk)["valid"], **seq_meta})
    return {"vab_count": len(vabs), "seq_count": len(seqs), "all_programs_lt_128": all(v["programs"] < 128 for v in vabs), "vabs": vabs, "seqs": seqs}


def build_synthetic_vab_t() -> bytes:
    """Build synthetic VAB.T matching VAB.T[0] (ver=6, progs=2, tones=23, vags=22) + .vb + SEQ."""
    progs, tones, vags = 2, 23, 22
    vh_size = 32 + 128 * 16 + progs * 16 * 32 + 512
    vag_bytes = vags * 1024
    vh = bytearray(vh_size)
    struct.pack_into("<4sIIIHHHHBBBBI", vh, 0, b"pBAV", 6, 0, vh_size + vag_bytes, 0xEEEE, progs, tones, vags, 127, 64, 0, 0, 0xFFFFFFFF)
    struct.pack_into("<BBBBbbHII", vh, 32, 12, 127, 0, 0, 64, 0, 0, 0, 0)
    struct.pack_into("<BBBBbbHII", vh, 48, 11, 127, 0, 0, 64, 0, 0, 0, 0)
    tone_base = 32 + 128 * 16
    for t in range(tones):
        struct.pack_into("<16BHHhh", vh, tone_base + t * 32, 0, 0, 127, 64, 60, 0, 0, 127, 0, 0, 0, 0, 0, 0, 0, 0, 0x80FF, 0x5FC0, t // 12, (t % vags) + 1)
    vag_tbl = tone_base + progs * 16 * 32
    for v in range(1, vags + 1):
        struct.pack_into("<H", vh, vag_tbl + v * 2, 1024 >> 3)
    vb = bytearray(vag_bytes)
    vb[0:16] = b"\x00\x07" + b"\x00" * 14
    seq = struct.pack(">4sIH5B", b"pQES", 1, 480, 0x0C, 0x8A, 0x7D, 4, 2) + b"\x00\xFF\x2F\x00"
    return build_synthetic_t_archive({0: bytes(vh), 1: bytes(vb), 2: seq}, total_slots=4)


def _find_vab_file(data_dir: Path | None) -> Path | None:
    disc_dir, _ = resolve_disc_files_dir(data_dir)
    if disc_dir is None:
        return None
    for cand in (disc_dir / "CD" / "COM" / "VAB.T", disc_dir / "VAB.T"):
        if cand.is_file():
            return cand
    return None


def run_parser(data_dir: Path | None, out_dir: Path | None, log_dir: Path | None, offline_synthetic: bool) -> tuple[int, dict[str, Any]]:
    """Run VAB.T (.vh/.vb/pQES) parser on Corpus or deterministic synthetic archive."""
    work_dir = (out_dir or (data_dir / "audio_parsed" if data_dir is not None else (Path(tempfile.gettempdir()) / "kf_synthetic" / "audio" if offline_synthetic else REPO_ROOT / "Corpus" / "work" / "audio"))).resolve()
    now_utc = utc_now_iso()
    if not offline_synthetic:
        vab_path = _find_vab_file(data_dir)
        if vab_path is None:
            err = {"status": "MISSING_CORPUS_MEDIA", "errorCode": "MISSING_CORPUS_MEDIA", "parser": "kf_audio_vab_seq", "dataDir": str(data_dir or work_dir), "required": ["CD/COM/VAB.T"], "generatedAtUtc": now_utc}
            write_json_log(log_dir, "kf_audio_vab_seq", err)
            return 2, err
        parsed = analyze_vab_archive(vab_path.read_bytes())
    else:
        parsed = analyze_vab_archive(build_synthetic_vab_t())
    assert_safe_out_dir(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    out_file = work_dir / "audio_report.json"
    out_file.write_text(json.dumps({"status": "OK", "mode": "offline-synthetic" if offline_synthetic else "corpus-media", "generatedAtUtc": now_utc, **parsed}, indent=2) + "\n", encoding="utf-8")
    summary = {"status": "OK", "mode": "offline-synthetic" if offline_synthetic else "corpus-media", "vab_count": parsed["vab_count"], "seq_count": parsed["seq_count"], "all_programs_lt_128": parsed["all_programs_lt_128"], "output": str(out_file)}
    write_json_log(log_dir, "kf_audio_vab_seq", summary)
    return 0, summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Parse SLUS-00158 VAB.T (.vh <IIIHHHHBBBBI + .vb) and pQES SEQ audio banks.")
    parser.add_argument("--data-dir", type=Path, default=None, help="Input directory containing CD/COM/VAB.T.")
    parser.add_argument("--out-dir", type=Path, default=None, help="Output report directory.")
    parser.add_argument("--log-dir", type=Path, default=None, help="Optional JSON log directory.")
    parser.add_argument("--offline-synthetic", action="store_true", help="Run with synthetic VAB.T (0 retail files).")
    args = parser.parse_args(argv)
    code, payload = run_parser(args.data_dir, args.out_dir, args.log_dir, args.offline_synthetic)
    print(json.dumps(payload, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
