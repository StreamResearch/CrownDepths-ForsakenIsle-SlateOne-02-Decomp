# Soundbanks (`VAB.T`: `.vh`/`.vb`) and Music Sequences (`pQES` SEQ)

**Specification ID:** `audio-vab-and-seq` · **Reference Parser:** [`Dev/scripts/kf_audio_vab_seq.py`](../../scripts/kf_audio_vab_seq.py) · **Parent Index:** [`Dev/docs/SPECIFICATIONS.md`](../SPECIFICATIONS.md)

This specification covers the PlayStation SPU audio containers in `CD/COM/VAB.T` (`331` slots / `122` active, `3,768,320` bytes) and `OP/*.D`: `56` paired VAB header (`.vh`) and ADPCM waveform body (`.vb`) soundbanks, `10` big-endian `pQES` MIDI sequences, and the resident `GAME.EXE` asynchronous audio streaming queue.

---

## 1. `CD/COM/VAB.T` Slot Partitioning (`56` `.vh` + `56` `.vb` + `10` `.seq`)

`VAB.T` pairs consecutive even/odd slots for soundbanks and assigns upper slots (`320..330`) to `pQES` BGM sequences:

| Slot Pattern | Active Count | Magic | Role | Sector Checksum (`0x12345678`) |
| :--- | ---: | :--- | :--- | :--- |
| Even slots (`0, 2, 4, ...`) | `56` | `"pBAV"` | VABp header + `ProgAtr` + `VagAtr` + VAG size table (`.vh`) | Enforced (`56 / 56` pass, mode `0x10`) |
| Odd slots (`1, 3, 5, ...`) | `56` | Raw ADPCM | Sector-aligned 4-bit PS-ADPCM sample body (`.vb`) | Bypassed (streamed via `mode 0x20/0x30`) |
| Upper slots (`320..330`) | `10` | `"pQES"` | Sequenced MIDI music track (`SLUS-00158` BGM) | Enforced (`10 / 10` pass, mode `0x10`) |

- `kf_game_mount_t_archives` loads `VAB[0]`/`VAB[1]` at boot as resident SFX bank `0`; `kf_game_step_area_load_fsm` loads area soundbanks via `kf_game_audio_load_vab_and_seq` (`0x8001474c`) and area BGM `pQES` tracks from `slot = 0x140 + (track_id % 100)` (`320 + id`).

---

## 2. `pBAV` Header Contract (`0x20` Bytes, `<IIIHHHHBBBBI` Fix)

Early unpackers misread the `pBAV` header with `<IIIIIIHHH`, causing `programs = 16511` (`0x407f` from packed `mvol/mpan` bytes). The verified `32`-byte little-endian `VABp` header layout matches `kf_game_snd_vab_parse_header` (`0x80052490`) across all `56 / 56` retail banks (`programs` strictly `2..12 < 128`):

| Offset | Size | Type | Field | Struct Pack (`+4`) | Verified Retail `VAB.T[0]` Value |
| :--- | ---: | :--- | :--- | :--- | :--- |
| `+0x00` | `4` | `char[4]` | `magic` | — | `"pBAV"` (`0x56414270` LE) |
| `+0x04` | `4` | `u32` | `version` | `I` | `6` (`>= 5` unlocks `128` program slots & `<< 3` VAG units) |
| `+0x08` | `4` | `u32` | `vab_id` | `I` | `0` |
| `+0x0C` | `4` | `u32` | `fsize` | `I` | `142,912` B (`3,616` B `.vh` + `139,296` B `.vb`) |
| `+0x10` | `2` | `u16` | `reserved_sys` | `H` | `0xEEEE` |
| `+0x12` | `2` | `u16` | `programs` | `H` | `2` (`VAB.T` range: `2..12`) |
| `+0x14` | `2` | `u16` | `tones` | `H` | `23` |
| `+0x16` | `2` | `u16` | `vags` | `H` | `22` |
| `+0x18` | `1` | `u8` | `master_vol` | `B` | `127` (`0x7F`) |
| `+0x19` | `1` | `u8` | `master_pan` | `B` | `64` (`0x40`, centered) |
| `+0x1A` | `1` | `u8` | `attr1` | `B` | `0` |
| `+0x1B` | `1` | `u8` | `attr2` | `B` | `0` |
| `+0x1C` | `4` | `u32` | `reserved2` | `I` | `0xFFFFFFFF` |

---

## 3. `ProgAtr[128]`, `VagAtr[16 * progs]` & VAG Size Table

