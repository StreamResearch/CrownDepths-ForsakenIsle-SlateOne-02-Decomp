# @module: CrownDepths.Dev.scripts.kf_t_archives
# @purpose: Clean-room PS1 .T sector containers, chunked SHA-256 gate, FN.D, and OP/*.D + OP/*.S parsers
# @depends-on: argparse, datetime, hashlib, json, logging, re, struct, sys, tempfile, time, unicodedata, pathlib
# @exports: T_SECTOR_BYTES, XA_SECTOR_BYTES, assert_safe_out_dir, setup_logger, emit_heartbeat, sha256_file_chunked, verify_required_disc_checksums, verify_sector_checksum, parse_t_header, iter_t_entries, decode_fn_d, parse_op_d_container, parse_op_str_header, build_synthetic_t_archive, run_parser, main

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import logging
import re
import struct
import sys
import tempfile
import time
import unicodedata
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
DEV_DIR = SCRIPTS_DIR.parent
REPO_ROOT = DEV_DIR.parent
INTEGRITY_SCHEMA_PATH = DEV_DIR / "schemas" / "standalone_integrity.json"
T_SECTOR_BYTES = 2048
XA_SECTOR_BYTES = 2336
SECTOR_CHECKSUM_SEED = 0x12345678
_TIM_MAGIC = b"\x10\x00\x00\x00"


def utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def assert_safe_out_dir(out_dir: Path) -> None:
    """Refuse writes inside Corpus/standalone, Dev/{scripts,schemas,docs}, .git, or Archive."""
    resolved = out_dir.resolve()
    for base in (REPO_ROOT / "Corpus" / "standalone", REPO_ROOT / "Dev" / "scripts", REPO_ROOT / "Dev" / "schemas", REPO_ROOT / "Dev" / "docs", REPO_ROOT / "Archive", REPO_ROOT / ".git"):
        try:
            resolved.relative_to(base.resolve())
            raise ValueError(f"Refusing to write inside protected path: {resolved}")
        except ValueError as exc:
            if "Refusing to write" in str(exc):
                raise


