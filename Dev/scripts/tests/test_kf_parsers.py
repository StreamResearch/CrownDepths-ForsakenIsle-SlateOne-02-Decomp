# @module: CrownDepths.Dev.scripts.tests.test_kf_parsers
# @purpose: Isolated synthetic unit & CLI tests for psx_kf_unpack and all 6 modular KF decoders
# @depends-on: json, struct, subprocess, sys, tempfile, unittest, pathlib
# @exports: TestKfParsers

from __future__ import annotations

import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import kf_audio_vab_seq  # noqa: E402
import kf_items_magic_talk  # noqa: E402
import kf_meshes_mo_rtmd  # noqa: E402
import kf_save_memcard  # noqa: E402
import kf_t_archives  # noqa: E402
import kf_world_fdat  # noqa: E402
import psx_kf_unpack  # noqa: E402


class TestKfParsers(unittest.TestCase):
    """Verify synthetic parser invariants, VAB.T header fix, FDAT[48], and fail-closed CLI behavior."""

    def test_cli_offline_synthetic_and_fail_closed_all_scripts(self) -> None:
        scripts = (
            "kf_t_archives.py",
            "kf_world_fdat.py",
            "kf_items_magic_talk.py",
            "kf_meshes_mo_rtmd.py",
            "kf_audio_vab_seq.py",
            "kf_save_memcard.py",
            "psx_kf_unpack.py",
            "materialize_decomp_tiers.py",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            empty_dir, log_dir = root / "empty", root / "logs"
            empty_dir.mkdir()
            for script in scripts:
                res_empty = subprocess.run([sys.executable, "-B", str(SCRIPTS_DIR / script), "--data-dir", str(empty_dir), "--log-dir", str(log_dir)], capture_output=True, text=True, timeout=30)
                self.assertNotEqual(res_empty.returncode, 0, f"{script} must fail closed on empty --data-dir")
                err = json.loads(res_empty.stdout)
                self.assertEqual(err["status"], "MISSING_CORPUS_MEDIA")
                self.assertEqual(err["errorCode"], "MISSING_CORPUS_MEDIA")

                out_dir = root / script.removesuffix(".py")
                res_syn = subprocess.run([sys.executable, "-B", str(SCRIPTS_DIR / script), "--data-dir", str(out_dir), "--log-dir", str(log_dir), "--offline-synthetic"], capture_output=True, text=True, timeout=30)
                self.assertEqual(res_syn.returncode, 0, f"{script} failed: {res_syn.stdout}\n{res_syn.stderr}")
                syn = json.loads(res_syn.stdout)
                self.assertEqual(syn["status"], "OK")
                self.assertEqual(syn["mode"], "offline-synthetic")
                if "output" in syn:
                    self.assertTrue(Path(syn["output"]).is_file())
                else:
                    self.assertEqual(len(syn.get("tiers", {})), 4)

    def test_vab_header_fixed_unpack_and_seq_parsing(self) -> None:
        vab_raw = kf_audio_vab_seq.build_synthetic_vab_t()
        parsed = kf_audio_vab_seq.analyze_vab_archive(vab_raw)
        self.assertEqual(parsed["vab_count"], 1)
        self.assertEqual(parsed["seq_count"], 1)
        self.assertTrue(parsed["all_programs_lt_128"])
        v0 = parsed["vabs"][0]
        self.assertEqual((v0["version"], v0["vab_id"], v0["programs"], v0["tones"], v0["vags"]), (6, 0, 2, 23, 22))
        self.assertLess(v0["programs"], 128)
        self.assertEqual(v0["reserved_sys"], "0xeeee")
        self.assertEqual((v0["master_vol"], v0["master_pan"]), (127, 64))
        self.assertEqual(v0["vag_table_count"], 22)
        self.assertEqual(v0["vag_table_total_bytes"], v0["vb_declared_bytes"])
        self.assertTrue(v0["vb_size_ok"])
        self.assertTrue(v0["checksum_ok"])
        self.assertEqual(parsed["seqs"][0]["resolution_ppqn"], 480)
        self.assertEqual(parsed["seqs"][0]["rhythm"], "4/4")

    def test_fdat_48_nine_sections_zones_and_viewmodels(self) -> None:
        fdat_raw = kf_world_fdat.build_synthetic_fdat_t()
        parsed = kf_world_fdat.analyze_fdat_archive(fdat_raw)
        self.assertEqual(parsed["zone_count"], 1)
        z0 = parsed["zones"][0]
        self.assertTrue(z0["map_cells_expected"])
        self.assertEqual(z0["non_empty_cells"], 100)
        self.assertTrue(z0["slot1_sizes_expected"])
        self.assertTrue(z0["checksums_ok"])
        f48 = parsed["fdat_48_master_db"]
        self.assertEqual(f48["section_count"], 9)
        self.assertEqual(tuple(f48["section_sizes"]), kf_world_fdat.FDAT48_EXPECTED_SIZES)
        self.assertTrue(f48["sizes_match_expected"])
        self.assertEqual(f48["map_obj_def_count"], 320)
        self.assertEqual(f48["magic_def_count"], 18)
        self.assertEqual(f48["item_def_count"], 64)
        self.assertEqual(f48["level_growth_count"], 100)
        self.assertEqual(f48["level_growth_sample"][0]["hp"], 50)
        self.assertEqual(parsed["weapon_viewmodel_count"], 1)
        self.assertEqual(parsed["fdat_47_vram"]["block_count"], 1)

    def test_items_talk_meshes_and_t_sector_checksum(self) -> None:
        item_t, talk_t, sec1, sec2 = kf_items_magic_talk.build_synthetic_item_talk()
        item_res = kf_items_magic_talk.parse_item_t(item_t)
        talk_res = kf_items_magic_talk.parse_talk_t(talk_t)
        self.assertEqual((item_res["tmd_count"], item_res["tim_count"]), (1, 1))
        self.assertEqual((talk_res["card_count"], talk_res["checksum_valid_count"]), (1, 1))
        self.assertEqual(kf_items_magic_talk.decode_magic_defs(sec1)["count"], 18)
        self.assertEqual(len(kf_items_magic_talk.decode_item_defs(sec2)), 64)

        mo_t, rtmd_t, rtim_t = kf_meshes_mo_rtmd.build_synthetic_mesh_corpus()
        mo_entries = kf_t_archives.iter_t_entries(mo_t)
        self.assertEqual(kf_meshes_mo_rtmd.parse_mo_entry(mo_entries[0][3])["variant"], "animated_mo")
        self.assertEqual(kf_meshes_mo_rtmd.parse_mo_entry(mo_entries[1][3])["variant"], "static_mo_tmd")
        self.assertTrue(kf_t_archives.verify_sector_checksum(mo_entries[0][3])["valid"])
        rtmd_entries = kf_t_archives.iter_t_entries(rtmd_t)
        self.assertEqual(kf_meshes_mo_rtmd.parse_tmd_header(rtmd_entries[0][3], allow_rtmd=True)["kind"], "rtmd")
        rtim_entries = kf_t_archives.iter_t_entries(rtim_t)
        self.assertEqual(kf_meshes_mo_rtmd.parse_rtim_stream(rtim_entries[0][3])["block_count"], 2)

    def test_save_memcard_checksum_and_tamper_detection(self) -> None:
        mcr = kf_save_memcard.build_synthetic_mcr_bytes(slot=2, cur_map=5, level=21, hp=310, mp=140, gold=9876, xp=12345)
        slots = kf_save_memcard.extract_mcr_saves(mcr)
        self.assertEqual(len(slots), 1)
        s0 = slots[0]
        self.assertTrue(s0["dir_xor_valid"])
        self.assertTrue(s0["checksum"]["checksum_valid"])
        self.assertEqual(s0["slot_name"], "BASLUS-001582")
        self.assertEqual((s0["state"]["cur_map"], s0["state"]["level"], s0["state"]["gold"]), (5, 21, 9876))
        self.assertEqual(s0["header"]["sjis_level"], 21)

        bad_payload = bytearray(mcr[0x2000:0x6000])
        bad_payload[0x405] ^= 0x01
        self.assertFalse(kf_save_memcard.decode_save_slot(bytes(bad_payload))["checksum"]["checksum_valid"])

        bad_mcr = bytearray(mcr)
        bad_mcr[0x85] ^= 0x01
        self.assertFalse(kf_save_memcard.extract_mcr_saves(bytes(bad_mcr))[0]["dir_xor_valid"])

    def test_psx_kf_unpack_synthetic_roundtrip_and_safe_out_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "unpack_out"
            res = psx_kf_unpack._run_offline_synthetic(out, None, Path(tmp) / "logs")
            self.assertTrue(res["checksumGateOk"])
            self.assertEqual(res["archivesUnpacked"], 7)
            self.assertTrue(res["saveChecksumsValid"])
            summary = json.loads(Path(res["output"]).read_text(encoding="utf-8"))
            self.assertEqual(summary["fn_d"]["count"], 2)
            self.assertEqual(summary["fdat_summary"]["fdat_48_master_db"]["section_count"], 9)
            png_files = list((out / "extracts" / "assets").rglob("*.png"))
            self.assertTrue(png_files and png_files[0].read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
        with self.assertRaises(ValueError):
            kf_t_archives.assert_safe_out_dir(SCRIPTS_DIR)


if __name__ == "__main__":
    unittest.main()