Immediately following the `32`-byte `pBAV` header, `.vh` packs three contiguous metadata tables (`total_vh_bytes = 32 + 2048 + programs * 512 + 512`):

### 1. `ProgAtr[128]` (`2,048` B at `+0x0020`, Stride `0x10` B)
| Offset | Size | Type | Field | Description |
| :--- | ---: | :--- | :--- | :--- |
| `+0x00` | `1` | `u8` | `tones` | Active tone count mapped to this program (`0` if unused) |
| `+0x01` | `1` | `u8` | `mvol` | Program master volume (`0..127`) |
| `+0x02..+0x03` | `2` | `u8, u8` | `prior, mode` | Voice allocation priority and playback mode |
| `+0x04..+0x07` | `4` | `u8, s8, s16` | `mpan, reserved0, attr` | Stereo pan (`64` center) and program attributes |
| `+0x08..+0x0F` | `8` | `u32, u32` | `reserved1, reserved2` | Runtime SPU bank/offset scratch slots |

### 2. `VagAtr[16 * programs]` (`512 * programs` B at `+0x0820`, Stride `0x20` B)
| Offset | Size | Type | Field | Description |
| :--- | ---: | :--- | :--- | :--- |
| `+0x00..+0x03` | `4` | `u8[4]` | `prior, mode, vol, pan` | Per-tone SPU voice priority, reverb mode, volume, pan |
| `+0x04..+0x07` | `4` | `u8[4]` | `center, shift, min, max` | Root MIDI note, pitch detune, keyboard split `[min, max]` |
| `+0x08..+0x0D` | `6` | `u8[6]` | `vibW, vibT, porW, porT, pbmin, pbmax` | Vibrato, portamento, and pitch-bend semitone limits |
| `+0x10..+0x13` | `4` | `u16, u16` | `adsr1, adsr2` | Raw PS1 SPU hardware ADSR envelope registers |
| `+0x14..+0x17` | `4` | `s16, s16` | `prog, vag` | Parent program index and `1`-based VAG waveform ID |

### 3. VAG Size Table (`u16[256]`, `512` B) & `.vb` PS-ADPCM Framing
- Located directly after `VagAtr` (`0x820 + programs * 512`), each nonzero `u16` entry encodes waveform length in `8`-byte units for `version >= 5` (`size_bytes = entry << 3`, or `entry << 2` for `ver <= 4`, verified in `kf_game_snd_vab_parse_header` lines `286–289`).
- On `VAB.T[0]`: `22` active VAG entries sum to `139,296` bytes (`142,912 - 3,616 == 139,296`), backed by `16`-byte PS-ADPCM frames (`1` predictor/shift byte, `1` loop flag byte, `14` compressed 4-bit sample bytes) in `VAB.T[1]` (`141,312` B sector-padded).

### SPU `ADSR1`/`ADSR2` Hardware Envelope Bitfields (`VagAtr +0x10..+0x13`)
- **`adsr1` (`u16`):** Attack mode (`bit 15`), Attack rate (`bits 14..8`), Decay rate (`bits 7..4`), Sustain level (`bits 3..0`).
- **`adsr2` (`u16`):** Sustain mode (`bits 15..14`), Sustain direction (`bit 13`), Sustain rate (`bits 12..6`), Release mode (`bit 5`), Release rate (`bits 4..0`).
- **Loop Flag Byte (`.vb` frame `+0x01`):** Bit `0` marks loop end, bit `1` marks repeat jump, bit `2` marks loop start address (`loop_addr`) uploaded into SPU RAM.
- **Pitch Conversion:** PS1 SPU native sample rate `44,100 Hz` corresponds to pitch register `0x1000`, scaled via `VagAtr.center` and `VagAtr.shift` semitone/fine-tune fields.

### Header Validation Invariants (`kf_audio_vab_seq.py`)
- Reject `pBAV` banks if `version not in {5, 6, 7}`, `programs > 128`, or `declared_bytes > 0x400000`.
- Assert `sum(vag_sizes) == declared_bytes - vh_bytes` and `len(vb_chunk) >= vb_declared_bytes`.
- Verify `0x12345678` sector checksum on every `.vh` (`56/56`) and `.seq` (`10/10`) entry.

---

## 4. `pQES` Sequenced Music Format & Sequencer Engine (`GAME.EXE`)

