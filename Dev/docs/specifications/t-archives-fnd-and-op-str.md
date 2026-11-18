# `.T` Sector Archives, `CD/FN.D`, and `OP/*` Streams (`SLUS-00158`)

**Specification ID:** `t-archives-fnd-and-op-str` · **Reference Parser:** [`Dev/scripts/kf_t_archives.py`](../../scripts/kf_t_archives.py) · **Parent Index:** [`Dev/docs/SPECIFICATIONS.md`](../SPECIFICATIONS.md)

This specification covers the seven sector-indexed `.T` resource containers in `CD/COM/*.T`, the `CD/FN.D` CP932 item descriptor table, the `OP/OP.D` and `OP/OPU.D` intro packs, the `OP/*.S` CD-XA Mode 2 Form 2 MDEC video streams, and the `0x12345678` CD sector checksum verified across `GAME.EXE`.

---

## 1. `.T` Archive Sector Table Header (`KfTArchiveHeader`)

Every archive under `CD/COM/` uses a little-endian `2,048`-byte sector-aligned directory header (`KfTArchiveHeader`), read at boot by `kf_game_open_t_archive_slot` (`0x800185a0`) into `g_kf_t_archive_slots` (`KfTArchiveSlot[7]`):

| Offset | Size | Type | Field | Verified Invariant |
| :--- | ---: | :--- | :--- | :--- |
| `+0x00` | `2` | `u16` | `entry_count` | Total number of directory slots (`N`) |
| `+0x02` | `2*(N+1)` | `u16[N+1]` | `sector_offsets` | Monotonic cumulative `2,048`-B sector indices (`offs[0] >= 1`) |
| `0x0000..offs[0]*2048` | `2,048 * offs[0]` | `u8[]` | `header_sectors` | Zero-padded sector block enclosing `sector_offsets` |

### Slot Indexing Rules (`kf_game_t_archive_resolve_entry` & `kf_game_t_archive_get_entry_size`)
- Entry `i` (`0 <= i < entry_count`) occupies `[sector_offsets[i] * 2048, sector_offsets[i + 1] * 2048)` inside the `.T` file.
- An entry is empty (skipped) whenever `sector_offsets[i + 1] == sector_offsets[i]`.
- For all seven retail archives, `sector_offsets[entry_count] * 2048 == file_size_bytes` with zero trailing slack.

### Complete `/CD/COM/*.T` Archive Registry (`KfTArchiveId`)

| Archive | `KfTArchiveId` | File Size (B) | Total Sectors | Total Slots | Active Slots | Primary Contents |
| :--- | :--- | ---: | ---: | ---: | ---: | :--- |
| `CD/COM/MO.T` | `KF_T_MO` (`0`) | `5,693,440` | `2,780` | `448` | `405` | `108` animated `.MO` + `297` static `0`-anim `.TMD` models |
| `CD/COM/RTMD.T` | `KF_T_RTMD` (`1`) | `1,083,392` | `529` | `9` | `9` | Per-zone map tile geometry (`185`..`28` objects, `240`-slot table) |
| `CD/COM/RTIM.T` | `KF_T_RTIM` (`2`) | `4,304,896` | `2,102` | `75` | `72` | Chained `KfRtimHeader` (`src_rect` + `dst_rect`) VRAM streams |
| `CD/COM/TALK.T` | `KF_T_TALK` (`3`) | `13,197,312` | `6,444` | `755` | `379` | `34,816`-B pre-rendered `256x256` 4-bpp TIM dialogue cards |
| `CD/COM/VAB.T` | `KF_T_VAB` (`4`) | `3,768,320` | `1,840` | `331` | `122` | `56` `.vh` + `56` `.vb` VAB soundbank pairs + `10` `pQES` SEQ tracks |
| `CD/COM/FDAT.T` | `KF_T_FDAT` (`5`) | `1,992,704` | `973` | `70` | `45` | Zone triplets (`0..7`, `10`), `FDAT[47]` VRAM, `FDAT[48]` boot DB, `18` weapon view-models |
| `CD/COM/ITEM.T` | `KF_T_ITEM` (`6`) | `11,110,400` | `5,425` | `548` | `403` | `103` `.TMD` 3D item meshes (`0..119`) + `300` `.TIM` UI/map textures (`120..547`) |

