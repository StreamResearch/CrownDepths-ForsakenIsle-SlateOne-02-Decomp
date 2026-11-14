#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "kingsfield_types.h"
#include "kingsfield_globals.h"

/* Exact lifted C declarations under test from readable/ translation units */
s32 kf_game_math_step_linear_clamp(s32 cur_val, s32 target_val, s32 step_delta);
bool kf_game_math_is_angle_cw_halfplane(s32 angle_a, s32 angle_b);
s32 kf_game_math_angle_diff_signed(s32 angle_a, s32 angle_b);
bool kf_game_math_intervals_overlap(s32 pos_a, s32 neg_extent, s32 pos_b, s32 pos_extent);
s32 kf_game_math_lerp_q12(s32 start_val, s32 end_val, s32 t_q12);
u32 kf_game_math_lerp_angle_q12(s32 start_angle, s16 end_angle, s32 t_q12);
void kf_game_math_lerp_pose_s16(s16 *src_pose, s16 *dst_pose, s16 *out_pose, s16 t_q12);
s32 kf_game_cd_bcd_to_int(u32 bcd_byte);
u32 kf_game_cd_int_to_bcd(u32 value);
bool kf_game_cd_verify_sector_checksum(s32 *buf, s32 sector_count);
s32 kf_game_t_archive_get_entry_size(u32 archive_slot, u32 entry_idx);
void kf_game_player_clamp_mp_regen(void);
void kf_game_player_clamp_hp_regen(void);
s32 kf_game_mc_checksum_payload(u8 *payload);
s32 kf_game_player_scale_gauge(s32 stat_val, s32 divisor);
s32 kf_game_player_eval_combat_curve(s32 base_val, s32 bonus_val, s32 scale_step);
void kf_end_init_str_decoder_state(void);

typedef struct {
    const char *name;
    bool (*fn)(const char *standalone_dir);
} ParityTest;