All `10` active `VAB.T` sequences (`slots 320..327, 329..330`) and `2` `OP.D` sequences carry a **big-endian** `15`-byte `pQES` header parsed by `kf_game_snd_parse_seq_header` (`0x80056808`):

| Offset | Size | Endian | Field | Verified Retail Examples (`VAB.T[320..330]`) |
| :--- | ---: | :--- | :--- | :--- |
| `+0x00` | `4` | ASCII | `magic` | `"pQES"` |
| `+0x04` | `4` | BE `u32` | `version` | `1` |
| `+0x08` | `2` | BE `u16` | `resolution_ppqn` | `480` PPQN (`0x01E0`) across all `10` tracks |
| `+0x0A` | `3` | BE `u24` | `tempo_us` | Microseconds per quarter note (`428,571`..`1,052,631` us -> `57..140` BPM) |
| `+0x0D` | `1` | `u8` | `rhythm_num` | Time signature numerator (`3` or `4`, `0` on ambient loop `329`) |
| `+0x0E` | `1` | `u8` | `rhythm_den_pow2` | Power-of-two denominator (`2` -> `/4` time, `0` -> `/1`) |

### Sequencer Opcodes & Runtime Streaming (`0x80014534` / `0x800578f4`)
- **VLQ Delta Timestamps (`kf_game_snd_read_seq_delta_time @ 0x80058810`):** Decodes standard 7-bit-per-byte variable-length MIDI deltas before dispatching Note On/Off, Program Change, Pitch Bend, Control Change, and Meta (`0x2F` End-of-Track, `0x51` Tempo) events.
- **NRPN Loop Control (`kf_game_snd_seq_handle_ctrl_change @ 0x800578f4` & `0x80057afc`):** Control changes `0x14` (loop start marker) and `0x1E` (loop target jump) plus `22` NRPN Data Entry opcodes drive dynamic ADSR, pan, pitch, and reverb mutations.
- **4-Slot Dynamic VAB Allocator (`kf_game_audio_alloc_vab_slot @ 0x80014670` & `0x80014534`):** Manages four dynamic VAB bank slots (`0x801993d8`) and pumps asynchronous CD-to-SPU DMA transfers (`mode 0x20/0x30`) each frame.

### SPU Hardware Reverb & Channel Voice Control (`SpuVoiceAttr` / `SpuCommonAttr`)
- **`kf_game_snd_init_core` (`0x80051920`):** Initializes all `24` SPU hardware voice channels (`VOICE_00_LEFT_RIGHT`) and `32` sequencer track descriptors (`0x40` B stride at `0x8009b7e4`).
- **`kf_game_snd_set_reverb_mode` (`0x800521a8`) & `kf_game_snd_set_reverb_depth` (`0x80052218`):** Validates SPU reverb algorithm ID (`< 10`), scales stereo depth `(depth * 0x7fff) / 0x7f`, and applies common attribute packets.
- **`kf_game_snd_vab_parse_header` (`0x80052490`):** Checks `magic >> 8 == 0x564142`, computes `max_progs` (`64` vs `128` for `version > 4`), maps `local_428[256]` byte sizes (`<< 2` or `<< 3`), reserves SPU sound RAM (`kf_game_spu_malloc`, bounded `< 0x80001`), and resolves each VAG's SPU start address (`>> 3`).
- **`kf_game_snd_seq_called_tbyt` (`0x800594b8`):** Advances per-tick BGM crescendo (`flag 0x10`) and decrescendo (`flag 0x20`) volume envelopes cleanly without stalling CD transfers.

### Verified Retail `VAB.T` Sample Banks & All `10` `pQES` Sequences

| Slot(s) | Kind | Bytes / Declared | Key Verified Metrics (`kf_audio_vab_seq.py`) |
| :--- | :--- | ---: | :--- |
| `0` / `1` | `VAB` (`pBAV` + `.vb`) | `142,912` B | `ver=6`, `vh=3,616` B, `vb=139,296` B, `progs=2`, `tones=23`, `vags=22` |
| `2` / `3` | `VAB` (`pBAV` + `.vb`) | `162,304` B | `ver=6`, `vh=7,200` B, `vb=155,104` B, `progs=9`, `tones=25`, `vags=12` |
| `6` / `7` | `VAB` (`pBAV` + `.vb`) | `158,192` B | `ver=6`, `vh=8,736` B, `vb=149,456` B, `progs=12`, `tones=15`, `vags=11` |
| `64` / `65` | `VAB` (`pBAV` + `.vb`) | `31,296` B | `ver=6`, `vh=3,104` B, `vb=28,192` B, `progs=1`, `tones=3`, `vags=4` |
| `320`..`323` | `SEQ` (`pQES`) | `2,048..6,144` B | `480` PPQN, `4/4` time, tempos `821,917..1,016,949` us (`59..87` BPM) |
| `324`..`326` | `SEQ` (`pQES`) | `6,144..10,240` B | `480` PPQN, `3/4` & `4/4` time, `57..140` BPM (`428,571` us fastest) |
| `327, 329, 330` | `SEQ` (`pQES`) | `2,048..10,240` B | `480` PPQN, `4/4` & `0/1` (`329` ambient), `59..81` BPM |