---

## 2. `KfTArchiveSlot` Runtime Table (`0x801b6f48`, `0x0C` B Stride)

`kf_game_mount_t_archives` (`0x80015dd4`) mounts all seven archives into a `KfTArchiveSlot` array in `GAME.EXE` BSS:

| Offset | Size | Type | Field | Verified Behavior |
| :--- | ---: | :--- | :--- | :--- |
| `+0x00` | `4` | `u16 *` | `sector_offsets` | Heap pointer storing `entry_count + 1` sector offsets (`(cnt + 1) * 2` B) |
| `+0x04` | `4` | `CdlLOC` | `start_loc` | Disc BCD `minute/second/sector/track` of the archive start sector |
| `+0x08` | `4` | `u32` | `total_size` | Archive byte size reported by ISO9660 directory search |

- `kf_game_t_archive_resolve_entry` (`0x80017f1c`) converts `start_loc` via `kf_game_cd_msf_to_lba`, adds `sector_offsets[entry_idx]`, converts back via `kf_game_cd_lba_to_msf`, and returns `(sector_offsets[entry_idx + 1] - sector_offsets[entry_idx]) * 2048`.

---

## 3. `0x12345678` CD Sector Checksum (`kf_game_cd_verify_sector_checksum`)

All `type = 0x10` synchronous/asynchronous `.T` streams validate integrity using `kf_game_cd_verify_sector_checksum` (`0x80017db0`):

- Let `words` be the little-endian `u32` view of the sector-aligned buffer (`sector_count * 512` words).
- Compute `acc = (0x12345678 + sum(words[0 .. len(words) - 2])) & 0xFFFFFFFF`.
- The transfer succeeds iff `acc == words[-1]` (the function returns `bool` `true` on mismatch to trigger retry).
- **Verified Empirical Coverage:** `45/45` `FDAT.T`, `403/403` `ITEM.T`, `405/405` `MO.T`, `9/9` `RTMD.T`, `379/379` `TALK.T`, and `66/66` `.vh`/`.seq` entries in `VAB.T` match `0x12345678` (`1,307 / 1,307`). Audio `.vb` (`mode 0x20/0x30`) and `RTIM.T` (`mode 0x40`) bypass the `0x10` checksum path.

---

## 4. `CD/FN.D` Item Descriptor Table (`1,188` Bytes)

`CD/FN.D` is a CRLF-delimited `CP932` (Shift-JIS half-width katakana) descriptor file terminated by a `999 99` sentinel and DOS `0x1A` EOF byte:

| Line Index | Format | Verified Retail Structure |
| :--- | :--- | :--- |
| `0` | `"01 004 045 2"` | Header control parameters |
| `1` | `"099"` | Table limit / sentinel tag |
| `2..59` | `"III CC   <cp932>"` | `58` fixed-width item index (`000..`), category (`CC`), and half-width Shift-JIS label |
| `60` | `"999 99"` | End-of-table sentinel record (`has_label = false`) |

---

## 5. `OP/OP.D`, `OP/OPU.D` (`552,344` B) & `OP/*.S` CD-XA MDEC Streams

### `OP.D` / `OPU.D` Container Layout (`552,344` Bytes Each)
Both `OP/OP.D` and `OP/OPU.D` concatenate graphics and resident audio inside one contiguous container:

