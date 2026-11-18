# @module: CrownDepths.Dev.scripts.tests.test_kf_decomp_cleanroom
# @purpose: Clean-room, spec coverage, SLOC/line limits, integrity schema, and .decomp bundle tests
# @depends-on: json, re, subprocess, sys, tempfile, unittest, zipfile, pathlib
# @exports: validate_cleanroom_tree, TestKfDecompCleanroom

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
DEV_DIR = SCRIPTS_DIR.parent
REPO_ROOT = DEV_DIR.parent
SCHEMAS_DIR = DEV_DIR / "schemas"
DOCS_DIR = DEV_DIR / "docs"

FORBIDDEN_EXTS = {
    ".bin", ".iso", ".cue", ".chd", ".img", ".mdf", ".mds", ".pbp", ".ecm",
    ".rom", ".n64", ".z64", ".v64", ".nes", ".sfc", ".smc", ".gb", ".gbc", ".gba",
    ".sav", ".srm", ".state", ".mcr", ".mcd", ".tim", ".tmd", ".vab", ".seq", ".vag",
    ".xa", ".str", ".gdt", ".til", ".exe", ".gpr", ".7z", ".zip",
}
FORBIDDEN_SUFFIXES = (".g.cs", ".generated.dll")
FORBIDDEN_TEXT_TOKENS = ("ghidra_" + "psx_ldr", "GNU General " + "Public License")
FORBIDDEN_PATH_TOKENS = (
    "ghidra_" + "psx_ldr",
    "lib" + "gpu.h", "lib" + "gte.h", "lib" + "gs.h", "lib" + "cd.h",
    "lib" + "spu.h", "lib" + "sn.h", "lib" + "snd.h", "lib" + "etc.h", "lib" + "api.h",
)
PSX_MAGIC = ("PS-X " + "EXE").encode("ascii")


def validate_cleanroom_tree(root: Path) -> list[str]:
    """Validate directory entries against PsxCleanRoomValidator clean-room boundaries."""
    violations: list[str] = []
    for fp in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = fp.relative_to(root).as_posix()
        low = rel.lower()
        if fp.suffix.lower() in FORBIDDEN_EXTS or low.endswith(FORBIDDEN_SUFFIXES):
            violations.append(f"ext:{rel}")
            continue
        if any(tok in low for tok in FORBIDDEN_PATH_TOKENS):
            violations.append(f"path_token:{rel}")
            continue
        head = fp.read_bytes()[:8]
        if head.startswith(PSX_MAGIC) or head.startswith(b"RST" + b"1"):
            violations.append(f"magic:{rel}")
            continue
        if fp.suffix.lower() in (".py", ".c", ".h", ".json", ".md", ".xml") and fp.stat().st_size <= 2 * 1024 * 1024:
            txt = fp.read_text(encoding="utf-8", errors="replace").lower()
            if any(tok.lower() in txt for tok in FORBIDDEN_TEXT_TOKENS):
                violations.append(f"text_token:{rel}")
    return violations