---

## 5. Mapped Specification Coverage Ledger (`16 / 16` Fields)

| # | `spec_coverage.json` Field Key | Binary / Struct Location | Verification Rule |
| ---: | :--- | :--- | :--- |
| `1` | `VAB_T.56_vh_vb_pairs_and_10_seq` | `CD/COM/VAB.T` (`331` slots) | `56` `.vh` + `56` `.vb` + `10` `.seq` |
| `2` | `pBAV.header_32_bytes_fixed_fmt` | `.vh` `+0x04..+0x1F` | `<IIIHHHHBBBBI` unpack (`0x20` B) |
| `3` | `pBAV.ver_6_vid_0_res_sys_0xeeee` | `.vh` `+0x04..+0x11` | `ver=6`, `vid=0`, `res_sys=0xeeee` |
| `4` | `pBAV.progs_tones_vags_vol_pan` | `.vh` `+0x12..+0x1F` | `progs < 128`, `mvol=127`, `mpan=64` |
| `5` | `ProgAtr.128_slots_16_bytes` | `.vh` `+0x0020..+0x081F` | `128 x 16` B program records |
| `6` | `VagAtr.16_tones_per_prog_32_bytes` | `.vh` `+0x0820` | `programs * 16 x 32` B tone array |
| `7` | `VagAtr.adsr1_adsr2_prog_vag` | `VagAtr` `+0x10..+0x17` | SPU ADSR1/2, parent `prog`, `vag` ID |
| `8` | `VAB.vag_size_table_256_u16_lshift3` | `.vh` VAG table (`512` B) | `sum(w << 3) == fsize - vh_bytes` |
| `9` | `VAB.vb_4bit_adpcm_16b_frames` | Odd `.vb` slots | Sector-padded 4-bit PS-ADPCM body |
| `10` | `pQES.header_15_bytes_be` | `SEQ` `+0x00..+0x0E` | `>4sIH5B` big-endian header |
| `11` | `pQES.ppqn_480_and_tempo_u24` | `pQES` `+0x08..+0x0C` | `480` PPQN + 24-bit `tempo_us` |
| `12` | `pQES.rhythm_num_and_den_pow2` | `pQES` `+0x0D..+0x0E` | Numerator + `1 << den_pow2` |
| `13` | `SEQ.vlq_delta_and_midi_events` | `kf_game_snd_read_seq_delta_time` | 7-bit VLQ delta + MIDI event stream |
| `14` | `SEQ.nrpn_0x14_0x1e_loop_opcodes` | `kf_game_snd_seq_handle_ctrl_change` | CC `0x14`/`0x1e` + `22` NRPN opcodes |
| `15` | `Audio.async_mode_0x20_0x30_streaming` | `kf_game_t_archive_read_async_20/30` | Non-checksummed SPU stream reads |
| `16` | `Audio.4_dynamic_vab_slots_801993d8` | `kf_game_audio_alloc_vab_slot` | `4` dynamic VAB slots (`0x801993d8`) |

---

## 6. Clean-Room Parser Usage & Verification

```powershell
# Offline synthetic VAB.T (ver=6, progs=2, tones=23, vags=22 + .vb + pQES) check
python -B Dev/scripts/kf_audio_vab_seq.py --offline-synthetic --data-dir "$env:TEMP\kf-work" --log-dir "$env:TEMP\kf-logs"

# Fail-closed empty directory check (exits 2 with MISSING_CORPUS_MEDIA JSON)
python -B Dev/scripts/kf_audio_vab_seq.py --data-dir "$env:TEMP\kf-empty"
```

Verified schemas: [`Dev/schemas/types/primitives_and_sdk.h`](../../schemas/types/primitives_and_sdk.h), [`Dev/schemas/spec_coverage.json`](../../schemas/spec_coverage.json).