| Offset Span | Contents | Verified Metadata |
| :--- | :--- | :--- |
| `0x000000..0x04E3FF` | `8` sequential `.TIM` graphics | `16`-bpp (`pmode=2`) and `4`-bpp UI/logo screens (`300x121`, `243x240`, etc.) |
| `0x04E400..0x084ABF` | Embedded `pBAV` soundbank | `222,912` B (`ver=6`, `programs=8`, `tones=12`, `vags=10`) |
| `0x084AC0..end` | Embedded `pQES` sequences | `2` intro/menu SEQ tracks (`0x084AC0`, `0x085130`) |

### `OP/*.S` Mode 2 Form 2 CD-XA MDEC Streams (`2,336`-B Sectors)
All five movie files store raw `2,336`-byte Mode 2 Form 2 CD-XA sectors with zero byte remainder (`bytes % 2336 == 0`). Each sector opens with a repeated `8`-byte XA subheader (`[0..3] == [4..7]`), followed at `+0x08` by the `320x240` MDEC STR packet header (`0x80010160` LE):

| Stream File | Bytes | `2,336`-B Sectors | Chunks / Frame | Dimensions | Subheader & Role |
| :--- | ---: | ---: | ---: | :--- | :--- |
| `OP/OP0.S` | `3,417,568` | `1,463` | `9` | `320x240` | Opening intro segment 0 |
| `OP/OP1.S` | `6,650,592` | `2,847` | `9` | `320x240` | Opening intro segment 1 |
| `OP/OP2.S` | `38,494,944` | `16,479` | `14` | `320x240` | Opening intro segment 2 |
| `OP/ED0.S` | `60,042,208` | `25,703` | `14` | `320x240` | Ending cinema segment 0 |
| `OP/ED1.S` | `98,315,232` | `42,087` | `14` | `320x240` | Ending cinema segment 1 |

---

## 6. Clean-Room Disc Integrity Gate (`standalone_integrity.json`)

Before extracting or decoding any media, [`Dev/scripts/psx_kf_unpack.py`](../../scripts/psx_kf_unpack.py) and [`Dev/scripts/kf_t_archives.py`](../../scripts/kf_t_archives.py) verify all `23` required `disc/files/*` paths in [`Dev/schemas/standalone_integrity.json`](../../schemas/standalone_integrity.json) (`schemaVersion: 2`) using `1 MiB` chunked SHA-256 hashing:

| Category | Required Entries | Total Bytes | Notes |
| :--- | ---: | ---: | :--- |
| Executables & System | `8` files | `785,205` | `SLUS_001.58`, `OPEN.EXE`, `GAME.EXE`, `END.EXE`, `SYSTEM.CNF`, `COPY.TXT`, `LICENSEA.DAT`, `license_data.dat` |
| `/CD/` & `/CD/COM/*.T` | `8` files | `41,151,564` | `CD/FN.D` + `FDAT.T`, `ITEM.T`, `MO.T`, `RTIM.T`, `RTMD.T`, `TALK.T`, `VAB.T` |
| `/OP/` Cinema & Packs | `7` files | `208,025,240` | `OP.D`, `OPU.D`, `OP0.S`, `OP1.S`, `OP2.S`, `ED0.S`, `ED1.S` (`98,315,232` B) |
| Raw Disc Image *(opt.)* | `1` optional | `258,183,744` | Raw image verified only when present (`isRequired: false`) |

### `GAME.EXE` CD-ROM Streaming Call Chain (`0x80017f1c..0x800187cc`)
- **`kf_game_t_archive_init_subsystem` (`0x80018690`):** Registers VSync root-counter tick event `0xf2000003` and resets all `KfTArchiveSlot` headers.
- **`kf_game_open_t_archive_slot` (`0x800185a0`):** Searches `\CD\COM\*.T;1`, populates `start_loc`/`total_size`, reads sector `0`, and allocates `(entry_count + 1) * 2` bytes for `sector_offsets`.
- **`kf_game_t_archive_read_async_10/20/30` (`0x80017fa4..0x8001804c`):** Enqueues sector reads with `0x10` (checksummed), `0x20`/`0x30` (streaming audio), or `0x40` (VRAM upload) transfer modes.
- **`kf_game_t_archive_read_sync_pool` (`0x800180a0`) & `kf_game_t_archive_shutdown` (`0x800187cc`):** Synchronous pool allocation and clean critical-section BIOS event teardown.