def setup_logger(log_dir: Path | None, name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    if log_dir is None:
        logger.addHandler(logging.NullHandler())
        return logger
    assert_safe_out_dir(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(log_dir / f"{name}.log", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(fh)
    return logger


def write_json_log(log_dir: Path | None, stem: str, payload: dict[str, Any]) -> None:
    if log_dir is not None:
        assert_safe_out_dir(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / f"{stem}.log.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def emit_heartbeat(cur: int, total: int, label: str, start_ts: float, last_ts: float, force: bool = False) -> float:
    """Emit throttled <= 15s progress updates without leaving raw escape garbage on pipes."""
    now = time.monotonic()
    if not force and (now - last_ts) < 15.0:
        return last_ts
    pct = (cur / total) * 100.0 if total else 0.0
    msg = f"[{pct:5.1f}%] ({cur}/{total}) {label} [Elapsed: {int(now - start_ts)}s]"
    sys.stderr.write(f"\r\x1b[K{msg}" if sys.stderr.isatty() else f"{msg}\n")
    sys.stderr.flush()
    return now


def sha256_file_chunked(path: Path, chunk_bytes: int = 1024 * 1024) -> str:
    """Compute SHA-256 in 1 MiB chunks, safe for > 64 MiB stream files."""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(chunk_bytes), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_disc_rel(disc_root: Path, rel_path: str) -> Path | None:
    trimmed = rel_path.removeprefix("disc/files/") if rel_path.startswith("disc/files/") else rel_path
    cands = [disc_root / rel_path, disc_root / trimmed, disc_root / "disc" / "files" / trimmed]
    if disc_root.name.lower() == "files":
        cands.extend([disc_root.parents[1] / rel_path, disc_root.parent / trimmed])
    for cand in cands:
        if cand.is_file():
            return cand
    return None


def verify_required_disc_checksums(disc_root: Path, checksums: list[dict[str, Any]], logger: logging.Logger | None = None) -> dict[str, Any]:
    """Verify retail disc files against standalone_integrity.json requiredDiscChecksums."""
    if not disc_root.is_dir():
        missing = [str(it["relativePath"]) for it in checksums if it.get("isRequired", True)]
        return {"ok": False, "status": "MISSING_CORPUS_MEDIA", "missingFiles": missing, "mismatchedFiles": [], "verifiedFiles": []}
    missing, mismatched, verified = [], [], []
    start_ts = last_ts = time.monotonic()
    for idx, entry in enumerate(checksums, start=1):
        rel, is_req = str(entry["relativePath"]), bool(entry.get("isRequired", True))
        target = _resolve_disc_rel(disc_root, rel)
        last_ts = emit_heartbeat(idx, len(checksums), f"SHA-256 {rel}", start_ts, last_ts)
        if target is None:
            if is_req:
                missing.append(rel)
            continue
        actual_sz, actual_sha = target.stat().st_size, sha256_file_chunked(target)
        exp_sz, exp_sha = entry.get("expectedSizeBytes"), str(entry.get("expectedSha256") or "").lower()
        if (exp_sz is not None and actual_sz != int(exp_sz)) or (exp_sha and actual_sha != exp_sha):
            mismatched.append({"relativePath": rel, "expectedSizeBytes": exp_sz, "actualSizeBytes": actual_sz, "expectedSha256": exp_sha, "actualSha256": actual_sha})
        else:
            verified.append(rel)
    emit_heartbeat(len(checksums), len(checksums), "Disc checksum gate finished", start_ts, last_ts, force=True)
    status = "MISSING_CORPUS_MEDIA" if missing else ("CHECKSUM_MISMATCH" if mismatched else "OK")
    if logger is not None:
        logger.info("Checksum gate status=%s verified=%d missing=%d mismatched=%d", status, len(verified), len(missing), len(mismatched))
    return {"ok": status == "OK", "status": status, "missingFiles": missing, "mismatchedFiles": mismatched, "verifiedFiles": verified}


def verify_sector_checksum(buf: bytes) -> dict[str, Any]:
    """Verify 32-bit additive checksum seeded with 0x12345678 (kf_game_cd_verify_sector_checksum)."""
    if len(buf) < 8 or (len(buf) % 4) != 0:
        return {"valid": False, "computed": None, "stored": None}
    words = struct.unpack(f"<{len(buf) // 4}I", buf)
    computed = (SECTOR_CHECKSUM_SEED + sum(words[:-1])) & 0xFFFFFFFF
    stored = words[-1]
    return {"valid": computed == stored, "computed": f"0x{computed:08x}", "stored": f"0x{stored:08x}"}


def parse_t_header(raw: bytes) -> dict[str, Any]:
    """Parse PS1 .T sector table header (u16 entry_count + u16 sector_offsets[count+1])."""
    if len(raw) < 4:
        raise ValueError("Truncated .T container (< 4 bytes)")
    cnt = struct.unpack_from("<H", raw, 0)[0]
    if cnt == 0 or len(raw) < (cnt + 2) * 2:
        raise ValueError(f"Invalid .T entry_count={cnt} for {len(raw)} bytes")
    offs = struct.unpack_from(f"<{cnt + 1}H", raw, 2)
    monotonic = offs[0] >= 1 and all(offs[i + 1] >= offs[i] for i in range(cnt))
    aligned_end = offs[-1] * T_SECTOR_BYTES == len(raw)
    active = sum(1 for i in range(cnt) if offs[i + 1] > offs[i])
    return {"total_slots": cnt, "active_slots": active, "first_sector": offs[0], "end_sector": offs[-1], "total_bytes": len(raw), "monotonic": monotonic, "aligned_end": aligned_end, "sector_offsets": list(offs)}


def iter_t_entries(raw: bytes) -> list[tuple[int, int, int, bytes]]:
    hdr = parse_t_header(raw)
    offs = hdr["sector_offsets"]
    return [(i, offs[i], offs[i + 1], raw[offs[i] * T_SECTOR_BYTES : offs[i + 1] * T_SECTOR_BYTES]) for i in range(hdr["total_slots"]) if offs[i + 1] > offs[i]]


def decode_fn_d(raw: bytes, include_names: bool = False) -> dict[str, Any]:
    """Decode /CD/FN.D CP932 item descriptor metrics cleanly (names opt-in for runtime extraction)."""
    lines = [ln.rstrip("\r\n") for ln in raw.rstrip(b"\x1a").decode("cp932", errors="replace").splitlines() if ln.strip()]
    rows = []
    for ln in lines[2:]:
        if m := re.match(r"^\s*(\d+)\s+(\d+)\s*(.*)$", ln):
            raw_nm = m.group(3).strip()
            rec: dict[str, Any] = {"id": int(m.group(1)), "category": int(m.group(2)), "has_label": bool(raw_nm)}
            if include_names:
                rec.update({"raw_jp": raw_nm, "name_jp": unicodedata.normalize("NFKC", raw_nm)})
            rows.append(rec)
    return {"bytes": len(raw), "header": lines[:2], "count": len(rows), "eof_marker": any(r["id"] == 999 for r in rows), "entries": rows}


def parse_op_d_container(raw: bytes) -> dict[str, Any]:
    """Analyze OP.D / OPU.D sequential TIM frames plus embedded pBAV/pQES audio blocks."""
    tim_headers, pos = [], 0
    while pos + 20 <= len(raw) and raw[pos : pos + 4] == _TIM_MAGIC:
        flags = struct.unpack_from("<I", raw, pos + 4)[0]
        p2 = pos + 8 + (struct.unpack_from("<I", raw, pos + 8)[0] if (flags & 8) else 0)
        if p2 + 12 > len(raw):
            break
        pb, px, py, pw, ph = struct.unpack_from("<IHHHH", raw, p2)
        tim_headers.append({"offset": f"0x{pos:06x}", "pmode": flags & 7, "vram": [px, py, pw, ph], "bytes": (p2 + pb) - pos})
        pos = p2 + pb
    return {
        "bytes": len(raw),
        "tim_count": len(tim_headers),
        "tim_span_end": f"0x{pos:06x}",
        "vab_offsets": [f"0x{i:06x}" for i in range(0, len(raw) - 3, 4) if raw[i : i + 4] == b"pBAV"],
        "seq_offsets": [f"0x{i:06x}" for i in range(0, len(raw) - 3, 4) if raw[i : i + 4] == b"pQES"],
        "tims": tim_headers,
    }


def parse_op_str_header(path: Path) -> dict[str, Any]:
    """Read first 64 bytes of an OP/*.S CD-XA MDEC stream (safe on > 64 MiB ED1.S)."""
    sz = path.stat().st_size
    with path.open("rb") as fh:
        head = fh.read(64)
    off = head.find(b"\x60\x01\x01\x80")
    info: dict[str, Any] = {"file": path.name, "bytes": sz, "sectors_2336": sz // XA_SECTOR_BYTES, "sector_remainder": sz % XA_SECTOR_BYTES}
    if off >= 0 and off + 20 <= len(head):
        magic, chunk_no, cpf, frame_num, sec_bytes, w, h = struct.unpack_from("<IHHIIHH", head, off)
        info.update({"str_offset": off, "magic": f"0x{magic:08x}", "chunk_no": chunk_no, "chunks_per_frame": cpf, "frame_num": frame_num, "sector_payload_bytes": sec_bytes, "width": w, "height": h})
    return info


def build_synthetic_t_archive(slots: dict[int, bytes], total_slots: int | None = None, stamp_checksum: bool = True) -> bytes:
    """Build a valid sector-aligned PS1 .T archive from {slot_index: payload_bytes}."""
    n = total_slots if total_slots is not None else (max(slots.keys(), default=0) + 1)
    hdr_sectors = max(1, ((2 + (n + 1) * 2) + T_SECTOR_BYTES - 1) // T_SECTOR_BYTES)
    cur_sec, offs, bodies = hdr_sectors, [hdr_sectors] * (n + 1), bytearray()
    for idx in range(n):
        offs[idx] = cur_sec
        if idx in slots:
            raw = slots[idx]
            pad = (-len(raw)) % T_SECTOR_BYTES
            blk = bytearray(raw + b"\x00" * pad) if (len(raw) + pad) > 0 else bytearray(T_SECTOR_BYTES)
            if stamp_checksum and len(blk) >= 8:
                words = struct.unpack(f"<{len(blk) // 4 - 1}I", blk[:-4])
                struct.pack_into("<I", blk, len(blk) - 4, (SECTOR_CHECKSUM_SEED + sum(words)) & 0xFFFFFFFF)
            bodies.extend(blk)
            cur_sec += len(blk) // T_SECTOR_BYTES
    offs[n] = cur_sec
    hdr = bytearray(hdr_sectors * T_SECTOR_BYTES)
    struct.pack_into(f"<H{n + 1}H", hdr, 0, n, *offs)
    return bytes(hdr) + bytes(bodies)


def resolve_disc_files_dir(data_dir: Path | None, disc_files: Path | None = None) -> tuple[Path | None, bool]:
    if disc_files is not None:
        return disc_files, True
    if data_dir is not None:
        for cand in (data_dir / "disc" / "files", data_dir / "standalone" / "disc" / "files", data_dir):
            if (cand / "CD").is_dir() or (cand / "SLUS_001.58").is_file():
                return cand, True
        return data_dir, True
    return REPO_ROOT / "Corpus" / "standalone" / "disc" / "files", False


def _build_synthetic_t_summary() -> dict[str, Any]:
    sample_t = build_synthetic_t_archive({0: b"\x00\xfa\x00\x00" + b"\x01" * 2040, 2: b"\x10\x00\x00\x00" + b"\x02" * 60}, total_slots=4)
    fn_raw = b"01 004 045 2\r\n099\r\n000 01   ITEM_A\r\n999 99\r\n\x1a"
    opd_tim = struct.pack("<IIIHHHH", 0x10, 0x02, 12 + 32, 0, 0, 4, 4) + b"\x00" * 32
    opd_raw = opd_tim + struct.pack("<4sIIIHHHHBBBBI", b"pBAV", 6, 0, 256, 0xEEEE, 1, 1, 1, 127, 64, 0, 0, 0xFFFFFFFF)
    with tempfile.TemporaryDirectory() as tmp:
        sp = Path(tmp) / "OP0.S"
        sp.write_bytes(bytes([1, 0, 0x42, 0x80] * 2) + struct.pack("<IHHIIHH", 0x80010160, 0, 9, 1, 1064, 320, 240) + b"\x00" * (XA_SECTOR_BYTES - 28))
        op_str = parse_op_str_header(sp)
    return {"archives": [{"archive": "SYNTH.T", **parse_t_header(sample_t), "sector_checksum_ok": verify_sector_checksum(iter_t_entries(sample_t)[0][3])["valid"]}], "fn_d": decode_fn_d(fn_raw), "op_d": [parse_op_d_container(opd_raw)], "op_streams": [op_str]}


def run_parser(data_dir: Path | None, out_dir: Path | None, log_dir: Path | None, offline_synthetic: bool) -> tuple[int, dict[str, Any]]:
    """Run .T archive, FN.D, and OP/*.D + OP/*.S structural verification."""
    work_dir = (out_dir or (data_dir / "t_archives_parsed" if data_dir is not None else (Path(tempfile.gettempdir()) / "kf_synthetic" / "t_archives" if offline_synthetic else REPO_ROOT / "Corpus" / "work" / "t_archives"))).resolve()
    now_utc = utc_now_iso()
    if not offline_synthetic:
        disc_dir, _ = resolve_disc_files_dir(data_dir)
        com_dir = (disc_dir / "CD" / "COM") if disc_dir else Path("")
        t_files = sorted(com_dir.glob("*.T")) if com_dir.is_dir() else []
        if not t_files and not (disc_dir and (disc_dir / "CD" / "FN.D").is_file()):
            err = {"status": "MISSING_CORPUS_MEDIA", "errorCode": "MISSING_CORPUS_MEDIA", "parser": "kf_t_archives", "dataDir": str(data_dir or work_dir), "required": ["CD/FN.D", "CD/COM/*.T", "OP/*"], "generatedAtUtc": now_utc}
            write_json_log(log_dir, "kf_t_archives", err)
            return 2, err
        archives = [{"archive": tp.name, **{k: v for k, v in parse_t_header(tp.read_bytes()).items() if k != "sector_offsets"}} for tp in t_files]
        fn_res = decode_fn_d((disc_dir / "CD" / "FN.D").read_bytes()) if (disc_dir / "CD" / "FN.D").is_file() else None
        op_dir = disc_dir / "OP"
        op_d = [parse_op_d_container((op_dir / nm).read_bytes()) for nm in ("OP.D", "OPU.D") if (op_dir / nm).is_file()]
        op_s = [parse_op_str_header(p) for p in sorted(op_dir.glob("*.S"))] if op_dir.is_dir() else []
        body = {"archives": archives, "fn_d": fn_res, "op_d": op_d, "op_streams": op_s}
    else:
        body = _build_synthetic_t_summary()
    assert_safe_out_dir(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    out_file = work_dir / "t_archives_report.json"
    out_file.write_text(json.dumps({"status": "OK", "mode": "offline-synthetic" if offline_synthetic else "corpus-media", "generatedAtUtc": now_utc, **body}, indent=2) + "\n", encoding="utf-8")
    summary = {"status": "OK", "mode": "offline-synthetic" if offline_synthetic else "corpus-media", "archive_count": len(body["archives"]), "fn_d_count": body["fn_d"]["count"] if body["fn_d"] else 0, "op_stream_count": len(body["op_streams"]), "output": str(out_file)}
    write_json_log(log_dir, "kf_t_archives", summary)
    return 0, summary


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Parse PS1 .T sector archives, CD/FN.D, and OP/*.D + OP/*.S headers.")
    p.add_argument("--data-dir", type=Path, default=None); p.add_argument("--out-dir", type=Path, default=None)
    p.add_argument("--log-dir", type=Path, default=None); p.add_argument("--offline-synthetic", action="store_true")
    args = p.parse_args(argv)
    code, payload = run_parser(args.data_dir, args.out_dir, args.log_dir, args.offline_synthetic)
    print(json.dumps(payload, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