class TestKfDecompCleanroom(unittest.TestCase):
    """Verify spec_coverage.json (96/96), spoke bounds, Python SLOC, integrity schema, and .decomp pack."""

    def test_spec_coverage_and_six_spokes_contract(self) -> None:
        cov_path = SCHEMAS_DIR / "spec_coverage.json"
        self.assertTrue(cov_path.is_file(), "Missing Dev/schemas/spec_coverage.json")
        cov = json.loads(cov_path.read_text(encoding="utf-8"))
        self.assertEqual(cov["schemaVersion"], 2)
        self.assertEqual(cov["gameId"], "kings-field")
        self.assertEqual((cov["totalFieldCount"], cov["mappedFieldCount"], cov["unresolvedFieldCount"]), (96, 96, 0))
        self.assertIs(cov["isPassed"], True)
        self.assertNotIn("passed", cov)
        self.assertNotIn("unresolvedFields", cov)
        self.assertEqual(len(cov["specifications"]), 6)

        index_md = (DOCS_DIR / "SPECIFICATIONS.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(index_md.splitlines()), 400)
        self.assertNotIn("file" + "://", index_md.lower())
        self.assertIn("spec_coverage.json", index_md)

        total = 0
        for item in cov["specifications"]:
            self.assertNotIn("passed", item)
            self.assertNotIn("unresolvedFields", item)
            self.assertIs(item["isPassed"], True)
            self.assertEqual(item["unresolvedFieldCount"], 0)
            self.assertEqual((item["fieldCount"], item["mappedFieldCount"], len(item["fields"])), (16, 16, 16))
            doc_p, scr_p = REPO_ROOT / item["docPath"], REPO_ROOT / item["parserScript"]
            self.assertTrue(doc_p.is_file(), f"Missing spoke {doc_p}")
            self.assertTrue(scr_p.is_file(), f"Missing parser {scr_p}")
            lines = doc_p.read_text(encoding="utf-8").splitlines()
            self.assertGreaterEqual(len(lines), 150, f"{doc_p.name} {len(lines)} < 150")
            self.assertLessEqual(len(lines), 380, f"{doc_p.name} {len(lines)} > 380")
            self.assertIn(doc_p.name, index_md)
            total += int(item["mappedFieldCount"])
        self.assertEqual(total, 96)

    def test_scripts_and_tests_sloc_and_raw_line_limits(self) -> None:
        owned_py = [
            SCRIPTS_DIR / "psx_kf_unpack.py",
            SCRIPTS_DIR / "kf_t_archives.py",
            SCRIPTS_DIR / "kf_world_fdat.py",
            SCRIPTS_DIR / "kf_items_magic_talk.py",
            SCRIPTS_DIR / "kf_meshes_mo_rtmd.py",
            SCRIPTS_DIR / "kf_audio_vab_seq.py",
            SCRIPTS_DIR / "kf_save_memcard.py",
            SCRIPTS_DIR / "export_decomp_bundle.py",
            SCRIPTS_DIR / "materialize_decomp_tiers.py",
            TESTS_DIR / "test_kf_parsers.py",
            TESTS_DIR / "test_kf_decomp_cleanroom.py",
        ]
        for py in owned_py:
            self.assertTrue(py.is_file(), f"Missing {py}")
            lines = py.read_text(encoding="utf-8").splitlines()
            sloc = sum(1 for ln in lines if ln.strip() and not ln.strip().startswith("#"))
            self.assertLessEqual(len(lines), 400, f"{py.name} raw lines {len(lines)} > 400")
            self.assertLessEqual(sloc, 250, f"{py.name} code SLOC {sloc} > 250")

    def test_cleanroom_spokes_scripts_and_integrity_zero_leaks(self) -> None:
        win_path_re = re.compile(r"[A-Za-z]:[/\\]+(?:Users|Projects|Programs|Python)", re.IGNORECASE)
        uuid_re = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE)
        vendor_word = "Psy" + "Q"
        targets = [
            DOCS_DIR / "SPECIFICATIONS.md",
            *(DOCS_DIR / "specifications").glob("*.md"),
            SCRIPTS_DIR / "psx_kf_unpack.py",
            SCRIPTS_DIR / "kf_t_archives.py",
            SCRIPTS_DIR / "kf_world_fdat.py",
            SCRIPTS_DIR / "kf_items_magic_talk.py",
            SCRIPTS_DIR / "kf_meshes_mo_rtmd.py",
            SCRIPTS_DIR / "kf_audio_vab_seq.py",
            SCRIPTS_DIR / "kf_save_memcard.py",
            SCRIPTS_DIR / "materialize_decomp_tiers.py",
            TESTS_DIR / "test_kf_parsers.py",
            TESTS_DIR / "test_kf_decomp_cleanroom.py",
            SCHEMAS_DIR / "spec_coverage.json",
            SCHEMAS_DIR / "standalone_integrity.json",
        ]
        for fp in targets:
            txt = fp.read_text(encoding="utf-8")
            self.assertNotIn("file" + "://", txt.lower(), f"file URI in {fp.name}")
            self.assertIsNone(win_path_re.search(txt), f"workstation path in {fp.name}")
            self.assertIsNone(uuid_re.search(txt), f"UUID leak in {fp.name}")
            self.assertNotIn(vendor_word.lower(), txt.lower(), f"vendor SDK brand in {fp.name}")
        self.assertEqual(validate_cleanroom_tree(DOCS_DIR / "specifications"), [])
        self.assertEqual(validate_cleanroom_tree(TESTS_DIR), [])

        integ = json.loads((SCHEMAS_DIR / "standalone_integrity.json").read_text(encoding="utf-8"))
        self.assertEqual(integ["schemaVersion"], 2)
        self.assertEqual(sum(1 for e in integ["requiredDiscChecksums"] if e.get("isRequired", True)), 23)
        self.assertNotIn(".gpr", json.dumps(integ).lower())

        cg = json.loads((SCHEMAS_DIR / "call_graph.json").read_text(encoding="utf-8"))
        funcs = cg.get("functions", {})
        self.assertFalse(any(bool(v.get("strings")) for v in funcs.values() if isinstance(v, dict)))
        for hp in (SCHEMAS_DIR / "types").glob("*.h"):
            self.assertNotIn(vendor_word.lower(), hp.read_text(encoding="utf-8").lower(), f"vendor SDK brand in {hp.name}")
        ws_file = SCHEMAS_DIR.parent / "CrownDepths-ForsakenIsle-SlateOne-02-Decomp.code-workspace"
        self.assertTrue(ws_file.is_file(), "Coded .code-workspace file missing")
        self.assertFalse((SCHEMAS_DIR.parent / "KingsField-PlayStation.code-workspace").exists(), "Legacy .code-workspace must stay deleted")
        ws_paths = [f.get("path", "") for f in json.loads(ws_file.read_text(encoding="utf-8")).get("folders", [])]
        self.assertEqual(len(ws_paths), 9)
        for tier in ("D1_Raw", "D2_Structured", "D3_Mapped"):
            self.assertIn(f"../Corpus/tiers/{tier}", ws_paths)
        self.assertTrue(any(f"../Corpus/tiers/{d4}" in ws_paths for d4 in ("D4_CleanSource", "D4_FunctionalRewrite")), "Missing D4_CleanSource tier folder in .code-workspace")
        for ext in ("svg", "png", "ico"):
            self.assertTrue((DEV_DIR / "assets" / f"CrownDepths-ForsakenIsle-SlateOne-02-Decomp.{ext}").is_file())
        tm_rx = re.compile(r"(?:king'?s\s+field|play\s*station)", re.I)
        for doc_name in ("README.md", "FEATURES.md", "ROADMAP.md", "CHANGELOG.md", "SECURITY.md", "CONTRIBUTING.md"):
            txt = (REPO_ROOT / doc_name).read_text(encoding="utf-8")
            body = txt.split("## License & Legal", 1)[0] if doc_name == "README.md" else txt
            self.assertIsNone(tm_rx.search(body), f"Trademark outside License & Legal in {doc_name}")

    def test_cleanroom_validator_rejects_synthetic_violations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            (td / "ok.json").write_text("{}\n", encoding="utf-8")
            self.assertEqual(validate_cleanroom_tree(td), [])
            (td / "bad.tim").write_bytes(b"\x10\x00\x00\x00")
            (td / "fake.c").write_bytes(PSX_MAGIC + b"\x00" * 16)
            (td / "leak.py").write_text("# " + FORBIDDEN_TEXT_TOKENS[0] + "\n", encoding="utf-8")
            self.assertEqual(len(validate_cleanroom_tree(td)), 3)

    def test_export_decomp_bundle_cleanroom_and_determinism(self) -> None:
        exporter_p = SCRIPTS_DIR / "export_decomp_bundle.py"
        recipe_p = SCHEMAS_DIR / "decomp_recipe.json"
        self.assertTrue(exporter_p.is_file() and recipe_p.is_file())
        recipe = json.loads(recipe_p.read_text(encoding="utf-8"))
        for key in ("moduleId", "title", "packageFileName", "platformId", "engineId", "engineVersion", "compatibleEngineTrack", "decompSchemaVersion", "targetDecompTier", "goalDecompTier", "preloadRomDir", "recipeEntryPoint"):
            self.assertTrue(recipe.get(key), f"Missing {key}")
        self.assertRegex(recipe["moduleId"], r"^[a-z0-9][a-z0-9-]*$")
        for tok in ("king", "field", "play" + "station"):
            self.assertNotIn(tok, recipe["moduleId"].lower())
            self.assertNotIn(tok, recipe["title"].lower())
            self.assertNotIn(tok, recipe["packageFileName"].lower())

        with tempfile.TemporaryDirectory() as tmp:
            out_a = Path(tmp) / "test_a.decomp"
            out_b = Path(tmp) / "test_b.decomp"
            logs = Path(tmp) / "logs"
            for out_p in (out_a, out_b):
                res = subprocess.run([sys.executable, "-B", str(exporter_p), "--out", str(out_p), "--verify-cleanroom", "--strict", "--log-dir", str(logs)], capture_output=True, text=True, timeout=60)
                self.assertEqual(res.returncode, 0, f"export_decomp_bundle failed: {res.stdout}\n{res.stderr}")
                self.assertTrue(out_p.is_file())
            self.assertEqual(out_a.read_bytes(), out_b.read_bytes())
            with zipfile.ZipFile(out_a, "r") as zf:
                names = set(zf.namelist())
                self.assertIn("module.decomp.json", names)
                self.assertIn("Dev/scripts/psx_kf_unpack.py", names)
                self.assertFalse(any(n.lower().endswith(tuple(FORBIDDEN_EXTS)) for n in names))


if __name__ == "__main__":
    unittest.main()