---

## 7. Mapped Specification Coverage Ledger (`16 / 16` Fields)

| # | `spec_coverage.json` Field Key | Binary / Struct Location | Verification Rule |
| ---: | :--- | :--- | :--- |
| `1` | `KfTArchiveHeader.entry_count` | `.T` `+0x00` (`u16`) | `entry_count > 0` |
| `2` | `KfTArchiveHeader.sector_offsets` | `.T` `+0x02` (`u16[N+1]`) | Monotonic; `offs[-1] * 2048 == size` |
| `3` | `KfTArchiveSlot.runtime_table` | `0x801b6f48` (`0x0c` stride) | `sector_offsets`, `start_loc`, `total_size` |
| `4` | `Archive.FDAT_T.70_slots` | `CD/COM/FDAT.T` | `70` slots / `45` active (`973` sec) |
| `5` | `Archive.ITEM_T.548_slots` | `CD/COM/ITEM.T` | `548` slots / `403` active (`5,425` sec) |
| `6` | `Archive.MO_T.448_slots` | `CD/COM/MO.T` | `448` slots / `405` active (`2,780` sec) |
| `7` | `Archive.RTIM_T.75_slots` | `CD/COM/RTIM.T` | `75` slots / `72` active (`2,102` sec) |
| `8` | `Archive.RTMD_T.9_slots` | `CD/COM/RTMD.T` | `9` slots / `9` active (`529` sec) |
| `9` | `Archive.TALK_T.755_slots` | `CD/COM/TALK.T` | `755` slots / `379` active (`6,444` sec) |
| `10` | `Archive.VAB_T.331_slots` | `CD/COM/VAB.T` | `331` slots / `122` active (`1,840` sec) |
| `11` | `CD.sector_checksum_0x12345678` | Mode `0x10` final `u32` | `0x12345678 + sum(u32[:-1]) == u32[-1]` |
| `12` | `CD.FN_D.cp932_item_table` | `CD/FN.D` (`1,188` B) | `CP932` rows + `999 99` EOF marker |
| `13` | `OP.OP_D.tim_vab_seq_bundle` | `OP/OP.D` (`552,344` B) | `8` TIMs + `pBAV` + `2` `pQES` |
| `14` | `OP.OPU_D.tim_vab_seq_bundle` | `OP/OPU.D` (`552,344` B) | `8` TIMs + `pBAV` + `2` `pQES` |
| `15` | `OP.STR.xa_mode2_form2_2336` | `OP/*.S` (`% 2336 == 0`) | `8`-B repeated XA subheader |
| `16` | `OP.STR.mdec_header_0x80010160` | `OP/*.S` `+0x08` | `320x240`, `9` or `14` chunks/frame |

---

## 8. Clean-Room Parser Usage & Verification

```powershell
# Offline synthetic verification (0 retail media)
python -B Dev/scripts/kf_t_archives.py --offline-synthetic --data-dir "$env:TEMP\kf-work" --log-dir "$env:TEMP\kf-logs"

# Fail-closed empty directory check (exits 2 with MISSING_CORPUS_MEDIA JSON)
python -B Dev/scripts/kf_t_archives.py --data-dir "$env:TEMP\kf-empty"
```

Verified schemas: [`Dev/schemas/types/kf_containers_and_io.h`](../../schemas/types/kf_containers_and_io.h), [`Dev/schemas/standalone_integrity.json`](../../schemas/standalone_integrity.json), [`Dev/schemas/spec_coverage.json`](../../schemas/spec_coverage.json).
