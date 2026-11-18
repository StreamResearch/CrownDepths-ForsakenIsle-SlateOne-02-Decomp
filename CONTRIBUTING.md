# Contributing

Contributions are welcome, including bug reports, documentation improvements, format findings, and pull requests.

## Ways to Contribute

- **Bug Reports:** Open an issue with your OS, Python version, command run, and relevant output.
- **Pull Requests:** Keep changes focused on a single fix or feature, and include tests for new behavior.
- **Documentation:** Improvements to clarity, examples, and format specifications are always appreciated.

## Dev Setup & Running Tests

```powershell
git clone https://github.com/StreamResearch/CrownDepths-ForsakenIsle-SlateOne-02-Decomp.git
cd CrownDepths-ForsakenIsle-SlateOne-02-Decomp
python -B -m unittest discover -s Dev/scripts/tests -v
```

You can also run the offline synthetic checks without a retail disc image:

```powershell
python -B Dev/scripts/psx_kf_unpack.py --offline-synthetic --data-dir "$env:TEMP\kf-unpack" --log-dir Dev/logs
python -B Dev/scripts/materialize_decomp_tiers.py --offline-synthetic --data-dir "$env:TEMP\kf-tiers" --log-dir Dev/logs
python -B Dev/scripts/build_and_verify_d4.py --offline-synthetic --data-dir "$env:TEMP\kf-d4" --log-dir Dev/logs
python -B Dev/scripts/verify_track_d4.py --offline-synthetic --data-dir "$env:TEMP\kf-d4" --log-dir Dev/logs
python -B Dev/scripts/export_decomp_bundle.py --verify-cleanroom --log-dir Dev/logs
```

## Pull Request Checklist

- [ ] All unit tests pass (`python -B -m unittest discover -s Dev/scripts/tests -v`).
- [ ] Offline synthetic verification passes with zero warnings.
- [ ] Changes stay focused and avoid unrelated edits.
- [ ] User-facing changes are noted in `CHANGELOG.md` under `[Unreleased]`.

## Clean-Room Rules

- **No Copyrighted Material:** Never commit or attach retail game binaries, disc images, audio, textures, console BIOS files, or Ghidra `.gpr` databases.
- **No Raw Disassembly or Retail Strings:** Do not paste copyrighted game text or raw vendor disassembly into issues or pull requests.
- **Security & Leak Reports:** See [SECURITY.md](SECURITY.md) for private reporting.
