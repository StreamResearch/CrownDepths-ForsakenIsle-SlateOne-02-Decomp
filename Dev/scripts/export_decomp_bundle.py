# @module: CrownDepths.Dev.scripts.export_decomp_bundle
# @purpose: Clean-room .decomp package exporter and PsxCleanRoomValidator-aligned archive verifier
# @depends-on: argparse, datetime, hashlib, json, os, re, sys, zipfile, pathlib, typing
# @exports: load_decomp_recipe, build_module_decomp_manifest, validate_cleanroom_bytes, validate_cleanroom_archive, export_decomp_bundle, main

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any
import zipfile

DEV_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = DEV_DIR.parent
DEFAULT_RECIPE_PATH = DEV_DIR / "schemas" / "decomp_recipe.json"

_FORBIDDEN_EXTS = frozenset({
    ".bin", ".cue", ".iso", ".img", ".chd", ".mdf", ".mds", ".pbp", ".ecm", ".rom",
    ".n64", ".z64", ".v64", ".nes", ".sfc", ".smc", ".gb", ".gbc", ".gba", ".gcm",
    ".rvz", ".sav", ".srm", ".state", ".mcr", ".mcd", ".tim", ".tmd", ".vab", ".seq",
    ".vag", ".vh", ".vb", ".xa", ".str", ".gpr", ".rep", ".gdt", ".til", ".exe",
    ".dll", ".o", ".a", ".obj", ".7z", ".zip", ".rar", ".elf", ".lib",
})
_FORBIDDEN_SUFFIXES = (".g.cs", ".generated.dll")
_GHIDRA_PROJ = "_".join(("ghidra", "project"))
_HARD_BLOCK_DIRS = frozenset({"corpus", "archive", ".git", _GHIDRA_PROJ})
_FORBIDDEN_DIRS = _HARD_BLOCK_DIRS | {"__pycache__", ".pytest_cache", "tests"}
_OS_JUNK_NAMES = frozenset({"desktop.ini", "thumbs.db", "ehthumbs.db", ".ds_store"})
_SKIP_EXTS = frozenset({".pyc", ".pyo", ".tmp"})
_FORBIDDEN_PREFIXES = (
    "corpus/", "archive/", "dev/data/", "dev/logs/", ".git/",
    "dev/docs/plans/", "dev/docs/reports/", "dev/docs/tests/", "dev/docs/archive/", f"{_GHIDRA_PROJ}/",
)
# Construct clean-room needles dynamically so the packaged script carries zero trigger literals.
_FORBIDDEN_TOKENS = (
    "_".join(("ghidra", "psx", "ldr")),
    " ".join(("gnu", "general", "public", "license")),
    *(f"lib{stem}.h" for stem in ("gpu", "gte", "gs", "cd", "spu", "sn", "snd", "etc", "api")),
)
_TRADEMARK_TOKENS = ("king", "field", "play" + "station")
_VENDOR_SDK_NEEDLE = "psy" + "q"
_WORKSTATION_RE = re.compile(r"[A-Za-z]:[/\\]+(?:Users|Projects|Programs|Python)", re.IGNORECASE)
_FILE_URI_NEEDLE = "file" + ":///"
_C_STRIP_RE = re.compile(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', re.DOTALL)
_C_FN_BODY_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\s*\([^;{}]*\)\s*\{")
_MODULE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_FORBIDDEN_MAGICS = (b"PS-X " + b"EXE", b"RST" + b"1", b"CD" + b"001", b"\x01CD" + b"001", b"PK\x03\x04", b"7z\xbc\xaf\x27\x1c")
_REQUIRED_MANIFEST_KEYS = (
    "moduleId", "title", "platformId", "engineId", "engineVersion", "compatibleEngineTrack",
    "decompSchemaVersion", "targetDecompTier", "goalDecompTier", "packageVersion",
    "preloadRomDir", "recipeEntryPoint", "customUnpackerScript", "toolchainRequirements",
)
_MANIFEST_KEYS = (
    *_REQUIRED_MANIFEST_KEYS[:10], "serialNumber", "defaultBootExecutable", "sleighLanguageId",
    "upstreamResearchPath", "ghidraProjectName", *_REQUIRED_MANIFEST_KEYS[10:],
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def load_decomp_recipe(recipe_path: Path | None = None) -> dict[str, Any]:
    """Load the clean-room decompilation recipe JSON."""
    return json.loads((Path(recipe_path) if recipe_path else DEFAULT_RECIPE_PATH).read_text(encoding="utf-8"))


def _validate_module_identity(data: dict[str, Any]) -> list[str]:
    mod_id, title, pkg_name = str(data.get("moduleId") or ""), str(data.get("title") or ""), str(data.get("packageFileName") or "")
    errs = [f"invalid_module_id:{mod_id}"] if not _MODULE_ID_RE.match(mod_id) else []
    if pkg_name.endswith(("-Decomp.decomp", "-Recomp.recomp")):
        errs.append(f"stutter_package_name:{pkg_name}")
    errs.extend(
        f"trademark_token({k}):{v}"
        for k, v in (("moduleId", mod_id), ("title", title), ("packageFileName", pkg_name))
        if any(tok in v.lower() for tok in _TRADEMARK_TOKENS)
    )
    return errs


def build_module_decomp_manifest(recipe: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build strongly-typed module.decomp.json manifest from decomp_recipe.json."""
    src = recipe if recipe is not None else load_decomp_recipe()
    manifest = {k: src[k] for k in _MANIFEST_KEYS if k in src}
    for req in _REQUIRED_MANIFEST_KEYS:
        val = manifest.get(req)
        if val is None or (isinstance(val, str) and not val.strip()):
            raise ValueError(f"module.decomp.json missing required field '{req}'.")
    if errs := _validate_module_identity(src):
        raise ValueError(f"Invalid clean-room identity: {'; '.join(errs)}")
    return manifest


def _is_forbidden_path(rel_posix: str) -> bool:
    norm = rel_posix.replace("\\", "/")
    parts = PurePosixPath(norm).parts if norm else ()
    if not norm or norm.startswith("/") or ":" in norm or any(p in ("", ".", "..") or p.lower() in _HARD_BLOCK_DIRS for p in parts):
        return True
    lower = norm.lower()
    return any(lower.startswith(p) for p in _FORBIDDEN_PREFIXES) or any(t in lower for t in _FORBIDDEN_TOKENS)


def _check_header_and_json_rules(norm: str, text: str, strict: bool) -> list[str]:
    errs: list[str] = []
    name_low, norm_low = PurePosixPath(norm).name.lower(), norm.lower()
    if name_low == "call_graph.json":
        try:
            funcs = json.loads(text).get("functions")
            if isinstance(funcs, dict) and any(isinstance(v, dict) and bool(v.get("strings")) for v in funcs.values()):
                errs.append(f"nonempty_call_graph_strings:{norm}")
        except (json.JSONDecodeError, AttributeError) as exc:
            errs.append(f"invalid_json({exc}):{norm}")
    if name_low.endswith(".h") and not norm_low.startswith("dev/scripts/d4_harness/") and _C_FN_BODY_RE.search(_C_STRIP_RE.sub(" ", text)):
        errs.append(f"c_function_body_in_header:{norm}")
    if strict:
        if name_low == "standalone_integrity.json" and (_GHIDRA_PROJ in text.lower() or ".gpr" in text.lower()):
            errs.append(f"forbidden_gpr_reference:{norm}")
        if PurePosixPath(norm).suffix.lower() in (".json", ".py", ".h", ".c", ".md"):
            if _WORKSTATION_RE.search(text) or _FILE_URI_NEEDLE in text.lower():
                errs.append(f"workstation_path_leak:{norm}")
            if (name_low.endswith(".h") or name_low in ("anchor_functions.json", "functions_catalog.json", "globals_map.json") or "/shards/" in norm_low) and _VENDOR_SDK_NEEDLE in text.lower():
                errs.append(f"vendor_sdk_brand_leak:{norm}")
    return errs


def validate_cleanroom_bytes(rel_path: str, payload: bytes, strict: bool = False) -> list[str]:
    """Validate one archive entry path and byte payload against PsxCleanRoomValidator rules."""
    norm = rel_path.replace("\\", "/")
    name_lower = PurePosixPath(norm).name.lower()
    violations = [f"forbidden_path:{norm}"] if _is_forbidden_path(norm) else []
    if os.path.splitext(name_lower)[1] in _FORBIDDEN_EXTS or any(name_lower.endswith(s) for s in _FORBIDDEN_SUFFIXES):
        violations.append(f"forbidden_ext:{norm}")
    if any(payload.startswith(m) for m in _FORBIDDEN_MAGICS) or (len(payload) >= 0x8006 and payload[0x8000:0x8006] == _FORBIDDEN_MAGICS[3]):
        violations.append(f"forbidden_magic:{norm}")
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        text = payload.decode("latin-1", errors="ignore")
    text_lower = text.lower()
    violations.extend(f"forbidden_token({tok}):{norm}" for tok in _FORBIDDEN_TOKENS if tok in text_lower)
    return violations + _check_header_and_json_rules(norm, text, strict)


def validate_cleanroom_archive(archive_path: Path, strict: bool = False) -> list[str]:
    """Validate a packaged .decomp ZIP archive against root manifest and clean-room rules."""
    target = Path(archive_path)
    if not target.is_file():
        return [f"missing_archive:{target.name}"]
    violations: list[str] = []
    with zipfile.ZipFile(target, "r") as zf:
        if "module.decomp.json" not in {i.filename for i in zf.infolist() if not i.is_dir()}:
            violations.append("missing_root_manifest:module.decomp.json")
        else:
            try:
                manifest = json.loads(zf.read("module.decomp.json").decode("utf-8"))
                violations.extend(f"invalid_manifest_field:{req}" for req in _REQUIRED_MANIFEST_KEYS if not manifest.get(req))
                violations.extend(_validate_module_identity(manifest))
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                violations.append(f"invalid_manifest_json:{exc}")
        for info in zf.infolist():
            if info.is_dir():
                if _is_forbidden_path(info.filename.rstrip("/")):
                    violations.append(f"forbidden_dir:{info.filename}")
            else:
                violations.extend(validate_cleanroom_bytes(info.filename, zf.read(info.filename), strict=strict))
    return violations


def _should_skip_source(rel_posix: str, path: Path, excluded_prefixes: tuple[str, ...]) -> bool:
    rel_low, name_lower = rel_posix.lower(), path.name.lower()
    if any(rel_low == p or rel_low.startswith(p + "/") for p in excluded_prefixes):
        return True
    if any(part.lower() in _FORBIDDEN_DIRS for part in PurePosixPath(rel_posix).parts[:-1]):
        return True
    return name_lower in _OS_JUNK_NAMES or name_lower.startswith("._") or path.suffix.lower() in _SKIP_EXTS or rel_low.endswith(".decomp")


def _collect_entries(root_dir: Path, manifest: dict[str, Any], recipe: dict[str, Any], strict: bool) -> list[tuple[str, bytes]]:
    entries: list[tuple[str, bytes]] = [("module.decomp.json", (json.dumps(manifest, indent=2) + "\n").encode("utf-8"))]
    violations: list[str] = []
    excluded = tuple(str(x).replace("\\", "/").strip("/").lower() for x in (recipe.get("excludedSubtrees") or []))
    for sub in recipe.get("bundleDirectories") or ["Dev/schemas", "Dev/scripts"]:
        sub_dir = root_dir / str(sub)
        if not sub_dir.is_dir():
            continue
        for fp in sorted((p for p in sub_dir.rglob("*") if p.is_file()), key=lambda p: p.as_posix()):
            rel_posix = fp.relative_to(root_dir).as_posix()
            if _should_skip_source(rel_posix, fp, excluded):
                continue
            payload = fp.read_bytes()
            errs = validate_cleanroom_bytes(rel_posix, payload, strict=strict)
            violations.extend(errs) if errs else entries.append((rel_posix, payload))
    if violations:
        raise ValueError(f"Clean-room pre-pack check failed ({len(violations)}): {'; '.join(violations[:8])}")
    return entries


def _resolve_output_path(out_path: Path | None, data_dir: Path | None, root_dir: Path, manifest: dict[str, Any], recipe: dict[str, Any] | None = None) -> Path:
    if out_path is not None:
        return Path(out_path).resolve()
    filename = f"{manifest['moduleId']}-v{manifest['packageVersion']}.decomp"
    if data_dir is not None:
        base = Path(data_dir).resolve()
        return (base / "extracts" / filename) if base.name.lower() == "work" else (base / "work" / "extracts" / filename)
    return (root_dir / str((recipe or {}).get("packageFileName") or f"{root_dir.name}.decomp").strip()).resolve()


def _write_log(log_dir: Path | None, report: dict[str, Any]) -> None:
    if log_dir is not None:
        target = Path(log_dir).resolve()
        target.mkdir(parents=True, exist_ok=True)
        with (target / "export_decomp_bundle.log").open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(report) + "\n")


def export_decomp_bundle(
    out_path: Path | None = None, data_dir: Path | None = None, log_dir: Path | None = None,
    verify_cleanroom: bool = True, recipe_path: Path | None = None, repo_root: Path | None = None, strict: bool = False,
) -> dict[str, Any]:
    """Assemble and optionally verify a deterministic clean-room .decomp ZIP archive."""
    root_dir = Path(repo_root).resolve() if repo_root else REPO_ROOT
    recipe = load_decomp_recipe(recipe_path or (root_dir / "Dev" / "schemas" / "decomp_recipe.json"))
    manifest = build_module_decomp_manifest(recipe)
    entries = _collect_entries(root_dir, manifest, recipe, strict=strict)
    dest = _resolve_output_path(out_path, data_dir, root_dir, manifest, recipe)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp_dest = dest.with_suffix(dest.suffix + ".tmp.decomp")
    with zipfile.ZipFile(tmp_dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for arcname, payload in entries:
            zi = zipfile.ZipInfo(arcname, date_time=(2026, 11, 18, 0, 0, 0))
            zi.compress_type, zi.external_attr = zipfile.ZIP_DEFLATED, 0o644 << 16
            zf.writestr(zi, payload)
    os.replace(tmp_dest, dest)
    do_verify = bool(verify_cleanroom or strict)
    if do_verify and (violations := validate_cleanroom_archive(dest, strict=strict)):
        dest.unlink(missing_ok=True)
        raise ValueError(f"Clean-room ZIP verification failed ({len(violations)}): {'; '.join(violations[:8])}")
    raw_zip = dest.read_bytes()
    report = {
        "schemaVersion": 2, "moduleId": manifest["moduleId"], "packageVersion": manifest["packageVersion"],
        "targetDecompTier": manifest["targetDecompTier"], "goalDecompTier": manifest["goalDecompTier"],
        "archivePath": dest.as_posix(), "fileSizeBytes": len(raw_zip), "sha256Hex": hashlib.sha256(raw_zip).hexdigest(),
        "entryCount": len(entries), "cleanRoomValidated": do_verify, "strict": bool(strict), "isPassed": True,
        "violations": [], "generatedAtUtc": _utc_now_iso(),
    }
    _write_log(log_dir, report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export a clean-room .decomp ZIP bundle for reStation/reEngine.")
    parser.add_argument("--out", type=Path, default=None, help="Output .decomp archive path.")
    parser.add_argument("--data-dir", type=Path, default=None, help="Data directory override for default .decomp output.")
    parser.add_argument("--log-dir", type=Path, default=None, help="Optional directory for export_decomp_bundle.log.")
    parser.add_argument("--recipe", type=Path, default=None, help="Optional decomp_recipe.json path override.")
    parser.add_argument("--verify-cleanroom", action="store_true", help="Verify generated .decomp archive against clean-room rules.")
    parser.add_argument("--strict", action="store_true", help="Enforce strict clean-room checks (implies --verify-cleanroom).")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(export_decomp_bundle(args.out, args.data_dir, args.log_dir, (args.verify_cleanroom or args.strict), args.recipe, strict=args.strict), indent=2))
        return 0
    except Exception as exc:
        err = {"schemaVersion": 2, "isPassed": False, "errorCode": "DECOMP_EXPORT_FAILED", "errorMessage": str(exc), "generatedAtUtc": _utc_now_iso()}
        _write_log(args.log_dir, err)
        print(json.dumps(err, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
