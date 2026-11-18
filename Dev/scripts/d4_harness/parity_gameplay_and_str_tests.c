/* Clean-room D4 CD BCD, save checksum, Q12 math, player gauge/regen, and END STR init tests. */
#include "parity_harness.h"

static int test_live_kf_cd_bcd_and_sector_checksum(void) {
    for (u32 v = 0; v < 100u; ++v) {
        u32 bcd = kf_game_cd_int_to_bcd(v);
        if ((u32)kf_game_cd_bcd_to_int(bcd) != v) return 0;
    }
    if (kf_game_cd_bcd_to_int(0x45u) != 45 || kf_game_cd_int_to_bcd(75u) != 0x75u) return 0;

    s32 sector[512];
    s32 sum = 0x12345678;
    for (int i = 0; i < 511; ++i) {
        sector[i] = (i * 131) ^ 0x5a5a;
        sum += sector[i];
    }
    sector[511] = sum;
    if (kf_game_cd_verify_sector_checksum(sector, 1) != false) return 0;
    sector[17] ^= 1;
    return kf_game_cd_verify_sector_checksum(sector, 1) == true;
}

static int test_live_kf_mc_save_checksum(void) {
    u8 payload[0x3c00];
    s32 expected = 0;
    for (size_t i = 0; i < sizeof(payload); ++i) {
        payload[i] = (u8)((i * 37u + 19u) & 0xffu);
        expected += (s32)payload[i];
    }
    if (kf_game_mc_checksum_payload(payload) != expected) return 0;
    payload[0] ^= 0x01u;
    return kf_game_mc_checksum_payload(payload) != expected;
}

static int test_live_kf_math_lerp_and_clamp(void) {
    if (kf_game_math_step_linear_clamp(10, 25, 6) != 16) return 0;
    if (kf_game_math_step_linear_clamp(22, 25, 6) != 25) return 0;
    if (kf_game_math_step_linear_clamp(30, 18, 5) != 25) return 0;
    if (kf_game_math_step_linear_clamp(20, 18, 5) != 18) return 0;
    if (kf_game_math_lerp_q12(100, 500, 0) != 100) return 0;
    if (kf_game_math_lerp_q12(100, 500, 2048) != 300) return 0;
    if (kf_game_math_lerp_q12(100, 500, 4096) != 500) return 0;
    return kf_game_math_intervals_overlap(100, 20, 85, 10) == true
        && kf_game_math_intervals_overlap(100, 10, 85, 10) == false
        && kf_game_math_intervals_overlap(100, 10, 120, 15) == false;
}

static int test_live_kf_math_angles_and_pose(void) {
    if (kf_game_math_angle_diff_signed(4000, 100) != 196) return 0;
    if (kf_game_math_angle_diff_signed(100, 4000) != -196) return 0;
    if (kf_game_math_is_angle_cw_halfplane(1024, 512) != true) return 0;
    if (kf_game_math_is_angle_cw_halfplane(512, 3072) != true) return 0;
    if (kf_game_math_lerp_angle_q12(4000, 100, 2048) != 2u) return 0;

    s16 src[9] = {0, 100, -200, 400, 500, 600, 700, 800, -100};
    s16 dst[9] = {400, 500, 200, 0, 900, 200, 1100, 400, 300};
    s16 out[9] = {0};
    kf_game_math_lerp_pose_s16(src, dst, out, 2048);
    return out[0] == 200 && out[1] == 300 && out[2] == 0 && out[3] == 200 && out[8] == 100;
}

static int test_live_kf_player_gauge_and_regen(void) {
    g_kf_player_scale_or_light = 0x1000u;
    s32 g_mid = kf_game_player_scale_gauge(10, 3);
    s32 g_cap = kf_game_player_scale_gauge(200, 0);
    s32 curve = kf_game_player_eval_combat_curve(20, 5, 4);
    if (g_mid != 161 || g_cap != 5000 || curve <= 0) return 0;

    g_kf_player_status_dark = 0x55;
    g_kf_player_status_paralyze = 99;
    kf_game_player_clamp_mp_regen();
    g_kf_player_status_curse = 0x70;
    g_kf_player_status_slow = 77;
    kf_game_player_clamp_hp_regen();
    return g_kf_player_status_dark == 0x40 && g_kf_player_status_paralyze == 0
        && g_kf_player_status_curse == 0x40 && g_kf_player_status_slow == 0;
}

static int test_live_kf_end_str_decoder_init(void) {
    kf_end_init_str_decoder_state();
    return g_kf_end_bss_ptr_8009d76c == &g_kf_end_ro_table_base_80039b6c
        && g_kf_end_bss_ptr_8009d770 == &g_kf_end_bss_table_base_80061b6c
        && g_kf_end_bss_ptr_8009d778 == &g_kf_end_bss_table_base_80089b6c
        && g_kf_end_bss_u16_8009d780 == 0x140u && g_kf_end_bss_u16_8009d782 == 0xf0u
        && g_kf_end_bss_u16_8009d788 == 0x140u && g_kf_end_bss_u16_8009d78a == 0xf0u
        && g_kf_end_bss_u16_8009d794 == 0x10u && g_kf_end_bss_u16_8009d796 == 0xf0u;
}

int d4_run_gameplay_and_str_tests(D4ParityResult *out, int max_out) {
    if (!out || max_out < 6) return 0;
    out[0] = (D4ParityResult){"live_kf_cd_bcd_and_sector_checksum", test_live_kf_cd_bcd_and_sector_checksum()};
    out[1] = (D4ParityResult){"live_kf_mc_save_checksum", test_live_kf_mc_save_checksum()};
    out[2] = (D4ParityResult){"live_kf_math_lerp_and_clamp", test_live_kf_math_lerp_and_clamp()};
    out[3] = (D4ParityResult){"live_kf_math_angles_and_pose", test_live_kf_math_angles_and_pose()};
    out[4] = (D4ParityResult){"live_kf_player_gauge_and_regen", test_live_kf_player_gauge_and_regen()};
    out[5] = (D4ParityResult){"live_kf_end_str_decoder_init", test_live_kf_end_str_decoder_init()};
    return 6;
}