static uint32_t read_le32(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static uint16_t read_le16(const uint8_t *p) {
    return (uint16_t)p[0] | ((uint16_t)p[1] << 8);
}

static uint8_t *read_file_alloc(const char *standalone_dir, const char *rel, size_t *out_size) {
    char path[1024];
    snprintf(path, sizeof(path), "%s/disc/files/%s", standalone_dir, rel);
    FILE *fp = fopen(path, "rb");
    if (!fp) return NULL;
    if (fseek(fp, 0, SEEK_END) != 0) { fclose(fp); return NULL; }
    long sz = ftell(fp);
    if (sz < 0 || fseek(fp, 0, SEEK_SET) != 0) { fclose(fp); return NULL; }
    uint8_t *buf = (uint8_t *)malloc((size_t)sz);
    if (!buf) { fclose(fp); return NULL; }
    size_t got = fread(buf, 1, (size_t)sz, fp);
    fclose(fp);
    if (got != (size_t)sz) { free(buf); return NULL; }
    if (out_size) *out_size = (size_t)sz;
    return buf;
}

static bool test_lp32_abi_and_struct_sizes(const char *standalone_dir) {
    (void)standalone_dir;
    return sizeof(void *) == 4 && sizeof(long) == 4 &&
           sizeof(KfGfxEnv) == 0xe0 && sizeof(KfCameraState) == 0x34 &&
           sizeof(KfSceneControl) == 0x1c && sizeof(KfMapCell) == 0x0a &&
           sizeof(KfMapObjDef) == 0x18 && sizeof(KfMapObjState) == 0x44 &&
           sizeof(KfWorldDrop) == 0x18 && sizeof(KfTextureAnimSlot) == 0x18 &&
           sizeof(KfEntityDef) == 0x78 && sizeof(KfEntityState) == 0x7c &&
           sizeof(KfPlayerState) == 0x160 && sizeof(KfTArchiveSlot) == 0x0c &&
           sizeof(KfItemDef) == 0x20 && sizeof(KfMagicDef) == 0x44 &&
           sizeof(KfSaveHeader) == 0x400 && sizeof(KfMoHeader) == 0x14 &&
           sizeof(KfFdatHeader) == 0x04;
}

static bool test_retail_psx_exe_headers(const char *standalone_dir) {
    static const struct {
        const char *rel;
        size_t expected_size;
        uint32_t pc0;
        uint32_t t_addr;
        uint32_t t_size;
    } exes[] = {
        {"SLUS_001.58", 4096, 0x80010128u, 0x80010000u, 0x800u},
        {"OPEN.EXE", 190464, 0x80013db8u, 0x80011000u, 0x2e000u},
        {"GAME.EXE", 387072, 0x8004a628u, 0x80011000u, 0x5e000u},
        {"END.EXE", 169984, 0x80011cb4u, 0x80011000u, 0x29000u},
    };
    for (size_t i = 0; i < sizeof(exes) / sizeof(exes[0]); ++i) {
        size_t sz = 0;
        uint8_t *buf = read_file_alloc(standalone_dir, exes[i].rel, &sz);
        if (!buf) return false;
        bool ok = (sz == exes[i].expected_size) &&
                  (memcmp(buf, "PS-X EXE", 8) == 0) &&
                  (read_le32(buf + 0x10) == exes[i].pc0) &&
                  (read_le32(buf + 0x18) == exes[i].t_addr) &&
                  (read_le32(buf + 0x1c) == exes[i].t_size);
        free(buf);
        if (!ok) return false;
    }
    return true;
}

static bool test_retail_t_archive_sector_tables(const char *standalone_dir) {
    static const struct {
        const char *rel;
        uint16_t entries;
    } archives[] = {
        {"CD/COM/FDAT.T", 70},
        {"CD/COM/ITEM.T", 548},
        {"CD/COM/MO.T", 448},
        {"CD/COM/RTIM.T", 75},
        {"CD/COM/RTMD.T", 9},
        {"CD/COM/TALK.T", 755},
        {"CD/COM/VAB.T", 331},
    };
    for (size_t i = 0; i < sizeof(archives) / sizeof(archives[0]); ++i) {
        size_t sz = 0;
        uint8_t *buf = read_file_alloc(standalone_dir, archives[i].rel, &sz);
        if (!buf || sz < 4) { free(buf); return false; }
        uint16_t cnt = read_le16(buf);
        if (cnt != archives[i].entries || sz < (size_t)(cnt + 2) * 2u) { free(buf); return false; }
        uint16_t *offs = (uint16_t *)(buf + 2);
        bool ok = offs[0] >= 1 && ((size_t)offs[cnt] * 2048u == sz);
        for (uint16_t j = 0; ok && j < cnt; ++j) {
            if (offs[j + 1] < offs[j]) ok = false;
        }
        if (ok) {
            memset(&g_kf_t_archive_slots[0], 0, sizeof(KfTArchiveSlot));
            g_kf_t_archive_slots[0].sector_offsets = offs;
            uint16_t sample_ids[3] = {0, (uint16_t)(cnt / 2), (uint16_t)(cnt - 1)};
            for (int k = 0; k < 3; ++k) {
                uint16_t idx = sample_ids[k];
                s32 got = kf_game_t_archive_get_entry_size(0u, idx);
                s32 exp = ((s32)offs[idx + 1] - (s32)offs[idx]) * 2048;
                if (got != exp) { ok = false; break; }
            }
            g_kf_t_archive_slots[0].sector_offsets = NULL;
        }
        free(buf);
        if (!ok) return false;
    }
    return true;
}

static bool test_retail_fnd_mo_vab_str_headers(const char *standalone_dir) {
    size_t fn_sz = 0, fdat_sz = 0, mo_sz = 0, vab_sz = 0;
    uint8_t *fn_d = read_file_alloc(standalone_dir, "CD/FN.D", &fn_sz);
    uint8_t *fdat = read_file_alloc(standalone_dir, "CD/COM/FDAT.T", &fdat_sz);
    uint8_t *mo = read_file_alloc(standalone_dir, "CD/COM/MO.T", &mo_sz);
    uint8_t *vab = read_file_alloc(standalone_dir, "CD/COM/VAB.T", &vab_sz);
    bool ok = fn_d && fdat && mo && vab &&
              fn_sz == 1188 && memcmp(fn_d, "01 004 045 2", 12) == 0;
    if (ok) {
        uint16_t fdat_s0 = read_le16(fdat + 2);
        const KfFdatHeader *fh = (const KfFdatHeader *)(fdat + (size_t)fdat_s0 * 2048u);
        uint16_t mo_s0 = read_le16(mo + 2);
        const KfMoHeader *mh = (const KfMoHeader *)(mo + (size_t)mo_s0 * 2048u);
        uint16_t vab_s0 = read_le16(vab + 2);
        const uint8_t *vh = vab + (size_t)vab_s0 * 2048u;
        ok = (fh->section_size == 6400u * sizeof(KfMapCell)) &&
             (mh->total_size == 0x0a64u && mh->anim_count == 4u && mh->anim_table_offset == sizeof(KfMoHeader)) &&
             (memcmp(vh, "pBAV", 4) == 0);
    }
    free(fn_d); free(fdat); free(mo); free(vab);
    if (!ok) return false;

    char op2_path[1024];
    snprintf(op2_path, sizeof(op2_path), "%s/disc/files/OP/OP2.S", standalone_dir);
    FILE *fp = fopen(op2_path, "rb");
    if (!fp) return false;
    uint8_t hdr[16];
    size_t got = fread(hdr, 1, sizeof(hdr), fp);
    fclose(fp);
    return got == sizeof(hdr) && read_le32(hdr) == 0x80420101u && read_le16(hdr + 8) == 0x0160u;
}

static bool test_live_kf_cd_bcd_and_sector_checksum(const char *standalone_dir) {
    (void)standalone_dir;
    for (u32 v = 0; v < 100; ++v) {
        u32 bcd = kf_game_cd_int_to_bcd(v);
        if ((u32)kf_game_cd_bcd_to_int(bcd) != v) return false;
    }
    if (kf_game_cd_bcd_to_int(0x45u) != 45 || kf_game_cd_int_to_bcd(75u) != 0x75u) return false;

    s32 sector[512];
    s32 sum = 0x12345678;
    for (int i = 0; i < 511; ++i) {
        sector[i] = (i * 131) ^ 0x5a5a;
        sum += sector[i];
    }
    sector[511] = sum;
    if (kf_game_cd_verify_sector_checksum(sector, 1) != false) return false;
    sector[17] ^= 1;
    return kf_game_cd_verify_sector_checksum(sector, 1) == true;
}

static bool test_live_kf_mc_save_checksum(const char *standalone_dir) {
    (void)standalone_dir;
    u8 payload[0x3c00];
    s32 expected = 0;
    for (size_t i = 0; i < sizeof(payload); ++i) {
        payload[i] = (u8)((i * 37u + 19u) & 0xffu);
        expected += (s32)payload[i];
    }
    if (kf_game_mc_checksum_payload(payload) != expected) return false;
    payload[0] ^= 0x01u;
    s32 updated = kf_game_mc_checksum_payload(payload);
    return updated != expected;
}

static bool test_live_kf_math_lerp_and_clamp(const char *standalone_dir) {
    (void)standalone_dir;
    if (kf_game_math_step_linear_clamp(10, 25, 6) != 16) return false;
    if (kf_game_math_step_linear_clamp(22, 25, 6) != 25) return false;
    if (kf_game_math_step_linear_clamp(30, 18, 5) != 25) return false;
    if (kf_game_math_step_linear_clamp(20, 18, 5) != 18) return false;
    if (kf_game_math_lerp_q12(100, 500, 0) != 100) return false;
    if (kf_game_math_lerp_q12(100, 500, 2048) != 300) return false;
    if (kf_game_math_lerp_q12(100, 500, 4096) != 500) return false;
    return kf_game_math_intervals_overlap(100, 20, 85, 10) == true &&
           kf_game_math_intervals_overlap(100, 10, 85, 10) == false &&
           kf_game_math_intervals_overlap(100, 10, 120, 15) == false;
}

static bool test_live_kf_math_angles_and_pose(const char *standalone_dir) {
    (void)standalone_dir;
    if (kf_game_math_angle_diff_signed(4000, 100) != 196) return false;
    if (kf_game_math_angle_diff_signed(100, 4000) != -196) return false;
    if (kf_game_math_is_angle_cw_halfplane(1024, 512) != true) return false;
    if (kf_game_math_is_angle_cw_halfplane(512, 3072) != true) return false;
    if (kf_game_math_lerp_angle_q12(4000, 100, 2048) != 2) return false;

    s16 src[9] = {0, 100, -200, 400, 500, 600, 700, 800, -100};
    s16 dst[9] = {400, 500, 200, 0, 900, 200, 1100, 400, 300};
    s16 out[9] = {0};
    kf_game_math_lerp_pose_s16(src, dst, out, 2048);
    return out[0] == 200 && out[1] == 300 && out[2] == 0 && out[3] == 200 && out[8] == 100;
}

static bool test_live_kf_player_gauge_and_regen(const char *standalone_dir) {
    (void)standalone_dir;
    g_kf_player_scale_or_light = 0x1000;
    s32 g_mid = kf_game_player_scale_gauge(10, 3);
    s32 g_cap = kf_game_player_scale_gauge(200, 0);
    s32 curve = kf_game_player_eval_combat_curve(20, 5, 4);
    if (g_mid != 161 || g_cap != 5000 || curve <= 0) return false;

    g_kf_player_status_dark = 0x55;
    g_kf_player_status_paralyze = 99;
    kf_game_player_clamp_mp_regen();
    g_kf_player_status_curse = 0x70;
    g_kf_player_status_slow = 77;
    kf_game_player_clamp_hp_regen();
    return g_kf_player_status_dark == 0x40 && g_kf_player_status_paralyze == 0 &&
           g_kf_player_status_curse == 0x40 && g_kf_player_status_slow == 0;
}

static bool test_live_kf_end_str_decoder_init(const char *standalone_dir) {
    (void)standalone_dir;
    kf_end_init_str_decoder_state();
    return g_kf_end_bss_ptr_8009d76c == &g_kf_end_ro_table_base_80039b6c &&
           g_kf_end_bss_ptr_8009d770 == &g_kf_end_bss_table_base_80061b6c &&
           g_kf_end_bss_ptr_8009d778 == &g_kf_end_bss_table_base_80089b6c &&
           g_kf_end_bss_u16_8009d780 == 0x140u && g_kf_end_bss_u16_8009d782 == 0xf0u &&
           g_kf_end_bss_u16_8009d788 == 0x140u && g_kf_end_bss_u16_8009d78a == 0xf0u &&
           g_kf_end_bss_u16_8009d794 == 0x10u && g_kf_end_bss_u16_8009d796 == 0xf0u;
}

int main(int argc, char **argv) {
    setvbuf(stdout, NULL, _IONBF, 0);
    const char *standalone_dir = "standalone";
    for (int i = 1; i + 1 < argc; ++i) {
        if (strcmp(argv[i], "--standalone-dir") == 0) standalone_dir = argv[i + 1];
    }
    static const ParityTest tests[] = {
        {"lp32_abi_and_struct_sizes", test_lp32_abi_and_struct_sizes},
        {"retail_psx_exe_headers", test_retail_psx_exe_headers},
        {"retail_t_archive_sector_tables", test_retail_t_archive_sector_tables},
        {"retail_fnd_mo_vab_str_headers", test_retail_fnd_mo_vab_str_headers},
        {"live_kf_cd_bcd_and_sector_checksum", test_live_kf_cd_bcd_and_sector_checksum},
        {"live_kf_mc_save_checksum", test_live_kf_mc_save_checksum},
        {"live_kf_math_lerp_and_clamp", test_live_kf_math_lerp_and_clamp},
        {"live_kf_math_angles_and_pose", test_live_kf_math_angles_and_pose},
        {"live_kf_player_gauge_and_regen", test_live_kf_player_gauge_and_regen},
        {"live_kf_end_str_decoder_init", test_live_kf_end_str_decoder_init},
    };
    int total = (int)(sizeof(tests) / sizeof(tests[0]));
    int passed = 0;
    printf("{\n  \"tests\": [\n");
    for (int i = 0; i < total; ++i) {
        bool ok = tests[i].fn(standalone_dir);
        if (ok) ++passed;
        printf("    {\"name\": \"%s\", \"passed\": %s}%s\n", tests[i].name, ok ? "true" : "false", (i + 1 < total) ? "," : "");
    }
    printf("  ],\n  \"passed\": %d,\n  \"failed\": %d,\n  \"total\": %d\n}\n", passed, total - passed, total);
    return (passed == total) ? 0 : 1;
}
