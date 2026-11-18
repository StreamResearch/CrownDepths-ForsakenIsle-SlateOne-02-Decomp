/* Clean-room D4 LP32 ABI, PS-X EXE headers, .T sector tables, and container parity tests. */
#include <stdlib.h>
#include <string.h>

#include "parity_harness.h"

static int test_lp32_abi_and_struct_sizes(void) {
    return sizeof(void *) == 4 && sizeof(long) == 4
        && sizeof(KfGfxEnv) == 0xe0 && sizeof(KfCameraState) == 0x34
        && sizeof(KfSceneControl) == 0x1c && sizeof(KfMapCell) == 0x0a
        && sizeof(KfMapObjDef) == 0x18 && sizeof(KfMapObjState) == 0x44
        && sizeof(KfWorldDrop) == 0x18 && sizeof(KfTextureAnimSlot) == 0x18
        && sizeof(KfEntityDef) == 0x78 && sizeof(KfEntityState) == 0x7c
        && sizeof(KfPlayerState) == 0x160 && sizeof(KfTArchiveSlot) == 0x0c
        && sizeof(KfItemDef) == 0x20 && sizeof(KfMagicDef) == 0x44
        && sizeof(KfSaveHeader) == 0x400 && sizeof(KfMoHeader) == 0x14
        && sizeof(KfFdatHeader) == 0x04;
}

static int test_retail_psx_exe_headers(const char *standalone_dir) {
    static const struct {
        const char *rel;
        size_t expected_size;
        uint32_t pc0;
        uint32_t t_addr;
        uint32_t t_size;
    } exes[] = {
        {"SLUS_001.58", 4096u, 0x80010128u, 0x80010000u, 0x800u},
        {"OPEN.EXE", 190464u, 0x80013db8u, 0x80011000u, 0x2e000u},
        {"GAME.EXE", 387072u, 0x8004a628u, 0x80011000u, 0x5e000u},
        {"END.EXE", 169984u, 0x80011cb4u, 0x80011000u, 0x29000u},
    };
    for (size_t i = 0; i < sizeof(exes) / sizeof(exes[0]); ++i) {
        size_t sz = 0;
        uint8_t *buf = d4_read_file_alloc(standalone_dir, exes[i].rel, &sz);
        if (!buf) return 0;
        int ok = sz == exes[i].expected_size
            && memcmp(buf, "PS-X EXE", 8) == 0
            && d4_rd_le32(buf + 0x10) == exes[i].pc0
            && d4_rd_le32(buf + 0x18) == exes[i].t_addr
            && d4_rd_le32(buf + 0x1c) == exes[i].t_size;
        free(buf);
        if (!ok) return 0;
    }
    return 1;
}

static int test_retail_t_archive_sector_tables(const char *standalone_dir) {
    static const struct {
        const char *rel;
        uint16_t entries;
    } archives[] = {
        {"CD/COM/FDAT.T", 70u},
        {"CD/COM/ITEM.T", 548u},
        {"CD/COM/MO.T", 448u},
        {"CD/COM/RTIM.T", 75u},
        {"CD/COM/RTMD.T", 9u},
        {"CD/COM/TALK.T", 755u},
        {"CD/COM/VAB.T", 331u},
    };
    for (size_t i = 0; i < sizeof(archives) / sizeof(archives[0]); ++i) {
        size_t sz = 0;
        uint8_t *buf = d4_read_file_alloc(standalone_dir, archives[i].rel, &sz);
        if (!buf || sz < 4u) { free(buf); return 0; }
        uint16_t cnt = d4_rd_le16(buf);
        if (cnt != archives[i].entries || sz < (size_t)(cnt + 2u) * 2u) { free(buf); return 0; }
        uint16_t *offs = (uint16_t *)(void *)(buf + 2);
        int ok = offs[0] >= 1u && ((size_t)offs[cnt] * 2048u == sz);
        for (uint16_t j = 0; ok && j < cnt; ++j) {
            if (offs[j + 1] < offs[j]) ok = 0;
        }
        if (ok) {
            memset(&g_kf_t_archive_slots[0], 0, sizeof(KfTArchiveSlot));
            g_kf_t_archive_slots[0].sector_offsets = offs;
            uint16_t sample_ids[3] = {0u, (uint16_t)(cnt / 2u), (uint16_t)(cnt - 1u)};
            for (int k = 0; k < 3; ++k) {
                uint16_t idx = sample_ids[k];
                s32 got = kf_game_t_archive_get_entry_size(0u, idx);
                s32 exp = ((s32)offs[idx + 1] - (s32)offs[idx]) * 2048;
                if (got != exp) { ok = 0; break; }
            }
            g_kf_t_archive_slots[0].sector_offsets = NULL;
        }
        free(buf);
        if (!ok) return 0;
    }
    return 1;
}

static int test_retail_fnd_mo_vab_str_headers(const char *standalone_dir) {
    size_t fn_sz = 0, fdat_sz = 0, mo_sz = 0, vab_sz = 0;
    uint8_t *fn_d = d4_read_file_alloc(standalone_dir, "CD/FN.D", &fn_sz);
    uint8_t *fdat = d4_read_file_alloc(standalone_dir, "CD/COM/FDAT.T", &fdat_sz);
    uint8_t *mo = d4_read_file_alloc(standalone_dir, "CD/COM/MO.T", &mo_sz);
    uint8_t *vab = d4_read_file_alloc(standalone_dir, "CD/COM/VAB.T", &vab_sz);
    int ok = fn_d && fdat && mo && vab
        && fn_sz == 1188u && memcmp(fn_d, "01 004 045 2", 12) == 0;
    if (ok) {
        uint16_t fdat_s0 = d4_rd_le16(fdat + 2);
        const KfFdatHeader *fh = (const KfFdatHeader *)(const void *)(fdat + (size_t)fdat_s0 * 2048u);
        uint16_t mo_s0 = d4_rd_le16(mo + 2);
        const KfMoHeader *mh = (const KfMoHeader *)(const void *)(mo + (size_t)mo_s0 * 2048u);
        uint16_t vab_s0 = d4_rd_le16(vab + 2);
        const uint8_t *vh = vab + (size_t)vab_s0 * 2048u;
        ok = fh->section_size == 6400u * sizeof(KfMapCell)
            && mh->total_size == 0x0a64u && mh->anim_count == 4u
            && mh->anim_table_offset == sizeof(KfMoHeader)
            && memcmp(vh, "pBAV", 4) == 0;
    }
    free(fn_d); free(fdat); free(mo); free(vab);
    if (!ok) return 0;

    uint8_t hdr[16];
    size_t got = d4_read_file_head(standalone_dir, "OP/OP2.S", hdr, sizeof(hdr));
    return got == sizeof(hdr) && d4_rd_le32(hdr) == 0x80420101u && d4_rd_le16(hdr + 8) == 0x0160u;
}

int d4_run_abi_and_media_tests(const char *standalone_dir, D4ParityResult *out, int max_out) {
    if (!out || max_out < 4) return 0;
    out[0] = (D4ParityResult){"lp32_abi_and_struct_sizes", test_lp32_abi_and_struct_sizes()};
    out[1] = (D4ParityResult){"retail_psx_exe_headers", test_retail_psx_exe_headers(standalone_dir)};
    out[2] = (D4ParityResult){"retail_t_archive_sector_tables", test_retail_t_archive_sector_tables(standalone_dir)};
    out[3] = (D4ParityResult){"retail_fnd_mo_vab_str_headers", test_retail_fnd_mo_vab_str_headers(standalone_dir)};
    return 4;
}
