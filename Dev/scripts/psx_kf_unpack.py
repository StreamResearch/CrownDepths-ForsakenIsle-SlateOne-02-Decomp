# @module: CrownDepths.Dev.scripts.psx_kf_unpack
# @purpose: Clean-room SLUS-00158 integrity gate and modular orchestrator delegating to kf_* decoders
# @depends-on: argparse, json, struct, sys, tempfile, time, pathlib, kf_*
# @exports: parse_tim_info, parse_and_export_tim, decode_fn_d, unpack_t_archive, unpack_op_assets, unpack_all, verify_required_disc_checksums, main

from __future__ import annotations

import argparse
import json
import struct
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
DEV_DIR = SCRIPTS_DIR.parent
REPO_ROOT = DEV_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from kf_audio_vab_seq import build_synthetic_vab_t, parse_vab_header  # noqa: E402
from kf_audio_vab_seq import parse_seq_header  # noqa: E402
from kf_items_magic_talk import build_synthetic_item_talk  # noqa: E402
from kf_meshes_mo_rtmd import (  # noqa: E402
    build_synthetic_mesh_corpus,
    parse_and_export_tim,
    parse_mo_entry,
    parse_rtim_stream,
    parse_tim_info,
    parse_tmd_header,
    scan_tim_entries,
)
from kf_save_memcard import build_synthetic_mcr_bytes, extract_mcr_saves  # noqa: E402
from kf_t_archives import (  # noqa: E402
    INTEGRITY_SCHEMA_PATH,
    assert_safe_out_dir,
    decode_fn_d as _decode_fn_d_bytes,
    emit_heartbeat,
    iter_t_entries,
    parse_op_d_container,
    parse_op_str_header,
    parse_t_header,
    resolve_disc_files_dir,
    setup_logger,
    sha256_file_chunked,
    utc_now_iso,
    verify_required_disc_checksums,
    write_json_log,
)
from kf_world_fdat import analyze_fdat_archive, build_synthetic_fdat_t  # noqa: E402


def decode_fn_d(fn_d_path: Path, assets_dir: Path) -> dict[str, Any]:
    assert_safe_out_dir(assets_dir)
    assets_dir.mkdir(parents=True, exist_ok=True)
    decoded = _decode_fn_d_bytes(fn_d_path.read_bytes(), include_names=True)
    out_json = assets_dir / "FN_D_items.json"
    out_json.write_text(json.dumps(decoded, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"count": decoded["count"], "json": str(out_json)}


def _classify_chunk(arch_name: str, idx: int, chunk: bytes, out_dir: Path, expect_vb: bool, export_pngs: bool) -> tuple[str, dict[str, Any], bool]:
    stem = f"entry_{idx:04d}"
    if expect_vb:
        return "vb", {"role": "VAB_body_adpcm", "bytes": len(chunk)}, False
    if chunk[:4] == b"pBAV" and (vh := parse_vab_header(chunk)):
        return "vh", vh, True
    if chunk[:4] == b"pQES" and (seq := parse_seq_header(chunk)):
        return "seq", seq, False
    if parse_tim_info(chunk):
        meta = parse_and_export_tim(chunk, out_dir / f"{stem}.png") if export_pngs else {k: v for k, v in (parse_tim_info(chunk) or {}).items() if k != "palette"}
        return "tim", (meta or {}), False
    if tmd := parse_tmd_header(chunk, allow_rtmd=(arch_name == "RTMD.T")):
        return ("rtmd" if arch_name == "RTMD.T" else "tmd"), tmd, False
    if arch_name == "MO.T" and (mo := parse_mo_entry(chunk)):
        return "mo", mo, False
    if arch_name == "RTIM.T":
        return "rtim", parse_rtim_stream(chunk), False
    if arch_name == "FDAT.T" and len(chunk) >= 16:
        return "fdat", {"head_words": [hex(x) for x in struct.unpack_from("<4I", chunk, 0)]}, False
    sub = scan_tim_entries(chunk, out_dir if export_pngs else None, stem) if arch_name in ("TALK.T", "ITEM.T") else []
    return "bin", {"head16": chunk[:16].hex(), "embedded_tims": len(sub)}, False


def unpack_t_archive(t_path: Path, assets_dir: Path, export_pngs: bool = True) -> dict[str, Any]:
    assert_safe_out_dir(assets_dir)
    raw = t_path.read_bytes()
    hdr = parse_t_header(raw)
    out_dir = assets_dir / t_path.name
    out_dir.mkdir(parents=True, exist_ok=True)
    entries, counts, expect_vb = [], {}, False
    active = iter_t_entries(raw)
    start_ts = last_ts = time.monotonic()
    for pos_i, (idx, s0, s1, chunk) in enumerate(active, start=1):
        last_ts = emit_heartbeat(pos_i, len(active), f"Unpacking {t_path.name}", start_ts, last_ts)
        ext, meta, expect_vb = _classify_chunk(t_path.name, idx, chunk, out_dir, expect_vb, export_pngs)
        fpath = out_dir / f"entry_{idx:04d}.{ext}"
        fpath.write_bytes(chunk)
        counts[ext] = counts.get(ext, 0) + 1
        entries.append({"index": idx, "sector_start": s0, "sectors": s1 - s0, "bytes": len(chunk), "ext": ext, "file": fpath.name, "meta": meta})
    manifest = {"archive": t_path.name, "total_slots": hdr["total_slots"], "non_empty_entries": len(entries), "total_bytes": len(raw), "formats": counts, "entries": entries}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return {"archive": t_path.name, "total_slots": hdr["total_slots"], "non_empty": len(entries), "formats": counts, "manifest": str(out_dir / "manifest.json")}


def unpack_op_assets(disc_files_dir: Path, assets_dir: Path, export_pngs: bool = True) -> dict[str, Any]:
    assert_safe_out_dir(assets_dir)
    op_dir = disc_files_dir / "OP"
    op_d_meta = []
    for nm in ("OP.D", "OPU.D"):
        p = op_dir / nm
        if p.is_file():
            raw = p.read_bytes()
            info = parse_op_d_container(raw)
            info["source"] = p.name
            if export_pngs and info["tim_count"] > 0:
                parse_and_export_tim(raw, assets_dir / "OP_TIM" / f"{p.stem}.png")
            op_d_meta.append(info)
    str_results = [parse_op_str_header(p) for p in sorted(op_dir.glob("*.S"))] if op_dir.is_dir() else []
    str_manifest = assets_dir / "OP_STR_manifest.json"
    str_manifest.parent.mkdir(parents=True, exist_ok=True)
    str_manifest.write_text(json.dumps(str_results, indent=2) + "\n", encoding="utf-8")
    return {"op_containers": op_d_meta, "op_streams": str_results, "str_manifest": str(str_manifest)}


def unpack_all(disc_files_dir: Path, assets_dir: Path, export_pngs: bool = True) -> dict[str, Any]:
    """Unpack FN.D, all 7 COM/*.T archives, FDAT master DB summary, and OP/*.D + OP/*.S."""
    assert_safe_out_dir(assets_dir)
    assets_dir.mkdir(parents=True, exist_ok=True)
    summary: dict[str, Any] = {"fn_d": None, "archives": [], "fdat_summary": None, "op": None}
    if (fn_d := disc_files_dir / "CD" / "FN.D").is_file():
        summary["fn_d"] = decode_fn_d(fn_d, assets_dir)
    if (com_dir := disc_files_dir / "CD" / "COM").is_dir():
        for tfile in sorted(com_dir.glob("*.T")):
            summary["archives"].append(unpack_t_archive(tfile, assets_dir, export_pngs=export_pngs))
            if tfile.name == "FDAT.T":
                summary["fdat_summary"] = analyze_fdat_archive(tfile.read_bytes())
    if (disc_files_dir / "OP").is_dir():
        summary["op"] = unpack_op_assets(disc_files_dir, assets_dir, export_pngs=export_pngs)
    (assets_dir / "assets_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def _run_offline_synthetic(data_dir: Path | None, out_dir: Path | None, log_dir: Path | None) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        disc = Path(tmp) / "synthetic_disc" / "files"
        (disc / "CD" / "COM").mkdir(parents=True, exist_ok=True)
        (disc / "OP").mkdir(parents=True, exist_ok=True)
        (disc / "CD" / "FN.D").write_bytes(b"01 004 045 2\r\n099\r\n000 01   ITEM_A\r\n999 99\r\n\x1a")
        item_t, talk_t, _, _ = build_synthetic_item_talk()
        mo_t, rtmd_t, rtim_t = build_synthetic_mesh_corpus()
        (disc / "CD" / "COM" / "FDAT.T").write_bytes(build_synthetic_fdat_t())
        (disc / "CD" / "COM" / "ITEM.T").write_bytes(item_t)
        (disc / "CD" / "COM" / "MO.T").write_bytes(mo_t)
        (disc / "CD" / "COM" / "RTIM.T").write_bytes(rtim_t)
        (disc / "CD" / "COM" / "RTMD.T").write_bytes(rtmd_t)
        (disc / "CD" / "COM" / "TALK.T").write_bytes(talk_t)
        (disc / "CD" / "COM" / "VAB.T").write_bytes(build_synthetic_vab_t())
        (disc / "OP" / "OP.D").write_bytes(struct.pack("<IIIHHHH", 0x10, 0x02, 44, 0, 0, 4, 4) + b"\x00" * 32)
        (disc / "OP" / "OP0.S").write_bytes(bytes([1, 0, 0x42, 0x80] * 2) + struct.pack("<IHHIIHH", 0x80010160, 0, 9, 1, 1064, 320, 240) + b"\x00" * 2308)
        checks = [{"relativePath": f"disc/files/{r}", "expectedSha256": sha256_file_chunked(disc / r), "expectedSizeBytes": (disc / r).stat().st_size, "isRequired": True} for r in ("CD/FN.D", "CD/COM/FDAT.T", "CD/COM/ITEM.T", "CD/COM/MO.T", "CD/COM/RTIM.T", "CD/COM/RTMD.T", "CD/COM/TALK.T", "CD/COM/VAB.T", "OP/OP.D", "OP/OP0.S")]
        gate = verify_required_disc_checksums(disc, checks)
        base_out = data_dir if data_dir is not None else (Path(tempfile.gettempdir()) / "kf_synthetic" / "unpack")
        target_out = (out_dir or (base_out / "extracts" / "assets")).resolve()
        res = unpack_all(disc, target_out, export_pngs=True)
        saves = extract_mcr_saves(build_synthetic_mcr_bytes(slot=1))
        integ = json.loads(INTEGRITY_SCHEMA_PATH.read_text(encoding="utf-8"))
        out = {"status": "OK", "mode": "offline-synthetic", "checksumGateOk": gate["ok"], "schemaRequiredDiscCount": sum(1 for c in integ.get("requiredDiscChecksums", []) if c.get("isRequired", True)), "archivesUnpacked": len(res["archives"]), "saveChecksumsValid": all(s["checksum"]["checksum_valid"] for s in saves), "output": str(target_out / "assets_summary.json")}
        write_json_log(log_dir, "psx_kf_unpack", out)
        return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify SLUS-00158 BYO disc SHA-256 digests and unpack all .T/FN.D/OP assets.")
    parser.add_argument("disc_files", nargs="?", type=Path, default=None, help="Path to extracted disc/files directory.")
    parser.add_argument("--data-dir", type=Path, default=None, help="Isolated BYO media and output data directory.")
    parser.add_argument("--out-dir", type=Path, default=None, help="Output assets directory.")
    parser.add_argument("--log-dir", type=Path, default=None, help="Optional diagnostic log directory.")
    parser.add_argument("--offline-synthetic", action="store_true", help="Run deterministic synthetic unpack with 0 retail media.")
    parser.add_argument("--no-pngs", action="store_true", help="Skip RGBA PNG preview export during .T unpacking.")
    args = parser.parse_args(argv)
    logger = setup_logger(args.log_dir, "psx_kf_unpack")
    if args.offline_synthetic:
        report = _run_offline_synthetic(args.data_dir, args.out_dir, args.log_dir)
        print(json.dumps(report, indent=2))
        return 0 if report["checksumGateOk"] and report["archivesUnpacked"] == 7 else 1

    input_dir, _ = resolve_disc_files_dir(args.data_dir, args.disc_files)
    integ = json.loads(INTEGRITY_SCHEMA_PATH.read_text(encoding="utf-8"))
    gate = verify_required_disc_checksums(input_dir or Path(""), integ.get("requiredDiscChecksums", []), logger=logger)
    if not gate["ok"]:
        err = {"status": gate["status"], "errorCode": gate["status"], "message": "Required SLUS-00158 retail disc media is missing or failed SHA-256 verification.", "dataDir": str(input_dir), "missingFiles": gate["missingFiles"], "mismatchedFiles": gate["mismatchedFiles"], "generatedAtUtc": utc_now_iso()}
        write_json_log(args.log_dir, "psx_kf_unpack", err)
        print(json.dumps(err, indent=2))
        return 2 if gate["status"] == "MISSING_CORPUS_MEDIA" else 1

    base_out = args.data_dir if args.data_dir is not None else (REPO_ROOT / "Corpus" / "work")
    out_dir = (args.out_dir or (base_out / "extracts" / "assets")).resolve()
    res = unpack_all(input_dir, out_dir, export_pngs=not args.no_pngs)
    out = {"status": "OK", "mode": "corpus-media", "archivesUnpacked": len(res["archives"]), "fn_d_count": res["fn_d"]["count"] if res["fn_d"] else 0, "output": str(out_dir / "assets_summary.json")}
    write_json_log(args.log_dir, "psx_kf_unpack", out)
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
